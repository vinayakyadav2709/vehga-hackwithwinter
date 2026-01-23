#!/usr/bin/env python3
"""
Generate Traffic Jam with LEFT-SIDE BIAS.
1. Identifies edges on the left side of the map.
2. Forces 70% of traffic to start on the left side.
3. Spawns a massive 1000+ vehicle wave.
"""

import sumolib
import random
import sys

# --- CONFIGURATION ---
SPECIFIC_START_EDGE = "-1154579502"
SPECIFIC_END_EDGE = "-215089904#5"

# Timing
SPECIAL_DEPART = 40  # Bus starts at 40s
JAM_END_TIME = 150  # Traffic continues until 150s
# ---------------------


def generate_routes(net_file, out_file, total_cars):
    print(f"Loading network {net_file}...")

    try:
        net = sumolib.net.readNet(net_file)
    except Exception as e:
        print(f"Error reading network: {e}")
        sys.exit(1)

    # Get all valid edges
    all_edges = [e for e in net.getEdges() if e.allows("passenger")]

    if len(all_edges) < 2:
        print("❌ Error: Network too small.")
        sys.exit(1)

    # ---------------------------------------------------------
    # 1. SPATIAL ANALYSIS (Find Left Side)
    # ---------------------------------------------------------
    # Sort edges by the X-coordinate of their starting node
    all_edges.sort(key=lambda e: e.getFromNode().getCoord()[0])

    # Define "Left Side" as the first 50% of edges (sorted by X)
    mid_point = len(all_edges) // 2
    left_edges = all_edges[:mid_point]

    print(f"Map Analysis:")
    print(f"  - Total Edges: {len(all_edges)}")
    print(f"  - Left-Side Edges: {len(left_edges)}")
    print(f"  - Strategy: Biasing 70% of traffic to start on the Left Side.")

    all_trips = []

    # ---------------------------------------------------------
    # 2. GENERATE SPECIAL ROUTE
    # ---------------------------------------------------------
    special_trip = None
    if net.hasEdge(SPECIFIC_START_EDGE) and net.hasEdge(SPECIFIC_END_EDGE):
        start_e = net.getEdge(SPECIFIC_START_EDGE)
        end_e = net.getEdge(SPECIFIC_END_EDGE)
        if net.getShortestPath(start_e, end_e):
            special_trip = {
                "id": "special",
                "type": "special",
                "depart": SPECIAL_DEPART,
                "from": SPECIFIC_START_EDGE,
                "to": SPECIFIC_END_EDGE,
            }
            print(
                f"✓ Special Route Confirmed: {SPECIFIC_START_EDGE} -> {SPECIFIC_END_EDGE}"
            )
        else:
            print("❌ Special Route Disconnected.")
    else:
        print("❌ Special Route Edges not found.")

    # ---------------------------------------------------------
    # 3. GENERATE BIASED BACKGROUND TRAFFIC
    # ---------------------------------------------------------
    print(f"Generating {total_cars} vehicles...")

    generated = 0
    attempts = 0

    while generated < total_cars and attempts < (total_cars * 50):
        attempts += 1

        # BIAS LOGIC: 70% chance to pick a start node from the LEFT side
        if random.random() < 0.7:
            start = random.choice(left_edges)
        else:
            start = random.choice(all_edges)

        end = random.choice(all_edges)

        if start == end:
            continue

        # Check path
        try:
            if not net.getShortestPath(start, end):
                continue
        except:
            continue

        # TIMING LOGIC: Flood early (0-40s) to block the bus
        if random.random() < 0.6:
            depart = random.randint(0, SPECIAL_DEPART)
        else:
            depart = random.randint(SPECIAL_DEPART, JAM_END_TIME)

        all_trips.append(
            {
                "id": f"veh{generated}",
                "type": "car",
                "depart": int(depart),
                "from": start.getID(),
                "to": end.getID(),
            }
        )
        generated += 1

    # ---------------------------------------------------------
    # 4. ADD SPECIAL & SORT
    # ---------------------------------------------------------
    if special_trip:
        all_trips.append(special_trip)

    all_trips.sort(key=lambda x: (x["depart"], x["id"]))

    # ---------------------------------------------------------
    # 5. WRITE OUTPUT
    # ---------------------------------------------------------
    with open(out_file, "w") as f:
        f.write("<routes>\n")
        f.write(
            '    <vType id="car" accel="2.6" decel="4.5" length="5.0" maxSpeed="50" color="200,200,200"/>\n'
        )
        f.write(
            '    <vType id="special" accel="1.2" decel="3.5" length="7.0" maxSpeed="40" color="255,0,0" guiShape="bus"/>\n'
        )

        for trip in all_trips:
            f.write(
                f'    <trip id="{trip["id"]}" type="{trip["type"]}" depart="{trip["depart"]}" from="{trip["from"]}" to="{trip["to"]}"/>\n'
            )

        f.write("</routes>\n")

    print(f"✓ Wrote {len(all_trips)} sorted routes to {out_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_routes.py <net_file> <out_file> [count]")
        sys.exit(1)

    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    generate_routes(sys.argv[1], sys.argv[2], count)
