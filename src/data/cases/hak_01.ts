import type { Case } from '../../types';

export const CASE_hak_01: Case = {
  id: 'hak-01',
  title: 'Signal Ghost',
  subtitle: 'Courier vanished',
  difficulty: 3,
  roleId: 'hacker',
  synopsis: 'Trace the signal through towers and servers. One loud scan and a van finds your door.',
  setting: 'Neon Grid / Tower 4',
  startRoom: 'desk',
  keyEvidence: ['ev-pkt', 'ev-tower'],
  solution: 'CFO honeypot routed the courier into a black site.',
  rewards: { xp: 200, title: 'Packet Phantom' },
  evidence: [
    { id: 'ev-pkt', name: 'Ghost packet', type: 'digital', description: 'Spoofed exit node.', isKey: true },
    { id: 'ev-tower', name: 'Tower 4 hop', type: 'digital', description: 'Last hop before drop.', isKey: true },
  ],
  rooms: [
    {
      id: 'desk', name: 'Your Desk', theme: 'server-room', mood: 'Screens. Courier last ping: Tower 4.',
      hotspots: [
        { id: 'term', x: 50, y: 50, label: 'Terminal', kind: 'object',
          actions: [
            { id: 'quiet', label: 'Passive capture', result: 'Ghost packet found.', revealsEvidence: ['ev-pkt'], requiresTool: 'tool-signal-tracer', scoreDelta: 30, consume: true },
            { id: 'scan', label: 'Port-scan tower mgmt', result: 'Honeypot.', isDeadly: true, deathMessage: 'Trace complete. Van arrives.' },
          ]},
        { id: 'to-tower', x: 85, y: 50, label: 'Tower 4', kind: 'exit', goesTo: 'tower', lockedBy: ['ev-pkt'] },
      ],
    },
    {
      id: 'tower', name: 'Tower 4 Node', theme: 'server-room', mood: 'Racks. Cold air. One admin console.',
      hotspots: [
        { id: 'rack', x: 40, y: 45, label: 'Core rack', kind: 'clue',
          actions: [{ id: 'hop', label: 'Read hop table', result: 'Last hop logged.', revealsEvidence: ['ev-tower'], scoreDelta: 25, consume: true }] },
        { id: 'phish', x: 70, y: 50, label: 'CFO mail gateway', kind: 'danger',
          actions: [
            { id: 'ph', label: 'Phish the CFO', result: 'Counter-phish.', isDeadly: true, deathMessage: 'Door kicks in.' },
            { id: 'mirror', label: 'Mirror silently', result: 'Path to black site clear.', scoreDelta: 25, consume: true },
          ]},
        { id: 'fin', x: 50, y: 75, label: 'Expose path', kind: 'person', lockedBy: ['ev-tower'],
          actions: [
            { id: 'drop', label: 'Drop proof to handlers', result: 'Courier recovered. Ghost closed.', winsCase: true, scoreDelta: 95 },
          ]},
        { id: 'back', x: 10, y: 50, label: 'Desk', kind: 'exit', goesTo: 'desk' },
      ],
    },
  ],
};
