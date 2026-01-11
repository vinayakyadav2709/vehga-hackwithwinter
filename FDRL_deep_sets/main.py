import os
import sys
import argparse
import traci
import utils
import junction
import fdrl_server
import models


SUMO_PORT = 9999
PROJECT_DIR = os.path.expanduser("~/Workspace/vegha/FDRL_deep_sets")
CONFIG_FILE = "complex.sumocfg"

AGGREGATION_INTERVAL = 500
LOCAL_WEIGHT_RETENTION = 0.5  # Balanced local/global learning
SAVE_PATH = "global_model.pth"


def parse_args():
    parser = argparse.ArgumentParser(description="FDRL Traffic Management System")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["train", "test", "actuated", "fixed_time"],
        default="train",
        help="'train' from scratch/pretrained or 'test' with frozen weights",
    )
    parser.add_argument(
        "--load", type=str, default=None, help="Path to pretrained model (optional)"
    )
    parser.add_argument(
        "--episodes", type=int, default=1, help="Number of simulation episodes"
    )
    parser.add_argument(
        "--no-gui", action="store_true", help="Run SUMO in headless mode (no GUI)"
    )
    return parser.parse_args()


def run_simulation(args, server, agents, episode_num):
    """Main simulation loop with FL aggregation."""
    step = 0
    aggregation_count = 0
    train_mode = args.mode == "train"

    print(f"\n>> Episode {episode_num + 1}/{args.episodes} (Mode: {args.mode})...")
    
    # Print Table Header
    header = f"{'Step':<8} | {'Total Wait':<12} | {'Avg Wait':<10} | {'Avg Speed':<10} | {'Queue':<8}"
    if train_mode:
        header += f" | {'Epsilon':<8}"
    print(header)
    print("-" * len(header))

    # Track Episode Stats for Final Summary
    episode_stats = {
        "wait": [],
        "avg_wait": [],
        "speed": [],
        "queue": []
    }

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        current_time = traci.simulation.getTime()

        # Skip first few steps to let simulation stabilize
        if step < 10:
            step += 1
            continue

        # Local Agent Updates
        for agent in agents.values():
            agent.step(current_time, train=train_mode)

        # Federated Aggregation (Only in training mode)
        if train_mode and step > 0 and step % AGGREGATION_INTERVAL == 0:
            print() # Blank line
            print(f"[Step {step}] >> Aggregation Round {aggregation_count + 1}...", flush=True)

            client_weights = [
                agent.get_weights() for agent in agents.values() if agent.get_weights()
            ]
            new_global_weights = server.aggregate(client_weights)

            for agent in agents.values():
                agent.update_weights(new_global_weights, alpha=LOCAL_WEIGHT_RETENTION)

            server.save_model(SAVE_PATH)
            aggregation_count += 1

        # Logging
        if step % 100 == 0:
            total_wait = 0
            total_queue = 0
            total_wait = 0
            total_speed = 0
            total_vol = 0
            active_agents = 0

            for agent in agents.values():
                # raw features: [queue, wait, speed, vol, occ]
                # We need raw values, so we pass None as normalizer
                raw_stats = utils.get_aggregated_features(agent.all_lanes, normalizer=None)
                total_queue += raw_stats[0]
                total_wait += raw_stats[1]
                total_speed += raw_stats[2]
                total_vol += raw_stats[3]
                active_agents += 1
            
            avg_system_speed = total_speed / max(1, active_agents)
            avg_wait_per_vehicle = total_wait / max(1, total_vol)

            # Store for end of episode
            episode_stats["wait"].append(total_wait)
            episode_stats["avg_wait"].append(avg_wait_per_vehicle)
            episode_stats["speed"].append(avg_system_speed)
            episode_stats["queue"].append(total_queue)

            epsilon = (
                agents[list(agents.keys())[0]].brain.epsilon if train_mode and hasattr(agents[list(agents.keys())[0]], 'brain') and agents[list(agents.keys())[0]].brain else 0.0
            )
            
            # Log Row
            row = f"\r{step:<8} | {total_wait:<12.1f} | {avg_wait_per_vehicle:<10.1f} | {avg_system_speed:<10.2f} | {total_queue:<8.0f}"
            if train_mode:
                row += f" | {epsilon:<8.3f}"
            
            print(row, flush=True)

        step += 1

    print(f"\n>> Episode {episode_num + 1} Finished.")
    
    # Print Final Summary
    print("\n" + "="*30)
    print(f"EPISODE {episode_num + 1} SUMMARY")
    print("="*30)
    if episode_stats["wait"]:
        # avg_wait_total = sum(episode_stats["wait"]) / len(episode_stats["wait"])
        avg_wait_per_veh = sum(episode_stats["avg_wait"]) / len(episode_stats["avg_wait"])
        avg_speed_total = sum(episode_stats["speed"]) / len(episode_stats["speed"])
        # avg_queue_total = sum(episode_stats["queue"]) / len(episode_stats["queue"])
        
        # print(f"Avg Total Wait : {avg_wait_total:.2f}")
        print(f"Avg Wait/Veh     : {avg_wait_per_veh:.2f}")
        print(f"Avg Speed/Veh    : {avg_speed_total:.2f}")
        # print(f"Avg Queue      : {avg_queue_total:.2f}")
    print("="*30 + "\n")


def main():
    args = parse_args()

    # Validate config
    if not os.path.exists(os.path.join(PROJECT_DIR, CONFIG_FILE)):
        print(f"Error: {CONFIG_FILE} not found. Run setup script first.")
        sys.exit(1)

    # Choose config based on mode
    current_config = "complex_actuated.sumocfg" if args.mode == "actuated" else CONFIG_FILE

    # Start SUMO
    # If no-gui is True, then gui=False
    use_gui = not args.no_gui
    proc = utils.start_sumo_docker(PROJECT_DIR, current_config, port=SUMO_PORT, gui=use_gui)

    try:
        traci.init(port=SUMO_PORT, host="localhost")

        # Initialize Server
        baseline_model = models.TrafficSignalScorer()
        server = fdrl_server.FDRLServer(baseline_model)

        # Load pretrained model if specified
        if args.load and os.path.exists(args.load):
            print(f">> Loading model from {args.load}...")
            server.load_model(args.load)
        elif args.mode == "test":
            print("Error: Test mode requires --load <model_path>")
            sys.exit(1)

        # Initialize Agents
        tls_ids = traci.trafficlight.getIDList() # gets all junctions/controllers
        print(f">> Discovered {len(tls_ids)} Junctions: {tls_ids}")

        global_weights = server.get_global_weights()
        agents = {}

        for tid in tls_ids:
            if args.mode == "actuated":
                agent = junction.ActuatedAgent(tid)
            elif args.mode == "fixed_time":
                agent = junction.FixedTimeAgent(tid)
            else:
                agent = junction.JunctionAgent(tid)
                if args.load:
                    agent.brain.set_weights(global_weights)
                if args.mode == "test":
                    agent.brain.epsilon = 0.0  # Disable exploration
            agents[tid] = agent

        # Run Episodes
        for ep in range(args.episodes):
            run_simulation(args, server, agents, ep)

            # Reset for next episode
            if ep < args.episodes - 1:
                traci.load(["-c", f"/sumo-projs/{current_config}"])
                for agent in agents.values():
                    agent.reset()

    except traci.exceptions.FatalTraCIError as e:
        print(f"TraCI Error: {e}")
    except KeyboardInterrupt:
        print("\n>> Interrupted by user")
    finally:
        traci.close()
        proc.kill()
        print(">> Shutdown complete")


if __name__ == "__main__":
    main()
