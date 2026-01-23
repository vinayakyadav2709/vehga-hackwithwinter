#!/usr/bin/env python3
"""
Extract bounds from SUMO network file (.net.xml or .net.xml.gz)
Shows min/max lat/lon to help decide crop area
"""

import xml.etree.ElementTree as ET
import sys
import gzip


def get_bounds(net_file):
    """Extract bounds from SUMO network file."""
    try:
        if net_file.endswith(".gz"):
            with gzip.open(net_file, "rt") as f:
                tree = ET.parse(f)
        else:
            tree = ET.parse(net_file)
        root = tree.getroot()

        # SUMO network structure: <net><location ... /><junction ... /></net>
        location = root.find("location")
        if location is not None:
            net_offset = location.get("netOffset", "0,0").split(",")
            print(f"Network Offset: {net_offset}")

        # Get junction bounds
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        junctions = root.findall("junction")
        print(f"Found {len(junctions)} junctions")

        for junction in junctions:
            x = float(junction.get("x", 0))
            y = float(junction.get("y", 0))
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        print(f"\nBounds (in SUMO coordinates):")
        print(f"  X: {min_x:.2f} to {max_x:.2f}")
        print(f"  Y: {min_y:.2f} to {max_y:.2f}")
        print(f"  Width: {max_x - min_x:.2f}")
        print(f"  Height: {max_y - min_y:.2f}")

        # Check for conversion info
        conv = root.find("location")
        if conv is not None:
            proj_params = conv.get("projParameter", "")
            print(f"\nProjection: {proj_params}")

        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
        }

    except Exception as e:
        print(f"Error reading {net_file}: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_bounds.py <network.net.xml>")
        print("Example: python get_bounds.py coldplay2/osm.net.xml")
        sys.exit(1)

    net_file = sys.argv[1]
    bounds = get_bounds(net_file)

    if bounds:
        print(f"\nUse these bounds for cropping in config.yaml:")
        print(f"  min_x: {bounds['min_x']:.2f}")
        print(f"  max_x: {bounds['max_x']:.2f}")
        print(f"  min_y: {bounds['min_y']:.2f}")
        print(f"  max_y: {bounds['max_y']:.2f}")
