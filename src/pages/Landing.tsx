import { motion } from 'framer-motion';
import { ChevronRight, Volume2, VolumeX, Skull } from 'lucide-react';
import { sfx } from '../lib/sound';
export function Landing({ onStart, soundEnabled, onToggleSound }: { onStart: () => void; soundEnabled: boolean; onToggleSound: () => void }) {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center px-6 relative overflow-hidden">
      <button onClick={() => { onToggleSound(); sfx.ui(); }} className="absolute top-6 right-6 p-2 rounded-xl border border-noir-700 text-noir-400">
        {soundEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
      </button>
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="text-center max-w-2xl">
        <p className="text-accent-400 text-sm tracking-[0.3em] uppercase font-medium mb-4">Deadly Stakes · Intellectual Cases</p>
        <h1 className="font-serif text-5xl sm:text-7xl font-bold text-noir-50">Tactica<span className="text-accent-500">24</span></h1>
        <p className="mt-6 text-noir-300 text-lg max-w-md mx-auto">Choose your role. Gather evidence. One wrong move can kill you.</p>
        <div className="mt-4 flex items-center justify-center gap-2 text-crimson-400 text-sm"><Skull className="w-4 h-4" /> Wrong choices are fatal.</div>
        <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.97 }} onClick={() => { sfx.select(); onStart(); }}
          className="mt-10 inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-accent-500 text-noir-950 font-semibold text-lg animate-pulse-glow">
          Begin Investigation <ChevronRight className="w-5 h-5" />
        </motion.button>
        <p className="mt-8 text-noir-500 text-xs">Web · Mobile PWA · Desktop (Electron)</p>
      </motion.div>
    </div>
  );
}
