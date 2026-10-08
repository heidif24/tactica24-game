import type { Role } from '../types';
import { motion } from 'framer-motion';
const sizes = { sm: 48, md: 80, lg: 120 };
export function CharacterAvatar({ role, size = 'md', showLabel = false }: { role: Role; size?: keyof typeof sizes; showLabel?: boolean }) {
  const s = sizes[size]; const u = role.uniform;
  return (
    <div className="flex flex-col items-center gap-2">
      <motion.div className="relative animate-breathe" style={{ width: s, height: s }} whileHover={{ scale: 1.05 }}>
        <svg viewBox="0 0 100 100" width={s} height={s} className="drop-shadow-lg">
          <circle cx="50" cy="50" r="48" fill={u.primary} stroke={u.accent} strokeWidth="2" />
          <circle cx="50" cy="32" r="14" fill="#e8d5b7" />
          {(role.id === 'hacker' || role.id === 'criminal') && <path d="M34 30 Q50 16 66 30 L66 38 Q50 34 34 38 Z" fill={u.secondary} />}
          {role.id === 'military' && <path d="M36 28 Q50 18 64 28 L64 34 Q50 30 36 34 Z" fill={u.secondary} />}
          {role.id === 'doctor' && <path d="M36 26 Q50 20 64 26 L62 32 Q50 28 38 32 Z" fill="#f1f5f9" />}
          <path d="M30 48 Q50 44 70 48 L74 85 Q50 92 26 85 Z" fill={u.secondary} stroke={u.accent} strokeWidth="1" />
          {u.silhouette === 'coat' && (<><path d="M30 50 L26 88 L38 85 L42 52" fill={u.primary} opacity=".7" /><path d="M70 50 L74 88 L62 85 L58 52" fill={u.primary} opacity=".7" /></>)}
          {u.silhouette === 'badge' && <rect x="44" y="58" width="12" height="10" rx="1" fill={u.accent} />}
          {u.silhouette === 'overalls' && (<><path d="M40 48 L38 70 L62 70 L60 48" fill="#0369a1" opacity=".8" /><circle cx="44" cy="58" r="2" fill={u.accent} /><circle cx="56" cy="58" r="2" fill={u.accent} /></>)}
          {u.silhouette === 'tactical' && (<><rect x="38" y="52" width="24" height="8" rx="1" fill={u.primary} /><rect x="42" y="64" width="16" height="4" fill={u.accent} opacity=".6" /></>)}
          {u.silhouette === 'hoodie' && <path d="M34 48 Q50 42 66 48 L64 56 Q50 52 36 56 Z" fill={u.primary} opacity=".9" />}
          <circle cx="45" cy="32" r="1.5" fill="#1a1a1a" /><circle cx="55" cy="32" r="1.5" fill="#1a1a1a" />
        </svg>
        <div className="absolute inset-0 rounded-full pointer-events-none" style={{ boxShadow: `0 0 20px ${u.accent}33` }} />
      </motion.div>
      {showLabel && <div className="text-center"><p className="text-sm font-medium text-noir-100">{role.name}</p><p className="text-[10px] text-noir-400 uppercase tracking-wider">{role.title}</p></div>}
    </div>
  );
}
