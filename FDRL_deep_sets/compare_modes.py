#!/usr/bin/env python3
"""
Benchmark Comparison Script
Compares FDRL, Actuated, and Fixed-Time traffic control modes.
"""
import os
import sys
import subprocess
import json
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration
EPISODES = 1  # Number of episodes to run for each mode
MODEL_PATH = "global_model.pth"  # Path to trained FDRL model

def run_mode(mode, episodes, load_model=None):
    """Run simulation for a specific mode and capture output."""
    print(f"\n{'='*70}")
    print(f"Running {mode.upper()} mode ({episodes} episodes)...")
    print(f"{'='*70}\n")
    
    cmd = ["uv", "run", "python", "main.py", "--mode", mode, "--episodes", str(episodes), "--no-gui"]
    
    if load_model and os.path.exists(load_model):
        cmd.extend(["--load", load_model])
    
    result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
    
    return {
        'mode': mode,
        'return_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr
    }

def parse_episode_summary(output):
    """Extract metrics from episode summary."""
    lines = output.split('\n')
    metrics = {
        'avg_wait_normal': None,
        'avg_wait_emergency': None,
        'wait_reduction': None,
        'emergency_ratio': None,
        'avg_speed': None,
        'peak_queue': None,
        'total_vehicles': 0
    }
    
    for i, line in enumerate(lines):
        if 'Normal Vehicles' in line and 'completed' in line:
            # Extract normal count
            parts = line.split(':')
            if len(parts) > 1:
                metrics['normal_count'] = int(parts[1].split('completed')[0].strip())
        
        elif 'Avg Wait' in line and i > 0:
            # Check if previous line was "Normal Vehicles"
            if 'Normal Vehicles' in lines[i-2]:
                try:
                    metrics['avg_wait_normal'] = float(line.split(':')[1].strip().replace('s', ''))
                except (IndexError, ValueError):
                    pass
            # Check if previous line was "Emergency Vehicles"
            elif 'Emergency Vehicles' in lines[i-2]:
                try:
                    metrics['avg_wait_emergency'] = float(line.split(':')[1].strip().replace('s', ''))
                except (IndexError, ValueError):
                    pass
        
        elif 'Wait Reduction' in line:
            try:
                metrics['wait_reduction'] = float(line.split(':')[1].strip().replace('%', ''))
            except (IndexError, ValueError):
                pass
        
        elif 'Emergency/Normal' in line:
            try:
                metrics['emergency_ratio'] = float(line.split(':')[1].strip().replace('%', ''))
            except (IndexError, ValueError):
                pass
        
        elif 'Avg Speed' in line and 'SUMMARY' not in lines[i-3]:
            try:
                metrics['avg_speed'] = float(line.split(':')[1].strip().split()[0])
            except (IndexError, ValueError):
                pass
        
        elif 'Peak Queue' in line:
            try:
                metrics['peak_queue'] = int(line.split(':')[1].strip().split()[0])
            except (IndexError, ValueError):
                pass
    
    return metrics

def generate_comparison_report(results):
    """Generate comparison report from all modes."""
    print(f"\n{'='*70}")
    print("COMPARISON REPORT")
    print(f"{'='*70}\n")
    print(f"Episodes per mode: {EPISODES}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Parse metrics for each mode
    mode_metrics = {}
    for result in results:
        mode = result['mode']
        metrics = parse_episode_summary(result['stdout'])
        mode_metrics[mode] = metrics
    
    # Print comparison table
    print("Performance Comparison:")
    print(f"{'Metric':<30} | {'Fixed-Time':<12} | {'Actuated':<12} | {'FDRL':<12}")
    print("-" * 75)
    
    metrics_to_compare = [
        ('Avg Wait (Normal)', 'avg_wait_normal', 's'),
        ('Avg Wait (Emergency)', 'avg_wait_emergency', 's'),
        ('Wait Reduction', 'wait_reduction', '%'),
        ('Emergency/Normal Ratio', 'emergency_ratio', '%'),
        ('Avg Speed', 'avg_speed', 'm/s'),
        ('Peak Queue', 'peak_queue', 'veh')
    ]
    
    for label, key, unit in metrics_to_compare:
        fixed = mode_metrics.get('fixed_time', {}).get(key, 'N/A')
        actuated = mode_metrics.get('actuated', {}).get(key, 'N/A')
        fdrl = mode_metrics.get('test', {}).get(key, 'N/A')
        
        # Format values
        def fmt(val):
            if val == 'N/A' or val is None:
                return 'N/A'
            return f"{val:.2f} {unit}"
        
        print(f"{label:<30} | {fmt(fixed):<12} | {fmt(actuated):<12} | {fmt(fdrl):<12}")
    
    print("\n" + "="*70)
    
    # Determine winner for key metrics
    print("\nKey Findings:")
    
    # Best overall wait time
    wait_times = {}
    for mode, metrics in mode_metrics.items():
        if metrics.get('avg_wait_normal'):
            wait_times[mode] = metrics['avg_wait_normal']
    
    if wait_times:
        best_mode = min(wait_times, key=wait_times.get)
        print(f"✓ Lowest Normal Wait Time: {best_mode.upper()} ({wait_times[best_mode]:.2f}s)")
    
    # Best emergency priority
    if mode_metrics.get('test', {}).get('wait_reduction'):
        reduction = mode_metrics['test']['wait_reduction']
        print(f"✓ FDRL Emergency Wait Reduction: {reduction:.1f}%")
        if reduction > 60:
            print(f"  → Target achieved! (>60% reduction)")
        else:
            print(f"  → Target not met (need >60% reduction)")
    
    # Best queue management
    queues = {}
    for mode, metrics in mode_metrics.items():
        if metrics.get('peak_queue'):
            queues[mode] = metrics['peak_queue']
    
    if queues:
        best_mode = min(queues, key=queues.get)
        print(f"✓ Lowest Peak Queue: {best_mode.upper()} ({queues[best_mode]} vehicles)")
    
    print("\n" + "="*70)
    
    # Save results to JSON
    output_file = f"comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(os.path.join(PROJECT_DIR, output_file), 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'episodes': EPISODES,
            'results': mode_metrics
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

def main():
    """Main comparison execution."""
    print("="*70)
    print("TRAFFIC CONTROL MODES COMPARISON")
    print("="*70)
    
    # Check if trained model exists for FDRL
    if not os.path.exists(os.path.join(PROJECT_DIR, MODEL_PATH)):
        print(f"\nError: Trained model not found at {MODEL_PATH}")
        print("Please train the FDRL model first:")
        print("  uv run python main.py --mode train --episodes 50 --no-gui")
        sys.exit(1)
    
    print(f"\nConfiguration:")
    print(f"  Episodes per mode: {EPISODES}")
    print(f"  FDRL model: {MODEL_PATH}")
    print(f"\nThis will take several minutes...\n")
    
    # Run all modes
    results = []
    
    # 1. Fixed-Time
    results.append(run_mode('fixed_time', EPISODES))
    
    # 2. Actuated
    results.append(run_mode('actuated', EPISODES))
    
    # 3. FDRL (Test mode with trained model)
    results.append(run_mode('test', EPISODES, load_model=MODEL_PATH))
    
    # Generate comparison report
    generate_comparison_report(results)
    
    print("\nComparison complete!")

if __name__ == "__main__":
    main()
