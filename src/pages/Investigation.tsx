import { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Heart, Volume2, VolumeX, Package, X, Skull } from 'lucide-react';
import type { Case, Hotspot, HotspotAction, Role, PlayerState } from '../types';
import { RoomScene } from '../components/RoomScene';
import { CharacterAvatar } from '../components/CharacterAvatar';
import { sfx } from '../lib/sound';
import clsx from 'clsx';

interface Props {
  caseData: Case;
  role: Role;
  state: PlayerState;
  onExit: () => void;
  onWin: (xp: number, caseId: string) => void;
  onDeath: () => void;
  onToggleSound: () => void;
}

export function Investigation({ caseData, role, state, onExit, onWin, onDeath, onToggleSound }: Props) {
  const [roomId, setRoomId] = useState(caseData.startRoom);
  const [discovered, setDiscovered] = useState<string[]>([]);
  const [consumed, setConsumed] = useState<Set<string>>(new Set());
  const [playerX, setPlayerX] = useState(50);
  const [panel, setPanel] = useState<{ hotspot: Hotspot; actions: HotspotAction[] } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [dead, setDead] = useState(false);
  const [deathMsg, setDeathMsg] = useState('');
  const [won, setWon] = useState(false);
  const [score, setScore] = useState(0);
  const [showInv, setShowInv] = useState(false);

  const room = useMemo(() => caseData.rooms.find((r) => r.id === roomId)!, [caseData, roomId]);
  const evidenceMap = useMemo(() => Object.fromEntries(caseData.evidence.map((e) => [e.id, e])), [caseData]);

  const flash = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2800);
  }, []);

  const moveTo = useCallback((h: Hotspot) => {
    setPlayerX(h.x);
    if (h.kind === 'exit' && h.goesTo) {
      sfx.select();
      setTimeout(() => {
        setRoomId(h.goesTo!);
        setPlayerX(50);
        setPanel(null);
      }, 280);
    }
  }, []);

  const runAction = useCallback(
    (h: Hotspot, a: HotspotAction) => {
      if (a.requiresTool) {
        const tool = state.inventory.find((t) => t.id === a.requiresTool);
        if (!tool || tool.uses <= 0) {
          sfx.wrong();
          flash(`Need tool: ${a.requiresTool.replace('tool-', '')}`);
          return;
        }
      }
      if (a.requiresEvidence && !a.requiresEvidence.every((e) => discovered.includes(e))) {
        sfx.wrong();
        flash('Missing evidence.');
        return;
      }
      if (a.isDeadly) {
        sfx.death();
        setDeathMsg(a.deathMessage || role.deathFlavor);
        setDead(true);
        onDeath();
        setPanel(null);
        return;
      }
      if (a.revealsEvidence) {
        setDiscovered((prev) => {
          const next = [...prev];
          a.revealsEvidence!.forEach((id) => {
            if (!next.includes(id)) next.push(id);
          });
          return next;
        });
        sfx.discover();
      } else {
        sfx.click();
      }
      if (a.scoreDelta) setScore((s) => s + a.scoreDelta!);
      flash(a.result);
      if (a.consume) setConsumed((prev) => new Set(prev).add(h.id));
      if (a.winsCase) {
        sfx.complete();
        setWon(true);
        setPanel(null);
        return;
      }
      setPanel(null);
    },
    [discovered, state.inventory, role.deathFlavor, onDeath, flash],
  );

  const onHotspot = useCallback(
    (h: Hotspot) => {
      setPlayerX(h.x);
      if (h.kind === 'exit') {
        moveTo(h);
        return;
      }
      if ((!h.actions || h.actions.length === 0) && h.inspect) {
        sfx.click();
        flash(h.inspect);
        if (h.revealsEvidence) {
          setDiscovered((prev) => {
            const next = [...prev];
            h.revealsEvidence!.forEach((id) => {
              if (!next.includes(id)) next.push(id);
            });
            return next;
          });
          sfx.discover();
        }
        return;
      }
      if (h.actions && h.actions.length === 1 && !h.actions[0].isDeadly && !h.actions[0].winsCase) {
        runAction(h, h.actions[0]);
        return;
      }
      if (h.actions && h.actions.length > 0) {
        sfx.ui();
        setPanel({ hotspot: h, actions: h.actions });
      }
    },
    [moveTo, runAction, flash],
  );

  if (dead) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center px-6 text-center">
        <Skull className="w-16 h-16 text-crimson-500 mb-4" />
        <h2 className="font-serif text-4xl text-crimson-400">You Are Dead</h2>
        <p className="text-noir-300 mt-3 max-w-md">{deathMsg}</p>
        <p className="text-noir-500 text-sm mt-2">{role.deathFlavor}</p>
        <p className="text-noir-400 mt-4">Lives remaining: {Math.max(0, state.lives - 1)}</p>
        <button onClick={onExit} className="mt-8 px-6 py-3 rounded-xl bg-noir-800 border border-noir-600 hover:border-accent-500 text-noir-100">
          Return to cases
        </button>
      </div>
    );
  }

  if (won) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center px-6 text-center">
        <div className="text-5xl mb-4">✓</div>
        <h2 className="font-serif text-4xl text-emerald-400">Case Closed</h2>
        <p className="text-noir-300 mt-3 max-w-lg">{caseData.solution}</p>
        <p className="text-accent-400 mt-4">+{caseData.rewards.xp} XP · Score {score}</p>
        {caseData.rewards.title && (
          <p className="text-noir-400 text-sm mt-1">Title unlocked: {caseData.rewards.title}</p>
        )}
        <button
          onClick={() => onWin(caseData.rewards.xp, caseData.id)}
          className="mt-8 px-6 py-3 rounded-xl bg-accent-500/20 border border-accent-500 text-accent-400 hover:bg-accent-500/30"
        >
          Continue
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full flex flex-col max-w-5xl mx-auto px-3 sm:px-6 py-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <button onClick={onExit} className="flex items-center gap-1.5 text-noir-400 hover:text-noir-100 text-sm">
          <ArrowLeft className="w-4 h-4" /> Exit
        </button>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-crimson-400 text-sm">
            <Heart className="w-4 h-4 fill-current" /> {state.lives}
          </div>
          <button onClick={() => setShowInv((v) => !v)} className="text-noir-400 hover:text-accent-400">
            <Package className="w-4 h-4" />
          </button>
          <button onClick={onToggleSound} className="text-noir-400 hover:text-noir-100">
            {state.soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <CharacterAvatar role={role} size="sm" />
        <div>
          <h1 className="font-serif text-xl sm:text-2xl text-noir-50">{caseData.title}</h1>
          <p className="text-noir-500 text-xs sm:text-sm">{caseData.subtitle}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3 min-h-[28px]">
        {discovered.length === 0 ? (
          <span className="text-xs text-noir-600">Explore the scene — tap glowing markers</span>
        ) : (
          discovered.map((id) => (
            <span key={id} className="px-2 py-0.5 rounded-full text-[11px] bg-accent-500/15 border border-accent-500/40 text-accent-400">
              {evidenceMap[id]?.name || id}
            </span>
          ))
        )}
      </div>

      <RoomScene room={room} discovered={discovered} consumed={consumed} onHotspot={onHotspot} playerX={playerX} />

      <div className="mt-3 flex flex-wrap gap-2">
        {caseData.rooms.map((r) => (
          <button
            key={r.id}
            disabled={r.id !== roomId}
            className={clsx(
              'px-2.5 py-1 rounded-lg text-xs border transition',
              r.id === roomId ? 'border-accent-500/60 bg-accent-500/15 text-accent-400' : 'border-noir-800 text-noir-600',
            )}
          >
            {r.name}
          </button>
        ))}
      </div>

      <AnimatePresence>
        {showInv && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} className="mt-3 p-4 rounded-xl bg-noir-900/90 border border-noir-700">
            <p className="text-xs uppercase tracking-widest text-noir-500 mb-2">Tools</p>
            <div className="flex flex-wrap gap-2">
              {state.inventory.map((t) => (
                <div key={t.id} className="px-3 py-2 rounded-lg bg-noir-800 border border-noir-600 text-sm">
                  <span className="mr-1">{t.icon}</span>
                  {t.name}
                  <span className="text-noir-500 ml-1 text-xs">×{t.uses}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {panel && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} className="fixed inset-x-0 bottom-0 z-40 p-4 sm:p-6 bg-gradient-to-t from-black via-noir-950/95 to-transparent">
            <div className="max-w-lg mx-auto rounded-2xl border border-noir-600 bg-noir-900/95 backdrop-blur-md p-5 shadow-2xl">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-noir-500">Interact</p>
                  <h3 className="font-serif text-xl text-noir-50">{panel.hotspot.label}</h3>
                </div>
                <button onClick={() => setPanel(null)} className="text-noir-500 hover:text-noir-200">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex flex-col gap-2">
                {panel.actions.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => runAction(panel.hotspot, a)}
                    className={clsx(
                      'w-full text-left px-4 py-3 rounded-xl border transition text-sm',
                      a.isDeadly
                        ? 'border-crimson-500/40 bg-crimson-500/10 hover:bg-crimson-500/20 text-crimson-300'
                        : a.winsCase
                          ? 'border-emerald-500/50 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300'
                          : 'border-noir-600 bg-noir-800/80 hover:border-accent-500/50 text-noir-100',
                    )}
                  >
                    {a.isDeadly && <Skull className="inline w-3.5 h-3.5 mr-2 text-crimson-400" />}
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 max-w-sm px-4 py-2.5 rounded-xl bg-black/85 border border-accent-500/40 text-sm text-noir-100 text-center shadow-xl">
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
