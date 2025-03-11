#!/usr/bin/env python3
from modules.controller import Controller
from modules.view import ClickView
from modules.view_textual import TextualView
import os
import sys
import json

CONFIG_FILE = os.path.expanduser("~/.choremate_config")

pos_to_id = {}


def process_arguments() -> tuple:
    """
    Process sys.argv to get the necessary parameters, like the database file location.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            choremate_home = json.load(f).get("CHOREMATEHOME")
    else:
        envhome = os.environ.get("CHOREMATEHOME")
        if envhome:
            choremate_home = envhome
        else:
            userhome = os.path.expanduser("~")
            choremate_home = os.path.join(userhome, ".choremate_home/")

    # backup_dir = os.path.join(choremate_home, "backup")
    # log_dir = os.path.join(choremate_home, "logs")
    reset = False
    if sys.argv[1:]:
        if sys.argv[1] == "XXX":
            reset = True
            db_path = "example.db"
        elif sys.argv[1] == "YYY":
            db_path = "example.db"
        else:
            db_path = sys.argv[1]
    else:
        os.makedirs(choremate_home, exist_ok=True)
        db_path = os.path.join(choremate_home, "choremate.db")

    # os.makedirs(backup_dir, exist_ok=True)
    # os.makedirs(log_dir, exist_ok=True)
    # os.makedirs(markdown_dir, exist_ok=True)

    return choremate_home, db_path, reset


# Get command-line arguments: Process the command-line arguments to get the database file location
# choremate_home, backup_dir, log_dir, db_path, reset = process_arguments()
choremate_home, db_path, reset = process_arguments()


def main():
    print(f"Using database: {db_path}, reset: {reset}")
    controller = Controller(db_path, reset=reset)
    # view = ClickView(controller)
    view = TextualView(controller)
    view.run()


if __name__ == "__main__":
    main()
