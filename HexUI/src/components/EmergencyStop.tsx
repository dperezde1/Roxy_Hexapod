import { useState } from 'react';
import { AlertOctagon } from 'lucide-react';
import { mqttService } from '../services/mqttService';

export const EmergencyStop: React.FC = () => {
  const [isTriggered, setIsTriggered] = useState(false);

  const handleStop = () => {
    // Send immediate stop command to Pi
    mqttService.publish('hexapod/command/emergency', JSON.stringify({ action: 'EMERGENCY_STOP' }));
    setIsTriggered(true);
    
    // In a real app we might want a reset or leave it triggered until hardware reset
    setTimeout(() => {
      setIsTriggered(false);
    }, 3000);
  };

  return (
    <div className="panel panel-emergency" style={{ 
      background: 'transparent', border: 'none', boxShadow: 'none', padding: 0 
    }}>
      <button 
        onClick={handleStop}
        style={{
          width: '100%',
          height: '100%',
          minHeight: '120px',
          background: isTriggered ? 'var(--danger-color)' : 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
          color: 'white',
          border: '4px solid rgba(255,255,255,0.2)',
          borderRadius: '16px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          boxShadow: isTriggered 
            ? 'inset 0 0 20px rgba(0,0,0,0.5), 0 0 30px rgba(239, 68, 68, 0.8)'
            : '0 8px 32px rgba(239, 68, 68, 0.4), inset 0 4px 10px rgba(255,255,255,0.3)',
          transform: isTriggered ? 'scale(0.95)' : 'scale(1)',
          transition: 'all 0.1s cubic-bezier(0.4, 0, 0.2, 1)',
          cursor: 'pointer',
          animation: 'pulseGlow 2s infinite alternate',
          textTransform: 'uppercase',
          fontWeight: 900,
          letterSpacing: '2px',
          fontSize: '1.25rem'
        }}
        onMouseDown={e => e.currentTarget.style.transform = 'scale(0.95)'}
        onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
        onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
      >
        <AlertOctagon size={48} strokeWidth={2.5} />
        {isTriggered ? 'SYSTEM HALTED' : 'EMERGENCY STOP'}
      </button>
    </div>
  );
};
