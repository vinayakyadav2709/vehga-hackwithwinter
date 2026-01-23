#!/bin/bash
# Workflow to create a new cropped SUMO scenario

set -e  # Exit on error

echo "=== SUMO Scenario Cropping Workflow ==="
echo

# Step 1: Get bounds from existing network
echo "Step 1: Extract bounds from coldplay2 network..."
python3 get_bounds.py coldplay2/osm.net.xml

echo
echo "Based on the bounds above, choose your crop area and run:"
echo
echo "Example for smaller area:"
echo "  bash crop_scenario.sh coldplay3 8000 8500 5000 5500 50"
echo
echo "Arguments:"
echo "  \$1 = output_dir (e.g., 'coldplay3')"
echo "  \$2 = min_x"
echo "  \$3 = max_x"
echo "  \$4 = min_y"
echo "  \$5 = max_y"
echo "  \$6 = num_vehicles (optional, default=50)"
