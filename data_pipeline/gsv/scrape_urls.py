"""Scrape resolved Google Street View URLs via Selenium.

Reads a list of GSV URLs from an input file, visits each in a browser,
waits for the redirect, and writes the final URL to an output file.
"""

import argparse
import os
import sys

import tqdm
from selenium import webdriver

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import DATA_DIR

GSV_DIR = os.path.join(DATA_DIR, "gsv_metadata")


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape resolved GSV URLs.")
    parser.add_argument("input_file", help="Name of the input file (without .txt extension) inside gsv_metadata/.")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = os.path.join(GSV_DIR, f"{args.input_file}.txt")
    output_path = os.path.join(GSV_DIR, f"out{args.input_file}.txt")

    urls = open(input_path).readlines()
    out = open(output_path, "a")
    driver = webdriver.Firefox()

    for url in tqdm.tqdm(urls):
        driver.get(url)
        initial = driver.current_url
        while driver.current_url == initial:
            pass
        out.write(driver.current_url + "\n")
        out.flush()

    driver.quit()


if __name__ == "__main__":
    main()
