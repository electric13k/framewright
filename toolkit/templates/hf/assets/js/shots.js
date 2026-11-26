// Shots: camera keys, who is where, and the grade, all as functions of timeline time t (deterministic).
// Times come from the voice: Ls(i, dt) = start of script line i + dt; m('mark', dt) = a named mark + dt.
// Rules: a new visual every 3-4 s (cut, not drift); wide enough to read; phone inserts close (fov < 30).
import { track, seg, ease, noise, clamp } from './util.js';
import { DUR, MARK, LINES } from './episode.js';
import { PLACES } from './world.js';

export const Ls = (i, dt = 0) => LINES[i][0] + dt;
export const m = (k, dt = 0) => (MARK[k] ?? 0) + dt;
const H = (place, x, y, z) => [(PLACES[place] || 0) + x, y, z];

// ---- camera keys: go(time, pose, ease); cut(time, pose). A pose is { p, yaw, pitch, roll, fov }.
const keys = [];
let last = null;
function look(p, tgt) { const dx = tgt[0] - p[0], dy = tgt[1] - p[1], dz = tgt[2] - p[2]; return [Math.atan2(-dx, -dz), Math.atan2(dy, Math.hypot(dx, dz))]; }
function at(p, tgt, fov) { const [yaw, pitch] = look(p, tgt); return { p, yaw, pitch, roll: 0, fov }; }
function go(t, pose, e = 'sine') {
  if (e === 'whip' && last) { keys.push([t - 0.001, ...last.p, last.yaw, last.pitch, last.roll, last.fov, 'lin']); e = 'lin'; } // calm: whip = cut
  last = pose; keys.push([t, ...pose.p, pose.yaw, pose.pitch, pose.roll, pose.fov, e]);
}
const cut = (t, pose) => go(t, pose, 'whip');

// ---- example episode: replace with this episode's shots
cut(0, at(H('room', 0.6, 1.7, 5.2), H('room', -0.2, 1.1, -0.6), 52));      // establish: both figures, the room
go(Ls(0, 1.2), at(H('room', 0.4, 1.6, 4.6), H('room', -0.2, 1.1, -0.6), 50));
cut(Ls(1, 0), at(H('room', 2.6, 1.4, 1.6), H('room', -1.4, 1.1, -1.2), 44)); // new angle on the next line
go(DUR, at(H('room', 2.4, 1.4, 1.4), H('room', -1.4, 1.1, -1.2), 42));

export function camAt(t) {
  const [x, y, z, yaw, pitch, roll, fov] = track(keys, t);
  const hand = 0.0025 * clamp(fov / 52, 0.15, 1); // faint drift only
  return { x: x + 0.004 * noise(t * 0.7, 1), y, z, yaw: yaw + hand * noise(t * 1.1, 2), pitch: pitch + hand * noise(t * 1.3, 3), roll, fov };
}

// ---- rewind (interactive series): the wrong turn plays backwards on its own frames. No marks = no rewind.
const T_HIT = MARK.wrongEnd != null ? m('wrongEnd', 0.55) : null, T_RW0 = T_HIT != null ? m('wrongEnd', 1.35) : null, T_OPEN = MARK.open;
export function warp(t) {
  if (T_HIT == null || t < T_HIT) return t;
  if (t < T_RW0) return T_HIT;
  if (t < T_OPEN) return Math.max(0, T_HIT * (1 - ease.sine((t - T_RW0) / (T_OPEN - T_RW0))));
  return t;
}
export function rewAt(t) { return T_HIT == null ? 0 : seg(t, T_RW0, T_RW0 + 0.06) * (1 - seg(t, T_OPEN - 0.14, T_OPEN)); }
export function deathAt(t) { // cyan flood, then black with an ember flatline, in real time over the freeze
  if (T_HIT == null) return { cyan: 0, dead: 0 };
  return { cyan: 3.2 * ease.sine(seg(t, T_HIT, T_HIT + 0.3)) * (t < T_RW0 + 0.05 ? 1 : 0),
           dead: ease.sine(seg(t, T_HIT + 0.15, T_RW0 - 0.02)) * (1 - seg(t, T_RW0, T_RW0 + 0.12)) };
}

export function stateAt(t) {
  return {
    cam: camAt(t),
    place: 'room',
    figures: [
      { id: 'hero', place: 'room', x: 0.9, z: 0.4, ry: -0.5, pose: { armL: 0.15, armR: -0.15 } },
      { id: 'mother', place: 'room', x: -1.3, z: -1.4, ry: 0.6, walk: t > Ls(1, 0) ? 0.6 : 0 },
    ],
    grade: { hush: 0, cyan: 0, flash: 0, dead: 0 },
  };
}
