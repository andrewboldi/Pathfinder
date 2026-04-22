"""Build weighted adjacency lists from road-network nodes.

Reads locations.txt and filename_locations.json, computes scenicness
heuristics (e.g. vegetation percentage) between adjacent nodes, and
writes the resulting adjacency dictionary to a file.
"""

import argparse
import json
import os
import sys
from math import asin, cos, pi, sqrt

import numpy as np
import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

LOCATIONS_PATH = os.path.join(DATA_DIR, "locations.txt")
FILENAME_LOCATIONS_PATH = os.path.join(DATA_DIR, "filename_locations.json")
PERCENTS_DIR = os.path.join(DATA_DIR, "images", "percents")
OUTPUT_DIR = os.path.join(DATA_DIR, "adjacency_lists")

# ── load shared data ────────────────────────────────────────────────────
filelines = open(LOCATIONS_PATH).readlines()
filename_locations = np.array(json.loads(open(FILENAME_LOCATIONS_PATH).read()))
coords, filename = list(filename_locations[:, 0]), list(filename_locations[:, 1])

for i, x in enumerate(filelines):
    filelines[i] = x.replace("\n", "")


# ── heuristic functions ─────────────────────────────────────────────────

def distance(latlon1, latlon2, p0_0, p0_1, p1_0, p1_1):
    """Haversine distance in miles between two lat,lon strings."""
    lat1, lon1 = latlon1.split(",")
    lat2, lon2 = latlon2.split(",")
    lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    p = pi / 180
    a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 3958.8 * asin(sqrt(a))


def vegetation(latlon1, latlon2, p0_0, p0_1, p1_0, p1_1):
    """Average vegetation fraction across the four image tiles of two nodes."""
    p0_0, p0_1, p1_0, p1_1 = np.array(p0_0), np.array(p0_1), np.array(p1_0), np.array(p1_1)

    def _get_veg(arr):
        try:
            return float(arr[:, 0][list(arr[:, 1]).index("vegetation")]) / 100
        except Exception:
            return 0.0

    p0_veg = 0.5 * (_get_veg(p0_0) + _get_veg(p0_1))
    p1_veg = 0.5 * (_get_veg(p1_0) + _get_veg(p1_1))
    return 0.5 * (p0_veg + p1_veg)


FUNCTION_LIST = {"vegetation": vegetation}


def scenicness(latlon1, latlon2, **kwargs):
    """Compute combined scenicness score between two nodes."""

    def _load_percents(latlon):
        base = "null"
        try:
            base = filename[coords.index(latlon)]
            p_0 = open(os.path.join(PERCENTS_DIR, f"{base}_0.txt")).readlines()
            p_1 = open(os.path.join(PERCENTS_DIR, f"{base}_1.txt")).readlines()
        except Exception:
            p_0 = open(os.path.join(PERCENTS_DIR, f"{base}.txt")).readlines()
            p_1 = open(os.path.join(PERCENTS_DIR, f"{base}.txt")).readlines()
        p_0 = [x.split("\n")[0].split(r"%: ") for x in p_0]
        p_1 = [x.split("\n")[0].split(r"%: ") for x in p_1]
        return p_0, p_1

    p0_0, p0_1 = _load_percents(latlon1)
    p1_0, p1_1 = _load_percents(latlon2)

    total = 0
    for var, contrib in kwargs.items():
        total += contrib * FUNCTION_LIST[var](latlon1, latlon2, p0_0, p0_1, p1_0, p1_1)
    return total


def main():
    # parameters to change
    params = {"vegetation": 1.0}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    adjacency_dict = {}

    for i, line in tqdm.tqdm(enumerate(filelines), total=len(filelines), desc="building adjacency"):
        if i == 0 or i == len(filelines) - 1:
            continue
        if filelines[i] == "[" or filelines[i] == "]":
            continue

        if filelines[i - 1] == "[":
            adjacency_dict.setdefault(line, []).append(
                [filelines[i + 1], scenicness(line, filelines[i + 1], **params)]
            )
        elif filelines[i + 1] == "]":
            adjacency_dict.setdefault(line, []).append(
                [filelines[i - 1], scenicness(line, filelines[i - 1], **params)]
            )
        elif filelines[i - 1] != "[" and filelines[i + 1] != "]":
            adjacency_dict.setdefault(line, []).append(
                [filelines[i - 1], scenicness(line, filelines[i - 1], **params)]
            )
            adjacency_dict.setdefault(line, []).append(
                [filelines[i + 1], scenicness(line, filelines[i + 1], **params)]
            )
        else:
            print(f"error on line #{i} because the line is {line}")

    out_name = ""
    for x in params.items():
        out_name += str(int(x[1] * 100))
        out_name += x[0]

    out_path = os.path.join(OUTPUT_DIR, f"{out_name}.txt")
    print(
        "{" + "\n".join("{!r}: {!r},".format(k, v) for k, v in adjacency_dict.items()) + "}",
        file=open(out_path, "a"),
    )
    print(f"Wrote adjacency list to {out_path}")


if __name__ == "__main__":
    main()
