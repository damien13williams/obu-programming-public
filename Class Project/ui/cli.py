import boto3
from collections import defaultdict
import json
from pathlib import Path


CONFIG_PATH = Path(__file__).parent.parent / "config" / "ui.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

REGION = config["aws"]["region"]
TABLE_NAME = config["aws"]["dynamo_table"]

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def line(width=72, char="-"):
    print(char * width)


def header(title):
    line()
    print(title.center(72))
    line()


def status_label(status):
    labels = {
        "not_started": "NOT STARTED",
        "in_progress": "IN PROGRESS",
        "complete": "COMPLETE",
    }
    return labels.get(status, status.upper())


def get_all_items():
    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return items


def get_game_status(puzzles):
    total = len(puzzles)
    completed = sum(1 for p in puzzles if p.get("solution") not in (None, {}))

    if completed == 0:
        return "not_started"
    if completed < total:
        return "in_progress"
    return "complete"


def grouped_games():
    items = get_all_items()
    games = defaultdict(list)

    for item in items:
        game_id = item.get("game_id")
        if game_id:
            games[game_id].append(item)

    return dict(sorted(games.items()))


def list_games():
    games = grouped_games()

    header("GAME LIST")

    if not games:
        print("No games found.")
        return

    print(f"{'GAME ID':<20} {'STATUS':<15} {'PUZZLES':>8} {'DONE':>8}")
    line()

    for game_id, puzzles in games.items():
        status = get_game_status(puzzles)
        completed = sum(1 for p in puzzles if p.get("solution") not in (None, {}))
        print(
            f"{game_id:<20} {status_label(status):<15} {len(puzzles):>8} {completed:>8}"
        )

    line()


def format_value(value, indent=0):
    space = " " * indent

    if isinstance(value, dict):
        lines = []
        for key, val in value.items():
            if isinstance(val, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.append(format_value(val, indent + 4))
            else:
                lines.append(f"{space}{key}: {val}")
        return "\n".join(lines)

    if isinstance(value, list):
        lines = []
        for i, item in enumerate(value, start=1):
            if isinstance(item, (dict, list)):
                lines.append(f"{space}[{i}]")
                lines.append(format_value(item, indent + 4))
            else:
                lines.append(f"{space}[{i}] {item}")
        return "\n".join(lines)

    return f"{space}{value}"


def show_game(game_id):
    games = grouped_games()
    puzzles = games.get(game_id)

    header("GAME DETAILS")

    if not puzzles:
        print(f"Game '{game_id}' not found.")
        line()
        return

    status = get_game_status(puzzles)
    completed = sum(1 for p in puzzles if p.get("solution") not in (None, {}))

    print(f"Game ID   : {game_id}")
    print(f"Status    : {status_label(status)}")
    print(f"Progress  : {completed}/{len(puzzles)} puzzles complete")
    line()

    for index, puzzle in enumerate(puzzles, start=1):
        print(f"PUZZLE {index}")
        line()

        for key in sorted(puzzle.keys()):
            value = puzzle[key]

            if isinstance(value, (dict, list)):
                print(f"{key}:")
                print(format_value(value, indent=4))
            else:
                print(f"{key}: {value}")

        line()



def menu():
    header("ESCAPE ROOM CLI")
    print("1. List all games")
    print("2. Show a game's details")
    print("3. Exit")
    line()


def main():
    while True:
        menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            list_games()
            input("Press Enter to continue...")
        elif choice == "2":
            game_id = input("Enter game_id: ").strip()
            show_game(game_id)
            input("Press Enter to continue...")
        elif choice == "3":
            print("Exiting CLI.")
            break
        else:
            print("Invalid option. Please choose 1, 2, or 3.")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main()
