
brew install awscli
aws --version

aws configure
# Paste your access key ID
# Paste your secret access key
# Region: eu-west-1
# Output format: json

# Step 6: Set Up Billing Alerts (5 mins)
# Critical so you don't get surprised:

# Go to Billing Dashboard → Billing preferences
# Enable "Receive Free Tier Usage Alerts"
# Enable "Receive Billing Alerts"
# Go to CloudWatch → Alarms → Billing
# Create alarm: Alert when charges > $20

# Replace with your bucket name (must be globally unique)
aws s3 mb s3://video-highlights-jade-1234 --region eu-west-1

# FIX PERMISSIONS
# Do this in the AWS Console (recommended)

# Go to IAM → Users → jadapus → Add permissions.

# For MVP speed, attach these managed policies:
# 	•	AmazonS3FullAccess
# 	•	AmazonEC2FullAccess

aws s3 ls
aws s3 ls s3://video-highlights-jade-1234
echo "test" > test.txt
aws s3 cp test.txt s3://video-highlights-jade-1234/test.txt
aws s3 ls s3://video-highlights-jade-1234/

export AWS_REGION=eu-west-1
export BUCKET=video-highlights-jade-123
export ROLE_NAME=clipforge-worker-role
export POLICY_NAME=clipforge-s3-policy
export INSTANCE_NAME=clipforge-worker
export KEY_NAME=clipforge-worker-key

echo "test" > /tmp/clipforge-test.txt
aws s3 cp /tmp/clipforge-test.txt s3://$BUCKET/infra/clipforge-test.txt --region $AWS_REGION
aws s3 ls s3://$BUCKET/infra/ --region $AWS_REGION

#Policy is set directly on console 
	# 1.	AWS Console → IAM → Policies → Create policy
	# 2.	Choose JSON
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Sid": "ListBucket",
#       "Effect": "Allow",
#       "Action": ["s3:ListBucket"],
#       "Resource": ["arn:aws:s3:::video-highlights-jade-1234"]
#     },
#     {
#       "Sid": "RWObjects",
#       "Effect": "Allow",
#       "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
#       "Resource": ["arn:aws:s3:::video-highlights-jade-1234/*"]
#     }
#   ]
# }

# 1.	AWS Console → EC2 → Instances → Launch instances
# 	2.	Name: clipforge-worker
# 	3.	Application and OS Images (Amazon Machine Image):
# 	•	Choose Amazon Linux 2023 (not Amazon Linux 2)
# 	•	Architecture: 64-bit (x86)
# 	4.	Instance type: t3.large
# 	5.	Key pair: select or create clipforge-worker-key
# 	6.	Network settings:
# 	•	Security group: clipforge-worker-sg
# 	•	SSH inbound rule: port 22 from your IP only
# 	7.	Advanced details:
# 	•	IAM instance profile: select clipforge-worker-role
# 	8.	Storage: 50 GB gp3
# 	9.	Launch

# ON EC2 instance 
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

