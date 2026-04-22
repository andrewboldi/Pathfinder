"""Calculate descriptive statistics for an adjacency-list file.

Reads a JSON adjacency list and prints summary statistics (mean,
std, quartiles, etc.) for the edge weights.
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

ADJ_DIR = os.path.join(DATA_DIR, "adjacency_lists")


def main():
    input_path = os.path.join(ADJ_DIR, "100distance.txt")
    distancefile = json.loads(open(input_path).read())

    li = []
    for parent, adj_li in dict(distancefile).items():
        for adj in adj_li:
            li.append(adj[1])

    df = pd.DataFrame(li)
    print(df.describe())


if __name__ == "__main__":
    main()
