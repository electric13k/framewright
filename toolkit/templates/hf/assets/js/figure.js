// One faceless figure per cast member, built from its spec in cast.js and cached: build once, clone per shot.
// Rules baked in: no face ever (plain head, helmet or mask), the outfit never changes between episodes,
// one recognition item per character (scarf, cap, bag...) so a viewer knows them in a 1-second silhouette.
import * as THREE from '../vendor/three.module.js';
import { CAST, INK, BONE } from './cast.js';

const cache = new Map();
const mat = (c) => new THREE.MeshBasicMaterial({ color: c, fog: false });
const outline = (r) => new THREE.Mesh(new THREE.SphereGeometry(r * 1.12, 18, 14), new THREE.MeshBasicMaterial({ color: INK, side: THREE.BackSide, fog: false }));

function limb(len, w, color) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, len, w), mat(color));
  m.geometry.translate(0, -len / 2, 0); // pivot at the top joint
  return m;
}

function head(spec) {
  const g = new THREE.Group(), r = 0.13 * (spec.scale || 1);
  const kind = spec.head || 'blank';
  if (kind === 'helmet') { // full helmet: shell in the outfit colour, dark visor, still no face
    g.add(new THREE.Mesh(new THREE.SphereGeometry(r, 20, 16), mat(spec.helmet || spec.top)), outline(r));
    const visor = new THREE.Mesh(new THREE.SphereGeometry(r * 1.01, 20, 10, -0.9, 1.8, 1.1, 0.7), mat('#0e1620'));
    visor.rotation.y = Math.PI / 2; g.add(visor);
  } else if (kind === 'mask') { // plain mask over a bone head: a flat oval plate, no features
    g.add(new THREE.Mesh(new THREE.SphereGeometry(r, 20, 16), mat(BONE)), outline(r));
    const plate = new THREE.Mesh(new THREE.CircleGeometry(r * 0.8, 24), mat(spec.mask || '#c9c2b6'));
    plate.position.z = r * 1.0; plate.scale.y = 1.2; g.add(plate);
  } else { // blank: the default, a plain bone-white circle with an ink outline
    g.add(new THREE.Mesh(new THREE.SphereGeometry(r, 20, 16), mat(BONE)), outline(r));
  }
  if (spec.hair) { const h = new THREE.Mesh(new THREE.SphereGeometry(r * 0.45, 12, 10), mat(spec.hair)); h.position.set(0, r * 0.85, -r * 0.4); g.add(h); }
  if (spec.cap) { const c = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.02, r * 1.05, r * 0.5, 20), mat(spec.cap)); c.position.y = r * 0.6; g.add(c); }
  return g;
}

function build(spec) {
  const s = spec.scale || 1, root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const hip = 0.9 * s, chest = 1.38 * s;
  const torso = new THREE.Mesh(new THREE.BoxGeometry(0.34 * s, chest - hip, 0.2 * s), mat(spec.top));
  torso.position.y = (hip + chest) / 2; body.add(torso);
  if (spec.skirt) { const k = new THREE.Mesh(new THREE.CylinderGeometry(0.17 * s, 0.27 * s, 0.55 * s, 16), mat(spec.skirt)); k.position.y = hip - 0.2 * s; body.add(k); }
  if (spec.apron) { const a = new THREE.Mesh(new THREE.BoxGeometry(0.22 * s, 0.5 * s, 0.02), mat(spec.apron)); a.position.set(0, hip + 0.05, 0.11 * s); body.add(a); }
  const parts = {};
  for (const side of [-1, 1]) {
    const arm = limb(0.56 * s, 0.07 * s, spec.sleeve || spec.top); arm.position.set(side * 0.2 * s, chest - 0.04, 0); body.add(arm);
    const leg = limb(0.88 * s, 0.09 * s, spec.legs || INK); leg.position.set(side * 0.09 * s, hip, 0); body.add(leg);
    parts[side < 0 ? 'armL' : 'armR'] = arm; parts[side < 0 ? 'legL' : 'legR'] = leg;
  }
  const h = head(spec); h.position.y = chest + 0.16 * s; body.add(h); parts.head = h;
  if (spec.scarf) { // the recognition item sits at the neck, always the same colour
    const sc = new THREE.Mesh(new THREE.TorusGeometry(0.12 * s, 0.045 * s, 8, 18), mat(spec.scarf)); sc.rotation.x = Math.PI / 2; sc.position.y = chest; body.add(sc);
    const tail = new THREE.Mesh(new THREE.BoxGeometry(0.07 * s, 0.3 * s, 0.03), mat(spec.scarf)); tail.position.set(0.08 * s, chest - 0.17 * s, 0.11 * s); body.add(tail);
  }
  if (spec.bag) { const b = new THREE.Mesh(new THREE.BoxGeometry(0.3 * s, 0.32 * s, 0.16 * s), mat(spec.bag)); b.position.set(0, chest - 0.18 * s, -0.19 * s); body.add(b); }
  root.userData.parts = parts;
  return root;
}

/** figure('mother') -> a new instance of the cached model; pose it through userData.parts. */
export function figure(id) {
  if (!CAST[id]) throw new Error(`cast.js has no "${id}"`);
  if (!cache.has(id)) cache.set(id, build(CAST[id]));
  const src = cache.get(id), inst = src.clone(true);
  const a = [], b = [];
  src.traverse((o) => a.push(o)); inst.traverse((o) => b.push(o)); // same order: map part refs onto the clone
  inst.userData.parts = Object.fromEntries(Object.entries(src.userData.parts).map(([k, v]) => [k, b[a.indexOf(v)]]));
  return inst;
}

/** Simple pose in radians: arm swing out, leg swing forward, head tilt. */
export function pose(f, { armL = 0.1, armR = -0.1, legL = 0, legR = 0, tilt = 0 } = {}) {
  const p = f.userData.parts;
  p.armL.rotation.z = -armL; p.armR.rotation.z = -armR; p.legL.rotation.x = legL; p.legR.rotation.x = legR; p.head.rotation.z = tilt;
}

/** Walk cycle driven by timeline time t (deterministic). */
export function walk(f, t, speed = 1) {
  const s = Math.sin(t * 6 * speed) * 0.45, p = f.userData.parts;
  pose(f, { armL: 0.1, armR: -0.1, legL: s, legR: -s });
  p.armL.rotation.x = -s; p.armR.rotation.x = s;
}
