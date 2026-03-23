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

  // Poll gamepad state
  const updateGamepadState = () => {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    let isGamepadConnected = false;

    // Grab first connected gamepad
    for (const gamepad of gamepads) {
      if (gamepad && gamepad.connected) {
        isGamepadConnected = true;
        
        const newAxes = {
          lx: gamepad.axes[0] || 0,
          ly: gamepad.axes[1] || 0,
          rx: gamepad.axes[2] || 0,
          ry: gamepad.axes[3] || 0
        };
        
        // Add deadzone
        const deadzone = 0.1;
        const applyDeadzone = (val: number) => Math.abs(val) > deadzone ? val : 0;
        
        newAxes.lx = applyDeadzone(newAxes.lx);
        newAxes.ly = applyDeadzone(newAxes.ly);
        newAxes.rx = applyDeadzone(newAxes.rx);
        newAxes.ry = applyDeadzone(newAxes.ry);

        setAxes(newAxes);

        const newButtons: { [key: number]: boolean } = {};
        gamepad.buttons.forEach((btn, index) => {
          newButtons[index] = btn.pressed;
        });
        
        // Since buttons update fast, we can optimize by only setting if changed... but for React state simple replace is fine for this demo
        setButtons(newButtons);

        // Publish to MQTT at max 20Hz (every 50ms)
        const now = Date.now();
        if (now - lastPublishTime.current > 50) {
          mqttService.publish('hexapod/command/controller', JSON.stringify({
            axes: newAxes,
            buttons: newButtons,
            timestamp: now
          }));
          lastPublishTime.current = now;
        }
        
        break; // Only care about first controller
      }
    }

    if (connected !== isGamepadConnected) {
      setConnected(isGamepadConnected);
    }
    
    // Loop
    requestRef.current = requestAnimationFrame(updateGamepadState);
  };

  useEffect(() => {
    window.addEventListener('gamepadconnected', () => setConnected(true));
    window.addEventListener('gamepaddisconnected', () => setConnected(false));
    
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
      window.removeEventListener('gamepadconnected', () => setConnected(true));
      window.removeEventListener('gamepaddisconnected', () => setConnected(false));
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
        </div>
      </div>
      
      <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', gap: '2rem' }}>
        {renderThumbstick(axes.lx, axes.ly, "LEFT STICK")}
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', alignSelf: 'center' }}>
          {/* Just mapping standard action buttons (A B X Y mapping index 0-3 usually) */}
          {['A', 'B', 'X', 'Y'].map((label, idx) => (
            <div key={label} style={{
              width: '40px', height: '40px', borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 'bold', fontFamily: 'monospace',
              background: buttons[idx] ? 'var(--accent-color)' : 'rgba(0,0,0,0.5)',
              color: buttons[idx] ? '#fff' : 'var(--text-secondary)',
              border: `1px solid ${buttons[idx] ? 'var(--accent-color)' : 'rgba(255,255,255,0.1)'}`,
              boxShadow: buttons[idx] ? '0 0 15px var(--accent-glow)' : 'none',
              transition: 'background 0.1s'
            }}>
              {label}
            </div>
          ))}
        </div>
        
        {renderThumbstick(axes.rx, axes.ry, "RIGHT STICK")}
      </div>
    </div>
  );
};
