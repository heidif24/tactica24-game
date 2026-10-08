import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, CheckCircle2, XCircle, MapPin, Skull, Heart } from 'lucide-react';
import { CASES, ALL_EVIDENCE } from '../data/cases';
import { ROLES } from '../data/roles';
import { CharacterAvatar } from '../components/CharacterAvatar';
import type { PlayerState, Choice } from '../types';
import clsx from 'clsx';
import { sfx } from '../lib/sound';

export function Investigation({ state, caseId, onDiscover, onUseTool, onAddScore, onComplete, onDeath, onExit }: {
  state: PlayerState; caseId: string;
  onDiscover: (id: string) => void; onUseTool: (id: string) => void;
  onAddScore: (d: number) => void; onComplete: (id: string, xp: number) => void;
  onDeath: () => void; onExit: () => void;
}) {
  const caseData = CASES.find(c => c.id === caseId)!;
  const role = ROLES.find(r => r.id === state.role)!;
  const [sceneIndex, setSceneIndex] = useState(0);
  const [feedback, setFeedback] = useState<{ text: string; correct?: boolean; deadly?: boolean } | null>(null);
  const [resolved, setResolved] = useState(false);
  const [dead, setDead] = useState(false);
  const [choiceMade, setChoiceMade] = useState(false);
  const scene = caseData.scenes[sceneIndex];
  const evidenceList = useMemo(() => scene.availableEvidence.map(id => ALL_EVIDENCE[id]).filter(Boolean), [scene]);

  const handleChoice = (choice: Choice) => {
    if (choiceMade || dead) return;
    setChoiceMade(true);
    if (choice.revealsEvidence) choice.revealsEvidence.forEach(onDiscover);
    if (choice.isCorrect || (choice.scoreDelta && choice.scoreDelta > 5)) {
      scene.availableEvidence.forEach(onDiscover);
      sfx.discover();
    }
    if (choice.scoreDelta) onAddScore(choice.scoreDelta);
    if (choice.isDeadly) {
      sfx.death();
      setFeedback({ text: choice.deathMessage || choice.consequence, deadly: true });
      setTimeout(() => { setDead(true); onDeath(); }, 2200);
      return;
    }
    if (choice.isCorrect) sfx.correct();
    else if (choice.scoreDelta && choice.scoreDelta < 0) sfx.wrong();
    setFeedback({ text: choice.consequence, correct: choice.isCorrect });
    if (scene.isClimax && choice.isCorrect) {
      setTimeout(() => { setResolved(true); sfx.complete(); onComplete(caseId, caseData.rewards.xp); }, 1800);
    } else if (choice.leadsTo) {
      setTimeout(() => {
        const next = caseData.scenes.findIndex(s => s.id === choice.leadsTo);
        if (next >= 0) { setSceneIndex(next); setFeedback(null); setChoiceMade(false); }
      }, 1500);
    } else if (!choice.isCorrect) {
      setTimeout(() => setChoiceMade(false), 1500);
    }
  };

  if (dead) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center px-6 text-center">
        <Skull className="w-16 h-16 text-crimson-500 mb-4" />
        <h2 className="font-serif text-3xl text-crimson-400 font-bold">You Are Dead</h2>
        <p className="text-noir-300 mt-3 max-w-md">{role.deathFlavor}</p>
        <p className="text-noir-500 text-sm mt-2">Lives remaining: {Math.max(0, state.lives - 1)}</p>
        <button onClick={onExit} className="mt-8 px-6 py-3 rounded-xl bg-noir-800 border border-noir-600 text-noir-100">Return to Case Files</button>
      </div>
    );
  }

  return (
    <div className="min-h-dvh flex flex-col">
      <header className="sticky top-0 z-20 border-b border-noir-800 bg-noir-950/90 backdrop-blur-md px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <button onClick={onExit} className="flex items-center gap-1.5 text-noir-400 text-sm"><ArrowLeft className="w-4 h-4" /> Exit</button>
          <div className="text-center">
            <p className="text-xs text-noir-500 uppercase tracking-widest">{caseData.title}</p>
            <p className="text-sm text-noir-200 flex items-center justify-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-accent-500" />{scene.location}</p>
          </div>
          <div className="flex items-center gap-3">
            <CharacterAvatar role={role} size="sm" />
            <span className="text-accent-400 font-mono text-sm">{state.score}</span>
            <span className="text-crimson-400 inline-flex items-center gap-0.5 text-sm"><Heart className="w-3.5 h-3.5" />{state.lives}</span>
          </div>
        </div>
      </header>
      <div className="flex-1 max-w-6xl mx-auto w-full px-4 py-6 grid lg:grid-cols-[1fr_280px] gap-6">
        <div className="space-y-6">
          <motion.div key={scene.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="p-6 rounded-2xl bg-noir-900/60 border border-noir-800">
            <h2 className="font-serif text-2xl text-noir-50 font-semibold">{scene.title}</h2>
            <p className="text-noir-300 leading-relaxed mt-4">{scene.narrative}</p>
          </motion.div>
          <AnimatePresence>
            {feedback && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className={clsx('p-4 rounded-xl border flex items-start gap-3',
                  feedback.deadly ? 'bg-crimson-500/15 border-crimson-500/40 text-crimson-300'
                    : feedback.correct ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-noir-800 border-noir-600 text-noir-200')}>
                {feedback.deadly ? <Skull className="w-5 h-5 text-crimson-400 shrink-0" /> : feedback.correct ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" /> : <XCircle className="w-5 h-5 text-noir-400 shrink-0" />}
                <p className="text-sm">{feedback.text}</p>
              </motion.div>
            )}
          </AnimatePresence>
          {!resolved && !dead && (
            <div className="space-y-3">
              <h3 className="text-xs uppercase tracking-widest text-noir-400">Your Move — choose carefully</h3>
              {scene.choices.map((choice, i) => {
                const missingTool = choice.requiresTool && !state.inventory.find(t => t.id === choice.requiresTool && t.uses > 0);
                return (
                  <motion.button key={choice.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
                    disabled={choiceMade || !!missingTool} onClick={() => handleChoice(choice)}
                    className={clsx('w-full text-left p-4 rounded-xl border transition-all',
                      choiceMade || missingTool ? 'opacity-40 cursor-not-allowed border-noir-800' : 'border-noir-700 bg-noir-900/70 hover:border-accent-500/50')}>
                    <p className="text-noir-100 text-sm">{choice.text}</p>
                    {missingTool && <p className="text-xs text-crimson-400 mt-1">Requires tool</p>}
                  </motion.button>
                );
              })}
            </div>
          )}
          {resolved && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
              <h3 className="font-serif text-2xl text-emerald-300 font-semibold">Case Closed — You Survived</h3>
              <p className="text-noir-300 mt-2 text-sm">{caseData.solution}</p>
              <p className="text-accent-400 mt-4">+{caseData.rewards.xp} XP{caseData.rewards.title && ` · ${caseData.rewards.title}`}</p>
              <button onClick={onExit} className="mt-6 px-6 py-2.5 rounded-xl bg-accent-500 text-noir-950 font-semibold">Return</button>
            </motion.div>
          )}
        </div>
        <aside className="space-y-4">
          <div className="p-4 rounded-2xl bg-noir-900/60 border border-noir-800">
            <p className="text-xs uppercase tracking-widest text-noir-400 mb-2">Tools</p>
            <div className="flex flex-wrap gap-2">
              {state.inventory.map(t => (
                <button key={t.id} onClick={() => t.uses > 0 && (sfx.ui(), onUseTool(t.id))} disabled={t.uses <= 0}
                  className={clsx('px-2 py-1 rounded-lg border text-xs', t.uses > 0 ? 'border-noir-600' : 'border-noir-800 text-noir-600')}
                  title={t.description}>{t.icon} {t.uses}</button>
              ))}
            </div>
            <button onClick={() => { sfx.discover(); scene.availableEvidence.forEach(onDiscover); }} className="mt-2 text-xs text-noir-400 hover:text-accent-400">Examine scene</button>
          </div>
          <div className="p-4 rounded-2xl bg-noir-900/60 border border-noir-800 space-y-2">
            <p className="text-xs uppercase tracking-widest text-noir-400">Evidence</p>
            {evidenceList.filter(e => state.discoveredEvidence.includes(e.id)).map(ev => (
              <div key={ev.id} className="p-2 rounded-lg border border-noir-700 text-xs">
                <p className="font-medium text-noir-100">{ev.name}</p>
                <p className="text-noir-400">{ev.description}</p>
              </div>
            ))}
            {evidenceList.filter(e => state.discoveredEvidence.includes(e.id)).length === 0 && <p className="text-noir-500 text-sm italic">None yet</p>}
          </div>
        </aside>
      </div>
    </div>
  );
}
