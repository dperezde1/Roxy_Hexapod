import React, { useEffect, useState } from 'react';
import { Footprints } from 'lucide-react';
import { mqttService } from '../services/mqttService';

export const FootContacts: React.FC = () => {
  const [contacts, setContacts] = useState<number[]>([0, 0, 0, 0, 0, 0]);

  useEffect(() => {
    const handleMessage = (_topic: string, message: Buffer) => {
      try {
        const data = JSON.parse(message.toString());
        if (data.contacts && Array.isArray(data.contacts)) {
          setContacts(data.contacts);
        }
      } catch (e) {
        // ignore JSON parse errors silently or log locally
      }
    };

    mqttService.subscribe('hexapod/telemetry/feet', handleMessage);

    return () => {
      mqttService.unsubscribe('hexapod/telemetry/feet', handleMessage);
    };
  }, []);

  // Map 1-6 legs to a 2-column hexapod layout:
  // L1(0) - R1(1)   (Wait, in hexapod_config.py: Leg1 is Front-Right, Leg6 is Front-Left. Let's arrange logically)
  // Left: L6, L5, L4.   Right: L1, L2, L3.
  // We'll just display them safely in a 2-column or list view.
  // The layout below assumes indexes:
  // Front:  (L6) [5]   [0] (L1)
  // Mid:    (L5) [4]   [1] (L2)
  // Back:   (L4) [3]   [2] (L3)

  const footStyle = (isContact: boolean) => ({
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    border: `2px solid ${isContact ? 'var(--success-color)' : 'rgba(255,255,255,0.2)'}`,
    background: isContact ? 'var(--success-glow)' : 'transparent',
    boxShadow: isContact ? '0 0 10px var(--success-glow)' : 'none',
    transition: 'all 0.1s ease-in-out'
  });

  return (
    <div className="panel" style={{ padding: '1rem', minWidth: '150px' }}>
      <div className="panel-header" style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>
        <Footprints size={16} className="text-accent" />
        <span>Contacts</span>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem' }}>
        {/* Front */}
        <div style={{ display: 'flex', gap: '2rem' }}>
          <div style={footStyle(contacts[5] === 1)} title="Front-Left (L6)" />
          <div style={footStyle(contacts[0] === 1)} title="Front-Right (L1)" />
        </div>
        
        {/* Middle */}
        <div style={{ display: 'flex', gap: '2.5rem' }}>
          <div style={footStyle(contacts[4] === 1)} title="Mid-Left (L5)" />
          <div style={footStyle(contacts[1] === 1)} title="Mid-Right (L2)" />
        </div>
        
        {/* Back */}
        <div style={{ display: 'flex', gap: '2rem' }}>
          <div style={footStyle(contacts[3] === 1)} title="Back-Left (L4)" />
          <div style={footStyle(contacts[2] === 1)} title="Back-Right (L3)" />
        </div>
      </div>
    </div>
  );
};
