"""Map panorama IDs to local filenames, and fix coordinate ordering.

Combines the former create_filename_locations.py and fix_locations.py
into two functions that can be run together or independently.
"""

import json
import os
import sys

import numpy as np
import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

GSV_DIR = os.path.join(DATA_DIR, "gsv_metadata")


def create_filename_locations():
    """For each location, replace the panorama ID with its local filename index."""
    out = open(os.path.join(GSV_DIR, "filename_locations.json"), "a")

    links = open(os.path.join(GSV_DIR, "unique_image_links.txt")).readlines()
    stuff = np.array(json.loads(open(os.path.join(GSV_DIR, "san_mateo_county_GSV.json")).read()))
    locations, IDs = stuff[:, 0], stuff[:, 1]

    for i, link in enumerate(links):
        links[i] = link.split("&panoid=")[1].split("&x=")[0]

    for j, location in tqdm.tqdm(enumerate(locations)):
        out.write(str([location, str(links.index(IDs[j]) // 2).zfill(6)]) + "\n")


def fix_locations():
    """Swap lat/lon ordering in locations.txt and write locations2.txt."""
    locations = open(os.path.join(GSV_DIR, "locations.txt")).readlines()
    out = []

    for line in locations:
        line = line.strip()
        if line == "[":
            out.append("[")
            continue
        if line == "]":
            out.append("]")
            continue
        parts = line.split()
        out.append(parts[1] + "," + parts[0])

    outfile = open(os.path.join(GSV_DIR, "locations2.txt"), "a")
    for x in out:
        outfile.write(x + "\n")


def main():
    print("Step 1: Creating filename-location mapping...")
    create_filename_locations()
    print("Step 2: Fixing coordinate ordering...")
    fix_locations()
    print("Done.")


if __name__ == "__main__":
    main()
