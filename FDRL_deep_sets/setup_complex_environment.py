#!/usr/bin/env python3
"""
SUMO Network and Traffic Setup
Generates network, routes with emergency vehicles, and configurations for all modes.
"""
import os
import subprocess
import xml.etree.ElementTree as ET
import random

# CONFIGURATION
DOCKER_IMAGE = "ghcr.io/eclipse-sumo/sumo:latest"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
EMERGENCY_RATIO = 0.05  # 5% emergency vehicles
SIMULATION_DURATION = 3600
VEHICLE_PERIOD = 2.0

def run_in_docker(cmd_args):
    """Execute SUMO tools in Docker."""
    docker_cmd = ["docker", "run", "--rm", "-v", f"{PROJECT_DIR}:/sumo-projs", 
                  "-w", "/sumo-projs", DOCKER_IMAGE] + cmd_args
    result = subprocess.run(docker_cmd, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(f"Warning: {result.stderr}")
    return result

# NETWORK TOPOLOGY
NODES_XML = """<nodes>
    <node id="C" x="0" y="0" type="traffic_light"/>
    <node id="N" x="0" y="400" type="traffic_light"/>
    <node id="S" x="0" y="-400" type="traffic_light"/>
    <node id="E" x="400" y="0" type="traffic_light"/>
    <node id="W" x="-400" y="0" type="traffic_light"/>
    <node id="X_NE" x="200" y="200" type="traffic_light"/>
    <node id="NE" x="350" y="350" type="traffic_light"/>
    <node id="Exit_N" x="0" y="800"/>
    <node id="Exit_S" x="0" y="-800"/>
    <node id="Exit_E" x="800" y="0"/>
    <node id="Exit_W" x="-800" y="0"/>
    <node id="Exit_NE" x="600" y="600"/>
</nodes>"""

EDGES_XML = """<edges>
    <edge id="N2C" from="N" to="C" priority="3" numLanes="1" speed="13.89"/>
    <edge id="C2N" from="C" to="N" priority="3" numLanes="1" speed="13.89"/>
    <edge id="S2C" from="S" to="C" priority="3" numLanes="1" speed="13.89"/>
    <edge id="C2S" from="C" to="S" priority="3" numLanes="1" speed="13.89"/>
    <edge id="E2C" from="E" to="C" priority="3" numLanes="1" speed="13.89"/>
    <edge id="C2E" from="C" to="E" priority="3" numLanes="1" speed="13.89"/>
    <edge id="W2C" from="W" to="C" priority="3" numLanes="1" speed="13.89"/>
    <edge id="C2W" from="C" to="W" priority="3" numLanes="1" speed="13.89"/>
    <edge id="C2X" from="C" to="X_NE" priority="3" numLanes="1" speed="13.89"/>
    <edge id="X2C" from="X_NE" to="C" priority="3" numLanes="1" speed="13.89"/>
    <edge id="X2NE" from="X_NE" to="NE" priority="2" numLanes="1" speed="13.89"/>
    <edge id="NE2X" from="NE" to="X_NE" priority="2" numLanes="1" speed="13.89"/>
    <edge id="N2X" from="N" to="X_NE" priority="2" numLanes="1" speed="13.89"/>
    <edge id="X2N" from="X_NE" to="N" priority="2" numLanes="1" speed="13.89"/>
    <edge id="E2X" from="E" to="X_NE" priority="2" numLanes="1" speed="13.89"/>
    <edge id="X2E" from="X_NE" to="E" priority="2" numLanes="1" speed="13.89"/>
    <edge id="N2E" from="N" to="E" priority="2" numLanes="1" speed="13.89"/>
    <edge id="E2N" from="E" to="N" priority="2" numLanes="1" speed="13.89"/>
    <edge id="N2W" from="N" to="W" priority="2" numLanes="1" speed="13.89"/>
    <edge id="W2N" from="W" to="N" priority="2" numLanes="1" speed="13.89"/>
    <edge id="S2E" from="S" to="E" priority="2" numLanes="1" speed="13.89"/>
    <edge id="E2S" from="E" to="S" priority="2" numLanes="1" speed="13.89"/>
    <edge id="S2W" from="S" to="W" priority="2" numLanes="1" speed="13.89"/>
    <edge id="W2S" from="W" to="S" priority="2" numLanes="1" speed="13.89"/>
    <edge id="E2W" from="E" to="W" priority="2" numLanes="1" speed="13.89"/>
    <edge id="W2E" from="W" to="E" priority="2" numLanes="1" speed="13.89"/>
    <edge id="In_N" from="Exit_N" to="N" priority="1" numLanes="1" speed="13.89"/>
    <edge id="In_S" from="Exit_S" to="S" priority="1" numLanes="1" speed="13.89"/>
    <edge id="In_E" from="Exit_E" to="E" priority="1" numLanes="1" speed="13.89"/>
    <edge id="In_W" from="Exit_W" to="W" priority="1" numLanes="1" speed="13.89"/>
    <edge id="In_NE" from="Exit_NE" to="NE" priority="1" numLanes="1" speed="13.89"/>
    <edge id="Out_N" from="N" to="Exit_N" priority="1" numLanes="1" speed="13.89"/>
    <edge id="Out_S" from="S" to="Exit_S" priority="1" numLanes="1" speed="13.89"/>
    <edge id="Out_E" from="E" to="Exit_E" priority="1" numLanes="1" speed="13.89"/>
    <edge id="Out_W" from="W" to="Exit_W" priority="1" numLanes="1" speed="13.89"/>
    <edge id="Out_NE" from="NE" to="Exit_NE" priority="1" numLanes="1" speed="13.89"/>
</edges>"""

print(">> Generating Network Files...")
with open(os.path.join(PROJECT_DIR, "network.nod.xml"), "w") as f:
    f.write(NODES_XML)
with open(os.path.join(PROJECT_DIR, "network.edg.xml"), "w") as f:
    f.write(EDGES_XML)

# Generate base network (FDRL - manual control)
run_in_docker(["netconvert", "-n", "network.nod.xml", "-e", "network.edg.xml", "-o", "network.net.xml"])
print("✓ Base network (FDRL)")

# Generate actuated network
run_in_docker(["netconvert", "-n", "network.nod.xml", "-e", "network.edg.xml", 
               "-o", "network_actuated.net.xml", "--tls.default-type", "actuated"])
print("✓ Actuated network")

# Generate fixed-time network
run_in_docker(["netconvert", "-n", "network.nod.xml", "-e", "network.edg.xml",
               "-o", "network_fixed.net.xml", "--tls.default-type", "static", "--tls.cycle.time", "90"])
print("✓ Fixed-time network")

# Generate routes with emergency vehicles
print(f">> Generating Routes ({EMERGENCY_RATIO*100:.0f}% emergency)...")
temp_file = "temp_routes.xml"
run_in_docker(["python", "/usr/share/sumo/tools/randomTrips.py", "-n", "network.net.xml",
               "-o", temp_file, "-e", str(SIMULATION_DURATION), "-p", str(VEHICLE_PERIOD),
               "--validate", "--fringe-factor", "50"])

tree = ET.parse(os.path.join(PROJECT_DIR, temp_file))
root = tree.getroot()
new_root = ET.Element('routes')
new_root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
new_root.set('xsi:noNamespaceSchemaLocation', 'http://sumo.dlr.de/xsd/routes_file.xsd')

# Vehicle types
vtype_car = ET.SubElement(new_root, 'vType')
vtype_car.set('id', 'car')
vtype_car.set('vClass', 'passenger')
vtype_car.set('speedFactor', '1.0')
vtype_car.set('color', '1,1,0')

vtype_emg = ET.SubElement(new_root, 'vType')
vtype_emg.set('id', 'emergency')
vtype_emg.set('vClass', 'emergency')
vtype_emg.set('speedFactor', '1.3')
vtype_emg.set('color', '1,0,0')
vtype_emg.set('guiShape', 'emergency')

emg_count, total = 0, 0
for trip in root.findall('trip'):
    total += 1
    trip.set('type', 'emergency' if random.random() < EMERGENCY_RATIO else 'car')
    if trip.get('type') == 'emergency':
        emg_count += 1
    new_root.append(trip)

temp_typed = "temp_trips_typed.xml"
ET.ElementTree(new_root).write(os.path.join(PROJECT_DIR, temp_typed), encoding='UTF-8', xml_declaration=True)

run_in_docker(["duarouter", "-n", "network.net.xml", "-t", temp_typed, 
               "-o", "traffic.rou.xml", "--ignore-errors", "--no-warnings"])

os.remove(os.path.join(PROJECT_DIR, temp_file))
os.remove(os.path.join(PROJECT_DIR, temp_typed))
print(f"✓ Routes: {total} vehicles ({emg_count} emergency, {total-emg_count} normal)")

# Generate config files
configs = {
    'fdrl.sumocfg': 'network.net.xml',
    'actuated.sumocfg': 'network_actuated.net.xml',
    'fixed.sumocfg': 'network_fixed.net.xml'
}

for cfg_name, net_file in configs.items():
    cfg_content = f"""<configuration>
    <input>
        <net-file value="{net_file}"/>
        <route-files value="traffic.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{SIMULATION_DURATION}"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
        <ignore-junction-blocker value="1"/>
    </processing>
</configuration>"""
    with open(os.path.join(PROJECT_DIR, cfg_name), "w") as f:
        f.write(cfg_content)
    print(f"✓ {cfg_name}")

print("\n>> Setup Complete!")
print(f"Emergency ratio: {emg_count/total*100:.1f}%")
print("Run: uv run python main.py --mode train --episodes 10 --no-gui")
