import type { Role } from '../types';

export const ROLES: Role[] = [
  {
    id: 'detective', name: 'Detective', title: 'The Investigator',
    description: 'Master of observation. One wrong move and the killer knows you are coming.',
    icon: '🔍', color: 'accent', strengths: ['Deduction', 'Evidence', 'Interrogation'],
    uniform: { primary: '#1a1a2e', secondary: '#16213e', accent: '#f59e0b', silhouette: 'coat' },
    deathFlavor: 'You walked into the trap. The case ends with your name on a toe tag.',
  },
  {
    id: 'criminal', name: 'Criminal', title: 'The Inside Mind',
    description: 'You think like the perpetrator. Betray the code and the underworld erases you.',
    icon: '🎭', color: 'crimson', strengths: ['Motive', 'Escape Routes', 'Street Sense'],
    uniform: { primary: '#2d1b1b', secondary: '#1a0a0a', accent: '#ef4444', silhouette: 'hoodie' },
    deathFlavor: 'You trusted the wrong contact. A single shot in the alley. Lights out.',
  },
  {
    id: 'police', name: 'Police Officer', title: 'The Enforcer',
    description: 'Procedure keeps you alive. Ignore protocol and the street will not forgive you.',
    icon: '👮', color: 'azure', strengths: ['Scene Control', 'Witnesses', 'Protocol'],
    uniform: { primary: '#0f172a', secondary: '#1e3a5f', accent: '#3b82f6', silhouette: 'badge' },
    deathFlavor: 'You breached without backup. Ambush. Your radio goes silent.',
  },
  {
    id: 'military', name: 'Military Operative', title: 'The Strategist',
    description: 'Every move calculated. One tactical error and the mission is a body bag.',
    icon: '🎖️', color: 'emerald', strengths: ['Tactics', 'Threat Assessment', 'Logistics'],
    uniform: { primary: '#14532d', secondary: '#052e16', accent: '#10b981', silhouette: 'tactical' },
    deathFlavor: 'You advanced into the kill zone. The extraction never comes.',
  },
  {
    id: 'plumber', name: 'Plumber', title: 'The Unexpected',
    description: 'You fix what others overlook. Misread the pipes and the building becomes your tomb.',
    icon: '🔧', color: 'accent', strengths: ['Access Points', 'Systems', 'Practical Insight'],
    uniform: { primary: '#1e3a5f', secondary: '#0c4a6e', accent: '#38bdf8', silhouette: 'overalls' },
    deathFlavor: 'The valve you opened flooded the chamber. You never made it back up.',
  },
  {
    id: 'hacker', name: 'Hacker', title: 'The Digital Ghost',
    description: 'Data never lies. Trip a honeypot and they trace you to your door.',
    icon: '💻', color: 'azure', strengths: ['Digital Forensics', 'Surveillance', 'Data Trails'],
    uniform: { primary: '#0f172a', secondary: '#020617', accent: '#22d3ee', silhouette: 'hoodie' },
    deathFlavor: 'You triggered the kill-switch. They found your location in under four minutes.',
  },
  {
    id: 'doctor', name: 'Doctor', title: 'The Healer-Analyst',
    description: 'The body tells a story. Misdiagnose the threat and you become the next case.',
    icon: '🩺', color: 'crimson', strengths: ['Forensics', 'Toxicology', 'Psychology'],
    uniform: { primary: '#f8fafc', secondary: '#e2e8f0', accent: '#dc2626', silhouette: 'coat' },
    deathFlavor: 'You handled the sample without protection. The pathogen does the rest.',
  },
];
