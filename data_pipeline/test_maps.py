"""Generate a Google Maps directions URL from evenly-spaced locations.

Picks ~23 evenly-spaced waypoints from locations.txt and prints a
Google Maps URL joining them with slashes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import DATA_DIR


def main():
    locations = open(os.path.join(DATA_DIR, "locations.txt")).readlines()
    a = ""
    b = []

    for i in range(0, len(locations), len(locations) // 23):
        b.append(locations[i].replace("\n", "").replace("[", "").replace("]", ""))
        a = "/".join(b)

    print(a)


if __name__ == "__main__":
    main()
