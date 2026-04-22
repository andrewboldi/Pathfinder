"""Analyse semantic-segmentation masks and write per-image class percentages.

Replaces the eight identical fast1.py-fast8.py worker scripts with a single
parameterised script using --worker-id / --num-workers.
"""

import argparse
import os
import sys

import matplotlib.image as img
import numpy as np
import tqdm
from json import loads

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import DATA_DIR

MASK_DIR = os.path.join(DATA_DIR, "images", "masks")
PERCENT_DIR = os.path.join(DATA_DIR, "images", "percents")
COLORKEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "colorkey.txt")


def parse_args():
    parser = argparse.ArgumentParser(description="Compute class percentages from segmentation masks.")
    parser.add_argument("--worker-id", type=int, default=0, help="Worker index (0-based, default: 0).")
    parser.add_argument("--num-workers", type=int, default=1, help="Total number of workers (default: 1).")
    return parser.parse_args()


def main():
    args = parse_args()

    images = sorted(f for f in os.listdir(MASK_DIR) if f.endswith(".png"))
    already_done = set(os.listdir(PERCENT_DIR))
    colorkey = loads(open(COLORKEY_PATH).read())

    worker_images = images[args.worker_id::args.num_workers]
    print(f"Worker {args.worker_id}/{args.num_workers}: {len(worker_images)} images to process")

    for image in tqdm.tqdm(worker_images):
        if image.replace("png", "txt") in already_done:
            continue

        gsv = img.imread(os.path.join(MASK_DIR, image), format="JPG")
        colors, counts = np.unique(gsv.reshape(-1, 3), return_counts=True, axis=0)

        for i, color in enumerate(colors):
            for j in range(3):
                colors[i][j] = int(colors[i][j] * 255)

        for i, x in enumerate(colors):
            colors[i] = x.tolist()

        colors = colors.tolist()

        out_path = os.path.join(PERCENT_DIR, image.replace(".png", ".txt"))
        for i, x in enumerate(colors):
            print(
                f"{round(((counts[i]) / 2621.4), 2)}%: {colorkey[str(x)]}",
                file=open(out_path, "a"),
            )


if __name__ == "__main__":
    main()
