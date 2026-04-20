from flask import Flask, jsonify
import boto3
from collections import defaultdict
from decimal import Decimal

app = Flask(__name__)

REGION = "us-east-1"
TABLE_NAME = "PuzzleTableDW"

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)