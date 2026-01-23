#!/bin/bash
set -e

OUTPUT_DIR="${1:-coldplay3}"
MIN_X="${2:-200}"
MAX_X="${3:-400}"
MIN_Y="${4:-1350}"
MAX_Y="${5:-1550}"
NUM_VEHICLES="${6:-50}"

echo "=== Creating Scenario with Custom TLS Logic ==="
mkdir -p "$OUTPUT_DIR"

# Step 1: Crop and Signalize
echo "Step 1: Cropping and Signalizing..."
if [ -f "coldplay2/osm.net.xml.gz" ]; then
    python3 crop_and_signalize.py coldplay2/osm.net.xml.gz "$OUTPUT_DIR/osm.net.xml" $MIN_X $MAX_X $MIN_Y $MAX_Y
elif [ -f "coldplay2/osm.net.xml" ]; then
    python3 crop_and_signalize.py coldplay2/osm.net.xml "$OUTPUT_DIR/osm.net.xml" $MIN_X $MAX_X $MIN_Y $MAX_Y
else
    echo "Error: Input network not found"
    exit 1
fi

# Step 2: Generate Routes (Using the robust version)
echo "Step 2: Generating routes..."
python3 generate_routes.py "$OUTPUT_DIR/osm.net.xml" "$OUTPUT_DIR/osm.rou.xml" $NUM_VEHICLES 15

# Step 3: GUI Settings
cat > "$OUTPUT_DIR/gui-settings.cfg" << 'EOF'
<viewsettings>
    <scheme name="standard">
        <opengl>true</opengl>
        <vehicles vehicleMode="0" vehicleQuality="2" vehicleMinSize="1.00" vehicleExaggeration="1.00" vehicleValue="0" vehicleName="0" vehicleIpad="0" vehicleTextSize="80.00"/>
    </scheme>
    <delay value="100"/>
</viewsettings>
EOF

# Step 4: SUMO Config
cat > "$OUTPUT_DIR/osm.sumocfg" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="osm.net.xml"/>
        <route-files value="osm.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
    <gui_only>
        <gui-settings-file value="gui-settings.cfg"/>
    </gui_only>
</configuration>
EOF

echo "=== Done! ==="
echo "Run: sumo-gui -c $OUTPUT_DIR/osm.sumocfg"