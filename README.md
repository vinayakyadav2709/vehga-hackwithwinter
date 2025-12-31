# FDRL Smart AI Traffic Management System

A comprehensive **Federated Deep Reinforcement Learning (FDRL)** based intelligent traffic signal control system that leverages edge computing, distributed learning, and real-time traffic analytics to optimize traffic flow in smart cities.

## 📋 Table of Contents

- [System Overview](#-system-overview)
- [Project Architecture](#-project-architecture)
- [Key Components](#-key-components)
- [Installation](#-installation)
- [Running the System](#-running-the-system)
- [Tech Stack](#-tech-stack)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 System Overview

FDRL is an advanced traffic management platform that replaces traditional fixed-time traffic signal controllers with an intelligent, adaptive system. The platform integrates:

- **Edge Computing**: Local traffic analysis on signal cameras using TensorFlow Lite models
- **Federated Learning**: Distributed AI training across multiple junctions without centralizing sensitive data
- **Deep Reinforcement Learning**: PPO (Proximal Policy Optimization) agent for intelligent signal control
- **Real-time Monitoring**: Comprehensive dashboard for traffic authorities and stakeholders
- **Multi-device Coordination**: Seamless communication between multiple camera devices to optimize network-wide traffic

### Key Benefits

✅ **Reduced Congestion**: Intelligent signal timing minimizes vehicle waiting times  
✅ **Privacy-Preserving**: Federated approach keeps traffic data localized  
✅ **Scalable**: Works across multiple junctions without central bottleneck  
✅ **Edge-Based**: Local processing reduces latency and bandwidth usage  
✅ **Real-time Adaptation**: Responds dynamically to actual traffic conditions  
✅ **Multi-device Coordination**: Devices communicate to ensure network-wide optimization

---

## 🏗️ Project Architecture

The complete system is organized into five main modules, each handling a specific aspect of the traffic management ecosystem:

1. **Server (`/Server`)**
   - The central nervous system of Vegha.
   - Built with **Flask** and **Socket.IO**.
   - Orchestrates communication between edge devices, the dashboard, and the simulation engine.
   - Manages global state and coordinates federated learning rounds.

2. **Frontend (`/Frontend`)**
   - A modern, responsive dashboard built with **Next.js**.
   - Provides real-time visualization of traffic junctions.
   - Displays analytics, system health, and training metrics for administrators.

3. **FDRL Core (`/FDRL`)**
   - The intelligence hub containing the Deep Reinforcement Learning logic.
   - Includes the **PPO Agent**, **Federated Learning client/server** logic, and **SUMO simulator** integration.
   - Used for training and validating models before deployment.

4. **Mobile Edge App (`/app`)**
   - A **React Native (Expo)** application designed for edge devices (e.g., smartphones mounted at junctions).
   - Performs real-time object detection using **TensorFlow Lite**.
   - Sends traffic metrics (vehicle counts, congestion levels) to the central server.
   - Receives signal control commands.

5. **MapServer (`/MapServer`)**
   - A dedicated Python service for handling geospatial data.
   - Serves map geometry and topology data to other components.

---

## ⚙️ Installation

### Prerequisites
- **Python 3.8+**
- **Node.js 18+** & **npm**
- **Bun** (for Frontend)
- **SUMO** (Simulation of Urban MObility) - Required for simulation mode.

### 1. Server Setup
```bash
cd Server
pip install -r requirements.txt
```

### 2. Frontend Setup
```bash
cd Frontend
bun install
```

### 3. FDRL Setup
```bash
cd FDRL
pip install -r requirements.txt  # Or use uv if available
```

### 4. Mobile App Setup
```bash
cd app
npm install
```

---

## 🚀 Running the System

To bring the entire Vegha system online, follow this startup sequence:

### 1. Start the Map Server
```bash
cd MapServer
python server.py
```

### 2. Start the Main Backend Server
```bash
cd Server
python main.py
```
*The server will start on port 5000.*

### 3. Start the Dashboard (Frontend)
```bash
cd Frontend
bun dev
```
*Access the dashboard at `http://localhost:3000`.*

### 4. Start the Mobile App (Edge Device)
```bash
cd app
npx expo start
```
*Scan the QR code with the Expo Go app to run on a physical device or emulator.*

### 5. (Optional) Run Simulation Training
To train the RL model using SUMO:
```bash
cd FDRL
python train.py
```

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO
- **Frontend**: TypeScript, Next.js, Tailwind CSS
- **Mobile**: React Native, Expo, TensorFlow Lite
- **AI/ML**: PyTorch, TensorFlow, SUMO (Simulation)
- **Communication**: WebSockets, REST APIs

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes. Ensure you follow the project's coding standards and include tests where applicable.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.