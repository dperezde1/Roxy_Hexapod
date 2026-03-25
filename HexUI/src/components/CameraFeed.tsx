import { useState, useEffect } from 'react';
import { Camera } from 'lucide-react';

interface CameraFeedProps {
  streamUrl: string;
}

export const CameraFeed: React.FC<CameraFeedProps> = ({ streamUrl }) => {
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // In a real scenario, this would check if the stream is accessible or just wait for load/error events on img
  useEffect(() => {
    // Reset states when url changes
    setHasError(false);
    setIsLoading(true);
  }, [streamUrl]);

  return (
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
        
        {/* Vignette Overlay with Center Crosshairs */}
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(circle, transparent 60%, rgba(0,0,0,0.6) 100%)' }}>
          {/* Center Crosshairs */}
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '40px', height: '40px', opacity: 0.5 }}>
            <div style={{ position: 'absolute', top: '0', left: '19px', width: '2px', height: '15px', background: 'rgba(59, 130, 246, 0.6)' }} />
            <div style={{ position: 'absolute', bottom: '0', left: '19px', width: '2px', height: '15px', background: 'rgba(59, 130, 246, 0.6)' }} />
            <div style={{ position: 'absolute', left: '0', top: '19px', width: '15px', height: '2px', background: 'rgba(59, 130, 246, 0.6)' }} />
            <div style={{ position: 'absolute', right: '0', top: '19px', width: '15px', height: '2px', background: 'rgba(59, 130, 246, 0.6)' }} />
          </div>
        </div>
      </div>
    </div>
  );
};

