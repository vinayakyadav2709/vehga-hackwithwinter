"""
Decision explanation and logging system for traffic signal control.
Tracks why each signal decision was made and provides human-readable explanations.
"""
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
import json


class DecisionLogger:
    """Records and explains traffic signal decisions."""
    
    def __init__(self, max_history=1000):
        self.history = deque(maxlen=max_history)
        self.current_episode = 0
    
    def log_decision(
        self,
        junction_id: str,
        sim_time: float,
        chosen_edge: str,
        alternatives: List[str],
        reason: str,
        decision_data: Optional[Dict] = None
    ):
        """
        Log a signal decision with explanation.
        
        Args:
            junction_id: ID of the junction making decision
            sim_time: Current simulation time
            chosen_edge: Edge that got green signal
            alternatives: Other edges that could have been chosen
            reason: Primary reason for decision (e.g., 'q_value', 'emergency', 'safety')
            decision_data: Additional data about the decision
        """
        entry = {
            'episode': self.current_episode,
            'junction': junction_id,
            'time': sim_time,
            'timestamp': datetime.now().isoformat(),
            'chosen_edge': chosen_edge,
            'alternatives': alternatives,
            'reason': reason,
            **(decision_data or {})
        }
        self.history.append(entry)
    
    def get_recent(self, n: int = 10) -> List[Dict]:
        """Get last n decisions across all junctions."""
        return list(self.history)[-n:]
    
    def get_for_junction(self, junction_id: str, n: int = 10) -> List[Dict]:
        """Get last n decisions for specific junction."""
        junction_decisions = [d for d in self.history if d['junction'] == junction_id]
        return junction_decisions[-n:]
    
    def get_for_episode(self, episode: Optional[int] = None) -> List[Dict]:
        """Get all decisions for an episode."""
        if episode is None:
            episode = self.current_episode
        return [d for d in self.history if d['episode'] == episode]
    
    def explain_decision(self, decision: Dict) -> str:
        """Generate human-readable explanation for a decision."""
        chosen = decision['chosen_edge']
        reason = decision['reason']
        
        if reason == 'emergency_override':
            emg_edges = decision.get('emergency_edges', [])
            return f"🚨 EMERGENCY: Switched to {chosen} due to emergency vehicles on {', '.join(emg_edges)}"
        
        elif reason == 'q_value':
            q_val = decision.get('q_value', 0)
            has_emergency = decision.get('has_emergency', False)
            emg_note = " (emergency vehicle present)" if has_emergency else ""
            return f"📊 Q-Learning: Switched to {chosen} (Q={q_val:.2f}){emg_note} - best option based on traffic conditions"
        
        elif reason == 'max_red_safety':
            exceeded_edge = decision.get('exceeded_edge', chosen)
            return f"⚠️  SAFETY: Forced switch to {exceeded_edge} - exceeded max red time (starvation prevention)"
        
        elif reason == 'max_green_safety':
            return f"⚠️  FAIRNESS: Forced switch from {chosen} - exceeded max green time"
        
        elif reason == 'continue':
            return f"✓ Continue: Keeping green for {chosen} - no better alternative"
        
        elif reason == 'exploration':
            return f"🎲 Exploration: Random selection of {chosen} (epsilon-greedy)"
        
        else:
            return f"Switched to {chosen} ({reason})"
    
    def get_decision_summary(self, episode: Optional[int] = None) -> Dict:
        """Get summary statistics of decisions for an episode."""
        decisions = self.get_for_episode(episode)
        
        if not decisions:
            return {}
        
        reason_counts = {}
        emergency_count = 0
        
        for d in decisions:
            reason = d['reason']
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if d.get('has_emergency', False):
                emergency_count += 1
        
        return {
            'total_decisions': len(decisions),
            'reason_breakdown': reason_counts,
            'decisions_with_emergency': emergency_count,
            'emergency_influence_rate': emergency_count / len(decisions) if decisions else 0,
        }
    
    def reset_episode(self):
        """Increment episode counter."""
        self.current_episode += 1
    
    def export_to_json(self, filepath: str, episode: Optional[int] = None):
        """Export decisions to JSON file."""
        decisions = self.get_for_episode(episode) if episode is not None else list(self.history)
        
        with open(filepath, 'w') as f:
            json.dump({
                'episode': episode or self.current_episode,
                'total_decisions': len(decisions),
                'decisions': decisions
            }, f, indent=2)


# Global decision logger instance
decision_logger = DecisionLogger()
