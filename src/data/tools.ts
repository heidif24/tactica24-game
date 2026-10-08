import type { Tool } from '../types';

export const DEFAULT_TOOLS: Tool[] = [
  { id: 'tool-flashlight', name: 'Tactical Flashlight', description: 'Illuminate dark corners.', icon: '🔦', uses: 5, maxUses: 5 },
  { id: 'tool-notebook', name: 'Field Notebook', description: 'Record and connect clues.', icon: '📓', uses: 99, maxUses: 99 },
  { id: 'tool-magnifier', name: 'Forensic Magnifier', description: 'Reveal micro-details.', icon: '🔎', uses: 4, maxUses: 4 },
  { id: 'tool-forensic-kit', name: 'Forensic Kit', description: 'Collect traces and prints.', icon: '🧪', uses: 3, maxUses: 3 },
  { id: 'tool-pressure-gauge', name: 'Pressure Gauge', description: 'Measure system differentials.', icon: '📊', uses: 3, maxUses: 3 },
  { id: 'tool-signal-tracer', name: 'Signal Tracer', description: 'Track digital and radio signals.', icon: '📡', uses: 3, maxUses: 3 },
];
