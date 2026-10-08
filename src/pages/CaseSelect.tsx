import { motion } from 'framer-motion';
import { CASES } from '../data/cases';
import { CaseCard } from '../components/CaseCard';
import { ROLES } from '../data/roles';
import { CharacterAvatar } from '../components/CharacterAvatar';
import type { PlayerState } from '../types';
import { Heart, Skull } from 'lucide-react';
export function CaseSelect({ state, onSelectCase, onBack, onReset }: {
  state: PlayerState; onSelectCase: (id: string) => void; onBack: () => void; onReset: () => void;
}) {
  const role = ROLES.find(r => r.id === state.role);
  const roleCases = CASES.filter(c => c.roleId === state.role);
  return (
    <div className="min-h-dvh px-4 py-10 sm:px-8 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          {role && <CharacterAvatar role={role} size="md" />}
          <div>
            <button onClick={onBack} className="text-noir-400 text-sm mb-1">← Change Role</button>
            <h1 className="font-serif text-3xl font-bold text-noir-50">{role?.name} Cases</h1>
            <p className="text-noir-400 mt-1 flex items-center gap-3 flex-wrap">
              {state.name} · Lvl {state.level} · {state.xp} XP
              <span className="inline-flex items-center gap-1 text-crimson-400"><Heart className="w-3.5 h-3.5" /> {state.lives}</span>
              <span className="inline-flex items-center gap-1 text-noir-500"><Skull className="w-3.5 h-3.5" /> {state.deaths}</span>
            </p>
          </div>
        </div>
        <button onClick={onReset} className="text-xs text-noir-500 hover:text-crimson-400">Reset</button>
      </div>
      <div className="grid sm:grid-cols-2 gap-5">
        {roleCases.map((c, i) => {
          const completed = state.completedCases.includes(c.id);
          const locked = i > 0 && !state.completedCases.includes(roleCases[i - 1].id);
          return (
            <motion.div key={c.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
              <CaseCard caseData={c} completed={completed} locked={locked || state.lives <= 0} onSelect={() => onSelectCase(c.id)} />
            </motion.div>
          );
        })}
      </div>
      <p className="mt-8 text-center text-noir-500 text-sm">Skull = deadly choices. Stay careful.</p>
    </div>
  );
}
