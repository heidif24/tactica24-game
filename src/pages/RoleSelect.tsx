import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { ROLES } from '../data/roles';
import { RoleCard } from '../components/RoleCard';
import { CharacterAvatar } from '../components/CharacterAvatar';
import type { RoleId } from '../types';
import { sfx } from '../lib/sound';
export function RoleSelect({ onConfirm, onBack }: { onConfirm: (role: RoleId, name: string) => void; onBack: () => void }) {
  const [selected, setSelected] = useState<RoleId | null>(null);
  const [name, setName] = useState('');
  const role = ROLES.find(r => r.id === selected);
  return (
    <div className="min-h-dvh px-4 py-10 sm:px-8 max-w-5xl mx-auto">
      <button onClick={onBack} className="text-noir-400 text-sm mb-6">← Back</button>
      <div className="flex flex-col sm:flex-row sm:items-end gap-6 mb-8">
        <div className="flex-1">
          <h1 className="font-serif text-3xl font-bold text-noir-50">Choose Your Role</h1>
          <p className="text-noir-400 mt-2">Each role has unique cases. Wrong choices can be fatal.</p>
        </div>
        {role && <CharacterAvatar role={role} size="lg" showLabel />}
      </div>
      <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Callsign"
        className="w-full max-w-sm px-4 py-3 rounded-xl bg-noir-900 border border-noir-700 text-noir-100 mb-6 focus:outline-none focus:border-accent-500" />
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {ROLES.map((r, i) => (
          <motion.div key={r.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <RoleCard role={r} selected={selected === r.id} onSelect={() => setSelected(r.id)} />
          </motion.div>
        ))}
      </div>
      <div className="mt-10 flex justify-end">
        <button disabled={!selected} onClick={() => selected && (sfx.select(), onConfirm(selected, name))}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-accent-500 text-noir-950 font-semibold disabled:opacity-40">
          Confirm Role <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
