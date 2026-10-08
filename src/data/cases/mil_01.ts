import type { Case } from '../../types';

export const CASE_mil_01: Case = {
  id: 'mil-01',
  title: 'Grid Seven',
  subtitle: '12-minute window',
  difficulty: 3,
  roleId: 'military',
  synopsis: 'Cross the grid, hit the relay, extract. Open ground is a death sentence.',
  setting: 'Grid Seven AO',
  startRoom: 'op',
  keyEvidence: ['ev-lane', 'ev-relay'],
  solution: 'North wash route under sniper lane.',
  rewards: { xp: 220, title: 'Grid Ghost' },
  evidence: [
    { id: 'ev-lane', name: 'Sniper lane', type: 'document', description: 'Ridge zeroed east-west.', isKey: true },
    { id: 'ev-relay', name: 'Relay code', type: 'digital', description: 'Shutdown sequence.', isKey: true },
  ],
  rooms: [
    {
      id: 'op', name: 'OP Overwatch', theme: 'military-camp', mood: 'Dust. Scope glint on the ridge.',
      hotspots: [
        { id: 'scope', x: 60, y: 35, label: 'Spotter scope', kind: 'clue',
          actions: [{ id: 'glass', label: 'Glass the ridge', result: 'Lane mapped.', revealsEvidence: ['ev-lane'], scoreDelta: 25, consume: true }] },
        { id: 'sprint', x: 50, y: 70, label: 'Ridge path', kind: 'danger',
          actions: [
            { id: 'run', label: 'Sprint the ridge', result: 'Sniper.', isDeadly: true, deathMessage: 'Lane was zeroed.' },
            { id: 'wash', label: 'Take north wash', result: 'Cover holds.', scoreDelta: 20, consume: true },
          ]},
        { id: 'to-comp', x: 85, y: 55, label: 'Compound', kind: 'exit', goesTo: 'compound', lockedBy: ['ev-lane'] },
      ],
    },
    {
      id: 'compound', name: 'Relay Compound', theme: 'warehouse', mood: 'Antenna. Guards. Wall charge option.',
      hotspots: [
        { id: 'wall', x: 30, y: 50, label: 'Weak wall', kind: 'danger',
          actions: [
            { id: 'blow', label: 'Blow the wall', result: 'Every gun turns.', isDeadly: true, deathMessage: 'You announced the assault.' },
            { id: 'cut', label: 'Cut fence quiet', result: 'Inside.', scoreDelta: 25, consume: true },
          ]},
        { id: 'box', x: 65, y: 45, label: 'Relay box', kind: 'object',
          actions: [
            { id: 'code', label: 'Pull shutdown code', result: 'Code secured.', revealsEvidence: ['ev-relay'], scoreDelta: 30, consume: true },
          ]},
        { id: 'exfil', x: 50, y: 80, label: 'Exfil field', kind: 'danger', lockedBy: ['ev-relay'],
          actions: [
            { id: 'open', label: 'Run open field', result: 'Technical.', isDeadly: true, deathMessage: 'No cover.' },
            { id: 'ditch', label: 'Ditch line to bird', result: 'Extract clean. Mission done.', winsCase: true, scoreDelta: 100 },
          ]},
        { id: 'back', x: 10, y: 50, label: 'OP', kind: 'exit', goesTo: 'op' },
      ],
    },
  ],
};
