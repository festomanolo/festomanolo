#!/usr/bin/env python3
"""
ASCENSION
The last year of contributions, rebuilt as a gothic city over a sea of lava,
and one pilgrim's run from the Abyss to Heaven's Gate.

  * every week is a tower; its seven windows are that week's seven days,
    lit gold by how much you shipped
  * taller towers = heavier weeks; the Punished God leaps from roof to roof
  * empty weeks are where demons wait; he cuts them down on the run
  * every tower holds a soul (that week's contributions), gathered as he passes
  * at the end of the year, The Darkness guards the Gate: three rounds,
    dodge its fire, return divine light, then walk into the Gate

Pure SVG + CSS keyframes on one master clock, no JavaScript,
so it plays inside a GitHub README.

Usage:
    python forge/ascension.py --user festomanolo --out assets/ascension.svg
    python forge/ascension.py --demo --out preview.svg
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
BLOOD, DEEP, GOLD, ASH, BONE = "#FF0000", "#7B0000", "#FFD700", "#8C8C8C", "#F5F1E8"
WINDOW = ["#1E0E0B", "#6B4E00", "#A87F00", "#E0B400", "#FFE45C"]   # day levels 0..4

# ---------------------------------------------------------------- stage (screen)
W, H = 900, 400
GROUND = 322            # lava line
HX = 250                # hero screen x while running
COLW, BLOCKW = 58, 44   # tower pitch and width; the rest is a lava crevice
START_L, START_R = 30, 196
COL0 = 222

# ---------------------------------------------------------------- clock
RUN0 = 4.0              # run begins
SPEED = 80.0            # px / s
EPS = 0.015
# ================================================================ data
def fetch_scrape(user: str):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "ascension"})
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
        "User-Agent": "ascension"})
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

# ================================================================ helpers
def font_face(name, file, weight):
    b64 = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
    return (f"@font-face{{font-family:'{name}';font-weight:{weight};font-style:normal;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def fmt(n):
    return f"{n:,}"


class Clock:
    def __init__(self, T):
        self.T = T

    def p(self, t):
        return f"{max(0.0, min(100.0, t / self.T * 100)):.3f}%"


def simplify(points, tol=0.35):
    """Drop samples that lie on the straight line between their neighbours."""
    if len(points) < 3:
        return points
    out = [points[0]]
    for i in range(1, len(points) - 1):
        (t0, *a), (t1, *b), (t2, *c) = out[-1], points[i], points[i + 1]
        u = (t1 - t0) / (t2 - t0) if t2 != t0 else 0
        if any(abs(bv - (av + (cv - av) * u)) > tol for av, bv, cv in zip(a, b, c)):
            out.append(points[i])
    out.append(points[-1])
    return out


# ================================================================ world model
def build(grid, total, user):
    N = len(grid)
    wk = []
    for col in grid:
        c = sum(d["count"] for d in col if d) or sum(d["level"] for d in col if d)
        wk.append(c)
    maxc = max(wk) or 1
    shown_total = total or sum(wk)
    scale_score = shown_total / (sum(wk) or 1)

    def tower_h(c):
        return 80 if c == 0 else 100 + 116 * math.log1p(c) / math.log1p(maxc)

    tops = [GROUND - tower_h(c) for c in wk]
    X = [COL0 + i * COLW for i in range(N)]
    XP = COL0 + N * COLW                      # final plateau (Heaven's Gate)
    start_top = GROUND - 92
    plat_top = GROUND - 92
    surfaces = [(START_L, START_R, start_top)] + [(X[i], X[i] + BLOCKW, tops[i]) for i in range(N)] + [(XP, XP + 2400, plat_top)]

    hero_start = 150
    hero_stop = XP + 40
    run_end = RUN0 + (hero_stop - hero_start) / SPEED
    B0 = run_end + 0.2                        # boss descends
    rounds = [B0 + 1.8 + k * 2.7 for k in range(3)]
    death = rounds[-1] + 1.95 + 0.35
    gate_open = death + 1.3
    walk0, walk1 = gate_open + 1.0, gate_open + 4.2
    T = walk1 + 7.2
    ck = Clock(T)
    p = ck.p

    def hero_x(t):
        if t <= RUN0:
            return hero_start
        return min(hero_stop, hero_start + SPEED * (t - RUN0))

    def time_at(x):
        return RUN0 + (x - hero_start) / SPEED

    # jumps between consecutive surfaces
    jumps = []
    for a, b in zip(surfaces, surfaces[1:]):
        ya, yb = a[2], b[2]
        climb = max(0.0, ya - yb)
        x0 = a[1] - 9 - climb * 0.22
        x1 = b[0] + 9
        k = 15 + climb * 0.55 + max(0.0, yb - ya) * 0.08
        jumps.append((x0, x1, ya, yb, k))

    def feet(x):
        for x0, x1, ya, yb, k in jumps:
            if x0 <= x <= x1:
                u = (x - x0) / (x1 - x0)
                return (1 - u) * ya + u * yb - k * 4 * u * (1 - u)
        for s in surfaces:
            if s[0] - 1 <= x <= s[1] + 1:
                return s[2]
        return surfaces[-1][2]

    # boss geometry (screen space)
    BX, BY = 596, 150
    GATE_SX = 790
    dodge = [(r + 0.42, r + 1.12, 74) for r in rounds]        # hero jumps over each volley

    def hero_screen(t):
        """(x offset from HX, feet y) at time t."""
        y = feet(hero_x(t))
        xo = 0.0
        if t >= B0:
            y = plat_top
            for a, b_, hgt in dodge:
                if a <= t <= b_:
                    u = (t - a) / (b_ - a)
                    y = plat_top - hgt * 4 * u * (1 - u)
        if walk0 <= t:
            u = min(1.0, (t - walk0) / (walk1 - walk0))
            xo = (GATE_SX - HX) * u
            y = plat_top
        return xo, y

    # ================================================================ css
    css = [font_face("CinzelDeco", "cinzel-decorative-900.woff2", 900),
           font_face("Cinzel", "cinzel-700.woff2", 700), font_face("Cinzel", "cinzel-400.woff2", 400)]
    a = css.append
    a(f"""
    text{{font-family:'Cinzel','Trajan Pro','Times New Roman',serif}}
    .deco{{font-family:'CinzelDeco','Cinzel',serif}}
    .lbl{{font-size:10px;letter-spacing:3px;fill:{ASH}}}
    .t{{animation-duration:{T:.2f}s;animation-iteration-count:infinite;animation-timing-function:linear;animation-fill-mode:both}}
    @keyframes pop{{0%{{opacity:0}}{EPS}%{{opacity:1;transform:translateY(0)}}{p(0.9)}{{opacity:0;transform:translateY(-26px)}}100%{{opacity:0;transform:translateY(-26px)}}}}
    @keyframes slash{{0%{{opacity:0}}{EPS}%{{opacity:1;transform:rotate(-50deg) scale(.7)}}{p(0.22)}{{opacity:1;transform:rotate(25deg) scale(1.15)}}{p(0.34)}{{opacity:0;transform:rotate(40deg) scale(1.2)}}100%{{opacity:0}}}}
    @keyframes burst{{0%{{opacity:0}}{EPS}%{{opacity:1;transform:scale(.4)}}{p(0.45)}{{opacity:0;transform:scale(2.4)}}100%{{opacity:0;transform:scale(2.4)}}}}
    @keyframes geyser{{0%{{opacity:0;transform:scaleY(0)}}{EPS}%{{opacity:1;transform:scaleY(.1)}}{p(0.25)}{{opacity:1;transform:scaleY(1)}}{p(0.7)}{{opacity:0;transform:scaleY(.6)}}100%{{opacity:0;transform:scaleY(0)}}}}
    @keyframes win{{0%{{opacity:0}}{EPS}%{{opacity:1}}{p(COLW / SPEED - 0.01)}{{opacity:1}}{p(COLW / SPEED)}{{opacity:0}}100%{{opacity:0}}}}
    @keyframes stride{{0%,100%{{transform:rotate(28deg)}}50%{{transform:rotate(-28deg)}}}}
    @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
    @keyframes flicker{{0%,100%{{opacity:.75}}40%{{opacity:1}}60%{{opacity:.6}}}}
    @keyframes lava{{to{{transform:translateX(-240px)}}}}
    @keyframes rise{{0%{{transform:translateY(0);opacity:0}}15%{{opacity:.9}}100%{{transform:translateY(-150px);opacity:0}}}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    @keyframes spinr{{to{{transform:rotate(-360deg)}}}}
    @keyframes breathe{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
    @media (prefers-reduced-motion: reduce){{*{{animation-play-state:paused!important}}}}
    """)

    def kf(name, stops):
        a(f"@keyframes {name}{{" + "".join(f"{p(t)}{{{v}}}" if isinstance(t, (int, float)) else f"{t}{{{v}}}" for t, v in stops) + "}")

    # ---------------- camera + parallax
    cam0 = HX - hero_start
    camE = HX - hero_stop
    kf("cam", [("0%", f"transform:translateX({cam0}px)"), (RUN0, f"transform:translateX({cam0}px)"),
               (run_end, f"transform:translateX({camE:.1f}px)"), ("100%", f"transform:translateX({camE:.1f}px)")])
    kf("para", [("0%", "transform:translateX(0px)"), (RUN0, "transform:translateX(0px)"),
                (run_end, f"transform:translateX({(camE - cam0) * 0.28:.1f}px)"), ("100%", f"transform:translateX({(camE - cam0) * 0.28:.1f}px)")])

    # ---------------- hero path (x offset + feet y), sampled then simplified
    samples, t = [], 0.0
    while t <= T + 1e-6:
        xo, y = hero_screen(t)
        samples.append((t, xo, y))
        t += 0.04
    samples = simplify(samples)
    kf("hero", [(s[0], f"transform:translate({s[1]:.1f}px,{s[2]:.1f}px)") for s in samples[:-1]]
       + [("100%", f"transform:translate(0px,{start_top:.1f}px)")])
    kf("heroglow", [("0%", "opacity:1"), (walk1 - 0.9, "opacity:1;transform:scale(1)"), (walk1, "opacity:0;transform:scale(.3)"),
                    (T - 0.6, "opacity:0;transform:scale(.3)"), ("100%", "opacity:1;transform:scale(1)")])
    running = [(RUN0, run_end), (walk0, walk1)]
    kf("runlegs", [("0%", "opacity:0"), (RUN0 - 0.01, "opacity:0"), (RUN0, "opacity:1"), (run_end, "opacity:1"), (run_end + 0.01, "opacity:0"),
                   (walk0 - 0.01, "opacity:0"), (walk0, "opacity:1"), (walk1, "opacity:1"), (walk1 + 0.01, "opacity:0"), ("100%", "opacity:0")])
    kf("idlelegs", [("0%", "opacity:1"), (RUN0 - 0.01, "opacity:1"), (RUN0, "opacity:0"), (run_end, "opacity:0"), (run_end + 0.01, "opacity:1"),
                    (walk0 - 0.01, "opacity:1"), (walk0, "opacity:0"), (walk1, "opacity:0"), (walk1 + 0.01, "opacity:1"), ("100%", "opacity:1")])

    body, world, para, fx = [], [], [], []
    b = body.append

    # ================================================================ backdrop
    b(f'<rect width="{W}" height="{H}" fill="#000"/>')
    world_w = XP + 1100
    # the sky travels with the world: hell-red at the start of the year, heaven-gold at the gate
    para.append(f'<rect x="-40" y="0" width="{(world_w) * 0.28 + W + 80:.0f}" height="{GROUND}" fill="url(#sky)"/>')
    rnd = random.Random(21)
    x = -40
    spires = []
    while x < world_w * 0.28 + W + 40:
        w = rnd.uniform(26, 60)
        h = rnd.uniform(60, 170)
        base = GROUND
        spires.append(f"M{x:.0f} {base} V{base-h:.0f} L{x+w/2:.0f} {base-h-rnd.uniform(20,60):.0f} L{x+w:.0f} {base-h:.0f} V{base}Z")
        x += w + rnd.uniform(-6, 18)
    para.append(f'<path d="{" ".join(spires)}" fill="#0C0707" opacity=".95"/>')
    # distant windows in the silhouette
    for k in range(70):
        wx = rnd.uniform(0, world_w * 0.28 + W)
        para.append(f'<rect x="{wx:.0f}" y="{rnd.uniform(GROUND-150, GROUND-30):.0f}" width="2" height="4" fill="{DEEP}" opacity=".7"/>')
    b(f'<g class="t" style="animation-name:para">{"".join(para)}</g>')
    b(f'<rect width="{W}" height="{H}" fill="url(#vignette)"/>')

    # ================================================================ world layer
    # starting ledge
    world.append(f'<rect x="{START_L}" y="{start_top}" width="{START_R-START_L}" height="{GROUND-start_top+40}" fill="url(#stone)" stroke="#2B2320"/>')
    world.append(f'<text x="{(START_L+START_R)/2}" y="{start_top+34}" text-anchor="middle" class="lbl" style="fill:{DEEP}">THE ABYSS</text>')
    # the towers
    for i, col in enumerate(grid):
        x0, top = X[i], tops[i]
        world.append(f'<rect x="{x0}" y="{top:.1f}" width="{BLOCKW}" height="{GROUND-top+40:.1f}" fill="url(#stone)" stroke="#2B2320" stroke-width="1"/>')
        for m in range(3):   # battlements
            world.append(f'<rect x="{x0 + 2 + m*15.5:.1f}" y="{top-5:.1f}" width="9" height="5" fill="#161110"/>')
        wy = top + 13
        for d, day in enumerate(col):
            if day is None:
                continue
            lvl = day["level"]
            glow = f' filter="url(#wglow)"' if lvl >= 3 else ""
            world.append(f'<rect x="{x0 + BLOCKW/2 - 7}" y="{wy + d*9:.1f}" width="14" height="6" rx="1.2" fill="{WINDOW[lvl]}"{glow}/>')
        if i % 4 == 0:
            m = dt.date.fromisoformat(next(d for d in col if d)["date"]).strftime("%b").upper()
            world.append(f'<text x="{x0 + BLOCKW/2}" y="{GROUND-8}" text-anchor="middle" font-size="8" letter-spacing="1.5" fill="#4A3B35">{m}</text>')
    # the plateau and Heaven's Gate
    world.append(f'<rect x="{XP}" y="{plat_top}" width="1400" height="{GROUND-plat_top+40}" fill="url(#stone)" stroke="#3A3000"/>')
    gx = XP + 40 + (GATE_SX - HX)
    gw, gh = 70, 128
    gtop = plat_top - gh
    world.append(f'<rect x="{gx-gw/2-30}" y="{gtop-40}" width="{gw+60}" height="{gh+40}" fill="url(#gatelight)"/>')
    world.append(f'<path d="M{gx-gw/2} {plat_top} V{gtop+30} Q{gx-gw/2} {gtop} {gx} {gtop-18} Q{gx+gw/2} {gtop} {gx+gw/2} {gtop+30} V{plat_top}" '
                 f'fill="#FFF7D6" stroke="{GOLD}" stroke-width="3" filter="url(#glowS)"/>')
    world.append(f'<g class="t" style="animation-name:doorL;transform-origin:{gx-gw/2}px 0"><rect x="{gx-gw/2+2}" y="{gtop+14}" width="{gw/2-2}" height="{gh-14}" fill="#140F00" stroke="{GOLD}" stroke-width="1"/>'
                 f'<path d="M{gx-gw/4} {gtop+36} V{gtop+70} M{gx-gw/4-8} {gtop+46} H{gx-gw/4+8}" stroke="{GOLD}" stroke-width="2"/></g>')
    world.append(f'<g class="t" style="animation-name:doorR;transform-origin:{gx+gw/2}px 0"><rect x="{gx}" y="{gtop+14}" width="{gw/2-2}" height="{gh-14}" fill="#140F00" stroke="{GOLD}" stroke-width="1"/>'
                 f'<path d="M{gx+gw/4} {gtop+36} V{gtop+70} M{gx+gw/4-8} {gtop+46} H{gx+gw/4+8}" stroke="{GOLD}" stroke-width="2"/></g>')
    world.append(f'<g class="t" style="animation-name:beams"><polygon points="{gx-10},{gtop} {gx-150},64 {gx+150},64 {gx+10},{gtop}" fill="url(#beam)"/></g>')
    world.append(f'<text x="{gx}" y="{plat_top+30}" text-anchor="middle" class="lbl" style="fill:{GOLD}">HEAVEN\'S GATE</text>')
    kf("doorL", [("0%", "transform:scaleX(1)"), (gate_open, "transform:scaleX(1)"), (gate_open + 1.1, "transform:scaleX(.08)"),
                 (T - 0.7, "transform:scaleX(.08)"), ("100%", "transform:scaleX(1)")])
    kf("doorR", [("0%", "transform:scaleX(1)"), (gate_open, "transform:scaleX(1)"), (gate_open + 1.1, "transform:scaleX(.08)"),
                 (T - 0.7, "transform:scaleX(.08)"), ("100%", "transform:scaleX(1)")])
    kf("beams", [("0%", "opacity:0"), (gate_open + 0.3, "opacity:0"), (gate_open + 1.3, "opacity:1"), (T - 0.8, "opacity:1"), ("100%", "opacity:0")])

    # ---------------- souls: one per non-empty week, gathered as he passes
    souls_t = []
    for i in range(N):
        if wk[i] == 0:
            continue
        ox, oy = X[i] + BLOCKW / 2, tops[i] - 34
        tc = time_at(ox)
        souls_t.append((tc, i))
        kf(f"s{i}", [("0%", "opacity:1;transform:scale(1)"), (tc, "opacity:1;transform:scale(1)"), (tc + 0.18, "opacity:0;transform:scale(2.2)"),
                     ("100%", "opacity:0;transform:scale(2.2)")])
        big = wk[i] / maxc
        r = 4 + 4 * math.sqrt(big)
        world.append(f'<g class="t" style="animation-name:s{i};transform-origin:{ox}px {oy}px">'
                     f'<g style="animation:bob 1.6s ease-in-out {-(i*0.37)%1.6:.2f}s infinite">'
                     f'<circle cx="{ox}" cy="{oy}" r="{r*2.2:.1f}" fill="url(#soulhalo)"/>'
                     f'<circle cx="{ox}" cy="{oy}" r="{r:.1f}" fill="{GOLD}"/><circle cx="{ox-1}" cy="{oy-1}" r="{r*0.45:.1f}" fill="#FFF"/></g></g>')
        world.append(f'<g class="t" style="animation-name:pop;animation-delay:{tc:.3f}s"><text x="{ox}" y="{oy-14}" text-anchor="middle" '
                     f'font-size="11" font-weight="700" fill="{GOLD}">+{fmt(round(wk[i]*scale_score))}</text></g>')

    # ---------------- demons: they wait in the empty weeks
    demons, last = [], -9
    for i in range(N):
        if wk[i] == 0 and i - last >= 2 and i > 0:
            demons.append(i)
            last = i
    demons = demons[:20]
    slay_t = []
    for n, i in enumerate(demons):
        dx, dy = X[i] + BLOCKW / 2 + 6, tops[i]
        ts = time_at(dx - 18)
        slay_t.append(ts)
        kf(f"d{n}", [("0%", "opacity:1;transform:scale(1)"), (ts + 0.06, "opacity:1;transform:scale(1)"),
                     (ts + 0.1, "opacity:1;transform:scale(1.25)"), (ts + 0.3, "opacity:0;transform:scale(.2) rotate(40deg)"),
                     ("100%", "opacity:0;transform:scale(.2)")])
        world.append(f'<g class="t" style="animation-name:d{n};transform-origin:{dx}px {dy-9}px">{demon(dx, dy)}</g>')
        world.append(f'<circle class="t" cx="{dx}" cy="{dy-9}" r="10" fill="none" stroke="{BLOOD}" stroke-width="2" '
                     f'style="animation-name:burst;animation-delay:{ts+0.1:.3f}s;transform-origin:{dx}px {dy-9}px"/>')
        # the slash, drawn in world space at the hero's sword
        _, fy = hero_screen(ts)
        sx = hero_x(ts) + 14
        fx.append(f'<g class="t" style="animation-name:slash;animation-delay:{ts:.3f}s;transform-origin:{sx-6}px {fy-14}px">'
                  f'<path d="M{sx-4} {fy-34} Q{sx+22} {fy-22} {sx+6} {fy+2}" fill="none" stroke="#FFF6CC" stroke-width="3.2" stroke-linecap="round" filter="url(#glowS)"/></g>')

    # ---------------- lava geysers erupt from crevices just behind him
    for i in range(3, N, 5):
        gxw = X[i] - (COLW - BLOCKW) / 2
        tg = time_at(gxw) + 0.35
        world.append(f'<g class="t" style="animation-name:geyser;animation-delay:{tg:.3f}s;transform-origin:{gxw}px {GROUND}px">'
                     f'<path d="M{gxw-6} {GROUND} Q{gxw-9} {GROUND-60} {gxw} {GROUND-96} Q{gxw+9} {GROUND-60} {gxw+6} {GROUND}Z" fill="url(#geyserg)"/>'
                     f'<circle cx="{gxw-5}" cy="{GROUND-100}" r="2.5" fill="{BLOOD}"/><circle cx="{gxw+6}" cy="{GROUND-86}" r="2" fill="#FF7A00"/></g>')

    b(f'<g class="t" style="animation-name:cam">{"".join(world)}{"".join(fx)}</g>')

    # ================================================================ lava sea (screen space)
    b(f'<rect x="0" y="{GROUND}" width="{W}" height="{H-GROUND}" fill="url(#lavag)"/>')
    wave = "M-20 {y}" + "".join(f" q30 -7 60 0 t60 0" for _ in range(10))
    b(f'<g style="animation:lava 6s linear infinite"><path d="{wave.format(y=GROUND+3)} V{H} H-20Z" fill="#FF4A00" opacity=".32"/></g>')
    b(f'<g style="animation:lava 9s linear infinite reverse"><path d="{wave.format(y=GROUND+9)} V{H} H-20Z" fill="#2A0000" opacity=".55"/></g>')
    prnd = random.Random(4)
    for k in range(18):
        b(f'<circle cx="{prnd.uniform(10, W-10):.0f}" cy="{GROUND+prnd.uniform(4, 20):.0f}" r="{prnd.uniform(.8, 2):.1f}" fill="#FF6A00" '
          f'style="animation:rise {prnd.uniform(3, 7):.1f}s linear {-prnd.uniform(0, 7):.1f}s infinite"/>')

    # ================================================================ the boss (screen space)
    kf("bossin", [("0%", "opacity:0;transform:translateY(-220px)"), (B0, "opacity:0;transform:translateY(-220px)"),
                  (B0 + 1.1, "opacity:1;transform:translateY(0)"), ("100%", "opacity:1;transform:translateY(0)")])
    shake = [("0%", "transform:translate(0,0) scale(1);opacity:1")]
    for r in rounds:
        hit = r + 1.95
        shake += [(hit - 0.01, "transform:translate(0,0) scale(1);opacity:1"), (hit + 0.05, "transform:translate(9px,-4px) scale(.94);opacity:1"),
                  (hit + 0.12, "transform:translate(-6px,3px) scale(1.02);opacity:1"), (hit + 0.2, "transform:translate(0,0) scale(1);opacity:1")]
    rr = random.Random(9)
    tt = rounds[-1] + 2.15
    while tt < death:
        shake.append((tt, f"transform:translate({rr.uniform(-8,8):.1f}px,{rr.uniform(-5,5):.1f}px) scale(1.03);opacity:1"))
        tt += 0.05
    shake += [(death, "transform:translate(0,0) scale(1.1);opacity:1"), (death + 0.25, "transform:translate(0,0) scale(2);opacity:0"),
              ("100%", "transform:translate(0,0) scale(2);opacity:0")]
    kf("bossdie", shake)
    boss = boss_svg(BX, BY)
    b(f'<g class="t" style="animation-name:bossin"><g class="t" style="animation-name:bossdie;transform-origin:{BX}px {BY}px">{boss}')
    for r in rounds:   # hit flashes
        b(f'<circle class="t" cx="{BX}" cy="{BY}" r="20" fill="none" stroke="#FFF" stroke-width="3" '
          f'style="animation-name:burst;animation-delay:{r+1.95:.3f}s;transform-origin:{BX}px {BY}px"/>')
    b('</g></g>')

    # volleys: the eye fires, he leaps; he lands and answers with light
    for k, r in enumerate(rounds):
        tx, ty = HX - 70, GROUND - 92 - 10
        kf(f"orb{k}", [("0%", f"opacity:0;transform:translate(0,0)"), (r, "opacity:0;transform:translate(0,0) scale(.3)"),
                       (r + 0.25, "opacity:1;transform:translate(0,0) scale(1.2)"),
                       (r + 0.95, f"opacity:1;transform:translate({tx-BX}px,{ty-BY}px) scale(1)"),
                       (r + 0.97, f"opacity:0;transform:translate({tx-BX}px,{ty-BY}px) scale(1)"), ("100%", "opacity:0")])
        b(f'<g class="t" style="animation-name:orb{k};transform-origin:{BX}px {BY}px"><circle cx="{BX}" cy="{BY}" r="14" fill="url(#orbg)"/>'
          f'<circle cx="{BX}" cy="{BY}" r="5" fill="#FFD0D0"/></g>')
        b(f'<circle class="t" cx="{tx}" cy="{ty}" r="16" fill="{BLOOD}" opacity=".9" style="animation-name:burst;animation-delay:{r+0.95:.3f}s;transform-origin:{tx}px {ty}px"/>')
        # counter-strike crescent
        c0x, c0y = HX + 18, GROUND - 92 - 18
        size = 1 + k * 0.45
        kf(f"cres{k}", [("0%", "opacity:0"), (r + 1.3, f"opacity:0;transform:translate(0,0) scale({size*.6:.2f})"),
                        (r + 1.34, f"opacity:1;transform:translate(0,0) scale({size*.7:.2f})"),
                        (r + 1.95, f"opacity:1;transform:translate({BX-c0x}px,{BY-c0y}px) scale({size:.2f})"),
                        (r + 1.97, f"opacity:0;transform:translate({BX-c0x}px,{BY-c0y}px) scale({size:.2f})"), ("100%", "opacity:0")])
        b(f'<g class="t" style="animation-name:cres{k};transform-origin:{c0x}px {c0y}px">'
          f'<path d="M{c0x-6} {c0y-18} Q{c0x+16} {c0y} {c0x-6} {c0y+18} Q{c0x+4} {c0y} {c0x-6} {c0y-18}Z" fill="#FFF3B0" filter="url(#glowS)"/></g>')
        b(f'<g class="t" style="animation-name:slash;animation-delay:{r+1.25:.3f}s;transform-origin:{HX+8}px {GROUND-92-14}px">'
          f'<path d="M{HX+10} {GROUND-92-34} Q{HX+36} {GROUND-92-22} {HX+20} {GROUND-92+2}" fill="none" stroke="#FFF6CC" stroke-width="3.2" stroke-linecap="round" filter="url(#glowS)"/></g>')

    # boss death: shards, shock rings, flash
    rs = random.Random(3)
    for k in range(20):
        ang = k / 20 * math.tau + rs.uniform(-.15, .15)
        rad = rs.uniform(150, 320)
        kf(f"sh{k}", [("0%", "opacity:0"), (death, "opacity:0;transform:translate(0,0) rotate(0)"),
                      (death + 0.03, "opacity:1;transform:translate(0,0) rotate(0)"),
                      (death + 1.8, f"opacity:0;transform:translate({math.cos(ang)*rad:.0f}px,{math.sin(ang)*rad*0.7:.0f}px) rotate({rs.uniform(-540,540):.0f}deg)"),
                      ("100%", "opacity:0")])
        sz = rs.uniform(5, 12)
        b(f'<g class="t" style="animation-name:sh{k};transform-origin:{BX}px {BY}px"><polygon points="{BX},{BY-sz:.1f} {BX+sz*.6:.1f},{BY+sz*.5:.1f} {BX-sz*.5:.1f},{BY+sz*.4:.1f}" fill="{BLOOD if k % 3 else GOLD}"/></g>')
    for k in range(3):
        s0 = death + k * 0.16
        kf(f"wave{k}", [("0%", "opacity:0;transform:scale(.2)"), (s0, "opacity:0;transform:scale(.2)"), (s0 + 0.02, "opacity:1;transform:scale(.3)"),
                        (s0 + 1.4, f"opacity:0;transform:scale({5+k*1.5})"), ("100%", "opacity:0;transform:scale(5)")])
        b(f'<circle class="t" cx="{BX}" cy="{BY}" r="30" fill="none" stroke="{GOLD if k == 1 else BLOOD}" stroke-width="{0.8-k*0.15:.2f}" style="animation-name:wave{k};transform-origin:{BX}px {BY}px"/>')
    kf("whiteout", [("0%", "opacity:0"), (death, "opacity:0"), (death + 0.05, "opacity:.6"), (death + 1.1, "opacity:0"), ("100%", "opacity:0")])
    b(f'<rect class="t" width="{W}" height="{H}" fill="url(#flash)" style="animation-name:whiteout"/>')

    # ================================================================ the hero
    b(f'<g transform="translate({HX} 0)"><g class="t" style="animation-name:hero">'
      f'<g class="t" style="animation-name:heroglow;transform-origin:0px -14px">{hero_svg()}</g></g></g>')

    # ================================================================ HUD
    b(f'<rect x="0" y="0" width="{W}" height="60" fill="url(#hudfade)"/>')
    b(f'<line x1="24" y1="60" x2="{W-24}" y2="60" stroke="url(#hudline)"/>')
    b(f'<text x="30" y="28" class="lbl">SOULS GATHERED</text>')
    b(f'<text x="200" y="28" class="lbl">DEMONS SLAIN</text>')

    def counter(x, y, events, final_text, size=20, color=GOLD, prefix="c"):
        """events: sorted [(t, text)]; each text holds until the next one."""
        seq = [(0.0, "0")] + events
        for n, (t0, txt) in enumerate(seq):
            t1 = seq[n + 1][0] if n + 1 < len(seq) else T - 0.4
            if n == 0:
                kf(f"{prefix}{n}", [("0%", "opacity:1"), (t1, "opacity:1"), (t1 + 0.001, "opacity:0"), (T - 0.4, "opacity:0"), ("100%", "opacity:1")])
            else:
                kf(f"{prefix}{n}", [("0%", "opacity:0"), (t0, "opacity:0"), (t0 + 0.001, "opacity:1"), (t1, "opacity:1"), (t1 + 0.001, "opacity:0"), ("100%", "opacity:0")])
            b(f'<g class="t" style="animation-name:{prefix}{n}"><text x="{x}" y="{y}" font-size="{size}" font-weight="700" fill="{color}">{txt}</text></g>')

    cum, ev = 0, []
    for tc, i in souls_t:
        cum += wk[i]
        ev.append((tc, fmt(round(cum * scale_score))))
    if ev:
        ev[-1] = (ev[-1][0], fmt(shown_total))
    counter(30, 50, ev, fmt(shown_total), prefix="sc")
    counter(200, 50, [(t_, f"{n+1} / {len(demons)}") for n, t_ in enumerate(slay_t)], "", color=BLOOD, prefix="dm")

    b(f'<text x="{W/2}" y="40" text-anchor="middle" class="deco" font-size="22" letter-spacing="6" fill="url(#titlegrad)">ASCENSION</text>')

    # right: pilgrimage progress, which becomes the boss bar at the gate
    bw = 210
    bx = W - 30 - bw
    kf("pilgrim", [("0%", "opacity:1"), (B0, "opacity:1"), (B0 + 0.3, "opacity:0"), (T - 0.5, "opacity:0"), ("100%", "opacity:1")])
    kf("bosshud", [("0%", "opacity:0"), (B0, "opacity:0"), (B0 + 0.3, "opacity:1"), (death, "opacity:1"), (death + 0.3, "opacity:0"), ("100%", "opacity:0")])
    kf("wonhud", [("0%", "opacity:0"), (death + 0.2, "opacity:0"), (death + 0.5, "opacity:1"), (T - 0.5, "opacity:1"), ("100%", "opacity:0")])
    kf("prog", [("0%", "transform:scaleX(0)"), (RUN0, "transform:scaleX(0)"), (run_end, "transform:scaleX(1)"), ("100%", "transform:scaleX(1)")])
    hp = [("0%", "transform:scaleX(1)")]
    for k, r in enumerate(rounds):
        hp += [(r + 1.95, f"transform:scaleX({1 - k/3:.3f})"), (r + 2.05, f"transform:scaleX({1 - (k+1)/3:.3f})")]
    hp += [("100%", "transform:scaleX(0)")]
    kf("hp", hp)
    b(f'<g class="t" style="animation-name:pilgrim"><text x="{W-30}" y="28" text-anchor="end" class="lbl" style="fill:{GOLD}">THE PILGRIMAGE</text>'
      f'<rect x="{bx}" y="38" width="{bw}" height="9" fill="#141000" stroke="#5A4A00"/>'
      f'<g class="t" style="animation-name:prog;transform-origin:{bx}px 0"><rect x="{bx+1.5}" y="39.5" width="{bw-3}" height="6" fill="url(#progg)"/></g></g>')
    b(f'<g class="t" style="animation-name:bosshud"><text x="{W-30}" y="28" text-anchor="end" class="lbl" style="fill:{BLOOD}">THE DARKNESS</text>'
      f'<rect x="{bx}" y="38" width="{bw}" height="9" fill="#1A0000" stroke="{DEEP}"/>'
      f'<g class="t" style="animation-name:hp;transform-origin:{bx}px 0"><rect x="{bx+1.5}" y="39.5" width="{bw-3}" height="6" fill="url(#hpgrad)"/></g>'
      + "".join(f'<line x1="{bx+bw*k/3:.1f}" y1="38" x2="{bx+bw*k/3:.1f}" y2="47" stroke="#000" stroke-width="2"/>' for k in (1, 2)) + '</g>')
    b(f'<g class="t" style="animation-name:wonhud"><text x="{W-30}" y="28" text-anchor="end" class="lbl" style="fill:{GOLD}">THE GATE IS OPEN</text>'
      f'<rect x="{bx}" y="38" width="{bw}" height="9" fill="url(#progg)"/></g>')

    # footer: which week he is crossing
    b(f'<rect x="0" y="{H-34}" width="{W}" height="34" fill="url(#footfade)"/>')
    b(f'<text x="30" y="{H-12}" class="lbl" style="fill:#C7A9A0">{html.escape(user.upper())} · THE LAST 365 DAYS</text>')
    for i, col in enumerate(grid):
        first = next((d for d in col if d), None)
        if not first:
            continue
        tw = time_at(X[i] - (COLW - BLOCKW) / 2)
        label = dt.date.fromisoformat(first["date"]).strftime("%b %d, %Y").upper()
        b(f'<g class="t" style="animation-name:win;animation-delay:{tw:.3f}s"><text x="{W-30}" y="{H-12}" text-anchor="end" class="lbl" style="fill:#C7A9A0">'
          f'WEEK {i+1:02d} / {N} · {label}</text></g>')

    # ================================================================ story cards
    def card(name, t0, t1, inner, fade=0.4, at_start=False):
        if at_start:
            kf(name, [("0%", "opacity:1"), (t1 - fade, "opacity:1"), (t1, "opacity:0"), (T - 0.4, "opacity:0"), ("100%", "opacity:1")])
        else:
            kf(name, [("0%", "opacity:0"), (t0, "opacity:0;transform:translateY(6px)"), (t0 + fade, "opacity:1;transform:translateY(0)"),
                      (t1 - fade, "opacity:1;transform:translateY(0)"), (t1, "opacity:0;transform:translateY(-4px)"), ("100%", "opacity:0")])
        b(f'<g class="t" style="animation-name:{name}">{inner}</g>')

    cy = 150
    card("intro", 0, RUN0, f'<rect x="300" y="{cy-40}" width="520" height="70" fill="#000" opacity=".78"/>'
         f'<text x="560" y="{cy-10}" text-anchor="middle" class="deco" font-size="19" letter-spacing="3" fill="{BONE}">FROM THE ABYSS TO THE GATE</text>'
         f'<text x="560" y="{cy+14}" text-anchor="middle" class="lbl" style="fill:{GOLD}">{N} WEEKS · {fmt(shown_total)} SOULS · ONE PILGRIM</text>', at_start=True)
    card("guard", B0 + 0.4, B0 + 1.8, f'<text x="{BX}" y="{BY-80}" text-anchor="middle" class="lbl" style="fill:{BLOOD};font-size:12px">THE DARKNESS GUARDS THE GATE</text>')
    card("won", death + 0.5, walk1 - 0.3, f'<text x="470" y="{cy+10}" text-anchor="middle" class="deco" font-size="30" letter-spacing="6" fill="{GOLD}" filter="url(#glowS)">ASCENDED</text>'
         f'<text x="470" y="{cy+36}" text-anchor="middle" class="lbl" style="fill:{BONE}">{fmt(shown_total)} SOULS · {len(demons)} DEMONS · ONE YEAR</text>')
    card("quote", walk1, T - 0.5, f'<rect x="0" y="62" width="{W}" height="{GROUND-62}" fill="#000" opacity=".55"/>'
         f'<text x="{W/2}" y="{cy}" text-anchor="middle" font-size="17" letter-spacing="1.5" fill="{BONE}">“I believe Darkness was not created,</text>'
         f'<text x="{W/2}" y="{cy+26}" text-anchor="middle" font-size="17" letter-spacing="1.5" fill="{BONE}">it was there before our creation.”</text>'
         f'<text x="{W/2}" y="{cy+56}" text-anchor="middle" class="lbl" style="fill:{BLOOD}">AND SO THE PILGRIMAGE BEGINS AGAIN</text>')
    kf("blackout", [("0%", "opacity:1"), (0.5, "opacity:0"), (T - 0.5, "opacity:0"), ("100%", "opacity:1")])
    b(f'<rect class="t" width="{W}" height="{H}" fill="#000" style="animation-name:blackout"/>')

    # frame
    b(f'<rect x="6.5" y="6.5" width="{W-13}" height="{H-13}" fill="none" stroke="{DEEP}"/>')
    for (cx_, cy_, sx, sy) in [(6.5, 6.5, 1, 1), (W-6.5, 6.5, -1, 1), (6.5, H-6.5, 1, -1), (W-6.5, H-6.5, -1, -1)]:
        b(f'<path d="M{cx_} {cy_+22*sy} V{cy_} H{cx_+22*sx}" fill="none" stroke="{GOLD}" stroke-width="1.5"/>')

    defs = f"""<defs>
    <linearGradient id="sky" x1="0" x2="1"><stop offset="0" stop-color="#3A0000"/><stop offset=".35" stop-color="#120000"/><stop offset=".7" stop-color="#0A0800"/><stop offset="1" stop-color="#4A3800"/></linearGradient>
    <radialGradient id="vignette" cx=".5" cy=".45" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".8"/></radialGradient>
    <linearGradient id="stone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#231B18"/><stop offset=".6" stop-color="#0E0A09"/><stop offset="1" stop-color="#2A0600"/></linearGradient>
    <linearGradient id="lavag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FF5A00"/><stop offset=".12" stop-color="#C00000"/><stop offset=".5" stop-color="#3A0000"/><stop offset="1" stop-color="#050000"/></linearGradient>
    <linearGradient id="geyserg" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FF8A00"/><stop offset=".6" stop-color="{BLOOD}"/><stop offset="1" stop-color="{BLOOD}" stop-opacity="0"/></linearGradient>
    <radialGradient id="soulhalo"><stop offset="0" stop-color="{GOLD}" stop-opacity=".55"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
    <radialGradient id="orbg"><stop offset="0" stop-color="#FF8080"/><stop offset=".5" stop-color="{BLOOD}"/><stop offset="1" stop-color="{BLOOD}" stop-opacity="0"/></radialGradient>
    <radialGradient id="gatelight"><stop offset="0" stop-color="{GOLD}" stop-opacity=".45"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
    <linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FFF6C8" stop-opacity=".7"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
    <radialGradient id="bossaura"><stop offset=".3" stop-color="{BLOOD}" stop-opacity=".25"/><stop offset="1" stop-color="{BLOOD}" stop-opacity="0"/></radialGradient>
    <radialGradient id="iris"><stop offset="0" stop-color="#FFB0B0"/><stop offset=".35" stop-color="{BLOOD}"/><stop offset="1" stop-color="{DEEP}"/></radialGradient>
    <radialGradient id="flash" cx="{BX/W:.3f}" cy="{BY/H:.3f}" r=".9"><stop offset="0" stop-color="#FFF"/><stop offset=".5" stop-color="#FFE9A8"/><stop offset="1" stop-color="{BLOOD}"/></radialGradient>
    <linearGradient id="titlegrad" x1="0" x2="1"><stop offset="0" stop-color="{BLOOD}"/><stop offset=".5" stop-color="#FFF4C2"/><stop offset="1" stop-color="{GOLD}"/></linearGradient>
    <linearGradient id="hudline" x1="0" x2="1"><stop offset="0" stop-color="{BLOOD}" stop-opacity=".7"/><stop offset=".5" stop-color="#333"/><stop offset="1" stop-color="{GOLD}" stop-opacity=".6"/></linearGradient>
    <linearGradient id="hudfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".9"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></linearGradient>
    <linearGradient id="footfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset=".6" stop-color="#000" stop-opacity=".85"/></linearGradient>
    <linearGradient id="hpgrad" x1="0" x2="1"><stop offset="0" stop-color="{DEEP}"/><stop offset="1" stop-color="{BLOOD}"/></linearGradient>
    <linearGradient id="progg" x1="0" x2="1"><stop offset="0" stop-color="#6B5200"/><stop offset="1" stop-color="{GOLD}"/></linearGradient>
    <filter id="glowS" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="wglow" x="-100%" y="-200%" width="300%" height="500%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>"""

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
            f'<title id="t">Ascension — {html.escape(user)}</title>'
            f'<desc id="d">A platformer built from {html.escape(user)}\'s last year on GitHub: {N} weeks become towers whose windows are days. '
            f'The Punished God crosses them, gathers {fmt(shown_total)} souls, slays {len(demons)} demons and defeats The Darkness at Heaven\'s Gate.</desc>'
            f'<style>{"".join(css)}</style>{defs}{"".join(body)}</svg>'), T


# ================================================================ sprites
def demon(x, y):
    """A small horned imp standing on a roof at (x, y)."""
    return (f'<g style="animation:bob 1.1s ease-in-out infinite">'
            f'<path d="M{x-7} {y} L{x-8} {y-10} Q{x} {y-22} {x+8} {y-10} L{x+7} {y}Z" fill="#3A0000" stroke="{BLOOD}" stroke-width="1"/>'
            f'<path d="M{x-6} {y-14} L{x-10} {y-24} L{x-3} {y-17}Z M{x+6} {y-14} L{x+10} {y-24} L{x+3} {y-17}Z" fill="{BLOOD}"/>'
            f'<circle cx="{x-3}" cy="{y-11}" r="1.6" fill="#FFD0A0" style="animation:flicker .8s infinite"/><circle cx="{x+3}" cy="{y-11}" r="1.6" fill="#FFD0A0"/>'
            f'<path d="M{x-8} {y-8} L{x-14} {y-4} M{x+8} {y-8} L{x+14} {y-4}" stroke="{BLOOD}" stroke-width="1.2"/></g>')


def hero_svg():
    """The Punished God, feet at (0,0), facing right."""
    legs_run = (f'<g class="t" style="animation-name:runlegs">'
                f'<g style="animation:stride .34s linear infinite;transform-origin:0px -9px"><rect x="-1.6" y="-9" width="3.2" height="9" rx="1" fill="#C9A200"/></g>'
                f'<g style="animation:stride .34s linear -.17s infinite;transform-origin:0px -9px"><rect x="-1.6" y="-9" width="3.2" height="9" rx="1" fill="#8A6E00"/></g></g>')
    legs_idle = (f'<g class="t" style="animation-name:idlelegs"><rect x="-3.4" y="-9" width="3" height="9" rx="1" fill="#8A6E00"/>'
                 f'<rect x=".6" y="-9" width="3" height="9" rx="1" fill="#C9A200"/></g>')
    return (f'<ellipse cx="0" cy="-14" rx="20" ry="22" fill="url(#soulhalo)"/>'
            # cape
            f'<path d="M-2 -24 Q-14 -18 -16 -5 Q-9 -8 -4 -10Z" fill="#9E0000"/>'
            # wing
            f'<path d="M-3 -22 C-14 -34 -22 -30 -27 -36 C-24 -26 -18 -20 -6 -17Z" fill="{GOLD}" opacity=".9"/>'
            f'{legs_run}{legs_idle}'
            # body
            f'<path d="M-5 -10 L-4 -24 L4 -24 L5 -10Z" fill="{GOLD}"/>'
            f'<rect x="-5" y="-13" width="10" height="2" fill="#6B5200"/>'
            # head + halo
            f'<circle cx="0" cy="-28.5" r="4.2" fill="{BONE}"/>'
            f'<ellipse cx="0" cy="-35.5" rx="5.5" ry="1.8" fill="none" stroke="{GOLD}" stroke-width="1.4" style="animation:breathe 1.4s infinite"/>'
            # sword
            f'<path d="M4 -19 L20 -27" stroke="#FFF6CC" stroke-width="2.2" stroke-linecap="round" filter="url(#glowS)"/>'
            f'<path d="M3 -21 L6 -16" stroke="{GOLD}" stroke-width="2"/>')


def boss_svg(x, y):
    ticks = "".join(f'<line x1="{x}" y1="{y-50}" x2="{x}" y2="{y-(44 if k%3 else 40)}" stroke="{BLOOD}" stroke-width="{2 if k%3==0 else 1}" '
                    f'transform="rotate({k*10} {x} {y})"/>' for k in range(36))
    return (f'<circle cx="{x}" cy="{y}" r="95" fill="url(#bossaura)"/>'
            f'<g style="animation:spin 18s linear infinite;transform-origin:{x}px {y}px"><circle cx="{x}" cy="{y}" r="66" fill="none" stroke="{DEEP}" stroke-dasharray="2 5"/>'
            f'<circle cx="{x}" cy="{y}" r="58" fill="none" stroke="{BLOOD}" stroke-width="1.2" stroke-dasharray="46 12 6 12" opacity=".8"/></g>'
            f'<g style="animation:spinr 11s linear infinite;transform-origin:{x}px {y}px">{ticks}</g>'
            f'<path d="M{x-38} {y} Q{x} {y-30} {x+38} {y} Q{x} {y+30} {x-38} {y}Z" fill="#0A0000" stroke="{BLOOD}" stroke-width="1.6" filter="url(#glowS)"/>'
            f'<circle cx="{x}" cy="{y}" r="13" fill="url(#iris)" style="animation:breathe 2.4s ease-in-out infinite"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="2.6" ry="11" fill="#000"/>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "festomanolo"))
    ap.add_argument("--out", default="assets/ascension.svg")
    ap.add_argument("--demo", action="store_true", help="use random data instead of GitHub")
    args = ap.parse_args()
    grid, total = load(args.user, args.demo)
    svg, T = build(grid, total, args.user)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(svg, encoding="utf-8")
    print(f"ascension: {total:,} contributions, {len(grid)} weeks, {T:.1f}s loop -> {args.out} ({len(svg)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
