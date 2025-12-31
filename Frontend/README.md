# Vegha Dashboard: City-Wide Observability & Control

> [!TIP]
> **Operational Realism**: This dashboard is designed for **Municipal Authorities** and **Traffic Controllers**, not just developers.

## 📌 Component Purpose
The Frontend provides a "God Mode" view of the city's traffic network. It visualizes the invisible logic of the **Decentralized AI**, allowing operators to intervene only when necessary.

## 🖥️ Key Operational Features

### 1. Real-Time Congestion Response (Map View)
*   **Live Heatmaps**: Visualizes density across the city using data from edge sensors.
*   **Junction Health**: Color-coded markers (Green/Red) indicate the operational status of hardware at each intersection.

### 2. Event Management Console
*   **Traffic Pattern Adaptation**: Operators can switch entire zones between "Morning Rush", "School Hours", or "Night Mode" with a single click.
*   **Emergency Overrides**: Dedicated interface for police/ambulance dispatchers to force signals green along a specific route.

### 3. Business Intelligence & Analytics
*   **TCO Monitoring**: Estimated fuel saved and carbon footprint reduction display.
*   **Performance Metrics**: Graphs showing average wait time reduction vs. traditional fixed-timers.

## 🛠️ Technical Implementation
*   **Next.js**: Server-side rendering for fast load times on low-end government hardware.
*   **WebSockets**: Sub-second latency for live traffic feeds.
*   **Component Modularity**: Built with a design system that allows easy white-labeling for different municipalities.

## 🚀 Round 2 Enhancements
*   **AR Overlay**: Future integration with CCTV feeds to overlay AI detection boxes directly on the video stream.
*   **Mobile Command App**: A lightweight version for field officers (Traffic Police) to control signals from their phone.