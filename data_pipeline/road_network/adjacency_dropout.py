"""Drop low-connectivity nodes from adjacency lists.

Reads adjacency files and removes nodes with 2 or fewer neighbours,
writing the filtered result to a *_dropout.txt file.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

ADJ_DIR = os.path.join(DATA_DIR, "adjacency_lists")


def main():
    bases = ["100vegetationdropout", "100distancedropout"]
    for basefilename in bases:
        input_path = os.path.join(ADJ_DIR, f"{basefilename}.txt")
        output_path = os.path.join(ADJ_DIR, f"{basefilename}_dropout.txt")

        original_tree = dict(json.loads(open(input_path).read()))
        new_file = open(output_path, "a")
        for key, value in original_tree.items():
            if len(value) > 2:
                new_file.write(f"{key}: {value}\n")


if __name__ == "__main__":
    main()
