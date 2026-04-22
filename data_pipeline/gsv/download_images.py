"""Download Google Street View image tiles.

Reads tile URLs from unique_image_links.txt and downloads pairs of tiles
(left/right) for each panorama, skipping any already present on disk.
"""

import os
import sys

import requests
import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

GSV_DIR = os.path.join(DATA_DIR, "gsv_metadata")
IMG_DIR = os.path.join(DATA_DIR, "images", "img")


def main():
    image_links = open(os.path.join(GSV_DIR, "unique_image_links.txt")).readlines()
    existing = set(os.listdir(IMG_DIR))

    for i in tqdm.tqdm(range(0, 257402, 2)):
        name_0 = f"{format(i // 2, '06')}_0.png"
        name_1 = f"{format(i // 2, '06')}_1.png"

        if name_0 not in existing:
            try:
                response = requests.get(image_links[i], timeout=10)
                open(os.path.join(IMG_DIR, name_0), "wb").write(response.content)
            except Exception:
                pass

        if name_1 not in existing:
            try:
                response2 = requests.get(image_links[i + 1], timeout=10)
                open(os.path.join(IMG_DIR, name_1), "wb").write(response2.content)
            except Exception:
                pass


if __name__ == "__main__":
    main()
