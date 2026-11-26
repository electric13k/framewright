// Puts the cached cast figures (figure.js) into the scene and poses them from state.figures each frame.
// state.figures: [{ id, place, x, z, ry, walk?: speed, pose?: { armL, armR, legL, legR, tilt } }]
import { figure, pose, walk } from './figure.js';
import { PLACES } from './world.js';

export function buildRig(camera) {
  const live = new Map(); // id -> instance, created on first use and kept
  const scene = camera.parent;
  return {
    update(t, s) {
      for (const f of live.values()) f.visible = false;
      for (const d of s.figures || []) {
        if (!live.has(d.id)) { const f = figure(d.id); live.set(d.id, f); scene.add(f); }
        const f = live.get(d.id);
        f.visible = true;
        f.position.set((PLACES[d.place] || 0) + (d.x || 0), 0, d.z || 0);
        f.rotation.y = d.ry || 0;
        if (d.walk) walk(f, t, d.walk); else pose(f, d.pose || {});
      }
    },
  };
}
