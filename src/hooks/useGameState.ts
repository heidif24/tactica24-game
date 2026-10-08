import { useState, useEffect, useCallback } from 'react';
import type { PlayerState, RoleId } from '../types';
import { DEFAULT_TOOLS } from '../data/tools';
import { setSoundEnabled } from '../lib/sound';

const KEY = 'tactica24-v3';
const def: PlayerState = {
  role: null, name: 'Agent', level: 1, xp: 0, completedCases: [], deaths: 0,
  currentCase: null, inventory: DEFAULT_TOOLS.map(t => ({ ...t })),
  discoveredEvidence: [], score: 0, soundEnabled: true, lives: 3,
};

export function useGameState() {
  const [state, setState] = useState<PlayerState>(() => {
    try { const r = localStorage.getItem(KEY); if (r) return { ...def, ...JSON.parse(r) }; } catch {}
    return def;
  });
  useEffect(() => { localStorage.setItem(KEY, JSON.stringify(state)); setSoundEnabled(state.soundEnabled); }, [state]);

  const setRole = useCallback((role: RoleId) => setState(s => ({ ...s, role })), []);
  const setName = useCallback((name: string) => setState(s => ({ ...s, name: name || 'Agent' })), []);
  const startCase = useCallback((caseId: string) => setState(s => ({
    ...s, currentCase: caseId, discoveredEvidence: [], score: 0,
    inventory: DEFAULT_TOOLS.map(t => ({ ...t })), lives: Math.max(s.lives, 1),
  })), []);
  const discoverEvidence = useCallback((id: string) => setState(s =>
    s.discoveredEvidence.includes(id) ? s : { ...s, discoveredEvidence: [...s.discoveredEvidence, id] }
  ), []);
  const useTool = useCallback((id: string) => setState(s => ({
    ...s, inventory: s.inventory.map(t => t.id === id && t.uses > 0 ? { ...t, uses: t.uses - 1 } : t),
  })), []);
  const addScore = useCallback((d: number) => setState(s => ({ ...s, score: Math.max(0, s.score + d) })), []);
  const recordDeath = useCallback(() => setState(s => ({
    ...s, deaths: s.deaths + 1, lives: Math.max(0, s.lives - 1), currentCase: null,
  })), []);
  const completeCase = useCallback((caseId: string, xp: number) => setState(s => {
    const newXp = s.xp + xp;
    return {
      ...s,
      completedCases: s.completedCases.includes(caseId) ? s.completedCases : [...s.completedCases, caseId],
      currentCase: null, xp: newXp, level: Math.floor(newXp / 200) + 1, lives: Math.min(5, s.lives + 1),
    };
  }), []);
  const toggleSound = useCallback(() => setState(s => ({ ...s, soundEnabled: !s.soundEnabled })), []);
  const resetProgress = useCallback(() => { setState(def); localStorage.removeItem(KEY); }, []);

  return { state, setRole, setName, startCase, discoverEvidence, useTool, addScore, recordDeath, completeCase, toggleSound, resetProgress };
}
