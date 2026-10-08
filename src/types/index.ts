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

/** Action when player taps a hotspot */
export interface HotspotAction {
  id: string;
  label: string;
  /** Short result shown in toast / panel */
  result: string;
  isDeadly?: boolean;
  deathMessage?: string;
  requiresTool?: string;
  requiresEvidence?: string[];
  revealsEvidence?: string[];
  scoreDelta?: number;
  /** Marks case as solved when taken (after checks) */
  winsCase?: boolean;
  /** Consumes the hotspot after success */
  consume?: boolean;
}

export interface Hotspot {
  id: string;
  /** Position in room as % of width/height */
  x: number;
  y: number;
  label: string;
  /** Visual cue */
  kind: 'object' | 'person' | 'exit' | 'danger' | 'clue';
  /** Room to enter when kind === 'exit' */
  goesTo?: string;
  /** Locked until player has these evidence ids */
  lockedBy?: string[];
  actions?: HotspotAction[];
  /** Auto-inspect text when first clicked with no multi-action */
  inspect?: string;
  revealsEvidence?: string[];
}

export type RoomTheme =
  | 'bank-lobby'
  | 'bank-corridor'
  | 'bank-vault'
  | 'street-night'
  | 'office'
  | 'hospital'
  | 'apartment'
  | 'warehouse'
  | 'basement'
  | 'server-room'
  | 'rooftop'
  | 'alley'
  | 'clinic'
  | 'military-camp';

export interface Room {
  id: string;
  name: string;
  theme: RoomTheme;
  /** One-line atmosphere, not a wall of text */
  mood: string;
  hotspots: Hotspot[];
}

export interface Case {
  id: string;
  title: string;
  subtitle: string;
  difficulty: 1 | 2 | 3 | 4 | 5;
  roleId: RoleId;
  synopsis: string;
  setting: string;
  startRoom: string;
  rooms: Room[];
  /** Evidence catalog for this case */
  evidence: Evidence[];
  /** Must collect these evidence ids to unlock the final win action, optional */
  keyEvidence: string[];
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
