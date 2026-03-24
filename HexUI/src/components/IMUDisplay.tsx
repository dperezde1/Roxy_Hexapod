import React, { useEffect, useState } from 'react';
import { Compass } from 'lucide-react';
import { mqttService } from '../services/mqttService';
import type { IMUData } from '../services/mqttService';

export const IMUDisplay: React.FC = () => {
  const [imuData, setImuData] = useState<IMUData>({
    pitch: 0, roll: 0, yaw: 0, accelX: 0, accelY: 0, accelZ: 0
  });

  useEffect(() => {
    const handleImuMessage = (_topic: string, message: Buffer) => {
      try {
        const data = JSON.parse(message.toString());
        setImuData(data);
      } catch (e) {
        console.error("Failed to parse IMU data", e);
      }
    };

    mqttService.subscribe('hexapod/telemetry/imu', handleImuMessage);

    return () => {
      mqttService.unsubscribe('hexapod/telemetry/imu', handleImuMessage);
    };
  }, []);

  const formatAngle = (angle: number) => angle.toFixed(1).padStart(5, ' ');
  const formatAccel = (accel: number) => accel.toFixed(2).padStart(5, ' ');

  return (
    <div className="panel panel-imu" style={{ padding: '0.75rem', gap: '0.4rem' }}>
      <div className="panel-header" style={{ marginBottom: '0.25rem', fontSize: '0.9rem' }}>
        <Compass size={16} className="text-accent" />
        <span>IMU Telemetry</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        
        {/* Attitude Indicators (Compact Row) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.4rem' }}>
          {[
            { label: 'PITCH', value: imuData.pitch, color: '#3b82f6' },
            { label: 'ROLL', value: imuData.roll, color: '#10b981' },
            { label: 'YAW', value: imuData.yaw, color: '#8b5cf6' }
          ].map(item => (
            <div key={item.label} style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '6px', padding: '0.3rem', textAlign: 'center', border: `1px solid rgba(255,255,255,0.05)` }}>
              <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', marginBottom: '0.1rem' }}>{item.label}</div>
              <div style={{ fontFamily: 'monospace', fontSize: '0.9rem', color: item.color, fontWeight: 'bold' }}>
                {Math.round(item.value)}°
              </div>
            </div>
          ))}
        </div>

        {/* Accelerometer data (Compact Horizontal Row) */}
        <div style={{ borderTop: '1px solid var(--panel-border)', paddingTop: '0.4rem' }}>
          <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', marginBottom: '0.2rem', textAlign: 'center' }}>ACCELERATION (G)</div>
          <div style={{ display: 'flex', justifyContent: 'space-around', fontFamily: 'monospace', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              <span style={{ color: '#ef4444' }}>X</span>
              <span>{imuData.accelX.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              <span style={{ color: '#10b981' }}>Y</span>
              <span>{imuData.accelY.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              <span style={{ color: '#3b82f6' }}>Z</span>
              <span>{imuData.accelZ.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
