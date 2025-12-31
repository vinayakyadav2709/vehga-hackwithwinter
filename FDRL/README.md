# FDRL Core: The Brain of the Intersection

> [!IMPORTANT]
> **Privacy First**: This module ensures that intelligence is shared, but **personal data never leaves the junction**.

## 📌 Component Purpose
The `FDRL` (Federated Deep Reinforcement Learning) module is the proprietary AI engine that runs on edge devices. It is responsible for making split-second decisions to optimize traffic flow.

## 🧠 Technical Deep Dive

### 1. Autonomous Intersection Agents
*   **PPO (Proximal Policy Optimization)**: We use PPO, a state-of-the-art Policy Gradient method, for stable and efficient online learning.
*   **State Space**: Queue length, waiting time, vehicle type (Ambulance vs. Car).
*   **Action Space**: Extend Green, Switch Phase, All Red.
*   **Reward Function**: Maximizing throughput while minimizing standard deviation of waiting times (Fairness).

### 2. Privacy-Preserving Design
*   **No Cloud Uploads**: Video frames are processed instantly and deleted.
*   **Weight Transmission**: Only the *learned policy parameters* (weights) of the Neural Network are sent to the central server.
*   **Compliance**: Fully GPDR and DPDP (Digital Personal Data Protection Act) compliant by design.

### 3. Digitally Validated Scenarios (Simulation)
*   **SUMO Integration**: Before deployment, every model is validated in a "Controlled Traffic Environment" using SUMO (Simulation of Urban MObility).
*   **Scenario Stress-Testing**:
    *   **Coldplay Concert**: Simulating massive unidirectional outflow.
    *   **VIP Movement**: Simulating sudden stops and corridor clearance.
    *   **Sensor Failure**: Simulating 20% camera blackout to test robustness.

## 📉 Impact on Economics
*   **Retrofit-Friendly**: The AI model is optimized (quantized) to run on low-cost hardware like Raspberry Pi 4 or Nvidia Jetson Nano, removing the need for server-grade GPUs at every pole.