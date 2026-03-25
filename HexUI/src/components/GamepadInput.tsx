import { useEffect, useState, useRef } from 'react';
import { Gamepad2 } from 'lucide-react';
import { mqttService } from '../services/mqttService';

interface axesPos {
  lx: number; ly: number; rx: number; ry: number;
}

export const GamepadInput: React.FC = () => {
  const [connected, setConnected] = useState(false);
  const [axes, setAxes] = useState<axesPos>({ lx: 0, ly: 0, rx: 0, ry: 0 });
  const [buttons, setButtons] = useState<{ [key: number]: boolean }>({});
  const [activeGait, setActiveGait] = useState<string>('TRIPOD');
  
  const requestRef = useRef<number>(0);
  const lastPublishTime = useRef<number>(0);
  const connectedRef = useRef(false);
  const lastButtonsRef = useRef<{ [key: number]: boolean }>({});

  // Poll gamepad state
  const updateGamepadState = () => {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    let isGamepadConnected = false;
    
    // Find the best gamepad (prioritize 'standard' mapping or those with activity)
    let selectedGamepad: Gamepad | null = null;
    for (const g of gamepads) {
      if (g && g.connected) {
        if (g.mapping === 'standard') {
          selectedGamepad = g;
          break;
        }
        if (!selectedGamepad && (g.axes.length > 0 || g.buttons.length > 0)) {
          selectedGamepad = g;
        }
      }
    }

    if (selectedGamepad) {
      const gamepad = selectedGamepad;
      isGamepadConnected = true;
      
      const a = gamepad.axes;
      const newAxes = {
        lx: a[0] || 0,
        ly: a[1] || 0,
        rx: (a.length > 4) ? (a[3] || a[2] || 0) : (a[2] || 0),
        ry: (a.length > 5) ? (a[4] || a[3] || 0) : (a[3] || 0)
      };

      if (gamepad.mapping === 'standard') {
          newAxes.rx = a[2] || 0;
          newAxes.ry = a[3] || 0;
      } else if (a.length >= 6) {
         newAxes.rx = a[3] || 0;
         newAxes.ry = a[4] || 0;
      }

      // Add deadzone
      const deadzone = 0.1;
      const applyDeadzone = (val: number) => Math.abs(val) > deadzone ? val : 0;
      
      const processedAxes = {
        lx: applyDeadzone(newAxes.lx),
        ly: applyDeadzone(newAxes.ly),
        rx: applyDeadzone(newAxes.rx),
        ry: applyDeadzone(newAxes.ry)
      };

      setAxes(processedAxes);

      const newButtons: { [key: number]: boolean } = {};
      gamepad.buttons.forEach((btn, index) => {
        newButtons[index] = btn.pressed;
      });
      
      setButtons(newButtons);
      
      // 🚀 Optimistic UI / Debouncing for Gait Switching (Button 3 = Triangle)
      const trianglePressed = !!newButtons[3];
      const wasTrianglePressed = !!lastButtonsRef.current[3];
      
      if (trianglePressed && !wasTrianglePressed) {
        console.log("Triangle pressed - toggling gait locally for feedback");
        setActiveGait(prev => prev === 'TRIPOD' ? 'RIPPLE' : 'TRIPOD');
      }

      // 🚀 Optimistic UI / Debouncing for Stair Climb (Button 0 = Cross/✖)
      const crossPressed = !!newButtons[0];
      const wasCrossPressed = !!lastButtonsRef.current[0];
      
      if (crossPressed && !wasCrossPressed) {
        console.log("Cross pressed - triggering Stair Climb locally for feedback");
        setActiveGait('STAIR CLIMB');
      }
      
      // Store current buttons for next debounce check
      lastButtonsRef.current = { ...newButtons };

      const now = Date.now();
      if (now - lastPublishTime.current > 50) {
        mqttService.publish('hexapod/command/controller', JSON.stringify({
          axes: processedAxes,
          buttons: newButtons,
          timestamp: now
        }));
        lastPublishTime.current = now;
      }
    }

    if (connectedRef.current !== isGamepadConnected) {
      connectedRef.current = isGamepadConnected;
      setConnected(isGamepadConnected);
      console.log(`Gamepad connection status changed: ${isGamepadConnected}`);
    }
    
    // Loop
    requestRef.current = requestAnimationFrame(updateGamepadState);
  };

  useEffect(() => {
    const onConnect = () => {
      console.log("Browser fired gamepadconnected event");
      // status will be updated by the polling loop
    };
    const onDisconnect = () => {
      console.log("Browser fired gamepaddisconnected event");
    };

    window.addEventListener('gamepadconnected', onConnect);
    window.addEventListener('gamepaddisconnected', onDisconnect);
    
    requestRef.current = requestAnimationFrame(updateGamepadState);
    
    const handleStateUpdate = (_topic: string, message: Buffer) => {
      try {
        const data = JSON.parse(message.toString());
        if (data.active_gait) {
          setActiveGait(data.active_gait);
        }
      } catch (e) {}
    };
    mqttService.subscribe('hexapod/telemetry/state', handleStateUpdate);

    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      window.removeEventListener('gamepadconnected', onConnect);
      window.removeEventListener('gamepaddisconnected', onDisconnect);
      mqttService.unsubscribe('hexapod/telemetry/state', handleStateUpdate);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Visualizer helper
  const renderThumbstick = (x: number, y: number, label: string) => {
    // Convert -1..1 to 0..100%
    const left = `${((x + 1) / 2) * 100}%`;
    const top = `${((y + 1) / 2) * 100}%`; // Note: Y axis is inverted on physical controllers vs screen
    
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', letterSpacing: '1px' }}>{label}</span>
        <div style={{ 
          width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(0,0,0,0.5)', 
          border: '2px solid rgba(255,255,255,0.1)', position: 'relative' 
        }}>
          {/* Crosshairs */}
          <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '1px', background: 'rgba(255,255,255,0.1)' }} />
          <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '1px', background: 'rgba(255,255,255,0.1)' }} />
          
          {/* Thumb */}
          <div style={{
            position: 'absolute', width: '24px', height: '24px', borderRadius: '50%',
            background: 'var(--accent-color)', boxShadow: '0 0 10px var(--accent-glow)',
            left, top, transform: 'translate(-50%, -50%)', transition: 'none'
          }} />
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', display: 'flex', gap: '0.5rem' }}>
          <span>X: {x.toFixed(2)}</span>
          <span>Y: {y.toFixed(2)}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="panel panel-controller">
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Gamepad2 size={20} className="text-accent" />
          <span>Teleoperation Link</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', fontWeight: 'bold' }}>
          <div style={{
            background: 'rgba(59, 130, 246, 0.2)',
            color: 'var(--accent-color)',
            padding: '4px 8px',
            borderRadius: '12px',
            marginRight: '1rem',
            border: '1px solid rgba(59, 130, 246, 0.5)'
          }}>
            MODE: {activeGait}
          </div>
          <span className={`dot ${connected ? 'connected' : 'disconnected'}`} />
          <span style={{ color: connected ? 'var(--success-color)' : 'var(--danger-color)' }}>
            {connected ? 'LINK ACTIVE' : 'NO CONTROLLER'}
          </span>
          {!connected && (
            <div style={{
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              fontStyle: 'italic',
              marginLeft: '0.5rem',
              animation: 'pulse 2s infinite'
            }}>
              (Press any button to activate)
            </div>
          )}
        </div>
      </div>
      
      <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', gap: '2rem' }}>
        {renderThumbstick(axes.lx, axes.ly, "LEFT STICK")}
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', alignSelf: 'center' }}>
          {[
            { label: '✖', color: '#3b82f6', name: 'Cross' },
            { label: '●', color: '#ef4444', name: 'Circle' },
            { label: '■', color: '#ec4899', name: 'Square' },
            { label: '▲', color: '#10b981', name: 'Triangle' }
          ].map((btn, idx) => (
            <div key={btn.name} style={{
              width: '42px', height: '42px', borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 'bold', fontSize: '1.1rem',
              background: buttons[idx] ? btn.color : 'rgba(0,0,0,0.5)',
              color: buttons[idx] ? '#fff' : 'rgba(255,255,255,0.2)',
              border: `2px solid ${buttons[idx] ? btn.color : 'rgba(255,255,255,0.05)'}`,
              boxShadow: buttons[idx] ? `0 0 15px ${btn.color}` : 'none',
              transition: 'all 0.1s',
              cursor: 'default'
            }}>
              {btn.label}
            </div>
          ))}
        </div>
        {renderThumbstick(axes.rx, axes.ry, "RIGHT STICK")}
      </div>
    </div>
  );
};
