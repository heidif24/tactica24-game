# Tactica24

**Think. Deduce. Solve.**

An intellectual case-solving game where you choose a role (Detective, Criminal, Police, Military, Plumber, Hacker, Doctor) and navigate escalating scenarios using tools, evidence, and pure deduction.

## Features

- **7 playable roles** with unique perspectives and strengths
- **3 fully interactive cases** with progressive unlock
- Evidence board, tool system, scoring & XP progression
- Beautiful dark noir aesthetic with smooth animations
- Persistent progress (localStorage)
- Fully responsive — works as **Web**, **PWA (installable app)**, and ready for **Desktop** (Electron / Tauri)

## Tech Stack

- React 19 + TypeScript
- Vite 8
- Tailwind CSS v4
- Framer Motion
- Lucide React

## Getting Started

```bash
# Install
npm install

# Development
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/     # UI building blocks
├── data/           # Roles, cases, tools, evidence
├── hooks/          # useGameState (persistence)
├── pages/          # Landing, RoleSelect, CaseSelect, Investigation
├── types/          # TypeScript interfaces
└── App.tsx         # Screen router
```

## Adding New Cases

1. Add evidence entries in `src/data/evidence.ts`
2. Define the case (scenes, choices, solution) in `src/data/cases.ts`
3. Cases unlock progressively after completing the previous one

## License

MIT — built for the community.

---

*Tactica24 — Every decision shapes the outcome.*
