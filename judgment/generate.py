#!/usr/bin/env python3
"""
THE LAST JUDGMENT
A contribution-graph boss battle, rendered as a single self-animating SVG.

The past year of contributions is summoned out of The Darkness (a boss on the
right) as red "sins". Week by week they scroll into the Judgment Gate, where
each one is struck, turned to gold, and fired back at the boss as light.
Every contribution is one point of damage. When the year is fully judged,
The Darkness falls.

No JavaScript: GitHub strips it from README images. Everything runs on CSS
keyframes that share one master clock, so the whole piece loops seamlessly.

Usage:
    python judgment/generate.py --user festomanolo --out assets/judgment.svg
    python judgment/generate.py --demo --out preview.svg     # random data
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import math
import os
import random
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- palette
ABYSS = "#000000"
BLOOD = "#FF0000"
BLOOD_DEEP = "#7B0000"
GOLD = "#FFD700"
ASH = "#8C8C8C"
BONE = "#FFFFFF"

RED_LEVELS = ["#140404", "#5C0000", "#9E0000", "#DA0000", "#FF2B2B"]
GOLD_LEVELS = ["#0E0B03", "#4D3A00", "#8A6A00", "#D4A800", "#FFD700"]
RATINGS = ["", "FAITHFUL", "BLESSED", "HOLY", "DIVINE"]

# ---------------------------------------------------------------- stage
W, H = 900, 352
GATE_X = 230            # the Judgment Gate
BOSS_X, BOSS_Y = 812, 158
LANE_TOP, LANE_PITCH = 86, 24
CELL, COL_PITCH = 14, 20
RED_CLIP_RIGHT = 752    # sins emerge from the boss here
GOLD_CLIP_LEFT = 24

# ---------------------------------------------------------------- clock
T = 28.0                # master loop, seconds
START = 2.2             # grid starts moving
LEAD = 0.55             # seconds before first column hits the gate
DELTA = 0.30            # seconds per week
SPEED = COL_PITCH / DELTA
BOSS_FALL = None        # computed from data
EPS = 0.02              # keyframe epsilon (percent)


def pct(t: float) -> str:
    return f"{max(0.0, min(100.0, t / T * 100)):.3f}%"


# ================================================================ data
def fetch_scrape(user: str):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "last-judgment"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    cells = {}
    for m in re.finditer(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
        tag = m.group(0)
        cid = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
        lvl = re.search(r'data-level="(\d)"', tag)
        date = re.search(r'data-date="([\d-]+)"', tag)
        if cid and lvl and date:
            d, w = int(cid.group(1)), int(cid.group(2))
            cells[(w, d)] = {"level": int(lvl.group(1)), "date": date.group(1), "count": 0,
                             "id": f"contribution-day-component-{d}-{w}"}
    for m in re.finditer(r'<tool-tip[^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', page):
        n = re.match(r"\s*([\d,]+) contribution", m.group(2))
        if n:
            for c in cells.values():
                if c["id"] == m.group(1):
                    c["count"] = int(n.group(1).replace(",", ""))
                    break
    if not cells:
        raise RuntimeError("no contribution cells found")
    weeks = max(w for w, _ in cells) + 1
    grid = [[cells.get((w, d)) for d in range(7)] for w in range(weeks)]
    total_m = re.search(r'js-contribution-activity-description[^>]*>\s*([\d,]+)', page)
    total = int(total_m.group(1).replace(",", "")) if total_m else sum(c["count"] for c in cells.values())
    return grid, total


def fetch_graphql(user: str, token: str):
    query = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{contributionCount contributionLevel weekday date}}}}}}"""
    body = json.dumps({"query": query, "variables": {"u": user}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "last-judgment"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    grid = []
    for wk in cal["weeks"]:
        col = [None] * 7
        for day in wk["contributionDays"]:
            col[day["weekday"]] = {"level": lv[day["contributionLevel"]],
                                   "count": day["contributionCount"], "date": day["date"]}
        grid.append(col)
    return grid, cal["totalContributions"]


def fake_data(seed=7):
    rnd = random.Random(seed)
    start = dt.date.today() - dt.timedelta(days=371)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    grid, total = [], 0
    for w in range(53):
        col = []
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            if day > dt.date.today():
                col.append(None)
                continue
            lvl = rnd.choices([0, 1, 2, 3, 4], [50, 22, 14, 8, 6])[0]
            cnt = [0, rnd.randint(1, 3), rnd.randint(4, 8), rnd.randint(9, 15), rnd.randint(16, 40)][lvl]
            total += cnt
            col.append({"level": lvl, "count": cnt, "date": day.isoformat()})
        grid.append(col)
    return grid, total


def load(user: str, demo: bool):
    if demo:
        return fake_data()
    try:
        return fetch_scrape(user)
    except Exception as e:  # noqa: BLE001
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise
        print(f"scrape failed ({e}); falling back to GraphQL", file=sys.stderr)
        return fetch_graphql(user, token)


# ================================================================ helpers
def font_face(name: str, file: str, weight: int) -> str:
    b64 = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
    return (f"@font-face{{font-family:'{name}';font-weight:{weight};font-style:normal;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def fmt(n: int) -> str:
    return f"{n:,}"


def lane_y(d: int) -> float:
    return LANE_TOP + d * LANE_PITCH


def month_label(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return d.strftime("%b %d, %Y").upper()


# ================================================================ build
def build(grid, total, user: str) -> str:
    weeks = len(grid)
    hits = [START + LEAD + i * DELTA for i in range(weeks)]
    last_hit = hits[-1]
    fall = last_hit + 0.55                      # the boss dies
    stop = fall + 0.4                           # grid halts
    col0_x = GATE_X + LEAD * SPEED              # column-0 left edge at t=0

    # per-week damage (contributions); fall back to levels if counts are missing
    wk_damage = []
    for col in grid:
        dmg = sum(c["count"] for c in col if c)
        if dmg == 0:
            dmg = sum(c["level"] for c in col if c)
        wk_damage.append(dmg)
    total_damage = sum(wk_damage) or 1
    shown_total = total or total_damage

    css, body = [], []
    a = css.append
    b = body.append

    # ---------------- base css
    a(font_face("CinzelDeco", "cinzel-decorative-900.woff2", 900))
    a(font_face("Cinzel", "cinzel-700.woff2", 700))
    a(font_face("Cinzel", "cinzel-400.woff2", 400))
    a(f"""
    text{{font-family:'Cinzel','Trajan Pro','Times New Roman',serif;}}
    .deco{{font-family:'CinzelDeco','Cinzel',serif;}}
    .lbl{{font-size:10px;letter-spacing:3px;fill:{ASH};font-weight:400;}}
    .t{{animation-duration:{T}s;animation-iteration-count:infinite;animation-timing-function:linear;animation-fill-mode:both;}}
    @keyframes hit{{0%{{opacity:0}}{EPS}%{{opacity:1;transform:scale(1)}}2%{{opacity:0;transform:scale(2.6)}}100%{{opacity:0;transform:scale(2.6)}}}}
    @keyframes win{{0%{{opacity:0}}{EPS}%{{opacity:1}}{pct(DELTA - 0.01)}{{opacity:1}}{pct(DELTA)}{{opacity:0}}100%{{opacity:0}}}}
    @keyframes pop{{0%{{opacity:0}}{EPS}%{{opacity:1;transform:translateY(6px)}}{pct(0.18)}{{opacity:1;transform:translateY(0)}}{pct(DELTA*0.95)}{{opacity:0;transform:translateY(-4px)}}100%{{opacity:0}}}}
    @keyframes bolt{{0%{{opacity:0;stroke-dashoffset:16}}{EPS}%{{opacity:1;stroke-dashoffset:16}}{pct(0.30)}{{opacity:1;stroke-dashoffset:-100}}{pct(0.32)}{{opacity:0;stroke-dashoffset:-100}}100%{{opacity:0;stroke-dashoffset:-100}}}}
    @keyframes beam{{0%{{opacity:0}}{EPS}%{{opacity:.55}}{pct(0.22)}{{opacity:0}}100%{{opacity:0}}}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    @keyframes spinr{{to{{transform:rotate(-360deg)}}}}
    @keyframes breathe{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
    @keyframes rise{{0%{{transform:translateY(0);opacity:0}}15%{{opacity:.9}}100%{{transform:translateY(-120px);opacity:0}}}}
    @keyframes fallmote{{0%{{transform:translateY(0);opacity:0}}20%{{opacity:.8}}100%{{transform:translateY(110px);opacity:0}}}}
    .spin{{animation:spin 18s linear infinite;transform-origin:{BOSS_X}px {BOSS_Y}px;}}
    .spinr{{animation:spinr 11s linear infinite;transform-origin:{BOSS_X}px {BOSS_Y}px;}}
    .breathe{{animation:breathe 2.4s ease-in-out infinite;}}
    @media (prefers-reduced-motion: reduce){{*{{animation-play-state:paused!important;}}}}
    """)

    # ---------------- grid motion (one transform drives every sin)
    dist = SPEED * (stop - START)
    a(f"@keyframes march{{0%{{transform:translateX(0);opacity:0}}{pct(0.9)}{{opacity:1}}"
      f"{pct(START)}{{transform:translateX(0)}}{pct(stop)}{{transform:translateX(-{dist:.1f}px)}}"
      f"{pct(fall + 1.2)}{{opacity:1}}{pct(fall + 2.4)}{{opacity:0;transform:translateX(-{dist:.1f}px)}}"
      f"100%{{opacity:0;transform:translateX(-{dist:.1f}px)}}}}")

    # ---------------- boss HP drain (stepped per week)
    stops = ["0%{transform:scaleX(1)}"]
    cum = 0
    for i, h in enumerate(hits):
        prev = 1 - cum / total_damage
        cum += wk_damage[i]
        now = max(0.0, 1 - cum / total_damage)
        if wk_damage[i]:
            stops.append(f"{pct(h + 0.26)}{{transform:scaleX({prev:.4f})}}")
            stops.append(f"{pct(h + 0.34)}{{transform:scaleX({now:.4f})}}")
    stops += [f"{pct(fall)}{{transform:scaleX(0)}}", f"{pct(T - 1.4)}{{transform:scaleX(0)}}",
              "100%{transform:scaleX(1)}"]
    a("@keyframes hp{" + "".join(stops) + "}")

    # ---------------- boss death choreography
    shake = [f"0%{{transform:translate(0,0) scale(1);opacity:1}}", f"{pct(last_hit - 0.4)}{{transform:translate(0,0) scale(1);opacity:1}}"]
    rnd = random.Random(3)
    t = last_hit - 0.35
    while t < fall:
        shake.append(f"{pct(t)}{{transform:translate({rnd.uniform(-7,7):.1f}px,{rnd.uniform(-5,5):.1f}px) scale(1.02);opacity:1}}")
        t += 0.06
    shake += [f"{pct(fall)}{{transform:translate(0,0) scale(1.08);opacity:1}}",
              f"{pct(fall + 0.25)}{{transform:translate(0,0) scale(1.9);opacity:0}}",
              f"{pct(T - 1.6)}{{transform:translate(0,0) scale(.4);opacity:0}}",
              "100%{transform:translate(0,0) scale(1);opacity:1}"]
    a("@keyframes bossdie{" + "".join(shake) + "}")
    a(f"@keyframes whiteout{{0%{{opacity:0}}{pct(fall)}{{opacity:0}}{pct(fall + 0.05)}{{opacity:.6}}{pct(fall + 1.1)}{{opacity:0}}100%{{opacity:0}}}}")
    for k in range(3):
        s = fall + k * 0.18
        a(f"@keyframes wave{k}{{0%{{opacity:0;transform:scale(.2)}}{pct(s)}{{opacity:0;transform:scale(.2)}}"
          f"{pct(s + 0.02)}{{opacity:1;transform:scale(.3)}}{pct(s + 1.4)}{{opacity:0;transform:scale({5 + k*1.5})}}100%{{opacity:0;transform:scale(5)}}}}")
    shards = []
    for k in range(18):
        ang = k / 18 * math.tau + rnd.uniform(-.15, .15)
        r = rnd.uniform(140, 300)
        dx, dy = math.cos(ang) * r, math.sin(ang) * r * 0.75
        rot = rnd.uniform(-540, 540)
        a(f"@keyframes shard{k}{{0%{{opacity:0;transform:translate(0,0) rotate(0)}}{pct(fall)}{{opacity:0;transform:translate(0,0) rotate(0)}}"
          f"{pct(fall + 0.03)}{{opacity:1;transform:translate(0,0) rotate(0)}}"
          f"{pct(fall + 1.8)}{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px) rotate({rot:.0f}deg)}}100%{{opacity:0}}}}")
        sz = rnd.uniform(5, 12)
        shards.append(f'<polygon points="0,{-sz:.1f} {sz*0.6:.1f},{sz*0.5:.1f} {-sz*0.5:.1f},{sz*0.4:.1f}" '
                      f'fill="{BLOOD if k % 3 else GOLD}" transform="translate({BOSS_X} {BOSS_Y})"/>'
                      .replace("<polygon", f'<g class="t" style="animation-name:shard{k};transform-origin:{BOSS_X}px {BOSS_Y}px"><polygon') + "</g>")

    # narrative cards
    def card(name, t0, t1, fade=0.45):
        a(f"@keyframes {name}{{0%{{opacity:0}}{pct(t0)}{{opacity:0;transform:translateY(6px)}}{pct(t0+fade)}{{opacity:1;transform:translateY(0)}}"
          f"{pct(t1-fade)}{{opacity:1;transform:translateY(0)}}{pct(t1)}{{opacity:0;transform:translateY(-4px)}}100%{{opacity:0}}}}")
    # the intro card must be visible at t=0 so the loop reads well paused
    a(f"@keyframes intro{{0%{{opacity:1}}{pct(START - 0.3)}{{opacity:1}}{pct(START + 0.3)}{{opacity:0}}{pct(T - 0.5)}{{opacity:0}}100%{{opacity:1}}}}")
    card("fallen", fall + 0.5, fall + 3.2)
    card("quote", fall + 3.4, T - 0.4)
    a(f"@keyframes endscore{{0%{{opacity:0}}{pct(last_hit)}{{opacity:0}}{pct(last_hit+0.02)}{{opacity:1}}{pct(T-0.3)}{{opacity:1}}100%{{opacity:0}}}}")
    a(f"@keyframes zeroscore{{0%{{opacity:1}}{pct(hits[0])}{{opacity:1}}{pct(hits[0]+0.01)}{{opacity:0}}{pct(T-0.3)}{{opacity:0}}100%{{opacity:1}}}}")
    a(f"@keyframes hudstate{{0%{{opacity:1}}{pct(fall)}{{opacity:1}}{pct(fall+0.1)}{{opacity:0}}{pct(T-1.2)}{{opacity:0}}{pct(T-0.8)}{{opacity:1}}100%{{opacity:1}}}}")
    a(f"@keyframes hudwin{{0%{{opacity:0}}{pct(fall)}{{opacity:0}}{pct(fall+0.3)}{{opacity:1}}{pct(T-1.8)}{{opacity:1}}{pct(T-1.4)}{{opacity:0}}100%{{opacity:0}}}}")

    # ================================================================ svg body
    b(f'<rect width="{W}" height="{H}" fill="{ABYSS}"/>')
    b(f'<rect width="{W}" height="{H}" fill="url(#hellglow)"/>')
    b(f'<rect width="{W}" height="{H}" fill="url(#heavenglow)"/>')

    # frame with corner ornaments
    b(f'<rect x="6.5" y="6.5" width="{W-13}" height="{H-13}" fill="none" stroke="{BLOOD_DEEP}" stroke-width="1"/>')
    for (cx, cy, sx, sy) in [(6.5, 6.5, 1, 1), (W-6.5, 6.5, -1, 1), (6.5, H-6.5, 1, -1), (W-6.5, H-6.5, -1, -1)]:
        b(f'<path d="M{cx} {cy+22*sy} V{cy} H{cx+22*sx}" fill="none" stroke="{GOLD}" stroke-width="1.5"/>'
          f'<rect x="{cx+5*sx-2:.1f}" y="{cy+5*sy-2:.1f}" width="4" height="4" fill="{GOLD}" transform="rotate(45 {cx+5*sx} {cy+5*sy})"/>')

    # ---------------- HUD
    b(f'<line x1="24" y1="58" x2="{W-24}" y2="58" stroke="url(#hudline)" stroke-width="1"/>')
    b(f'<text x="30" y="28" class="lbl">SOULS JUDGED</text>')
    b(f'<g class="t" style="animation-name:zeroscore"><text x="30" y="49" font-size="20" font-weight="700" fill="{GOLD}">0</text></g>')
    cum = 0
    for i, h in enumerate(hits):
        cum += wk_damage[i]
        if i < weeks - 1:
            val = round(shown_total * cum / total_damage)
            b(f'<g class="t" style="animation-name:win;animation-delay:{h:.3f}s"><text x="30" y="49" font-size="20" font-weight="700" fill="{GOLD}">{fmt(val)}</text></g>')
    b(f'<g class="t" style="animation-name:endscore"><text x="30" y="49" font-size="20" font-weight="700" fill="{GOLD}">{fmt(shown_total)}</text></g>')

    b(f'<text x="{W/2}" y="38" text-anchor="middle" class="deco" font-size="19" letter-spacing="4" fill="url(#titlegrad)">THE LAST JUDGMENT</text>')

    b(f'<g class="t" style="animation-name:hudstate"><text x="{W-30}" y="28" text-anchor="end" class="lbl" style="fill:{BLOOD}">THE DARKNESS</text></g>')
    b(f'<g class="t" style="animation-name:hudwin"><text x="{W-30}" y="28" text-anchor="end" class="lbl" style="fill:{GOLD}">THE DARKNESS HAS FALLEN</text></g>')
    bw = 210
    b(f'<rect x="{W-30-bw}" y="38" width="{bw}" height="9" fill="#1A0000" stroke="{BLOOD_DEEP}" stroke-width="1"/>')
    b(f'<g class="t" style="animation-name:hp;transform-origin:{W-30-bw}px 0"><rect x="{W-30-bw+1.5}" y="39.5" width="{bw-3}" height="6" fill="url(#hpgrad)"/></g>')
    for k in range(1, 10):
        x = W - 30 - bw + bw * k / 10
        b(f'<line x1="{x:.1f}" y1="39" x2="{x:.1f}" y2="46" stroke="#000" stroke-width="1" opacity=".6"/>')

    # ---------------- lanes
    for d in range(7):
        y = lane_y(d) + CELL / 2
        b(f'<line x1="{GOLD_CLIP_LEFT}" y1="{y}" x2="{GATE_X}" y2="{y}" stroke="#1C1604" stroke-width="1"/>')
        b(f'<line x1="{GATE_X}" y1="{y}" x2="{RED_CLIP_RIGHT+20}" y2="{y}" stroke="#1C0303" stroke-width="1"/>')

    # ---------------- the sins (red, right of gate) and the redeemed (gold, left)
    red, gold = [], []
    for w, col in enumerate(grid):
        x = col0_x + w * COL_PITCH
        for d, c in enumerate(col):
            if c is None:
                continue
            y = lane_y(d)
            lvl = c["level"]
            red.append(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{RED_LEVELS[lvl]}"/>')
            gold.append(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{GOLD_LEVELS[lvl]}"/>')
    b(f'<g clip-path="url(#redclip)"><g class="t" style="animation-name:march">{"".join(red)}</g></g>')
    b(f'<g clip-path="url(#goldclip)" mask="url(#goldfade)"><g class="t" style="animation-name:march">{"".join(gold)}</g></g>')

    # ---------------- the boss
    boss = [
        f'<circle cx="{BOSS_X}" cy="{BOSS_Y}" r="92" fill="url(#bossaura)"/>',
        f'<g class="spin"><circle cx="{BOSS_X}" cy="{BOSS_Y}" r="66" fill="none" stroke="{BLOOD_DEEP}" stroke-width="1" stroke-dasharray="2 5"/>'
        f'<circle cx="{BOSS_X}" cy="{BOSS_Y}" r="58" fill="none" stroke="{BLOOD}" stroke-width="1.2" stroke-dasharray="46 12 6 12" opacity=".8"/></g>',
        '<g class="spinr">' + "".join(
            f'<line x1="{BOSS_X}" y1="{BOSS_Y-50}" x2="{BOSS_X}" y2="{BOSS_Y-(44 if k%3 else 40)}" stroke="{BLOOD}" stroke-width="{2 if k%3==0 else 1}" transform="rotate({k*10} {BOSS_X} {BOSS_Y})"/>'
            for k in range(36)) + "</g>",
        # triangle sigil
        f'<g class="spin" style="animation-duration:40s"><polygon points="{BOSS_X},{BOSS_Y-40} {BOSS_X+34.6:.1f},{BOSS_Y+20} {BOSS_X-34.6:.1f},{BOSS_Y+20}" fill="none" stroke="{BLOOD_DEEP}" stroke-width="1"/>'
        f'<polygon points="{BOSS_X},{BOSS_Y+40} {BOSS_X+34.6:.1f},{BOSS_Y-20} {BOSS_X-34.6:.1f},{BOSS_Y-20}" fill="none" stroke="{BLOOD_DEEP}" stroke-width="1"/></g>',
        # the eye
        f'<path d="M{BOSS_X-38} {BOSS_Y} Q{BOSS_X} {BOSS_Y-30} {BOSS_X+38} {BOSS_Y} Q{BOSS_X} {BOSS_Y+30} {BOSS_X-38} {BOSS_Y}Z" fill="#0A0000" stroke="{BLOOD}" stroke-width="1.6" filter="url(#glow)"/>',
        f'<circle class="breathe" cx="{BOSS_X}" cy="{BOSS_Y}" r="13" fill="url(#iris)"/>',
        f'<ellipse cx="{BOSS_X}" cy="{BOSS_Y}" rx="2.6" ry="11" fill="#000"/>',
    ]
    b(f'<g class="t" style="animation-name:bossdie;transform-origin:{BOSS_X}px {BOSS_Y}px">{"".join(boss)}')
    for i, h in enumerate(hits):   # damage flashes on the eye
        if wk_damage[i]:
            b(f'<circle class="t" cx="{BOSS_X}" cy="{BOSS_Y}" r="18" fill="none" stroke="{BONE}" stroke-width="1.5" '
              f'style="animation-name:hit;animation-delay:{h+0.3:.3f}s;transform-origin:{BOSS_X}px {BOSS_Y}px"/>')
    b('</g>')

    # ---------------- the Judgment Gate
    b(f'<rect x="{GATE_X-9}" y="{LANE_TOP-10}" width="18" height="{7*LANE_PITCH+10}" fill="url(#gatehaze)"/>')
    b(f'<rect x="{GATE_X-1.5}" y="{LANE_TOP-10}" width="3" height="{7*LANE_PITCH+10}" fill="{GOLD}" filter="url(#glow)"/>')
    # halo + wings
    hx, hy = GATE_X, LANE_TOP - 18
    wing = lambda s: (f'<path d="M{hx+6*s} {hy+2} C{hx+26*s} {hy-14} {hx+46*s} {hy-10} {hx+58*s} {hy-18} '
                      f'C{hx+50*s} {hy-4} {hx+40*s} {hy+2} {hx+30*s} {hy+4} C{hx+36*s} {hy+6} {hx+42*s} {hy+6} {hx+48*s} {hy+4} '
                      f'C{hx+36*s} {hy+12} {hx+20*s} {hy+10} {hx+6*s} {hy+6}Z" fill="{GOLD}" opacity=".92"/>')
    b(f'<g filter="url(#glow)">{wing(1)}{wing(-1)}<ellipse cx="{hx}" cy="{hy-9}" rx="11" ry="3.5" fill="none" stroke="{GOLD}" stroke-width="2"/>'
      f'<rect x="{hx-4}" y="{hy-1}" width="8" height="8" fill="{GOLD}" transform="rotate(45 {hx} {hy+3})"/></g>')
    base_y = LANE_TOP + 7 * LANE_PITCH
    b(f'<path d="M{GATE_X-16} {base_y+6} L{GATE_X} {base_y-2} L{GATE_X+16} {base_y+6}" fill="none" stroke="{GOLD}" stroke-width="1.5"/>')

    # ---------------- per-note judgment: flash on the gate + light bolt at the boss
    for w, col in enumerate(grid):
        h = hits[w]
        strongest = None
        for d, c in enumerate(col):
            if c and c["level"] > 0:
                cx, cy = GATE_X, lane_y(d) + CELL / 2
                b(f'<rect class="t" x="{cx-8}" y="{cy-8}" width="16" height="16" rx="3" fill="none" stroke="{GOLD}" stroke-width="1.5" '
                  f'style="animation-name:hit;animation-delay:{h:.3f}s;transform-origin:{cx}px {cy}px"/>')
                b(f'<rect class="t" x="{cx-5}" y="{cy-5}" width="10" height="10" fill="{BONE}" '
                  f'style="animation-name:hit;animation-delay:{h:.3f}s;transform-origin:{cx}px {cy}px"/>')
                if strongest is None or c["level"] > col[strongest]["level"]:
                    strongest = d
        if strongest is not None:
            y0 = lane_y(strongest) + CELL / 2
            midx = (GATE_X + BOSS_X) / 2
            b(f'<path class="t" pathLength="100" d="M{GATE_X+8} {y0} Q{midx} {y0 - 70 + strongest*8} {BOSS_X-40} {BOSS_Y}" fill="none" '
              f'stroke="{GOLD}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="16 200" filter="url(#glow)" '
              f'style="animation-name:bolt;animation-delay:{h:.3f}s"/>')
            b(f'<rect class="t" x="{GATE_X-6}" y="{LANE_TOP-10}" width="12" height="{7*LANE_PITCH+10}" fill="{BONE}" opacity=".0" '
              f'style="animation-name:beam;animation-delay:{h:.3f}s"/>')

    # ---------------- ratings, combo, week counter
    combo = 0
    ry = base_y + 32
    for w, col in enumerate(grid):
        h = hits[w]
        lvls = [c["level"] for c in col if c]
        notes = sum(1 for l in lvls if l > 0)
        combo = combo + notes if notes else 0
        top = max(lvls) if lvls else 0
        if top:
            color = GOLD if top >= 3 else "#E8C66A"
            b(f'<g class="t" style="animation-name:pop;animation-delay:{h:.3f}s"><text x="{GATE_X}" y="{ry}" text-anchor="middle" '
              f'font-size="{14 if top == 4 else 12}" font-weight="700" letter-spacing="3" fill="{color}">{RATINGS[top]}</text></g>')
        if combo >= 3:
            b(f'<g class="t" style="animation-name:win;animation-delay:{h:.3f}s"><text x="{GATE_X}" y="{ry+17}" text-anchor="middle" '
              f'font-size="10" letter-spacing="2.5" fill="{BLOOD}">×{combo} COMBO</text></g>')
        first = next((c for c in col if c), None)
        if first:
            b(f'<g class="t" style="animation-name:win;animation-delay:{h:.3f}s"><text x="{W-30}" y="{H-24}" text-anchor="end" class="lbl">'
              f'WEEK {w+1:02d} / {weeks} · {month_label(first["date"])}</text></g>')
    b(f'<text x="30" y="{H-24}" class="lbl">{html.escape(user.upper())} · THE LAST 365 DAYS</text>')

    # ---------------- narrative cards
    mid_y = LANE_TOP + 3.5 * LANE_PITCH
    b(f'<g class="t" style="animation-name:intro">'
      f'<rect x="{GATE_X+40}" y="{mid_y-34}" width="{RED_CLIP_RIGHT-GATE_X-120}" height="58" fill="#000" opacity=".82"/>'
      f'<text x="{(GATE_X+RED_CLIP_RIGHT)/2-20}" y="{mid_y-8}" text-anchor="middle" class="deco" font-size="17" letter-spacing="3" fill="{BONE}">A YEAR OF SINS AWAITS</text>'
      f'<text x="{(GATE_X+RED_CLIP_RIGHT)/2-20}" y="{mid_y+13}" text-anchor="middle" class="lbl" style="fill:{BLOOD}">{fmt(shown_total)} CONTRIBUTIONS · {weeks} WEEKS · ONE GATE</text></g>')
    cx_red = (GATE_X + W) / 2
    b(f'<g class="t" style="animation-name:fallen"><text x="{cx_red}" y="{mid_y}" text-anchor="middle" class="deco" font-size="26" letter-spacing="5" fill="{GOLD}" filter="url(#glow)">JUDGMENT COMPLETE</text>'
      f'<text x="{cx_red}" y="{mid_y+26}" text-anchor="middle" class="lbl" style="fill:{BONE}">THE DARKNESS HAS FALLEN · {fmt(shown_total)} SOULS JUDGED</text></g>')
    b(f'<g class="t" style="animation-name:quote"><text x="{cx_red}" y="{mid_y-4}" text-anchor="middle" font-size="16" font-weight="400" letter-spacing="1.5" fill="{BONE}">'
      f'“I believe Darkness was not created,</text><text x="{cx_red}" y="{mid_y+20}" text-anchor="middle" font-size="16" font-weight="400" letter-spacing="1.5" fill="{BONE}">'
      f'it was there before our creation.”</text><text x="{cx_red}" y="{mid_y+46}" text-anchor="middle" class="lbl" style="fill:{BLOOD}">IT RETURNS</text></g>')

    # ---------------- death fx
    b("".join(shards))
    for k in range(3):
        b(f'<circle class="t" cx="{BOSS_X}" cy="{BOSS_Y}" r="30" fill="none" stroke="{GOLD if k == 1 else BLOOD}" stroke-width="{0.7 - k*0.15:.2f}" '
          f'style="animation-name:wave{k};transform-origin:{BOSS_X}px {BOSS_Y}px"/>')
    b(f'<rect class="t" width="{W}" height="{H}" fill="url(#flash)" style="animation-name:whiteout"/>')

    # ---------------- ambient particles: embers rise in hell, motes fall in heaven
    prnd = random.Random(11)
    for k in range(16):
        x = prnd.uniform(GATE_X + 60, W - 20)
        y = prnd.uniform(H - 60, H - 20)
        dur, dl = prnd.uniform(4, 8), prnd.uniform(0, 8)
        b(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{prnd.uniform(.8, 1.8):.1f}" fill="{BLOOD}" '
          f'style="animation:rise {dur:.1f}s linear {-dl:.1f}s infinite"/>')
    for k in range(9):
        x = prnd.uniform(30, GATE_X - 20)
        y = prnd.uniform(64, 110)
        dur, dl = prnd.uniform(5, 9), prnd.uniform(0, 8)
        b(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{prnd.uniform(.6, 1.4):.1f}" fill="{GOLD}" '
          f'style="animation:fallmote {dur:.1f}s linear {-dl:.1f}s infinite"/>')

    # ================================================================ defs
    defs = f"""
    <defs>
      <radialGradient id="hellglow" cx="{BOSS_X/W:.3f}" cy="{BOSS_Y/H:.3f}" r=".55"><stop offset="0" stop-color="{BLOOD_DEEP}" stop-opacity=".45"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
      <radialGradient id="heavenglow" cx="{GATE_X/W:.3f}" cy=".2" r=".35"><stop offset="0" stop-color="{GOLD}" stop-opacity=".10"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
      <radialGradient id="bossaura"><stop offset=".3" stop-color="{BLOOD}" stop-opacity=".22"/><stop offset="1" stop-color="{BLOOD}" stop-opacity="0"/></radialGradient>
      <radialGradient id="iris"><stop offset="0" stop-color="#FFB0B0"/><stop offset=".35" stop-color="{BLOOD}"/><stop offset="1" stop-color="{BLOOD_DEEP}"/></radialGradient>
      <radialGradient id="flash" cx="{BOSS_X/W:.3f}" cy="{BOSS_Y/H:.3f}" r=".9"><stop offset="0" stop-color="#FFF"/><stop offset=".5" stop-color="#FFE9A8"/><stop offset="1" stop-color="{BLOOD}"/></radialGradient>
      <linearGradient id="titlegrad" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}"/><stop offset=".5" stop-color="#FFF4C2"/><stop offset="1" stop-color="{BLOOD}"/></linearGradient>
      <linearGradient id="hudline" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity=".6"/><stop offset=".5" stop-color="#333"/><stop offset="1" stop-color="{BLOOD}" stop-opacity=".7"/></linearGradient>
      <linearGradient id="hpgrad" x1="0" x2="1"><stop offset="0" stop-color="{BLOOD_DEEP}"/><stop offset="1" stop-color="{BLOOD}"/></linearGradient>
      <linearGradient id="gatehaze" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset=".5" stop-color="{GOLD}" stop-opacity=".22"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
      <linearGradient id="fadeg" x1="0" x2="1"><stop offset="0" stop-color="#000"/><stop offset=".55" stop-color="#FFF"/></linearGradient>
      <mask id="goldfade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect x="{GOLD_CLIP_LEFT}" y="0" width="{GATE_X-GOLD_CLIP_LEFT}" height="{H}" fill="url(#fadeg)"/></mask>
      <clipPath id="redclip"><rect x="{GATE_X}" y="0" width="{RED_CLIP_RIGHT-GATE_X}" height="{H}"/></clipPath>
      <clipPath id="goldclip"><rect x="{GOLD_CLIP_LEFT}" y="0" width="{GATE_X-GOLD_CLIP_LEFT}" height="{H}"/></clipPath>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>"""

    # a fade on the right edge so sins look like they seep out of the boss
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-labelledby="t d"><title id="t">The Last Judgment — {html.escape(user)}</title>'
            f'<desc id="d">{html.escape(user)}\'s contribution graph as a boss battle: {fmt(shown_total)} contributions '
            f'over {weeks} weeks are judged at a golden gate until The Darkness falls.</desc>'
            f'<style>{"".join(css)}</style>{defs}{"".join(body)}</svg>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "festomanolo"))
    ap.add_argument("--out", default="assets/judgment.svg")
    ap.add_argument("--demo", action="store_true", help="use random data instead of GitHub")
    args = ap.parse_args()
    grid, total = load(args.user, args.demo)
    svg = build(grid, total, args.user)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(svg, encoding="utf-8")
    notes = sum(1 for col in grid for c in col if c and c["level"])
    print(f"judged {total:,} contributions ({notes} active days, {len(grid)} weeks) -> {args.out} "
          f"({len(svg)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
