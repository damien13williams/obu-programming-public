import sys
import json
import time
from pathlib import Path
from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table, put_item


class CipherWorker(BaseWorker):
    """
    Worker that processes Caesar cipher puzzles from SQS messages.

    Expected SQS message body:
    {
        "type": "CIPHER",
        "table_name": "PuzzleTableDW",
        "item_id": "item_1"
    }

    Reads the encrypted_text field from DynamoDB, brute-forces the
    Caesar shift that produces the most recognisable English words,
    and writes the solution back to the same table.
    """

    def __init__(self, config_file_path):
        # Pass the path to BaseWorker
        super().__init__(config_file_path)

        # Load config JSON for internal use
        config_path = Path(config_file_path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Load English words from words_list.txt
        words_file = Path(__file__).parent.parent / "utils" / "words_list.txt"
        if not words_file.is_file():
            raise FileNotFoundError(f"Words file not found: {words_file}")
        with open(words_file, "r") as f:
            self.ENGLISH_WORDS = set(line.strip().upper() for line in f)

        # Load SQS/Dynamo config
        self.queue_url = self.config["aws"]["sqs_queue_url"]
        self.region = self.config["aws"]["region"]
        self.max_sqs_messages = self.config["worker"]["max_sqs_messages"]
        self.sqs_wait_time = self.config["worker"]["sqs_wait_time"]
        self.visibility_timeout = self.config["worker"]["visibility_timeout"]
        self.max_retries = self.config["worker"]["max_retries"]

    # Message routing
    def should_process(self, message_type):
        return message_type == "CIPHER"

    # Caesar cipher logic
    def caesar_decrypt(self, text, shift):
        result = []
        for ch in text:
            if ch.isupper():
                result.append(chr((ord(ch) - ord('A') - shift) % 26 + ord('A')))
            elif ch.islower():
                result.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
            else:
                result.append(ch)
        return ''.join(result)

    def score_text(self, text):
        """Count how many space-separated tokens are valid English words."""
        return sum(1 for w in text.upper().split() if w in self.ENGLISH_WORDS)

    def solve_cipher(self, encrypted_message):
        """Try all 25 Caesar shifts and return the best (text, shift) pair."""
        best_score, best_text, best_shift = -1, "", 0
        for shift in range(1, 26):
            candidate = self.caesar_decrypt(encrypted_message, shift)
            score = self.score_text(candidate)
            if score > best_score:
                best_score, best_text, best_shift = score, candidate, shift
        return best_text, best_shift

    # Core processing
    def process_message(self, message):
        start_time = time.time()
        table_name = message["table_name"]
        item_id = message["item_id"]
        input_table = get_dynamodb_table(table_name, self.region)
        task_item = input_table.get_item(Key={"item_id": item_id}).get("Item")

        if not task_item:
            print(f"[WARN] No item found for item_id={item_id} in table {table_name}")
            return

        encrypted_message = task_item["encrypted_text"]
        decrypted_text, shift_used = self.solve_cipher(encrypted_message)
        vault_code = "7294"  # placeholder

        solution_item = {
            "item_id": item_id,
            "puzzle_id": task_item.get("puzzle_id", "N/A"),
            "game_id": task_item.get("game_id", "N/A"),
            "cipher_type": task_item.get("cipher_type", "caesar"),
            "encrypted_text": encrypted_message,
            "hint": task_item.get("hint", ""),
            "solution": {
                "shift": shift_used,
                "decrypted_text": decrypted_text,
                "vault_code": vault_code,
            },
            "processing_time_ms": int((time.time() - start_time) * 1000),
        }

        put_item(input_table, solution_item)
        print(f"[INFO] Solved {item_id}: shift={shift_used}, text={decrypted_text}")


# Lambda entry point
_lambda_worker: CipherWorker | None = None


def handler(event, context=None):
    """
    Lambda handler triggered by SQS.
    `event` contains all SQS messages in event['Records'].
    """
    global _lambda_worker
    if _lambda_worker is None:
        config_file = Path(__file__).parent.parent / "config" / "cipher_worker.json"
        _lambda_worker = CipherWorker(config_file)

    processed_count = 0

    # SQS messages are in event['Records']
    for record in event.get("Records", []):
        # SQS sends the message body as a string
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

if __name__ == "__main__":
    config_file = Path(__file__).parent.parent / "config" / "cipher_worker.json"
    worker = CipherWorker(config_file)
    try:
        worker.poll_sqs()
    except KeyboardInterrupt:
        print("\n[INFO] Cipher worker stopped.")