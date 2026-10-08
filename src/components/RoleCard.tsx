import { motion } from 'framer-motion';
import type { Role } from '../types';
import { CharacterAvatar } from './CharacterAvatar';
import clsx from 'clsx';
import { sfx } from '../lib/sound';

export function RoleCard({ role, selected, onSelect }: { role: Role; selected: boolean; onSelect: () => void }) {
  return (
    <motion.button
      whileHover={{ scale: 1.03, y: -4 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => { sfx.select(); onSelect(); }}
      className={clsx(
        'relative w-full text-left p-5 rounded-2xl border transition-all bg-noir-900/80',
        selected
          ? 'border-accent-500 shadow-[0_0_30px_rgba(245,158,11,0.25)]'
          : 'border-noir-700 hover:border-noir-500'
      )}
    >
      <div className='flex items-start gap-4'>
        <CharacterAvatar role={role} size='sm' />
        <div className='flex-1 min-w-0'>
          <h3 className='font-serif text-xl text-noir-50 font-semibold'>{role.name}</h3>
          <p className='text-accent-400 text-sm mt-0.5'>{role.title}</p>
          <p className='text-noir-300 text-sm mt-2 line-clamp-2'>{role.description}</p>
        </div>
      </div>
      {selected && (
        <div className='absolute top-3 right-3 w-2.5 h-2.5 rounded-full bg-accent-500' />
      )}
    </motion.button>
  );
}
