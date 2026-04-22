"""Semantic segmentation inference using mmseg (BDD100K model).

Merges the former gpu/inference.py and cpu/ITWORKSFULL.py into a single
script controlled by a --device flag.
"""

import argparse
import os
import sys

import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import DATA_DIR, PROJECT_ROOT

from mmseg.apis import inference_segmentor, init_segmentor

# ── paths ────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(
    PROJECT_ROOT,
    "scenery", "models", "bdd100k", "sem_seg", "configs", "sem_seg",
    "upernet_convnext-t_fp16_512x1024_80k_sem_seg_bdd100k.py",
)
CHECKPOINT_FILE = os.path.join(
    DATA_DIR, "models",
    "upernet_convnext-t_fp16_512x1024_80k_sem_seg_bdd100k.pth",
)

IMG_DIR = os.path.join(DATA_DIR, "images", "img")
MASK_DIR = os.path.join(DATA_DIR, "images", "masks")

# ── BDD100K 19-class palette ────────────────────────────────────────────
MY_PALETTE = [
    [128, 64, 128],
    [244, 35, 232],
    [70, 70, 70],
    [102, 102, 156],
    [190, 153, 153],
    [153, 153, 153],
    [250, 170, 30],
    [220, 220, 0],
    [107, 142, 35],
    [152, 251, 152],
    [70, 130, 180],
    [220, 20, 60],
    [255, 0, 0],
    [0, 0, 142],
    [0, 0, 70],
    [0, 60, 100],
    [0, 80, 100],
    [0, 0, 230],
    [119, 11, 32],
]


def parse_args():
    parser = argparse.ArgumentParser(description="Run BDD100K semantic segmentation inference.")
    parser.add_argument(
        "--device", choices=["cpu", "gpu"], default="gpu",
        help="Device to run inference on (default: gpu).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    device = "cuda" if args.device == "gpu" else "cpu"

    model = init_segmentor(CONFIG_FILE, CHECKPOINT_FILE, device=device)

    all_images = sorted(os.listdir(IMG_DIR))
    existing_masks = set(os.listdir(MASK_DIR))

    todo = [f for f in all_images if f not in existing_masks]
    print(f"{len(todo)} images to process ({len(all_images)} total, {len(existing_masks)} already done)")

    for filename in tqdm.tqdm(todo):
        img_path = os.path.join(IMG_DIR, filename)
        mask_path = os.path.join(MASK_DIR, filename)
        result = inference_segmentor(model, img_path)
        model.show_result(img_path, result, MY_PALETTE, show=False, out_file=mask_path, opacity=1.0)


if __name__ == "__main__":
    main()
