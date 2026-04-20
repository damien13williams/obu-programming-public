import json
import time
import threading
from pathlib import Path
import os

from utils.sqs_utils import get_sqs_client, send_message
from utils.dynamo_utils import get_dynamodb_table, get_item


class Orchestrator:
    """
    Reads a task plan from a JSON file, dispatches tasks to the correct SQS queue,
    and monitors completion via DynamoDB while supporting both parallel
    and sequential execution modes.
    """

    def __init__(self, config_file, task_plan_file):
        # Load config
        config_path = Path(config_file)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path) as f:
            config = json.load(f)

        self.region = config["aws"]["region"]
        self.worker_queue_urls = config["aws"]["worker_queue_urls"]
        self.poll_interval = config["orchestrator"]["poll_interval_seconds"]
        self.completion_timeout = config["orchestrator"]["completion_timeout_seconds"]

        # Load task plan
        plan_path = Path(task_plan_file)
        if not plan_path.is_file():
            raise FileNotFoundError(f"Task plan not found: {plan_path}")
        with open(plan_path) as f:
            plan = json.load(f)

        self.mode = plan.get("mode", "sequential")
        self.tasks = plan.get("tasks", [])

        self.sqs_client = get_sqs_client(self.region)
        self.task_states = {}

        print(f"[INFO] Orchestrator initialised: mode={self.mode}, tasks={len(self.tasks)}")

    def _dispatch_task(self, task):
        """
        Send each task to the correct worker queue based on task type.
        """
        item_id = task["item_id"]
        task_type = task["type"]

        if task_type not in self.worker_queue_urls:
            print(f"[ERROR] No queue configured for task type: {task_type}")
            self.task_states[item_id] = {"task": task, "status": "failed"}
            return

        queue_url = self.worker_queue_urls[task_type]

        message = {
            "type": task_type,
            "table_name": task["table_name"],
            "item_id": item_id
        }

        send_message(self.sqs_client, queue_url, message)

        self.task_states[item_id] = {"task": task, "status": "dispatched"}
        print(f"[INFO] Dispatched task: type={task_type}, item_id={item_id}, queue={queue_url}")

    def _dispatch_parallel(self):
        print(f"[INFO] Dispatching {len(self.tasks)} tasks in PARALLEL")
        threads = [
            threading.Thread(target=self._dispatch_task, args=(task,), daemon=True)
            for task in self.tasks
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def _dispatch_sequential(self):
        print(f"[INFO] Dispatching {len(self.tasks)} tasks SEQUENTIALLY")
        for task in self.tasks:
            self._dispatch_task(task)
            item_id = task["item_id"]
            print(f"[INFO] Waiting for task {item_id} to complete before continuing...")
            completed = self._wait_for_task(task)
            if not completed:
                print(f"[ERROR] Task {item_id} timed out or failed — aborting sequence")
                break

    def _is_task_complete(self, task):
        table = get_dynamodb_table(task["table_name"], self.region)
        item = get_item(table, {"item_id": task["item_id"]})

        if not item:
            return False

        solution = item.get("solution")
        return solution is not None and solution != {}

    def _wait_for_task(self, task):
        item_id = task["item_id"]
        deadline = time.time() + self.completion_timeout

        while time.time() < deadline:
            if self._is_task_complete(task):
                self.task_states[item_id]["status"] = "complete"
                print(f"[INFO] Task {item_id} completed")
                return True

            print(f"[INFO] Task {item_id} still running — checking again in {self.poll_interval}s")
            time.sleep(self.poll_interval)

        self.task_states[item_id]["status"] = "failed"
        print(f"[WARN] Task {item_id} timed out after {self.completion_timeout}s")
        return False

    def _monitor_parallel(self):
        print("[INFO] Monitoring all tasks in parallel...")
        threads = [
            threading.Thread(target=self._wait_for_task, args=(task,), daemon=True)
            for task in self.tasks
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def _print_summary(self):
        print("\n[INFO] ── Task Summary ──────────────────────────────")
        for item_id, state in self.task_states.items():
            task_type = state["task"]["type"]
            status = state["status"].upper()
            print(f"[INFO]   {item_id} ({task_type}): {status}")
        print("[INFO] ─────────────────────────────────────────────\n")

    def run(self):
        print(f"[INFO] Orchestrator starting — mode={self.mode}")

        if self.mode == "parallel":
            self._dispatch_parallel()
            self._monitor_parallel()
        else:
            self._dispatch_sequential()

        self._print_summary()
        print("[INFO] Orchestrator finished")


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    config_file = os.path.join(BASE_DIR, "config", "orchestrator.json")
    task_plan = os.path.join(BASE_DIR, "config", "task_plan.json")

    orchestrator = Orchestrator(config_file, task_plan)
    orchestrator.run()