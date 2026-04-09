"""
Temporal Maze — Edge-Based Walls + Multiplayer Edition
=========================================================
pip install pygame
python temporal_maze.py

✨ FEATURES:
• Edge-based walls (lines between cells, not whole blocks)
• 4 Game Modes: Play Yourself, Watch AI, Multi-Agent Race, Local Multiplayer
• 3-player local co-op with unique key bindings
• Time mechanics: walls open/close based on time slice
• Particle effects, animations, gradients, accessibility patterns
"""

import pygame, sys, math, random, heapq, textwrap
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List, Set

# ── Palette ──────────────────────────────────────────────────────────────────
C = dict(
    bg          =( 10,  13,  22),
    panel       =( 16,  21,  36),
    panel2      =( 20,  27,  46),
    border      =( 38,  50,  80),
    border2     =( 55,  72, 115),
    cell_open   =( 20,  34,  68),
    cell_wall   =( 28,  28,  28),
    cell_temp   =( 90,  44,   0),
    cell_tint   =( 55,  22,  88),
    cell_path   =( 16,  98,  62),
    cell_start  =( 14,  82,  44),
    cell_exit   =(115,  20,  20),
    text        =(210, 220, 240),
    text2       =(150, 162, 190),
    text3       =( 85,  96, 118),
    accent      =( 70, 140, 225),
    accent2     =( 46,  96, 170),
    green       =( 36, 160,  80),
    warn        =(220, 158,  35),
    err         =(200,  55,  55),
    paradox     =(255,  35,  35),
    pill_off    =( 22,  32,  58),
    win_bg      =( 12,  48,  26),
    win_border  =( 32, 148,  70),
    r0          =(255, 200,   0),
    r1          =( 70, 200, 255),
    r2          =(185,  75, 255),
    wall_perm   =(255, 255, 255),     
    wall_temp   =(255,   0,   0),
    wall_open   =(100, 200, 255, 80),
    grad_start  =( 80, 160, 240),
    grad_end    =( 40, 100, 200),
    glow_player =(140, 220, 255),
    glow_robot0 =(255, 220, 100),
    glow_robot1 =(100, 230, 255),
    glow_robot2 =(220, 140, 255),
    grid_line   =( 30,  40,  70),
    pulse_on    =(100, 200, 255),
    pulse_off   =( 50, 100, 150),
    pattern_diag=(255, 255, 255, 25),
    pattern_dot =(255, 255, 255, 35),
)
RCOLS   = [C["r0"], C["r1"], C["r2"]]
RNAMES  = ["Gold", "Cyan", "Violet"]
NUM_R   = 3

# ── Direction Constants ──────────────────────────────────────────────────────
DIRS = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

# ── Player Key Bindings ──────────────────────────────────────────────────────
PLAYER_KEYS = {
    0: {"up": pygame.K_w, "down": pygame.K_s, "left": pygame.K_a, "right": pygame.K_d, "wait": pygame.K_LSHIFT, "name": "Player 1"},
    1: {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT, "wait": pygame.K_RSHIFT, "name": "Player 2"},
    2: {"up": pygame.K_i, "down": pygame.K_k, "left": pygame.K_j, "right": pygame.K_l, "wait": pygame.K_SPACE, "name": "Player 3"},
}

DIFFS = {
    "Medium": dict(n=9,  T=3, tw=0.18),
    "Hard":   dict(n=13, T=4, tw=0.28),
    "Expert": dict(n=17, T=5, tw=0.34),
    "Brutal": dict(n=21, T=6, tw=0.40),
}

F_TITLE = F_HEAD = F_UI = F_SM = F_MONO = None
W, H = 1024, 768

# ── Particle System ───────────────────────────────────────────────────────────
@dataclass
class Particle:
    x: float; y: float; vx: float; vy: float
    life: float; max_life: float
    color: tuple; size: float; decay: float = 0.98
    
    def update(self, dt: float) -> bool:
        self.x += self.vx * dt * 0.06
        self.y += self.vy * dt * 0.06
        self.vy += 0.02
        self.size *= self.decay
        self.life -= dt * 0.016
        return self.life > 0 and self.size > 0.5
    
    def draw(self, surf: pygame.Surface):
        alpha = int(255 * (self.life / self.max_life))
        if alpha < 10: return
        s = pygame.Surface((int(self.size*2)+1, int(self.size*2)+1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (int(self.size)+1, int(self.size)+1), int(self.size)+1)
        surf.blit(s, (int(self.x - self.size), int(self.y - self.size)))

def spawn_particles(particles: list, x, y, color, count=12, spread=2.0, life=1.5):
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(0.5, 2.5)
        particles.append(Particle(x=x, y=y, vx=math.cos(angle)*speed*spread, vy=math.sin(angle)*speed*spread-1, life=life, max_life=life, color=color, size=random.uniform(2, 5)))

# ── Drawing Helpers ───────────────────────────────────────────────────────────
def gradient_surf(w, h, start_color, end_color, vertical=True):
    surf = pygame.Surface((w, h))
    for i in range(h if vertical else w):
        ratio = i / max(1, (h if vertical else w) - 1)
        color = tuple(int(start_color[j] + (end_color[j] - start_color[j]) * ratio) for j in range(3))
        if vertical: pygame.draw.line(surf, color, (0, i), (w, i))
        else: pygame.draw.line(surf, color, (i, 0), (i, h))
    return surf

def drect_animated(surf, color, rect, r=6, a=255, border=0, bcol=None, hover=False, pulse=False, frame=0, glow_color=None):
    x,y,w,h = rect
    if pulse and isinstance(color, tuple) and len(color) >= 3:
        pulse_factor = 0.1 * math.sin(frame * 0.15)
        color = tuple(min(255, max(0, c + int(pulse_factor * 30))) for c in color[:3])
    offset_y = -2 if hover else 0
    if hover:
        shadow_surf = pygame.Surface((w+4, h+4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0,0,0,80), (2, 4, w, h), border_radius=r+2)
        surf.blit(shadow_surf, (x-1, y+1))
    if glow_color and (pulse or hover):
        glow_surf = pygame.Surface((w+6, h+6), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_color[:3], 50), (0,0,w+6,h+6), border_radius=r+3)
        surf.blit(glow_surf, (x-3, y+offset_y-3))
    if isinstance(color, (list, tuple)) and len(color) == 2:
        grad = gradient_surf(w, h+abs(offset_y), color[0], color[1])
        surf.blit(grad, (x, y+offset_y))
        pygame.draw.rect(surf, bcol or color[1], (x, y+offset_y, w, h), border_radius=r, width=max(1, border))
    else:
        if a < 255:
            ss = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(ss, (*color[:3], a), (0, 0, w, h), border_radius=r)
            surf.blit(ss, (x, y+offset_y))
        else:
            pygame.draw.rect(surf, color, (x, y+offset_y, w, h), border_radius=r)
        if border: pygame.draw.rect(surf, bcol or C["border"], (x, y+offset_y, w, h), border_radius=r, width=border)

def dtext(surf, txt, fnt, color, x, y, anchor="topleft", shadow=False, pulse=False, frame=0):
    if isinstance(color, tuple) and len(color) == 4: alpha, color_rgb = color[3], color[:3]
    else: alpha, color_rgb = 255, color if isinstance(color, tuple) else (color, color, color)
    if pulse: color_rgb = tuple(min(255, max(0, c + int(0.2 * math.sin(frame * 0.2) * 40))) for c in color_rgb)
    if shadow:
        img = fnt.render(str(txt), True, (0, 0, 0))
        surf.blit(img, img.get_rect(**{anchor: (x+1, y+1)}))
    img = fnt.render(str(txt), True, color_rgb)
    if alpha < 255: img.set_alpha(alpha)
    surf.blit(img, img.get_rect(**{anchor: (x, y)}))

def tri(surf, color, cx, cy, sz, lbl="", fnt=None, glow=False, frame=0):
    h = sz * 0.86
    pts = [(int(cx), int(cy-h*0.56)), (int(cx+sz*0.46), int(cy+h*0.40)), (int(cx-sz*0.46), int(cy+h*0.40))]
    if glow:
        gs = pygame.Surface((sz+10, sz+10), pygame.SRCALPHA)
        pygame.draw.polygon(gs, (*color[:3], 60), [(p[0]-cx+sz//2+5, p[1]-cy+sz//2+5) for p in pts], width=3)
        surf.blit(gs, (cx-sz//2-5, cy-sz//2-5))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, (0,0,0), pts, 1)
    if lbl and fnt: surf.blit(fnt.render(lbl, True, (20,20,20)), fnt.render(lbl, True, (20,20,20)).get_rect(center=(int(cx), int(cy+h*0.08))))

def draw_key_badge(surf, key_str, x, y, highlighted=False, frame=0):
    w = F_SM.size(key_str)[0] + 14
    if highlighted:
        pulse = 0.15 * math.sin(frame * 0.2)
        bg = tuple(min(255, c + int(pulse * 30)) for c in C["accent"][:3])
        drect_animated(surf, bg, (x, y, w, 20), r=5, border=2, bcol=C["glow_player"], pulse=True, frame=frame)
    else:
        drect_animated(surf, C["panel2"], (x, y, w, 20), r=5, border=1, bcol=C["border2"])
    dtext(surf, key_str, F_SM, C["text"] if highlighted else C["accent"], x+w//2, y+10, "center")
    return w

def draw_cell_pattern(surf, pattern_type, x, y, size):
    overlay = pygame.Surface((size, size), pygame.SRCALPHA)
    if pattern_type == "temporal":
        for i in range(-size, size*2, 8): pygame.draw.line(overlay, C["pattern_diag"], (i, 0), (i+size, size), width=2)
    elif pattern_type == "path":
        for i in range(3, size, 7):
            for j in range(3, size, 7): pygame.draw.circle(overlay, C["pattern_dot"], (i, j), 2)
    elif pattern_type == "start":
        pygame.draw.line(overlay, C["pattern_dot"], (2, 2), (size-2, size-2), width=2)
        pygame.draw.line(overlay, C["pattern_dot"], (size-2, 2), (2, size-2), width=2)
    elif pattern_type == "exit":
        pygame.draw.circle(overlay, C["pattern_dot"], (size//2, size//2), size//3, width=2)
    surf.blit(overlay, (x, y))

def draw_parallax_bg(surf, W, H, frame):
    for y in range(H):
        ratio = y / H
        wave = 0.03 * math.sin(frame * 0.02 + y * 0.01)
        pygame.draw.line(surf, (int(10+3*ratio+wave*5), int(13+5*ratio), int(22+15*ratio+wave*8)), (0, y), (W, y))
    for i in range(-2, W//50 + 3):
        x = i * 50 - (frame * 0.4) % 50
        pygame.draw.line(surf, (*C["grid_line"], int(20+12*math.sin(frame*0.05+i*0.3))), (x, 0), (x, H), width=1)

def apply_screen_shake(offset, intensity, duration):
    if duration <= 0: return (0, 0), 0
    return (random.randint(-intensity, intensity), random.randint(-intensity, intensity)), duration - 1

# ── Edge-Based Maze Logic ─────────────────────────────────────────────────────
def build_maze_edge(n, T, tw, seed):
    rng = random.Random(seed)
    walls = [[{'N','S','E','W'} for _ in range(n)] for _ in range(n)]
    tm = [[{} for _ in range(n)] for _ in range(n)]
    sys.setrecursionlimit(max(10000, n*n*4))
    
    def carve(r, c):
        dirs = list(DIRS.items()); rng.shuffle(dirs)
        for direction, (dr, dc) in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and walls[nr][nc] == {'N','S','E','W'}:
                walls[r][c].discard(direction); walls[nr][nc].discard(OPPOSITE[direction]); carve(nr, nc)
    
    carve(0, 0)
    walls[0][0].discard('N'); walls[0][0].discard('W')
    walls[n-1][n-1].discard('S'); walls[n-1][n-1].discard('E')
    
    edges = [(r, c, d) for r in range(n) for c in range(n) for d in DIRS if 0<=r+DIRS[d][0]<n and 0<=c+DIRS[d][1]<n]
    rng.shuffle(edges)
    for r, c, direction in edges[:int(len(edges) * tw)]:
        nb = 2 if rng.random() < 0.3 else 1
        blocked = set()
        while len(blocked) < nb: blocked.add(rng.randint(0, T-1))
        tm[r][c][direction] = list(blocked)
    return walls, tm

def edge_blocked(walls, tm, n, T, r, c, direction, t):
    dr, dc = DIRS.get(direction, (0, 0)); nr, nc = r + dr, c + dc
    if nr < 0 or nr >= n or nc < 0 or nc >= n: return True
    if direction in walls[r][c]: return True
    if direction in tm[r][c] and t in tm[r][c][direction]: return True
    return False

def can_move(walls, tm, n, T, r, c, dr, dc, t):
    for direction, (ddr, ddc) in DIRS.items():
        if ddr == dr and ddc == dc: return not edge_blocked(walls, tm, n, T, r, c, direction, t)
    return False

def astar_edge(walls, tm, n, T, sr=0, sc=0, st=0, reserved=None):
    heur = lambda r,c: abs(r-(n-1))+abs(c-(n-1)); key = lambda r,c,t: (r*n+c)*T+t
    heap, gs, came, vis = [], {}, {}, set()
    k0 = key(sr,sc,st); gs[k0] = 0; heapq.heappush(heap, (heur(sr,sc), sr, sc, st))
    while heap:
        _, r, c, t = heapq.heappop(heap); k = key(r,c,t)
        if k in vis: continue; vis.add(k)
        if r == n-1 and c == n-1:
            path, cur = [], f"{r},{c},{t}"
            while cur in came: rr,cc,tt = map(int,cur.split(',')); path.append((rr,cc,tt)); cur = came[cur]
            path.append((sr,sc,st)); path.reverse(); return path
        for direction, (dr, dc) in DIRS.items():
            nr, nc, nt = r+dr, c+dc, (t+1)%T
            if not can_move(walls, tm, n, T, r, c, dr, dc, t): continue
            if reserved and (nr,nc,nt) in reserved: continue
            nk = key(nr,nc,nt); ng = gs.get(k,0) + 1
            if gs.get(nk, 1e18) > ng: gs[nk] = ng; came[f"{nr},{nc},{nt}"] = f"{r},{c},{t}"; heapq.heappush(heap, (ng+heur(nr,nc), nr, nc, nt))
        nt = (t+1)%T
        if not reserved or (r,c,nt) not in reserved:
            nk = key(r,c,nt); ng = gs.get(k,0) + 0.3
            if gs.get(nk, 1e18) > ng: gs[nk] = ng; came[f"{r},{c},{nt}"] = f"{r},{c},{t}"; heapq.heappush(heap, (ng+heur(r,c), r, c, nt))
    return None

def robot_starts(n): return [(r,c) for r,c in [(0,0),(0,1),(1,0),(0,2),(2,0),(1,1),(2,2)] if r<n and c<n][:NUM_R]

def negotiate_edge(walls, tm, n, T):
    reserved, starts, paths = {}, robot_starts(n), []
    for rid in range(NUM_R):
        sr,sc = starts[rid]; st = next((tt for tt in range(T) if not edge_blocked(walls,tm,n,T,sr,sc,'E',tt)), 0)
        path = astar_edge(walls, tm, n, T, sr, sc, st, reserved) or astar_edge(walls, tm, n, T, sr, sc, st, None)
        paths.append(path)
        if path:
            for r,c,t in path: reserved[(r,c,t)] = rid
    return paths, reserved

# ── State Class ───────────────────────────────────────────────────────────────
@dataclass
class GS:
    n:int=13; T:int=4; tw:float=0.28; diff:str="Hard"; mode:str="player"
    walls:list=field(default_factory=list); temporal:list=field(default_factory=list); seed:int=0
    pr:int=0; pc:int=0; pt:int=0; steps:int=0; waits:int=0; won:bool=False; par:int=0
    trail:list=field(default_factory=list); view_t:int=0; path_set:set=field(default_factory=set)
    msg:str=""; msg_col:tuple=field(default_factory=lambda:C["text3"]); msg_timer:int=0
    scout_pos:list=field(default_factory=list); solver_pos:Optional[tuple]=None; ai_running:bool=False
    ma_mode:bool=False; ma_paths:list=field(default_factory=list); ma_step:int=0
    ma_pos:list=field(default_factory=list); ma_done:list=field(default_factory=list); ma_winner:int=-1
    ma_reserved:dict=field(default_factory=dict); ma_paradox:list=field(default_factory=list)
    ma_trails:list=field(default_factory=list); ma_phase:str=""; ma_log:list=field(default_factory=list)
    hint_txt:str=""; show_hint:bool=False; anim_tick:int=0
    particles:list=field(default_factory=list); view_transition:float=0.0; target_view_t:Optional[int]=None
    show_settings:bool=False; show_fps:bool=False; particle_fx:bool=True
    screen_shake:tuple=(0,0); shake_timer:int=0; debug_mode:bool=False
    mp_players:list=field(default_factory=lambda:[{"r":0,"c":0,"t":0,"steps":0,"waits":0,"done":False,"trail":[],"winner_order":0} for _ in range(NUM_R)])
    mp_winner:int=-1; mp_rankings:list=field(default_factory=list); mp_collisions:list=field(default_factory=list)

def new_level(s:GS):
    for _ in range(30):
        seed = random.randint(0, 0x7fffffff); walls, tm = build_maze_edge(s.n, s.T, s.tw, seed)
        if astar_edge(walls, tm, s.n, s.T): s.seed,s.walls,s.temporal,s.par = seed,walls,tm,len(astar_edge(walls,tm,s.n,s.T)); break
    s.pr=s.pc=s.pt=s.steps=s.waits=s.view_t=0; s.trail=[]; s.path_set=set(); s.won=False; s.msg=""
    s.scout_pos=[]; s.solver_pos=None; s.ai_running=False; s.ma_mode=False; s.ma_paths=[]; s.ma_step=0
    s.ma_pos=list(robot_starts(s.n)); s.ma_done=[False]*NUM_R; s.ma_winner=-1; s.ma_reserved={}; s.ma_paradox=[]
    s.ma_trails=[[] for _ in range(NUM_R)]; s.ma_phase=""; s.ma_log=[]; s.hint_txt=""; s.show_hint=False
    s.particles=[]; s.view_transition=0.0; s.target_view_t=None; s.show_settings=False; s.screen_shake=(0,0); s.shake_timer=0
    s.mp_players=[{"r":st[0],"c":st[1],"t":0,"steps":0,"waits":0,"done":False,"trail":[],"winner_order":0} for st in robot_starts(s.n)]
    s.mp_winner=-1; s.mp_rankings=[]; s.mp_collisions=[]

# ── UI Drawing Functions ──────────────────────────────────────────────────────
LEGEND_ITEMS = [(C["cell_open"],None,"Open cell"),(C["wall_perm"],None,"Permanent wall (edge)"),(C["wall_temp"],None,"Time wall (edge)"),(C["cell_tint"],None,"Changes over time"),(C["cell_path"],None,"AI path"),(C["cell_start"],None,"Start (S)"),(C["cell_exit"],None,"Exit (E)")]

def draw_legend(surf, x, y, W_panel, frame):
    drect_animated(surf, C["panel"], (x,y,W_panel,len(LEGEND_ITEMS)*22+14), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf,"Legend", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for i,(col,pattern,label) in enumerate(LEGEND_ITEMS):
        ry=y+18+i*22
        if pattern==C["wall_perm"]: pygame.draw.line(surf,col,(x+8,ry+10),(x+22,ry+10),width=3)
        elif pattern==C["wall_temp"]: pygame.draw.line(surf,col,(x+8,ry+10),(x+14,ry+10),width=2); pygame.draw.line(surf,col,(x+16,ry+10),(x+22,ry+10),width=2)
        else: drect_animated(surf,col,(x+8,ry+3,14,14),r=3,frame=frame)
        dtext(surf,label,F_SM,C["text3"],x+26,ry+4)

def draw_controls_panel(surf, x, y, W_panel, mode, frame):
    rows = {"player":[("Move","[↑↓←→]/[WASD]"),("Wait","[SPACE]"),("Hint","[H]"),("Restart","[R]"),("Menu","[ESC]"),("Quit","[Q]")],
            "ai":[("Run AI","[A]"),("Reset","[R]"),("Menu","[ESC]"),("Quit","[Q]")],
            "multi":[("Run Race","[A]"),("Reset","[R]"),("Menu","[ESC]"),("Quit","[Q]")],
            "local_mp":[("P1 Gold","[WASD]+[SPACE]"),("P2 Cyan","[Arrows]+[SHIFT]"),("P3 Violet","[IJKL]+[ENTER]"),("Restart","[R]"),("Menu","[ESC]")]}
    rows = rows.get(mode, [("Run","[A]"),("Reset","[R]"),("Menu","[ESC]")])
    ph = len(rows)*20+20
    drect_animated(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf,"Controls", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for i,(action,keys) in enumerate(rows):
        ry=y+20+i*20; col=C["accent"] if mode=="local_mp" and i<3 else C["text3"]
        dtext(surf,action+":",F_SM,col,x+8,ry); dtext(surf,keys,F_SM,C["accent"] if i<3 else C["text2"],x+W_panel-8,ry,"topright")

def draw_robot_panel(surf, x, y, W_panel, s:GS, frame):
    ph = NUM_R*38+20
    drect_animated(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf,"🤖 Robots", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for rid in range(NUM_R):
        ry=y+20+rid*38; col=RCOLS[rid]
        pygame.draw.circle(surf,col,(x+18,ry+14),8); pygame.draw.circle(surf,(0,0,0),(x+18,ry+14),8,1)
        if s.ma_phase=="execute" and not s.ma_done[rid]:
            pygame.draw.circle(surf,(*C[f"glow_robot{rid}"],40),(x+18,ry+14),10+int(2*math.sin(frame*0.3+rid)),width=2)
        fnt=pygame.font.SysFont("monospace",9,bold=True); surf.blit(fnt.render(str(rid),True,(20,20,20)),fnt.render(str(rid),True,(20,20,20)).get_rect(center=(x+18,ry+14)))
        is_winner=(rid==s.ma_winner and s.ma_winner>=0)
        dtext(surf,f"R{rid}—{RNAMES[rid]}",F_SM,col,x+32,ry+2,pulse=is_winner and frame%20<10,frame=frame)
        if s.ma_done[rid]: status,scol=("🏆 WINNER!",C["green"]) if rid==s.ma_winner else ("✓ Finished",C["text3"])
        elif s.ma_phase=="execute" and rid<len(s.ma_paths) and s.ma_paths[rid]: status,scol=f"⚡ {min(100,int(s.ma_step/max(1,len(s.ma_paths[rid]))*100))}%",C["text2"]
        elif s.ma_phase in("negotiate","scout","gossip"): status,scol=f"📋 Plan:{len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0} steps",C["text2"]
        else: status,scol="⏳ Waiting",C["text3"]
        dtext(surf,status,F_SM,scol,x+32,ry+17)
        prio,scol=["🔥 HIGH",C["green"]],["⚡ MED",C["warn"]],["💤 LOW",C["text3"]][rid]
        dtext(surf,f"prio:{prio[0]}",F_SM,prio[1],x+W_panel-8,ry+2,"topright")

def draw_mp_player_panel(surf, x, y, W_panel, s:GS, frame):
    ph = NUM_R*42+24
    drect_animated(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf,"🎮 Players", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for pid in range(NUM_R):
        player=s.mp_players[pid]; ry=y+22+pid*42; col=RCOLS[pid]; keys=PLAYER_KEYS[pid]
        pygame.draw.circle(surf,col,(x+20,ry+16),10); pygame.draw.circle(surf,(0,0,0),(x+20,ry+16),10,1)
        if player["done"] and pid==s.mp_winner:
            for angle in range(0,360,60):
                rad=14; px=x+20+int(rad*math.cos(math.radians(angle+frame*2))); py=ry+16+int(rad*math.sin(math.radians(angle+frame*2)))
                pygame.draw.circle(surf,C["r0"],(px,py),3)
        dtext(surf,f"{keys['name']}",F_SM,col,x+36,ry+4)
        dtext(surf,f"[{pygame.key.name(keys['up']).upper()}]",F_SM,C["text3"],x+36,ry+16)
        if player["done"]:
            if pid==s.mp_winner: status,scol="🏆 1st PLACE!",C["green"]
            elif pid in s.mp_rankings:
                place=s.mp_rankings.index(pid)+2; status=("🥈 2nd" if place==2 else "🥉 3rd" if place==3 else f" {place}th"); scol=C["warn"] if place==2 else C["text3"]
            else: status,scol="✓ Finished",C["text3"]
        else: status,scol=f"⚡ {player['steps']} steps",C["text2"]
        dtext(surf,status,F_SM,scol,x+36,ry+28)
        draw_key_badge(surf,pygame.key.name(keys['wait']).upper(),x+W_panel-50,ry+8,frame=frame)

def draw_maze_edge(surf, s:GS, ox, oy, cell, frame):
    n,T=s.n,s.T; walls,tm=s.walls,s.temporal; vt=s.view_t
    ms=pygame.Surface((n*cell,n*cell),pygame.SRCALPHA)
    for r in range(n):
        for c in range(n):
            x,y=c*cell,r*cell
            pygame.draw.rect(ms,C["cell_open"],(x+1,y+1,cell-2,cell-2),border_radius=2)
            if r==0 and c==0: pygame.draw.rect(ms,C["cell_start"],(x+3,y+3,cell-6,cell-6),border_radius=3)
            if r==n-1 and c==n-1:
                pulse=0.1*math.sin(frame*0.15); exit_col=tuple(min(255,c+int(pulse*30)) for c in C["cell_exit"][:3])
                pygame.draw.rect(ms,exit_col,(x+3,y+3,cell-6,cell-6),border_radius=3)
    for r in range(n):
        for c in range(n):
            x,y=c*cell,r*cell
            for direction,(dr,dc) in DIRS.items():
                nr,nc=r+dr,c+dc
                if nr<0 or nr>=n or nc<0 or nc>=n: continue
                if direction=='N': x1,y1,x2,y2=x,y,x+cell,y
                elif direction=='S': x1,y1,x2,y2=x,y+cell,x+cell,y+cell
                elif direction=='W': x1,y1,x2,y2=x,y,x,y+cell
                elif direction=='E': x1,y1,x2,y2=x+cell,y,x+cell,y+cell
                else: continue
                is_perm=direction in walls[r][c]; is_temp=direction in tm[r][c] and vt in tm[r][c][direction]
                if is_perm: 
                    # ✅ Solid black wall (Removed the white bevel line that caused the jagged look)
                    pygame.draw.line(ms, C["wall_perm"], (x1+1, y1+1), (x2-1, y2-1), width=3)
                
                elif is_temp:
                    # ✅ Dotted translucent brown wall
                    pulse = 0.3 * (0.5 + 0.5 * math.sin(frame * 0.3))
                    alpha = int(130 + pulse * 50)  # Translucent brown
                    
                    dist = math.hypot(x2-x1, y2-y1)
                    dot_radius = 2
                    spacing = 5  # Pixel distance between dots
                    
                    num_dots = int(dist / spacing)
                    for k in range(num_dots + 1):
                        progress = k / (num_dots + 1)
                        dot_x = x1 + (x2 - x1) * progress
                        dot_y = y1 + (y2 - y1) * progress
                        # Draw a circle instead of a line segment
                        pygame.draw.circle(ms, (*C["wall_temp"], alpha), (dot_x, dot_y), dot_radius)
    for i in range(n+1):
        alpha=30+int(15*math.sin(frame*0.05+i)); pygame.draw.line(ms,(*C["grid_line"],alpha),(i*cell,0),(i*cell,n*cell)); pygame.draw.line(ms,(*C["grid_line"],alpha),(0,i*cell),(n*cell,i*cell))
    lf=pygame.font.SysFont("monospace",max(8,cell//4),bold=True); dtext(ms,"S",lf,(255,255,255),cell//2,cell//2,"center"); dtext(ms,"E",lf,(255,255,255),(n-1)*cell+cell//2,(n-1)*cell+cell//2,"center")
    surf.blit(ms,(ox,oy)); af=pygame.font.SysFont("monospace",max(6,cell//5),bold=True)
    for i,(tr,tc) in enumerate(s.trail):
        age_ratio=i/max(1,len(s.trail)); alpha=int(32+40*age_ratio); ts=pygame.Surface((cell-6,cell-6),pygame.SRCALPHA); ts.fill((*C["r0"],alpha)); surf.blit(ts,(ox+tc*cell+3,oy+tr*cell+3))
    if s.mode=="player" and not s.won: tri(surf,C["r0"],ox+s.pc*cell+cell//2,oy+s.pr*cell+cell//2,max(8,int(cell*0.68)),"P",af,glow=True,frame=frame)
    if s.solver_pos: tri(surf,C["r0"],ox+s.solver_pos[1]*cell+cell//2,oy+s.solver_pos[0]*cell+cell//2,max(8,int(cell*0.68)),"A",af)
    for sr2,sc2,st2,alpha in s.scout_pos:
        if st2!=vt: continue; cx2,cy2=ox+sc2*cell+cell//2,oy+sr2*cell+cell//2; rad=max(4,int(cell*0.22)); pulse_rad=rad+int(2*math.sin(frame*0.2))
        ss2=pygame.Surface((pulse_rad*2+2,pulse_rad*2+2),pygame.SRCALPHA); pygame.draw.circle(ss2,(*C["r1"],int(alpha*255)),(pulse_rad+1,pulse_rad+1),pulse_rad); surf.blit(ss2,(cx2-pulse_rad-1,cy2-pulse_rad-1))
    if s.ma_phase:
        for rid in range(NUM_R):
            col=RCOLS[rid]; trail=s.ma_trails[rid]
            for i,(tr2,tc2) in enumerate(trail):
                age_ratio=i/max(1,len(trail)); alpha=int(28+60*age_ratio); size=int((cell-6)*(0.5+0.5*age_ratio)); offset=(cell-size)//2
                ts2=pygame.Surface((size,size),pygame.SRCALPHA); pygame.draw.rect(ts2,(*col,alpha),(0,0,size,size),border_radius=size//4); surf.blit(ts2,(ox+tc2*cell+3+offset//2,oy+tr2*cell+3+offset//2))
            if rid<len(s.ma_pos):
                pr3,pc3=s.ma_pos[rid]; cx,cy=ox+pc3*cell+cell//2,oy+pr3*cell+cell//2
                if s.ma_done[rid]:
                    pygame.draw.circle(surf,col,(cx,cy),max(4,cell//5)); pygame.draw.circle(surf,(0,0,0),(cx,cy),max(4,cell//5),1)
                    if rid==s.ma_winner and s.ma_winner>=0:
                        for angle in range(0,360,45): rad=cell//3+int(3*math.sin(frame*0.3+angle)); px,py=cx+int(rad*math.cos(math.radians(angle))),cy+int(rad*math.sin(math.radians(angle))); pygame.draw.circle(surf,C["r0"],(px,py),3)
                else: tri(surf,col,cx,cy,max(8,int(cell*0.65)),str(rid),af,glow=(s.ma_phase=="execute"),frame=frame)
    if s.mode=="local_mp":
        for pid in range(NUM_R):
            player=s.mp_players[pid]; col=RCOLS[pid]
            for i,(tr,tc) in enumerate(player["trail"]):
                age_ratio=i/max(1,len(player["trail"])); alpha=int(30+50*age_ratio); ts=pygame.Surface((cell-6,cell-6),pygame.SRCALPHA); ts.fill((*col,alpha)); surf.blit(ts,(ox+tc*cell+3,oy+tr*cell+3))
        for pid in range(NUM_R):
            player=s.mp_players[pid]; col=RCOLS[pid]; cx,cy=ox+player["c"]*cell+cell//2,oy+player["r"]*cell+cell//2
            glow=0.2*math.sin(frame*0.3+pid*2) if not player["done"] else 0; tri_size=max(8,int(cell*0.7+glow*3))
            tri(surf,col,cx,cy,tri_size,str(pid+1),af,glow=(not player["done"]),frame=frame)
            if player["done"] and pid==s.mp_winner:
                for angle in range(0,360,72): rad=cell//2+int(4*math.sin(frame*0.4+angle)); px,py=cx+int(rad*math.cos(math.radians(angle))),cy-int(rad*math.sin(math.radians(angle)))+cell//4; pygame.draw.circle(surf,C["r0"],(px,py),4)
            if (player["r"],player["c"]) in s.mp_collisions: pygame.draw.circle(surf,C["paradox"],(cx,cy),cell//2+2,width=2)
    for (cr,cc) in s.mp_collisions:
        pulse=0.4*(0.5+0.5*math.sin(frame*0.4)); cf=pygame.Surface((cell,cell),pygame.SRCALPHA); pygame.draw.circle(cf,(*C["paradox"],int(180+pulse*40)),(cell//2,cell//2),cell//2-2); surf.blit(cf,(ox+cc*cell,oy+cr*cell))

HUD_H=52
def draw_hud(surf,s:GS,W,frame):
    drect_animated(surf,C["panel"],(0,0,W,HUD_H),r=0,frame=frame); pygame.draw.line(surf,C["border"],(0,HUD_H),(W,HUD_H))
    if s.mode=="local_mp":
        stats_w=(W-200)//NUM_R
        for pid in range(NUM_R):
            player=s.mp_players[pid]; col=RCOLS[pid]; x=12+pid*stats_w
            drect_animated(surf,C["panel2"],(x,8,stats_w-8,36),r=6,border=1,bcol=col,frame=frame)
            dtext(surf,f"P{pid+1}",F_SM,col,x+12,12); dtext(surf,f"Steps:{player['steps']}",F_SM,C["text"],x+12,26)
            if player["done"]:
                place="🏆 1st" if pid==s.mp_winner else (f"{s.mp_rankings.index(pid)+2}nd" if s.mp_rankings.index(pid)+2==2 else f"{s.mp_rankings.index(pid)+2}rd" if s.mp_rankings.index(pid)+2==3 else f"{s.mp_rankings.index(pid)+2}th")
                dtext(surf,place,F_SM,C["green"] if pid==s.mp_winner else C["text3"],x+stats_w-14,26,"topright")
    elif s.mode=="player":
        stats=[("STEPS",str(s.steps)),("WAITS",str(s.waits)),("TIME","t="+str(s.view_t)),("PAR",str(s.par))]; x=12
        for lbl,val in stats: drect_animated(surf,C["panel2"],(x,8,56,36),r=6,border=1,bcol=C["border"],frame=frame); dtext(surf,lbl,F_SM,C["text3"],x+28,12,"center"); dtext(surf,val,F_UI,C["text"],x+28,26,"center",shadow=True); x+=64
    else:
        PHASE_INFO={"scout":(C["r1"],"🔍 SCOUT","Mapping edges"),"gossip":(C["warn"],"📡 GOSSIP","Sharing maps"),"negotiate":(C["r2"],"🤝 NEGOTIATE","Planning paths"),"execute":(C["green"],"🏁 EXECUTE","Racing!"),"done":(C["green"],"✅ DONE","Complete"),"":(C["text3"],"⏸️ READY","Press A")}
        ph=s.ma_phase; col,name,desc=PHASE_INFO.get(ph,PHASE_INFO[""]); pulse=0.1*math.sin(frame*0.2) if ph=="execute" else 0
        badge_col=tuple(min(255,c+int(pulse*30)) for c in col[:3]) if pulse else col
        drect_animated(surf,C["panel2"],(8,6,150,40),r=8,border=1,bcol=badge_col,pulse=(ph=="execute"),frame=frame)
        dtext(surf,name,F_HEAD,badge_col,83,14,"center",shadow=True); dtext(surf,desc,F_SM,C["text3"],83,32,"center")
        if s.ma_winner>=0: wc=RCOLS[s.ma_winner]; drect_animated(surf,C["win_bg"],(165,8,170,36),r=8,border=1,bcol=wc,pulse=True,frame=frame); dtext(surf,f"🏆 R{s.ma_winner} WINS!",F_UI,wc,250,26,"center",shadow=True)
    px=W-s.T*46-8; dtext(surf,"TIME SLICE",F_SM,C["text3"],px-4,10,"topright")
    for t in range(s.T):
        on=(t==s.view_t)
        if on and s.view_transition<=0: pulse=0.2*math.sin(frame*0.25); bg_color=tuple(min(255,c+int(pulse*40)) for c in C["accent"][:3]); glow_size=int(3+pulse*4); text_pulse=True
        else: bg_color,glow_size,text_pulse=C["pill_off"],0,False
        if glow_size>0: gs=pygame.Surface((40+glow_size*2,22+glow_size*2),pygame.SRCALPHA); pygame.draw.rect(gs,(*C["accent"][:3],50),(0,0,40+glow_size*2,22+glow_size*2),border_radius=11+glow_size//2); surf.blit(gs,(px-glow_size,24-glow_size))
        drect_animated(surf,bg_color,(px,24,40,22),r=11,border=2,bcol=C["accent"] if on else C["border2"],pulse=on,frame=frame)
        alpha=255 if on else int(180+40*math.sin(frame*0.1+t)); dtext(surf,f"t={t}",F_SM,(*C["text"][:3],alpha) if on else C["text3"],px+20,35,"center",pulse=text_pulse,frame=frame); px+=46
    dtext(surf,f"{s.diff} {s.n}×{s.n} T={s.T}",F_SM,C["text3"],W//2,10,"center"); dtext(surf,f"Seed #{s.seed&0xFFFF:04X}",F_SM,C["text3"],W//2,26,"center")

BOT_H=28
def draw_statusbar(surf,s:GS,W,H,frame):
    y=H-BOT_H; drect_animated(surf,C["panel"],(0,y,W,BOT_H),r=0,frame=frame); pygame.draw.line(surf,C["border"],(0,y),(W,y))
    if s.msg and s.msg_timer>0: alpha=min(255,int(s.msg_timer/30*255)); dtext(surf,s.msg,F_SM,(*s.msg_col[:3],alpha),W//2,y+7,"center")
    else:
        parts={"player":["[↑↓←→/WASD] Move","[SPACE] Wait","[H] Hint","[R] Restart","[ESC] Menu"],"ai":["[A] Run AI","[R] Reset","[ESC] Menu"],"multi":["[A] Run Race","[R] Reset","[ESC] Menu"],"local_mp":["🎮 P1:WASD | P2:Arrows | P3:IJKL","[R] Restart","[ESC] Menu"]}.get(s.mode,["[A] Run","[R] Reset"])
        dtext(surf," · ".join(parts),F_SM,C["text3"],W//2,y+7,"center")

def draw_log_panel(surf,s:GS,x,y,w,frame):
    if not s.ma_log: return
    lines=s.ma_log[-7:]; ph=len(lines)*16+14
    drect_animated(surf,C["panel"],(x,y,w,ph),r=8,border=1,bcol=C["border"],frame=frame); dtext(surf,"📋 Event Log",F_SM,C["text3"],x+w//2,y+4,"center")
    for i,ln in enumerate(lines):
        col,pulse=(C["green"],frame%30<15) if "WINNER" in ln else (C["paradox"],frame%20<10) if "PARADOX" in ln else (C["text2"],False) if ln.startswith("Phase") else (C["text3"],False)
        dtext(surf,ln if len(ln)<=w//7 else ln[:w//7-3]+"...",F_SM,col,x+6,y+14+i*16,pulse=pulse,frame=frame)

def draw_hint(surf,s:GS,W,H,frame):
    if not s.show_hint or not s.hint_txt: return
    lines=s.hint_txt.split("\n"); pw=min(W-60,540); ph=len(lines)*20+60; px,py=(W-pw)//2,(H-ph)//2
    drect_animated(surf,(0,0,0),(0,0,W,H),a=140,frame=frame); drect_animated(surf,C["panel"],(px,py,pw,ph),r=12,border=2,bcol=C["accent"],pulse=True,frame=frame)
    dtext(surf,"💡 HINT",F_HEAD,C["accent"],px+pw//2,py+12,"center",pulse=True,frame=frame); pygame.draw.line(surf,C["border"],(px+12,py+34),(px+pw-12,py+34))
    for i,ln in enumerate(lines):
        fade=min(255,int((frame-i*5)/10*255)) if frame>i*5 else 0
        if fade>0: dtext(surf,ln,F_UI,(*C["text"][:3],fade),px+16,py+42+i*20)
    dtext(surf,"Press [H] to close",F_SM,C["text3"],px+pw//2,py+ph-20,"center",pulse=True,frame=frame)

def draw_win(surf,s:GS,W,H,frame):
    if not s.won: return
    drect_animated(surf,(0,0,0),(0,0,W,H),a=170,frame=frame)
    if s.particle_fx and frame%5==0 and len(s.particles)<150: spawn_particles(s.particles,random.randint(0,W),random.randint(0,H//2),random.choice([C["r0"],C["r1"],C["r2"],C["green"]]),count=3,spread=1.5,life=2.5)
    if s.particle_fx: s.particles=[p for p in s.particles if p.update(16)]; [p.draw(surf) for p in s.particles]
    pw,ph=(min(W-40,520),220 if s.mode in("player","local_mp") else 260); px,py=(W-pw)//2,(H-ph)//2
    drect_animated(surf,C["win_bg"],(px,py,pw,ph),r=16,border=2,bcol=C["win_border"],pulse=True,frame=frame)
    for i in range(ph-40):
        ratio=i/(ph-40); pulse=0.05*math.sin(frame*0.1+i*0.1)
        pygame.draw.line(surf,(int(12+(36+pulse*20)*ratio),int(48+(100+pulse*30)*ratio),int(26+(50+pulse*15)*ratio)),(px+20,py+40+i),(px+pw-20,py+40+i))
    if s.mode=="player":
        eff=round(s.par/max(s.steps,1)*100); grade="S" if eff>=100 else ("A" if eff>=85 else ("B" if eff>=70 else "C")); gcol={"S":(255,215,0),"A":C["green"],"B":C["warn"],"C":C["err"]}[grade]
        dtext(surf,"🎉 EXIT REACHED!",F_TITLE,C["win_border"],px+pw//2,py+18,"center",shadow=True,pulse=True,frame=frame); pygame.draw.line(surf,C["border"],(px+20,py+54),(px+pw-20,py+54))
        stat_data=[("STEPS",str(s.steps)),("WAITS",str(s.waits)),("OPTIMAL",str(s.par)),("EFF",f"{eff}%")]; bw=(pw-40)//4
        for i,(lbl,val) in enumerate(stat_data):
            bx=px+20+i*(bw+4); pulse=(frame//15+i)%4==0
            drect_animated(surf,C["panel2"],(bx,py+64,bw,52),r=8,border=1,bcol=C["border2"],pulse=pulse,frame=frame)
            dtext(surf,lbl,F_SM,C["text3"],bx+bw//2,py+70,"center"); dtext(surf,val,F_HEAD,C["text"],bx+bw//2,py+86,"center",shadow=True)
        drect_animated(surf,gcol,(px+pw//2-30,py+130,60,50),r=10,border=2,bcol=gcol,pulse=True,frame=frame)
        dtext(surf,grade,pygame.font.SysFont("segoeui",36,bold=True),(20,20,20),px+pw//2,py+155,"center"); dtext(surf,"GRADE",F_SM,C["text3"],px+pw//2,py+132,"center")
        dtext(surf,"[N] Next [R] Retry [ESC] Menu",F_UI,C["text3"],px+pw//2,py+196,"center",pulse=True,frame=frame)
    elif s.mode=="local_mp":
        winner=s.mp_winner; dtext(surf,"🏁 RACE COMPLETE!",F_TITLE,C["win_border"],px+pw//2,py+18,"center",shadow=True,pulse=True,frame=frame); pygame.draw.line(surf,C["border"],(px+20,py+54),(px+pw-20,py+54))
        if winner>=0: wc=RCOLS[winner]; drect_animated(surf,C["panel2"],(px+pw//2-100,py+64,200,55),r=10,border=2,bcol=wc,pulse=True,frame=frame); dtext(surf,f"🏆 {PLAYER_KEYS[winner]['name']} WINS!",F_HEAD,wc,px+pw//2,py+78,"center",shadow=True,pulse=True,frame=frame); dtext(surf,f"{RNAMES[winner]} Team",F_SM,C["text3"],px+pw//2,py+102,"center")
        dtext(surf,"📊 Rankings:",F_UI,C["text2"],px+20,py+135)
        for rank,pid in enumerate([s.mp_winner]+[p for p in range(NUM_R) if p!=s.mp_winner and p in s.mp_rankings]):
            if rank>=3: break
            player=s.mp_players[pid]; col=RCOLS[pid]; medal="🥇" if rank==0 else "🥈" if rank==1 else "🥉"
            dtext(surf,f"{medal} {rank+1}. {PLAYER_KEYS[pid]['name']}: {player['steps']} steps",F_SM,col if rank==0 else C["text2"],px+20,py+155+rank*18)
        dtext(surf,"[N] Next [R] Retry [ESC] Menu",F_UI,C["text3"],px+pw//2,py+ph-22,"center")
    else:
        w=s.ma_winner; title="🏁 RACE OVER!" if w>=0 else "✅ RACE COMPLETE"; dtext(surf,title,F_TITLE,C["win_border"],px+pw//2,py+18,"center",shadow=True,pulse=True,frame=frame); pygame.draw.line(surf,C["border"],(px+20,py+54),(px+pw-20,py+54))
        if w>=0: wc=RCOLS[w]; drect_animated(surf,C["panel2"],(px+pw//2-110,py+64,220,60),r=10,border=2,bcol=wc,pulse=True,frame=frame); pygame.draw.circle(surf,wc,(px+pw//2-70,py+94),18); dtext(surf,str(w),F_HEAD,(20,20,20),px+pw//2-70,py+94,"center"); dtext(surf,f"🤖 ROBOT {w} WINS!",F_HEAD,wc,px+pw//2+10,py+80,"center",shadow=True,pulse=True,frame=frame); dtext(surf,RNAMES[w]+" team",F_SM,C["text3"],px+pw//2+10,py+104,"center")
        for rid in range(NUM_R):
            ry=py+140+rid*26; col=RCOLS[rid]; pygame.draw.circle(surf,col,(px+60,ry+10),8)
            status=("🏆 WINNER!" if rid==w else ("✓ Finished" if s.ma_done[rid] else "✗ DNF")); scol=C["green"] if rid==w else C["text2"]
            plen=len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0
            dtext(surf,f"R{rid} {RNAMES[rid]}:",F_UI,col,px+80,ry+3); dtext(surf,f"{status} · {plen} steps",F_SM,scol,px+210,ry+5,pulse=(rid==w),frame=frame)
        dtext(surf,"[N] Next [R] Retry [ESC] Menu",F_UI,C["text3"],px+pw//2,py+ph-22,"center")

def draw_settings_panel(surf,s:GS,W,H,frame):
    if not s.show_settings:
        drect_animated(surf,C["panel2"],(W-40,HUD_H+8,32,32),r=6,border=1,bcol=C["border"],hover=True,frame=frame); dtext(surf,"⚙️",F_UI,C["text3"],W-24,HUD_H+18,"center"); return
    pw,ph,px,py=340,260,(W-340)//2,(H-260)//2-20
    if frame<25: py+=int(30*(1-frame/25))
    drect_animated(surf,C["panel"],(px,py,pw,ph),r=12,border=2,bcol=C["accent"],pulse=True,frame=frame); dtext(surf,"⚙️ Settings",F_HEAD,C["accent"],px+pw//2,py+14,"center")
    options=[("Show Hints",s.show_hint,"h","Toggle hint overlay"),("Particle FX",s.particle_fx,"p","Celebration particles"),("Show FPS",s.show_fps,"f","Display frame rate"),("Debug Mode",s.debug_mode,"d","Extra diagnostics")]
    for i,(label,enabled,key,desc) in enumerate(options):
        y_pos=py+45+i*38; dtext(surf,f"{label} [{key.upper()}]",F_SM,C["text2"],px+18,y_pos); dtext(surf,desc,F_SM,C["text3"],px+18,y_pos+14)
        switch_x=px+pw-70; drect_animated(surf,C["pill_off"] if not enabled else C["green"],(switch_x,y_pos+4,50,22),r=11,frame=frame)
        circle_x=switch_x+11+(28 if enabled else 0); pygame.draw.circle(surf,(255,255,255),(int(circle_x),y_pos+15),9)
    dtext(surf,"Press [S] or click outside to close",F_SM,C["text3"],px+pw//2,py+ph-22,"center",pulse=True,frame=frame)

def draw_title(surf,W,H,sel_diff,sel_mode,hover,frame):
    draw_parallax_bg(surf,W,H,frame)
    rng2=random.Random(42)
    for i in range(24):
        px2,py2=int(rng2.random()*W),int(rng2.random()*H*0.55); r2=rng2.randint(1,3)
        alpha=int(70+50*math.sin(frame*0.03+i+rng2.random()*6)); size=r2+int(1.5*math.sin(frame*0.1+i*0.5))
        ss=pygame.Surface((size*2,size*2),pygame.SRCALPHA); pygame.draw.circle(ss,(*C["accent"],alpha),(size,size),size); surf.blit(ss,(px2-size,py2-size))
    dtext(surf,"TEMPORAL",F_TITLE,C["accent"],W//2,28,"center",shadow=True,pulse=True,frame=frame); dtext(surf,"MAZE",F_TITLE,C["text"],W//2,64,"center",shadow=True,pulse=True,frame=frame)
    dtext(surf,"✨ Edge-Based + Multiplayer ✨",F_UI,C["text3"],W//2,102,"center",pulse=True,frame=frame); pygame.draw.line(surf,C["border"],(W//2-160,118),(W//2+160,118))
    tw_cards=[(C["r0"],"🧱 Edge Walls","Walls are lines between cells\nNot whole blocks - more precise!"),(C["cell_temp"],"⏱️ Time Edges","Orange dashed edges block\nonly at specific time slices"),(C["accent"],"🔄 Wait=Time Travel","Press WAIT to advance time\nand open blocked edges"),(C["r2"],"👥 Local Multiplayer","3 players on one keyboard!\nRace to the exit first")]
    cw2,ch2=int((W-60)//4),115
    for i,(icol,title2,body) in enumerate(tw_cards):
        cx2,cy2=20+i*(cw2+6),130; on=(hover==f"card{i}")
        bg=gradient_surf(cw2,ch2,C["panel2"],C["panel"]) if on else C["panel"]; bc=C["accent"] if on else C["border"]
        drect_animated(surf,bg if isinstance(bg,tuple) and len(bg)==2 else C["panel2"],(cx2,cy2,cw2,ch2),r=10,border=2 if on else 1,bcol=bc,hover=on,frame=frame)
        pygame.draw.line(surf,icol,(cx2,cy2),(cx2+cw2+int(5*math.sin(frame*0.1+i)),cy2),width=5); dtext(surf,title2,F_UI,C["text"],cx2+cw2//2,cy2+14,"center",shadow=on,pulse=on,frame=frame)
        pygame.draw.line(surf,C["border"],(cx2+10,cy2+32),(cx2+cw2-10,cy2+32))
        for j,line in enumerate(body.split("\n")): fade=min(255,int((frame-j*3)/8*255)) if frame>j*3 else 100; dtext(surf,line,F_SM,(*C["text3"][:3],fade),cx2+cw2//2,cy2+40+j*18,"center")
    diffs=list(DIFFS.keys()); dtext(surf,"SELECT DIFFICULTY",F_UI,C["text3"],W//2,255,"center"); pygame.draw.line(surf,C["border"],(W//2-100,271),(W//2+100,271))
    dcw,dch=int((W-40)//4),78
    for i,d in enumerate(diffs):
        dcx,dcy,on=20+i*(dcw+5),277,(d==sel_diff)
        bg=gradient_surf(dcw,dch,C["accent2"],C["panel"]) if on else C["panel"]; bc=C["accent"] if on else C["border"]
        drect_animated(surf,bg if isinstance(bg,tuple) and len(bg)==2 else C["panel"],(dcx,dcy,dcw,dch),r=10,border=2 if on else 1,bcol=bc,hover=on,pulse=on,frame=frame)
        info=DIFFS[d]; dtext(surf,d,F_HEAD,C["text"] if on else C["text2"],dcx+dcw//2,dcy+8,"center",shadow=on,pulse=on,frame=frame)
        dtext(surf,f"{info['n']}×{info['n']}",F_UI,C["accent"] if on else C["text3"],dcx+dcw//2,dcy+30,"center")
        dtext(surf,f"{info['T']} time slices",F_SM,C["text3"],dcx+dcw//2,dcy+48,"center"); dtext(surf,f"{int(info['tw']*100)}% temporal edges",F_SM,C["text3"],dcx+dcw//2,dcy+63,"center")
    dtext(surf,"SELECT MODE",F_UI,C["text3"],W//2,362,"center"); pygame.draw.line(surf,C["border"],(W//2-100,378),(W//2+100,378))
    modes=[("player","🎮 PLAY YOURSELF","Control agent with keyboard","WASD/Arrows + Space"),("ai","🤖 WATCH AI","A* solver animates solution","Press A to run"),("multi","🏁 MULTI-AGENT","3 AI robots Scout→Race","Press A to start"),("local_mp","👥 LOCAL MULTIPLAYER","🎮 3 players on one keyboard!","WASD | Arrows | IJKL")]
    mw,mh=int((W-40)//4),98
    for i,(m,mname,mdesc,mhint) in enumerate(modes):
        mcx,mcy,on=20+i*(mw+5),384,(m==sel_mode)
        bg=gradient_surf(mw,mh,C["accent2"],C["panel"]) if on else C["panel"]; bc=C["accent"] if on else C["border"]
        drect_animated(surf,bg if isinstance(bg,tuple) and len(bg)==2 else C["panel"],(mcx,mcy,mw,mh),r=10,border=2 if on else 1,bcol=bc,hover=on,pulse=on,frame=frame)
        dtext(surf,mname,F_HEAD,C["text"] if on else C["text2"],mcx+mw//2,mcy+8,"center",shadow=on,pulse=on,frame=frame)
        for j,line in enumerate(mdesc.split("\n")): dtext(surf,line,F_SM,C["text3"],mcx+mw//2,mcy+30+j*17,"center")
        dtext(surf,mhint,F_SM,C["accent"] if on else C["text3"],mcx+mw//2,mcy+mh-20,"center",pulse=on,frame=frame)
    bw2,bh2,bx2,by2,on2=200,50,(W-200)//2,495,(hover=="start")
    drect_animated(surf,(C["grad_start"],C["grad_end"]),(bx2,by2,bw2,bh2),r=12,border=2,bcol=C["accent"],hover=on2,pulse=on2,glow_color=C["glow_player"],frame=frame)
    dtext(surf,"🚀 START GAME",F_HEAD,(255,255,255),bx2+bw2//2,by2+bh2//2,"center",shadow=True,pulse=on2,frame=frame); dtext(surf,"or press Enter",F_SM,C["text3"],W//2,by2+bh2+10,"center")
    shortcuts=[("← →","Select difficulty"),("Tab","Cycle mode"),("Enter","Start game")]; sy=560
    for k2,v2 in shortcuts:
        kw=F_SM.size(f"[{k2}]")[0]+14; kx=W//2-190
        drect_animated(surf,C["panel2"],(kx,sy,kw,20),r=5,border=1,bcol=C["border2"],frame=frame)
        dtext(surf,f"[{k2}]",F_SM,C["accent"],kx+kw//2,sy+10,"center"); dtext(surf,v2,F_SM,C["text3"],kx+kw+12,sy+10,"midleft"); sy+=24
    hit_rects={}; [hit_rects.update({f"diff_{d}":(20+i*(dcw+5),277,dcw,dch)}) for i,d in enumerate(diffs)]; [hit_rects.update({f"mode_{m}":(20+i*(mw+5),384,mw,mh)}) for i,(m,*_) in enumerate(modes)]; hit_rects["start"]=(bx2,by2,bw2,bh2); return hit_rects

# ── AI Generators ─────────────────────────────────────────────────────────────
def gen_single_edge(s:GS,W,H):
    n,T=s.n,s.T; walls,tm=s.walls,s.temporal
    for t in range(T):
        for r in range(n):
            for c in range(n):
                s.scout_pos=[(a,b,d,max(0,e-0.07)) for a,b,d,e in s.scout_pos if e>0.02]; s.scout_pos.append((r,c,t,1.0)); s.view_t=t; yield "scout"
    s.scout_pos=[]; path=astar_edge(walls,tm,n,T)
    if not path: s.won=True; return
    for p in path: s.path_set.add(p[0]*n+p[1])
    tw2=sum(1 for i in range(1,len(path)) if path[i][:2]==path[i-1][:2]); s.msg=f"✨ AI: {len(path)} steps, {tw2} waits"; s.msg_col=C["green"]; s.msg_timer=300
    for r,c,t in path: s.solver_pos=(r,c); s.view_t=t; yield "solve"
    s.won=True; s.solver_pos=(n-1,n-1)
    if s.particle_fx: spawn_particles(s.particles,W//2,H//2,C["green"],count=30,spread=3.0,life=3.0)

def gen_multi_edge(s:GS,W,H):
    n,T=s.n,s.T; walls,tm=s.walls,s.temporal; s.ma_phase="scout"; s.ma_log=["✨ Phase 1 — Scout: mapping edges..."]; slices_per=max(1,T//NUM_R); scout_maps={rid:set() for rid in range(NUM_R)}
    for t in range(T):
        owner=min(t//slices_per,NUM_R-1)
        for r in range(n):
            for c in range(n):
                s.scout_pos=[(a,b,d,max(0,e-0.06)) for a,b,d,e in s.scout_pos if e>0.02]; s.scout_pos.append((r,c,t,1.0))
                for direction in DIRS:
                    if not edge_blocked(walls,tm,n,T,r,c,direction,t): scout_maps[owner].add((r,c,direction,t))
                s.view_t=t; yield "scout"
    s.scout_pos=[]; s.ma_log.append(f"🔍 Scouts mapped {sum(len(v) for v in scout_maps.values())} open edges"); yield "scout_done"
    s.ma_phase="gossip"; s.ma_log.append("📡 Phase 2 — Gossip: sharing maps..."); all_open=set(); [all_open.update(v) for v in scout_maps.values()]; [scout_maps.update({rid:all_open}) for rid in range(NUM_R)]; s.ma_log.append(f"✅ Gossip: {len(all_open)} edges known"); yield "gossip"
    s.ma_phase="negotiate"; s.ma_log.append("🤝 Phase 3 — Negotiate: planning paths..."); paths,reserved=negotiate_edge(walls,tm,n,T); s.ma_paths,s.ma_reserved=paths,reserved
    for rid,path in enumerate(paths):
        if path: wt=sum(1 for i in range(1,len(path)) if path[i][:2]==path[i-1][:2]); s.ma_log.append(f"  ✅ R{rid}: {len(path)} steps, {wt} waits")
        else: s.ma_log.append(f"  ⚠️ R{rid}: no path"); yield "negotiate"
    s.ma_phase="execute"; s.ma_log.append("🏁 Phase 4 — Execute: racing!"); max_steps=max((len(p) for p in paths if p),default=0)
    for step in range(max_steps):
        s.ma_step=step; s.ma_paradox=[]; occupied={}
        for rid in range(NUM_R):
            if s.ma_done[rid]: continue
            path=paths[rid]
            if not path or step>=len(path): s.ma_done[rid]=True; continue
            r,c,t=path[step]; s.ma_pos[rid]=(r,c); s.view_t=t; s.ma_trails[rid].append((r,c))
            if len(s.ma_trails[rid])>22: s.ma_trails[rid].pop(0)
            if (r,c) in occupied: s.ma_paradox.append((r,c)); s.ma_log.append(f"  ⚡ PARADOX! R{rid}&R{occupied[(r,c)]} at ({r},{c})"); s.shake_timer=10
            occupied[(r,c)]=rid
            if r==n-1 and c==n-1 and not s.ma_done[rid]:
                s.ma_done[rid]=True
                if s.ma_winner<0: s.ma_winner=rid; s.ma_log.append(f"  🏆 R{rid} WINS!"); s.shake_timer=15
                if s.particle_fx: spawn_particles(s.particles,W//2+random.randint(-100,100),H//2+random.randint(-50,50),RCOLS[rid],count=20,spread=2.5,life=3.0)
        if all(s.ma_done): break; yield "execute"
    [s.ma_done.update({rid:True}) for rid in range(NUM_R) if not s.ma_done[rid]]; s.ma_phase="done"; s.ma_mode=False
    if s.ma_winner<0 and any(s.ma_done): s.ma_winner=next(i for i,d in enumerate(s.ma_done) if d)
    s.won=True; s.ma_log.append(f"🏁 Complete · Winner:R{s.ma_winner}"); yield "done"

# ── Movement Functions ────────────────────────────────────────────────────────
def pmove_edge(s,dr,dc,smsg_func):
    if s.won or s.mode!="player": return
    nr,nc,nt=s.pr+dr,s.pc+dc,(s.pt+1)%s.T
    if not can_move(s.walls,s.temporal,s.n,s.T,s.pr,s.pc,dr,dc,s.pt):
        smsg_func("⚠️ Cannot wait!" if dr==dc==0 else "🚫 Edge blocked!",C["warn"] if dr==dc==0 else C["err"]); return
    if dr==dc==0: s.waits+=1
    s.pr,s.pc,s.pt=nr,nc,nt; s.steps+=1; s.view_t=nt; s.trail.append((nr,nc))
    if len(s.trail)>20: s.trail.pop(0); smsg_func("")
    if nr==s.n-1 and nc==s.n-1:
        s.won=True
        if s.particle_fx: spawn_particles(s.particles,W//2,H//2,C["green"],count=40,spread=3.0,life=3.0)
        s.shake_timer=15

def mp_move_edge(s,pid,dr,dc,smsg_func,W,H):
    if s.won or s.mode!="local_mp": return False
    player=s.mp_players[pid]
    if player["done"]: return False
    nr,nc,nt=player["r"]+dr,player["c"]+dc,(player["t"]+1)%s.n
    if not can_move(s.walls,s.temporal,s.n,s.T,player["r"],player["c"],dr,dc,player["t"]):
        smsg_func(f"⚠️ {PLAYER_KEYS[pid]['name']}: Wait blocked!" if dr==dc==0 else f"🚫 {PLAYER_KEYS[pid]['name']}: Edge blocked!",C["warn"] if dr==dc==0 else C["err"]); return False
    if dr==dc==0: player["waits"]+=1
    player["r"],player["c"],player["t"]=nr,nc,nt; player["steps"]+=1; s.view_t=nt; player["trail"].append((nr,nc))
    if len(player["trail"])>20: player["trail"].pop(0)
    if nr==s.n-1 and nc==s.n-1 and not player["done"]:
        player["done"]=True
        if s.mp_winner<0: s.mp_winner=pid; s.won=True; smsg_func(f"🏆 {PLAYER_KEYS[pid]['name']} WINS!",C["green"],400)
        if s.particle_fx: spawn_particles(s.particles,W//2,H//2,RCOLS[pid],count=50,spread=3.5,life=4.0); s.shake_timer=20
        elif pid not in s.mp_rankings: s.mp_rankings.append(pid); smsg_func(f"✓ {PLAYER_KEYS[pid]['name']} finished!",C["text2"],200)
    for other_pid in range(NUM_R):
        if other_pid!=pid and not s.mp_players[other_pid]["done"] and (player["r"],player["c"])==(s.mp_players[other_pid]["r"],s.mp_players[other_pid]["c"]) and (player["r"],player["c"]) not in s.mp_collisions:
            s.mp_collisions.append((player["r"],player["c"])); smsg_func(f"⚡ Collision! P{pid+1}&P{other_pid+1}",C["paradox"],150); s.shake_timer=8
    return True

# ── Main Function ─────────────────────────────────────────────────────────────
def main():
    global F_TITLE,F_HEAD,F_UI,F_SM,F_MONO,W,H
    pygame.init(); screen=pygame.display.set_mode((1024,768),pygame.RESIZABLE); pygame.display.set_caption("✨ Temporal Maze — Edge-Based ✨"); clock=pygame.time.Clock()
    F_TITLE,F_HEAD,F_UI,F_SM,F_MONO=pygame.font.SysFont("segoeui",32,bold=True),pygame.font.SysFont("segoeui",16),pygame.font.SysFont("segoeui",13),pygame.font.SysFont("segoeui",11),pygame.font.SysFont("monospace",11,bold=True)
    SIDEBAR_W,SCOUT_MS,SOLVE_MS,EXEC_MS=190,7,85,115; sel_diff,sel_mode,cur_scr="Hard","player","title"
    state,ai_gen,ai_accum=GS(),None,0.0; frame,hover_id,title_hit_rects=0,"",{}; shake_offset,shake_timer=(0,0),0
    
    def start(): nonlocal cur_scr,ai_gen; cfg=DIFFS[sel_diff]; state.n,state.T,state.tw,state.diff,state.mode=cfg["n"],cfg["T"],cfg["tw"],sel_diff,sel_mode; new_level(state); cur_scr,ai_gen="game",None
    def smsg(txt,col=None,dur=220): state.msg,state.msg_col,state.msg_timer=txt,col or C["text3"],dur
    def pmove(dr,dc): pmove_edge(state,dr,dc,smsg)
    def mp_move(pid,dr,dc): return mp_move_edge(state,pid,dr,dc,smsg,W,H)
    def do_hint():
        path=astar_edge(state.walls,state.temporal,state.n,state.T)
        if not path: state.hint_txt="⚠️ No solution. Try restarting."; state.show_hint=True; return
        twpts=[path[i][2] for i in range(1,len(path)) if path[i][:2]==path[i-1][:2]]
        state.hint_txt=f"✨ Optimal: {len(path)} steps, {len(twpts)} waits.\nWait at: t={',t='.join(map(str,twpts))}\n💡 Press WAIT to advance time!" if twpts else f"✨ Optimal: {len(path)} steps — no waits!\n💡 Navigate to exit (E)."
        state.show_hint=not state.show_hint
    def launch_single(): nonlocal ai_gen; state.ai_running=True if not state.ai_running else None; ai_gen=gen_single_edge(state,W,H) if not state.ai_running else None
    def launch_multi(): nonlocal ai_gen; state.ai_running,state.ma_mode=True,True; state.ma_pos,state.ma_done,state.ma_winner=list(robot_starts(state.n)),[False]*NUM_R,-1; state.ma_trails,state.ma_paradox,state.ma_log=[[] for _ in range(NUM_R)],[],[]; ai_gen=gen_multi_edge(state,W,H)
    def reset_ai(): nonlocal ai_gen; state.ai_running,state.ma_mode,ai_gen=False,False,None; state.scout_pos,state.solver_pos,state.path_set=[],None,set(); state.ma_phase,state.ma_pos="",list(robot_starts(state.n)); state.ma_done,state.ma_winner=[False]*NUM_R,-1; state.ma_trails,state.ma_paradox,state.ma_log=[[] for _ in range(NUM_R)],[],[]; state.won=False
    
    state._h_prev,state._p_prev,state._f_prev,state._d_prev=state.show_hint,state.particle_fx,state.show_fps,state.debug_mode
    
    while True:
        W,H=screen.get_size(); dt_ms=clock.tick(60); frame+=1; state.anim_tick=frame; mx_g,my_g=pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if cur_scr=="title":
                diffs=list(DIFFS.keys())
                if ev.type==pygame.KEYDOWN:
                    if ev.key==pygame.K_RETURN: start()
                    if ev.key==pygame.K_TAB: ml=["player","ai","multi","local_mp"]; sel_mode=ml[(ml.index(sel_mode)+1)%len(ml)]
                    if ev.key==pygame.K_LEFT: idx=diffs.index(sel_diff); sel_diff=diffs[max(0,idx-1)]
                    if ev.key==pygame.K_RIGHT: idx=diffs.index(sel_diff); sel_diff=diffs[min(len(diffs)-1,idx+1)]
                    if ev.key==pygame.K_q: pygame.quit(); sys.exit()
                    if ev.key==pygame.K_RALT: state.show_settings=not state.show_settings
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    for hid,(hx,hy,hw,hh2) in title_hit_rects.items():
                        if hx<=mx_g<=hx+hw and hy<=my_g<=hy+hh2:
                            if hid=="start": start()
                            elif hid.startswith("diff_"): sel_diff=hid[5:]
                            elif hid.startswith("mode_"): sel_mode=hid[5:]
            else:
                if ev.type==pygame.KEYDOWN:
                    k=ev.key
                    if k==pygame.K_q: pygame.quit(); sys.exit()
                    if k==pygame.K_ESCAPE: cur_scr="title"
                    if k==pygame.K_r: new_level(state) if state.mode in("player","local_mp") else reset_ai(); ai_gen=None if state.mode in("player","local_mp") else ai_gen
                    if k==pygame.K_n and state.won: new_level(state); ai_gen=None; reset_ai()
                    if k==pygame.K_RALT: state.show_settings=not state.show_settings
                    if k==pygame.K_p: state.particle_fx=not state.particle_fx; state._p_prev=state.particle_fx
                    if k==pygame.K_f: state.show_fps=not state.show_fps; state._f_prev=state.show_fps
                    if k==pygame.K_d: state.debug_mode=not state.debug_mode; state._d_prev=state.debug_mode
                    if state.mode=="local_mp" and not state.won:
                        for pid in range(NUM_R):
                            keys=PLAYER_KEYS[pid]; player=state.mp_players[pid]
                            if player["done"]: continue
                            if ev.key==keys["up"]: mp_move(pid,-1,0)
                            elif ev.key==keys["down"]: mp_move(pid,1,0)
                            elif ev.key==keys["left"]: mp_move(pid,0,-1)
                            elif ev.key==keys["right"]: mp_move(pid,0,1)
                            elif ev.key==keys["wait"]: mp_move(pid,0,0)
                    elif state.mode=="player":
                        if k in(pygame.K_UP,pygame.K_w): pmove(-1,0)
                        if k in(pygame.K_DOWN,pygame.K_s): pmove(1,0)
                        if k in(pygame.K_LEFT,pygame.K_a): pmove(0,-1)
                        if k in(pygame.K_RIGHT,pygame.K_d): pmove(0,1)
                        if k==pygame.K_SPACE: pmove(0,0)
                        if k==pygame.K_h: do_hint()
                        for ti in range(state.T):
                            if k==getattr(pygame,f"K_{ti}",None) and state.view_t!=ti: state.target_view_t,state.view_transition=ti,1.0
                    elif state.mode=="ai" and k==pygame.K_a: launch_single()
                    elif state.mode=="multi" and k in(pygame.K_a,pygame.K_m): launch_multi()
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    pill_x=W-state.T*46-8
                    for ti in range(state.T):
                        if pill_x+ti*46<=mx_g<=pill_x+ti*46+40 and 24<=my_g<=46 and state.view_t!=ti: state.target_view_t,state.view_transition=ti,1.0
                    if state.show_settings:
                        pw,ph,px,py=340,260,(W-340)//2,(H-260)//2-20
                        if not(px<=mx_g<=px+pw and py<=my_g<=py+ph): state.show_settings=False
                        else:
                            for i,(label,enabled,key,_) in enumerate([("Show Hints",state.show_hint,"h",""),("Particle FX",state.particle_fx,"p",""),("Show FPS",state.show_fps,"f",""),("Debug Mode",state.debug_mode,"d","")]):
                                y_pos=py+45+i*38; switch_x=px+pw-70-180
                                if switch_x<=mx_g<=switch_x+50 and y_pos+4<=my_g<=y_pos+26:
                                    if key=="h": state.show_hint=not state.show_hint; state._h_prev=state.show_hint
                                    elif key=="p": state.particle_fx=not state.particle_fx; state._p_prev=state.particle_fx
                                    elif key=="f": state.show_fps=not state.show_fps; state._f_prev=state.show_fps
                                    elif key=="d": state.debug_mode=not state.debug_mode; state._d_prev=state.debug_mode
                    elif state.mode=="player" and not state.won:
                        maze_x0,mah2,maze_w=SIDEBAR_W+4,H-HUD_H-BOT_H,W-SIDEBAR_W-8; cell2=max(18,min(mah2//state.n,maze_w//state.n))
                        ox2,oy2=maze_x0+(maze_w-cell2*state.n)//2,HUD_H+(mah2-cell2*state.n)//2; cc2,cr2=(mx_g-ox2)//cell2,(my_g-oy2)//cell2
                        if 0<=cr2<state.n and 0<=cc2<state.n:
                            dr3,dc3=cr2-state.pr,cc2-state.pc
                            if abs(dr3)+abs(dc3)==1: pmove(int(math.copysign(1,dr3)) if dr3 else 0,int(math.copysign(1,dc3)) if dc3 else 0)
                            elif dr3==dc3==0: pmove(0,0)
        if cur_scr=="title":
            hover_id=""; [hover_id:=hid for hid,(hx,hy,hw,hh2) in title_hit_rects.items() if hx<=mx_g<=hx+hw and hy<=my_g<=hy+hh2]
        if cur_scr=="game" and state.ai_running and ai_gen:
            ph=state.ma_phase; tick=SCOUT_MS if ph in("","scout","gossip","negotiate") else (EXEC_MS if ph=="execute" else SOLVE_MS); ai_accum+=dt_ms
            if ai_accum>=tick: ai_accum=0
            try: next(ai_gen)
            except StopIteration: state.ai_running=False; ai_gen=None
        if state.msg_timer>0: state.msg_timer-=1
        if state.msg_timer==0 and state.msg and not state.won: state.msg=""
        if state.view_transition>0:
            state.view_transition-=0.18
            if state.view_transition<=0: state.view_transition,state.view_t=0,state.target_view_t if state.target_view_t is not None else state.view_t
            elif state.target_view_t is not None: state.view_t=int(state.view_t+(state.target_view_t-state.view_t)*(1-state.view_transition)**2*(3-2*(1-state.view_transition)))
        if state.shake_timer>0: shake_offset,state.shake_timer=apply_screen_shake(shake_offset,4,state.shake_timer)
        else: shake_offset=(0,0)
        state._h_prev,state._p_prev,state._f_prev,state._d_prev=state.show_hint,state.particle_fx,state.show_fps,state.debug_mode
        render_surf=pygame.Surface((W,H))
        if cur_scr=="title": title_hit_rects=draw_title(render_surf,W,H,sel_diff,sel_mode,hover_id,frame); draw_settings_panel(render_surf,state,W,H,frame)
        else:
            render_surf.fill(C["bg"]); mah,maze_x0,maze_w=H-HUD_H-BOT_H,SIDEBAR_W+4,W-SIDEBAR_W-8; cell=max(18,min(mah//state.n,maze_w//state.n)); ox,oy=maze_x0+(maze_w-cell*state.n)//2,HUD_H+(mah-cell*state.n)//2
            drect_animated(render_surf,C["panel"],(0,HUD_H,SIDEBAR_W,mah),r=0,border=1,bcol=C["border"],frame=frame); draw_legend(render_surf,4,HUD_H+6,SIDEBAR_W-8,frame)
            leg_h,ctrl_y=len(LEGEND_ITEMS)*22+18,HUD_H+len(LEGEND_ITEMS)*22+24; draw_controls_panel(render_surf,4,ctrl_y,SIDEBAR_W-8,state.mode,frame)
            ctrl_rows,ctrl_h={"player":6,"ai":4,"multi":4,"local_mp":5},{"player":6,"ai":4,"multi":4,"local_mp":5}.get(state.mode,4)*20+20
            if state.mode=="multi" and state.ma_phase: draw_robot_panel(render_surf,4,ctrl_y+ctrl_h+8,SIDEBAR_W-8,state,frame)
            elif state.mode=="local_mp": draw_mp_player_panel(render_surf,4,ctrl_y+ctrl_h+8,SIDEBAR_W-8,state,frame)
            draw_hud(render_surf,state,W,frame); draw_maze_edge(render_surf,state,ox,oy,cell,frame); draw_statusbar(render_surf,state,W,H,frame)
            if state.ma_log and H-(oy+cell*state.n+4)-BOT_H>40: draw_log_panel(render_surf,state,maze_x0,oy+cell*state.n+4,W-SIDEBAR_W-10,frame)
            if not state.ai_running and not state.won:
                prompt={"ai":"Press [A] to run AI ✨","multi":"Press [A] to start race 🏁","local_mp":"🎮 3 Players Ready!"}.get(state.mode,"")
                if prompt: pw2,px2,py2=F_HEAD.size(prompt)[0]+28,ox+(cell*state.n-F_HEAD.size(prompt)[0]-28)//2,oy+cell*state.n//2-18; drect_animated(render_surf,C["panel2"],(px2,py2,pw2,36),r=8,border=1,bcol=C["accent"],pulse=True,frame=frame); dtext(render_surf,prompt,F_HEAD,C["accent"],px2+pw2//2,py2+18,"center",pulse=True,frame=frame)
            draw_hint(render_surf,state,W,H,frame); draw_win(render_surf,state,W,H,frame); draw_settings_panel(render_surf,state,W,H,frame)
            if state.show_fps: dtext(render_surf,f"FPS:{int(clock.get_fps())}",F_SM,C["text3"],10,H-20)
            if state.debug_mode: [dtext(render_surf,info,F_SM,C["text3"],10,20+i*16) for i,info in enumerate([f"View:{state.view_t}/{state.T}",f"Trans:{state.view_transition:.2f}",f"Particles:{len(state.particles)}"])]
        screen.blit(render_surf,shake_offset); pygame.display.flip()

if __name__=="__main__": main()