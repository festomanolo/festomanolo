#!/usr/bin/env python3
"""The Dual Arsenal, rendered as a gothic triptych altarpiece.
Left wing: CURSED of KNOWLEDGE (mortal iron). Centre: THE HEAVENLY UI/UX (gold).
Right wing: THE HELLISH STACK (blood). One slow rite lights the nine relics in turn.

Run: python forge/arsenal.py  ->  assets/arsenal.svg"""
import base64
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets"
GOLD, BLOOD, BONE, ASH, IRON = "#FFD700", "#FF0000", "#F2EEE6", "#8C8C8C", "#C9C3B8"

PANELS = [
    {"title": "CURSED of KNOWLEDGE", "sub": "Resonance. Effort. Undying Passion.", "tint": IRON, "deep": "#2A2622",
     "relics": [("Node.js", "nodedotjs"), ("Docker", "docker"), ("Linux", "linux")], "emblem": "chain"},
    {"title": "THE HEAVENLY UI/UX", "sub": "Aesthetic. Light. Divine Experience.", "tint": GOLD, "deep": "#3A2E00",
     "relics": [("Figma", "figma"), ("Adobe XD", None), ("Tailwind", "tailwindcss")], "emblem": "halo"},
    {"title": "THE HELLISH STACK", "sub": "Deep Learning. Raw Power. Algorithms.", "tint": BLOOD, "deep": "#3A0000",
     "relics": [("Python", "python"), ("TensorFlow", "tensorflow"), ("PyTorch", "pytorch")], "emblem": "horns"},
]

W, H = 900, 540
CYCLE = 9.0  # seconds for the rite to light all nine relics


def face(name, file, weight):
    b64 = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
    return f"@font-face{{font-family:'{name}';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def icon_path(slug):
    svg = (HERE / "icons" / f"{slug}.svg").read_text()
    return re.search(r'<path d="([^"]+)"', svg).group(1)


def arch(x, y, w, h, peak):
    """A pointed gothic arch panel: straight sides, two arcs meeting at a point."""
    r = w * 0.62
    return (f"M{x} {y+h} V{y+peak} A{r:.1f} {r:.1f} 0 0 1 {x+w/2} {y} "
            f"A{r:.1f} {r:.1f} 0 0 1 {x+w} {y+peak} V{y+h} Z")


def emblem(kind, cx, cy, tint):
    if kind == "halo":
        rays = "".join(f'<line x1="{cx}" y1="{cy-15}" x2="{cx}" y2="{cy-21}" stroke="{tint}" stroke-width="1.2" '
                       f'transform="rotate({a} {cx} {cy})"/>' for a in range(-60, 61, 20))
        return (f'{rays}<ellipse cx="{cx}" cy="{cy}" rx="13" ry="4.5" fill="none" stroke="{tint}" stroke-width="2"/>')
    if kind == "horns":
        return (f'<path d="M{cx-12} {cy+6} C{cx-16} {cy-4} {cx-12} {cy-14} {cx-4} {cy-18} C{cx-8} {cy-10} {cx-8} {cy-2} {cx-3} {cy+4}Z" fill="{tint}"/>'
                f'<path d="M{cx+12} {cy+6} C{cx+16} {cy-4} {cx+12} {cy-14} {cx+4} {cy-18} C{cx+8} {cy-10} {cx+8} {cy-2} {cx+3} {cy+4}Z" fill="{tint}"/>'
                f'<circle cx="{cx}" cy="{cy+4}" r="2.4" fill="{tint}"/>')
    # chain: three interlocked links
    return "".join(f'<rect x="{cx-17+i*11}" y="{cy-5}" width="14" height="10" rx="5" fill="none" stroke="{tint}" stroke-width="1.8"/>'
                   for i in range(3))


def build():
    css = [face("CinzelDeco", "cinzel-decorative-900.woff2", 900), face("Cinzel", "cinzel-700.woff2", 700),
           face("Cinzel", "cinzel-400.woff2", 400),
           "text{font-family:'Cinzel','Times New Roman',serif}.deco{font-family:'CinzelDeco','Cinzel',serif}",
           "@keyframes breathe{0%,100%{opacity:.35}50%{opacity:.8}}",
           "@keyframes drift{0%{transform:translateY(0);opacity:0}20%{opacity:.8}100%{transform:translateY(-60px);opacity:0}}",
           "@keyframes sink{0%{transform:translateY(0);opacity:0}20%{opacity:.8}100%{transform:translateY(60px);opacity:0}}",
           "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"]
    step = CYCLE / 9
    lit = step / CYCLE * 100
    # one relic "ignites" per step; shared keyframes, staggered by delay
    css.append(f"@keyframes ignite{{0%{{opacity:0}}{lit*0.25:.2f}%{{opacity:1}}{lit*1.6:.2f}%{{opacity:.0}}100%{{opacity:0}}}}")
    css.append(f"@keyframes kindle{{0%{{opacity:.25}}{lit*0.25:.2f}%{{opacity:1}}{lit*1.6:.2f}%{{opacity:.25}}100%{{opacity:.25}}}}")

    defs = [f'<filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="5" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
            f'<filter id="soft" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="9"/></filter>',
            f'<radialGradient id="bg" cx=".5" cy=".15" r=".9"><stop offset="0" stop-color="#1A1500"/><stop offset=".55" stop-color="#000"/></radialGradient>']
    body = [f'<rect width="{W}" height="{H}" fill="#000"/>', f'<rect width="{W}" height="{H}" fill="url(#bg)"/>']

    gap, side_w, mid_w = 18, 272, 300
    xs = [(W - (2 * side_w + mid_w + 2 * gap)) / 2]
    xs.append(xs[0] + side_w + gap)
    xs.append(xs[1] + mid_w + gap)
    relic_index = 0
    for p_i, (panel, x) in enumerate(zip(PANELS, xs)):
        w = mid_w if p_i == 1 else side_w
        top = 14 if p_i == 1 else 44
        h = H - top - 16
        peak = 96 if p_i == 1 else 80
        tint, deep = panel["tint"], panel["deep"]
        gid = f"pg{p_i}"
        defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{deep}"/>'
                    f'<stop offset=".45" stop-color="#050505"/><stop offset="1" stop-color="#000"/></linearGradient>')
        d = arch(x, top, w, h, peak)
        body.append(f'<path d="{d}" fill="url(#{gid})" stroke="{tint}" stroke-opacity=".55" stroke-width="1.2"/>')
        body.append(f'<path d="{arch(x+7, top+9, w-14, h-16, peak-4)}" fill="none" stroke="{tint}" stroke-opacity=".18" stroke-width="1"/>')
        cx = x + w / 2

        # heavenly rays in the centre panel, falling ash / rising embers on the wings
        if p_i == 1:
            defs.append(f'<clipPath id="c1"><path d="{d}"/></clipPath>')
            rays = "".join(f'<polygon points="{cx},{top+10} {cx-150+k*60-14},{H} {cx-150+k*60+14},{H}" fill="{GOLD}" opacity=".05"/>' for k in range(6))
            body.append(f'<g clip-path="url(#c1)" style="animation:breathe 6s ease-in-out infinite">{rays}</g>')
        for k in range(6):
            px = x + 24 + (k * 41) % (w - 48)
            if p_i == 2:
                body.append(f'<circle cx="{px}" cy="{H-40-(k*13)%40}" r="1.3" fill="{BLOOD}" style="animation:drift {4+k%3}s linear {-k*0.9:.1f}s infinite"/>')
            elif p_i == 0:
                body.append(f'<circle cx="{px}" cy="{top+120+(k*17)%40}" r="1" fill="{ASH}" style="animation:sink {6+k%3}s linear {-k*1.1:.1f}s infinite"/>')
            else:
                body.append(f'<circle cx="{px}" cy="{top+110+(k*19)%50}" r="1.1" fill="{GOLD}" style="animation:sink {5+k%3}s linear {-k*0.8:.1f}s infinite"/>')

        # emblem in the arch, then title + creed
        ey = top + peak * 0.62
        body.append(f'<g filter="url(#glow)">{emblem(panel["emblem"], cx, ey, tint)}</g>')
        ty = top + peak + 34
        size = 17 if p_i == 1 else 15
        body.append(f'<text x="{cx}" y="{ty}" text-anchor="middle" class="deco" font-size="{size}" letter-spacing="1.5" fill="{tint}">{panel["title"]}</text>')
        body.append(f'<text x="{cx}" y="{ty+22}" text-anchor="middle" font-size="{11 if p_i == 1 else 10.2}" letter-spacing=".4" fill="{ASH}">{panel["sub"]}</text>')
        body.append(f'<line x1="{cx-60}" y1="{ty+38}" x2="{cx+60}" y2="{ty+38}" stroke="{tint}" stroke-opacity=".35"/>'
                    f'<rect x="{cx-3}" y="{ty+35}" width="6" height="6" fill="{tint}" transform="rotate(45 {cx} {ty+38})"/>')

        # the three relics
        ry0 = ty + 84
        for r_i, (name, slug) in enumerate(panel["relics"]):
            ry = ry0 + r_i * 96
            mx, my = cx, ry
            delay = relic_index * step
            relic_index += 1
            # halo that ignites during the rite
            body.append(f'<circle cx="{mx}" cy="{my}" r="30" fill="{tint}" opacity="0" filter="url(#soft)" '
                        f'style="animation:ignite {CYCLE}s linear {delay:.2f}s infinite both"/>')
            # medallion: a diamond frame around a circle
            body.append(f'<rect x="{mx-24}" y="{my-24}" width="48" height="48" fill="#000" stroke="{tint}" stroke-opacity=".5" '
                        f'stroke-width="1" transform="rotate(45 {mx} {my})"/>')
            body.append(f'<circle cx="{mx}" cy="{my}" r="24" fill="#050505" stroke="{tint}" stroke-width="1.4" '
                        f'style="animation:kindle {CYCLE}s linear {delay:.2f}s infinite both"/>')
            if slug:
                s = 24 / 24
                body.append(f'<g transform="translate({mx-12} {my-12}) scale({s})"><path d="{icon_path(slug)}" fill="{tint}"/></g>')
            else:
                body.append(f'<rect x="{mx-12}" y="{my-12}" width="24" height="24" rx="5" fill="none" stroke="{tint}" stroke-width="1.8"/>'
                            f'<text x="{mx}" y="{my+5}" text-anchor="middle" font-size="12" font-weight="700" fill="{tint}">Xd</text>')
            # name plate beneath
            body.append(f'<text x="{mx}" y="{my+52}" text-anchor="middle" font-size="12.5" font-weight="700" letter-spacing="2.5" fill="{BONE}">{name.upper()}</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
           f'<title id="t">The Dual Arsenal (Heavenly Design &amp; Hellish Logic)</title>'
           f'<desc id="d">CURSED of KNOWLEDGE: Node.js, Docker, Linux. THE HEAVENLY UI/UX: Figma, Adobe XD, Tailwind. '
           f'THE HELLISH STACK: Python, TensorFlow, PyTorch.</desc>'
           f'<style>{"".join(css)}</style><defs>{"".join(defs)}</defs>{"".join(body)}</svg>')
    OUT.mkdir(exist_ok=True)
    (OUT / "arsenal.svg").write_text(svg, encoding="utf-8")
    print(f"wrote assets/arsenal.svg ({len(svg)/1024:.0f} KB)")


if __name__ == "__main__":
    build()
