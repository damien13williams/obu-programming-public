import json
from utils.sqs_utils import get_sqs_client, receive_messages, delete_message, retry_with_backoff


class BaseWorker:
    """
    Base class for all workers.
    Handles SQS polling, retries, and message deletion.
    Child workers only implement process_message().
    """

    def __init__(self, config_file):
        # Load configuration
        with open(config_file) as f:
            config = json.load(f)

        # AWS config
        self.region = config["aws"]["region"]
        self.sqs_url = config["aws"]["sqs_queue_url"]


        # Worker config
        self.max_messages = config["worker"]["max_sqs_messages"]
        self.wait_time = config["worker"]["sqs_wait_time"]
        self.visibility_timeout = config["worker"]["visibility_timeout"]
        self.max_retries = config["worker"]["max_retries"]

        # Create SQS client
        self.sqs_client = get_sqs_client(self.region)

    # Polls SQS for incoming messages

    def poll_sqs(self):
        """
        Main loop for polling SQS.
        """
        print(f"[INFO] Worker polling queue: {self.sqs_url}")

        while True:
            messages = receive_messages(
                client=self.sqs_client,
                queue_url=self.sqs_url,
                max_messages=self.max_messages,
                wait_time=self.wait_time,
                visibility_timeout=self.visibility_timeout
            )

            if not messages:
                continue

            for msg in messages:
                retry_with_backoff(
                    lambda: self.process_sqs_message(msg),
                    max_retries=self.max_retries
                )

    # Handles the message for processing and deletes after

    def process_sqs_message(self, msg):
        """
        Wrapper that extracts the message body and deletes it after success.
        """
        body = json.loads(msg["Body"])

        print(f"[INFO] Processing message: {body}")

        # Call the specific worker logic
        self.process_message(body)

        # Delete message after successful processing
        delete_message(
            self.sqs_client,
            self.sqs_url,
            msg["ReceiptHandle"]
        )

        print("[INFO] Message processed and deleted")

    #

    def process_message(self, message):
        """
        Must be implemented by child workers.
        """
        raise NotImplementedError("Child workers must implement process_message()")\
        
if __name__ == "__main__":
    import subprocess
    import sys

    WORKERS = ["cipher", "data", "worker3", "worker4", "worker5"]

    processes = [
        subprocess.Popen(["python", "-m", f"workers.{w}_worker"])
        for w in WORKERS
    ]

    print("[INFO]All workers nowrunning. Press Ctrl+C to stop.")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down all workers...")
        for p in processes:
            p.terminate()
        sys.exit(0)