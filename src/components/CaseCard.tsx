import { motion } from 'framer-motion';
import { Lock, CheckCircle2, Star, Skull } from 'lucide-react';
import type { Case } from '../types';
import clsx from 'clsx';
import { sfx } from '../lib/sound';
export function CaseCard({ caseData, completed, locked, onSelect }: { caseData: Case; completed: boolean; locked: boolean; onSelect: () => void }) {
  return (
    <motion.button whileHover={locked ? {} : { scale: 1.02, y: -3 }} whileTap={locked ? {} : { scale: 0.98 }}
      onClick={() => { if (!locked) { sfx.click(); onSelect(); } }} disabled={locked}
      className={clsx('relative w-full text-left p-6 rounded-2xl border transition-all bg-noir-900/70',
        locked ? 'border-noir-800 opacity-50 cursor-not-allowed' : completed ? 'border-emerald-500/40' : 'border-noir-700 hover:border-accent-500/60')}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] uppercase tracking-widest text-noir-400">Lvl {caseData.difficulty}</span>
            <div className="flex gap-0.5">{Array.from({ length: caseData.difficulty }).map((_, i) => <Star key={i} className="w-3 h-3 fill-accent-500 text-accent-500" />)}</div>
            <Skull className="w-3 h-3 text-crimson-400" />
          </div>
          <h3 className="font-serif text-xl text-noir-50 font-semibold">{caseData.title}</h3>
          <p className="text-noir-400 text-sm mt-1 italic">{caseData.subtitle}</p>
        </div>
        {completed ? <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" /> : locked ? <Lock className="w-5 h-5 text-noir-500 shrink-0" /> : null}
      </div>
      <p className="text-noir-300 text-sm mt-4 line-clamp-3">{caseData.synopsis}</p>
      <div className="mt-4 text-xs text-accent-500/80">+{caseData.rewards.xp} XP</div>
    </motion.button>
  );
}
