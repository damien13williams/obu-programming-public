import sys
import json
import time
import csv
import io
from decimal import Decimal
from pathlib import Path
import boto3
from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table

# Make bundled packages available in Lambda (/var/task is where Lambda extracts the ZIP)
sys.path.insert(0, "/var/task/packages")


class DataWorker(BaseWorker):
    """
    Worker that processes 'DATA' type messages from SQS.

    Expected SQS message body:
    {
        "type": "DATA",
        "table_name": "PuzzleTableDW",
        "item_id": "item_5"
    }

    Reads a CSV file from S3 specified in the DynamoDB item and computes
    the median. Updates the DynamoDB item with the solution.
    """

    def __init__(self, config_file_path):
        super().__init__(config_file_path)

        # Load config JSON for internal use
        config_path = Path(config_file_path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # AWS S3 client
        self.s3_client = boto3.client("s3", region_name=self.region)

    # Only process DATA messages
    def should_process(self, message_type):
        return message_type == "DATA"

    # Compute median from CSV file-like object
    def streaming_median(self, file_obj):
        values = []
        reader = csv.reader(file_obj)
        for row in reader:
            if not row:
                continue
            try:
                values.append(float(row[0]))
            except ValueError:
                continue
        if not values:
            return None
        values.sort()
        n = len(values)
        mid = n // 2
        if n % 2 == 0:
            return (values[mid - 1] + values[mid]) / 2
        return values[mid]

    # Fetch CSV from S3 and compute median
    def compute_median_from_s3(self, bucket, key):
        obj = self.s3_client.get_object(Bucket=bucket, Key=key)
        return self.streaming_median(io.TextIOWrapper(obj["Body"], encoding="utf-8"))

    # Core processing
    def process_message(self, message):
        start_time = time.time()
        table_name = message["table_name"]
        item_id = message["item_id"]

        table = get_dynamodb_table(table_name, self.region)
        item = table.get_item(Key={"item_id": item_id}).get("Item")
        if not item:
            print(f"[WARN] No item found for item_id={item_id} in table {table_name}")
            return

        # Extract S3 info
        s3_bucket = item.get("s3_bucket")
        s3_key = item.get("s3_key")
        task = item.get("task")
        if not s3_bucket or not s3_key or task != "find_median":
            print(f"[WARN] Invalid DynamoDB item for median: {item}")
            return

        # Compute median
        median = self.compute_median_from_s3(s3_bucket, s3_key)
        vault_code = 1234  # placeholder value

        # Update only the solution and processing time
        table.update_item(
            Key={"item_id": item_id},
            UpdateExpression="SET #sol = :solution, processing_time_ms = :ptime",
            ExpressionAttributeNames={"#sol": "solution"},
            ExpressionAttributeValues={
                ":solution": {
                    "median": Decimal(str(median)) if median is not None else None,
                    "vault_code": vault_code
                },
                ":ptime": int((time.time() - start_time) * 1000)
            }
        )

        print(f"[INFO] Processed {item_id}: median={median}, vault_code={vault_code}")


# Lambda entry point
_lambda_worker: DataWorker | None = None


def handler(event, context=None):
    """
    Lambda handler triggered by SQS messages
    """
    global _lambda_worker
    if _lambda_worker is None:
        config_file = Path(__file__).parent.parent / "config" / "data_worker.json"
        _lambda_worker = DataWorker(config_file)

    processed_count = 0

    for record in event.get("Records", []):
        try:
            message_body = json.loads(record["body"])
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON in message: {record['body']}")
            continue

        if _lambda_worker.should_process(message_body.get("type", "")):
            _lambda_worker.process_message(message_body)
            processed_count += 1
        else:
            print(f"[INFO] Skipping message of type: {message_body.get('type')}")

    return {"processed_messages": processed_count}


# Local testing
if __name__ == "__main__":
    config_file = Path(__file__).parent.parent / "config" / "data_worker.json"
    worker = DataWorker(config_file)
    try:
        worker.poll_sqs()  # Polls SQS continuously like CipherWorker
    except KeyboardInterrupt:
        print("\n[INFO] Data worker stopped.")