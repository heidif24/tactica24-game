import type { Case } from '../../types';

export const CASE_det_02: Case = {
  id: 'det-02',
  title: 'The Silent Ward',
  subtitle: 'Patient vanished',
  difficulty: 2,
  roleId: 'detective',
  synopsis: 'Room 4B empty. Charts altered. Move the halls carefully — wrong accusation gets you sedated permanently.',
  setting: 'St. Aurelia Hospital',
  startRoom: 'ward',
  keyEvidence: ['ev-chart', 'ev-cam2', 'ev-badge'],
  solution: 'Dr. Marsh falsified transfer orders.',
  rewards: { xp: 180, title: 'Ward Walker' },
  evidence: [
    { id: 'ev-chart', name: 'Altered chart', type: 'document', description: 'Transfer time overwritten.', isKey: true },
    { id: 'ev-cam2', name: 'Hall cam still', type: 'digital', description: 'Gurney at 03:11 toward service lift.', isKey: true },
    { id: 'ev-badge', name: 'Marsh badge swipe', type: 'digital', description: 'Swipe at lift at 03:09.', isKey: true },
  ],
  rooms: [
    {
      id: 'ward', name: 'Ward 4B', theme: 'hospital', mood: 'Beeping monitors. Empty bed. Curtain half-drawn.',
      hotspots: [
        { id: 'bed', x: 50, y: 55, label: 'Empty bed', kind: 'object',
          actions: [
            { id: 'chart', label: 'Check chart', result: 'Ink overwrite on transfer time.', revealsEvidence: ['ev-chart'], scoreDelta: 20, consume: true },
            { id: 'accuse-nurse', label: 'Accuse nurse on shift', result: 'Panic button.', isDeadly: true, deathMessage: 'Injection. You never leave the ward.' },
          ]},
        { id: 'to-hall', x: 90, y: 50, label: 'Hall', kind: 'exit', goesTo: 'hhall' },
      ],
    },
    {
      id: 'hhall', name: 'Service Hall', theme: 'hospital', mood: 'Gurney marks. Lift doors.',
      hotspots: [
        { id: 'cam', x: 30, y: 25, label: 'Ceiling cam', kind: 'clue',
          actions: [{ id: 'pull', label: 'Pull footage', result: 'Gurney at 03:11.', revealsEvidence: ['ev-cam2'], scoreDelta: 25, consume: true }] },
        { id: 'lift', x: 70, y: 50, label: 'Service lift', kind: 'object',
          actions: [
            { id: 'log', label: 'Badge log', result: 'Marsh at 03:09.', revealsEvidence: ['ev-badge'], scoreDelta: 25, consume: true },
            { id: 'ride', label: 'Ride alone to basement', result: 'Dark. Wrong company.', isDeadly: true, deathMessage: 'Private contractors. Lights out.' },
          ]},
        { id: 'to-ward', x: 10, y: 50, label: 'Ward', kind: 'exit', goesTo: 'ward' },
        { id: 'to-office', x: 50, y: 85, label: 'Staff office', kind: 'exit', goesTo: 'office', lockedBy: ['ev-chart', 'ev-cam2', 'ev-badge'] },
      ],
    },
    {
      id: 'office', name: 'Staff Office', theme: 'office', mood: 'Desk lamp. Marsh standing.',
      hotspots: [
        { id: 'marsh', x: 55, y: 50, label: 'Dr. Marsh', kind: 'person',
          actions: [
            { id: 'show', label: 'Show all evidence', result: 'She folds. Transfer was a cover.', winsCase: true, scoreDelta: 90 },
            { id: 'grab', label: 'Block the door alone', result: 'She is not alone.', isDeadly: true, deathMessage: 'Two against one in a locked office.' },
          ]},
        { id: 'back', x: 10, y: 50, label: 'Hall', kind: 'exit', goesTo: 'hhall' },
      ],
    },
  ],
};
