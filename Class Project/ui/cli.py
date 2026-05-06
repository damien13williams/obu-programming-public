import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


CONFIG_PATH = Path(__file__).parent.parent / "config" / "ui.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

DEFAULT_BASE_URL = config["service"]["base_url"].rstrip("/")
BASE_URL = DEFAULT_BASE_URL


def line(width=72, char="-"):
    print(char * width)


def header(title):
    line()
    print(title.center(72))
    line()


def set_base_url():
    global BASE_URL
    header("WEB SERVICE SETUP")
    print(f"Current service URL: {BASE_URL}")
    entered_url = input("Enter another student's App Runner URL, or press Enter to keep current: ").strip()
    if entered_url:
        BASE_URL = entered_url.rstrip("/")
    print(f"Using service URL: {BASE_URL}")


def fetch_text(path):
    url = f"{BASE_URL}{path}"
    with urlopen(url) as response:
        return response.read().decode("utf-8")


def list_games():
    header("GAME LIST")

    try:
        print(fetch_text("/get-all-game-status"))
    except HTTPError as e:
        print(f"Request failed: HTTP {e.code}")
        print("Make sure the other student's service supports /get-games-in-text.")
    except URLError:
        print("Could not connect to the UI web service.")
        print(f"Check that it is running at {BASE_URL}.")


def show_game(game_id):
    header("GAME DETAILS")

    try:
        print(fetch_text(f"/get-game-status"))
    except HTTPError as e:
        if e.code == 404:
            print(f"Game '{game_id}' not found.")
        else:
            print(f"Request failed: HTTP {e.code}")
    except URLError:
        print("Could not connect to the UI web service.")
        print(f"Check that it is running at {BASE_URL}.")

    line()


def menu():
    header("ESCAPE ROOM CLI")
    print(f"Service URL: {BASE_URL}")
    print("1. List all games")
    print("2. Show a game's details")
    print("3. Change service URL")
    print("4. Exit")
    line()


def main():
    set_base_url()

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
            set_base_url()
            input("Press Enter to continue...")
        elif choice == "4":
            print("Exiting CLI.")
            break
        else:
            print("Invalid option. Please choose 1, 2, 3, or 4.")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main()
