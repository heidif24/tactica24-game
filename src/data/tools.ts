import type { Tool } from '../types';

export const ALL_TOOLS: Record<string, Tool> = {
  magnifier: { id: 'magnifier', name: 'Magnifying Glass', description: 'Reveal hidden details on physical evidence.', icon: '🔍', uses: 5, maxUses: 5 },
  notepad: { id: 'notepad', name: 'Field Notepad', description: 'Record observations and theories.', icon: '📝', uses: 99, maxUses: 99 },
  handcuffs: { id: 'handcuffs', name: 'Handcuffs', description: 'Restrain a suspect when the moment is right.', icon: '🔒', uses: 2, maxUses: 2 },
  lockpick: { id: 'lockpick', name: 'Lockpick Set', description: 'Open locked doors and containers quietly.', icon: '🔑', uses: 4, maxUses: 4 },
  mask: { id: 'mask', name: 'Balaclava', description: 'Hide your identity during infiltration.', icon: '🥷', uses: 3, maxUses: 3 },
  crowbar: { id: 'crowbar', name: 'Crowbar', description: 'Force entry or pry open sealed containers.', icon: '🪓', uses: 3, maxUses: 3 },
  radio: { id: 'radio', name: 'Police Radio', description: 'Call for backup (when available).', icon: '📻', uses: 3, maxUses: 3 },
  baton: { id: 'baton', name: 'Baton', description: 'Non-lethal force option.', icon: '🗡️', uses: 4, maxUses: 4 },
  flashlight: { id: 'flashlight', name: 'Tactical Flashlight', description: 'Illuminate dark areas and disorient.', icon: '🔦', uses: 8, maxUses: 8 },
  knife: { id: 'knife', name: 'Combat Knife', description: 'Last-resort close-quarters tool.', icon: '🗡️', uses: 2, maxUses: 2 },
  binoculars: { id: 'binoculars', name: 'Binoculars', description: 'Observe from a safe distance.', icon: '🔍', uses: 6, maxUses: 6 },
  medkit: { id: 'medkit', name: 'Field Medkit', description: 'Restore a limited amount of health.', icon: '🩺', uses: 2, maxUses: 2 },
  wrench: { id: 'wrench', name: 'Adjustable Wrench', description: 'Manipulate pipes and mechanical fixtures.', icon: '🔧', uses: 5, maxUses: 5 },
  'snake-cam': { id: 'snake-cam', name: 'Snake Camera', description: 'Inspect inside pipes and tight spaces.', icon: '📷', uses: 4, maxUses: 4 },
  laptop: { id: 'laptop', name: 'Portable Terminal', description: 'Hack systems and analyze digital evidence.', icon: '💻', uses: 6, maxUses: 6 },
  'usb-key': { id: 'usb-key', name: 'Encrypted USB', description: 'Extract or plant data payloads.', icon: '💾', uses: 3, maxUses: 3 },
  'signal-jammer': { id: 'signal-jammer', name: 'Signal Jammer', description: 'Block wireless communications temporarily.', icon: '📡', uses: 2, maxUses: 2 },
  stethoscope: { id: 'stethoscope', name: 'Stethoscope', description: 'Listen for heartbeats, leaks, or hidden mechanisms.', icon: '🩺', uses: 5, maxUses: 5 },
  syringe: { id: 'syringe', name: 'Emergency Syringe', description: 'Administer adrenaline or sedatives.', icon: '💉', uses: 2, maxUses: 2 },
  gloves: { id: 'gloves', name: 'Sterile Gloves', description: 'Handle forensic evidence without contamination.', icon: '🦞', uses: 8, maxUses: 8 },
};

export function createInventory(toolIds: string[]): import('../types').Tool[] {
  return toolIds.map(id => ({ ...ALL_TOOLS[id] }));
}
