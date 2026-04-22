"""Parse scraped Google links to extract geolocation + panorama ID pairs.

Reads geolocations and raw Google links, filters out non-street-view
entries, and writes [geolocation, pano_id] pairs to a JSON-like output.
"""

import os
import sys

import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

GSV_DIR = os.path.join(DATA_DIR, "gsv_metadata")


def main():
    geolocations = open(os.path.join(GSV_DIR, "san_mateo_county_geolocations.txt")).readlines()
    google_links = open(os.path.join(GSV_DIR, "links.txt")).readlines()
    out = open(os.path.join(GSV_DIR, "out.json"), "a")

    for i, link in tqdm.tqdm(enumerate(google_links)):
        if r"data=!3m3!1e1!3m1!2e0" in link:
            continue
        elif "data=!3m6!1e1!3m4!1sAF" in link:
            continue
        elif r"data=!3m6!1e1!3m4!1s" in link:
            out.write(
                f'["{geolocations[i].split("cbll=")[1].split(r"&cbp=")[0]}", '
                f'"{link.split(r"data=!3m6!1e1!3m4!1s")[1].split("!")[0]}"],\n'
            )
        else:
            continue


if __name__ == "__main__":
    main()
