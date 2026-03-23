import time
from pathlib import Path
from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table, put_item


class DataWorker(BaseWorker):
    """
    Worker that processes DATA tasks from SQS.
    """

    def should_process(self, message_type):
        return message_type == "DATA"

    def process_message(self, message):
        """
        Example message:
        {
            "type": "DATA",
            "table_name": "PuzzleTableDW",
            "item_id": "item_1"
        }
        """
        start_time = time.time()

        table_name = message["table_name"]
        item_id = message["item_id"]

        table = get_dynamodb_table(table_name, self.region)

        item = table.get_item(Key={"item_id": item_id}).get("Item")

        if not item:
            print(f"[WARN] No item found: {item_id}")
            return

        # Data Task Logic
        item["data_processed"] = True

        put_item(table, item)

        print(f"[INFO] Data processed for {item_id} in {int((time.time() - start_time)*1000)}ms")


if __name__ == "__main__":
    config_file = Path(__file__).parent.parent / "config" / "data_worker.json"
    worker = DataWorker(config_file)

    try:
        worker.poll_sqs()
    except KeyboardInterrupt:
        print("\n[INFO] Data worker stopped.")