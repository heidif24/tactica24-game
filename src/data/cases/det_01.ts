import type { Case } from '../../types';

export const CASE_det_01: Case = {
  id: 'det-01',
  title: 'The Shadow Vault',
  subtitle: 'Bank heist · 02:17',
  difficulty: 1,
  roleId: 'detective',
  synopsis: 'Meridian Trust is silent. Vault open. $2.4M gone. Move through the bank — one wrong door and you do not leave.',
  setting: 'Meridian Trust Bank',
  startRoom: 'lobby',
  keyEvidence: ['ev-cam', 'ev-override', 'ev-print'],
  solution: 'Night guard used a master override with Vale.',
  rewards: { xp: 140, title: 'Shadow Breaker' },
  evidence: [
    { id: 'ev-cam', name: 'Cam loop timestamp', type: 'digital', description: '02:14–02:22 blackout matches vault open.', isKey: true },
    { id: 'ev-override', name: 'Master override log', type: 'document', description: 'Night-shift badge used the override.', isKey: true },
    { id: 'ev-print', name: 'Partial print on keypad', type: 'forensic', description: 'Matches night guard glove liner.', isKey: true },
    { id: 'ev-mud', name: 'Mud near side door', type: 'physical', description: 'Fresh track from alley.', isKey: false },
  ],
  rooms: [
    {
      id: 'lobby',
      name: 'Main Lobby',
      theme: 'bank-lobby',
      mood: 'Yellow tape. Rain on glass. Manager by the desk.',
      hotspots: [
        { id: 'mgr', x: 28, y: 58, label: 'Manager', kind: 'person', inspect: 'Hands shake. Vault cameras died. Guard was on break.' },
        { id: 'desk', x: 48, y: 62, label: 'Reception desk', kind: 'object',
          actions: [
            { id: 'search', label: 'Search drawers', result: 'Override log printout.', revealsEvidence: ['ev-override'], scoreDelta: 20, consume: true },
            { id: 'shove', label: 'Slam desk, demand answers', result: 'Panic. Security draws.', isDeadly: true, deathMessage: 'You escalated. A shot rings out in the lobby.' },
          ]},
        { id: 'cam', x: 72, y: 28, label: 'Security cam', kind: 'clue',
          actions: [
            { id: 'pull', label: 'Pull last night log', result: 'Loop from 02:14.', revealsEvidence: ['ev-cam'], scoreDelta: 25, consume: true },
          ]},
        { id: 'to-hall', x: 88, y: 50, label: 'Corridor', kind: 'exit', goesTo: 'corridor' },
        { id: 'to-street', x: 8, y: 70, label: 'Street', kind: 'exit', goesTo: 'street' },
      ],
    },
    {
      id: 'corridor',
      name: 'Vault Corridor',
      theme: 'bank-corridor',
      mood: 'Steel doors. Emergency lights. Air feels wrong.',
      hotspots: [
        { id: 'panel', x: 40, y: 45, label: 'Keypad panel', kind: 'clue',
          actions: [
            { id: 'dust', label: 'Dust for prints', result: 'Partial print under the lip.', revealsEvidence: ['ev-print'], requiresTool: 'tool-forensic-kit', scoreDelta: 30, consume: true },
            { id: 'force', label: 'Force the panel open', result: 'Sparks. Alarm trip.', isDeadly: true, deathMessage: 'Silent alarm. Response team treats you as hostile.' },
          ]},
        { id: 'to-vault', x: 78, y: 48, label: 'Vault door', kind: 'exit', goesTo: 'vault' },
        { id: 'to-lobby', x: 12, y: 50, label: 'Lobby', kind: 'exit', goesTo: 'lobby' },
        { id: 'dark-side', x: 55, y: 75, label: 'Dark side door', kind: 'danger',
          actions: [
            { id: 'enter', label: 'Open alone', result: 'Door seals.', isDeadly: true, deathMessage: 'Gas fills the chamber. Vale planned for the curious.' },
            { id: 'mark', label: 'Mark and leave', result: 'You note the seal. Smart.', scoreDelta: 10, consume: true },
          ]},
      ],
    },
    {
      id: 'vault',
      name: 'The Vault',
      theme: 'bank-vault',
      mood: 'Empty cages. Open door. Money ghosts.',
      hotspots: [
        { id: 'cage', x: 50, y: 55, label: 'Empty cage', kind: 'object', inspect: 'Cut locks. Professional work.' },
        { id: 'floor', x: 35, y: 72, label: 'Floor scuff', kind: 'clue', inspect: 'Wheel marks toward side exit.' },
        { id: 'accuse', x: 65, y: 40, label: 'Night guard (radio)', kind: 'person',
          lockedBy: ['ev-cam', 'ev-override', 'ev-print'],
          actions: [
            { id: 'arrest', label: 'Confront with evidence', result: 'He breaks. Vale paid him for the override.', winsCase: true, scoreDelta: 80 },
            { id: 'solo', label: 'Corner him alone, no backup', result: 'He panics.', isDeadly: true, deathMessage: 'Struggle. Your head hits steel.' },
          ]},
        { id: 'to-corr', x: 10, y: 50, label: 'Corridor', kind: 'exit', goesTo: 'corridor' },
      ],
    },
    {
      id: 'street',
      name: 'Side Alley',
      theme: 'street-night',
      mood: 'Rain. Dumpsters. One open service door.',
      hotspots: [
        { id: 'mud', x: 45, y: 68, label: 'Mud track', kind: 'clue',
          actions: [
            { id: 'bag', label: 'Bag sample', result: 'Mud logged.', revealsEvidence: ['ev-mud'], scoreDelta: 15, consume: true },
          ]},
        { id: 'chase', x: 70, y: 50, label: 'Shadow in fog', kind: 'danger',
          actions: [
            { id: 'run', label: 'Chase into fog', result: 'Ambush.', isDeadly: true, deathMessage: 'You run into a waiting blade.' },
            { id: 'radio', label: 'Call units, hold position', result: 'Units sweep. Empty. Good call.', scoreDelta: 15, consume: true },
          ]},
        { id: 'to-lobby', x: 20, y: 40, label: 'Bank entrance', kind: 'exit', goesTo: 'lobby' },
      ],
    },
  ],
};
