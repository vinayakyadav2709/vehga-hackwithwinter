import os
import subprocess
import time
import traci
import numpy as np


def start_sumo_docker(project_dir, config_file, port=9999, gui=True):
    """Launches SUMO container. Returns subprocess object."""
    docker_image = "ghcr.io/eclipse-sumo/sumo:latest"
    binary = "sumo-gui" if gui else "sumo"

    print(f">> Launching SUMO ({binary}) in Docker...")

    cmd = [
        "docker",
        "run",
        "--rm",
        # --network=host shares port of container and host
        "--network=host",
        # Below 2 lines map the host port to container port, but there is some issue hence we are using --network=host
        # "-p",
        # f"{SUMO_PORT}:{SUMO_PORT}",
        "-e", f"DISPLAY={os.environ.get('DISPLAY', '')}",
        "-v", "/tmp/.X11-unix:/tmp/.X11-unix:rw",
        "-v", f"{os.environ.get('XAUTHORITY', '')}:/root/.Xauthority:rw",
        "-v", f"{project_dir}:/sumo-projs",
        "-it",
        docker_image,
        binary,  
        "-c",
        f"/sumo-projs/{config_file}",
        "--remote-port",
        str(port),
        "--start",
        "--quit-on-end",
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(">> Waiting 3s for SUMO initialization...")
    time.sleep(3)
    return process


def get_controlled_lanes(tls_id):
    """
    Returns Dictionary: { 'EdgeID': ['LaneID_1', 'LaneID_2', ...] }
    Only lanes controlled by this traffic light.
    """
    links = traci.trafficlight.getControlledLinks(tls_id)
    edge_lanes_map = {}

    for link_group in links:
        if not link_group:
            continue

        incoming_lane = link_group[0][0]
        edge_id = traci.lane.getEdgeID(incoming_lane)

        if edge_id not in edge_lanes_map:
            edge_lanes_map[edge_id] = set()
        edge_lanes_map[edge_id].add(incoming_lane)

    # Convert to sorted lists
    for edge in edge_lanes_map:
        edge_lanes_map[edge] = sorted(list(edge_lanes_map[edge]))

    return edge_lanes_map


class Normalizer:
    """Normalizes traffic features to [0, 1] range using Logarithmic Scaling."""

    def __init__(self):
        # We use log(x+1) / log(max+1) to squash large values while keeping sensitivity for small ones.
        self.max_queue = 100.0   # Soft max for linear, but we use log
        self.max_wait = 10000.0  # Increased significanty to prevent saturation
        self.max_speed = 30.0    
        self.max_vol = 50.0
        self.max_emergency_count = 5.0
        self.max_emergency_wait = 500.0  # Emergency vehicles should wait less

    def scale(self, features):
        queue, wait, speed, vol, occ, emg_count, emg_wait, has_emg = features
        
        # Log scaling helper
        def log_scale(val, max_val):
            return np.log(val + 1) / np.log(max_val + 1)

        return [
            min(log_scale(queue, self.max_queue), 1.0),
            min(log_scale(wait, self.max_wait), 1.0),
            min(speed / self.max_speed, 1.0), # Speed is naturally bounded
            min(log_scale(vol, self.max_vol), 1.0),
            occ,
            min(log_scale(emg_count, self.max_emergency_count), 1.0),
            min(log_scale(emg_wait, self.max_emergency_wait), 1.0),
            has_emg,  # Already 0 or 1
        ]


import traci.constants as tc

REQUIRED_LANE_VARS = [
    tc.LAST_STEP_VEHICLE_HALTING_NUMBER,
    tc.VAR_WAITING_TIME,
    tc.LAST_STEP_VEHICLE_NUMBER,
    tc.LAST_STEP_MEAN_SPEED,
    tc.LAST_STEP_OCCUPANCY
]

def subscribe_lanes(lane_ids):
    """Subscribes to required variables for a list of lanes."""
    for lane_id in lane_ids:
        try:
             traci.lane.subscribe(lane_id, REQUIRED_LANE_VARS)
        except traci.exceptions.TraCIException as e:
             print(f"Warning: Could not subscribe to lane {lane_id}: {e}")
    # print(f"DEBUG: Subscribed to {len(lane_ids)} lanes.")

def get_emergency_features(lane_ids):
    """
    Detect emergency vehicles on given lanes.
    Returns: (emergency_count, emergency_wait_time, has_emergency)
    """
    emergency_count = 0
    emergency_wait = 0.0
    
    for lane_id in lane_ids:
        try:
            vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
            for veh_id in vehicles:
                try:
                    vtype = traci.vehicle.getTypeID(veh_id)
                    if vtype == "emergency":
                        emergency_count += 1
                        emergency_wait += traci.vehicle.getAccumulatedWaitingTime(veh_id)
                except traci.exceptions.TraCIException:
                    continue
        except traci.exceptions.TraCIException:
            continue
    
    has_emergency = 1.0 if emergency_count > 0 else 0.0
    return emergency_count, emergency_wait, has_emergency


def get_aggregated_features(lane_ids, normalizer=None):
    """
    Aggregates metrics for a list of lanes.
    Uses subscription results if available, falls back to direct calls.
    """
    total_queue = 0
    total_wait = 0
    total_vol = 0
    avg_speed = 0
    avg_occ = 0
    count = 0

    for lane_id in lane_ids:
        try:
            # Try getting subscription results first
            subs = traci.lane.getSubscriptionResults(lane_id)
            
            if subs:
                queue = subs[tc.LAST_STEP_VEHICLE_HALTING_NUMBER]
                wait = subs[tc.VAR_WAITING_TIME]
                vol = subs[tc.LAST_STEP_VEHICLE_NUMBER]
                speed = subs[tc.LAST_STEP_MEAN_SPEED]
                occ = subs[tc.LAST_STEP_OCCUPANCY]
            else:
                # Fallback to individual calls
                # Debugging why subscription fails
                # print(f"DEBUG: Subscription logic check. Lane: {lane_id}, Result: {subs}")
                print(f"Warning: Subscription results not available for lane {lane_id}")
                queue = traci.lane.getLastStepHaltingNumber(lane_id)
                wait = traci.lane.getWaitingTime(lane_id)
                vol = traci.lane.getLastStepVehicleNumber(lane_id)
                speed = traci.lane.getLastStepMeanSpeed(lane_id)
                occ = traci.lane.getLastStepOccupancy(lane_id)

            total_queue += queue
            total_wait += wait
            total_vol += vol
            avg_speed += speed
            avg_occ += occ
            count += 1
            
        except traci.exceptions.TraCIException:
            continue

    if count > 0:
        avg_speed /= count
        avg_occ /= count

    # Add emergency features
    emg_count, emg_wait, has_emg = get_emergency_features(lane_ids)
    
    raw = [total_queue, total_wait, avg_speed, total_vol, avg_occ, emg_count, emg_wait, has_emg]

    if normalizer:
        return normalizer.scale(raw)
    return raw



def compute_reward(lane_ids, normalizer):
    """
    Encourages maintaining flow, not just clearing stopped cars.
    Emergency vehicles are heavily prioritized with 10x penalty.
    """
    stats = get_aggregated_features(lane_ids, normalizer)
    # stats = [queue, wait, speed, vol, occ, emg_count, emg_wait, has_emg] (normalized)
    
    # Heuristic weights for reward shaping
    r_queue = -1.0 * stats[0]
    r_wait = -1.0 * stats[1]
    
    # CRITICAL: Emergency vehicle penalty (10x normal)
    # This heavily incentivizes the agent to clear emergency vehicles quickly
    r_emergency_wait = -10.0 * stats[6]
    
    return r_queue + r_wait + r_emergency_wait
