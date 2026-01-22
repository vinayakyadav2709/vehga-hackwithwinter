# FDRL Traffic Control with Emergency Vehicle Priority

**Federated Deep Reinforcement Learning** system for multi-intersection traffic signal control with **emergency vehicle prioritization**.

## 🚀 Features

- **Emergency Vehicle Priority**: Automatically detects and prioritizes emergency vehicles (ambulances, police, fire trucks)
- **Multi-Agent Learning**: 7 intersections learning cooperatively via federated learning
- **Deep Sets Architecture**: Handles variable number of incoming edges per intersection
- **Explainable AI**: Decision logging with human-readable explanations
- **REST API**: Backend API for real-time metrics and decision explanations
- **Performance**: Competitive with state-of-the-art actuated control

## 📊 System Architecture

### Model Overview

**Model Type**: Deep Q-Network (DQN) with Deep Sets  
**Architecture**:
```
Input: 18 features per candidate edge
  - Per Edge: [queue, wait, speed, volume, occupancy, 
              emergency_count, emergency_wait, has_emergency, 
              time_since_last_green, is_green]
  - Context: [global queue, wait, speed, volume, occupancy,
             emergency_count, emergency_wait, has_emergency]

Network: 18 → 256 → 128 → 1 (Q-value)
```

**Learning Algorithm**: DQN with Experience Replay + Federated Aggregation  
**Emergency Priority**: 10x penalty for emergency vehicle wait time

### Components

| Component | Purpose |
|-----------|---------|
| `main.py` | Simulation orchestrator & training loop |
| `junction.py` | Individual intersection agent with DQN |
| `models.py` | Deep Sets neural network architecture |
| `utils.py` | Feature extraction & reward computation |
| `metrics.py` | Vehicle & simulation metrics tracking |
| `decision_logger.py` | Decision explanations & logging |
| `fdrl_server.py` | Federated aggregation server |
| `api_server.py` | REST API for frontend integration |
| `setup_complex_environment.py` | Network & route generation |

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- Docker (for SUMO simulation)
- uv (Python package manager)

### Setup

```bash
# Clone the repository
cd FDRL_deep_sets

# Install dependencies
uv sync

# Generate network and routes (all modes at once)
uv run python setup_complex_environment.py
```

This generates:
- **network.net.xml** - Base network for FDRL
- **network_actuated.net.xml** - Actuated traffic lights
- **network_fixed.net.xml** - Fixed-time traffic lights  
- **traffic.rou.xml** - Routes with 5% emergency vehicles
- **fdrl.sumocfg**, **actuated.sumocfg**, **fixed.sumocfg** - Configs for each mode

## 🎯 Usage

### Training

```bash
# Full training (500 episodes recommended)
uv run python main.py --mode train --episodes 500 --no-gui

# Quick training test
uv run python main.py --mode train --episodes 10 --no-gui

# Continue from checkpoint
uv run python main.py --mode train --load global_model.pth --episodes 200 --no-gui
```

**Training Output**:
```
Step  | Total Wait | Avg Wait | Avg Speed | Queue | Active EMG | Epsilon
--------------------------------------------------------------------------------
100   | 282.0     | 5.6      | 8.86      | 21    | 3          | 1.000
500   | 1864.0    | 15.7     | 6.66      | 87    | 12         | 0.995

[Step 500] >> Aggregation Round 1...
>> Global Model saved to global_model.pth
```

### Testing

```bash
# Test trained model
uv run python main.py --mode test --load global_model.pth --episodes 10 --no-gui
```

### Baseline Comparison

```bash
# Actuated control (adaptive baseline)
uv run python main.py --mode actuated --episodes 10 --no-gui

# Fixed-time control (static baseline)
uv run python main.py --mode fixed_time --episodes 10 --no-gui
```

### Automated Comparison

Run comprehensive benchmark across all modes:

```bash
# Compares Fixed-Time vs Actuated vs FDRL
uv run python compare_modes.py
```

This will:
1. Run Fixed-Time control for 10 episodes
2. Run Actuated control for 10 episodes
3. Run FDRL test mode for 10 episodes
4. Generate comparison report
5. Save results to JSON file

**Output:**
```
Performance Comparison:
Metric                         | Fixed-Time   | Actuated     | FDRL        
---------------------------------------------------------------------------
Avg Wait (Normal)              | 52.30 s      | 38.50 s      | 35.20 s     
Avg Wait (Emergency)           | 52.30 s      | 38.50 s      | 8.75 s      
Wait Reduction                 | 0.0 %        | 0.0 %        | 77.2 %      
Peak Queue                     | 149 veh      | 42 veh       | 38 veh      
```

## 📈 Model Performance

### Episode Summary Example

```
======================================================================
EPISODE 50 SUMMARY
======================================================================
Simulation Steps     : 3500
Avg Wait/Vehicle     : 35.20s
Avg Speed            : 13.8 m/s
Peak Queue           : 38 vehicles

--- Vehicle Performance ---
Normal Vehicles      : 1638 completed
  Avg Wait           : 38.50s
  Avg Journey        : 115.30s
Emergency Vehicles   : 162 completed
  Avg Wait           : 8.20s
  Avg Journey        : 88.60s

--- Emergency Priority Performance ---
Wait Reduction       : 78.7%
Emergency/Normal     : 21.3%
======================================================================
```

**Key Metrics**:
- **Emergency Wait Reduction**: Percentage reduction in emergency vehicle wait time vs normal vehicles
- **Emergency/Normal Ratio**: Emergency wait as percentage of normal wait (lower is better)

### Expected Performance

| Metric | Fixed-Time | Actuated | FDRL (Ours) |
|--------|------------|----------|-------------|
| Avg Wait | ~60s | ~35s | ~35s |
| Peak Queue | 149 | 29 | 37 |
| Emergency Priority | None | None | **✅ 70-80% reduction** |

## 🔌 API Integration

### Starting the API Server

```bash
# Standalone API server
uv run python api_server.py

# Server runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

### API Endpoints

#### 1. Get Current Metrics
```bash
GET /api/metrics
```

**Response**:
```json
{
  "step": 1500,
  "total_wait": 5418.0,
  "avg_wait": 23.1,
  "avg_speed": 4.54,
  "queue": 185,
  "emergency": {
    "active_emergency": 19,
    "avg_emergency_wait": 12.5
  }
}
```

#### 2. Get Recent Decisions with Explanations
```bash
GET /api/decisions/recent?n=10
```

**Response**:
```json
{
  "count": 10,
  "decisions": [
    {
      "junction": "C",
      "time": 125.5,
      "chosen_edge": "N2C",
      "reason": "q_value",
      "emergency_present": true,
      "explanation": "📊 Q-Learning: Switched to N2C (Q=-0.45) (emergency vehicle present) - best option based on traffic conditions"
    }
  ]
}
```

#### 3. Get Junction-Specific Decisions
```bash
GET /api/decisions/junction/C?n=5
```

#### 4. Get Emergency Statistics
```bash
GET /api/emergency/stats
```

**Response**:
```json
{
  "current": {
    "active_emergency": 20,
    "active_normal": 158
  },
  "episode": {
    "emergency": {
      "count": 162,
      "avg_wait": 8.75,
      "avg_journey_time": 92.4
    },
    "normal": {
      "count": 1638,
      "avg_wait": 42.3,
      "avg_journey_time": 118.2
    },
    "emergency_wait_reduction_percent": 79.3,
    "emergency_delay_ratio": 0.207
  }
}
```

#### 5. Get All Junction States
```bash
GET /api/junctions
```

### Frontend Integration Example

#### Using Fetch API

```javascript
// Get real-time data every second
setInterval(async () => {
    const response = await fetch('http://localhost:8000/api/realtime');
    const data = await response.json();
    
    console.log(`Step: ${data.simulation.step}, Wait: ${data.simulation.avg_wait}s`);
    updateDashboard(data);
}, 1000);

// Get decision explanations
async function getDecisions() {
    const response = await fetch('http://localhost:8000/api/decisions/recent?n=20');
    const data = await response.json();
    
    data.decisions.forEach(decision => {
        console.log(decision.explanation);
    });
}
```

## 📡 API Usage Guide

### Starting the API

The API server starts automatically when you run the simulation:

```bash
uv run python main.py --mode train --episodes 10 --no-gui
# API will be available at http://localhost:8000
```

Or run standalone:
```bash
uv run python api_server.py
```

### Available Endpoints

#### 1. Real-Time Data (Recommended for Frontend)
```bash
GET /api/realtime
```
Returns complete current state updated every 100 simulation steps:
```json
{
  "simulation": {
    "step": 1500,
    "episode": 1,
    "avg_wait": 23.4,
    "avg_speed": 7.2,
    "active_emergency": 15,
    "epsilon": 0.85
  },
  "junctions": {
    "C": {
      "current_edge": "N2C",
      "phase_duration": 12.5
    }
  },
  "recent_decisions": [...],
  "metrics": {...}
}
```

#### 2. Decision Explanations
```bash
GET /api/decisions/recent?n=10
```
Returns recent decisions with human-readable explanations.

#### 3. Emergency Statistics
```bash
GET /api/emergency/stats
```
Returns emergency vehicle performance metrics.

#### 4. Junction States
```bash
GET /api/junctions
```
Returns current state of all traffic signals.

### Frontend Integration Examples

#### React Hook
```jsx
import { useState, useEffect } from 'react';

function useTrafficData() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const res = await fetch('http://localhost:8000/api/realtime');
      const json = await res.json();
      setData(json);
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  return data;
}

function Dashboard() {
  const data = useTrafficData();
  
  return (
    <div>
      <h2>Traffic Control Dashboard</h2>
      {data && (
        <>
          <p>Step: {data.simulation.step}</p>
          <p>Avg Wait: {data.simulation.avg_wait}s</p>
          <p>Active Emergency: {data.simulation.active_emergency}</p>
        </>
      )}
    </div>
  );
}
```

#### Vue.js
```vue
<template>
  <div>
    <h2>Traffic Metrics</h2>
    <p>Step: {{ metrics.step }}</p>
    <p>Wait Time: {{ metrics.avg_wait }}s</p>
  </div>
</template>

<script>
export default {
  data() {
    return { metrics: {} }
  },
  mounted() {
    setInterval(async () => {
      const res = await fetch('http://localhost:8000/api/realtime');
      const data = await res.json();
      this.metrics = data.simulation;
    }, 1000);
  }
}
</script>
```

### API Response Examples

**Decision Explanation:**
```json
{
  "junction": "C",
  "chosen_edge": "N2C",
  "reason": "q_value",
  "has_emergency": true,
  "explanation": "📊 Q-Learning: Switched to N2C (Q=-0.45) (emergency vehicle present)"
}
```

**Emergency Stats:**
```json
{
  "episode": {
    "normal": {
      "avg_wait": 42.3,
      "count": 1638
    },
    "emergency": {
      "avg_wait": 8.75,
      "count": 162
    },
    "wait_reduction": 79.3
  }
}
```

#### Using Axios

```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

// Get metrics
const metrics = await axios.get(`${API_BASE}/metrics`);

// Get decisions for specific junction
const decisions = await axios.get(`${API_BASE}/decisions/junction/C?n=5`);

// Get emergency stats
const emergency = await axios.get(`${API_BASE}/emergency/stats`);
```

#### React Example

```jsx
import React, { useState, useEffect } from 'react';

function TrafficDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [decisions, setDecisions] = useState([]);

  useEffect(() => {
    // Fetch metrics every 5 seconds
    const interval = setInterval(async () => {
      const response = await fetch('http://localhost:8000/api/metrics');
      const data = await response.json();
      setMetrics(data);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Fetch recent decisions
    async function fetchDecisions() {
      const response = await fetch('http://localhost:8000/api/decisions/recent?n=5');
      const data = await response.json();
      setDecisions(data.decisions);
    }
    
    fetchDecisions();
    const interval = setInterval(fetchDecisions, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1>Traffic Control Dashboard</h1>
      
      {metrics && (
        <div>
          <h2>Current Status</h2>
          <p>Active Emergency Vehicles: {metrics.emergency?.active_emergency || 0}</p>
          <p>Average Wait: {metrics.avg_wait?.toFixed(1)}s</p>
          <p>Queue Length: {metrics.queue}</p>
        </div>
      )}

      <div>
        <h2>Recent Decisions</h2>
        {decisions.map((d, i) => (
          <div key={i}>
            <strong>{d.junction}</strong>: {d.explanation}
          </div>
        ))}
      </div>
    </div>
  );
}
```

## 🧠 How the Model Works

### 1. State Representation
Each intersection observes:
- **Per Edge**: Queue length, wait time, speed, volume, occupancy
- **Emergency Features**: Count, wait time, presence flag
- **Temporal**: Time since last green
- **Context**: Global network state

### 2. Emergency Detection
```python
# Real-time detection via vehicle type
for vehicle in lane.getVehicles():
    if vehicle.getType() == "emergency":
        emergency_count += 1
        emergency_wait += vehicle.getAccumulatedWaitingTime()
```

### 3. Reward Function
```python
reward = -queue - wait - (10.0 * emergency_wait)
```

The **10x penalty** for emergency vehicles ensures they are heavily prioritized.

### 4. Learning Process
1. **Local Learning**: Each junction agent learns from experience
2. **Experience Replay**: Stores transitions for stable learning
3. **Federated Aggregation**: Every 500 steps, agents share and aggregate model weights
4. **Outlier Detection**: Removes poor-performing agents from aggregation

### 5. Decision Making
```
For each signal change:
1. Compute Q-values for all candidate edges
2. Check for emergency vehicles
3. Apply safety constraints (max red/green time)
4. Select edge with highest Q-value
5. Log decision with explanation
```

## 📁 Project Structure

```
FDRL_deep_sets/
├── main.py                    # Training & testing orchestrator
├── junction.py                # Junction agent (DQN)
├── models.py                  # Deep Sets neural network
├── utils.py                   # Features & rewards
├── metrics.py                 # Performance tracking
├── decision_logger.py         # Decision explanations
├── fdrl_server.py            # Federated aggregation
├── api_server.py             # REST API backend
├── setup_complex_environment.py  # Network generation
├── complex.net.xml          # Road network topology
├── complex.rou.xml           # Traffic routes (with emergency vehicles)
├── complex.sumocfg           # SUMO configuration
├── global_model.pth          # Trained model (generated)
└── pyproject.toml            # Dependencies
```

## 🔧 Configuration

### Emergency Vehicle Generation

Edit `setup_complex_environment.py`:
```python
# Line 12: Adjust emergency ratio
EMERGENCY_RATIO = 0.05  # 5% emergency vehicles
```

### Reward Tuning

Edit `utils.py`:
```python
# Line 218: Adjust emergency penalty
r_emergency_wait = -10.0 * emergency_wait  # Try 5x, 10x, 15x
```

### Safety Constraints

Edit `junction.py`:
```python
MAX_RED_TIME = 120.0   # Max time an edge can stay red
MAX_GREEN_TIME = 100.0  # Max time an edge can stay green
```

## 🧪 Testing

### Smoke Test
```bash
# Quick functionality test (1 episode)
uv run python main.py --mode train --episodes 1 --no-gui
```

### API Test
```bash
# Start API in background
uv run python api_server.py &

# Test endpoints
curl http://localhost:8000/api/status
curl http://localhost:8000/api/metrics
curl http://localhost:8000/api/decisions/recent?n=5
curl http://localhost:8000/api/emergency/stats
```

## 📝 Citation

If you use this code in your research, please cite:

```bibtex
@software{fdrl_emergency_traffic_2026,
  title={Federated Deep Reinforcement Learning for Traffic Signal Control with Emergency Vehicle Priority},
  author={Your Name},
  year={2026},
  url={https://github.com/yourusername/FDRL_deep_sets}
}
```

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Contact

For questions or issues, please open a GitHub issue or contact [your-email@example.com]

## 🙏 Acknowledgments

- SUMO Traffic Simulator
- PyTorch Deep Learning Framework
- FastAPI Web Framework
