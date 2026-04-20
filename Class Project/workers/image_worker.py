import json
import time
import boto3
import io
import re
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode

from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table, put_item


class ImageWorker(BaseWorker):
    """
    Worker that processes QR image puzzles from SQS messages.

    Expected SQS message:
    {
        "type": "IMAGE",
        "table_name": "PuzzleTableDW",
        "item_id": "image_001"
    }

    Workflow:
    1. Fetch item from DynamoDB
    2. Download image from S3
    3. Decode QR code
    4. Extract vault code (placeholder logic)
    5. Write full updated item back to DynamoDB
    """

    def __init__(self, config_file_path):
        super().__init__(config_file_path)

        config_path = Path(config_file_path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            self.config = json.load(f)

        self.s3 = boto3.client("s3")

        self.region = self.config["aws"]["region"]
        self.queue_url = self.config["aws"]["sqs_queue_url"]
        self.max_sqs_messages = self.config["worker"]["max_sqs_messages"]
        self.sqs_wait_time = self.config["worker"]["sqs_wait_time"]
        self.max_retries = self.config["worker"]["max_retries"]

    # ---------------------------
    # Message routing
    # ---------------------------
    def should_process(self, message_type):
        return message_type == "IMAGE"

    # ---------------------------
    # Image logic
    # ---------------------------
    def download_image(self, bucket, key):
        obj = self.s3.get_object(Bucket=bucket, Key=key)
        return Image.open(io.BytesIO(obj["Body"].read())).convert("RGB")

    def extract_qr(self, image):
        decoded = decode(image)
        if not decoded:
            return None
        return decoded[0].data.decode("utf-8")

    def extract_vault_code(self, text):
        # Placeholder logic (same idea as your earlier version)
        return "0000"

    # ---------------------------
    # Core processing
    # ---------------------------
    def process_message(self, message):
        start_time = time.time()

        table_name = message["table_name"]
        item_id = message["item_id"]

        table = get_dynamodb_table(table_name, self.region)
        task_item = table.get_item(Key={"item_id": item_id}).get("Item")

        if not task_item:
            print(f"[WARN] No item found for item_id={item_id}")
            return

        # Get S3 info FROM DYNAMODB (NOT SQS)
        bucket = task_item["s3_bucket"]
        key = task_item["s3_key"]

        # Process image
        image = self.download_image(bucket, key)

        extracted_text = self.extract_qr(image)
        if not extracted_text:
            extracted_text = ""

        vault_code = self.extract_vault_code(extracted_text)

        processing_time = int((time.time() - start_time) * 1000)

        updated_item = {
            **task_item,  # preserve everything already in DB

            "solution": {
                "extracted_text": extracted_text,
                "vault_code": vault_code
            },

            "status": "completed",
            "processing_time_ms": processing_time
        }

        put_item(table, updated_item)

        print(f"[INFO] Solved {item_id}: {extracted_text}")

if __name__ == "__main__":
    config_file = Path(__file__).parent.parent / "config" / "image_worker.json"
    worker = ImageWorker(config_file)

    try:
        worker.poll_sqs()
    except KeyboardInterrupt:
        print("\n[INFO] Image worker stopped.")