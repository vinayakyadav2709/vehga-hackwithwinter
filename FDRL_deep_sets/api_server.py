"""
FastAPI backend server for traffic control system.
Provides real-time metrics, decision explanations, and simulation state.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from datetime import datetime

# Import from our modules (will be available when running alongside simulation)
try:
    from decision_logger import decision_logger
    from metrics import MetricsTracker
except ImportError:
    # Fallback for standalone testing
    decision_logger = None
    MetricsTracker = None

app = FastAPI(
    title="Traffic Control API",
    description="Backend API for FDRL Traffic Signal Control System with Emergency Vehicle Priority",
    version="1.0.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (updated by simulation)
current_metrics = {}
current_junctions = {}
current_simulation_state = {}
metrics_tracker_ref = None


def set_metrics_tracker(tracker):
    """Called by simulation to set metrics tracker reference."""
    global metrics_tracker_ref
    metrics_tracker_ref = tracker


def update_simulation_state(state: Dict):
    """Called by simulation to update current state (includes metrics)."""
    global current_simulation_state
    current_simulation_state = state


def update_metrics(metrics_data: Dict):
    """Called by simulation to update current metrics."""
    global current_metrics
    current_metrics = metrics_data


def update_junctions(junction_data: Dict):
    """Called by simulation to update junction states."""
    global current_junctions
    current_junctions = junction_data


@app.get("/")
async def root():
    """Root endpoint - API status."""
    return {
        "status": "running",
        "system": "FDRL Traffic Control with Emergency Priority",
        "version": "1.0.0",
        "endpoints": {
            "metrics": "/api/metrics",
            "decisions": "/api/decisions",
            "emergency": "/api/emergency/stats",
            "junctions": "/api/junctions"
        }
    }


@app.get("/api/metrics")
async def get_current_metrics():
    """Get current simulation metrics."""
    if not current_metrics:
        return {"message": "No metrics available yet", "data": {}}
    return current_metrics


@app.get("/api/decisions/recent")
async def get_recent_decisions(n: int = 10):
    """
    Get recent signal decisions with explanations.
    
    Args:
        n: Number of recent decisions to retrieve (default: 10)
    """
    if not decision_logger:
        raise HTTPException(status_code=503, detail="Decision logger not available")
    
    decisions = decision_logger.get_recent(n)
    
    return {
        "count": len(decisions),
        "decisions": [
            {
                **d,
                "explanation": decision_logger.explain_decision(d)
            }
            for d in decisions
        ]
    }


@app.get("/api/decisions/junction/{junction_id}")
async def get_junction_decisions(junction_id: str, n: int = 10):
    """
    Get decisions for a specific junction.
    
    Args:
        junction_id: Junction ID (e.g., 'C', 'N', 'S')
        n: Number of recent decisions to retrieve
    """
    if not decision_logger:
        raise HTTPException(status_code=503, detail="Decision logger not available")
    
    decisions = decision_logger.get_for_junction(junction_id, n)
    
    return {
        "junction": junction_id,
        "count": len(decisions),
        "decisions": [
            {
                **d,
                "explanation": decision_logger.explain_decision(d)
            }
            for d in decisions
        ]
    }


@app.get("/api/decisions/episode/{episode}")
async def get_episode_decisions(episode: int):
    """Get all decisions for a specific episode."""
    if not decision_logger:
        raise HTTPException(status_code=503, detail="Decision logger not available")
    
    decisions = decision_logger.get_for_episode(episode)
    summary = decision_logger.get_decision_summary(episode)
    
    return {
        "episode": episode,
        "summary": summary,
        "total_decisions": len(decisions),
        "decisions": decisions[:100]  # Limit to first 100 for API response
    }


@app.get("/api/decisions/summary")
async def get_decision_summary(episode: Optional[int] = None):
    """Get summary statistics of decisions for current or specified episode."""
    if not decision_logger:
        raise HTTPException(status_code=503, detail="Decision logger not available")
    
    summary = decision_logger.get_decision_summary(episode)
    return summary


@app.get("/api/emergency/stats")
async def get_emergency_stats():
    """Get emergency vehicle statistics."""
    if metrics_tracker_ref:
        stats = metrics_tracker_ref.get_comprehensive_stats()
        return {
            "current": stats.get('current_vehicles', {}),
            "episode": stats.get('episode_vehicles', {}),
            "all_time": stats.get('all_time', {})
        }
    elif 'emergency' in current_metrics:
        return current_metrics['emergency']
    else:
        return {"message": "No emergency statistics available", "data": {}}


@app.get("/api/junctions")
async def get_junctions():
    """Get all junction states."""
    if not current_junctions:
        return {"message": "No junction data available", "data": {}}
    return current_junctions


@app.get("/api/status")
async def get_system_status():
    """Get overall system status."""
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics_available": bool(current_metrics),
        "junctions_available": bool(current_junctions),
        "decision_logger_available": decision_logger is not None,
        "metrics_tracker_available": metrics_tracker_ref is not None,
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/realtime")
async def get_realtime_data():
    """Get complete real-time simulation state for frontend."""
    # Get recent decisions with explanations
    decisions_recent = []
    if decision_logger:
        recent = decision_logger.get_recent(10)
        decisions_recent = [
            {**d, "explanation": decision_logger.explain_decision(d)}
            for d in recent
        ]
    
    # Get comprehensive metrics if available
    metrics = {}
    if metrics_tracker_ref:
        try:
            metrics = metrics_tracker_ref.get_comprehensive_stats()
        except Exception:
            pass
    
    return {
        "simulation": current_simulation_state,
        "junctions": current_junctions,
        "recent_decisions": decisions_recent,
        "metrics": metrics,
        "timestamp": current_simulation_state.get('timestamp', datetime.now().timestamp())
    }


# For standalone testing
if __name__ == "__main__":
    import uvicorn
    print("Starting API server on http://localhost:8000")
    print("API documentation available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
