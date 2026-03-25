import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import './App.css';
import { mqttService } from './services/mqttService';

// Components
import { CameraFeed } from './components/CameraFeed';
import { IMUDisplay } from './components/IMUDisplay';
import { GamepadInput } from './components/GamepadInput';
import { EmergencyStop } from './components/EmergencyStop';
import { FootContacts } from './components/FootContacts';

function App() {
  const [mqttConnected, setMqttConnected] = useState(false);

  // 🛠️ CONFIGURATION: Set this to your Raspberry Pi's IP address
  const PI_IP = '172.20.10.2';
  const brokerUrl = `ws://${PI_IP}:9001`;

  useEffect(() => {
    // Attempt connection
    mqttService.connect(brokerUrl);

    // Give it a short delay to check connection state, or listen to an event emitter in a real app
    const interval = setInterval(() => {
      setMqttConnected(mqttService.getStatus());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      {/* Header Panel */}
      <div className="header">
        <h1 className="title">
          <Activity size={32} className="title-icon text-accent" />
          HEXUI COMMAND CENTER
        </h1>

        <div className="status-indicator">
          MQTT BROKER:
          <span className={`dot ${mqttConnected ? 'connected' : 'disconnected'}`} />
          <span style={{ color: mqttConnected ? 'var(--success-color)' : 'var(--danger-color)' }}>
            {mqttConnected ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* Main Grid Panels */}

      {/* 1. Camera Feed (Right, spanning full height) */}
      <CameraFeed streamUrl={`http://${PI_IP}:8080/?action=stream`} />

      {/* 2. IMU Orientation Data (Left Top) */}
      <IMUDisplay />

      {/* 3. Gamepad input publisher (Left Middle) */}
      <GamepadInput />

      {/* 4. Emergency Stop (Left Bottom) */}
      <EmergencyStop />

      {/* Floating Foot Contacts Widget (Overlay bottom right of camera) */}
      <div style={{ position: 'absolute', bottom: '150px', right: '30px', zIndex: 10 }}>
        <FootContacts />
      </div>

    </div>
  );
}

export default App;
