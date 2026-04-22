import os
import numpy as np
import geopandas as gpd
from matplotlib import pyplot as plt

from core.config import DATA_DIR


def visualize(coords, start: str, end: str, critical_value: float,
              basefilename: str, output_path: str = None):
    """Plot route coordinates on top of TIGER road shapefiles.

    Args:
        coords: List of [lat, lon] pairs to plot
        start: 'lat,lon' string for start point
        end: 'lat,lon' string for end point
        critical_value: The p-value used (for filename)
        basefilename: Base name for the data source (for filename)
        output_path: Where to save the PNG. If None, auto-generates path.
    """
    print("Visualizing...")
    coords = np.asarray(coords)
    # latitude = vertical position, longitude = horizontal position
    x, y = coords[:, 1], coords[:, 0]
    line_shapes = os.path.join(DATA_DIR, "tiger", "tl_2021_06081_roads.shp")

    gdf = gpd.read_file(line_shapes)
    gdf.plot(figsize=(30, 10))
    plt.xlim([-122.60, -122.00])
    plt.ylim([37.0, 37.8])
    plt.scatter(x, y, color="red")
    plt.scatter(
        [float(start.split(",")[1])], [float(start.split(",")[0])], color="green"
    )
    plt.scatter(
        [float(end.split(",")[1])], [float(end.split(",")[0])], color="green"
    )

    if output_path is None:
        from core.config import OUTPUT_DIR
        os.makedirs(os.path.join(OUTPUT_DIR, "visualizations"), exist_ok=True)
        output_path = os.path.join(
            OUTPUT_DIR, "visualizations",
            f"p{critical_value}_{basefilename}_{start}_{end}.png",
        )

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved to {output_path}")
