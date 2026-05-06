import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


CONFIG_PATH = Path(__file__).parent.parent / "config" / "ui.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

BASE_URL = config["service"]["base_url"].rstrip("/")


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


def fetch_json(path):
    url = f"{BASE_URL}{path}"
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def list_games():
    header("GAME LIST")

    try:
        games = fetch_json("/games")
    except HTTPError as e:
        print(f"Request failed: HTTP {e.code}")
        print("Make sure the UI web service is running.")
        return
    except URLError:
        print("Could not connect to the UI web service.")
        print(f"Check that it is running at {BASE_URL}.")
        return

    if not games:
        print("No games found.")
        return

    print(f"{'GAME ID':<20} {'STATUS':<15} {'PUZZLES':>8} {'DONE':>8}")
    line()

    for game in games:
        print(
            f"{game.get('game_id', 'N/A'):<20} "
            f"{status_label(game.get('status', 'unknown')):<15} "
            f"{game.get('total_puzzles', 0):>8} "
            f"{game.get('completed_puzzles', 0):>8}"
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
    header("GAME DETAILS")

    try:
        details = fetch_json(f"/games/{game_id}")
    except HTTPError as e:
        if e.code == 404:
            print(f"Game '{game_id}' not found.")
            line()
            return
        print(f"Request failed: HTTP {e.code}")
        line()
        return
    except URLError:
        print("Could not connect to the UI web service.")
        print(f"Check that it is running at {BASE_URL}.")
        line()
        return

    puzzles = details.get("puzzles", [])

    print(f"Game ID   : {details.get('game_id', game_id)}")
    print(f"Status    : {status_label(details.get('status', 'unknown'))}")
    print(
        f"Progress  : {details.get('completed_puzzles', 0)}/"
        f"{details.get('total_puzzles', len(puzzles))} puzzles complete"
    )
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
