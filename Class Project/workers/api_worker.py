import json
import time
import asyncio
from decimal import Decimal
from pathlib import Path

import aiohttp

from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table


class APIWorker(BaseWorker):
    """
    API Aggregator Worker

    Expected SQS message body:
    {
        "type": "API",
        "table_name": "PuzzleTableDW",
        "item_id": "item_8"
    }

    Expected DynamoDB item format:
    {
        "item_id": "item_8",
        "puzzle_id": "api_001",
        "game_id": "game_12345",
        "apis": [
            {
                "url": "https://api.open-meteo.com/...",
                "extract": "current_weather.temperature",
                "name": "temperature"
            },
            {
                "url": "https://api.coingecko.com/...",
                "extract": "bitcoin.usd",
                "name": "price"
            }
        ],
        "condition": "temperature > 70 AND price > 100"
    }
    """

    def __init__(self, config_file_path):
        super().__init__(config_file_path)

        config_path = Path(config_file_path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            self.config = json.load(f)

        self.region = self.config["aws"]["region"]

    def should_process(self, message_type):
        return message_type == "API"

    async def fetch(self, session, url):
        """
        Fetch JSON from a single API endpoint.
        """
        try:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            print(f"[ERROR] API failed for {url}: {e}")
            return {}

    async def fetch_all(self, apis):
        """
        Run all API calls in parallel.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch(session, api["url"]) for api in apis]
            return await asyncio.gather(*tasks)

    def extract_value(self, data, field):
        """
        Extract field
        Example:
            field = "current_weather.temperature"
        """
        try:
            value = data
            for key in field.split("."):
                value = value[key]
            return value
        except Exception:
            return None

    def evaluate_condition(self, condition, values):
        """
        Example:
            condition = "temperature > 70 AND price > 100"
            values = {"temperature": 73.6, "price": 65000}
            returns true
        """
        try:
            expr = condition

            for key, value in values.items():
                expr = expr.replace(key, str(value))

            expr = expr.replace("AND", "and").replace("OR", "or")

            return bool(eval(expr))
        except Exception as e:
            print(f"[ERROR] condition failed: {e}")
            return False

    def convert_floats_to_decimal(self, obj):
        """
        DynamoDB does not support Python float directly. (ran into errors on this)
        Convert all floats recursively to Decimal.
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        if isinstance(obj, dict):
            return {k: self.convert_floats_to_decimal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.convert_floats_to_decimal(v) for v in obj]
        return obj

    def update_solution(self, table, item_id, new_solution, processing_time):
        try:
            existing_item = table.get_item(Key={"item_id": item_id}).get("Item", {})
            merged_solution = existing_item.get("solution", {})
            merged_solution.update(new_solution)

            merged_solution = self.convert_floats_to_decimal(merged_solution)

            table.update_item(
                Key={"item_id": item_id},
                UpdateExpression="SET #solution = :solution, processing_time_ms = :processing_time",
                ExpressionAttributeNames={
                    "#solution": "solution"
                },
                ExpressionAttributeValues={
                    ":solution": merged_solution,
                    ":processing_time": processing_time
                }
            )
        except Exception as e:
            print(f"[ERROR] Dynamo update failed: {e}")

    def process_message(self, message):
        start_time = time.time()

        table_name = message["table_name"]
        item_id = message["item_id"]

        table = get_dynamodb_table(table_name, self.region)
        item = table.get_item(Key={"item_id": item_id}).get("Item")

        if not item:
            print(f"[WARN] No item found for item_id={item_id} in table {table_name}")
            return

        apis = item.get("apis", [])
        condition = item.get("condition", "")

        if not apis:
            print(f"[WARN] No APIs found for item_id={item_id}")
            return

        responses = asyncio.run(self.fetch_all(apis))

        values = {}
        for api, response in zip(apis, responses):
            extract_path = api["extract"]
            output_name = api.get("name", extract_path.split(".")[-1])
            extracted_value = self.extract_value(response, extract_path)
            values[output_name] = extracted_value

        print(f"[DEBUG] Extracted values: {values}")

        condition_met = self.evaluate_condition(condition, values)

        solution = {
            "condition_met": condition_met,
            "values": values,
            "vault_code": "FINAL" if condition_met else "FAILED"
        }

        processing_time_ms = int((time.time() - start_time) * 1000)

        self.update_solution(table, item_id, solution, processing_time_ms)

        print(f"[INFO] API processed {item_id} -> {condition_met}")

# Lambda handler
_lambda_worker = None


def handler(event, context=None):
    """
    Lambda handler for SQS-triggered execution.
    """
    global _lambda_worker

    if _lambda_worker is None:
        config_file = Path(__file__).parent.parent / "config" / "api_worker.json"
        _lambda_worker = APIWorker(config_file)

    processed_count = 0

    for record in event.get("Records", []):
        try:
            message_body = json.loads(record["body"])
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON in message: {record.get('body')}")
            continue

        if _lambda_worker.should_process(message_body.get("type", "")):
            _lambda_worker.process_message(message_body)
            processed_count += 1
        else:
            print(f"[INFO] Skipping message of type: {message_body.get('type')}")

    return {"processed_messages": processed_count}


# Local SQS polling
if __name__ == "__main__":
    config_file = Path(__file__).parent.parent / "config" / "api_worker.json"
    worker = APIWorker(config_file)

    try:
        worker.poll_sqs()
    except KeyboardInterrupt:
        print("\n[INFO] API worker stopped.")