import React, { useState, useEffect, useCallback, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, Dimensions, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useVideoPlayer, VideoView } from 'expo-video';
import * as ImagePicker from 'expo-image-picker';
import * as VideoThumbnails from 'expo-video-thumbnails';
import { federatedService, NeighborData } from '../services/FederatedService';
import { useYoloModel, runYoloInference } from '../services/YoloInference';

const { width, height } = Dimensions.get('window');

// --- Types & Constants ---
type SignalState = 'RED' | 'YELLOW' | 'GREEN';
interface SignalCardProps {
    name: string;
    ip: string;
    state: SignalState;
    count: number;
}

// --- Traffic Light Component ---
const TrafficLight = ({ state, size = 'small' }: { state: SignalState, size?: 'small' | 'large' }) => {
    const s = size === 'large' ? 24 : 14;
    const p = size === 'large' ? 10 : 5;

    // Dimming logic
    const getOp = (target: SignalState) => state === target ? 1.0 : 0.2;

    return (
        <View style={{
            backgroundColor: '#111',
            padding: p,
            borderRadius: 8,
            borderWidth: 2,
            borderColor: '#333',
            alignItems: 'center',
            gap: p
        }}>
            <View style={{ width: s, height: s, borderRadius: s / 2, backgroundColor: '#ff3333', opacity: getOp('RED'), borderWidth: 1, borderColor: '#500' }} />
            <View style={{ width: s, height: s, borderRadius: s / 2, backgroundColor: '#ffff33', opacity: getOp('YELLOW'), borderWidth: 1, borderColor: '#550' }} />
            <View style={{ width: s, height: s, borderRadius: s / 2, backgroundColor: '#33ff33', opacity: getOp('GREEN'), borderWidth: 1, borderColor: '#050' }} />
        </View>
    );
};

// --- Signal Card ---
const SignalCard = ({ name, ip, state, count }: SignalCardProps) => {
    const borderColor = state === 'GREEN' ? '#00ff00' : state === 'YELLOW' ? '#ffff00' : '#333';
    return (
        <View style={[styles.signalCard, { borderColor: borderColor }]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardName}>{name}</Text>
                <Text style={styles.cardIp}>{ip}</Text>
            </View>
            <View style={styles.cardBody}>
                <TrafficLight state={state} size="small" />
                <View style={{ alignItems: 'center', marginLeft: 15 }}>
                    <Text style={styles.cardCount}>{count}</Text>
                    <Text style={styles.cardUnit}>VEHICLES</Text>
                    <Text style={{ fontSize: 16 }}>🚗</Text>
                </View>
            </View>
        </View>
    );
};

export default function Dashboard() {
    // --- State ---
    const [connectedMode, setConnectedMode] = useState(true);
    const [serverIp, setServerIp] = useState("10.10.45.202");
    const [statusLog, setStatusLog] = useState<string[]>([]);

    // Video
    const [videoSource, setVideoSource] = useState<string | null>(null);
    const player = useVideoPlayer(videoSource, player => {
        player.loop = true;
        player.muted = true;
        player.play();
    });

    // Stats
    const [lastHash, setLastHash] = useState("-");
    const [lastUpdate, setLastUpdate] = useState<{ time: number | string, size: number }>({ time: "-", size: 0 });



    // Main Signal
    const [mySignal, setMySignal] = useState<SignalState>('RED');
    const [myCount, setMyCount] = useState(0);
    const [aiOutput, setAiOutput] = useState("{}");

    // Neighbors
    const [neighbors, setNeighbors] = useState<NeighborData[]>([
        { name: "N1", ip: "10.10.X.X", signal: 'RED', count: 12 },
        { name: "N2", ip: "10.10.X.X", signal: 'RED', count: 8 },
        { name: "N3", ip: "10.10.X.X", signal: 'RED', count: 5 },
    ]);



    const addLog = (msg: string) => {
        setStatusLog(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev.slice(0, 50)]);
    };

    // --- 1. FEDERATED SERVICE (Connected Mode) ---
    useEffect(() => {
        if (connectedMode) {
            federatedService.connect();

            federatedService.onStatusChange = (msg) => {
                if (msg.includes("Update Sent")) {
                    setLastUpdate({ time: Date.now(), size: 2048 + Math.floor(Math.random() * 100) });
                }
                addLog(`🌐 ${msg}`);
            };
            federatedService.onWeightsUpdate = (w, hash) => setLastHash(hash.substring(0, 10));

            federatedService.onNeighborUpdate = (newData) => {
                setNeighbors(prev => {
                    const updated = [...prev];
                    newData.forEach((d, i) => { if (updated[i]) updated[i] = { ...d }; });
                    return updated;
                });
            };
        } else {
            federatedService.disconnect();
        }
    }, [connectedMode]);

    // Load YOLO Model
    const { model, modelState } = useYoloModel();

    // --- Refs for Control Loop ---
    const myCountRef = useRef(myCount);
    const neighborsRef = useRef(neighbors);
    const connectedRef = useRef(connectedMode);
    const mySignalRef = useRef(mySignal);

    useEffect(() => { myCountRef.current = myCount; }, [myCount]);
    useEffect(() => { neighborsRef.current = neighbors; }, [neighbors]);
    useEffect(() => { connectedRef.current = connectedMode; }, [connectedMode]);
    useEffect(() => { mySignalRef.current = mySignal; }, [mySignal]);

    // --- LOGIC: CONTROL LOOP ---
    // --- LOGIC: CONTROL LOOP (1 Second Tick) ---
    useEffect(() => {
        // State Machine Vars
        let timer = 0;
        let phase: 'GREEN' | 'YELLOW' = 'GREEN';
        let currentStates = [0, 0, 0, 0]; // [Me, N1, N2, N3]. 1, 0, -1

        // Safety Validator (At least 3 zeros)
        const validateTrafficRule = (states: number[]) => {
            const zeros = states.filter(s => s === 0).length;
            if (zeros < 3) {
                addLog(`⚠️ CRITICAL: Rule Violation! Resetting.`);
                return false;
            }
            return true;
        };

        const updateSignals = (newStates: number[]) => {
            if (!validateTrafficRule(newStates)) newStates = [0, 0, 0, 0];

            // "if array is same dont do anything" check implicitly handled by logic flow, 
            // but we can add optimization:
            const isSame = newStates.every((v, i) => v === currentStates[i]);
            if (isSame) return; // Skip update if identical

            currentStates = [...newStates];

            const stateMap: Record<number, SignalState> = { 1: 'GREEN', 0: 'RED', '-1': 'YELLOW' };
            setMySignal(stateMap[newStates[0]]);
            setNeighbors(prev => prev.map((n, i) => ({
                ...n,
                signal: stateMap[newStates[i + 1]]
            })));
        };

        const tick = () => {
            timer++;

            // Helper to get name
            const getName = (idx: number) => idx === 0 ? "ME" : (neighborsRef.current[idx - 1]?.name || `N${idx}`);

            // 1. Identify Target (Max Count)
            const counts = [myCountRef.current, ...neighborsRef.current.map(n => n.count)];
            let maxIndex = 0;
            let maxVal = counts[0];
            for (let i = 1; i < 4; i++) {
                if (counts[i] > maxVal) {
                    maxVal = counts[i];
                    maxIndex = i;
                }
            }

            // 2. State Machine
            const currentGreenIndex = currentStates.indexOf(1);

            if (currentStates.every(s => s === 0)) {
                // Initialize: First Run / Reset
                const startState = [0, 0, 0, 0];
                startState[maxIndex] = 1;
                updateSignals(startState);
                phase = 'GREEN';
                timer = 0;
                addLog(`🚀 Start: ${getName(maxIndex)}`);
                return;
            }

            if (phase === 'GREEN') {
                // Check if switch needed
                if (currentGreenIndex !== maxIndex) {
                    if (timer >= 3) {
                        // Switch Initiated: Turn YELLOW
                        addLog(`⚖️ Switch: ${getName(currentGreenIndex)} -> YELLOW`);

                        const nextState = [...currentStates];
                        nextState[currentGreenIndex] = -1; // Yellow
                        updateSignals(nextState);

                        phase = 'YELLOW';
                        timer = 0;
                    }
                    // else: Wait (Minimum Green Time)
                } else {
                    // Holding Green, No Change Needed
                    // Reset timer to keep it clean or let it grow? 
                    // User said "keep loop count to manage it", so growing is fine.
                }
            }
            else if (phase === 'YELLOW') {
                if (timer >= 1) {
                    // Complete Switch: Turn current RED, target GREEN
                    addLog(`🟢 Green: ${getName(maxIndex)}`);

                    const nextState = [0, 0, 0, 0]; // Reset all to Red first/implicit
                    // Actually, we must ensure we don't violate rule logic mid-update?
                    // New state is: Everyone Red except Target.

                    // currentStates has -1 at old Green pos.
                    // We want 0 at old Green pos, 1 at new Target pos.

                    nextState[maxIndex] = 1;
                    updateSignals(nextState);

                    phase = 'GREEN';
                    timer = 0;
                }
            }

            // Broadcast Status if Connected
            if (connectedRef.current) {
                // Note: we use refs for latest state
                federatedService.sendStatus(mySignalRef.current, myCountRef.current);
            }
        };

        const interval = setInterval(tick, 1000);
        return () => clearInterval(interval);
    }, []);

    // --- SIMULATION (Disconnected Mode) ---
    useEffect(() => {
        if (connectedMode) return;
        const interval = setInterval(() => {
            // Update neighbor counts with some randomness to simulate traffic
            setNeighbors(prev => prev.map(n => ({
                ...n,
                count: Math.max(0, Math.min(50, n.count + (Math.floor(Math.random() * 7) - 3)))
            })));
        }, 2000);
        return () => clearInterval(interval);
    }, [connectedMode]);

    // --- REAL YOLO INFERENCE ---
    useEffect(() => {
        const interval = setInterval(async () => {
            if (!videoSource || !model || modelState !== 'loaded') {
                if (videoSource) setMyCount(0);
                setAiOutput(modelState === 'loading' ? "Loading YOLO Model..." : "Waiting for video");
            } else {
                try {
                    const { uri } = await VideoThumbnails.getThumbnailAsync(videoSource, {
                        time: Date.now() % 10000,
                    });
                    const { count, detections } = await runYoloInference(model, uri, 0.30);
                    setMyCount(count);
                    setAiOutput(JSON.stringify({
                        detected: count,
                        detections: detections.map(d => `${d.label} (${(d.score * 100).toFixed(0)}%)`)
                    }, null, 2));
                } catch (error) { setMyCount(0); }
            }
        }, 1000);
        return () => clearInterval(interval);
    }, [videoSource, model, modelState]);


    // Helper for "Seconds Ago"
    const getTimeAgo = () => {
        if (lastUpdate.time === "-") return "-";
        const diff = Math.floor((Date.now() - (lastUpdate.time as number)) / 1000);
        return `${diff}s ago`;
    };

    const pickVideo = async () => {
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Videos,
        });
        if (!result.canceled) setVideoSource(result.assets[0].uri);
    };

    return (
        <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
            <View style={styles.verticalStatusBar}>
                <View style={styles.statusRow}>
                    <Text style={styles.statusLabel}>SERVER IP:</Text>
                    <Text style={styles.statusValue}>{serverIp}</Text>
                </View>
                <View style={styles.statusRow}>
                    <Text style={styles.statusLabel}>HASH:</Text>
                    <Text style={styles.statusValue}>{lastHash}</Text>
                </View>
                <View style={styles.statusRow}>
                    <Text style={styles.statusLabel}>LAST UPD:</Text>
                    <Text style={styles.statusValue}>{getTimeAgo()}</Text>
                </View>
                <View style={styles.statusRow}>
                    <Text style={styles.statusLabel}>SIZE:</Text>
                    <Text style={styles.statusValue}>{lastUpdate.size} B</Text>
                </View>
                <View style={styles.statusRow}>
                    <Text style={styles.statusLabel}>MODE:</Text>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Text style={{ color: connectedMode ? '#0f0' : '#666', fontSize: 10, marginRight: 5 }}>
                            {connectedMode ? "CONNECTED" : "DISCONNECTED"}
                        </Text>
                        <Switch
                            value={connectedMode}
                            onValueChange={setConnectedMode}
                            trackColor={{ false: '#333', true: '#004400' }}
                            thumbColor={connectedMode ? '#00ff00' : '#888'}
                            style={{ transform: [{ scaleX: .7 }, { scaleY: .7 }] }}
                        />
                    </View>
                </View>
            </View>

            <View style={styles.mainArea}>
                {/* Left: Video */}
                <View style={[styles.videoContainer, { borderColor: mySignal === 'GREEN' ? '#00ff00' : mySignal === 'YELLOW' ? '#ffff00' : '#333' }]}>
                    {videoSource ? (
                        <VideoView style={styles.video} player={player} contentFit="contain" nativeControls={false} />
                    ) : (
                        <TouchableOpacity style={styles.pickBtn} onPress={pickVideo}>
                            <Text style={styles.pickText}>Select Video</Text>
                        </TouchableOpacity>
                    )}
                    <View style={styles.overlay}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 15 }}>
                            <View>
                                <Text style={styles.overlayText}>MY SIGNAL</Text>
                                <Text style={styles.countBig}>{myCount}</Text>
                                <Text style={styles.carIcon}>🚗</Text>
                            </View>
                            <TrafficLight state={mySignal} size="large" />
                        </View>
                    </View>
                </View>

                {/* Right: Neighbors */}
                <View style={styles.neighborsContainer}>
                    {neighbors.map((n, i) => (
                        <SignalCard
                            key={i}
                            name={n.name || `Neighbor ${i + 1}`}
                            ip={n.ip}
                            state={n.signal}
                            count={n.count}
                        />
                    ))}
                </View>
            </View>

            <View style={styles.bottomSection}>
                <View style={styles.aiPanel}>
                    <Text style={styles.sectionTitle}>AI INFERENCE NODE (YOLO)</Text>
                    <ScrollView>
                        <Text style={styles.code}>{aiOutput}</Text>
                    </ScrollView>
                </View>
                <View style={styles.logsPanel}>
                    <Text style={styles.sectionTitle}>SYSTEM LOGS</Text>
                    <ScrollView ref={ref => ref?.scrollToEnd()} onContentSizeChange={() => { }}>
                        {statusLog.map((l, i) => <Text key={i} style={styles.logText}>{l}</Text>)}
                    </ScrollView>
                </View>
            </View>
        </SafeAreaView >
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#050505' },

    verticalStatusBar: { margin: 5, backgroundColor: '#111', borderRadius: 8, padding: 8, borderWidth: 1, borderColor: '#333' },
    statusRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 },
    statusLabel: { color: '#888', fontSize: 10, fontWeight: 'bold' },
    statusValue: { color: '#fff', fontSize: 12, fontFamily: 'monospace', fontWeight: 'bold' },

    mainArea: { flexDirection: 'row', height: height * 0.45, marginBottom: 5, paddingHorizontal: 5 },
    videoContainer: { flex: 2, borderWidth: 3, marginRight: 5, borderRadius: 8, overflow: 'hidden', backgroundColor: '#000', justifyContent: 'center' },
    video: { width: '100%', height: '100%' },
    pickBtn: { alignSelf: 'center', padding: 20, backgroundColor: '#222', borderRadius: 8 },
    pickText: { color: '#888' },

    overlay: { position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(0,0,0,0.85)', padding: 10, borderRadius: 8, borderWidth: 1, borderColor: '#333' },
    overlayText: { color: '#bbb', fontSize: 10, fontWeight: 'bold', marginBottom: 2 },
    countBig: { color: '#fff', fontSize: 32, fontWeight: 'bold' },
    carIcon: { fontSize: 24, marginTop: -5 },

    neighborsContainer: { flex: 1, justifyContent: 'space-between' },
    signalCard: { flex: 1, borderWidth: 2, borderRadius: 8, marginBottom: 5, backgroundColor: '#111', padding: 5, justifyContent: 'center' },
    cardHeader: { borderBottomWidth: 1, borderColor: '#333', paddingBottom: 4, marginBottom: 5, flexDirection: 'row', justifyContent: 'space-between' },
    cardName: { color: '#fff', fontSize: 12, fontWeight: 'bold' },
    cardIp: { color: '#00ff00', fontSize: 10, fontWeight: 'bold' },
    cardBody: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around' },
    cardCount: { color: '#fff', fontSize: 24, fontWeight: 'bold' },
    cardUnit: { color: '#666', fontSize: 8 },

    bottomSection: { flex: 1, flexDirection: 'row' },
    aiPanel: { flex: 1, borderRightWidth: 1, borderColor: '#333', padding: 10, backgroundColor: '#0a0a0a' },
    logsPanel: { flex: 1.5, padding: 10, backgroundColor: '#000' },
    sectionTitle: { color: '#00ff00', fontSize: 10, marginBottom: 8, fontWeight: 'bold', letterSpacing: 1 },
    code: { color: '#00ff00', fontFamily: 'monospace', fontSize: 10 },
    logText: { color: '#888', fontFamily: 'monospace', fontSize: 9, marginBottom: 3 }
});
