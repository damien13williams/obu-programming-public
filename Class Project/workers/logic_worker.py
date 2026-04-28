import json
import time
from itertools import product
from pathlib import Path
from decimal import Decimal

from workers.base_worker import BaseWorker
from utils.dynamo_utils import get_dynamodb_table


class LogicWorker(BaseWorker):
    """
    Logic Solver Worker

    Expected SQS message body:
    {
        "type": "LOGIC",
        "table_name": "PuzzleTableDW",
        "item_id": "item_9"
    }

    Expected DynamoDB item format:
    {
        "item_id": "item_9",
        "puzzle_id": "logic_001",
        "game_id": "game_12345",
        "puzzle_type": "boolean_sat",
        "clauses": [
            ["A", "B", "!C"],
            ["!A", "C"],
            ["B", "!D"]
        ],
        "variables": ["A", "B", "C", "D"]
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
        return message_type == "LOGIC"

    def literal_value(self, literal, assignment):
        """
        Evaluate a literal under an assignment.
        Examples:
            "A"  -> assignment["A"]
            "!A" -> not assignment["A"]
        """
        if literal.startswith("!"):
            var = literal[1:]
            return not assignment[var]
        return assignment[literal]

    def clause_satisfied(self, clause, assignment):
        """
        A clause is satisfied if any literal in it is True.
        """
        return any(self.literal_value(lit, assignment) for lit in clause)

    def solve_boolean_sat(self, variables, clauses):
        """
        Brute-force SAT solver.
        Tries all True/False assignments and returns the first satisfying one.
        """
        for values in product([False, True], repeat=len(variables)):
            assignment = dict(zip(variables, values))
            if all(self.clause_satisfied(clause, assignment) for clause in clauses):
                return assignment
        return None

    def assignment_to_vault_code(self, variables, assignment):
        """
        Convert assignment to binary string in variable order.
        True -> 1
        False -> 0
        """
        return "".join("1" if assignment[var] else "0" for var in variables)

    def convert_numbers_for_dynamodb(self, obj):
        """
        Convert Python numeric types into DynamoDB-safe values.
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        if isinstance(obj, dict):
            return {k: self.convert_numbers_for_dynamodb(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.convert_numbers_for_dynamodb(v) for v in obj]
        return obj

    def update_solution(self, table, item_id, new_solution, processing_time):
        try:
            existing_item = table.get_item(Key={"item_id": item_id}).get("Item", {})
            merged_solution = existing_item.get("solution", {})
            merged_solution.update(new_solution)

            merged_solution = self.convert_numbers_for_dynamodb(merged_solution)

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

        puzzle_type = item.get("puzzle_type", "")
        variables = item.get("variables", [])
        clauses = item.get("clauses", [])

        if puzzle_type != "boolean_sat":
            print(f"[WARN] Unsupported puzzle_type '{puzzle_type}' for item_id={item_id}")
            return

        if not variables or not clauses:
            print(f"[WARN] Missing variables or clauses for item_id={item_id}")
            return

        assignment = self.solve_boolean_sat(variables, clauses)

        if assignment is None:
            solution = {
                "assignment": {},
                "vault_code": "",
                "satisfied": False
            }
            print(f"[INFO] No satisfying assignment found for {item_id}")
        else:
            vault_code = self.assignment_to_vault_code(variables, assignment)
            solution = {
                "assignment": assignment,
                "vault_code": vault_code,
                "satisfied": True
            }
            print(f"[INFO] Logic solved {item_id} -> {vault_code}")

        processing_time_ms = int((time.time() - start_time) * 1000)
        self.update_solution(table, item_id, solution, processing_time_ms)


# Lambda handler
_lambda_worker = None


def handler(event, context=None):
    """
    Lambda handler for SQS-triggered execution.
    """
    global _lambda_worker

    if _lambda_worker is None:
        config_file = Path(__file__).parent.parent / "config" / "logic_worker.json"
        _lambda_worker = LogicWorker(config_file)

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
    config_file = Path(__file__).parent.parent / "config" / "logic_worker.json"
    worker = LogicWorker(config_file)

    try:
        worker.poll_sqs()
    except KeyboardInterrupt:
        print("\n[INFO] Logic worker stopped.")