export interface TargetData {
  detected: boolean;
  distanceMeter: number;
  confidence: number;
  direction: 'left' | 'right' | 'center' | 'far-left' | 'far-right' | 'behind' | 'none'; // Added direction for HUD
}
