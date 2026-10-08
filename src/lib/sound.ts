/** Lightweight procedural SFX via Web Audio — no external files needed */

let ctx: AudioContext | null = null;
let enabled = true;

function getCtx() {
  if (!ctx) ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  return ctx;
}

export function setSoundEnabled(v: boolean) {
  enabled = v;
}

export function playTone(freq: number, duration: number, type: OscillatorType = 'sine', gain = 0.08) {
  if (!enabled) return;
  try {
    const c = getCtx();
    const osc = c.createOscillator();
    const g = c.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(gain, c.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
    osc.connect(g);
    g.connect(c.destination);
    osc.start();
    osc.stop(c.currentTime + duration);
  } catch {}
}

export const sfx = {
  click: () => playTone(420, 0.06, 'square', 0.04),
  select: () => { playTone(520, 0.08, 'sine', 0.06); setTimeout(() => playTone(680, 0.1, 'sine', 0.05), 60); },
  discover: () => { playTone(600, 0.1, 'triangle', 0.07); setTimeout(() => playTone(900, 0.15, 'triangle', 0.05), 80); },
  correct: () => {
    playTone(523, 0.12, 'sine', 0.08);
    setTimeout(() => playTone(659, 0.12, 'sine', 0.08), 100);
    setTimeout(() => playTone(784, 0.2, 'sine', 0.07), 200);
  },
  wrong: () => playTone(180, 0.25, 'sawtooth', 0.06),
  complete: () => {
    [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => playTone(f, 0.2, 'sine', 0.07), i * 120));
  },
  ui: () => playTone(300, 0.04, 'square', 0.03),
};
