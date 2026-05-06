import json
import os
from pathlib import Path

from flask import Flask, jsonify, Response
import boto3
from collections import defaultdict
from decimal import Decimal

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "ui.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

REGION = os.getenv("AWS_REGION", config["aws"]["region"])
TABLE_NAME = os.getenv("TABLE_NAME", config["aws"]["dynamo_table"])

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(x) for x in obj]
    if isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def get_game_status(puzzles):
    total = len(puzzles)
    completed = 0

    for puzzle in puzzles:
        solution = puzzle.get("solution")
        if solution is not None and solution != {}:
            completed += 1

    if completed == 0:
        return "not_started"
    elif completed < total:
        return "in_progress"
    else:
        return "complete"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
@app.route("/help", methods=["GET"])
def help_page():
    readme_path = Path(__file__).parent / "README.md"

    if not readme_path.exists():
        return jsonify({"error": "README.md not found"}), 404

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    html = f"""
    <html>
        <head>
            <title>Puzzle Project Help</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 900px;
                    margin: 40px auto;
                    line-height: 1.6;
                    padding: 20px;
                    white-space: pre-wrap;
                }}
                pre {{
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
            </style>
        </head>
        <body>
            <pre>{readme_content}</pre>
        </body>
    </html>
    """

    return Response(html, mimetype="text/html")


@app.route("/games", methods=["GET"])
def list_games():
    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    games = defaultdict(list)

    for item in items:
        game_id = item.get("game_id")
        if game_id:
            games[game_id].append(item)

    results = []
    for game_id, puzzles in games.items():
        status = get_game_status(puzzles)

        results.append({
            "game_id": game_id,
            "status": status,
            "total_puzzles": len(puzzles),
            "completed_puzzles": sum(
                1 for p in puzzles if p.get("solution") is not None and p.get("solution") != {}
            )
        })

    results.sort(key=lambda x: x["game_id"])
    return jsonify(convert_decimal(results)), 200

@app.route("/games/<game_id>", methods=["GET"])
def game_details(game_id):
    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    puzzles = [item for item in items if item.get("game_id") == game_id]

    if not puzzles:
        return jsonify({"error": "Game not found"}), 404

    details = {
        "game_id": game_id,
        "status": get_game_status(puzzles),
        "total_puzzles": len(puzzles),
        "completed_puzzles": sum(
            1 for p in puzzles if p.get("solution") is not None and p.get("solution") != {}
        ),
        "puzzles": []
    }

    for p in puzzles:
        details["puzzles"].append({
            "item_id": p.get("item_id"),
            "puzzle_id": p.get("puzzle_id"),
            "type": p.get("type") or p.get("puzzle_type") or p.get("cipher_type"),
            "processing_time_ms": p.get("processing_time_ms"),
            "solution_present": p.get("solution") is not None and p.get("solution") != {},
            "solution": p.get("solution", {})
        })

    return jsonify(convert_decimal(details)), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
