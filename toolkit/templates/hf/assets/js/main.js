// Renders one frame of the street for timeline time t. Driven by HyperFrames' hf-seek event.
import * as THREE from '../vendor/three.module.js';
import { buildWorld } from './world.js';
import { buildRig } from './rig.js';
import { stateAt, camAt, warp, rewAt, deathAt } from './shots.js';
import { hash } from './util.js';

const W = 1080, H = 1920;
const el = document.getElementById('street');
const renderer = new THREE.WebGLRenderer({ canvas: el, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;

window.__hf = window.__hf || {};
window.__hf.buildReady = window.__hf.buildReady || {};
const fonts = Promise.all(['400 30px Inter', '700 30px Inter', '900 30px Inter', '300 30px Inter'].map((f) => document.fonts.load(f)));
let ready; window.__hf.buildReady.street = new Promise((r) => (ready = r)); // resolves once the set is built and listening
await fonts; // textures paint text, so fonts must be in before the set is drawn

const camera = new THREE.PerspectiveCamera(52, W / H, 0.02, 1200);
camera.rotation.order = 'YXZ';
const world = buildWorld();
world.scene.add(camera);
const rig = buildRig(camera);
world.attach(camera);
const [osdC, osdG] = canvasOsd(); const osdT = new THREE.CanvasTexture(osdC); osdT.colorSpace = THREE.SRGBColorSpace;
function canvasOsd() { const c = document.createElement('canvas'); c.width = 512; c.height = 116; return [c, c.getContext('2d')]; }
function drawOsd(t) { // tape deck on-screen display: two arrows going back, REW, a running counter
  osdG.clearRect(0, 0, 512, 116); osdG.fillStyle = '#f1eee9'; const sh = (Math.round(t * 30) % 6) * 2;
  for (const x of [8 + sh, 58 + sh]) { osdG.beginPath(); osdG.moveTo(x + 44, 18); osdG.lineTo(x, 58); osdG.lineTo(x + 44, 98); osdG.fill(); }
  osdG.font = '900 76px Inter, sans-serif'; osdG.fillText('REW', 130, 88); osdG.font = '700 34px Inter, sans-serif'; osdG.fillText('SP  0:' + String(Math.floor(((t * 37) % 60))).padStart(2, '0'), 340, 88);
  osdT.needsUpdate = true;
}

const rt = new THREE.WebGLRenderTarget(W, H, { samples: 4 });
rt.texture.colorSpace = THREE.SRGBColorSpace;
const post = new THREE.ShaderMaterial({
  uniforms: { tScene: { value: rt.texture }, vel: { value: new THREE.Vector2() }, zoom: { value: 0 }, seed: { value: 0 }, hush: { value: 0 }, cyan: { value: 0 }, dead: { value: 0 }, rew: { value: 0 }, flash: { value: 0 }, tt: { value: 0 }, tOsd: { value: osdT } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }',
  fragmentShader: `
    varying vec2 vUv; uniform sampler2D tScene; uniform vec2 vel; uniform float zoom, seed, hush, cyan, dead, rew, flash, tt; uniform sampler2D tOsd;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + seed) * 43758.5453); }
    void main(){
      vec2 vuv = vUv; float fr = floor(tt * 30.), trk = 0., fx = 0.;
      if (rew > 0.) { // VHS rewind: torn bands, a rolling tracking bar, colour fringing
        float band = floor(vUv.y * 48.);
        float tear = step(.7, h(vec2(band, fr))) * (h(vec2(band + 7., fr)) - .5) * .24 * rew;
        trk = smoothstep(.09, 0., abs(vUv.y - fract(tt * 1.9)));
        tear += trk * (h(vec2(floor(vUv.y * 220.), fr)) - .5) * .14 * rew;
        vuv.x += tear; fx = .011 * rew;
      }
      vec2 c = vuv - .5; vec3 col = vec3(0.); float n = 0.;
      for (int i = 0; i < 18; i++) { // directional blur from camera turn + radial blur from zoom/dolly
        float k = float(i) / 17. - .5;
        vec2 uv = vuv + vel * k - c * zoom * k;
        float ca = length(vel) * .12 + zoom * .08 + .0012 * dot(c, c);
        col += vec3(texture2D(tScene, uv + c * ca + vec2(fx, 0.)).r, texture2D(tScene, uv).g, texture2D(tScene, uv - c * ca - vec2(fx, 0.)).b); n += 1.;
      }
      col /= n; col *= 1.12;
      float l = dot(col, vec3(.2126, .7152, .0722));
      col = mix(col, vec3(l), .25 * hush);                       // the hush drains colour
      col *= mix(vec3(1.), vec3(.86, .95, 1.06), .35);              // cool night grade
      col = mix(col, col * vec3(.8, 1.08, 1.05), .25 * cyan);
      float v = 1. - .55 * smoothstep(.28, .82, length(c * vec2(1., .62)));
      col *= v * (1. - .25 * hush);
      if (dead > 0.) { // death/taken: colour drains, black closes from the edges, ember flatline with one blip
        col = mix(col, vec3(dot(col, vec3(.2126, .7152, .0722))), clamp(dead * 1.6, 0., 1.));
        float ed = length(c * vec2(1., .8)) / .72, cl = 1. - dead * 1.15;
        col *= smoothstep(cl, cl - .35, ed) * (1. - .5 * dead);
        float lp = smoothstep(.62, .9, dead), fx2 = vUv.x - .5, blip = (1. - smoothstep(.55, 1., dead)) * exp(-pow((fx2 + .12) / .018, 2.)) * sin((fx2 + .12) * 260.) * .07;
        float ly = abs(vUv.y - .5 - blip);
        col += vec3(.992, .514, .345) * lp * (smoothstep(.004, 0., ly) + .25 * smoothstep(.02, 0., ly)) * smoothstep(.5, .12, abs(fx2));
      }
      if (rew > 0.) {
        float sy = floor(vUv.y * 90.), sr = h(vec2(sy, fr + 3.));
        float streak = step(.92, sr) * (.4 + .6 * h(vec2(sy, 1.))) * exp(-abs(vUv.x - fract(sr * 13. + tt * 3.)) * 3.2);
        col += vec3(1., .5, .28) * streak * rew;                      // ember streaks
        col += trk * rew * (h(vUv * 500. + tt) - .5) * .8;            // tape snow in the tracking bar
        float l2 = dot(col, vec3(.2126, .7152, .0722));
        col = mix(col, vec3(l2) * vec3(1.12, .94, .78), .38 * rew) * (1. + .25 * rew) * (1. - .14 * rew * (.5 + .5 * sin(vUv.y * 1500.)));
        vec2 q = (vUv - vec2(.08, .82)) / vec2(.47, .06);
        if (q.x > 0. && q.x < 1. && q.y > 0. && q.y < 1.) { vec4 o = texture2D(tOsd, vec2(q.x, q.y)); col = mix(col, o.rgb, o.a * rew); }
      }
      col = col * (1. + 1.1 * flash) + flash * .22;                    // every light comes on
      col += (h(vUv * 913.) - .5) * .06;                           // grain, seeded per frame
      gl_FragColor = vec4(col, 1.);
    }`,
  depthTest: false, depthWrite: false,
});
const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), post);
const postScene = new THREE.Scene(); postScene.add(quad);
const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

function place(c) {
  camera.position.set(c.x, c.y, c.z);
  camera.rotation.set(c.pitch, c.yaw, c.roll);
  camera.fov = c.fov; camera.updateProjectionMatrix();
}

function renderAt(t) {
  const ts = warp(t), s = stateAt(ts), c = s.cam, p = camAt(warp(Math.max(0, t - 1 / 30)));
  const rw = rewAt(t); if (rw > 0) drawOsd(t);
  place(c);
  world.update(ts, c, s);
  rig.update(ts, s);
  const vf = (c.fov * Math.PI) / 180, hf = 2 * Math.atan(Math.tan(vf / 2) * (W / H));
  const vx = (c.yaw - p.yaw) / hf, vy = -(c.pitch - p.pitch) / vf;
  const mag = Math.hypot(vx, vy), lim = 0.03, k = mag > lim ? lim / mag : 1;
  post.uniforms.vel.value.set(vx * k * 0.9, vy * k * 0.9);
  post.uniforms.zoom.value = Math.min(0.04, Math.abs(c.fov - p.fov) / c.fov * 1.4 + Math.abs(c.z - p.z) * 0.012);
  post.uniforms.seed.value = hash(Math.round(t * 30)) * 100; post.uniforms.rew.value = rw; post.uniforms.tt.value = t; post.uniforms.flash.value = s.grade.flash;
  const dz = deathAt(t); post.uniforms.hush.value = s.grade.hush; post.uniforms.cyan.value = Math.max(s.grade.cyan, dz.cyan); post.uniforms.dead.value = Math.max(s.grade.dead || 0, dz.dead);
  renderer.setRenderTarget(rt); renderer.render(world.scene, camera);
  renderer.setRenderTarget(null); renderer.render(postScene, postCam);
}

window.addEventListener('hf-seek', (e) => renderAt(e.detail.time));
renderAt(0);
ready();
