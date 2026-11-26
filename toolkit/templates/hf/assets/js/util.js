// Seeded helpers: every random value comes from these so frames render identically.
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const seg = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
export function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let r = Math.imul(s ^ (s >>> 15), 1 | s);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
export const hash = (n) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
// 1D value noise, smooth, range -1..1
export function noise(x, seed = 0) {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(hash(i + seed * 57.3), hash(i + 1 + seed * 57.3), u) * 2 - 1;
}
export const ease = {
  lin: (t) => t,
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  out: (t) => 1 - Math.pow(1 - t, 3),
  expo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  whip: (t) => (t < 0.97 ? 0 : 1), // calm camera: a whip is a straight cut
  in: (t) => t * t * t,
};
// Keyframes: [[t, value(s)..., easeName]]. The ease on a key shapes the move INTO that key.
export function track(keys, t) {
  if (t <= keys[0][0]) return keys[0].slice(1, -1);
  for (let i = 1; i < keys.length; i++) {
    const k = keys[i];
    if (t <= k[0]) {
      const p = keys[i - 1], e = ease[k[k.length - 1]] || ease.sine;
      const u = e((t - p[0]) / (k[0] - p[0]));
      return k.slice(1, -1).map((v, j) => (typeof v === 'number' ? lerp(p[j + 1], v, u) : u < 0.5 ? p[j + 1] : v));
    }
  }
  return keys[keys.length - 1].slice(1, -1);
}
