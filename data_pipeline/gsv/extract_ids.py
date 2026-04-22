"""Extract unique image tile URLs from the GSV JSON data.

Reads the deduplicated panorama IDs and writes tile download URLs
(two tiles per panorama: x=0 and x=1) to unique_image_links.txt.
"""

import json
import os
import sys

import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

GSV_DIR = os.path.join(DATA_DIR, "gsv_metadata")


def main():
    outfile = open(os.path.join(GSV_DIR, "unique_image_links.txt"), "a")
    IDs = json.loads(open(os.path.join(GSV_DIR, "san_mateo_county_GSV.json")).read())
    out = []

    for i, ele in tqdm.tqdm(enumerate(IDs)):
        if i == 0:
            out.append(ele[1])
            continue
        if ele[1] == IDs[i - 1][1]:
            continue
        out.append(ele[1])

    for j in out:
        outfile.write(
            f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile&panoid={j}&x=0&y=0&zoom=1\n"
        )
        outfile.write(
            f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile&panoid={j}&x=1&y=0&zoom=1\n"
        )


if __name__ == "__main__":
    main()
