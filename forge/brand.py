#!/usr/bin/env python3
"""Builds the static brand pieces: assets/hero.svg and assets/divider.svg.
Run once (or whenever you tweak them): python judgment/brand.py"""
import base64
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets"
GOLD, BLOOD, DEEP, ASH = "#FFD700", "#FF0000", "#7B0000", "#8C8C8C"


def face(name, file, weight):
    b64 = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
    return f"@font-face{{font-family:'{name}';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def hero():
    W, H = 900, 300
    cx = W / 2
    rnd = random.Random(5)
    rays = "".join(
        f'<polygon points="{cx},-40 {cx - 40 - i*62 - rnd.uniform(0,20):.0f},{H} {cx - 12 - i*62:.0f},{H}" fill="url(#ray)" opacity="{0.35 - i*0.05:.2f}"/>'
        for i in range(6))
    embers = "".join(
        f'<circle cx="{rnd.uniform(cx+30, W-20):.0f}" cy="{rnd.uniform(H-70, H-10):.0f}" r="{rnd.uniform(.7,1.9):.1f}" fill="{BLOOD}" '
        f'style="animation:rise {rnd.uniform(5,9):.1f}s linear {-rnd.uniform(0,9):.1f}s infinite"/>' for _ in range(22))
    motes = "".join(
        f'<circle cx="{rnd.uniform(20, cx-30):.0f}" cy="{rnd.uniform(10, 70):.0f}" r="{rnd.uniform(.6,1.5):.1f}" fill="{GOLD}" '
        f'style="animation:fall {rnd.uniform(6,10):.1f}s linear {-rnd.uniform(0,10):.1f}s infinite"/>' for _ in range(18))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">
<title id="t">Festomanolo, between Heaven (seamless UI) and Hell (complex backend logic)</title>
<style>{face('CinzelDeco','cinzel-decorative-900.woff2',900)}{face('Cinzel','cinzel-400.woff2',400)}{face('Cinzel','cinzel-700.woff2',700)}
text{{font-family:'Cinzel','Times New Roman',serif}}
.deco{{font-family:'CinzelDeco','Cinzel',serif}}
@keyframes rise{{0%{{transform:translateY(0);opacity:0}}15%{{opacity:.9}}100%{{transform:translateY(-170px);opacity:0}}}}
@keyframes fall{{0%{{transform:translateY(0);opacity:0}}20%{{opacity:.8}}100%{{transform:translateY(170px);opacity:0}}}}
@keyframes glint{{0%,55%{{transform:translateX(-520px)}}100%{{transform:translateX(520px)}}}}
@keyframes seam{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
@keyframes open{{0%{{opacity:0;letter-spacing:2px}}100%{{opacity:1;letter-spacing:9px}}}}
.name{{animation:open 1.6s cubic-bezier(.2,.7,.1,1) both}}
.glint{{animation:glint 7s cubic-bezier(.5,0,.3,1) infinite}}
.seam{{animation:seam 3.2s ease-in-out infinite}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
  <linearGradient id="split" x1="0" x2="1"><stop offset=".0" stop-color="#1A1400"/><stop offset=".5" stop-color="#000"/><stop offset="1" stop-color="#1F0000"/></linearGradient>
  <radialGradient id="hell" cx=".92" cy="1.05" r=".75"><stop offset="0" stop-color="{DEEP}" stop-opacity=".9"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <radialGradient id="heaven" cx=".08" cy="-.05" r=".7"><stop offset="0" stop-color="{GOLD}" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <linearGradient id="ray" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity=".35"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
  <linearGradient id="namefill" x1="0" x2="1"><stop offset=".08" stop-color="{GOLD}"/><stop offset=".5" stop-color="#FFF6D0"/><stop offset=".92" stop-color="{BLOOD}"/></linearGradient>
  <linearGradient id="seamg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GOLD}"/><stop offset=".5" stop-color="#FFF"/><stop offset="1" stop-color="{BLOOD}"/></linearGradient>
  <linearGradient id="glintg" x1="0" x2="1"><stop offset="0" stop-color="#FFF" stop-opacity="0"/><stop offset=".5" stop-color="#FFF" stop-opacity=".95"/><stop offset="1" stop-color="#FFF" stop-opacity="0"/></linearGradient>
  <clipPath id="left"><rect width="{cx}" height="{H}"/></clipPath>
  <mask id="namemask"><text x="{cx}" y="160" text-anchor="middle" class="deco name" font-size="54" fill="#fff">FESTOMANOLO</text></mask>
  <filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect width="{W}" height="{H}" fill="#000"/>
<rect width="{W}" height="{H}" fill="url(#split)"/>
<rect width="{W}" height="{H}" fill="url(#heaven)"/>
<rect width="{W}" height="{H}" fill="url(#hell)"/>
<g clip-path="url(#left)">{rays}</g>
{motes}{embers}
<rect class="seam" x="{cx-0.75}" y="24" width="1.5" height="{H-48}" fill="url(#seamg)" filter="url(#glow)"/>
<text x="{cx}" y="160" text-anchor="middle" class="deco name" font-size="54" fill="url(#namefill)" filter="url(#glow)">FESTOMANOLO</text>
<g mask="url(#namemask)"><g transform="skewX(-20)"><rect class="glint" x="{cx-10}" y="100" width="120" height="80" fill="url(#glintg)"/></g></g>
<text x="{cx-40}" y="222" text-anchor="end" font-size="13" font-weight="700" letter-spacing="6" fill="{GOLD}">HEAVEN</text>
<text x="{cx-40}" y="242" text-anchor="end" font-size="12" letter-spacing="2" fill="{ASH}">Seamless UI</text>
<text x="{cx+40}" y="222" font-size="13" font-weight="700" letter-spacing="6" fill="{BLOOD}">HELL</text>
<text x="{cx+40}" y="242" font-size="12" letter-spacing="2" fill="{ASH}">Complex Backend Logic</text>
<rect x="{cx-5}" y="226" width="10" height="10" fill="#000" stroke="url(#seamg)" stroke-width="1.5" transform="rotate(45 {cx} 231)"/>
<text x="{cx}" y="{H-18}" text-anchor="middle" font-size="10" letter-spacing="5" fill="#555">FESTOMANOLO.COM</text>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" fill="none" stroke="#1E1E1E"/>
</svg>"""
    (OUT / "hero.svg").write_text(svg, encoding="utf-8")


def divider():
    W, H = 900, 26
    cx, cy = W / 2, H / 2
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="presentation">
<style>@keyframes run{{0%{{transform:translateX(-120px)}}100%{{transform:translateX({W}px)}}}}.run{{animation:run 5s cubic-bezier(.6,0,.4,1) infinite}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>
<defs>
  <linearGradient id="l" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset=".45" stop-color="{GOLD}"/><stop offset=".55" stop-color="{BLOOD}"/><stop offset="1" stop-color="{BLOOD}" stop-opacity="0"/></linearGradient>
  <linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <mask id="m"><rect x="0" y="{cy-1}" width="{W}" height="2" fill="#fff"/></mask>
</defs>
<rect x="0" y="{cy-.5}" width="{W}" height="1" fill="url(#l)"/>
<g mask="url(#m)"><rect class="run" x="0" y="{cy-1}" width="120" height="2" fill="url(#g)"/></g>
<rect x="{cx-6}" y="{cy-6}" width="12" height="12" fill="#000" stroke="{GOLD}" stroke-width="1.2" transform="rotate(45 {cx} {cy})"/>
<rect x="{cx-2.5}" y="{cy-2.5}" width="5" height="5" fill="{BLOOD}" transform="rotate(45 {cx} {cy})"/>
<rect x="{cx-40}" y="{cy-2}" width="4" height="4" fill="{GOLD}" transform="rotate(45 {cx-38} {cy})"/>
<rect x="{cx+36}" y="{cy-2}" width="4" height="4" fill="{BLOOD}" transform="rotate(45 {cx+38} {cy})"/>
</svg>"""
    (OUT / "divider.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    hero()
    divider()
    print("wrote assets/hero.svg and assets/divider.svg")
