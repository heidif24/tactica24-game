import type { Case } from '../../types';

export const CASE_pol_01: Case = {
  id: 'pol-01',
  title: 'No-Knock Night',
  subtitle: 'Warrant clean. House is not.',
  difficulty: 2,
  roleId: 'police',
  synopsis: 'Clear the house room by room. First through the wrong door dies.',
  setting: 'Eastside Row House',
  startRoom: 'front',
  keyEvidence: ['ev-layout', 'ev-tick'],
  solution: 'Secondary shooter in the attic.',
  rewards: { xp: 170, title: 'Steady Shield' },
  evidence: [
    { id: 'ev-layout', name: 'Floor plan', type: 'document', description: 'Attic access behind false wall.', isKey: true },
    { id: 'ev-tick', name: 'Timer sound', type: 'physical', description: 'Device in hallway closet.', isKey: true },
  ],
  rooms: [
    {
      id: 'front', name: 'Front Porch', theme: 'street-night', mood: 'Stack ready. Windows dark.',
      hotspots: [
        { id: 'plan', x: 30, y: 60, label: 'Briefing sheet', kind: 'clue',
          actions: [{ id: 'read', label: 'Study plan', result: 'Attic noted.', revealsEvidence: ['ev-layout'], scoreDelta: 20, consume: true }] },
        { id: 'breach', x: 55, y: 45, label: 'Front door', kind: 'danger',
          actions: [
            { id: 'hard', label: 'Breach immediately', result: 'They were ready.', isDeadly: true, deathMessage: 'First through the door.' },
            { id: 'soft', label: 'Soft clear, flash first', result: 'Entry secured.', scoreDelta: 25, consume: true },
          ]},
        { id: 'in', x: 70, y: 50, label: 'Enter house', kind: 'exit', goesTo: 'hall', lockedBy: ['ev-layout'] },
      ],
    },
    {
      id: 'hall', name: 'Hallway', theme: 'apartment', mood: 'Tick. Tick. Closet door.',
      hotspots: [
        { id: 'closet', x: 40, y: 50, label: 'Closet', kind: 'danger',
          actions: [
            { id: 'kick', label: 'Kick the door', result: 'Not a decoy.', isDeadly: true, deathMessage: 'Blast takes the hallway.' },
            { id: 'listen', label: 'Listen, call bomb tech', result: 'Timer confirmed.', revealsEvidence: ['ev-tick'], scoreDelta: 30, consume: true },
          ]},
        { id: 'to-room', x: 80, y: 50, label: 'Back room', kind: 'exit', goesTo: 'back', lockedBy: ['ev-tick'] },
      ],
    },
    {
      id: 'back', name: 'Back Room', theme: 'apartment', mood: 'Suspect raised hands. Attic hatch open.',
      hotspots: [
        { id: 'sus', x: 45, y: 55, label: 'Suspect', kind: 'person',
          actions: [
            { id: 'cover', label: 'Cover + call attic team', result: 'Second shooter bagged. Clean.', winsCase: true, scoreDelta: 90 },
            { id: 'rush', label: 'Rush him', result: 'Second shooter.', isDeadly: true, deathMessage: 'Tunnel vision. Attic fires.' },
          ]},
      ],
    },
  ],
};
