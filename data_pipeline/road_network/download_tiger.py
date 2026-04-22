"""Download US Census TIGER road shapefiles.

Reads county URLs from a counties.txt file and downloads each one
into a census/ subdirectory.
"""

import os
import sys

import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

TIGER_DIR = os.path.join(DATA_DIR, "tiger")
CENSUS_DIR = os.path.join(TIGER_DIR, "census")


def main():
    zips = open(os.path.join(TIGER_DIR, "counties.txt")).readlines()
    existing = set(os.listdir(CENSUS_DIR)) if os.path.isdir(CENSUS_DIR) else set()

    for _zip in tqdm.tqdm(zips):
        _zip = _zip.strip()
        if _zip in existing:
            continue
        os.system(f"wget -P {CENSUS_DIR} {_zip}")


if __name__ == "__main__":
    main()
