import { useState, useEffect } from 'react';
import { Camera, Focus, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import type { TargetData } from '../types';

interface CameraFeedProps {
  streamUrl: string;
  targetData: TargetData;
}

export const CameraFeed: React.FC<CameraFeedProps> = ({ streamUrl, targetData }) => {
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // In a real scenario, this would check if the stream is accessible or just wait for load/error events on img
  useEffect(() => {
    // Reset states when url changes
    setHasError(false);
    setIsLoading(true);
  }, [streamUrl]);

  return (
    <>
      <style>
        {`
          @keyframes hudPulseSide {
            0% { opacity: 0.4; transform: translateY(-50%) scale(0.95); }
            50% { opacity: 1; transform: translateY(-50%) scale(1.05); }
            100% { opacity: 0.4; transform: translateY(-50%) scale(0.95); }
          }
          @keyframes hudPulseBehind {
            0% { opacity: 0.4; transform: translateX(-50%) scale(0.95); }
            50% { opacity: 1; transform: translateX(-50%) scale(1.05); }
            100% { opacity: 0.4; transform: translateX(-50%) scale(0.95); }
          }
        `}
      </style>
      <div className="panel panel-camera" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 0, overflow: 'hidden' }}>
        <div className="panel-header" style={{ padding: '1rem 1.5rem', marginBottom: 0, background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid var(--panel-border)' }}>
          <Camera size={20} className="text-accent" />
          <span>Primary Vision Feed</span>
        </div>
      
      <div style={{ flex: 1, position: 'relative', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {hasError ? (
          <div style={{ color: 'var(--danger-color)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <Camera size={48} opacity={0.5} />
            <span style={{ fontSize: '1.2rem', fontFamily: 'monospace' }}>NO SIGNAL DETECTED</span>
          </div>
        ) : (
          <>
            {isLoading && (
              <div style={{ position: 'absolute', color: 'var(--accent-color)', fontFamily: 'monospace', letterSpacing: '2px' }}>
                ESTABLISHING CONNECTION...
              </div>
            )}
            <img 
              src={streamUrl} 
              alt="MJPEG Camera Feed" 
              style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: isLoading ? 0.3 : 1, transition: 'opacity 0.5s ease' }}
              onLoad={() => setIsLoading(false)}
              onError={() => { setHasError(true); setIsLoading(false); }}
            />
          </>
        )}
        
        {/* Synthetic HUD Overlay overlaying the camera feed */}
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(circle, transparent 60%, rgba(0,0,0,0.6) 100%)' }}>
          {/* Center Crosshairs */}
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '40px', height: '40px', opacity: 0.5 }}>
            <div style={{ position: 'absolute', top: '0', left: '19px', width: '2px', height: '15px', background: 'rgba(59, 130, 246, 0.6)' }} />
            <div style={{ position: 'absolute', bottom: '0', left: '19px', width: '2px', height: '15px', background: 'rgba(59, 130, 246, 0.6)' }} />
            <div style={{ position: 'absolute', left: '0', top: '19px', width: '15px', height: '2px', background: 'rgba(59, 130, 246, 0.6)' }} />
            <div style={{ position: 'absolute', right: '0', top: '19px', width: '15px', height: '2px', background: 'rgba(59, 130, 246, 0.6)' }} />
          </div>

            {/* Out-of-frame tracking indicators */}
            {targetData.detected && targetData.direction === 'far-left' && (
              <div style={{ position: 'absolute', left: '2rem', top: '50%', display: 'flex', flexDirection: 'column', alignItems: 'center', color: 'var(--warning-color)', animation: 'hudPulseSide 2s infinite' }}>
                <ChevronLeft size={64} />
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold', fontSize: '1.2rem', textShadow: '0 0 10px rgba(245, 158, 11, 0.5)' }}>TURN LEFT</span>
              </div>
            )}
            
            {targetData.detected && targetData.direction === 'far-right' && (
              <div style={{ position: 'absolute', right: '2rem', top: '50%', display: 'flex', flexDirection: 'column', alignItems: 'center', color: 'var(--warning-color)', animation: 'hudPulseSide 2s infinite' }}>
                <ChevronRight size={64} />
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold', fontSize: '1.2rem', textShadow: '0 0 10px rgba(245, 158, 11, 0.5)' }}>TURN RIGHT</span>
              </div>
            )}

            {targetData.detected && targetData.direction === 'behind' && (
              <div style={{ position: 'absolute', bottom: '2rem', left: '50%', display: 'flex', flexDirection: 'column', alignItems: 'center', color: 'var(--danger-color)', animation: 'hudPulseBehind 2s infinite' }}>
                <RotateCcw size={48} />
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold', fontSize: '1.2rem', textShadow: '0 0 10px rgba(239, 68, 68, 0.5)', marginTop: '0.5rem' }}>TARGET BEHIND</span>
              </div>
            )}

            {/* Dynamic Target Box (In Frame) */}
            {targetData.detected && ['left', 'center', 'right'].includes(targetData.direction) && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: targetData.direction === 'left' ? '25%' : targetData.direction === 'right' ? '75%' : '50%',
                transform: 'translate(-50%, -50%)',
                width: '150px',
                height: '250px',
                border: '2px solid rgba(239, 68, 68, 0.8)',
                boxShadow: '0 0 15px rgba(239, 68, 68, 0.5), inset 0 0 15px rgba(239, 68, 68, 0.3)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-start',
                alignItems: 'center',
                paddingTop: '0.5rem',
                transition: 'left 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)' // Smooth tracking animation
              }}>
                <div style={{ 
                  background: 'rgba(239, 68, 68, 0.8)', 
                  color: 'white', 
                  padding: '2px 8px', 
                  fontSize: '0.75rem', 
                  fontFamily: 'monospace',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transform: 'translateY(-20px)'
                }}>
                  <Focus size={12} />
                  TARGET LOCK: {targetData.distanceMeter}m
                </div>
                
                {/* Corner reticles for aesthetics */}
                <div style={{ position: 'absolute', top: -5, left: -5, width: 15, height: 15, borderTop: '2px solid #ef4444', borderLeft: '2px solid #ef4444' }} />
                <div style={{ position: 'absolute', top: -5, right: -5, width: 15, height: 15, borderTop: '2px solid #ef4444', borderRight: '2px solid #ef4444' }} />
                <div style={{ position: 'absolute', bottom: -5, left: -5, width: 15, height: 15, borderBottom: '2px solid #ef4444', borderLeft: '2px solid #ef4444' }} />
                <div style={{ position: 'absolute', bottom: -5, right: -5, width: 15, height: 15, borderBottom: '2px solid #ef4444', borderRight: '2px solid #ef4444' }} />
              </div>
            )}
          </div>
      </div>
    </div>
    </>
  );
};
