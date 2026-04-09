"""
Temporal Maze — Multi-Agent Negotiation Edition
================================================
Run:  pip install pygame
      python temporal_maze.py

MODES
-----
  Player mode   : Arrow/WASD=move, Space=wait, H=hint, R=restart, Q=quit
  Watch AI       : A=run single solver
  Multi-Agent    : A=run 3-robot negotiation race

MULTI-AGENT PIPELINE
--------------------
  Phase 1 – Scout     : Each robot scouts its own T-slice band concurrently.
  Phase 2 – Gossip    : Robots broadcast maps to each other (union merge).
  Phase 3 – Negotiate : Priority planning — R0 plans freely, R1 avoids R0's
                        reservations, R2 avoids R0+R1.  Cell (r,c,t) reserved
                        by at most one robot.
  Phase 4 – Execute   : All robots step simultaneously.  First to exit wins.
                        Paradox (two robots same cell same t) → red flash + log.
"""

import pygame, sys, math, random, heapq
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List

# ── colours ────────────────────────────────────────────────────────────────────
C = dict(
    bg          =(14, 18, 28),
    cell_open   =(22, 36, 70),
    cell_wall   =(32, 32, 32),
    cell_temp   =(85, 42,  0),
    cell_tint   =(55, 25, 90),
    cell_path   =(18, 95, 60),
    cell_start  =(18, 80, 45),
    cell_exit   =(120,24, 24),
    text        =(195,208,228),
    text_dim    =( 90,100,120),
    hud_bg      =( 18, 24, 38),
    hud_border  =( 44, 55, 82),
    pill_on     =( 70,138,220),
    pill_off    =( 26, 36, 60),
    pill_txt    =(175,198,235),
    win_bg      =( 16, 52, 30),
    win_border  =( 36,148, 72),
    hint_bg     =( 24, 30, 50),
    hint_border =( 70,138,220),
    warn        =(215,155, 35),
    err         =(195, 55, 55),
    paradox     =(255, 40, 40),
    r0=(255,200,  0),   # gold
    r1=( 80,200,255),   # cyan
    r2=(180, 80,255),   # violet
)
RCOLS = [C["r0"], C["r1"], C["r2"]]
NUM_R = 3

DIFFS = {
    "Medium": dict(n=9,  T=3, tw=0.18),
    "Hard":   dict(n=13, T=4, tw=0.28),
    "Expert": dict(n=17, T=5, tw=0.34),
    "Brutal": dict(n=21, T=6, tw=0.40),
}

FUI = FSM = FBIG = None   # fonts set in main()

# ── maze ───────────────────────────────────────────────────────────────────────
def build_maze(n, T, tw, seed):
    rng = random.Random(seed)
    g = [[1]*n for _ in range(n)]
    sys.setrecursionlimit(max(10000, n*n*4))

    def carve(r, c):
        g[r][c] = 0
        dirs = [(0,2),(2,0),(0,-2),(-2,0)]
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r+dr, c+dc
            if 0<=nr<n and 0<=nc<n and g[nr][nc]:
                g[r+dr//2][c+dc//2] = 0
                carve(nr, nc)

    carve(0, 0)
    g[n-1][n-1] = 0
    if n >= 2:
        if g[n-2][n-1]: g[n-2][n-1] = 0
        if g[n-1][n-2]: g[n-1][n-2] = 0

    for r in range(1, n-1):
        for c in range(1, n-1):
            if g[r][c] and rng.random() < 0.04 + tw*0.05:
                g[r][c] = 0

    tm = [[[] for _ in range(n)] for _ in range(n)]
    opens = [(r,c) for r in range(n) for c in range(n)
             if g[r][c]==0 and not(r==0 and c==0) and not(r==n-1 and c==n-1)]
    rng.shuffle(opens)
    for r, c in opens[:int(len(opens)*tw)]:
        nb = 2 if rng.random() < 0.3 else 1
        blk: set = set()
        while len(blk) < nb:
            blk.add(rng.randint(0, T-1))
        tm[r][c] = list(blk)

    return g, tm


def walled(g, tm, n, T, r, c, t):
    if r < 0 or r >= n or c < 0 or c >= n: return True
    if g[r][c]: return True
    if t in tm[r][c]: return True
    return False


def astar(g, tm, n, T, sr=0, sc=0, st=0, reserved: Optional[Dict]=None):
    heur = lambda r, c: abs(r-(n-1)) + abs(c-(n-1))
    key  = lambda r, c, t: (r*n+c)*T+t
    heap = []; gs = {}; came = {}
    k0 = key(sr, sc, st); gs[k0] = 0
    heapq.heappush(heap, (heur(sr,sc), sr, sc, st))
    vis = set()
    while heap:
        _, r, c, t = heapq.heappop(heap)
        k = key(r, c, t)
        if k in vis: continue
        vis.add(k)
        if r == n-1 and c == n-1:
            path = []; cur = f"{r},{c},{t}"
            while cur in came:
                rr, cc, tt = map(int, cur.split(','))
                path.append((rr, cc, tt))
                cur = came[cur]
            path.append((sr, sc, st))
            path.reverse()
            return path
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1),(0,0)]:
            nr, nc, nt = r+dr, c+dc, (t+1)%T
            if walled(g, tm, n, T, nr, nc, nt): continue
            if reserved and (nr, nc, nt) in reserved: continue
            nk = key(nr, nc, nt)
            ng = gs.get(k, 0) + 1 + (0.3 if dr==dc==0 else 0)
            if gs.get(nk, 1e18) > ng:
                gs[nk] = ng
                came[f"{nr},{nc},{nt}"] = f"{r},{c},{t}"
                heapq.heappush(heap, (ng + heur(nr,nc), nr, nc, nt))
    return None


def robot_starts(n):
    candidates = [(0,0),(0,1),(1,0),(0,2),(2,0),(1,1),(2,2)]
    return [(r,c) for r,c in candidates if r<n and c<n][:NUM_R]


def negotiate(g, tm, n, T):
    reserved: Dict[Tuple,int] = {}
    starts = robot_starts(n)
    paths = []
    for rid in range(NUM_R):
        sr, sc = starts[rid]
        st = next((tt for tt in range(T) if not walled(g,tm,n,T,sr,sc,tt)), 0)
        path = astar(g, tm, n, T, sr, sc, st, reserved)
        if path is None:
            path = astar(g, tm, n, T, sr, sc, st, None)
        paths.append(path)
        if path:
            for r, c, t in path:
                reserved[(r, c, t)] = rid
    return paths, reserved


# ── game state ─────────────────────────────────────────────────────────────────
@dataclass
class GS:
    n: int=13; T: int=4; tw: float=0.28
    diff: str="Hard"; mode: str="player"
    grid: list = field(default_factory=list)
    temporal: list = field(default_factory=list)
    seed: int=0

    pr: int=0; pc: int=0; pt: int=0
    steps: int=0; waits: int=0; won: bool=False; par: int=0
    trail: list = field(default_factory=list)
    view_t: int=0
    path_set: set = field(default_factory=set)

    msg: str=""; msg_col: tuple=field(default_factory=lambda:C["text_dim"])
    msg_timer: int=0

    scout_pos: list = field(default_factory=list)
    solver_pos: Optional[tuple]=None
    ai_running: bool=False

    ma_mode: bool=False
    ma_paths: list = field(default_factory=list)
    ma_step: int=0
    ma_pos: list = field(default_factory=list)
    ma_done: list = field(default_factory=list)
    ma_winner: int=-1
    ma_reserved: dict = field(default_factory=dict)
    ma_paradox: list = field(default_factory=list)
    ma_trails: list = field(default_factory=list)
    ma_phase: str=""
    ma_log: list = field(default_factory=list)

    hint_txt: str=""; show_hint: bool=False


def new_level(s: GS):
    for _ in range(30):
        seed = random.randint(0, 0x7fffffff)
        g, tm = build_maze(s.n, s.T, s.tw, seed)
        path = astar(g, tm, s.n, s.T)
        if path:
            s.seed=seed; s.grid=g; s.temporal=tm; s.par=len(path); break
    s.pr=s.pc=s.pt=0; s.steps=s.waits=0; s.view_t=0
    s.trail=[]; s.path_set=set(); s.won=False; s.msg=""
    s.scout_pos=[]; s.solver_pos=None; s.ai_running=False
    s.ma_mode=False; s.ma_paths=[]; s.ma_step=0
    s.ma_pos=list(robot_starts(s.n))
    s.ma_done=[False]*NUM_R; s.ma_winner=-1
    s.ma_reserved={}; s.ma_paradox=[]
    s.ma_trails=[[] for _ in range(NUM_R)]
    s.ma_phase=""; s.ma_log=[]
    s.hint_txt=""; s.show_hint=False


# ── draw helpers ───────────────────────────────────────────────────────────────
def drect(surf, color, rect, r=6, a=255):
    if a < 255:
        ss = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(ss, (*color[:3], a), (0,0,rect[2],rect[3]), border_radius=r)
        surf.blit(ss, (rect[0], rect[1]))
    else:
        pygame.draw.rect(surf, color, rect, border_radius=r)


def dt(surf, txt, fnt, color, x, y, anchor="topleft"):
    img = fnt.render(str(txt), True, color)
    rc = img.get_rect(**{anchor: (x, y)})
    surf.blit(img, rc)
    return rc


def tri(surf, color, cx, cy, sz, lbl="", fnt=None):
    h = sz*0.88
    pts = [(cx, cy-h*0.55), (cx+sz*0.46, cy+h*0.40), (cx-sz*0.46, cy+h*0.40)]
    pygame.draw.polygon(surf, color, pts)
    if lbl and fnt:
        img = fnt.render(lbl, True, (25,25,25))
        surf.blit(img, img.get_rect(center=(int(cx), int(cy+h*0.08))))


# ── maze draw ──────────────────────────────────────────────────────────────────
def draw_maze(surf, s: GS, ox, oy, cell):
    n, T = s.n, s.T; g, tm = s.grid, s.temporal; vt = s.view_t
    ms = pygame.Surface((n*cell, n*cell), pygame.SRCALPHA)

    for r in range(n):
        for c in range(n):
            x, y = c*cell, r*cell
            blk = walled(g, tm, n, T, r, c, vt)
            op  = r*n+c in s.path_set
            if blk:
                fill = C["cell_temp"] if not g[r][c] else C["cell_wall"]
            else:
                fill = C["cell_path"] if op else C["cell_open"]
            pygame.draw.rect(ms, fill, (x+1,y+1,cell-2,cell-2), border_radius=2)
            if not blk and tm[r][c]:
                tint = pygame.Surface((cell-2,cell-2), pygame.SRCALPHA)
                tint.fill((*C["cell_tint"], 50))
                ms.blit(tint, (x+1, y+1))
            if r==0 and c==0:
                pygame.draw.rect(ms, C["cell_start"], (x+2,y+2,cell-4,cell-4), border_radius=2)
            if r==n-1 and c==n-1:
                pygame.draw.rect(ms, C["cell_exit"], (x+2,y+2,cell-4,cell-4), border_radius=2)

    # paradox flash
    for pr2, pc2 in s.ma_paradox:
        pf = pygame.Surface((cell-2,cell-2), pygame.SRCALPHA)
        pf.fill((*C["paradox"], 130))
        ms.blit(pf, (pc2*cell+1, pr2*cell+1))

    for i in range(n+1):
        pygame.draw.line(ms, (*C["bg"], 65), (i*cell,0),(i*cell,n*cell))
        pygame.draw.line(ms, (*C["bg"], 65), (0,i*cell),(n*cell,i*cell))

    lf = pygame.font.SysFont("monospace", max(8,cell//4), bold=True)
    dt(ms, "S", lf, (255,255,255), cell//2, cell//2, "center")
    dt(ms, "E", lf, (255,255,255), (n-1)*cell+cell//2, (n-1)*cell+cell//2, "center")
    surf.blit(ms, (ox, oy))

    af = pygame.font.SysFont("monospace", max(7,cell//5), bold=True)

    # player trail + agent
    for tr, tc in s.trail:
        ts = pygame.Surface((cell-4,cell-4), pygame.SRCALPHA)
        ts.fill((*C["r0"], 38))
        surf.blit(ts, (ox+tc*cell+2, oy+tr*cell+2))
    if s.mode == "player" and not s.won:
        tri(surf, C["r0"], ox+s.pc*cell+cell//2, oy+s.pr*cell+cell//2,
            max(8,int(cell*0.68)), "P", af)

    # single AI solver
    if s.solver_pos:
        tri(surf, C["r0"], ox+s.solver_pos[1]*cell+cell//2,
            oy+s.solver_pos[0]*cell+cell//2, max(8,int(cell*0.68)), "A", af)

    # scouts
    for sr2, sc2, st2, alpha in s.scout_pos:
        if st2 != vt: continue
        cx2 = ox+sc2*cell+cell//2; cy2 = oy+sr2*cell+cell//2
        rad = max(4, int(cell*0.23))
        ss2 = pygame.Surface((rad*2+2,rad*2+2), pygame.SRCALPHA)
        pygame.draw.circle(ss2, (*C["r1"], int(alpha*255)), (rad+1,rad+1), rad)
        surf.blit(ss2, (cx2-rad-1, cy2-rad-1))

    # multi-agent robots
    if s.ma_phase:
        for rid in range(NUM_R):
            col = RCOLS[rid]
            for tr2, tc2 in s.ma_trails[rid]:
                ts2 = pygame.Surface((cell-4,cell-4), pygame.SRCALPHA)
                ts2.fill((*col, 32))
                surf.blit(ts2, (ox+tc2*cell+2, oy+tr2*cell+2))
            if rid < len(s.ma_pos):
                pr3, pc3 = s.ma_pos[rid]
                if s.ma_done[rid]:
                    pygame.draw.circle(surf, col,
                        (ox+pc3*cell+cell//2, oy+pr3*cell+cell//2), max(4,cell//5))
                else:
                    tri(surf, col, ox+pc3*cell+cell//2, oy+pr3*cell+cell//2,
                        max(8,int(cell*0.65)), str(rid), af)


# ── HUD ────────────────────────────────────────────────────────────────────────
def draw_hud(surf, s: GS, W, hh):
    drect(surf, C["hud_bg"], (0,0,W,hh), r=0)
    pygame.draw.line(surf, C["hud_border"], (0,hh),(W,hh))

    if s.mode == "player":
        x = 10
        for lbl, val in [("Steps",s.steps),("Waits",s.waits),
                         ("Time",f"t={s.view_t}"),("Par",s.par)]:
            dt(surf, lbl, FSM, C["text_dim"], x, 5)
            dt(surf, val, FUI, C["text"], x, 17)
            x += 72
    else:
        phase_col = {
            "scout":C["r1"],"gossip":C["warn"],"negotiate":C["r2"],
            "execute":C["win_border"],"done":C["win_border"]
        }.get(s.ma_phase, C["text_dim"])
        if s.ma_phase:
            dt(surf, f"Phase: {s.ma_phase.upper()}", FUI, phase_col, 10, 12)
            if s.ma_winner >= 0:
                dt(surf, f"Winner: Robot {s.ma_winner}!", FUI,
                   RCOLS[s.ma_winner], 200, 12)
            for rid in range(NUM_R):
                n_steps = len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0
                status = "done" if rid<len(s.ma_done) and s.ma_done[rid] else f"step {min(s.ma_step,n_steps)}"
                dt(surf, f"R{rid}: {status}", FSM, RCOLS[rid], 10+rid*120, 30)
        else:
            dt(surf, f"{s.diff}  {s.n}×{s.n}  T={s.T}", FUI, C["text"], 10, 12)

    # t-pills
    px2 = W - s.T*42 - 8
    for t in range(s.T):
        on = (t == s.view_t)
        drect(surf, C["pill_on"] if on else C["pill_off"], (px2,7,36,20), r=10)
        dt(surf, f"t={t}", FSM, C["pill_txt"], px2+18, 17, "center")
        px2 += 42

    # robot colour legend when multi
    if s.ma_phase or s.mode=="multi":
        lx = W - s.T*42 - 8 - 200
        for rid in range(NUM_R):
            pygame.draw.circle(surf, RCOLS[rid], (lx+rid*60+10,18), 7)
            dt(surf, f"R{rid}", FSM, RCOLS[rid], lx+rid*60+22, 12)


def draw_ma_log(surf, s: GS, W, y0):
    for i, line in enumerate(s.ma_log[-6:]):
        dt(surf, line, FSM, C["text_dim"], W//2, y0+i*14, "center")


def draw_hint(surf, s: GS, W, H):
    if not s.show_hint or not s.hint_txt: return
    lines = s.hint_txt.split("\n")
    pw = min(W-40,520); ph = len(lines)*17+18
    px = (W-pw)//2; py = H//2-ph//2
    drect(surf, C["hint_bg"], (px,py,pw,ph), r=10)
    pygame.draw.rect(surf, C["hint_border"], (px,py,pw,ph), 1, border_radius=10)
    for i, ln in enumerate(lines):
        dt(surf, ln, FSM, C["text"], px+12, py+9+i*17)


def draw_win(surf, s: GS, W, H):
    if not s.won: return
    if s.mode == "player":
        eff = round(s.par/max(s.steps,1)*100)
        lines = ["Exit reached!",
                 f"Steps {s.steps}  Waits {s.waits}  Par {s.par}  Eff {eff}%",
                 "N=next level  R=restart  Q=quit"]
    else:
        w = s.ma_winner
        lines = [f"Race over! {'Robot '+str(w)+' wins!' if w>=0 else 'No winner.'}",
                 f"Robots finished: {sum(s.ma_done)}/{NUM_R}",
                 "N=next  R=restart  Q=quit"]
    pw,ph = W-60,82; px,py = 30,H//2-ph//2
    drect(surf, C["win_bg"], (px,py,pw,ph), r=12)
    pygame.draw.rect(surf, C["win_border"], (px,py,pw,ph), 1, border_radius=12)
    dt(surf, lines[0], FBIG, C["win_border"], W//2, py+10, "center")
    dt(surf, lines[1], FSM,  C["text"],       W//2, py+37, "center")
    dt(surf, lines[2], FSM,  C["text_dim"],   W//2, py+56, "center")


def draw_title(surf, W, H, sel_diff, sel_mode):
    surf.fill(C["bg"])
    dt(surf,"Temporal Maze  —  Multi-Agent Negotiation",FBIG,C["text"],W//2,28,"center")
    dt(surf,"Walls shift across time. Robots scout, gossip, negotiate, then race.",
       FSM, C["text_dim"], W//2, 58, "center")

    diffs = list(DIFFS.keys())
    cw, ch = 152, 68; total = len(diffs)*cw+(len(diffs)-1)*10
    sx = (W-total)//2
    for i, d in enumerate(diffs):
        cx2=sx+i*(cw+10); cy2=90; on=(d==sel_diff)
        drect(surf, C["pill_on"] if on else C["hud_bg"], (cx2,cy2,cw,ch), r=10)
        pygame.draw.rect(surf, C["pill_on"] if on else C["hud_border"],
                         (cx2,cy2,cw,ch), 1, border_radius=10)
        info = DIFFS[d]
        dt(surf, d, FUI, C["text"], cx2+cw//2, cy2+10, "center")
        dt(surf, f"{info['n']}x{info['n']}, {info['T']} slices", FSM,
           C["text_dim"], cx2+cw//2, cy2+30, "center")
        dt(surf, f"density {int(info['tw']*100)}%", FSM,
           C["text_dim"], cx2+cw//2, cy2+47, "center")

    modes = [("player","Play yourself"),("ai","Watch single AI"),("multi","Multi-Agent Race")]
    bw = 155; gap = 12
    bx0 = W//2-(len(modes)*bw+(len(modes)-1)*gap)//2
    for i, (m, lbl) in enumerate(modes):
        on = (m==sel_mode)
        drect(surf, C["pill_on"] if on else C["hud_bg"],
              (bx0+i*(bw+gap), 182, bw, 34), r=8)
        pygame.draw.rect(surf, C["hud_border"],
                         (bx0+i*(bw+gap), 182, bw, 34), 1, border_radius=8)
        dt(surf, lbl, FSM, C["text"], bx0+i*(bw+gap)+bw//2, 199, "center")

    drect(surf, C["pill_on"], (W//2-75,232,150,38), r=10)
    dt(surf, "Start  (Enter)", FUI, (255,255,255), W//2, 251, "center")

    guide = [
        "Left/Right = select difficulty   Tab = cycle mode   Enter = start",
        "In-game player: Arrow/WASD move  Space wait  H hint  R restart  Q quit",
        "In-game AI:  A = run solver",
        "In-game multi: A = launch race   R = reset",
        "Robot colours:  Gold=R0 (priority 1)   Cyan=R1   Violet=R2",
        "Paradox (collision) = red cell flash + log message",
    ]
    for i, ln in enumerate(guide):
        dt(surf, ln, FSM, C["text_dim"], W//2, 290+i*17, "center")


# ── AI generators ──────────────────────────────────────────────────────────────
def gen_single(s: GS):
    n, T = s.n, s.T; g, tm = s.grid, s.temporal
    for t in range(T):
        for r in range(n):
            for c in range(n):
                s.scout_pos = [(sr2,sc2,st2,max(0,a-0.07))
                               for sr2,sc2,st2,a in s.scout_pos if a>0.02]
                s.scout_pos.append((r,c,t,1.0))
                s.view_t = t
                yield "scout"
    s.scout_pos = []
    path = astar(g, tm, n, T)
    if not path: s.won = True; return
    for p in path: s.path_set.add(p[0]*n+p[1])
    tw = sum(1 for i in range(1,len(path))
             if path[i][:2]==path[i-1][:2])
    s.msg = f"AI: {len(path)} steps, {tw} waits"; s.msg_col = C["text_dim"]
    for r, c, t in path:
        s.solver_pos=(r,c); s.view_t=t; yield "solve"
    s.won=True; s.solver_pos=(n-1,n-1)


def gen_multi(s: GS):
    n, T = s.n, s.T; g, tm = s.grid, s.temporal

    # ── Phase 1: Scout ──────────────────────────────────────────────────────
    s.ma_phase = "scout"
    s.ma_log = ["Phase 1: Robots scouting their time-slice bands..."]
    slices_per = max(1, T//NUM_R)
    scout_maps: Dict[int,set] = {rid: set() for rid in range(NUM_R)}

    for t in range(T):
        owner = min(t//slices_per, NUM_R-1)
        for r in range(n):
            for c in range(n):
                s.scout_pos = [(sr2,sc2,st2,max(0,a-0.06))
                               for sr2,sc2,st2,a in s.scout_pos if a>0.02]
                s.scout_pos.append((r,c,t,1.0))
                if not walled(g,tm,n,T,r,c,t):
                    scout_maps[owner].add((r,c,t))
                s.view_t = t
                yield "scout"

    s.scout_pos = []
    total = sum(len(v) for v in scout_maps.values())
    s.ma_log.append(f"Scouts found {total} open (r,c,t) cells across all slices.")
    yield "scout_done"

    # ── Phase 2: Gossip ─────────────────────────────────────────────────────
    s.ma_phase = "gossip"
    s.ma_log.append("Phase 2: Gossip broadcast — each robot shares its map...")
    all_open: set = set()
    for v in scout_maps.values(): all_open |= v
    for rid in range(NUM_R): scout_maps[rid] = all_open
    s.ma_log.append(f"Gossip done. Each robot now knows all {len(all_open)} open cells.")
    yield "gossip"

    # ── Phase 3: Negotiate ──────────────────────────────────────────────────
    s.ma_phase = "negotiate"
    s.ma_log.append("Phase 3: Negotiating paths (priority R0 > R1 > R2)...")
    paths, reserved = negotiate(g, tm, n, T)
    s.ma_paths = paths
    s.ma_reserved = reserved

    for rid, path in enumerate(paths):
        if path:
            wt = sum(1 for i in range(1,len(path)) if path[i][:2]==path[i-1][:2])
            s.ma_log.append(f"  R{rid}: {len(path)} steps, {wt} waits — "
                            f"{'conflict-free' if rid==0 else 'avoids R'+',R'.join(str(j) for j in range(rid))}")
        else:
            s.ma_log.append(f"  R{rid}: no path found — using best-effort route")
    yield "negotiate"

    # ── Phase 4: Execute ────────────────────────────────────────────────────
    s.ma_phase = "execute"
    s.ma_log.append("Phase 4: Robots racing simultaneously...")
    max_steps = max((len(p) for p in paths if p), default=0)

    for step in range(max_steps):
        s.ma_step = step
        s.ma_paradox = []
        occupied: Dict[tuple,int] = {}

        for rid in range(NUM_R):
            if s.ma_done[rid]: continue
            path = paths[rid]
            if not path or step >= len(path):
                s.ma_done[rid] = True; continue
            r, c, t = path[step]
            s.ma_pos[rid] = (r, c)
            s.view_t = t
            s.ma_trails[rid].append((r, c))
            if len(s.ma_trails[rid]) > 22: s.ma_trails[rid].pop(0)

            if (r,c) in occupied:
                s.ma_paradox.append((r,c))
                other = occupied[(r,c)]
                s.ma_log.append(f"  PARADOX! R{rid} & R{other} collide at ({r},{c}) t={t}")
            occupied[(r,c)] = rid

            if r==n-1 and c==n-1 and not s.ma_done[rid]:
                s.ma_done[rid] = True
                if s.ma_winner < 0:
                    s.ma_winner = rid
                    s.ma_log.append(f"  *** Robot {rid} reaches exit first — WINNER! ***")

        if all(s.ma_done): break
        yield "execute"

    # finish any lingering robots
    for rid in range(NUM_R):
        if not s.ma_done[rid]: s.ma_done[rid]=True

    s.ma_phase = "done"; s.ma_mode = False
    if s.ma_winner < 0 and any(s.ma_done):
        s.ma_winner = next(i for i,d in enumerate(s.ma_done) if d)
    s.won = True
    s.ma_log.append(f"Race complete. Winner: {'R'+str(s.ma_winner) if s.ma_winner>=0 else 'none'}  "
                    f"| Paradoxes: {len(s.ma_paradox)}")
    yield "done"


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    global FUI, FSM, FBIG

    pygame.init()
    screen = pygame.display.set_mode((880, 720), pygame.RESIZABLE)
    pygame.display.set_caption("Temporal Maze — Multi-Agent Negotiation")
    clock = pygame.time.Clock()

    FUI  = pygame.font.SysFont("segoeui",  13)
    FBIG = pygame.font.SysFont("segoeui",  19)
    FSM  = pygame.font.SysFont("segoeui",  11)

    sel_diff = "Hard"; sel_mode = "player"
    cur_scr  = "title"
    state    = GS()
    ai_gen   = None; ai_accum = 0.0

    SCOUT_MS = 7; SOLVE_MS = 80; EXEC_MS = 110

    def start():
        nonlocal cur_scr, ai_gen
        cfg = DIFFS[sel_diff]
        state.n=cfg["n"]; state.T=cfg["T"]; state.tw=cfg["tw"]
        state.diff=sel_diff; state.mode=sel_mode
        new_level(state); cur_scr="game"; ai_gen=None

    def smsg(txt, col=None, dur=200):
        state.msg=txt; state.msg_col=col or C["text_dim"]; state.msg_timer=dur

    def pmove(dr, dc):
        if state.won or state.mode!="player": return
        nr,nc,nt = state.pr+dr, state.pc+dc, (state.pt+1)%state.T
        if walled(state.grid, state.temporal, state.n, state.T, nr, nc, nt):
            smsg("Blocked! Wall at next time step." if dr or dc
                 else "Cannot wait — wall appears here next step!",
                 C["warn"] if not(dr or dc) else C["err"]); return
        if dr==dc==0: state.waits+=1
        state.pr,state.pc,state.pt=nr,nc,nt; state.steps+=1; state.view_t=nt
        state.trail.append((nr,nc))
        if len(state.trail)>20: state.trail.pop(0)
        smsg("")
        if nr==state.n-1 and nc==state.n-1: state.won=True

    def do_hint():
        path = astar(state.grid, state.temporal, state.n, state.T)
        if not path: state.hint_txt="No solution found."; state.show_hint=True; return
        twpts=[path[i][2] for i in range(1,len(path)) if path[i][:2]==path[i-1][:2]]
        if twpts:
            state.hint_txt=(f"Optimal: {len(path)} steps, {len(twpts)} wait(s).\n"
                            f"Waits at t={', t='.join(map(str,twpts))}\n"
                            f"Press Space when a temporal wall blocks you — opens at t+1.")
        else:
            state.hint_txt=(f"Optimal: {len(path)} steps, no waits needed.\n"
                            f"Pure spatial navigation — find the open corridor.")
        state.show_hint = not state.show_hint

    def launch_single():
        nonlocal ai_gen
        if state.ai_running: return
        state.ai_running=True; ai_gen=gen_single(state)

    def launch_multi():
        nonlocal ai_gen
        if state.ai_running: return
        state.ai_running=True; state.ma_mode=True
        state.ma_pos=list(robot_starts(state.n))
        state.ma_done=[False]*NUM_R; state.ma_winner=-1
        state.ma_trails=[[] for _ in range(NUM_R)]
        state.ma_paradox=[]; state.ma_log=[]
        ai_gen=gen_multi(state)

    def reset_ai():
        nonlocal ai_gen
        state.ai_running=False; state.ma_mode=False; ai_gen=None
        state.scout_pos=[]; state.solver_pos=None
        state.path_set=set(); state.ma_phase=""
        state.ma_pos=list(robot_starts(state.n))
        state.ma_done=[False]*NUM_R; state.ma_winner=-1
        state.ma_trails=[[] for _ in range(NUM_R)]
        state.ma_paradox=[]; state.ma_log=[]; state.won=False

    while True:
        W, H = screen.get_size()
        dt_ms = clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()

            if cur_scr == "title":
                diffs = list(DIFFS.keys())
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN: start()
                    if ev.key == pygame.K_TAB:
                        ml=["player","ai","multi"]
                        sel_mode=ml[(ml.index(sel_mode)+1)%len(ml)]
                    if ev.key in (pygame.K_LEFT,):
                        idx=diffs.index(sel_diff); sel_diff=diffs[max(0,idx-1)]
                    if ev.key in (pygame.K_RIGHT,):
                        idx=diffs.index(sel_diff); sel_diff=diffs[min(len(diffs)-1,idx+1)]
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    mx2,my2=ev.pos
                    cw2=152; total2=len(diffs)*cw2+(len(diffs)-1)*10
                    sx3=(W-total2)//2
                    for i,d in enumerate(diffs):
                        if sx3+i*(cw2+10)<=mx2<=sx3+i*(cw2+10)+cw2 and 90<=my2<=158:
                            sel_diff=d
                    bw2=155; gap2=12
                    bx3=W//2-(3*bw2+2*gap2)//2
                    for i,(m,_) in enumerate([("player",""),("ai",""),("multi","")]):
                        if bx3+i*(bw2+gap2)<=mx2<=bx3+i*(bw2+gap2)+bw2 and 182<=my2<=216:
                            sel_mode=m
                    if W//2-75<=mx2<=W//2+75 and 232<=my2<=270: start()

            else:
                if ev.type == pygame.KEYDOWN:
                    k = ev.key
                    if k==pygame.K_q: pygame.quit(); sys.exit()
                    if k==pygame.K_ESCAPE: cur_scr="title"
                    if k==pygame.K_r:
                        if state.mode=="player": new_level(state); ai_gen=None
                        else: reset_ai()
                    if k==pygame.K_n and state.won:
                        new_level(state); ai_gen=None; reset_ai()
                    if state.mode=="player":
                        if k in(pygame.K_UP,   pygame.K_w): pmove(-1,0)
                        if k in(pygame.K_DOWN, pygame.K_s): pmove(1,0)
                        if k in(pygame.K_LEFT, pygame.K_a): pmove(0,-1)
                        if k in(pygame.K_RIGHT,pygame.K_d): pmove(0,1)
                        if k==pygame.K_SPACE: pmove(0,0)
                        if k==pygame.K_h: do_hint()
                        for ti in range(state.T):
                            if k==getattr(pygame,f"K_{ti}",None): state.view_t=ti
                    elif state.mode=="ai":
                        if k==pygame.K_a: launch_single()
                    elif state.mode=="multi":
                        if k in(pygame.K_a,pygame.K_m): launch_multi()

                if ev.type==pygame.MOUSEBUTTONDOWN:
                    mx3,my3=ev.pos
                    HH=50; BH=30; mh2=H-HH-BH
                    c3=max(18,min(mh2//state.n,(W-20)//state.n))
                    ox3=(W-c3*state.n)//2; oy3=HH+(mh2-c3*state.n)//2
                    pp2=W-state.T*42-8
                    for ti in range(state.T):
                        if pp2+ti*42<=mx3<=pp2+ti*42+36 and 7<=my3<=27:
                            state.view_t=ti
                    if state.mode=="player":
                        cc3=(mx3-ox3)//c3; cr3=(my3-oy3)//c3
                        if 0<=cr3<state.n and 0<=cc3<state.n:
                            dr3=cr3-state.pr; dc3=cc3-state.pc
                            if abs(dr3)+abs(dc3)==1:
                                pmove(int(math.copysign(1,dr3)) if dr3 else 0,
                                      int(math.copysign(1,dc3)) if dc3 else 0)
                            elif dr3==dc3==0: pmove(0,0)

        # AI tick
        if cur_scr=="game" and state.ai_running and ai_gen:
            ph = state.ma_phase
            tick = (SCOUT_MS if ph in("","scout","gossip","negotiate")
                    else EXEC_MS if ph=="execute" else SOLVE_MS)
            ai_accum += dt_ms
            if ai_accum >= tick:
                ai_accum = 0
                try: next(ai_gen)
                except StopIteration:
                    state.ai_running=False; ai_gen=None

        if state.msg_timer>0: state.msg_timer-=1
        if state.msg_timer==0 and state.msg and not state.won: state.msg=""

        # ── render ──────────────────────────────────────────────────────────
        if cur_scr=="title":
            draw_title(screen, W, H, sel_diff, sel_mode)
        else:
            screen.fill(C["bg"])
            HH=50; BH=30; mah=H-HH-BH
            cell=max(18,min(mah//state.n,(W-20)//state.n))
            ox=(W-cell*state.n)//2; oy=HH+(mah-cell*state.n)//2

            draw_hud(screen, state, W, HH)
            draw_maze(screen, state, ox, oy, cell)

            ctrl = {
                "player":"Arrow/WASD=move  Space=wait  H=hint  R=restart  Q=quit",
                "ai":    "A=run single AI solver  R=reset  Q=quit",
                "multi": "A=run multi-agent race  R=reset  Q=quit  |  Gold=R0  Cyan=R1  Violet=R2",
            }.get(state.mode,"")
            dt(screen, ctrl, FSM, C["text_dim"], W//2, H-20, "center")

            if state.msg and state.msg_timer>0:
                dt(screen, state.msg, FSM, state.msg_col, W//2, oy+cell*state.n+6, "center")

            if state.ma_log:
                draw_ma_log(screen, state, W, oy+cell*state.n+6)

            if not state.ai_running and not state.won:
                prompt = {
                    "ai":   "Press A to run AI solver",
                    "multi":"Press A to start multi-agent race",
                }.get(state.mode, "")
                if prompt:
                    dt(screen, prompt, FUI, C["pill_on"],
                       W//2, oy+cell*state.n//2, "center")

            draw_hint(screen, state, W, H)
            draw_win(screen, state, W, H)

        pygame.display.flip()


if __name__ == "__main__":
    main()