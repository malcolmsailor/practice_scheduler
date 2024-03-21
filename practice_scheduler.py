"""
This script takes one required argument, `--input-folder`.

The input folder should be arranged as follows:
```
[input_folder]/
    [config.yaml]
    deck1/
        [config.yaml]
    deck2/
    deck3/
```

The decks can be added with the `--add-deck` command but any config.yaml files need to
be created manually.

Each deck can contain an optional config.yaml file specifying the properties of the 
Config dataclass below. If it is not found, the config.yaml in the root folder will be
used, and if that isn't found, then the default values are used.

New items can be added either by creating a new file in the appropriate directory, or
(probably preferable) with the --add [deck name] [item name] flag.

"""

import argparse
import datetime
import os
import pdb
import re
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import asdict, dataclass, field

import git
import numpy as np
import pandas as pd
import yaml
from tabulate import tabulate


def initialize_repo(path):
    if not os.path.isdir(os.path.join(path, ".git")):
        repo = git.Repo.init(path)
        commit_changes(repo)
    else:
        repo = git.Repo(path)
    return repo


def commit_changes(repo):
    repo.git.add(A=True)
    repo.index.commit("Auto-commit: Script changes")


def undo_last_commit(repo):
    repo.git.reset("--hard", "HEAD~1")


def get_today_date():
    return datetime.date.today().strftime("%Y-%m-%d")


@dataclass
class Config:
    max_reviews_per_day: int | None = None
    max_new_per_day: int | None = None
    jitter: float | None = None
    seed: int = 42


@dataclass
class Memory:
    reviews_today: int = 0
    new_today: int = 0
    date: str = field(default_factory=get_today_date)

    def __post_init__(self):
        if self.date < get_today_date():
            self.date = get_today_date()
            self.reviews_today = 0
            self.new_today = 0


def custom_excepthook(exc_type, exc_value, exc_traceback):
    if exc_type != KeyboardInterrupt:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        pdb.post_mortem(exc_traceback)


def load_dataclass_from_yaml(config_path, data_cls, default_value=None):
    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            yaml_values = yaml.safe_load(file)
    elif default_value is not None:
        return default_value
    else:
        yaml_values = {}
    return data_cls(**yaml_values)


def folder_to_name(folder):
    return folder.replace("_", " ")


def name_to_folder(folder):
    return folder.replace(" ", "_")


def see_new(folder, deck_name):
    out = []
    deck_folder = os.path.join(folder, name_to_folder(deck_name))
    for file in os.listdir(deck_folder):
        if file.endswith(".yaml") and not file.endswith(".memory.yaml"):
            file_path = os.path.join(deck_folder, file)

            with open(file_path, "r") as yaml_file:
                data = yaml.safe_load(yaml_file)
            if data is None:
                data = {}
            touch_time = data.get("touch", os.path.getmtime(file_path))
            file_date = data.get("date", None)
            if file_date is None:
                out.append((file_path, touch_time))
    out.sort(key=lambda x: x[1])
    return [x[0] for x in out]


def process_folders(folder, global_config, peek):
    result = defaultdict(dict)
    current_date = datetime.date.today()

    for subfolder in os.listdir(folder):
        subfolder_path = os.path.join(folder, subfolder)

        if os.path.isdir(subfolder_path):
            result_key = folder_to_name(subfolder)
            files_list = []
            new_list = []

            local_config_path = os.path.join(subfolder_path, "config.yaml")
            local_config = load_dataclass_from_yaml(
                local_config_path, Config, global_config
            )

            memory_path = os.path.join(subfolder_path, ".memory.yaml")
            memory = load_dataclass_from_yaml(memory_path, Memory)

            for file in os.listdir(subfolder_path):
                if file.endswith(".yaml") and not (
                    file.endswith(".memory.yaml") or file.endswith("config.yaml")
                ):
                    file_path = os.path.join(subfolder_path, file)

                    with open(file_path, "r") as yaml_file:
                        data = yaml.safe_load(yaml_file)
                    if data is None:
                        data = {}
                    if data.get("suspend", False):
                        continue
                    touch_time = data.get("touch", os.path.getmtime(file_path))
                    file_date = data.get("date", None)
                    if file_date is None:
                        new_list.append((file_path, touch_time))
                        continue
                    if isinstance(file_date, str):
                        file_date = datetime.datetime.strptime(
                            file_date, "%Y-%m-%d"
                        ).date()

                    if file_date <= current_date + datetime.timedelta(days=int(peek)):
                        # print(datetime.datetime.fromtimestamp(mod_time), file_path)
                        files_list.append((file_path, touch_time))

            for key, list_, max_, today_ in zip(
                ("due", "new"),
                (files_list, new_list),
                (local_config.max_reviews_per_day, local_config.max_new_per_day),
                (memory.reviews_today, memory.new_today),
            ):
                if max_ is not None:
                    max_ -= today_
                list_.sort(key=lambda x: x[1])  # Sort by modification time
                if list_:
                    result[result_key][key] = [f[0] for f in list_][:max_]
                    result[result_key]["memory"] = memory
                    result[result_key]["path"] = subfolder_path

    return result


def get_studied_cards(folder, date):
    accumulator = []

    if m := re.match(r"(?P<days>\d+)d", date):
        date = (
            datetime.date.today() + datetime.timedelta(days=-1 * int(m.group("days")))
        ).strftime("%Y-%m-%d")

    current_date = datetime.date.today().strftime("%Y-%m-%d")
    assert date <= current_date
    for subfolder in os.listdir(folder):
        if subfolder == ".git":
            continue
        subfolder_path = os.path.join(folder, subfolder)

        if os.path.isdir(subfolder_path):
            deck_name = folder_to_name(subfolder)
            files_list = []
            for file in os.listdir(subfolder_path):
                if file.endswith(".yaml") and not (
                    file.endswith(".memory.yaml") or file.endswith("config.yaml")
                ):
                    file_path = os.path.join(subfolder_path, file)

                    with open(file_path, "r") as yaml_file:
                        data = yaml.safe_load(yaml_file)
                    touch_time = data.get("touch", os.path.getmtime(file_path))
                    file_date = data.get("last_seen", None)
                    past_dates = data.get("past_dates", [])
                    if file_date is None and not past_dates:
                        continue
                    if file_date == date or date in past_dates:
                        content = data.get(
                            "content",
                            os.path.splitext(os.path.basename(file_path))[0].replace(
                                "_", " "
                            ),
                        )
                        files_list.append((content, touch_time))
            files_list.sort(key=lambda x: x[1])  # Sort by modification time
            for file, _ in files_list:
                accumulator.append({"Deck": deck_name, f"Card studied on {date}": file})

    df = pd.DataFrame(accumulator)
    print(tabulate(df, headers=df.columns))  # type:ignore


def create_dataframe_from_yaml(data_dict, all=False, jitter=None):
    data_list = []

    def _append_item(file_path, new, n_due, n_new):
        with open(file_path, "r") as yaml_file:
            data = yaml.safe_load(yaml_file)
        if data is None:
            data = {}

        content = data.get(
            "content",
            os.path.splitext(os.path.basename(file_path))[0].replace("_", " "),
        )
        last_seen = data.get("last_seen", None)
        if isinstance(last_seen, str):
            last_seen = datetime.datetime.strptime(last_seen, "%Y-%m-%d").date()

        if last_seen is None:
            interval = 1
        else:
            interval = (datetime.date.today() - last_seen).days
        data_list.append(
            [
                key,
                n_due,
                n_new,
                file_path,
                content + (" (new)" if new else ""),
                interval,
            ]
        )

    for key in data_dict:
        due_list = data_dict[key].get("due", ())
        new_list = data_dict[key].get("new", ())
        if due_list or new_list:
            if not all:
                if due_list:
                    file_path = due_list[0]
                    new = False
                else:
                    file_path = new_list[0]
                    new = True
                _append_item(file_path, new, len(due_list), len(new_list))
            else:
                for file_path in due_list:
                    _append_item(file_path, False, len(due_list), len(new_list))
                for file_path in new_list:
                    _append_item(file_path, True, len(due_list), len(new_list))

    df = pd.DataFrame(
        data_list, columns=["Deck", "N due", "N new", "File", "Top card", "Good"]
    )
    if jitter is not None:
        jitter_amt = np.random.random(len(df)) * 2 * jitter - jitter + 1
        df["Good"] = (df["Good"] * jitter_amt).round().astype(int)
    df["Hard"] = df["Good"] // 2
    df.loc[df["Hard"] < 1, "Hard"] = 1
    df["Easy"] = df["Good"] * 2

    df.index += 1
    return df


def print_df(df):
    df = df[["Deck", "N due", "N new", "Top card", "Hard", "Good", "Easy"]]

    add_d = lambda x: f"{x}d"

    # In order to avoid `utureWarning: Setting an item of incompatible dtype is
    #   deprecated and will raise in a future error of pandas,` we seemingly need
    #   to drop the columns and then re-add them.
    hard_days = df["Hard"].apply(add_d).astype(str)
    good_days = df["Good"].apply(add_d).astype(str)
    easy_days = df["Easy"].apply(add_d).astype(str)
    df = df.drop(["Hard", "Good", "Easy"], axis=1)
    df["Hard"] = hard_days
    df["Good"] = good_days
    df["Easy"] = easy_days
    print(tabulate(df, headers=df.columns))


def update_yaml_from_df(df, i, response):
    if i not in df.index:
        print(f"Error: {i} is not an active deck")
        return

    file_path = df.at[i, "File"]

    if response == "Cycle":
        # Read the YAML file
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        if data is None:
            data = {}
        data["touch"] = time.time()
        with open(file_path, "w") as file:
            yaml.safe_dump(data, file)
        print(
            f"Cycled {df.at[i, 'Deck']}: {df.at[i, 'Top card']} to back of today's cards"
        )
        return

    is_new = df.at[i, "N due"] <= 0
    deck_name = df.at[i, "Deck"]

    if response == "Suspend":
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        data["suspend"] = True
        with open(file_path, "w") as file:
            yaml.safe_dump(data, file)
        print(f"Suspended {deck_name}: {df.at[i, 'Top card']}")
        return deck_name, is_new

    if response == "Bury":
        if is_new:
            raise ValueError("Can't bury new cards")
        interval = 1
    elif re.match(r"^\d+d$", response):
        interval = int(response[:-1])
    else:
        interval = df.at[i, response]

    # Read the YAML file
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    if data is None:
        data = {}

    # Update the dictionary
    today_date = datetime.date.today()
    if response != "Bury":
        data["last_seen"] = today_date.strftime("%Y-%m-%d")
    future_date = today_date + datetime.timedelta(days=int(interval))
    data["date"] = future_date.strftime("%Y-%m-%d")
    if "past_dates" in data:
        data["past_dates"].append(today_date.strftime("%Y-%m-%d"))
    else:
        data["past_dates"] = [today_date.strftime("%Y-%m-%d")]

    # Write back to the YAML file
    with open(file_path, "w") as file:
        yaml.safe_dump(data, file)

    print(f"Updated {deck_name}: {df.at[i, 'Top card']}. New due date: {future_date}")
    return deck_name, is_new


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder")
    parser.add_argument("--undo", action="store_true", help="undo the last change")
    parser.add_argument("--all", action="store_true", help="see all due cards")
    parser.add_argument(
        "--add", nargs=2, metavar=("'DECK NAME'", "'CARD NAME'"), help="add a new card"
    )
    parser.add_argument("--add-deck", metavar="'DECK NAME'", help="add a new deck")
    parser.add_argument(
        "--see-new",
        nargs="+",
        metavar="'DECK NAME'",
        help="see new cards belonging to DECK NAME",
    )
    parser.add_argument(
        "--due", metavar="YYYY-MM-DD", help="add a due date when adding a new card"
    )
    parser.add_argument(
        "--peek", type=int, default=0, metavar="N", help="peek N days ahead"
    )
    parser.add_argument(
        "--see-studied",
        nargs="?",
        metavar="YYYY-MM-DD",
        const=datetime.date.today().strftime("%Y-%m-%d"),
        help=(
            f"see cards studied on YYYY-MM-DD (default: today). "
            "You can also indicate a number of days ago as 1d or 4d"
        ),
    )
    parser.add_argument(
        "--debug", action="store_true", help="enter debuger on exception"
    )
    args, remaining = parser.parse_known_args()

    if args.add:
        assert not remaining
    responses = []
    if remaining:
        try:
            assert len(remaining) % 2 == 0
            while remaining:
                i = int(remaining[0])
                response = remaining[1].capitalize()
                remaining = remaining[2:]
                assert response in {
                    "Hard",
                    "Good",
                    "Easy",
                    "Bury",
                    "Cycle",
                    "Suspend",
                } or re.match(r"^\d+d$", response)
                responses.append((i, response))
        except:
            # TODO: (Malcolm 2024-01-10) improve this help
            print("Error: usage `1 Hard`, `2 Good`, `1 3d`, etc.")
            sys.exit(1)

    return args, responses


def check_for_illegal_chars(item):
    illegal_chars = {os.path.sep}
    for char in illegal_chars:
        if char in item:
            print(f"Error: illegal character '{char}' in '{item}'")
            sys.exit(1)


def add_deck(folder, deck):
    check_for_illegal_chars(deck)
    subfolder_path = os.path.join(folder, deck.replace(" ", "_"))
    try:
        os.makedirs(subfolder_path, exist_ok=False)
    except OSError:
        print(f"Warning: deck '{deck}' already exists")


def add_item(folder, deck, card, due):
    for item in (deck, card):
        check_for_illegal_chars(item)
    subfolder_path = os.path.join(folder, deck.replace(" ", "_"))
    assert os.path.exists(subfolder_path) and os.path.isdir(subfolder_path)

    file_path = os.path.join(subfolder_path, f"{card.replace(' ', '_')}.yaml")
    if os.path.exists(file_path):
        print(f"Error: {file_path} already exists!")
        sys.exit(1)

    data = {}
    data["touch"] = time.time()
    if due:
        assert re.match(r"\d{4}-\d{2}-\d{2}", due)
        data["date"] = due
    with open(file_path, "w") as file:
        yaml.safe_dump(data, file)


def update_memory(folder_contents, result):
    deck_name, is_new = result
    memory = folder_contents[deck_name]["memory"]
    if is_new:
        memory.new_today += 1
    else:
        memory.reviews_today += 1


def write_memories(folder_contents):
    for values in folder_contents.values():
        folder_path = values["path"]
        memory = values["memory"]
        memory_dict = asdict(memory)
        with open(os.path.join(folder_path, ".memory.yaml"), "w") as outf:
            yaml.dump(memory_dict, outf)


if __name__ == "__main__":
    pd.set_option("display.max_colwidth", 100)
    args, responses = parse_args()
    repo = initialize_repo(args.input_folder)
    changes = False
    config_path = os.path.join(args.input_folder, "config.yaml")
    global_config = load_dataclass_from_yaml(config_path, Config)
    np.random.seed(global_config.seed)
    if args.debug:
        sys.excepthook = custom_excepthook
    if args.undo:
        undo_last_commit(repo)
    if args.see_new:
        for deck_name in args.see_new:
            new_files = see_new(args.input_folder, deck_name)
            if not new_files:
                new_files = ["No new files"]
            print(tabulate([[n] for n in new_files], headers=[deck_name]))
            print("")
        sys.exit(0)
    if args.see_studied:
        get_studied_cards(args.input_folder, args.see_studied)
        sys.exit(0)

    if args.add_deck:
        changes = True
        add_deck(args.input_folder, args.add_deck)
    if args.add:
        changes = True
        assert (
            len(args.add) == 2
        ), "--add must be followed by 2 items, a deck name followed by a card"
        add_item(args.input_folder, args.add[0], args.add[1], args.due)
    elif args.due:
        print("'--due' has no effect if not adding a card")
        sys.exit(1)

    if responses:
        changes = True
        folder_contents = process_folders(args.input_folder, global_config, args.peek)
        df = create_dataframe_from_yaml(folder_contents, args.all, global_config.jitter)

        for i, response in responses:
            result = update_yaml_from_df(df, i, response)
            if result is not None:
                update_memory(folder_contents, result)
                write_memories(folder_contents)

    folder_contents = process_folders(args.input_folder, global_config, args.peek)
    df = create_dataframe_from_yaml(folder_contents, args.all, global_config.jitter)

    print_df(df)
    if changes:
        write_memories(folder_contents)
        commit_changes(repo)
