"""Verify that all expected image tiles were downloaded successfully.

Walks through expected filenames and reports any that are missing or
out of order in the download directory.
"""

import os
import sys

import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

GSV_DIR = os.path.join(DATA_DIR, "gsv_metadata")
IMG_DIR = os.path.join(DATA_DIR, "images", "img")


def main():
    image_links = open(os.path.join(GSV_DIR, "unique_image_links.txt")).readlines()
    filelist = sorted(os.listdir(IMG_DIR))

    for i in tqdm.tqdm(range(0, 257402, 2)):
        expected_0 = f"{format(i // 2, '06')}_0.png"
        expected_1 = f"{format(i // 2, '06')}_1.png"

        if filelist and expected_0 == filelist[0]:
            del filelist[0]
        else:
            print(f"Missing or out of order: expected {expected_0}, got {filelist[0] if filelist else 'EOF'}")

        if filelist and expected_1 == filelist[0]:
            del filelist[0]
        else:
            print(f"Missing or out of order: expected {expected_1}, got {filelist[0] if filelist else 'EOF'}")


if __name__ == "__main__":
    main()
