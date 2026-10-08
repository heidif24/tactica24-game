import type { Case } from '../../types';

export const CASE_plu_01: Case = {
  id: 'plu-01',
  title: 'Pipe Dream',
  subtitle: 'Building drowned inside',
  difficulty: 2,
  roleId: 'plumber',
  synopsis: 'Trace the flood. Wrong valve and the basement becomes a tomb.',
  setting: 'Harbor View Towers',
  startRoom: 'lobby-p',
  keyEvidence: ['ev-pressure', 'ev-valve'],
  solution: 'Crowe bypassed the relief valve for insurance.',
  rewards: { xp: 150, title: 'Pressure Reader' },
  evidence: [
    { id: 'ev-pressure', name: 'Pressure spike log', type: 'document', description: 'Spike at 01:40.', isKey: true },
    { id: 'ev-valve', name: 'Bypassed relief', type: 'physical', description: 'Welded shut.', isKey: true },
  ],
  rooms: [
    {
      id: 'lobby-p', name: 'Tower Lobby', theme: 'bank-lobby', mood: 'Wet carpet. Manager points down.',
      hotspots: [
        { id: 'gauge', x: 40, y: 50, label: 'Wall gauge', kind: 'clue',
          actions: [{ id: 'read', label: 'Read pressure', result: 'Spike logged.', revealsEvidence: ['ev-pressure'], requiresTool: 'tool-pressure-gauge', scoreDelta: 25, consume: true }] },
        { id: 'riser', x: 70, y: 45, label: 'Main riser', kind: 'danger',
          actions: [
            { id: 'open', label: 'Open main riser', result: 'Surge.', isDeadly: true, deathMessage: 'You do not surface.' },
            { id: 'bypass', label: 'Isolate branch first', result: 'Safe path down.', scoreDelta: 20, consume: true },
          ]},
        { id: 'down', x: 50, y: 80, label: 'Basement', kind: 'exit', goesTo: 'base', lockedBy: ['ev-pressure'] },
      ],
    },
    {
      id: 'base', name: 'Basement Plant', theme: 'basement', mood: 'Standing water. Steam lines. Crowe tools.',
      hotspots: [
        { id: 'steam', x: 30, y: 40, label: 'Live steam line', kind: 'danger',
          actions: [
            { id: 'crawl', label: 'Crawl the live line', result: 'Steam.', isDeadly: true, deathMessage: 'Instant scald.' },
            { id: 'shut', label: 'Shut upstream first', result: 'Line cools.', scoreDelta: 20, consume: true },
          ]},
        { id: 'relief', x: 65, y: 55, label: 'Relief valve', kind: 'clue',
          actions: [{ id: 'inspect', label: 'Inspect valve', result: 'Welded bypass.', revealsEvidence: ['ev-valve'], scoreDelta: 30, consume: true }] },
        { id: 'crowe', x: 80, y: 50, label: 'Crowe', kind: 'person', lockedBy: ['ev-valve'],
          actions: [
            { id: 'show', label: 'Show welded bypass', result: 'He confesses insurance play.', winsCase: true, scoreDelta: 80 },
            { id: 'corner', label: 'Corner him in gas room', result: 'Wrong mix.', isDeadly: true, deathMessage: 'Gases. Lights out.' },
          ]},
      ],
    },
  ],
};
