import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Landing } from './pages/Landing';
import { RoleSelect } from './pages/RoleSelect';
import { CaseSelect } from './pages/CaseSelect';
import { Investigation } from './pages/Investigation';
import { useGameState } from './hooks/useGameState';
import type { RoleId } from './types';

type Screen = 'landing' | 'role' | 'cases' | 'investigation';

export default function App() {
  const [screen, setScreen] = useState<Screen>('landing');
  const [activeCase, setActiveCase] = useState<string | null>(null);
  const { state, setRole, setName, startCase, discoverEvidence, useTool, addScore, recordDeath, completeCase, toggleSound, resetProgress } = useGameState();

  return (
    <div className="min-h-dvh bg-noir-950 text-noir-100">
      <AnimatePresence mode="wait">
        {screen === 'landing' && (
          <motion.div key="l" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Landing onStart={() => setScreen(state.role ? 'cases' : 'role')} soundEnabled={state.soundEnabled} onToggleSound={toggleSound} />
          </motion.div>
        )}
        {screen === 'role' && (
          <motion.div key="r" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <RoleSelect onConfirm={(role: RoleId, name: string) => { setRole(role); setName(name); setScreen('cases'); }} onBack={() => setScreen('landing')} />
          </motion.div>
        )}
        {screen === 'cases' && (
          <motion.div key="c" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <CaseSelect state={state} onSelectCase={(id) => { startCase(id); setActiveCase(id); setScreen('investigation'); }}
              onBack={() => setScreen('role')} onReset={() => { resetProgress(); setScreen('landing'); }} />
          </motion.div>
        )}
        {screen === 'investigation' && activeCase && (
          <motion.div key="i" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Investigation state={state} caseId={activeCase}
              onDiscover={discoverEvidence} onUseTool={useTool} onAddScore={addScore}
              onComplete={completeCase} onDeath={recordDeath}
              onExit={() => { setActiveCase(null); setScreen('cases'); }} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
