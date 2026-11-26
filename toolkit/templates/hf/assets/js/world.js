// Sets. Each place is built ONCE at load at its own x offset and reused; state.place picks what the camera sees.
// Add a place as one function + one entry in PLACES. Keep sets few (max 6 per season) and reuse them.
import * as THREE from '../vendor/three.module.js';

const mat = (c) => new THREE.MeshLambertMaterial({ color: c });

function room(scene, x0, { floor = '#3a2c22', wall = '#27313b', lamp = '#ffcf9a' } = {}) {
  const g = new THREE.Group(); g.position.x = x0; scene.add(g);
  const f = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), mat(floor)); f.rotation.x = -Math.PI / 2; g.add(f);
  const back = new THREE.Mesh(new THREE.PlaneGeometry(12, 4), mat(wall)); back.position.set(0, 2, -4); g.add(back);
  const side = new THREE.Mesh(new THREE.PlaneGeometry(12, 4), mat(wall)); side.position.set(-4, 2, 0); side.rotation.y = Math.PI / 2; g.add(side);
  const light = new THREE.PointLight(lamp, 60, 14, 1.4); light.position.set(1, 2.6, -1); g.add(light);
  return g;
}

export const PLACES = { room: 0, street: 100 }; // x offsets

export function buildWorld() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0b0f14');
  scene.fog = new THREE.Fog('#0b0f14', 6, 40);
  scene.add(new THREE.HemisphereLight('#8a9ab0', '#1b2129', 1.6));
  room(scene, PLACES.room);
  room(scene, PLACES.street, { floor: '#1b2129', wall: '#1d2733', lamp: '#ffb070' });
  return {
    scene,
    attach() {},
    update(/* t, cam, state */) {},
  };
}
