"""
Unified metrics tracking for traffic simulation.
Tracks both normal and emergency vehicle performance.
"""
import traci
from collections import defaultdict
from typing import Dict, List, Optional


class VehicleMetrics:
    """Tracks individual vehicle journey times and delays."""
    
    def __init__(self):
        # Active vehicles being tracked
        self.active_vehicles = {}  # veh_id -> vehicle_data
        
        # Completed journeys
        self.completed_emergency = []
        self.completed_normal = []
        
        # Per-episode stats
        self.episode_num = 0
    
    def step(self):
        """Call every simulation step to update vehicle tracking."""
        # Get all active vehicles
        all_vehicles = traci.vehicle.getIDList()
        
        for veh_id in all_vehicles:
            try:
                vtype = traci.vehicle.getTypeID(veh_id)
                is_emergency = (vtype == "emergency")
                
                # Initialize tracking for new vehicles
                if veh_id not in self.active_vehicles:
                    self.active_vehicles[veh_id] = {
                        'type': vtype,
                        'is_emergency': is_emergency,
                        'depart_time': traci.simulation.getTime(),
                        'total_wait': 0,
                    }
                
                # Update accumulated wait time
                wait = traci.vehicle.getAccumulatedWaitingTime(veh_id)
                self.active_vehicles[veh_id]['total_wait'] = wait
                
            except traci.exceptions.TraCIException:
                continue
        
        # Check for arrived vehicles
        arrived = traci.simulation.getArrivedIDList()
        for veh_id in arrived:
            if veh_id in self.active_vehicles:
                data = self.active_vehicles.pop(veh_id)
                data['arrival_time'] = traci.simulation.getTime()
                data['journey_time'] = data['arrival_time'] - data['depart_time']
                data['episode'] = self.episode_num
                
                # Store in appropriate list
                if data['is_emergency']:
                    self.completed_emergency.append(data)
                else:
                    self.completed_normal.append(data)
    
    def get_current_stats(self) -> Dict:
        """Get statistics for currently active vehicles."""
        active_emergency = [v for v in self.active_vehicles.values() if v['is_emergency']]
        active_normal = [v for v in self.active_vehicles.values() if not v['is_emergency']]
        
        return {
            'total_active': len(self.active_vehicles),
            'active_emergency': len(active_emergency),
            'active_normal': len(active_normal),
            'active_emergency_avg_wait': (
                sum(v['total_wait'] for v in active_emergency) / len(active_emergency)
                if active_emergency else 0
            ),
        }
    
    def get_episode_stats(self) -> Dict:
        """Get statistics for current episode (completed vehicles)."""
        # Filter for current episode
        episode_emergency = [v for v in self.completed_emergency if v['episode'] == self.episode_num]
        episode_normal = [v for v in self.completed_normal if v['episode'] == self.episode_num]
        
        stats = {
            'episode': self.episode_num,
            'emergency': self._compute_vehicle_stats(episode_emergency),
            'normal': self._compute_vehicle_stats(episode_normal),
        }
        
        # Calculate reduction percentage and delay ratio
        if stats['normal']['avg_wait'] > 0:
            reduction = (
                (stats['normal']['avg_wait'] - stats['emergency']['avg_wait']) 
                / stats['normal']['avg_wait'] * 100
            )
            stats['emergency_wait_reduction_percent'] = reduction
            
            # Calculate emergency delay as percentage of normal
            emergency_ratio = stats['emergency']['avg_wait'] / stats['normal']['avg_wait']
            stats['emergency_delay_ratio'] = emergency_ratio
        else:
            stats['emergency_wait_reduction_percent'] = 0
            stats['emergency_delay_ratio'] = 0
        
        return stats
    
    def get_all_time_stats(self) -> Dict:
        """Get statistics across all episodes."""
        return {
            'total_emergency': len(self.completed_emergency),
            'total_normal': len(self.completed_normal),
            'emergency': self._compute_vehicle_stats(self.completed_emergency),
            'normal': self._compute_vehicle_stats(self.completed_normal),
        }
    
    def _compute_vehicle_stats(self, vehicles: List[Dict]) -> Dict:
        """Compute statistics for a list of vehicles."""
        if not vehicles:
            return {
                'count': 0,
                'avg_wait': 0,
                'avg_journey_time': 0,
                'total_wait': 0,
            }
        
        return {
            'count': len(vehicles),
            'avg_wait': sum(v['total_wait'] for v in vehicles) / len(vehicles),
            'avg_journey_time': sum(v['journey_time'] for v in vehicles) / len(vehicles),
            'total_wait': sum(v['total_wait'] for v in vehicles),
            'max_wait': max(v['total_wait'] for v in vehicles),
            'min_wait': min(v['total_wait'] for v in vehicles),
        }
    
    def reset_episode(self):
        """Reset for new episode (increment episode counter, clear active vehicles)."""
        self.episode_num += 1
        self.active_vehicles = {}
    
    def reset_all(self):
        """Complete reset (for new training session)."""
        self.active_vehicles = {}
        self.completed_emergency = []
        self.completed_normal = []
        self.episode_num = 0


class SimulationMetrics:
    """Tracks overall simulation metrics (aggregated from lanes)."""
    
    def __init__(self):
        self.history = []  # List of metric snapshots over time
        self.episode_num = 0
    
    def record_step(self, step: int, metrics: Dict):
        """Record metrics for current simulation step."""
        entry = {
            'episode': self.episode_num,
            'step': step,
            **metrics
        }
        self.history.append(entry)
    
    def get_episode_summary(self, episode: Optional[int] = None) -> Dict:
        """Get summary statistics for an episode."""
        if episode is None:
            episode = self.episode_num
        
        episode_data = [h for h in self.history if h['episode'] == episode]
        
        if not episode_data:
            return {}
        
        # Calculate averages across episode
        return {
            'episode': episode,
            'steps': len(episode_data),
            'avg_total_wait': sum(h.get('total_wait', 0) for h in episode_data) / len(episode_data),
            'avg_wait_per_vehicle': sum(h.get('avg_wait', 0) for h in episode_data) / len(episode_data),
            'avg_speed': sum(h.get('avg_speed', 0) for h in episode_data) / len(episode_data),
            'avg_queue': sum(h.get('total_queue', 0) for h in episode_data) / len(episode_data),
            'peak_queue': max(h.get('total_queue', 0) for h in episode_data),
            'peak_wait': max(h.get('total_wait', 0) for h in episode_data),
        }
    
    def reset_episode(self):
        """Reset for new episode."""
        self.episode_num += 1
    
    def reset_all(self):
        """Complete reset."""
        self.history = []
        self.episode_num = 0


class MetricsTracker:
    """
    Unified metrics tracking system for the entire simulation.
    Combines vehicle-level and simulation-level metrics.
    """
    
    def __init__(self):
        self.vehicle_metrics = VehicleMetrics()
        self.simulation_metrics = SimulationMetrics()
    
    def step(self, simulation_step: int, lane_metrics: Optional[Dict] = None):
        """Update all metrics for current step."""
        self.vehicle_metrics.step()
        
        if lane_metrics:
            self.simulation_metrics.record_step(simulation_step, lane_metrics)
    
    def get_comprehensive_stats(self) -> Dict:
        """Get all current statistics in one call."""
        return {
            'current_vehicles': self.vehicle_metrics.get_current_stats(),
            'episode_vehicles': self.vehicle_metrics.get_episode_stats(),
            'episode_simulation': self.simulation_metrics.get_episode_summary(),
            'all_time': self.vehicle_metrics.get_all_time_stats(),
        }
    
    def print_episode_summary(self, episode_num: int):
        """Print comprehensive episode summary."""
        stats = self.get_comprehensive_stats()
        
        print("\n" + "="*70)
        print(f"EPISODE {episode_num + 1} SUMMARY")
        print("="*70)
        
        # Simulation metrics
        sim = stats['episode_simulation']
        if sim:
            print(f"Simulation Steps     : {sim.get('steps', 0)}")
            print(f"Avg Wait/Vehicle     : {sim.get('avg_wait_per_vehicle', 0):.2f}s")
            print(f"Avg Speed            : {sim.get('avg_speed', 0):.2f} m/s")
            print(f"Peak Queue           : {sim.get('peak_queue', 0):.0f} vehicles")
        
        # Vehicle metrics
        veh = stats['episode_vehicles']
        emg = veh['emergency']
        norm = veh['normal']
        
        if emg['count'] > 0 or norm['count'] > 0:
            print(f"\n--- Vehicle Performance ---")
            print(f"Normal Vehicles      : {norm['count']} completed")
            print(f"  Avg Wait           : {norm['avg_wait']:.2f}s")
            print(f"  Avg Journey        : {norm['avg_journey_time']:.2f}s")
            
            print(f"Emergency Vehicles   : {emg['count']} completed")
            print(f"  Avg Wait           : {emg['avg_wait']:.2f}s")
            print(f"  Avg Journey        : {emg['avg_journey_time']:.2f}s")
            
            if 'emergency_wait_reduction_percent' in veh:
                reduction = veh['emergency_wait_reduction_percent']
                ratio = veh['emergency_delay_ratio']
                
                print(f"\n--- Emergency Priority Performance ---")
                print(f"Wait Reduction       : {reduction:.1f}%")
                print(f"Emergency/Normal     : {ratio:.1%}")
        
        print("="*70 + "\n")
    
    def reset_episode(self):
        """Reset both trackers for new episode."""
        self.vehicle_metrics.reset_episode()
        self.simulation_metrics.reset_episode()
    
    def reset_all(self):
        """Complete reset for new training session."""
        self.vehicle_metrics.reset_all()
        self.simulation_metrics.reset_all()
