#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openai import OpenAI


DEFAULT_CONFIG = {
    "highlights_count": 3,
    "min_clip_seconds": 8.0,
    "max_clip_seconds": 20.0,
    "max_total_seconds": 45.0,
    "max_segments_sent": 200,  # prevent huge prompts
    "model": "gpt-4o-mini",
}


# ----------------------------
# 1) Load
# ----------------------------
def load_transcript(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# 2) Preprocess
# ----------------------------
def preprocess_segments(transcript: Dict[str, Any], max_segments: int) -> List[Dict[str, Any]]:
    """
    Keep only what we need, normalize whitespace, drop empties.
    Transcript format expected:
      {"segments": [{"start":..., "end":..., "text":...}, ...]}
    """
    segments = transcript.get("segments", [])
    cleaned = []

    for seg in segments[:max_segments]:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        text = (seg.get("text") or "").strip()

        if not text:
            continue
        if end <= start:
            continue

        # Normalize whitespace a bit
        text = " ".join(text.split())

        cleaned.append({"start": start, "end": end, "text": text})

    return cleaned


# ----------------------------
# LLM prompt + call
# ----------------------------
def build_prompt(segments: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    schema = {
        "title": "string",
        "caption": "string",
        "highlights": [
            {
                "start": "number (seconds)",
                "end": "number (seconds)",
                "text": "string (what is said in the highlight)",
                "reason": "string (why this was chosen)",
            }
        ],
    }

    rules = f"""
You are selecting highlight clips from a transcript of a video/audio.

Return JSON ONLY. No markdown. No backticks.

Constraints:
- Choose exactly {config["highlights_count"]} highlights.
- Each highlight duration must be between {config["min_clip_seconds"]} and {config["max_clip_seconds"]} seconds.
- Highlights must not overlap.
- Total duration of all highlights must be <= {config["max_total_seconds"]} seconds.
- Prefer highlights that form a mini-story: hook -> insight -> takeaway.
- Avoid repetitive content. Choose moments with clear meaning and strong wording.
- Use timestamps that align with the provided segment boundaries as closely as possible.

Output schema (must match exactly):
{json.dumps(schema, indent=2)}

Important:
- start/end must be numbers (seconds)
- start < end
"""

    # Provide segments in a compact format
    segments_payload = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in segments]

    prompt = rules + "\n\nTRANSCRIPT SEGMENTS:\n" + json.dumps(segments_payload, ensure_ascii=False)
    return prompt


def call_openai(prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY env var")

    client = OpenAI(api_key=api_key)

    # We want clean JSON output.
    # This uses "response_format" which strongly encourages valid JSON.
    resp = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": "You are a precise assistant that outputs strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    content = resp.choices[0].message.content
    return json.loads(content)


# ----------------------------
# 4) Validate (+ retry)
# ----------------------------
def overlaps(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
    return max(a[0], b[0]) < min(a[1], b[1])


def validate_highlights(result: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
    errors = []

    if not isinstance(result, dict):
        return ["Output is not a JSON object"]

    if "title" not in result or not isinstance(result["title"], str) or not result["title"].strip():
        errors.append("Missing or invalid 'title'")

    if "caption" not in result or not isinstance(result["caption"], str) or not result["caption"].strip():
        errors.append("Missing or invalid 'caption'")

    highlights = result.get("highlights")
    if not isinstance(highlights, list):
        errors.append("'highlights' must be a list")
        return errors

    if len(highlights) != config["highlights_count"]:
        errors.append(f"Must return exactly {config['highlights_count']} highlights")

    intervals = []
    total = 0.0

    for i, h in enumerate(highlights):
        if not isinstance(h, dict):
            errors.append(f"Highlight {i} is not an object")
            continue

        for key in ["start", "end", "text", "reason"]:
            if key not in h:
                errors.append(f"Highlight {i} missing '{key}'")

        try:
            start = float(h.get("start"))
            end = float(h.get("end"))
        except Exception:
            errors.append(f"Highlight {i} start/end must be numbers")
            continue

        if end <= start:
            errors.append(f"Highlight {i} must satisfy end > start")
            continue

        dur = end - start
        total += dur

        if dur < config["min_clip_seconds"] or dur > config["max_clip_seconds"]:
            errors.append(
                f"Highlight {i} duration {dur:.1f}s outside [{config['min_clip_seconds']}, {config['max_clip_seconds']}]"
            )

        text = h.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"Highlight {i} text must be a non-empty string")

        reason = h.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"Highlight {i} reason must be a non-empty string")

        intervals.append((start, end))

    # Non-overlap check
    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            if overlaps(intervals[i], intervals[j]):
                errors.append(f"Highlights {i} and {j} overlap")

    if total > config["max_total_seconds"]:
        errors.append(f"Total highlight duration {total:.1f}s exceeds max_total_seconds={config['max_total_seconds']}")

    return errors


def retry_prompt(original_prompt: str, bad_output: Dict[str, Any], errors: List[str]) -> str:
    return (
        original_prompt
        + "\n\nYour previous JSON output had validation errors.\n"
        + "ERRORS:\n"
        + "\n".join([f"- {e}" for e in errors])
        + "\n\nPrevious output:\n"
        + json.dumps(bad_output, ensure_ascii=False)
        + "\n\nReturn FIXED JSON only."
    )


def chunk_segments(segments, target_s=15.0, min_s=10.0, max_s=22.0):
    """
    Accumulate consecutive Whisper segments into chunks around ~target_s.
    Cut only at segment boundaries. Output chunks with start/end/text.
    """
    chunks = []
    cur = {"start": None, "end": None, "text_parts": []}

    def cur_dur():
        if cur["start"] is None or cur["end"] is None:
            return 0.0
        return float(cur["end"]) - float(cur["start"])

    def flush():
        if cur["start"] is None:
            return
        text = " ".join(cur["text_parts"]).strip()
        if text:
            chunks.append({"start": float(cur["start"]), "end": float(cur["end"]), "text": text})
        cur["start"] = None
        cur["end"] = None
        cur["text_parts"] = []

    for s in segments:
        s_start = float(s["start"])
        s_end = float(s["end"])
        s_text = (s.get("text") or "").strip()
        if not s_text or s_end <= s_start:
            continue

        # If current chunk is empty, start it
        if cur["start"] is None:
            cur["start"] = s_start
            cur["end"] = s_end
            cur["text_parts"] = [s_text]
            continue

        # If adding this segment would exceed max_s a lot, flush first
        prospective_end = s_end
        prospective_dur = prospective_end - float(cur["start"])

        if prospective_dur > max_s and cur_dur() >= min_s:
            flush()
            cur["start"] = s_start
            cur["end"] = s_end
            cur["text_parts"] = [s_text]
            continue

        # Otherwise add it
        cur["end"] = s_end
        cur["text_parts"].append(s_text)

        # If we've reached target, flush (even if slightly over)
        if cur_dur() >= target_s and cur_dur() >= min_s:
            flush()

    flush()
    return chunks

# ----------------------------
# 5) Write output
# ----------------------------
def write_json(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", "-i", dest="input_path", required=True, help="Path to transcript JSON")
    parser.add_argument("--out", "-o", dest="output_path", default=None, help="Output JSON path (default: same dir as input, highlights.json)")
    args = parser.parse_args()

    inp = Path(args.input_path).resolve()
    if not inp.exists():
        print(f"Input file not found: {inp}", file=sys.stderr)
        sys.exit(1)
    out_path = Path(args.output_path).resolve() if args.output_path else inp.parent / "highlights.json"

    config = dict(DEFAULT_CONFIG)

    transcript = load_transcript(str(inp))
    segments = preprocess_segments(transcript, max_segments=config["max_segments_sent"])

    if not segments:
        print("No segments found in transcript.json", file=sys.stderr)
        sys.exit(1)

    chunks = chunk_segments(segments, target_s=15, min_s=10, max_s=22)
    prompt = build_prompt(chunks, config)

    # First attempt
    result = call_openai(prompt, config)
    errors = validate_highlights(result, config)

    if not errors:
        best_result, best_errors = result, []
    else:
        # Retry with validation feedback
        prompt2 = retry_prompt(prompt, result, errors)
        result2 = call_openai(prompt2, config)
        errors2 = validate_highlights(result2, config)
        # Pick best: valid wins; else fewer errors; else prefer retry
        if not errors2:
            best_result, best_errors = result2, []
        elif len(errors2) < len(errors):
            best_result, best_errors = result2, errors2
        else:
            best_result, best_errors = result, errors

    write_json(str(out_path), best_result)
    print(f"Wrote highlights to {out_path}")

    if best_errors:
        print("Validation issues (output written anyway):", file=sys.stderr)
        for e in best_errors:
            print(" -", e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
    