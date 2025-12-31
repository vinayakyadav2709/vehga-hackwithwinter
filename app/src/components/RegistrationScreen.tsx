import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert } from 'react-native';
import { federatedService, IntersectionType, SignalPosition } from '../services/FederatedService';

interface RegistrationScreenProps {
    onRegistered: () => void;
}

export default function RegistrationScreen({ onRegistered }: RegistrationScreenProps) {
    const [name, setName] = useState('');
    const [ip, setIp] = useState('10.10.45.202');
    const [type, setType] = useState<IntersectionType>('4-way');
    const [signal, setSignal] = useState<SignalPosition>('Signal 1');
    const [loading, setLoading] = useState(false);

    const handleRegister = async () => {
        if (!name.trim()) {
            Alert.alert("Error", "Please enter a device name");
            return;
        }

        setLoading(true);
        federatedService.setConfig({
            name,
            serverIp: ip,
            intersectionType: type,
            position: signal
        });

        const success = await federatedService.register();
        setLoading(false);

        if (success) {
            onRegistered();
        } else {
            Alert.alert("Error", "Registration failed. Check IP and try again.");
        }
    };

    return (
        <View style={styles.container}>
            <Text style={styles.title}>MapServer Registry</Text>

            <View style={styles.inputGroup}>
                <Text style={styles.label}>Device Name</Text>
                <TextInput
                    style={styles.input}
                    value={name}
                    onChangeText={setName}
                    placeholder="e.g. Junction-Alpha"
                    placeholderTextColor="#666"
                />
            </View>

            <View style={styles.inputGroup}>
                <Text style={styles.label}>Server IP</Text>
                <TextInput
                    style={styles.input}
                    value={ip}
                    onChangeText={setIp}
                    keyboardType="numeric"
                />
            </View>

            <View style={styles.inputGroup}>
                <Text style={styles.label}>Intersection Type</Text>
                <View style={styles.radioContainer}>
                    <TouchableOpacity
                        style={[styles.radio, type === '3-way' && styles.radioActive]}
                        onPress={() => setType('3-way')}
                    >
                        <Text style={styles.radioText}>3-Way</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.radio, type === '4-way' && styles.radioActive]}
                        onPress={() => setType('4-way')}
                    >
                        <Text style={styles.radioText}>4-Way</Text>
                    </TouchableOpacity>
                </View>
            </View>

            <View style={styles.inputGroup}>
                <Text style={styles.label}>Your Signal Position</Text>
                <View style={styles.radioContainer}>
                    {(['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4'] as SignalPosition[]).map((sig) => (
                        <TouchableOpacity
                            key={sig}
                            style={[styles.radio, signal === sig && styles.radioActive]}
                            onPress={() => setSignal(sig)}
                        >
                            <Text style={styles.radioText}>{sig.replace('Signal ', 'S')}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            </View>

            <TouchableOpacity
                style={[styles.button, loading && styles.disabled]}
                onPress={handleRegister}
                disabled={loading}
            >
                <Text style={styles.buttonText}>{loading ? "Registering..." : "Connect"}</Text>
            </TouchableOpacity>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#1a1a1a',
        justifyContent: 'center',
        padding: 20,
    },
    title: {
        fontSize: 28,
        color: '#00ff00',
        fontWeight: 'bold',
        textAlign: 'center',
        marginBottom: 40,
        textTransform: 'uppercase',
        letterSpacing: 2
    },
    inputGroup: {
        marginBottom: 20
    },
    label: {
        color: '#888',
        marginBottom: 8,
        fontSize: 12,
        textTransform: 'uppercase'
    },
    input: {
        backgroundColor: '#333',
        color: 'white',
        padding: 15,
        borderRadius: 8,
        fontSize: 16,
        borderWidth: 1,
        borderColor: '#444'
    },
    radioContainer: {
        flexDirection: 'row',
        gap: 10
    },
    radio: {
        flex: 1,
        padding: 15,
        backgroundColor: '#333',
        alignItems: 'center',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#444'
    },
    radioActive: {
        backgroundColor: '#004400',
        borderColor: '#00ff00'
    },
    radioText: {
        color: 'white',
        fontWeight: 'bold'
    },
    button: {
        backgroundColor: '#00ff00',
        padding: 18,
        borderRadius: 8,
        alignItems: 'center',
        marginTop: 20
    },
    disabled: {
        opacity: 0.5
    },
    buttonText: {
        color: 'black',
        fontWeight: 'bold',
        fontSize: 16
    }
});
