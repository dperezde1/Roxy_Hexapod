import { useEffect } from 'react';
import { Target } from 'lucide-react';
import type { TargetData } from '../types';

interface HumanDetectionMockProps {
  targetData: TargetData;
  setTargetData: React.Dispatch<React.SetStateAction<TargetData>>;
}

export const HumanDetectionMock: React.FC<HumanDetectionMockProps> = ({ targetData, setTargetData }) => {
  // Simulate incoming theoretical sensor data
  useEffect(() => {
    const interval = setInterval(() => {
      // 30% chance to detect something
      const isDetected = Math.random() > 0.7;
      
      // Include out of frame directions
      const directions: ('left' | 'center' | 'right' | 'far-left' | 'far-right' | 'behind')[] = ['left', 'center', 'right', 'far-left', 'far-right', 'behind'];
      
      setTargetData({
        detected: isDetected,
        distanceMeter: isDetected ? +(Math.random() * 10 + 1).toFixed(2) : 0, // 1 to 11 meters
        confidence: isDetected ? +(Math.random() * 40 + 60).toFixed(1) : 0, // 60% to 100%
        direction: isDetected ? directions[Math.floor(Math.random() * directions.length)] : 'none'
      });
    }, 6000); // Slowed down to 6 seconds for demo purposes

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="panel panel-mock">
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Target size={20} className={targetData.detected ? "text-danger" : "text-accent"} />
          <span>Target Acquisition (mmWave)</span>
        </div>
        <div style={{ fontSize: '0.65rem', background: 'rgba(59, 130, 246, 0.2)', color: 'var(--accent-color)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--accent-color)' }}>
          THROUGH-CONCRETE
        </div>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1, justifyContent: 'center' }}>
        <div style={{ 
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
          padding: '0.75rem', borderRadius: '12px',
          background: targetData.detected ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
          border: `1px solid ${targetData.detected ? 'var(--danger-color)' : 'var(--success-color)'}`,
          transition: 'all 0.3s ease'
        }}>
          {targetData.detected ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ color: 'var(--danger-color)', fontWeight: 'bold', fontSize: '1rem', letterSpacing: '1px' }}>HUMAN DETECTED</span>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem', fontFamily: 'monospace' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>DIST</span>
                  <span style={{ fontSize: '1.1rem' }}>{targetData.distanceMeter}m</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>CONF</span>
                  <span style={{ fontSize: '1.1rem' }}>{targetData.confidence}%</span>
                </div>
              </div>
              <div style={{ color: 'var(--warning-color)', fontSize: '0.875rem', fontWeight: 'bold', marginTop: '0.5rem' }}>
                TARGET AT {targetData.direction.toUpperCase()}
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--success-color)', fontWeight: 'bold', fontSize: '1.2rem', letterSpacing: '2px', textAlign: 'center' }}>
              AREA CLEAR
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem', fontFamily: 'monospace' }}>SCANNING (MAX 11m)...</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
