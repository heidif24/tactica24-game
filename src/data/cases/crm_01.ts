import type { Case } from '../../types';

export const CASE_crm_01: Case = {
  id: 'crm-01',
  title: 'The Debt Mark',
  subtitle: 'Your face is on a list',
  difficulty: 2,
  roleId: 'criminal',
  synopsis: 'Move the docks and back rooms. Talk soft. Loud threats get you buried.',
  setting: 'Harbor District',
  startRoom: 'bar',
  keyEvidence: ['ev-name', 'ev-route'],
  solution: 'Leo set the mark to clear his own debt.',
  rewards: { xp: 160, title: 'Ghost Mark' },
  evidence: [
    { id: 'ev-name', name: 'Kira tip', type: 'testimony', description: 'Leo sold your name.', isKey: true },
    { id: 'ev-route', name: 'Drop route', type: 'document', description: 'Pier 7 at midnight.', isKey: true },
  ],
  rooms: [
    {
      id: 'bar', name: 'The Rust Hook', theme: 'alley', mood: 'Smoke. Low lights. Kira in the corner.',
      hotspots: [
        { id: 'kira', x: 60, y: 55, label: 'Kira', kind: 'person',
          actions: [
            { id: 'buy', label: 'Buy a drink, ask soft', result: 'Leo sold you. Pier 7.', revealsEvidence: ['ev-name'], scoreDelta: 25, consume: true },
            { id: 'threat', label: 'Threaten her loud', result: 'Hit team was listening.', isDeadly: true, deathMessage: 'You made a scene. The room empties with guns.' },
          ]},
        { id: 'to-pier', x: 90, y: 60, label: 'To docks', kind: 'exit', goesTo: 'pier', lockedBy: ['ev-name'] },
      ],
    },
    {
      id: 'pier', name: 'Pier 7', theme: 'street-night', mood: 'Fog. Crates. A tied figure.',
      hotspots: [
        { id: 'crate', x: 35, y: 60, label: 'Marked crate', kind: 'clue',
          actions: [{ id: 'open', label: 'Open quietly', result: 'Route sheet inside.', revealsEvidence: ['ev-route'], scoreDelta: 20, consume: true }] },
        { id: 'hostage', x: 65, y: 50, label: 'Tied courier', kind: 'person',
          actions: [
            { id: 'cut-smart', label: 'Cut free, stay low', result: 'He points to Leo boat.', scoreDelta: 15, consume: true },
            { id: 'cut-loud', label: 'Cut free and shout', result: 'Cornered rat protocol.', isDeadly: true, deathMessage: 'Snipers on the roofs.' },
          ]},
        { id: 'to-boat', x: 80, y: 40, label: 'Boat', kind: 'exit', goesTo: 'boat', lockedBy: ['ev-name', 'ev-route'] },
        { id: 'back', x: 10, y: 50, label: 'Bar', kind: 'exit', goesTo: 'bar' },
      ],
    },
    {
      id: 'boat', name: 'Leo Boat', theme: 'warehouse', mood: 'Engine idle. Leo waits.',
      hotspots: [
        { id: 'leo', x: 50, y: 50, label: 'Leo', kind: 'person',
          actions: [
            { id: 'deal', label: 'Show proof, deal out', result: 'He folds. Mark lifted.', winsCase: true, scoreDelta: 85 },
            { id: 'alone', label: 'Meet him alone, no exit', result: 'Friends below deck.', isDeadly: true, deathMessage: 'No stairs left.' },
          ]},
      ],
    },
  ],
};
