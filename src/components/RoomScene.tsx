import { motion, AnimatePresence } from 'framer-motion';
import type { Room, RoomTheme, Hotspot } from '../types';
import clsx from 'clsx';

const THEME_BG: Record<RoomTheme, { sky: string; floor: string; accent: string }> = {
  'bank-lobby': { sky: '#1a1a24', floor: '#2a2430', accent: '#c9a227' },
  'bank-corridor': { sky: '#12141c', floor: '#1c2030', accent: '#4a5568' },
  'bank-vault': { sky: '#0c1018', floor: '#1a2030', accent: '#718096' },
  'street-night': { sky: '#0a0e18', floor: '#1a1e28', accent: '#3b82f6' },
  office: { sky: '#1a1820', floor: '#252030', accent: '#a78bfa' },
  hospital: { sky: '#141c22', floor: '#1e2a30', accent: '#34d399' },
  apartment: { sky: '#1a1818', floor: '#2a2424', accent: '#f87171' },
  warehouse: { sky: '#141410', floor: '#222218', accent: '#fbbf24' },
  basement: { sky: '#0e1210', floor: '#1a221c', accent: '#38bdf8' },
  'server-room': { sky: '#0a1218', floor: '#121c28', accent: '#22d3ee' },
  rooftop: { sky: '#0a1020', floor: '#181e2a', accent: '#60a5fa' },
  alley: { sky: '#100e14', floor: '#1c1820', accent: '#f59e0b' },
  clinic: { sky: '#141c1c', floor: '#1e2828', accent: '#2dd4bf' },
  'military-camp': { sky: '#12180e', floor: '#1c2414', accent: '#84cc16' },
};

function RoomArt({ theme }: { theme: RoomTheme }) {
  const t = THEME_BG[theme];
  return (
    <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={t.sky} />
          <stop offset="100%" stopColor={t.floor} />
        </linearGradient>
        <linearGradient id="floorG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={t.floor} stopOpacity="0.9" />
          <stop offset="100%" stopColor="#050508" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill="url(#sky)" />
      <polygon points="0,62 100,62 100,100 0,100" fill="url(#floorG)" />
      <line x1="0" y1="62" x2="100" y2="62" stroke={t.accent} strokeOpacity="0.25" strokeWidth="0.3" />
      {(theme === 'bank-lobby' || theme === 'bank-corridor') && (
        <>
          <rect x="8" y="28" width="18" height="34" fill="#1e1e2a" stroke={t.accent} strokeWidth="0.4" opacity="0.8" />
          <rect x="74" y="28" width="18" height="34" fill="#1e1e2a" stroke={t.accent} strokeWidth="0.4" opacity="0.8" />
          <rect x="40" y="20" width="20" height="42" fill="#16161f" stroke={t.accent} strokeWidth="0.5" />
          <circle cx="50" cy="42" r="1.2" fill={t.accent} opacity="0.6" />
        </>
      )}
      {theme === 'bank-vault' && (
        <>
          <circle cx="50" cy="48" r="22" fill="none" stroke="#4a5568" strokeWidth="1.5" />
          <circle cx="50" cy="48" r="16" fill="#0c1018" stroke="#718096" strokeWidth="0.8" />
          <circle cx="50" cy="48" r="3" fill="#c9a227" opacity="0.7" />
          {[0, 45, 90, 135].map((a) => (
            <line key={a} x1="50" y1="48" x2={50 + 14 * Math.cos((a * Math.PI) / 180)} y2={48 + 14 * Math.sin((a * Math.PI) / 180)} stroke="#4a5568" strokeWidth="0.5" />
          ))}
        </>
      )}
      {(theme === 'street-night' || theme === 'alley') && (
        <>
          <rect x="5" y="20" width="25" height="42" fill="#12121a" />
          <rect x="70" y="25" width="22" height="37" fill="#101018" />
          <circle cx="20" cy="35" r="4" fill="#fbbf24" opacity="0.15" />
          <rect x="15" y="50" width="8" height="12" fill="#1a1a24" stroke="#333" strokeWidth="0.3" />
          <line x1="0" y1="62" x2="100" y2="62" stroke="#333" strokeWidth="0.8" />
        </>
      )}
      {(theme === 'hospital' || theme === 'clinic') && (
        <>
          <rect x="20" y="30" width="60" height="32" fill="#1a2428" stroke="#34d399" strokeWidth="0.3" opacity="0.5" />
          <rect x="35" y="38" width="30" height="18" fill="#0e1818" stroke="#2dd4bf" strokeWidth="0.4" />
          <line x1="50" y1="38" x2="50" y2="56" stroke="#2dd4bf" strokeWidth="0.3" opacity="0.5" />
        </>
      )}
      {theme === 'server-room' && (
        <>
          {[15, 35, 55, 75].map((x) => (
            <g key={x}>
              <rect x={x} y="25" width="12" height="37" fill="#0c1820" stroke="#22d3ee" strokeWidth="0.3" opacity="0.7" />
              {[30, 36, 42, 48, 54].map((y) => (
                <rect key={y} x={x + 2} y={y} width="8" height="2" fill="#22d3ee" opacity="0.25" />
              ))}
            </g>
          ))}
        </>
      )}
      {theme === 'basement' && (
        <>
          <ellipse cx="50" cy="75" rx="40" ry="8" fill="#1a3040" opacity="0.4" />
          <rect x="25" y="35" width="8" height="28" fill="#1a2820" stroke="#38bdf8" strokeWidth="0.3" />
          <rect x="67" y="35" width="8" height="28" fill="#1a2820" stroke="#38bdf8" strokeWidth="0.3" />
        </>
      )}
      {theme === 'military-camp' && (
        <>
          <polygon points="20,62 35,30 50,62" fill="#1a2414" stroke="#84cc16" strokeWidth="0.3" opacity="0.5" />
          <rect x="60" y="40" width="25" height="22" fill="#1c2418" stroke="#84cc16" strokeWidth="0.3" />
        </>
      )}
      {(theme === 'office' || theme === 'apartment' || theme === 'warehouse') && (
        <>
          <rect x="25" y="32" width="50" height="30" fill="#1a1820" stroke={t.accent} strokeWidth="0.3" opacity="0.6" />
          <rect x="40" y="45" width="20" height="12" fill="#121018" />
        </>
      )}
      <radialGradient id="vig" cx="50%" cy="45%" r="65%">
        <stop offset="40%" stopColor="transparent" />
        <stop offset="100%" stopColor="#000" stopOpacity="0.55" />
      </radialGradient>
      <rect width="100" height="100" fill="url(#vig)" />
    </svg>
  );
}

const KIND_COLOR: Record<Hotspot['kind'], string> = {
  object: 'border-accent-500/70 bg-accent-500/20 text-accent-400',
  person: 'border-azure-400/70 bg-azure-500/20 text-azure-400',
  exit: 'border-emerald-400/70 bg-emerald-500/15 text-emerald-400',
  danger: 'border-crimson-400/80 bg-crimson-500/20 text-crimson-400',
  clue: 'border-accent-400/70 bg-accent-500/15 text-accent-400',
};

export function RoomScene({
  room,
  discovered,
  consumed,
  onHotspot,
  playerX,
}: {
  room: Room;
  discovered: string[];
  consumed: Set<string>;
  onHotspot: (h: Hotspot) => void;
  playerX: number;
}) {
  const visible = room.hotspots.filter((h) => {
    if (consumed.has(h.id) && h.kind !== 'exit') return false;
    if (h.lockedBy && !h.lockedBy.every((e) => discovered.includes(e))) return false;
    return true;
  });

  return (
    <div className="relative w-full aspect-[16/10] max-h-[min(62vh,560px)] rounded-2xl overflow-hidden border border-noir-700 shadow-2xl shadow-black/50">
      <RoomArt theme={room.theme} />
      <div className="absolute top-3 left-3 z-20 px-3 py-1.5 rounded-lg bg-black/55 backdrop-blur-sm border border-white/10">
        <p className="text-[10px] uppercase tracking-[0.2em] text-noir-400">Location</p>
        <p className="font-serif text-lg text-noir-50 leading-tight">{room.name}</p>
        <p className="text-xs text-noir-400 mt-0.5">{room.mood}</p>
      </div>
      <AnimatePresence>
        {visible.map((h) => (
          <motion.button
            key={h.id}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.15 }}
            whileTap={{ scale: 0.95 }}
            style={{ left: `${h.x}%`, top: `${h.y}%` }}
            className="absolute z-20 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1 group"
            onClick={() => onHotspot(h)}
          >
            <span
              className={clsx(
                'w-10 h-10 sm:w-12 sm:h-12 rounded-full border-2 flex items-center justify-center shadow-lg animate-pulse-glow',
                KIND_COLOR[h.kind],
              )}
            >
              {h.kind === 'exit' ? '➤' : h.kind === 'person' ? '👤' : h.kind === 'danger' ? '⚠' : h.kind === 'clue' ? '✦' : '◎'}
            </span>
            <span className="px-2 py-0.5 rounded bg-black/70 text-[10px] sm:text-xs text-noir-100 whitespace-nowrap opacity-90 group-hover:opacity-100 border border-white/10">
              {h.label}
            </span>
          </motion.button>
        ))}
      </AnimatePresence>
      <motion.div
        className="absolute z-10 bottom-[8%] -translate-x-1/2 pointer-events-none"
        animate={{ left: `${playerX}%` }}
        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
      >
        <div className="flex flex-col items-center">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-b from-accent-400 to-accent-600 border-2 border-white/30 shadow-lg shadow-accent-500/30" />
          <div className="w-5 h-7 sm:w-6 sm:h-9 rounded-b-md bg-gradient-to-b from-noir-600 to-noir-800 border border-white/10 -mt-1" />
          <div className="text-[9px] text-accent-400 mt-1 font-medium tracking-wide">YOU</div>
        </div>
      </motion.div>
    </div>
  );
}
