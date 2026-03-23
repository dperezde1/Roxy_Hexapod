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
    <div className="panel panel-imu">
      <div className="panel-header">
        <Compass size={20} className="text-accent" />
        <span>Inertial Measurement Unit</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', flex: 1, justifyContent: 'center' }}>
        
        {/* Attitude Indicators (Pitch, Roll, Yaw) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', textAlign: 'center' }}>
          {[
            { label: 'PITCH', value: imuData.pitch, color: '#3b82f6' }, // Blue
            { label: 'ROLL', value: imuData.roll, color: '#10b981' },  // Green
            { label: 'YAW', value: imuData.yaw, color: '#8b5cf6' }     // Purple
          ].map(item => (
            <div key={item.label} style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '1rem 0', border: `1px solid rgba(255,255,255,0.05)` }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', letterSpacing: '1px' }}>{item.label}</div>
              <div style={{ fontFamily: 'monospace', fontSize: '1.5rem', color: item.color, fontWeight: 'bold' }}>
                {formatAngle(item.value)}°
              </div>
              
              {/* Simple visual indicator block */}
              <div style={{ width: '80%', height: '4px', background: 'rgba(255,255,255,0.1)', margin: '0.5rem auto 0', borderRadius: '2px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ 
                  position: 'absolute', top: 0, bottom: 0, left: '50%', width: '50%', background: item.color,
                  transformOrigin: 'left',
                  transform: `scaleX(${Math.min(Math.max(item.value / 90, -1), 1)})`,
                  transition: 'transform 0.1s linear'
                }} />
              </div>
            </div>
          ))}
        </div>

        {/* Accelerometer data */}
        <div>
          <h4 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', borderBottom: '1px solid var(--panel-border)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>LINEAR ACCELERATION (g)</h4>
          <div style={{ fontFamily: 'monospace', fontSize: '1.1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#ef4444' }}>X-AXIS</span>
              <span>{formatAccel(imuData.accelX)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#10b981' }}>Y-AXIS</span>
              <span>{formatAccel(imuData.accelY)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#3b82f6' }}>Z-AXIS</span>
              <span>{formatAccel(imuData.accelZ)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
