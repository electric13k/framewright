"""Create the folder for a new episode from the episode 1 engine.

Usage:
  python new_episode.py 2 --script ../plotkit/episodes/ep02.script.json
  python new_episode.py 3 --script <series>/ep03.script.json --from <series>/ep02

Creates <series_root>/epNN with:
  shared engine, copied unchanged from --from (default: the previous episode, else episode 1):
    hf/assets/vendor/three.module.js, hf/assets/js/{main,util,rig,tex}.js, hf/hyperframes.json, hf/package.json
  the set, copied from --from so the world carries forward, then edited for this episode:
    hf/assets/js/world.js (the 3D set), phone.js (phone screens), every other set module (garden.js, interior.js),
    and shots.js (rewrite its shots; keep its exports)
  reset to the template (episode-specific):
    hf/gen.mjs, audio/score.py, audio/score.json (recorded CC0 beds), script.json
  empty: voice/, out/, stills/
It never touches episode 1 and refuses to overwrite an existing folder.
"""
import argparse, json, shutil, sys, time
from pathlib import Path

KIT = Path(__file__).resolve().parent
TPL = KIT / 'templates'
PATHS = {'series_root': '.'}
SHARED = ['main.js', 'util.js', 'rig.js', 'tex.js']
SET = ['world.js', 'phone.js']  # plus every other set module in the source js folder (garden.js, interior.js, ...)


def fail(msg):
    print(f'new_episode: {msg}', file=sys.stderr)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('number', type=int, help='episode number, 2..30')
    ap.add_argument('--script', help='script.json to install (an episode file from plotkit/episodes or one you wrote)')
    ap.add_argument('--from', dest='src', help='episode folder to copy the engine and set from')
    ap.add_argument('--root', default=PATHS['series_root'], help='series folder (default from paths.json)')
    a = ap.parse_args()

    if not 1 <= a.number <= 30:
        fail('episode number must be 1..30')
    root = Path(a.root)
    dest = root / f'ep{a.number:02d}'
    if dest.exists():
        fail(f'{dest} already exists. Pick another number or move it aside yourself; this tool never overwrites.')
    ref = Path(PATHS['reference_episode'])
    prev = root / f'ep{a.number - 1:02d}'
    src = Path(a.src) if a.src else (prev if (prev / 'hf' / 'assets' / 'js' / 'world.js').exists() else ref)
    js = src / 'hf' / 'assets' / 'js'
    for f in SHARED + SET:
        if not (js / f).exists():
            fail(f'{js / f} is missing; --from must be an episode folder with hf/assets/js')
    vendor = src / 'hf' / 'assets' / 'vendor' / 'three.module.js'
    if not vendor.exists():
        vendor = ref / 'hf' / 'assets' / 'vendor' / 'three.module.js'

    script = None
    if a.script:
        sp = Path(a.script)
        if not sp.exists():
            fail(f'script not found: {sp}')
        script = json.loads(sp.read_text(encoding='utf-8'))
        if script.get('episode') != a.number:
            fail(f'{sp} is for episode {script.get("episode")}, not {a.number}')

    out_js = dest / 'hf' / 'assets' / 'js'
    out_js.mkdir(parents=True)
    (dest / 'hf' / 'assets' / 'vendor').mkdir(parents=True)
    for d in ('audio', 'voice', 'out', 'stills'):
        (dest / d).mkdir()
    shutil.copy2(vendor, dest / 'hf' / 'assets' / 'vendor' / 'three.module.js')
    skip = {'episode.js'}  # written by gen.mjs
    for f in sorted(p.name for p in js.glob('*.js')):
        if f not in skip:
            shutil.copy2(js / f, out_js / f)  # shots.js too: it keeps the warp/rewAt exports main.js imports; rewrite its shots
    for f in ('hyperframes.json', 'package.json'):
        shutil.copy2((src if (src / 'hf' / f).exists() else ref) / 'hf' / f, dest / 'hf' / f)
    (dest / 'hf' / 'meta.json').write_text(json.dumps({'id': f'ep{a.number:02d}', 'name': f'ep{a.number:02d}', 'createdAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}))
    shutil.copy2(TPL / 'gen.mjs', dest / 'hf' / 'gen.mjs')
    shutil.copy2(TPL / 'score.py', dest / 'audio' / 'score.py')
    shutil.copy2(TPL / 'score.json', dest / 'audio' / 'score.json')
    if script is None:
        script = json.loads((TPL / 'script.json').read_text(encoding='utf-8'))
        script['episode'] = a.number
    (dest / 'script.json').write_text(json.dumps(script, indent=1, ensure_ascii=False), encoding='utf-8')
    (dest / 'EPISODE.md').write_text(
        f'# Episode {a.number}\n\nCreated from {src}.\n\n'
        'Edit: script.json (words, marks, fx, choice), hf/assets/js/shots.js (camera, phone poses, story state), '
        'hf/assets/js/world.js (set), hf/assets/js/phone.js (phone screens), audio/score.json (music).\n'
        'Do not edit: hf/assets/js/{main,util,rig,tex}.js except to add a new texture function to tex.js; '
        'hf/index.html, captions.json, events.json, episode.json and assets/js/episode.js are written by gen.mjs.\n',
        encoding='utf-8')
    print(f'new_episode: created {dest} (engine and set from {src})')
    print(f'next: edit {dest / "script.json"}, then python {KIT / "build.py"} {dest} --until stills')


if __name__ == '__main__':
    main()
