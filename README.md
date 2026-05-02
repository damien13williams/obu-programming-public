# Puzzle Project
### Escape Room Puzzle 

---

## Overview

The Puzzle Project is a puzzle-solving engine for escape room games. Puzzle tasks are dispatched via AWS SQS to specialised worker processes that solve them (cipher decryption, data analysis, image processing, logic solving, and API aggregation) and write solutions back to DynamoDB. The system supports both local SQS polling and AWS Lambda execution, as well as sequential and parallel orchestration modes.

---

## Architecture

```
task_plan.json  →  Orchestrator (dispatches to SQS)  →  Workers (process & solve)  →  DynamoDB (stores solutions)
                                                                                              ↓
                                                                               Flask API / CLI (reads results)
```

| Worker | Message Type | SQS Queue | Description |
|---|---|---|---|
| CipherWorker | `CIPHER` | damien-cipher-sqs | Brute-forces Caesar cipher shifts using English word scoring |
| DataWorker | `DATA` | damien-data-sqs | Streams CSV from S3 and computes median value |
| ImageWorker | `IMAGE` | damien-image-sqs | Downloads image from S3, decodes QR code, extracts vault code |
| LogicWorker | `LOGIC` | damien-logic-sqs | Brute-force boolean SAT solver over variable clauses |
| APIWorker | `API` | damien-api-sqs | Fetches external APIs in parallel and evaluates conditions |

---

## Project Structure

```
project-root/
├── config/                  ← JSON config files per worker + orchestrator
├── workers/
│   ├── base_worker.py       ← Shared SQS polling, retry, and message handling
│   ├── cipher_worker.py
│   ├── data_worker.py
│   ├── image_worker.py
│   ├── logic_worker.py
│   └── api_worker.py
├── utils/
│   ├── sqs_utils.py
│   ├── dynamo_utils.py
│   └── words_list.txt
├── orchestrator/
│   └── orchestrator.py
├── app.py                   ← Flask REST API (port 3000)
└── cli.py                   ← Terminal UI for viewing game results
```

---

## Prerequisites

- Python 3.10+
- AWS credentials configured via environment variables or `~/.aws/credentials`
- Required packages:

```bash
pip install boto3 aiohttp flask pillow pyzbar
```

---

## Requirements

| ID | Description | Sprint |
|---|---|---|
| R001 | All code shall be modular and extensible and use good OO practices | 001 |
| R002 | Workers shall consume messages from an AWS SQS queue | 001 |
| R003 | The worker queue URL shall be defined in a config file loaded at runtime | 001 |
| R004 | The worker queue region shall be defined in a config file loaded at runtime | 001 |
| R005 | The worker queue max number of messages to process shall be defined in a config file loaded at runtime | 001 |
| R006 | The worker queue wait time / polling interval shall be defined in a config file loaded at runtime | 001 |
| R007 | The worker queue visibility timeout shall be defined in a config file loaded at runtime | 001 |
| R008 | The worker queue max consecutive errors shall be defined in a config file loaded at runtime | 001 |
| R009 | The worker shall log detailed messages to the console | 001 |
| R010 | The worker shall delete messages on completion | 001 |
| R011 | The worker shall use exponential backoff on errors | 001 |
| R012 | The worker shall process messages until the user enters ^C at the terminal, or the maximum number of errors is exceeded | 001 |
| R013 | The cipher worker shall process messages with the attribute `CIPHER` | 001/002 |
| R014 | The data worker shall process messages with the attribute `DATA` | 001/002 |
| R015 | The body of a cipher worker message shall contain at least a DynamoDB table and item ID that defines the work to be done | 001/002 |
| R016 | The body of a data worker message shall contain at least a DynamoDB table and item ID that defines the work to be done | 001/002 |
| R017 | The cipher worker performs the task as defined in the specification | 001/002 |
| R018 | The data worker performs the task as defined in the specification | 001/002 |
| R019 | The orchestrator requests tasks to perform by posting task requirements to a queue | 002 |
| R020 | The orchestrator monitors completion of tasks | 002 |
| R021 | The orchestrator maintains task plan | 002 |
| R022 | The orchestrator can request tasks in parallel or sequence | 002 |
| R023 | The orchestrator reads the task plan from a file | 002 |
| R024 | All workers are implemented as an AWS Lambda function | 002 |
| R025 | The logic solver worker performs the task as defined in the specification | 003 |
| R026 | The image processing worker performs the task as defined in the specification | 003 |
| R027 | The API aggregator worker performs the task as defined in the specification | 003 |
| R028 | The escape room shall integrate the orchestrator as a standalone application (or lambda function) with workers as lambda functions | 003 |
| R029 | The UI web service returns a list of all games and their status (in progress, complete, etc.) | 003/004 |
| R030 | The UI web service returns the details of a specific game (workers involved, completion time, etc.) | 003/004 |
| R031 | The UI web service is deployed as a local container executing on Docker or Podman | 004 |
| R032 | The UI web service is deployed as a local container on AWS executing as an App Runner service | 004 |
| R033 | The UI is a command-line interface running locally that allows the user to list all games and their status, list the details of a specific game, and exit the UI | 004 |

---

## Sprint 01

### Completed

- Cipher worker and base worker created and finished
- DynamoDB table and SQS queue provisioned
- Full project path functional: SQS message → DynamoDB solution
- Requirements met: R001–R013, R015, R017

### How to Run

1. Download the project and all corresponding folders/files
2. Open the project in your terminal
3. Run the base worker:

```bash
python -m workers.base_worker
```

### Improvements / To-Do

- Add a type attribute to SQS messages to route tasks to the correct worker
- Resolve terminal errors on worker shutdown
- Consolidate worker config files into a single shared config
- Review and remove unused code and files

---

## Sprint 02

### Completed

- Data worker completed and processing CSV files from S3
- Orchestrator completed and integrated
- Both workers (cipher, data) implemented as Lambda functions triggered by SQS
- End-to-end workflow: `task_plan.json` → Orchestrator → Workers → DynamoDB solution
- Requirements met: R014, R016, R018–R024

### How to Run Locally

Open the project in three separate terminals:

```bash
# Terminal 1
python -m workers.cipher_worker

# Terminal 2
python -m workers.data_worker

# Terminal 3
python -m orchestrator.orchestrator
```

### How to Run as Lambda

1. Deploy each worker file to its own Lambda function
2. Set the corresponding SQS queue as the Lambda trigger in the AWS Console
3. Set the function handler to point to the `handler()` function in each worker file (e.g. `cipher_worker.handler`)

---

## Sprint 03

### Completed

- Image worker completed — downloads from S3, decodes QR codes via pyzbar
- Logic worker completed — brute-force boolean SAT solver
- API worker completed — fetches external endpoints in parallel and evaluates conditions
- All five workers implement both local SQS polling and Lambda handler modes besides image
- Flask REST API (`app.py`) added for game status and puzzle details
- Orchestrator supports both parallel and sequential execution modes
- Requirements met: R025–R030, R033

### How to Run Locally (All Workers)

Start each worker in its own terminal, then run the orchestrator:

```bash
python -m workers.cipher_worker
python -m workers.data_worker
python -m workers.image_worker
python -m workers.logic_worker
python -m workers.api_worker

python -m orchestrator.orchestrator
```

### Flask API

Start the API server:

```bash
python app.py
```

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check — returns `{"status": "ok"}` |
| GET | `/games` | Lists all games with status and puzzle counts |
| GET | `/games/<game_id>` | Returns full details and solutions for a specific game |

---

## Sprint 04

### Completed

- Flask API containerised and deployable via Docker/Podman (R031)
- CLI (`cli.py`) added for terminal-based game inspection
- App Runner deployment not configured for AWS (R032) (told to skip and focus on CLI)
- Requirements met: R031–R033

### CLI

Launch the terminal interface:

```bash
python cli.py
```

Options: list all games, view puzzle details for a specific game, or exit.

---

## Lambda Deployment

Every worker exposes a `handler()` function that AWS Lambda calls when SQS delivers messages. The same code runs identically whether polling locally or invoked by Lambda.

### Deploying a Worker

1. Zip the worker file together with the `workers/`, `utils/`, and `config/` directories
2. Create a new Lambda function in the AWS Console (Python 3.10+ runtime)
3. Upload the zip and set the handler — e.g. `cipher_worker.handler`
4. Add the corresponding SQS queue as a trigger 
5. Package the config JSON files inside the zip under `config/`

### Handler Signature

```python
def handler(event, context=None):
    # event['Records'] contains SQS messages
    # Each record['body'] is a JSON string with type, table_name, item_id
```

---

## Docker

Workers can be containerised and run as long-lived polling processes. This is useful for local development or deployment to ECS/EC2 instead of Lambda.

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "workers.cipher_worker"]
```

---

## Orchestrator

The orchestrator reads a `task_plan.json` file and dispatches each task to the correct SQS queue. It supports two modes:

- **sequential** — dispatches one task at a time and waits for DynamoDB confirmation of completion before proceeding
- **parallel** — dispatches all tasks at once using threads, then monitors all concurrently

### task_plan.json Format

```json
{
  "mode": "parallel",
  "tasks": [
    { "type": "CIPHER", "table_name": "PuzzleTableDW", "item_id": "item_1" },
    { "type": "DATA",   "table_name": "PuzzleTableDW", "item_id": "item_5" },
    { "type": "IMAGE",  "table_name": "PuzzleTableDW", "item_id": "item_7" },
    { "type": "LOGIC",  "table_name": "PuzzleTableDW", "item_id": "item_9" },
    { "type": "API",    "table_name": "PuzzleTableDW", "item_id": "item_8" }
  ]
}
```

---

## AWS Configuration

All workers read their AWS settings from a JSON config file in `config/`. Each file specifies the region, SQS queue URL, DynamoDB table name, and worker tuning parameters.

| Config File | Queue | DynamoDB Table |
|---|---|---|
| `cipher_worker.json` | damien-cipher-sqs | PuzzleTableDW |
| `data_worker.json` | damien-data-sqs | PuzzleTableDW |
| `image_worker.json` | damien-image-sqs | PuzzleTableDW |
| `api_worker.json` | damien-api-sqs | PuzzleTableDW |

### Config File Structure

```json
{
  "aws": {
    "region": "us-east-1",
    "sqs_queue_url": "https://sqs.us-east-1.amazonaws.com/...",
    "dynamo_table": "PuzzleTableDW"
  },
  "worker": {
    "max_sqs_messages": 5,
    "sqs_wait_time": 20,
    "visibility_timeout": 180,
    "max_retries": 5
  }
}
```