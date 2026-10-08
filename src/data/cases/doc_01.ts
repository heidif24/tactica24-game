import type { Case } from '../../types';

export const CASE_doc_01: Case = {
  id: 'doc-01',
  title: 'Code Grey',
  subtitle: 'ER lies',
  difficulty: 2,
  roleId: 'doctor',
  synopsis: 'Walk the ER and labs. Misdiagnose under pressure and the next patient is you.',
  setting: 'City General ER',
  startRoom: 'er',
  keyEvidence: ['ev-tox', 'ev-batch'],
  solution: 'Contaminated batch from supplier Helix.',
  rewards: { xp: 160, title: 'Grey Clear' },
  evidence: [
    { id: 'ev-tox', name: 'Tox screen', type: 'forensic', description: 'Unknown compound.', isKey: true },
    { id: 'ev-batch', name: 'Batch sticker', type: 'physical', description: 'Helix lot H-19.', isKey: true },
  ],
  rooms: [
    {
      id: 'er', name: 'Trauma Bay', theme: 'clinic', mood: 'Curtains. Alarms. Chart cart.',
      hotspots: [
        { id: 'patient', x: 45, y: 55, label: 'Unstable patient', kind: 'person',
          actions: [
            { id: 'tox', label: 'Order full tox', result: 'Unknown compound.', revealsEvidence: ['ev-tox'], scoreDelta: 25, consume: true },
            { id: 'guess', label: 'Push wide-spectrum blind', result: 'Reaction.', isDeadly: true, deathMessage: 'Anaphylaxis cascade. You lose the bay.' },
          ]},
        { id: 'to-lab', x: 85, y: 50, label: 'Lab', kind: 'exit', goesTo: 'lab', lockedBy: ['ev-tox'] },
      ],
    },
    {
      id: 'lab', name: 'Path Lab', theme: 'clinic', mood: 'Fridge. Samples. Supply crate.',
      hotspots: [
        { id: 'crate', x: 55, y: 50, label: 'Supply crate', kind: 'clue',
          actions: [{ id: 'sticker', label: 'Check batch labels', result: 'Helix H-19.', revealsEvidence: ['ev-batch'], scoreDelta: 30, consume: true }] },
        { id: 'admin', x: 30, y: 45, label: 'Admin phone', kind: 'person', lockedBy: ['ev-batch'],
          actions: [
            { id: 'report', label: 'Report Helix batch', result: 'Recall starts. Lives saved.', winsCase: true, scoreDelta: 85 },
            { id: 'inject', label: 'Self-test the compound', result: 'You are not the assay.', isDeadly: true, deathMessage: 'Dose unknown. Collapse.' },
          ]},
        { id: 'back', x: 10, y: 50, label: 'ER', kind: 'exit', goesTo: 'er' },
      ],
    },
  ],
};
