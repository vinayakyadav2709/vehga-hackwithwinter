
import os
import sys
import subprocess
import time
import traci
import traci.constants as tc
# Simplified setup
SUMO_PORT = 9991
PROJECT_DIR = os.path.expanduser("~/Workspace/vegha/FDRL_deep_sets")
CONFIG_FILE = "complex.sumocfg"

REQUIRED_LANE_VARS = [
    tc.LAST_STEP_VEHICLE_HALTING_NUMBER,
    tc.VAR_WAITING_TIME,
    tc.LAST_STEP_VEHICLE_NUMBER,
    tc.LAST_STEP_MEAN_SPEED,
    tc.LAST_STEP_OCCUPANCY
]

def run_test():
    # Start SUMO in Docker
    print("Starting SUMO in Docker...")
    docker_image = "ghcr.io/eclipse-sumo/sumo:latest"
    cmd = [
        "docker", "run", "--rm",
        "--network=host",
        "-v", f"{PROJECT_DIR}:/sumo-projs",
        docker_image,
        "sumo",
        "-c", f"/sumo-projs/{CONFIG_FILE}",
        "--remote-port", str(SUMO_PORT),
        "--no-step-log", "true",
        "--random"
    ]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5) # Wait longer for docker
    
    try:
        traci.init(port=SUMO_PORT, host="localhost")
        
        # Get a lane
        lanes = traci.lane.getIDList()
        test_lane = lanes[0]
        print(f"Testing subscription on lane: {test_lane}")
        
        # Subscribe
        traci.lane.subscribe(test_lane, REQUIRED_LANE_VARS)
        print("Subscribed.")
        
        # Step
        traci.simulationStep()
        
        # Check results
        res = traci.lane.getSubscriptionResults(test_lane)
        print(f"Results after step 1: {res}")
        
        if not res:
            print("FAILURE: Subscription returned empty!")
        else:
            print("SUCCESS: Subscription returned data.")
            
        # RELOAD
        print("\nReloading simulation...")
        traci.load(["-c", os.path.join(PROJECT_DIR, CONFIG_FILE)])
        
        # Step
        traci.simulationStep()
        
        # Check results again
        res_after_reload = traci.lane.getSubscriptionResults(test_lane)
        print(f"Results after reload: {res_after_reload}")
        
        if not res_after_reload:
            print("FAILURE: Subscription LOST after reload!")
        else:
            print("SUCCESS: Subscription persisted.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        traci.close()
        proc.kill()

if __name__ == "__main__":
    run_test()
