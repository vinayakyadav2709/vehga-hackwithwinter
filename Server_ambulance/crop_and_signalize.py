#!/usr/bin/env python3
"""
Unified Crop + Advanced TLS Script.
1. Crops the network (fixing the netconvert flags).
2. Applies your custom sumolib logic to detect and clean traffic lights.
"""

import os
import sys
import math
import shutil
import subprocess
import tempfile
import gzip
import xml.etree.ElementTree as ET
from collections import defaultdict

# Try to import sumolib
try:
    import sumolib
except ImportError:
    print("❌ Error: 'sumolib' not found.")
    print("   Run: uv pip install sumolib --python ../.venv")
    sys.exit(1)

# ================= CONFIG =================
MERGE_DIST_M = 25.0
MIN_INCOMING = 3
CROSS_THRESH = 0.3
# =========================================


def run_cmd(cmd):
    print("▶", " ".join(cmd))
    subprocess.run(cmd, check=True)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def is_geometry_node(n):
    return len(n.getIncoming()) == 1 and len(n.getOutgoing()) == 1


def is_vehicle_edge(edge):
    """Returns True if edge has at least one lane usable by motor vehicles."""
    for lane in edge.getLanes():
        try:
            perms = lane.getPermissions()
        except Exception:
            return True  # Fallback
        if not perms:
            return True  # Allow all
        if any(v in perms for v in ("passenger", "bus", "truck", "taxi", "emergency")):
            return True
    return False


def has_conflict(node):
    incoming = node.getIncoming()
    if len(incoming) < MIN_INCOMING:
        return False

    dirs = []
    edge_ids = set()

    for e in incoming:
        edge_ids.add(e.getID())
        s = e.getShape()
        if len(s) < 2:
            continue
        x1, y1 = s[-2]
        x2, y2 = s[-1]
        dx, dy = x2 - x1, y2 - y1
        l = math.hypot(dx, dy)
        if l > 0:
            dirs.append((dx / l, dy / l))

    if len(edge_ids) < len(incoming):
        return False  # Geometry split

    distinct = []
    for d in dirs:
        if not any(abs(d[0] * o[1] - d[1] * o[0]) < CROSS_THRESH for o in distinct):
            distinct.append(d)

    if len(distinct) < 2:
        return False

    # Check angles
    angles = []
    for i in range(len(distinct)):
        for j in range(i + 1, len(distinct)):
            dot = distinct[i][0] * distinct[j][0] + distinct[i][1] * distinct[j][1]
            angle = abs(math.degrees(math.acos(max(-1, min(1, dot)))))
            angles.append(angle)

    if not angles or max(angles) < 60:
        return False

    # Must have at least one meaningful crossing
    for i in range(len(distinct)):
        for j in range(i + 1, len(distinct)):
            dot = distinct[i][0] * distinct[j][0] + distinct[i][1] * distinct[j][1]
            angle = abs(math.degrees(math.acos(max(-1, min(1, dot)))))
            if angle >= 45:
                return True

    return False


def is_green_phase(state):
    s = state.lower()
    return "g" in s and "y" not in s


def crop_and_signalize(input_file, output_file, min_x, max_x, min_y, max_y):
    # Create temp files
    fd, temp_cropped = tempfile.mkstemp(suffix=".net.xml")
    os.close(fd)
    fd, temp_tls = tempfile.mkstemp(suffix=".net.xml")
    os.close(fd)

    try:
        # --------------------------------------------------
        # STEP 1: CROP NETWORK (Geometry Only)
        # --------------------------------------------------
        print(f"\n✂️  Cropping network to {min_x},{min_y} - {max_x},{max_y}")

        # FIXED: Removed '--keep-edges.in-boundary.keep-via' which caused your error
        cmd_crop = [
            "netconvert",
            "--sumo-net-file",
            input_file,
            "--output-file",
            temp_cropped,
            "--keep-edges.in-boundary",
            f"{min_x},{min_y},{max_x},{max_y}",
            "--tls.discard-loaded",
            "true",  # Remove existing TLS to start fresh
            "--no-turnarounds",
            "true",
            "--ignore-errors",
            "true",
            "--xml-validation",
            "never",
        ]
        run_cmd(cmd_crop)

        # Check if crop worked
        if os.path.getsize(temp_cropped) < 1000:
            print("\n❌ ERROR: Cropped network is empty! Check your coordinates.")
            sys.exit(1)

        # --------------------------------------------------
        # STEP 2: ANALYZE WITH SUMOLIB (Your Custom Logic)
        # --------------------------------------------------
        print("\n🧠 Running Custom TLS detection logic...")
        net = sumolib.net.readNet(temp_cropped)
        nodes = net.getNodes()

        # Cluster
        clusters = []
        visited = set()
        for n in nodes:
            if n.getID() in visited:
                continue
            cluster = [n]
            visited.add(n.getID())
            for m in nodes:
                if m.getID() in visited:
                    continue
                if dist(n.getCoord(), m.getCoord()) <= MERGE_DIST_M:
                    cluster.append(m)
                    visited.add(m.getID())
            clusters.append(cluster)

        # Select TLS Nodes
        tls_nodes = []
        for cluster in clusters:
            for n in cluster:
                if is_geometry_node(n):
                    continue
                veh_incoming = [e for e in n.getIncoming() if is_vehicle_edge(e)]
                if len(veh_incoming) < MIN_INCOMING:
                    continue
                if has_conflict(n):
                    tls_nodes.append(n.getID())
                    break

        print(f"🚦 Selected {len(tls_nodes)} junctions for Traffic Lights")

        if not tls_nodes:
            print("⚠️  No complex junctions found. Saving simple network.")
            shutil.copy(temp_cropped, output_file)
            return

        # --------------------------------------------------
        # STEP 3: APPLY TLS
        # --------------------------------------------------
        print("\n🚥 Applying TLS configuration...")
        run_cmd(
            [
                "netconvert",
                "--sumo-net-file",
                temp_cropped,
                "--output-file",
                temp_tls,
                "--tls.set",
                ",".join(tls_nodes),
                "--tls.default-type",
                "actuated",
                "--tls.yellow.time",
                "3",
                "--no-turnarounds",
                "true",
            ]
        )

        # --------------------------------------------------
        # STEP 4: CLEAN XML (Remove bad programs)
        # --------------------------------------------------
        print("\n🔍 Cleaning invalid TLS programs...")
        tree = ET.parse(temp_tls)
        root = tree.getroot()

        tls_incoming = defaultdict(set)
        for c in root.findall("connection"):
            tl = c.get("tl")
            if tl:
                tls_incoming[tl].add(c.get("from"))

        bad = set()
        for tlLogic in root.findall("tlLogic"):
            tid = tlLogic.get("id")
            # Filter 1: Not enough incoming edges
            if len(tls_incoming.get(tid, [])) <= 1:
                bad.add(tid)
                continue
            # Filter 2: Not enough green phases
            greens = sum(
                1
                for p in tlLogic.findall("phase")
                if is_green_phase(p.get("state", ""))
            )
            if greens <= 1:
                bad.add(tid)

        print(f"🚫 Removing {len(bad)} invalid TLS programs")

        # Remove bad tlLogic elements
        for tlLogic in list(root.findall("tlLogic")):
            if tlLogic.get("id") in bad:
                root.remove(tlLogic)

        # Downgrade junctions to priority
        for j in root.findall("junction"):
            if j.get("type") == "traffic_light" and j.get("id") in bad:
                j.set("type", "priority")

        # Remove attributes from connections
        for conn in root.findall("connection"):
            tl = conn.get("tl")
            if tl in bad:
                del conn.attrib["tl"]
                if "linkIndex" in conn.attrib:
                    del conn.attrib["linkIndex"]

        # --------------------------------------------------
        # STEP 5: WRITE FINAL OUTPUT
        # --------------------------------------------------
        print(f"\n💾 Writing final network to {output_file}")

        # Handle .gz output if requested
        if output_file.endswith(".gz"):
            with gzip.open(output_file, "wt", encoding="utf-8") as f:
                tree.write(f, encoding="unicode", xml_declaration=True)
        else:
            tree.write(output_file, encoding="utf-8", xml_declaration=True)

        print("✅ Done.")

    finally:
        # Cleanup temp files
        if os.path.exists(temp_cropped):
            os.remove(temp_cropped)
        if os.path.exists(temp_tls):
            os.remove(temp_tls)


if __name__ == "__main__":
    if len(sys.argv) < 7:
        print(
            "Usage: python crop_and_signalize.py <input> <output> <min_x> <max_x> <min_y> <max_y>"
        )
        sys.exit(1)

    crop_and_signalize(
        sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
    )
