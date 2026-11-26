"""Series title card frames (PIL, run with the system python): the series name is typed over scrambled cyan
glyphs, a cyan scan bar sweeps down with an RGB split, a red rule grows, then SEASON/EPISODE and the title type on.

Usage: python -I title_card.py <font.ttf> <out dir> <seconds> <series> <season> <episode> <title>
Writes <out dir>/000.png...; prints JSON [letter_times, scan_start] for the audio.
"""
import json
import random
import sys
from pathlib import Path

W, H_PX, FPS = 1080, 1920, 30
def make_title_frames(font, out_dir, d, series, season, episode, title, seed=7):
    """Series title card, drawn frame by frame with PIL: the series name is typed over scrambled cyan glyphs,
    a cyan scan bar sweeps down with an RGB split, a red rule grows, then SEASON/EPISODE and the title type on.
    Returns the letter times (s) so the audio can tick on each one."""
    from PIL import Image, ImageDraw, ImageFont
    rnd = random.Random(seed)
    out_dir.mkdir(exist_ok=True)
    word = series.upper()
    size = 176
    while ImageFont.truetype(str(font), size).getlength(word) > 930 and size > 60:
        size -= 6
    big, sub, ttl = (ImageFont.truetype(str(font), s) for s in (size, 46, 54))
    cy = int(H_PX * 0.42)
    lt = [0.08 + i * 0.05 for i in range(len(word))]
    scan0, scan1 = lt[-1] + 0.12, lt[-1] + 0.42
    sub_t, ttl_t = scan1 + 0.05, scan1 + 0.25
    ink, bone, cyan, red = (11, 15, 20), (241, 238, 233), (53, 224, 208), (229, 72, 77)
    glyphs = "#%&@$*+=?/<>[]{}01"
    grain = [Image.effect_noise((W // 2, H_PX // 2), 24).resize((W, H_PX)) for _ in range(4)]
    n = int(round(d * FPS))
    for f in range(n):
        t = f / FPS
        im = Image.new("RGB", (W, H_PX), ink)
        dr = ImageDraw.Draw(im)
        for y in range(0, H_PX, 6):  # faint CRT lines
            dr.line([(0, y), (W, y)], fill=(15, 20, 27))
        x0 = (W - big.getlength(word)) / 2
        scanning = scan0 <= t < scan1
        split = 10 if scanning else (4 if t < scan1 + 0.1 else 0)
        x = x0
        for i, ch in enumerate(word):
            w = big.getlength(ch)
            if t >= lt[i]:
                c = bone if t >= lt[i] + 0.07 else cyan
                g = ch if t >= lt[i] + 0.07 else rnd.choice(glyphs)
                if split and c == bone:
                    dr.text((x - split, cy), g, font=big, fill=red, anchor="lm")
                    dr.text((x + split, cy), g, font=big, fill=cyan, anchor="lm")
                dr.text((x, cy), g, font=big, fill=c, anchor="lm")
            elif i == next((k for k, v in enumerate(lt) if t < v), None) and int(t * 12) % 2 == 0:
                dr.rectangle([x, cy - size * 0.36, x + w * 0.7, cy + size * 0.36], fill=cyan)
            x += w
        if scanning:
            yb = int((t - scan0) / (scan1 - scan0) * H_PX)
            dr.rectangle([0, yb - 3, W, yb + 3], fill=cyan)
            dr.rectangle([0, yb - 40, W, yb - 3], fill=(18, 60, 62))
        if t >= scan1:
            k = min(1.0, (t - scan1) / 0.25)
            half = int(320 * (1 - (1 - k) ** 3))
            dr.rectangle([W // 2 - half, cy + size * 0.64, W // 2 + half, cy + size * 0.64 + 6], fill=red)
        if t >= sub_t:
            a = min(1.0, (t - sub_t) / 0.2)
            col = tuple(int(ink[j] + (bone[j] - ink[j]) * a) for j in range(3))
            dr.text((W / 2, cy + size * 0.64 + 70 + 20 * (1 - a)), f"SEASON {season}  \u00b7  EPISODE {episode}",
                    font=sub, fill=col, anchor="mm")
        if t >= ttl_t:
            m = min(len(title), int((t - ttl_t) / 0.035) + 1)
            txt = title[:m] + ("_" if int(t * 6) % 2 == 0 else " ")
            dr.text((W / 2, cy + size * 0.64 + 160), txt, font=ttl, fill=(205, 202, 197), anchor="mm")
        if t > d - 0.2:  # fade out with one glitch flash
            k = (t - (d - 0.2)) / 0.2
            im = Image.blend(im, Image.new("RGB", (W, H_PX), ink), min(1.0, k))
        im = Image.blend(im, Image.merge("RGB", [grain[f % 4]] * 3), 0.05)
        im.save(out_dir / f"{f:03d}.png")
    return [lt, scan0]


if __name__ == "__main__":
    f, o, d, se, sn, ep, ti = sys.argv[1:8]
    print(json.dumps(make_title_frames(Path(f), Path(o), float(d), se, sn, ep, ti)))
