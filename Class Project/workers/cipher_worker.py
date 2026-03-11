import json
import time
from pathlib import Path
from nltk.corpus import words
from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table, put_item
from utils.sqs_utils import get_sqs_client, receive_messages, delete_message, retry_with_backoff

class CipherWorker(BaseWorker):
    """Worker that processes Caesar cipher puzzles from SQS messages."""

    def __init__(self, config_file):
        super().__init__(config_file)
        # Load English words for scoring
        self.ENGLISH_WORDS = set(word.upper() for word in words.words())

    # ---------------- Cipher Logic ----------------
    def caesar_decrypt(self, text, shift):
        decrypted = []
        for char in text:
            if char.isupper():
                decrypted.append(chr((ord(char) - ord('A') - shift) % 26 + ord('A')))
            elif char.islower():
                decrypted.append(chr((ord(char) - ord('a') - shift) % 26 + ord('a')))
            else:
                decrypted.append(char)
        return ''.join(decrypted)

    def score_text(self, text):
        return sum(1 for w in text.upper().split() if w in self.ENGLISH_WORDS)

    def solve_cipher(self, encrypted_message):
        best_score = -1
        best_text = ""
        best_shift = 0
        for shift in range(1, 26):
            decrypted = self.caesar_decrypt(encrypted_message, shift)
            score = self.score_text(decrypted)
            if score > best_score:
                best_score = score
                best_text = decrypted
                best_shift = shift
        return best_text, best_shift

    # ---------------- Worker Processing ----------------
    def process_message(self, message):
        """
        Processes a single SQS message.
        SQS message contains:
        {
            "table_name": "CipherInputTableDW",
            "item_id": "item_1"
        }
        """
        start_time = time.time()
        input_table_name = message["table_name"]
        item_id = message["item_id"]

        # --- Pull puzzle data from input table ---
        input_table = get_dynamodb_table(input_table_name, self.region)
        task_item = input_table.get_item(Key={"item_id": item_id}).get("Item")

        if not task_item:
            print(f"[WARN] No input found for item_id={item_id} in table {input_table_name}")
            return

        encrypted_message = task_item["encrypted_text"]

        # --- Process puzzle ---
        decrypted_text, shift_used = self.solve_cipher(encrypted_message)
        vault_code = "7294"  # placeholder logic

        # --- Write solution to solution table ---
        solution_table = get_dynamodb_table("CipherSolutionTableDW", self.region)
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
                "vault_code": vault_code
            },
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }

        put_item(solution_table, solution_item)
        print(f"[INFO] Solved {item_id}: shift={shift_used}, decrypted={decrypted_text}")

    def process_sqs_message(self, msg):
        """
        Wrapper to process the SQS message and delete after success.
        """
        body = json.loads(msg["Body"])
        self.process_message(body)
        delete_message(self.sqs_client, self.sqs_url, msg["ReceiptHandle"])

    def poll_sqs(self):
        """Continuously poll SQS using config values."""
        print(f"[INFO] Polling SQS queue: {self.sqs_url}")
        while True:
            messages = receive_messages(
                client=self.sqs_client,
                queue_url=self.sqs_url,
                max_messages=self.max_messages,
                wait_time=self.wait_time,
                visibility_timeout=self.visibility_timeout
            )

            for msg in messages:
                retry_with_backoff(lambda: self.process_sqs_message(msg), max_retries=self.max_retries)


if __name__ == "__main__":
    # Load worker config dynamically
    config_file = Path(__file__).parent.parent / "config" / "cipher_worker.json"
    worker = CipherWorker(config_file)
    worker.poll_sqs()