import React, { useState } from 'react';
import { StyleSheet, View, StatusBar } from 'react-native';
import RegistrationScreen from './src/components/RegistrationScreen';
import Dashboard from './src/components/Dashboard';

export default function App() {
  const [isRegistered, setIsRegistered] = useState(false);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#000" />
      {!isRegistered ? (
        <RegistrationScreen onRegistered={() => setIsRegistered(true)} />
      ) : (
        <Dashboard />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
});
