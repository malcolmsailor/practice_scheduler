import argparse
import os
from collections import defaultdict

import yaml


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder")
    parser.add_argument("--by-deck", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.by_deck:
        data = defaultdict(list)
    else:
        data = []

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
                    file_date = file_metadata.get("date", None)
                    if file_date is None:
                        new_count += 1
                        continue
                    name = file[:-5].replace("_", " ")
                    if args.by_deck:
                        data[subfolder].append((name, file_date))
                    else:
                        data.append((deck_name, name, file_date))

    if args.by_deck:
        for subfolder, files in data.items():
            files.sort(key=lambda x: x[-1])
            print(subfolder)
            for file, date in files:
                print(f"  {date} {file}")
    else:
        data.sort(key=lambda x: x[-1])
        for deck, file, date in data:
            print(f"  {date} {deck} {file}")
        print()


if __name__ == "__main__":
    main()
