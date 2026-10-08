export type RoleId = 'detective' | 'criminal' | 'police' | 'military' | 'plumber' | 'hacker' | 'doctor';

export interface Role {
  id: RoleId;
  name: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  strengths: string[];
  uniform: { primary: string; secondary: string; accent: string; silhouette: string };
  deathFlavor: string;
}

export type EvidenceType = 'physical' | 'testimony' | 'digital' | 'document' | 'forensic';

export interface Evidence {
  id: string;
  name: string;
  type: EvidenceType;
  description: string;
  isKey: boolean;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  icon: string;
  uses: number;
  maxUses: number;
}

export interface Choice {
  id: string;
  text: string;
  consequence: string;
  leadsTo?: string;
  requiresEvidence?: string[];
  requiresTool?: string;
  requiresCombination?: string[];
  isCorrect?: boolean;
  isDeadly?: boolean;
  deathMessage?: string;
  scoreDelta?: number;
  revealsEvidence?: string[];
}

export interface Scene {
  id: string;
  title: string;
  narrative: string;
  location: string;
  availableEvidence: string[];
  choices: Choice[];
  isClimax?: boolean;
  deductionPuzzle?: { prompt: string; correctCombination: string[]; hints: string[] };
}

export interface Case {
  id: string;
  title: string;
  subtitle: string;
  difficulty: 1 | 2 | 3 | 4 | 5;
  roleId: RoleId;
  synopsis: string;
  setting: string;
  scenes: Scene[];
  solution: string;
  rewards: { xp: number; title?: string };
}

export interface PlayerState {
  role: RoleId | null;
  name: string;
  level: number;
  xp: number;
  completedCases: string[];
  deaths: number;
  currentCase: string | null;
  inventory: Tool[];
  discoveredEvidence: string[];
  score: number;
  soundEnabled: boolean;
  lives: number;
}
