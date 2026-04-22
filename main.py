#!/usr/bin/env python3
"""Pathfinder: Scenic driving route finder using percolation theory.

Usage:
    uv run main.py                          # default route (Belmont Hills)
    uv run main.py --example 3              # run example route 3
    uv run main.py --example list           # show all examples
    uv run main.py --start 37.52,-122.31 --end 37.45,-122.26
    uv run main.py -e 0.3 -p 0.6 -n 15     # tweak parameters
    uv run main.py --no-open                # don't open map in browser
"""
import argparse
import webbrowser

import matplotlib
matplotlib.use("Agg")

from core.percolation import run_percolation_pipeline
from core.directions import generate_route_directions

EXAMPLES = {
    "1": {
        "name": "Belmont Hills",
        "desc": "Scenic residential hills between Belmont and San Carlos",
        "start": "37.538288,-122.308576",
        "end": "37.561886,-122.3522",
        "eccentricity": 0.4,
        "scenicness": 0.5,
        "clusters": 10,
    },
    "2": {
        "name": "Hillsborough Loop",
        "desc": "Winding roads through Hillsborough estates",
        "start": "37.55,-122.34",
        "end": "37.57,-122.36",
        "eccentricity": 0.5,
        "scenicness": 0.4,
        "clusters": 8,
    },
    "3": {
        "name": "Redwood City to San Carlos",
        "desc": "Cross-town scenic route through tree-lined neighborhoods",
        "start": "37.485,-122.236",
        "end": "37.51,-122.27",
        "eccentricity": 0.4,
        "scenicness": 0.5,
        "clusters": 10,
    },
    "4": {
        "name": "Crystal Springs",
        "desc": "Along the Crystal Springs reservoir corridor",
        "start": "37.53,-122.33",
        "end": "37.47,-122.31",
        "eccentricity": 0.3,
        "scenicness": 0.4,
        "clusters": 12,
    },
    "5": {
        "name": "Foster City to Belmont",
        "desc": "From the bay flats up into the scenic hills",
        "start": "37.555,-122.27",
        "end": "37.52,-122.30",
        "eccentricity": 0.5,
        "scenicness": 0.5,
        "clusters": 8,
    },
}


def print_examples():
    print("Available example routes:\n")
    for key, ex in EXAMPLES.items():
        print(f"  {key}. {ex['name']}")
        print(f"     {ex['desc']}")
        print(f"     {ex['start']} -> {ex['end']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Find scenic driving routes using percolation theory."
    )
    parser.add_argument(
        "--example", "--ex", metavar="N",
        help="run example route (1-5), or 'list' to show all"
    )
    parser.add_argument(
        "--start", help="start lat,lon"
    )
    parser.add_argument(
        "--end", help="end lat,lon"
    )
    parser.add_argument(
        "-e", "--eccentricity", type=float,
        help="ellipse bound eccentricity 0-1 (default: 0.4)"
    )
    parser.add_argument(
        "-p", "--scenicness", type=float,
        help="scenicness p-value cutoff 0-1 (default: 0.5)"
    )
    parser.add_argument(
        "-n", "--clusters", type=int,
        help="number of scenic clusters to visit (default: 10)"
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="don't open the interactive map in the browser"
    )
    args = parser.parse_args()

    if args.example == "list":
        print_examples()
        return

    # Resolve parameters: example -> explicit args -> defaults
    if args.example:
        ex = EXAMPLES.get(args.example)
        if not ex:
            print(f"Unknown example '{args.example}'. Use --example list to see options.")
            return
        print(f"Running example {args.example}: {ex['name']}")
        print(f"  {ex['desc']}\n")
        start = args.start or ex["start"]
        end = args.end or ex["end"]
        eccentricity = args.eccentricity if args.eccentricity is not None else ex["eccentricity"]
        scenicness = args.scenicness if args.scenicness is not None else ex["scenicness"]
        clusters = args.clusters if args.clusters is not None else ex["clusters"]
    else:
        ex = EXAMPLES["1"]  # default
        start = args.start or ex["start"]
        end = args.end or ex["end"]
        eccentricity = args.eccentricity if args.eccentricity is not None else ex["eccentricity"]
        scenicness = args.scenicness if args.scenicness is not None else ex["scenicness"]
        clusters = args.clusters if args.clusters is not None else ex["clusters"]

    final_path = run_percolation_pipeline(
        start, end, eccentricity, scenicness, clusters
    )

    if final_path:
        result = generate_route_directions(final_path, start, end)
        if not args.no_open and result.get("map"):
            webbrowser.open(f"file://{result['map']}")


if __name__ == "__main__":
    main()
