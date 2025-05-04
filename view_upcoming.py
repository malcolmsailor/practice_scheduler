import argparse
import datetime
import os
from collections import defaultdict

import yaml


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder")
    parser.add_argument("--by-deck", action="store_true")
    parser.add_argument("--max-days", type=int, default=None)
    parser.add_argument("--max-days-from-now", type=int, default=None)
    return parser.parse_args()


def get_date(file_metadata):
    if "date" not in file_metadata:
        return None
    date = datetime.datetime.strptime(file_metadata["date"], "%Y-%m-%d").date()
    current_date = datetime.date.today()
    if date < current_date:
        date = current_date
    return date


def get_interval(file_metadata):
    last_date = datetime.datetime.strptime(
        file_metadata["last_seen"], "%Y-%m-%d"
    ).date()
    next_date = get_date(file_metadata)
    return (next_date - last_date).days


def get_time_delta(date: datetime.date):
    return (date - datetime.date.today()).days


def main():
    args = parse_args()

    if args.by_deck:
        data = defaultdict(lambda: defaultdict(list))
    else:
        data = defaultdict(list)

    if args.max_days_from_now is not None:
        max_date = datetime.date.today() + datetime.timedelta(
            days=args.max_days_from_now
        )
    else:
        max_date = None

    for subfolder in os.listdir(args.input_folder):
        subfolder_path = os.path.join(args.input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            new_count = 0
            deck_name = subfolder.replace("_", " ")
            for file in os.listdir(subfolder_path):
                if file.endswith(".yaml") and not (
                    file.endswith(".memory.yaml") or file.endswith("config.yaml")
                ):
                    file_path = os.path.join(subfolder_path, file)

                    with open(file_path, "r") as yaml_file:
                        file_metadata = yaml.safe_load(yaml_file)
                    if file_metadata is None:
                        continue
                    if file_metadata.get("suspend", False):
                        continue
                    file_date = get_date(file_metadata)
                    if file_date is None:
                        new_count += 1
                        continue
                    elif max_date is not None and file_date > max_date:
                        continue
                    else:
                        interval = get_interval(file_metadata)
                    name = file[:-5].replace("_", " ")
                    if args.by_deck:
                        data[subfolder][file_date].append((name, interval))
                    else:
                        data[file_date].append((deck_name, name, interval))

    if args.by_deck:
        for subfolder, files in data.items():
            print(f"\033[34m{subfolder}\033[0m")
            print("-" * len(subfolder))
            for date in sorted(files.keys())[: args.max_days]:
                delta = get_time_delta(date)
                date_headline = f"  \033[32m{date}\033[0m ({delta} day{'' if delta == 1 else 's'} from now)"
                print(date_headline)
                # print("-" * (len(date_headline) - 9))
                these_files = files[date]
                these_files.sort(key=lambda x: x[-1])
                for i, (file, interval) in enumerate(these_files):
                    print(f"    {i + 1:>2d}. {file} ({interval} days)")
    else:
        first_date = True
        for date in sorted(data.keys())[: args.max_days]:
            delta = get_time_delta(date)
            date_headline = f"\033[32m{date}\033[0m ({delta} day{'' if delta == 1 else 's'} from now)"
            if not first_date:
                print("")
            print(date_headline)
            print("-" * (len(date_headline) - 9))
            these_files = data[date]
            these_files.sort(key=lambda x: x[-1])
            for deck, file, interval in these_files:
                print(f"  \033[34m{deck}\033[0m {file} ({interval} days)")
            first_date = False


if __name__ == "__main__":
    main()
