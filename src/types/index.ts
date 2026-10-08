export type RoleId = 'detective' | 'criminal' | 'police' | 'military' | 'plumber' | 'hacker' | 'doctor';

export interface Role {
  id: RoleId;
  name: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  strengths: string[];
  uniform: {
    primary: string;
    secondary: string;
    accent: string;
    silhouette: string;
  };
  startingTools: string[];
}

export type EvidenceType = 'physical' | 'testimony' | 'digital' | 'document' | 'forensic';

export interface Evidence {
  id: string;
  name: string;
  type: EvidenceType;
  description: string;
  isKey: boolean;
  discovered: boolean;
  combinesWith?: string[];
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
  isFatal?: boolean;          // wrong choice can kill the character
  deathMessage?: string;      // shown on fatal outcome
  scoreDelta?: number;
  revealsEvidence?: string[];
  healthDelta?: number;       // negative for damage
}

export interface Scene {
  id: string;
  title: string;
  narrative: string;
  location: string;
  availableEvidence: string[];
  availableTools: string[];
  choices: Choice[];
  isClimax?: boolean;
  deductionPuzzle?: {
    prompt: string;
    correctCombination: string[];
    hints: string[];
  };
}

export interface Case {
  id: string;
  title: string;
  subtitle: string;
  difficulty: 1 | 2 | 3 | 4 | 5;
  roleAffinity: RoleId[];
  minLevel: number;
  synopsis: string;
  setting: string;
  scenes: Scene[];
  solution: string;
  solutionEvidence: string[];
  rewards: { xp: number; title?: string };
}

export interface PlayerState {
  role: RoleId | null;
  name: string;
  level: number;
  xp: number;
  health: number;
  maxHealth: number;
  completedCases: string[];
  currentCase: string | null;
  currentScene: string | null;
  inventory: Tool[];
  discoveredEvidence: string[];
  score: number;
  notes: string[];
  soundEnabled: boolean;
  lives: number;
}

export type GameScreen =
  | 'splash'
  | 'role-select'
  | 'hub'
  | 'case-select'
  | 'scene'
  | 'death'
  | 'victory'
  | 'case-complete'
  | 'inventory'
  | 'notes';
