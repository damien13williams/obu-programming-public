import html
import json
import os
from pathlib import Path
from collections import defaultdict
from decimal import Decimal

import boto3
from flask import Flask, jsonify, Response

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


def scan_all_items():
    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return items


def solution_present(puzzle):
    solution = puzzle.get("solution")
    return solution is not None and solution != {}


def get_game_status(puzzles):
    total = len(puzzles)
    completed = sum(1 for puzzle in puzzles if solution_present(puzzle))

    if total == 0 or completed == 0:
        return "not_started"
    if completed < total:
        return "in_progress"
    return "complete"


def build_games_list():
    items = scan_all_items()
    games = defaultdict(list)

    for item in items:
        game_id = item.get("game_id")
        if game_id:
            games[game_id].append(item)

    results = []
    for game_id, puzzles in games.items():
        results.append({
            "game_id": game_id,
            "status": get_game_status(puzzles),
            "total_puzzles": len(puzzles),
            "completed_puzzles": sum(1 for p in puzzles if solution_present(p)),
        })

    results.sort(key=lambda x: x["game_id"])
    return convert_decimal(results)


def build_game_details(game_id):
    items = scan_all_items()
    puzzles = [item for item in items if item.get("game_id") == game_id]

    if not puzzles:
        return None

    details = {
        "game_id": game_id,
        "status": get_game_status(puzzles),
        "total_puzzles": len(puzzles),
        "completed_puzzles": sum(1 for p in puzzles if solution_present(p)),
        "puzzles": [],
    }

    for p in sorted(puzzles, key=lambda x: str(x.get("item_id", ""))):
        details["puzzles"].append({
            "item_id": p.get("item_id"),
            "puzzle_id": p.get("puzzle_id"),
            "type": p.get("type") or p.get("puzzle_type") or p.get("cipher_type"),
            "processing_time_ms": p.get("processing_time_ms"),
            "solution_present": solution_present(p),
            "solution": p.get("solution", {}),
        })

    return convert_decimal(details)


def format_solution_text(value, indent=0):
    space = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, val in value.items():
            if isinstance(val, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.append(format_solution_text(val, indent + 4))
            else:
                lines.append(f"{space}{key}: {val}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for index, item in enumerate(value, start=1):
            lines.append(f"{space}[{index}]")
            lines.append(format_solution_text(item, indent + 4))
        return "\n".join(lines)
    return f"{space}{value}"


def render_games_text(games):
    if not games:
        return "No games found.\n"

    lines = ["GAME ID | STATUS | COMPLETED/TOTAL"]
    lines.append("-" * 40)
    for game in games:
        lines.append(
            f"{game['game_id']} | {game['status']} | "
            f"{game['completed_puzzles']}/{game['total_puzzles']}"
        )
    return "\n".join(lines) + "\n"


def render_game_details_text(details):
    if details is None:
        return "Game not found.\n"

    lines = [
        f"Game ID: {details['game_id']}",
        f"Status: {details['status']}",
        f"Progress: {details['completed_puzzles']}/{details['total_puzzles']} puzzles complete",
        "",
        "Puzzles:",
    ]

    for puzzle in details["puzzles"]:
        lines.append("-" * 40)
        lines.append(f"Item ID: {puzzle.get('item_id')}")
        lines.append(f"Puzzle ID: {puzzle.get('puzzle_id')}")
        lines.append(f"Type: {puzzle.get('type')}")
        lines.append(f"Processing Time: {puzzle.get('processing_time_ms')} ms")
        lines.append(f"Solution Present: {puzzle.get('solution_present')}")
        lines.append("Solution:")
        lines.append(format_solution_text(puzzle.get("solution", {}), indent=4))

    return "\n".join(lines) + "\n"


def render_games_html(games):
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(game['game_id']))}</td>"
        f"<td>{html.escape(str(game['status']))}</td>"
        f"<td>{game['completed_puzzles']}</td>"
        f"<td>{game['total_puzzles']}</td>"
        "</tr>"
        for game in games
    )

    if not rows:
        rows = "<tr><td colspan='4'>No games found.</td></tr>"

    return f"""
    <html>
        <head><title>Games</title></head>
        <body>
            <h1>Games</h1>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>Game ID</th>
                    <th>Status</th>
                    <th>Completed Puzzles</th>
                    <th>Total Puzzles</th>
                </tr>
                {rows}
            </table>
        </body>
    </html>
    """


def render_game_details_html(details):
    if details is None:
        return "<html><body><h1>Game not found</h1></body></html>"

    puzzle_blocks = []
    for puzzle in details["puzzles"]:
        solution_text = html.escape(format_solution_text(puzzle.get("solution", {})))
        puzzle_blocks.append(f"""
            <li>
                <strong>Item ID:</strong> {html.escape(str(puzzle.get('item_id')))}<br>
                <strong>Puzzle ID:</strong> {html.escape(str(puzzle.get('puzzle_id')))}<br>
                <strong>Type:</strong> {html.escape(str(puzzle.get('type')))}<br>
                <strong>Processing Time:</strong> {html.escape(str(puzzle.get('processing_time_ms')))} ms<br>
                <strong>Solution Present:</strong> {html.escape(str(puzzle.get('solution_present')))}<br>
                <strong>Solution:</strong>
                <pre>{solution_text}</pre>
            </li>
        """)

    return f"""
    <html>
        <head><title>Game Details</title></head>
        <body>
            <h1>Game Details: {html.escape(str(details['game_id']))}</h1>
            <p><strong>Status:</strong> {html.escape(str(details['status']))}</p>
            <p><strong>Progress:</strong> {details['completed_puzzles']}/{details['total_puzzles']} puzzles complete</p>
            <h2>Puzzles</h2>
            <ul>{''.join(puzzle_blocks)}</ul>
        </body>
    </html>
    """


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
@app.route("/help", methods=["GET"])
def help_page():
    readme_path = Path(__file__).parent.parent / "README.md"

    if not readme_path.exists():
        return jsonify({"error": "README.md not found"}), 404

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    html_page = f"""
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
            <pre>{html.escape(readme_content)}</pre>
        </body>
    </html>
    """

    return Response(html_page, mimetype="text/html")


# Existing JSON routes kept for compatibility.
@app.route("/games", methods=["GET"])
def list_games():
    return jsonify(build_games_list()), 200


@app.route("/games/<game_id>", methods=["GET"])
def game_details(game_id):
    details = build_game_details(game_id)
    if details is None:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(details), 200


# Final exam required routes
@app.route("/get-games-in-html", methods=["GET"])
def get_games_in_html():
    return Response(render_games_html(build_games_list()), mimetype="text/html")


@app.route("/get-games-in-text", methods=["GET"])
def get_games_in_text():
    return Response(render_games_text(build_games_list()), mimetype="text/plain")


@app.route("/get-game-details-in-html/<game_id>", methods=["GET"])
def get_game_details_in_html(game_id):
    details = build_game_details(game_id)
    status_code = 404 if details is None else 200
    return Response(render_game_details_html(details), status=status_code, mimetype="text/html")


@app.route("/get-game-details-in-text/<game_id>", methods=["GET"])
def get_game_details_in_text(game_id):
    details = build_game_details(game_id)
    status_code = 404 if details is None else 200
    return Response(render_game_details_text(details), status=status_code, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
