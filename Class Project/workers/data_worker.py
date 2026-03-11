import os

# AWS settings
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/216990846240/cis-3823-project-queue-001")
DYNAMO_TABLE = os.getenv("DYNAMO_TABLE", "MyTasksTable")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Worker settings
MAX_SQS_RETRIES = int(os.getenv("MAX_SQS_RETRIES", 5))