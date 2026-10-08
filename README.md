# Tactica24

**Think. Deduce. Survive.**

Intellectual case-solving game. Choose a role. Each role has dedicated cases. **Wrong choices can kill you.**

## Roles (each with own cases)

| Role | Cases | Risk |
|------|-------|------|
| Detective | Shadow Vault, Silent Ward | Traps, ambushes |
| Criminal | The Debt Mark | Betrayal, hits |
| Police | No-Knock Night | Breach mistakes |
| Military | Grid Seven | Kill zones |
| Plumber | Pipe Dream | Live systems |
| Hacker | Signal Ghost | Trace-backs |
| Doctor | Cold Sample | Pathogen exposure |

## Play (Web / Laptop)

```bash
npm install
npm run dev
```

## Desktop (Electron)

```bash
npm install
npm run build
npm run electron:pack   # installers in /release
```

## Mobile

1. **PWA**: Open web build in Chrome/Safari → Add to Home Screen.
2. **Capacitor** (native Android/iOS):
   ```bash
   npm install @capacitor/core @capacitor/cli
   npx cap init Tactica24 com.tactica24.game
   npm run build && npx cap add android && npx cap add ios
   npx cap sync && npx cap open android
   ```

## Mechanics

- Lives (3 start; +1 on win; -1 on death)
- Deadly choices = instant death for that run
- Evidence combination at climax
- Progressive unlock per role
- SVG role avatars with uniforms

## License

MIT
