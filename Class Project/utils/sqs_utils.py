import boto3
import json
import time

def get_sqs_client(region):
    """
    Return a boto3 SQS client for a given region.
    """
    return boto3.client("sqs", region_name=region)


def receive_messages(client, queue_url, max_messages, wait_time, visibility_timeout):
    """
    Receive messages from SQS.

    All parameters are passed in dynamically from the worker's config.

    """
    try:
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=visibility_timeout
        )
        return response.get("Messages", [])
    except Exception as e:
        print(f"[ERROR] Failed to receive messages from SQS: {e}")
        raise


def delete_message(client, queue_url, receipt_handle):
    """
    Delete a message from SQS after processing.
    """
    try:
        client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        print(f"[INFO] Deleted message from SQS")
    except Exception as e:
        print(f"[ERROR] Failed to delete SQS message: {e}")
        raise


def send_message(client, queue_url, message_body):
    """
    Send a message to SQS.
    """
    try:
        client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        print(f"[INFO] Sent message to SQS queue {queue_url}")
    except Exception as e:
        print(f"[ERROR] Failed to send message to SQS: {e}")
        raise


def retry_with_backoff(func, max_retries):
    """
    Retry a function with exponential backoff.

    """
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as e:
            wait_time = 2 ** attempt
            print(f"[WARN] Attempt {attempt}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    raise Exception(f"[ERROR] Function failed after {max_retries} retries")