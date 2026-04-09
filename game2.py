"""
Temporal Maze — Multi-Agent Negotiation Edition  (UI v3 ✨ Enhanced)
=========================================================
pip install pygame
python temporal_maze.py

✨ ENHANCEMENTS:
• Animated gradient buttons with hover effects
• Particle system for celebrations & feedback
• Smooth time-slice transitions with pulse animation
• Parallax background grid
• Enhanced win screen with confetti
• Robot trail fade effects
• Accessibility patterns for colorblind support
• Settings panel (press S)
• Screen shake on events
• FPS counter (F3 toggle)
"""

import pygame, sys, math, random, heapq, textwrap
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List

# ── Enhanced palette with gradients, glows & accessibility ────────────────────
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
    # ✨ NEW: Gradients & effects
    grad_start  =( 80, 160, 240),
    grad_end    =( 40, 100, 200),
    glow_player =(140, 220, 255),
    glow_robot0 =(255, 220, 100),
    glow_robot1 =(100, 230, 255),
    glow_robot2 =(220, 140, 255),
    grid_line   =( 30,  40,  70),
    pulse_on    =(100, 200, 255),
    pulse_off   =( 50, 100, 150),
    # Accessibility patterns
    pattern_diag=(255, 255, 255, 25),
    pattern_dot =(255, 255, 255, 35),
)
RCOLS   = [C["r0"], C["r1"], C["r2"]]
RNAMES  = ["Gold", "Cyan", "Violet"]
NUM_R   = 3

DIFFS = {
    "Medium": dict(n=9,  T=3, tw=0.18),
    "Hard":   dict(n=13, T=4, tw=0.28),
    "Expert": dict(n=17, T=5, tw=0.34),
    "Brutal": dict(n=21, T=6, tw=0.40),
}

# fonts — set in main()
F_TITLE = F_HEAD = F_UI = F_SM = F_MONO = None

# ── Particle System for Visual Polish ─────────────────────────────────────────
@dataclass
class Particle:
    x: float; y: float; vx: float; vy: float
    life: float; max_life: float
    color: tuple; size: float; decay: float = 0.98
    
    def update(self, dt: float) -> bool:
        """Update particle, return False if dead"""
        self.x += self.vx * dt * 0.06
        self.y += self.vy * dt * 0.06
        self.vy += 0.02  # subtle gravity
        self.size *= self.decay
        self.life -= dt * 0.016
        return self.life > 0 and self.size > 0.5
    
    def draw(self, surf: pygame.Surface):
        alpha = int(255 * (self.life / self.max_life))
        if alpha < 10: return
        s = pygame.Surface((int(self.size*2)+1, int(self.size*2)+1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), 
                          (int(self.size)+1, int(self.size)+1), int(self.size)+1)
        surf.blit(s, (int(self.x - self.size), int(self.y - self.size)))


def spawn_particles(particles: list, x, y, color, count=12, spread=2.0, life=1.5):
    """Spawn burst of particles at position"""
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(0.5, 2.5)
        particles.append(Particle(
            x=x, y=y,
            vx=math.cos(angle) * speed * spread,
            vy=math.sin(angle) * speed * spread - 1,
            life=life, max_life=life,
            color=color,
            size=random.uniform(2, 5)
        ))


# ── Enhanced Drawing Helpers ──────────────────────────────────────────────────
def gradient_surf(w, h, start_color, end_color, vertical=True):
    """Create a smooth gradient surface"""
    surf = pygame.Surface((w, h))
    for i in range(h if vertical else w):
        ratio = i / max(1, (h if vertical else w) - 1)
        color = tuple(int(start_color[j] + (end_color[j] - start_color[j]) * ratio) 
                     for j in range(3))
        if vertical:
            pygame.draw.line(surf, color, (0, i), (w, i))
        else:
            pygame.draw.line(surf, color, (i, 0), (i, h))
    return surf


def drect_animated(surf, color, rect, r=6, a=255, border=0, bcol=None, 
                   hover=False, pulse=False, frame=0, glow_color=None):
    """Enhanced rect drawing with hover, pulse, and glow effects"""
    x,y,w,h = rect
    
    # Pulse animation
    if pulse:
        pulse_factor = 0.1 * math.sin(frame * 0.15)
        if isinstance(color, tuple) and len(color) >= 3:
            color = tuple(min(255, max(0, c + int(pulse_factor * 30))) for c in color[:3])
    
    # Hover lift effect
    offset_y = -2 if hover else 0
    shadow_alpha = 80 if hover else 30
    
    # Draw subtle shadow on hover
    if hover and offset_y != 0:
        shadow_surf = pygame.Surface((w+4, h+4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0,0,0,shadow_alpha), 
                        (2, 4, w, h), border_radius=r+2)
        surf.blit(shadow_surf, (x-1, y+1))
    
    # Glow effect for active elements
    if glow_color and (pulse or hover):
        glow_size = 3 if hover else 2
        glow_surf = pygame.Surface((w+glow_size*2, h+glow_size*2), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_color[:3], 50), 
                        (0,0,w+glow_size*2,h+glow_size*2), 
                        border_radius=r+glow_size)
        surf.blit(glow_surf, (x-glow_size, y+offset_y-glow_size))
    
    # Main button with gradient support
    if isinstance(color, (list, tuple)) and len(color) == 2:
        # Gradient color
        grad = gradient_surf(w, h+abs(offset_y), color[0], color[1])
        surf.blit(grad, (x, y+offset_y))
        pygame.draw.rect(surf, bcol or color[1], (x, y+offset_y, w, h), 
                        border_radius=r, width=max(1, border))
    else:
        # Standard rect
        if a < 255:
            ss = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(ss, (*color[:3], a), (0, 0, w, h), border_radius=r)
            surf.blit(ss, (x, y+offset_y))
        else:
            pygame.draw.rect(surf, color, (x, y+offset_y, w, h), border_radius=r)
        if border:
            pygame.draw.rect(surf, bcol or C["border"], (x, y+offset_y, w, h), 
                           border_radius=r, width=border)


def dtext(surf, txt, fnt, color, x, y, anchor="topleft", shadow=False, pulse=False, frame=0):
    """Enhanced text drawing with shadow and pulse animation"""
    # Handle RGBA colors
    if isinstance(color, tuple) and len(color) == 4:
        alpha = color[3]
        color_rgb = color[:3]
    else:
        alpha = 255
        color_rgb = color if isinstance(color, tuple) else (color, color, color)
    
    # Pulse effect for attention
    if pulse:
        pulse_val = 0.2 * math.sin(frame * 0.2)
        color_rgb = tuple(min(255, max(0, c + int(pulse_val * 40))) for c in color_rgb)
    
    if shadow:
        img = fnt.render(str(txt), True, (0, 0, 0))
        rc = img.get_rect(**{anchor: (x+1, y+1)})
        surf.blit(img, rc)
    
    img = fnt.render(str(txt), True, color_rgb)
    if alpha < 255:
        img.set_alpha(alpha)
    rc = img.get_rect(**{anchor: (x, y)})
    surf.blit(img, rc)
    return rc


def tri(surf, color, cx, cy, sz, lbl="", fnt=None, glow=False, frame=0):
    """Enhanced triangle drawing with optional glow"""
    h = sz * 0.86
    pts = [(int(cx), int(cy-h*0.56)), 
           (int(cx+sz*0.46), int(cy+h*0.40)), 
           (int(cx-sz*0.46), int(cy+h*0.40))]
    
    # Glow effect
    if glow:
        glow_surf = pygame.Surface((sz+10, sz+10), pygame.SRCALPHA)
        pygame.draw.polygon(glow_surf, (*color[:3], 60), 
                           [(p[0]-cx+sz//2+5, p[1]-cy+sz//2+5) for p in pts], width=3)
        surf.blit(glow_surf, (cx-sz//2-5, cy-sz//2-5))
    
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, (0,0,0), pts, 1)
    
    if lbl and fnt:
        img = fnt.render(lbl, True, (20,20,20))
        surf.blit(img, img.get_rect(center=(int(cx), int(cy+h*0.08))))


def draw_key_badge(surf, key_str, x, y, highlighted=False, frame=0):
    """Draw an enhanced keyboard key badge"""
    w = F_SM.size(key_str)[0] + 14
    if highlighted:
        pulse = 0.15 * math.sin(frame * 0.2)
        bg = tuple(min(255, c + int(pulse * 30)) for c in C["accent"][:3])
        drect_animated(surf, bg, (x, y, w, 20), r=5, border=2, 
                      bcol=C["glow_player"], pulse=True, frame=frame)
    else:
        drect_animated(surf, C["panel2"], (x, y, w, 20), r=5, 
                      border=1, bcol=C["border2"])
    dtext(surf, key_str, F_SM, C["text"] if highlighted else C["accent"], 
          x+w//2, y+10, "center")
    return w


# ── Accessibility Helpers ─────────────────────────────────────────────────────
def draw_cell_pattern(surf, pattern_type, x, y, size):
    """Draw accessibility patterns for colorblind support"""
    overlay = pygame.Surface((size, size), pygame.SRCALPHA)
    
    if pattern_type == "temporal":
        # Diagonal stripes for time walls
        for i in range(-size, size*2, 8):
            pygame.draw.line(overlay, C["pattern_diag"], 
                           (i, 0), (i+size, size), width=2)
    elif pattern_type == "path":
        # Dot pattern for solution path
        for i in range(3, size, 7):
            for j in range(3, size, 7):
                pygame.draw.circle(overlay, C["pattern_dot"], (i, j), 2)
    elif pattern_type == "start":
        # Cross pattern for start
        pygame.draw.line(overlay, C["pattern_dot"], (2, 2), (size-2, size-2), width=2)
        pygame.draw.line(overlay, C["pattern_dot"], (size-2, 2), (2, size-2), width=2)
    elif pattern_type == "exit":
        # Circle pattern for exit
        pygame.draw.circle(overlay, C["pattern_dot"], (size//2, size//2), size//3, width=2)
    
    surf.blit(overlay, (x, y))


# ── Maze Logic (unchanged from original) ──────────────────────────────────────
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
        nb = 2 if rng.random()<0.3 else 1
        blk: set = set()
        while len(blk)<nb: blk.add(rng.randint(0,T-1))
        tm[r][c] = list(blk)
    return g, tm


def walled(g, tm, n, T, r, c, t):
    if r<0 or r>=n or c<0 or c>=n: return True
    if g[r][c]: return True
    if t in tm[r][c]: return True
    return False


def astar(g, tm, n, T, sr=0, sc=0, st=0, reserved=None):
    heur = lambda r,c: abs(r-(n-1))+abs(c-(n-1))
    key  = lambda r,c,t: (r*n+c)*T+t
    heap=[]; gs={}; came={}
    k0=key(sr,sc,st); gs[k0]=0
    heapq.heappush(heap,(heur(sr,sc),sr,sc,st))
    vis=set()
    while heap:
        _,r,c,t = heapq.heappop(heap)
        k=key(r,c,t)
        if k in vis: continue
        vis.add(k)
        if r==n-1 and c==n-1:
            path=[]; cur=f"{r},{c},{t}"
            while cur in came:
                rr,cc,tt=map(int,cur.split(','))
                path.append((rr,cc,tt)); cur=came[cur]
            path.append((sr,sc,st)); path.reverse(); return path
        for dr,dc in [(1,0),(-1,0),(0,1),(0,-1),(0,0)]:
            nr,nc,nt=r+dr,c+dc,(t+1)%T
            if walled(g,tm,n,T,nr,nc,nt): continue
            if reserved and (nr,nc,nt) in reserved: continue
            nk=key(nr,nc,nt)
            ng=gs.get(k,0)+1+(0.3 if dr==dc==0 else 0)
            if gs.get(nk,1e18)>ng:
                gs[nk]=ng; came[f"{nr},{nc},{nt}"]=f"{r},{c},{t}"
                heapq.heappush(heap,(ng+heur(nr,nc),nr,nc,nt))
    return None


def robot_starts(n):
    cands=[(0,0),(0,1),(1,0),(0,2),(2,0),(1,1),(2,2)]
    return [(r,c) for r,c in cands if r<n and c<n][:NUM_R]


def negotiate(g, tm, n, T):
    reserved: Dict[Tuple,int]={}
    starts=robot_starts(n); paths=[]
    for rid in range(NUM_R):
        sr,sc=starts[rid]
        st=next((tt for tt in range(T) if not walled(g,tm,n,T,sr,sc,tt)),0)
        path=astar(g,tm,n,T,sr,sc,st,reserved)
        if path is None: path=astar(g,tm,n,T,sr,sc,st,None)
        paths.append(path)
        if path:
            for r,c,t in path: reserved[(r,c,t)]=rid
    return paths, reserved


# ── Enhanced State ────────────────────────────────────────────────────────────
@dataclass
class GS:
    n:int=13; T:int=4; tw:float=0.28; diff:str="Hard"; mode:str="player"
    grid:list=field(default_factory=list)
    temporal:list=field(default_factory=list)
    seed:int=0
    pr:int=0; pc:int=0; pt:int=0
    steps:int=0; waits:int=0; won:bool=False; par:int=0
    trail:list=field(default_factory=list)
    view_t:int=0; path_set:set=field(default_factory=set)
    msg:str=""; msg_col:tuple=field(default_factory=lambda:C["text3"])
    msg_timer:int=0
    scout_pos:list=field(default_factory=list)
    solver_pos:Optional[tuple]=None
    ai_running:bool=False
    ma_mode:bool=False
    ma_paths:list=field(default_factory=list)
    ma_step:int=0
    ma_pos:list=field(default_factory=list)
    ma_done:list=field(default_factory=list)
    ma_winner:int=-1
    ma_reserved:dict=field(default_factory=dict)
    ma_paradox:list=field(default_factory=list)
    ma_trails:list=field(default_factory=list)
    ma_phase:str=""
    ma_log:list=field(default_factory=list)
    hint_txt:str=""; show_hint:bool=False
    anim_tick:int=0
    # ✨ NEW: Enhanced features
    particles: list = field(default_factory=list)
    view_transition: float = 0.0
    target_view_t: Optional[int] = None
    show_settings: bool = False
    show_fps: bool = False
    particle_fx: bool = True
    screen_shake: tuple = (0, 0)
    shake_timer: int = 0
    debug_mode: bool = False


def new_level(s:GS):
    for _ in range(30):
        seed=random.randint(0,0x7fffffff)
        g,tm=build_maze(s.n,s.T,s.tw,seed)
        path=astar(g,tm,s.n,s.T)
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
    # ✨ Reset enhanced features
    s.particles = []
    s.view_transition = 0.0
    s.target_view_t = None
    s.show_settings = False
    s.screen_shake = (0, 0)
    s.shake_timer = 0


# ── Parallax Background ───────────────────────────────────────────────────────
def draw_parallax_bg(surf, W, H, frame):
    """Subtle animated parallax background grid"""
    # Base gradient with subtle animation
    for y in range(H):
        ratio = y / H
        wave = 0.03 * math.sin(frame * 0.02 + y * 0.01)
        r = int(10 + 3 * ratio + wave * 5)
        g = int(13 + 5 * ratio)
        b = int(22 + 15 * ratio + wave * 8)
        pygame.draw.line(surf, (r, g, b), (0, y), (W, y))
    
    # Floating grid lines (parallax effect)
    grid_spacing = 50
    offset = (frame * 0.4) % grid_spacing
    for i in range(-2, W//grid_spacing + 3):
        x = i * grid_spacing - offset
        alpha = int(20 + 12 * math.sin(frame * 0.05 + i * 0.3))
        pygame.draw.line(surf, (*C["grid_line"], alpha), 
                        (x, 0), (x, H), width=1)
    
    # Secondary parallax layer (slower)
    offset2 = (frame * 0.15) % (grid_spacing * 2)
    for i in range(-2, W//(grid_spacing*2) + 3):
        x = i * grid_spacing * 2 - offset2
        alpha = int(10 + 6 * math.sin(frame * 0.03 + i * 0.2))
        pygame.draw.line(surf, (*C["grid_line"], alpha), 
                        (x, 0), (x, H), width=1)


# ── Legend strip ───────────────────────────────────────────────────────────────
LEGEND_ITEMS = [
    (C["cell_open"],  "open",  "Open cell"),
    (C["cell_wall"],  "wall",  "Permanent wall"),
    (C["cell_temp"],  "temporal",  "Time wall (blocked NOW)"),
    (C["cell_tint"],  "tint",  "Changes over time"),
    (C["cell_path"],  "path",  "AI solution path"),
    (C["cell_start"], "start",  "Start (S)"),
    (C["cell_exit"],  "exit",  "Exit (E)"),
]

def draw_legend(surf, x, y, W_panel, frame):
    """Draw the colour legend with accessibility patterns"""
    drect_animated(surf, C["panel"], (x,y,W_panel,len(LEGEND_ITEMS)*22+14), r=8,
          border=1, bcol=C["border"], frame=frame)
    dtext(surf,"Legend", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for i,(col,pattern,label) in enumerate(LEGEND_ITEMS):
        ry=y+18+i*22
        # Draw color box
        drect_animated(surf, col, (x+8, ry+3, 14, 14), r=3, frame=frame)
        # Draw accessibility pattern overlay
        if pattern:
            draw_cell_pattern(surf, pattern, x+8, ry+3, 14)
        dtext(surf, label, F_SM, C["text3"], x+26, ry+4)


def draw_controls_panel(surf, x, y, W_panel, mode, frame):
    """Draw mode-specific control reference with enhanced styling"""
    if mode=="player":
        rows=[
            ("Move",      "[↑↓←→] or [WASD]"),
            ("Wait/Time", "[SPACE]"),
            ("Hint",      "[H]"),
            ("Restart",   "[R]"),
            ("Menu",      "[ESC]"),
            ("Quit",      "[Q]"),
        ]
    elif mode=="ai":
        rows=[
            ("Run solver", "[A]"),
            ("Reset",      "[R]"),
            ("Menu",       "[ESC]"),
            ("Quit",       "[Q]"),
        ]
    else:
        rows=[
            ("Run race",  "[A]"),
            ("Reset",     "[R]"),
            ("Menu",      "[ESC]"),
            ("Quit",      "[Q]"),
        ]
    ph = len(rows)*20+20
    drect_animated(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf,"Controls", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for i,(action,keys) in enumerate(rows):
        ry=y+20+i*20
        dtext(surf, action+":", F_SM, C["text3"], x+8, ry)
        dtext(surf, keys,       F_SM, C["accent"],x+W_panel-8, ry, "topright")


def draw_robot_panel(surf, x, y, W_panel, s:GS, frame):
    """Draw robot status panel for multi-agent mode with animations"""
    ph = NUM_R*38+20
    drect_animated(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf,"Robots", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for rid in range(NUM_R):
        ry=y+20+rid*38
        col=RCOLS[rid]
        glow = C[f"glow_robot{rid}"]
        
        # Robot icon with glow
        pygame.draw.circle(surf, col, (x+18,ry+14), 8)
        pygame.draw.circle(surf, (0,0,0), (x+18,ry+14), 8, 1)
        # Glow ring for active robots
        if s.ma_phase == "execute" and not s.ma_done[rid]:
            glow_rad = 10 + int(2 * math.sin(frame * 0.3 + rid))
            pygame.draw.circle(surf, (*glow, 40), (x+18, ry+14), glow_rad, width=2)
        
        fnt=pygame.font.SysFont("monospace",9,bold=True)
        img=fnt.render(str(rid),True,(20,20,20))
        surf.blit(img,img.get_rect(center=(x+18,ry+14)))
        
        # name + status with pulse for winner
        is_winner = (rid == s.ma_winner and s.ma_winner >= 0)
        name_pulse = is_winner and frame % 20 < 10
        dtext(surf, f"R{rid} — {RNAMES[rid]}", F_SM, col, x+32, ry+2, pulse=name_pulse, frame=frame)
        
        if s.ma_done[rid]:
            status = "🏆 WINNER!" if rid==s.ma_winner else "✓ Finished"
            scol=C["green"] if rid==s.ma_winner else C["text3"]
        elif s.ma_phase=="execute" and rid<len(s.ma_paths) and s.ma_paths[rid]:
            pct=min(100,int(s.ma_step/max(1,len(s.ma_paths[rid]))*100))
            status=f"⚡ Running  {pct}%"
            scol=C["text2"]
        elif s.ma_phase in("negotiate",):
            nsteps=len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0
            status=f"📋 Plan: {nsteps} steps" if nsteps else "⚠ No path"
            scol=C["text2"]
        else:
            status="⏳ Waiting"
            scol=C["text3"]
        dtext(surf, status, F_SM, scol, x+32, ry+17)
        
        # priority badge with color coding
        prio=["🔥 HIGH","⚡ MED","💤 LOW"][rid]
        pc=C["green"] if rid==0 else (C["warn"] if rid==1 else C["text3"])
        dtext(surf, f"prio:{prio}", F_SM, pc, x+W_panel-8, ry+2, "topright")


# ── Enhanced Maze Renderer ────────────────────────────────────────────────────
def draw_maze(surf, s:GS, ox, oy, cell, frame):
    n,T=s.n,s.T; g,tm=s.grid,s.temporal; vt=s.view_t
    ms=pygame.Surface((n*cell,n*cell),pygame.SRCALPHA)

    for r in range(n):
        for c in range(n):
            x,y=c*cell,r*cell
            blk=walled(g,tm,n,T,r,c,vt)
            op=r*n+c in s.path_set
            
            if blk:
                fill=C["cell_temp"] if not g[r][c] else C["cell_wall"]
                pattern="temporal" if not g[r][c] else "wall"
            else:
                fill=C["cell_path"] if op else C["cell_open"]
                pattern="path" if op else None
            
            # Draw cell with subtle animation for active view
            alpha = 255
            if s.view_transition > 0 and abs(vt - s.view_t) <= 1:
                # Fade cells that are transitioning
                dist = abs((r+c) - (s.pr+s.pc))
                alpha = max(100, 255 - int(80 * s.view_transition * (1 - dist/(n*0.5))))
            
            pygame.draw.rect(ms, (*fill, alpha) if alpha < 255 else fill,
                           (x+1,y+1,cell-2,cell-2), border_radius=2)
            
            # Draw accessibility pattern
            if pattern:
                draw_cell_pattern(ms, pattern, x+1, y+1, cell-2)
            
            # Time-varying tint animation
            if not blk and tm[r][c]:
                tint_alpha = 52 + int(20 * math.sin(frame * 0.1 + r + c))
                tint=pygame.Surface((cell-2,cell-2),pygame.SRCALPHA)
                tint.fill((*C["cell_tint"], tint_alpha))
                ms.blit(tint,(x+1,y+1))
            
            # Start/Exit with special patterns
            if r==0 and c==0:
                pygame.draw.rect(ms,C["cell_start"],(x+2,y+2,cell-4,cell-4),border_radius=2)
                draw_cell_pattern(ms, "start", x+2, y+2, cell-4)
            if r==n-1 and c==n-1:
                # Pulsing exit
                pulse = 0.1 * math.sin(frame * 0.15)
                exit_col = tuple(min(255, c + int(pulse * 30)) for c in C["cell_exit"][:3])
                pygame.draw.rect(ms, exit_col, (x+2,y+2,cell-4,cell-4), border_radius=2)
                draw_cell_pattern(ms, "exit", x+2, y+2, cell-4)

    # Draw paradox markers with animation
    for pr2,pc2 in s.ma_paradox:
        pulse = 0.3 * (0.5 + 0.5 * math.sin(frame * 0.3))
        pf=pygame.Surface((cell-2,cell-2),pygame.SRCALPHA)
        pf.fill((*C["paradox"], int(140 + pulse * 50)))
        ms.blit(pf,(pc2*cell+1,pr2*cell+1))

    # Grid lines with subtle animation
    for i in range(n+1):
        alpha = 60 + int(20 * math.sin(frame * 0.05 + i))
        pygame.draw.line(ms, (*C["bg"], alpha), (i*cell, 0), (i*cell, n*cell))
        pygame.draw.line(ms, (*C["bg"], alpha), (0, i*cell), (n*cell, i*cell))

    # S and E labels
    lf=pygame.font.SysFont("monospace", max(8, cell//4), bold=True)
    dtext(ms, "S", lf, (255,255,255), cell//2, cell//2, "center")
    dtext(ms, "E", lf, (255,255,255), (n-1)*cell+cell//2, (n-1)*cell+cell//2, "center")
    
    surf.blit(ms, (ox, oy))

    # Draw trails with fade effect
    af=pygame.font.SysFont("monospace", max(6, cell//5), bold=True)

    for i, (tr, tc) in enumerate(s.trail):
        age_ratio = i / max(1, len(s.trail))
        alpha = int(32 + 40 * age_ratio)
        ts=pygame.Surface((cell-4, cell-4), pygame.SRCALPHA)
        ts.fill((*C["r0"], alpha))
        surf.blit(ts, (ox+tc*cell+2, oy+tr*cell+2))

    # Player robot with glow
    if s.mode=="player" and not s.won:
        glow = 0.15 * math.sin(frame * 0.25)
        tri(surf, C["r0"], ox+s.pc*cell+cell//2, oy+s.pr*cell+cell//2,
            max(8, int(cell*0.68)), "P", af, glow=True, frame=frame)

    # AI solver position
    if s.solver_pos:
        tri(surf, C["r0"], ox+s.solver_pos[1]*cell+cell//2,
            oy+s.solver_pos[0]*cell+cell//2, max(8, int(cell*0.68)), "A", af)

    # Scout positions with fade
    for sr2, sc2, st2, alpha in s.scout_pos:
        if st2 != vt: continue
        cx2 = ox + sc2*cell + cell//2
        cy2 = oy + sr2*cell + cell//2
        rad = max(4, int(cell*0.22))
        # Animated pulse for scouts
        pulse_rad = rad + int(2 * math.sin(frame * 0.2))
        ss2 = pygame.Surface((pulse_rad*2+2, pulse_rad*2+2), pygame.SRCALPHA)
        pygame.draw.circle(ss2, (*C["r1"], int(alpha*255)), (pulse_rad+1, pulse_rad+1), pulse_rad)
        surf.blit(ss2, (cx2-pulse_rad-1, cy2-pulse_rad-1))

    # Multi-agent robots with enhanced trails
    if s.ma_phase:
        for rid in range(NUM_R):
            col = RCOLS[rid]
            trail = s.ma_trails[rid]
            
            # Enhanced trail with fade and size variation
            for i, (tr2, tc2) in enumerate(trail):
                age_ratio = i / max(1, len(trail))
                alpha = int(28 + 60 * age_ratio)
                size = int((cell-4) * (0.5 + 0.5 * age_ratio))
                offset = (cell - size) // 2
                
                ts2 = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.rect(ts2, (*col, alpha), (0, 0, size, size), 
                               border_radius=size//4)
                surf.blit(ts2, (ox + tc2*cell + offset, oy + tr2*cell + offset))
            
            # Robot position
            if rid < len(s.ma_pos):
                pr3, pc3 = s.ma_pos[rid]
                cx = ox + pc3*cell + cell//2
                cy = oy + pr3*cell + cell//2
                
                if s.ma_done[rid]:
                    # Finished robot with celebration effect
                    pygame.draw.circle(surf, col, (cx, cy), max(4, cell//5))
                    pygame.draw.circle(surf, (0,0,0), (cx, cy), max(4, cell//5), 1)
                    if rid == s.ma_winner and s.ma_winner >= 0:
                        # Winner crown effect
                        for angle in range(0, 360, 45):
                            rad = cell//3 + int(3 * math.sin(frame * 0.3 + angle))
                            px = cx + int(rad * math.cos(math.radians(angle)))
                            py = cy + int(rad * math.sin(math.radians(angle)))
                            pygame.draw.circle(surf, C["r0"], (px, py), 3)
                else:
                    # Active robot with pulse
                    tri(surf, col, cx, cy, max(8, int(cell*0.65)), str(rid), af, 
                        glow=(s.ma_phase == "execute"), frame=frame)


# ── Enhanced HUD bar ──────────────────────────────────────────────────────────
HUD_H = 52

def draw_hud(surf, s:GS, W, frame):
    drect_animated(surf, C["panel"], (0,0,W,HUD_H), r=0, frame=frame)
    pygame.draw.line(surf, C["border"], (0,HUD_H),(W,HUD_H))

    # left: stats or phase
    if s.mode=="player":
        stats=[("STEPS",str(s.steps)),("WAITS",str(s.waits)),
               (f"TIME","t="+str(s.view_t)),("PAR",str(s.par))]
        x=12
        for lbl,val in stats:
            drect_animated(surf, C["panel2"], (x,8,56,36), r=6, border=1, 
                          bcol=C["border"], frame=frame)
            dtext(surf, lbl, F_SM, C["text3"], x+28, 12, "center")
            dtext(surf, val, F_UI, C["text"], x+28, 26, "center", shadow=True)
            x+=64
    else:
        # Enhanced phase indicator with animation
        PHASE_INFO={
            "scout":    (C["r1"],   "🔍 SCOUT",    "Mapping time slices"),
            "gossip":   (C["warn"], "📡 GOSSIP",   "Sharing maps"),
            "negotiate":(C["r2"],   "🤝 NEGOTIATE","Planning paths"),
            "execute":  (C["green"],"🏁 EXECUTE",  "Racing to exit"),
            "done":     (C["green"],"✅ DONE",     "Race complete"),
            "":         (C["text3"],"⏸️  READY",    "Press A to start"),
        }
        ph=s.ma_phase; col,name,desc=PHASE_INFO.get(ph, PHASE_INFO[""])
        
        # Animated phase badge
        pulse = 0.1 * math.sin(frame * 0.2) if ph == "execute" else 0
        badge_col = tuple(min(255, c + int(pulse * 30)) for c in col[:3]) if pulse else col
        
        drect_animated(surf, C["panel2"], (8,6,150,40), r=8, border=1, 
                      bcol=badge_col, pulse=(ph=="execute"), frame=frame)
        dtext(surf, name, F_HEAD, badge_col, 83, 14, "center", shadow=True)
        dtext(surf, desc, F_SM, C["text3"], 83, 32, "center")
        
        # Winner badge with celebration
        if s.ma_winner >= 0:
            wc = RCOLS[s.ma_winner]
            drect_animated(surf, C["win_bg"], (165,8,170,36), r=8, 
                          border=1, bcol=wc, pulse=True, frame=frame)
            dtext(surf, f"🏆 R{s.ma_winner} WINS!", F_UI, wc, 250, 26, "center", shadow=True)

    # right: animated time-slice pills
    px = W - s.T*46 - 8
    dtext(surf, "TIME SLICE", F_SM, C["text3"], px-4, 10, "topright")
    
    for t in range(s.T):
        on = (t == s.view_t)
        # Enhanced pulse animation for active pill
        if on and s.view_transition <= 0:
            pulse = 0.2 * math.sin(frame * 0.25)
            bg_color = tuple(min(255, c + int(pulse * 40)) for c in C["accent"][:3])
            glow_size = int(3 + pulse * 4)
            text_pulse = True
        else:
            bg_color = C["pill_off"]
            glow_size = 0
            text_pulse = False
        
        # Draw glow for active
        if glow_size > 0:
            glow_surf = pygame.Surface((40+glow_size*2, 22+glow_size*2), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*C["accent"][:3], 50), 
                           (0,0,40+glow_size*2,22+glow_size*2), 
                           border_radius=11+glow_size//2)
            surf.blit(glow_surf, (px-glow_size, 24-glow_size))
        
        # Main pill with animation
        drect_animated(surf, bg_color, (px, 24, 40, 22), r=11, border=2, 
                      bcol=C["accent"] if on else C["border2"], 
                      pulse=on, frame=frame)
        
        # Animated number
        alpha = 255 if on else int(180 + 40*math.sin(frame*0.1 + t))
        dtext(surf, f"t={t}", F_SM, (*C["text"][:3], alpha) if on else C["text3"], 
              px+20, 35, "center", pulse=text_pulse, frame=frame)
        px += 46

    # centre: diff badge with subtle animation
    dtext(surf, f"{s.diff}  {s.n}×{s.n}  T={s.T}", F_SM, C["text3"], W//2, 10, "center")
    dtext(surf, f"Seed #{s.seed & 0xFFFF:04X}", F_SM, C["text3"], W//2, 26, "center")


# ── Enhanced status bar ───────────────────────────────────────────────────────
BOT_H = 28

def draw_statusbar(surf, s:GS, W, H, frame):
    y = H - BOT_H
    drect_animated(surf, C["panel"], (0, y, W, BOT_H), r=0, frame=frame)
    pygame.draw.line(surf, C["border"], (0, y), (W, y))

    if s.msg and s.msg_timer > 0:
        # Animated message with fade
        alpha = min(255, int(s.msg_timer / 30 * 255))
        dtext(surf, s.msg, F_SM, (*s.msg_col[:3], alpha), W//2, y+7, "center")
    else:
        if s.mode == "player":
            parts = ["[↑↓←→/WASD] Move", "[SPACE] Wait", "[H] Hint", "[R] Restart", "[ESC] Menu"]
        elif s.mode == "ai":
            parts = ["[A] Run AI", "[R] Reset", "[ESC] Menu"]
        else:
            parts = ["[A] Run race", "[R] Reset", "[ESC] Menu"]
        hint = " · ".join(parts)
        dtext(surf, hint, F_SM, C["text3"], W//2, y+7, "center")


# ── Enhanced phase log panel ──────────────────────────────────────────────────
def draw_log_panel(surf, s:GS, x, y, w, frame):
    if not s.ma_log: return
    lines = s.ma_log[-7:]
    ph = len(lines)*16 + 14
    drect_animated(surf, C["panel"], (x, y, w, ph), r=8, border=1, bcol=C["border"], frame=frame)
    dtext(surf, "📋 Event Log", F_SM, C["text3"], x+w//2, y+4, "center")
    
    for i, ln in enumerate(lines):
        # Color coding with animation for important messages
        if "WINNER" in ln:
            col = C["green"]
            pulse = frame % 30 < 15
        elif "PARADOX" in ln:
            col = C["paradox"]
            pulse = frame % 20 < 10
        elif ln.startswith("Phase"):
            col = C["text2"]
            pulse = False
        else:
            col = C["text3"]
            pulse = False
        
        # Truncate to fit with ellipsis
        max_chars = w // 7
        display_ln = ln if len(ln) <= max_chars else ln[:max_chars-3] + "..."
        dtext(surf, display_ln, F_SM, col, x+6, y+14+i*16, pulse=pulse, frame=frame)


# ── Enhanced hint overlay ─────────────────────────────────────────────────────
def draw_hint(surf, s:GS, W, H, frame):
    if not s.show_hint or not s.hint_txt: return
    lines = s.hint_txt.split("\n")
    pw = min(W-60, 540)
    ph = len(lines)*20 + 60
    px = (W-pw)//2
    py = (H-ph)//2
    
    # Animated backdrop
    drect_animated(surf, (0,0,0), (0,0,W,H), a=140, frame=frame)
    
    # Enhanced panel with gradient border
    drect_animated(surf, C["panel"], (px, py, pw, ph), r=12, border=2, 
                  bcol=C["accent"], pulse=True, frame=frame)
    
    # Animated title
    dtext(surf, "💡 HINT", F_HEAD, C["accent"], px+pw//2, py+12, "center", 
          pulse=True, frame=frame)
    pygame.draw.line(surf, C["border"], (px+12, py+34), (px+pw-12, py+34))
    
    # Hint content with line-by-line fade
    for i, ln in enumerate(lines):
        # Staggered fade-in animation
        fade_alpha = min(255, int((frame - i*5) / 10 * 255)) if frame > i*5 else 0
        if fade_alpha > 0:
            dtext(surf, ln, F_UI, (*C["text"][:3], fade_alpha), 
                  px+16, py+42+i*20)
    
    # Close instruction with pulse
    dtext(surf, "Press [H] to close", F_SM, C["text3"], px+pw//2, py+ph-20, 
          "center", pulse=True, frame=frame)


# ── Enhanced win / race-over overlay ──────────────────────────────────────────
def draw_win(surf, s:GS, W, H, frame):
    if not s.won: return
    
    # Animated backdrop with particles
    drect_animated(surf, (0,0,0), (0,0,W,H), a=170, frame=frame)
    
    # Spawn celebration particles
    if s.particle_fx and frame % 5 == 0 and len(s.particles) < 150:
        spawn_particles(s.particles, random.randint(0, W), random.randint(0, H//2), 
                       random.choice([C["r0"], C["r1"], C["r2"], C["green"]]), 
                       count=3, spread=1.5, life=2.5)
    
    # Update and draw particles
    if s.particle_fx:
        s.particles = [p for p in s.particles if p.update(16)]
        for p in s.particles:
            p.draw(surf)
    
    pw = min(W-40, 520)
    ph = 220 if s.mode=="player" else 260
    px = (W-pw)//2
    py = (H-ph)//2
    
    # Enhanced win panel with animated gradient background
    drect_animated(surf, C["win_bg"], (px, py, pw, ph), r=16, border=2, 
                  bcol=C["win_border"], pulse=True, frame=frame)
    
    # Animated gradient background for win panel
    grad_h = ph - 40
    for i in range(grad_h):
        ratio = i / grad_h
        pulse = 0.05 * math.sin(frame * 0.1 + i * 0.1)
        r = int(12 + (36 + pulse*20) * ratio)
        g = int(48 + (100 + pulse*30) * ratio)  
        b = int(26 + (50 + pulse*15) * ratio)
        pygame.draw.line(surf, (r,g,b), (px+20, py+40+i), (px+pw-20, py+40+i))

    if s.mode == "player":
        eff = round(s.par/max(s.steps,1)*100)
        grade = "S" if eff>=100 else ("A" if eff>=85 else ("B" if eff>=70 else "C"))
        gcol = {"S":(255,215,0), "A":C["green"], "B":C["warn"], "C":C["err"]}[grade]
        
        # Animated title
        dtext(surf, "🎉 EXIT REACHED!", F_TITLE, C["win_border"], 
              px+pw//2, py+18, "center", shadow=True, pulse=True, frame=frame)
        pygame.draw.line(surf, C["border"], (px+20, py+54), (px+pw-20, py+54))
        
        # Animated stat boxes
        stat_data = [("STEPS", str(s.steps)), ("WAITS", str(s.waits)),
                     ("OPTIMAL", str(s.par)), ("EFF", f"{eff}%")]
        bw = (pw-40)//4
        for i, (lbl, val) in enumerate(stat_data):
            bx = px+20 + i*(bw+4)
            # Hover-like pulse for stats
            pulse = (frame // 15 + i) % 4 == 0
            drect_animated(surf, C["panel2"], (bx, py+64, bw, 52), r=8, 
                          border=1, bcol=C["border2"], pulse=pulse, frame=frame)
            dtext(surf, lbl, F_SM, C["text3"], bx+bw//2, py+70, "center")
            dtext(surf, val, F_HEAD, C["text"], bx+bw//2, py+86, "center", shadow=True)
        
        # Animated grade badge
        drect_animated(surf, gcol, (px+pw//2-30, py+130, 60, 50), r=10, 
                      border=2, bcol=gcol, pulse=True, frame=frame)
        grade_font = pygame.font.SysFont("segoeui", 36, bold=True)
        dtext(surf, grade, grade_font, (20,20,20), px+pw//2, py+155, "center")
        dtext(surf, "GRADE", F_SM, C["text3"], px+pw//2, py+132, "center")
        
        # Button hints with animation
        dtext(surf, "[N] Next Level    [R] Retry    [ESC] Menu",
              F_UI, C["text3"], px+pw//2, py+196, "center", pulse=True, frame=frame)
    else:
        w = s.ma_winner
        title = "🏁 RACE OVER!" if w>=0 else "✅ RACE COMPLETE"
        dtext(surf, title, F_TITLE, C["win_border"], px+pw//2, py+18, 
              "center", shadow=True, pulse=True, frame=frame)
        pygame.draw.line(surf, C["border"], (px+20, py+54), (px+pw-20, py+54))
        
        if w >= 0:
            wc = RCOLS[w]
            drect_animated(surf, C["panel2"], (px+pw//2-110, py+64, 220, 60), 
                          r=10, border=2, bcol=wc, pulse=True, frame=frame)
            pygame.draw.circle(surf, wc, (px+pw//2-70, py+94), 18)
            dtext(surf, str(w), F_HEAD, (20,20,20), px+pw//2-70, py+94, "center")
            dtext(surf, f"🤖 ROBOT {w} WINS!", F_HEAD, wc, px+pw//2+10, py+80, 
                  "center", shadow=True, pulse=True, frame=frame)
            dtext(surf, RNAMES[w]+" team", F_SM, C["text3"], px+pw//2+10, py+104, "center")
        
        # All robots summary with animations
        for rid in range(NUM_R):
            ry = py+140 + rid*26
            col = RCOLS[rid]
            pygame.draw.circle(surf, col, (px+60, ry+10), 8)
            
            status = "🏆 WINNER!" if rid==w else ("✓ Finished" if s.ma_done[rid] else "✗ DNF")
            scol = C["green"] if rid==w else C["text2"]
            plen = len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0
            
            dtext(surf, f"R{rid} {RNAMES[rid]}:", F_UI, col, px+80, ry+3)
            dtext(surf, f"{status} · {plen} steps", F_SM, scol, px+210, ry+5, 
                  pulse=(rid==w), frame=frame)
        
        dtext(surf, "[N] Next    [R] Retry    [ESC] Menu",
              F_UI, C["text3"], px+pw//2, py+ph-22, "center")


# ── Enhanced TITLE SCREEN ─────────────────────────────────────────────────────
def draw_title(surf, W, H, sel_diff, sel_mode, hover, frame):
    # Animated parallax background
    draw_parallax_bg(surf, W, H, frame)

    # Animated particle dots
    rng2 = random.Random(42)
    for i in range(24):
        px2 = int(rng2.random() * W)
        py2 = int(rng2.random() * H * 0.55)
        r2 = rng2.randint(1, 3)
        # Enhanced animation with multiple frequencies
        alpha = int(70 + 50 * math.sin(frame * 0.03 + i + rng2.random() * 6))
        size = r2 + int(1.5 * math.sin(frame * 0.1 + i * 0.5))
        ss = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        pygame.draw.circle(ss, (*C["accent"], alpha), (size, size), size)
        surf.blit(ss, (px2-size, py2-size))

    # Animated title with pulse
    dtext(surf, "TEMPORAL", F_TITLE, C["accent"], W//2, 28, "center", 
          shadow=True, pulse=True, frame=frame)
    dtext(surf, "MAZE", F_TITLE, C["text"], W//2, 64, "center", 
          shadow=True, pulse=True, frame=frame)
    dtext(surf, "✨ Multi-Agent Negotiation Edition ✨", F_UI, C["text3"], 
          W//2, 102, "center", pulse=True, frame=frame)

    pygame.draw.line(surf, C["border"], (W//2-160, 118), (W//2+160, 118))

    # ── HOW TO PLAY cards with hover animation ─────────────────────────────
    tw_cards = [
        (C["r0"],  "🎮 Move Through Space",
         "Use Arrow keys or WASD\nto navigate the grid.\nReach the RED exit cell."),
        (C["cell_temp"], "⏱️  Time Walls",
         "Amber cells are blocked\nONLY at certain time steps.\nThey open as time advances!"),
        (C["accent"], "🔄 Wait = Time Travel",
         "Press SPACE to stay in\nplace. This advances time\nby 1 — opening new paths."),
        (C["r2"],  "🤖 Multi-Agent Race",
         "3 robots Scout → Gossip →\nNegotiate paths → Race\nto the exit simultaneously."),
    ]
    cw2 = int((W-60)//4)
    ch2 = 115
    for i, (icol, title2, body) in enumerate(tw_cards):
        cx2 = 20 + i*(cw2+6)
        cy2 = 130
        on = (hover == f"card{i}")
        
        # Enhanced card with gradient border on hover
        bg = gradient_surf(cw2, ch2, C["panel2"], C["panel"]) if on else C["panel"]
        bc = C["accent"] if on else C["border"]
        drect_animated(surf, bg if isinstance(bg, tuple) and len(bg)==2 else C["panel2"], 
                      (cx2, cy2, cw2, ch2), r=10, border=2 if on else 1, 
                      bcol=bc, hover=on, frame=frame)
        
        # Animated color bar top
        bar_w = cw2 + int(5 * math.sin(frame * 0.1 + i))
        drect_animated(surf, icol, (cx2, cy2, bar_w, 5), r=3, frame=frame)
        
        dtext(surf, title2, F_UI, C["text"], cx2+cw2//2, cy2+14, "center", 
              shadow=on, pulse=on, frame=frame)
        pygame.draw.line(surf, C["border"], (cx2+10, cy2+32), (cx2+cw2-10, cy2+32))
        
        for j, line in enumerate(body.split("\n")):
            # Staggered text animation
            fade = min(255, int((frame - j*3) / 8 * 255)) if frame > j*3 else 100
            dtext(surf, line, F_SM, (*C["text3"][:3], fade), 
                  cx2+cw2//2, cy2+40+j*18, "center")

    # ── DIFFICULTY selector with animations ─────────────────────────────────
    diffs = list(DIFFS.keys())
    dtext(surf, "SELECT DIFFICULTY", F_UI, C["text3"], W//2, 255, "center")
    pygame.draw.line(surf, C["border"], (W//2-100, 271), (W//2+100, 271))

    dcw = int((W-40)//4)
    dch = 78
    for i, d in enumerate(diffs):
        dcx = 20 + i*(dcw+5)
        dcy = 277
        on = (d == sel_diff)
        bg = gradient_surf(dcw, dch, C["accent2"], C["panel"]) if on else C["panel"]
        bc = C["accent"] if on else C["border"]
        
        drect_animated(surf, bg if isinstance(bg, tuple) and len(bg)==2 else C["panel"], 
                      (dcx, dcy, dcw, dch), r=10, border=2 if on else 1, 
                      bcol=bc, hover=on, pulse=on, frame=frame)
        
        info = DIFFS[d]
        dtext(surf, d, F_HEAD, C["text"] if on else C["text2"], 
              dcx+dcw//2, dcy+8, "center", shadow=on, pulse=on, frame=frame)
        dtext(surf, f"{info['n']}×{info['n']}", F_UI, C["accent"] if on else C["text3"],
              dcx+dcw//2, dcy+30, "center")
        dtext(surf, f"{info['T']} time slices", F_SM, C["text3"], 
              dcx+dcw//2, dcy+48, "center")
        dtext(surf, f"{int(info['tw']*100)}% temporal walls", F_SM, C["text3"], 
              dcx+dcw//2, dcy+63, "center")

    # ── MODE selector with enhanced cards ───────────────────────────────────
    dtext(surf, "SELECT MODE", F_UI, C["text3"], W//2, 362, "center")
    pygame.draw.line(surf, C["border"], (W//2-100, 378), (W//2+100, 378))

    modes = [
        ("player", "🎮 PLAY YOURSELF", "Control the agent\nwith keyboard", "Arrow/WASD + Space"),
        ("ai", "🤖 WATCH AI", "Single A* solver\nanimates the solution", "Press A to run"),
        ("multi", "🏁 MULTI-AGENT RACE", "3 robots Scout→Gossip\n→Negotiate→Race", "Press A to start"),
    ]
    mw = int((W-40)//3)
    mh = 92
    for i, (m, mname, mdesc, mhint) in enumerate(modes):
        mcx = 20 + i*(mw+5)
        mcy = 384
        on = (m == sel_mode)
        bg = gradient_surf(mw, mh, C["accent2"], C["panel"]) if on else C["panel"]
        bc = C["accent"] if on else C["border"]
        
        drect_animated(surf, bg if isinstance(bg, tuple) and len(bg)==2 else C["panel"], 
                      (mcx, mcy, mw, mh), r=10, border=2 if on else 1, 
                      bcol=bc, hover=on, pulse=on, frame=frame)
        
        dtext(surf, mname, F_HEAD, C["text"] if on else C["text2"], 
              mcx+mw//2, mcy+8, "center", shadow=on, pulse=on, frame=frame)
        for j, line in enumerate(mdesc.split("\n")):
            dtext(surf, line, F_SM, C["text3"], mcx+mw//2, mcy+30+j*17, "center")
        dtext(surf, mhint, F_SM, C["accent"] if on else C["text3"],
              mcx+mw//2, mcy+mh-18, "center", pulse=on, frame=frame)

    # ── START button with enhanced animation ─────────────────────────────────
    bw2 = 200
    bh2 = 50
    bx2 = (W-bw2)//2
    by2 = 485
    on2 = (hover == "start")
    
    # Pulsing gradient button
    grad_colors = (C["grad_start"], C["grad_end"])
    drect_animated(surf, grad_colors, (bx2, by2, bw2, bh2), r=12,
                  border=2, bcol=C["accent"], hover=on2, pulse=on2, 
                  glow_color=C["glow_player"], frame=frame)
    
    # Animated text
    dtext(surf, "🚀 START GAME", F_HEAD, (255,255,255), bx2+bw2//2, by2+bh2//2, 
          "center", shadow=True, pulse=on2, frame=frame)
    dtext(surf, "or press  Enter", F_SM, C["text3"], W//2, by2+bh2+10, "center")

    # ── keyboard shortcuts with badges ───────────────────────────────────────
    shortcuts = [
        ("← →", "Select difficulty"),
        ("Tab", "Cycle mode"),
        ("Enter", "Start game"),
    ]
    sy = 550
    for k2, v2 in shortcuts:
        kw = F_SM.size(f"[{k2}]")[0] + 14
        kx = W//2 - 190
        drect_animated(surf, C["panel2"], (kx, sy, kw, 20), r=5, 
                      border=1, bcol=C["border2"], frame=frame)
        dtext(surf, f"[{k2}]", F_SM, C["accent"], kx+kw//2, sy+10, "center")
        dtext(surf, v2, F_SM, C["text3"], kx+kw+12, sy+10, "midleft")
        sy += 24

    # ── return rects for hit-testing ───────────────────────────────────────
    hit_rects = {}
    for i, d in enumerate(diffs):
        hit_rects[f"diff_{d}"] = (20+i*(dcw+5), 277, dcw, dch)
    for i, (m, *_) in enumerate(modes):
        hit_rects[f"mode_{m}"] = (20+i*(mw+5), 384, mw, mh)
    hit_rects["start"] = (bx2, by2, bw2, bh2)
    return hit_rects


# ── Settings Panel ────────────────────────────────────────────────────────────
def draw_settings_panel(surf, s:GS, W, H, frame):
    """Draw toggleable settings panel"""
    if not s.show_settings:
        # Small settings button in corner
        btn_w, btn_h = 32, 32
        drect_animated(surf, C["panel2"], (W-btn_w-8, HUD_H+8, btn_w, btn_h), 
                      r=6, border=1, bcol=C["border"], hover=True, frame=frame)
        dtext(surf, "⚙️", F_UI, C["text3"], W-btn_w//2-8, HUD_H+10)
        return
    
    pw, ph = 340, 240
    px, py = (W-pw)//2, (H-ph)//2 - 20
    
    # Animated panel entrance
    if frame < 25:
        py += int(30 * (1 - frame/25))  # Slide in animation
    
    drect_animated(surf, C["panel"], (px, py, pw, ph), r=12, border=2, 
                  bcol=C["accent"], pulse=True, frame=frame)
    dtext(surf, "⚙️  Settings", F_HEAD, C["accent"], px+pw//2, py+14, "center")
    
    # Toggle options
    options = [
        ("Show Hints", s.show_hint, "h", "Toggle hint overlay"),
        ("Particle FX", s.particle_fx, "p", "Celebration particles"),
        ("Show FPS", s.show_fps, "f", "Display frame rate"),
        ("Debug Mode", s.debug_mode, "d", "Extra diagnostics"),
    ]
    
    for i, (label, enabled, key, desc) in enumerate(options):
        y_pos = py + 45 + i * 36
        dtext(surf, f"{label}  [{key.upper()}]", F_SM, C["text2"], px+18, y_pos)
        dtext(surf, desc, F_SM, C["text3"], px+18, y_pos+14)
        
        # Animated toggle switch
        switch_x = px + pw - 70
        drect_animated(surf, C["pill_off"] if not enabled else C["green"], 
                      (switch_x, y_pos+4, 50, 22), r=11, frame=frame)
        circle_x = switch_x + 11 + (28 if enabled else 0)
        # Animated circle position
        if enabled != getattr(s, f"_{key}_prev", enabled):
            circle_x = switch_x + 11 + (28 * min(1, (frame % 10) / 10))
        pygame.draw.circle(surf, (255,255,255), (int(circle_x), y_pos+15), 9)
    
    # Close instruction
    dtext(surf, "Press [S] or click outside to close", F_SM, C["text3"], 
          px+pw//2, py+ph-22, "center", pulse=True, frame=frame)


# ── Screen Shake Helper ───────────────────────────────────────────────────────
def apply_screen_shake(offset, intensity, duration):
    """Calculate screen shake offset"""
    if duration <= 0:
        return (0, 0), 0
    new_offset = (random.randint(-intensity, intensity), 
                  random.randint(-intensity, intensity))
    return new_offset, duration - 1


# ── AI generators (unchanged logic, enhanced logging) ─────────────────────────
def gen_single(s:GS):
    n,T=s.n,s.T; g,tm=s.grid,s.temporal
    for t in range(T):
        for r in range(n):
            for c in range(n):
                s.scout_pos=[(a,b,d,max(0,e-0.07)) for a,b,d,e in s.scout_pos if e>0.02]
                s.scout_pos.append((r,c,t,1.0))
                s.view_t=t; yield "scout"
    s.scout_pos=[]
    path=astar(g,tm,n,T)
    if not path: s.won=True; return
    for p in path: s.path_set.add(p[0]*n+p[1])
    tw2=sum(1 for i in range(1,len(path)) if path[i][:2]==path[i-1][:2])
    s.msg=f"✨ AI found path: {len(path)} steps, {tw2} time waits"
    s.msg_col=C["green"]; s.msg_timer=300
    for r,c,t in path:
        s.solver_pos=(r,c); s.view_t=t; yield "solve"
    s.won=True; s.solver_pos=(n-1,n-1)
    # Celebration particles on win
    if s.particle_fx:
        spawn_particles(s.particles, W//2, H//2, C["green"], count=30, spread=3.0, life=3.0)


def gen_multi(s:GS):
    n,T=s.n,s.T; g,tm=s.grid,s.temporal

    s.ma_phase="scout"
    s.ma_log=["✨ Phase 1 — Scout: robots mapping time slices..."]
    slices_per=max(1,T//NUM_R)
    scout_maps={rid:set() for rid in range(NUM_R)}

    for t in range(T):
        owner=min(t//slices_per, NUM_R-1)
        for r in range(n):
            for c in range(n):
                s.scout_pos=[(a,b,d,max(0,e-0.06)) for a,b,d,e in s.scout_pos if e>0.02]
                s.scout_pos.append((r,c,t,1.0))
                if not walled(g,tm,n,T,r,c,t): scout_maps[owner].add((r,c,t))
                s.view_t=t; yield "scout"

    s.scout_pos=[]
    total2=sum(len(v) for v in scout_maps.values())
    s.ma_log.append(f"🔍 Scouts found {total2} open (r,c,t) cells total.")
    yield "scout_done"

    s.ma_phase="gossip"
    s.ma_log.append("📡 Phase 2 — Gossip: broadcasting maps to all robots...")
    all_open: set=set()
    for v in scout_maps.values(): all_open|=v
    for rid in range(NUM_R): scout_maps[rid]=all_open
    s.ma_log.append(f"✅ Gossip complete — each robot knows {len(all_open)} open cells.")
    yield "gossip"

    s.ma_phase="negotiate"
    s.ma_log.append("🤝 Phase 3 — Negotiate: priority planning (R0>R1>R2)...")
    paths,reserved=negotiate(g,tm,n,T)
    s.ma_paths=paths; s.ma_reserved=reserved
    for rid,path in enumerate(paths):
        if path:
            wt=sum(1 for i in range(1,len(path)) if path[i][:2]==path[i-1][:2])
            avoid=f"avoids R{',R'.join(str(j) for j in range(rid))}" if rid>0 else "conflict-free"
            s.ma_log.append(f"  ✅ R{rid}: {len(path)} steps, {wt} waits — {avoid}")
        else:
            s.ma_log.append(f"  ⚠️  R{rid}: no path — using best-effort")
    yield "negotiate"

    s.ma_phase="execute"
    s.ma_log.append("🏁 Phase 4 — Execute: robots racing simultaneously!")
    max_steps=max((len(p) for p in paths if p), default=0)

    for step in range(max_steps):
        s.ma_step=step; s.ma_paradox=[]
        occupied:Dict[tuple,int]={}
        for rid in range(NUM_R):
            if s.ma_done[rid]: continue
            path=paths[rid]
            if not path or step>=len(path): s.ma_done[rid]=True; continue
            r,c,t=path[step]
            s.ma_pos[rid]=(r,c); s.view_t=t
            s.ma_trails[rid].append((r,c))
            if len(s.ma_trails[rid])>22: s.ma_trails[rid].pop(0)
            if (r,c) in occupied:
                s.ma_paradox.append((r,c))
                other=occupied[(r,c)]
                s.ma_log.append(f"  ⚡ PARADOX! R{rid} & R{other} collide at ({r},{c}) t={t}")
                # Screen shake on paradox
                s.shake_timer = 10
            occupied[(r,c)]=rid
            if r==n-1 and c==n-1 and not s.ma_done[rid]:
                s.ma_done[rid]=True
                if s.ma_winner<0:
                    s.ma_winner=rid
                    s.ma_log.append(f"  🏆 *** R{rid} ({RNAMES[rid]}) reaches exit — WINNER! ***")
                    # Celebration particles
                    if s.particle_fx:
                        spawn_particles(s.particles, 
                                       W//2 + random.randint(-100,100), 
                                       H//2 + random.randint(-50,50), 
                                       RCOLS[rid], count=20, spread=2.5, life=3.0)
        if all(s.ma_done): break
        yield "execute"

    for rid in range(NUM_R):
        if not s.ma_done[rid]: s.ma_done[rid]=True
    s.ma_phase="done"; s.ma_mode=False
    if s.ma_winner<0 and any(s.ma_done):
        s.ma_winner=next(i for i,d in enumerate(s.ma_done) if d)
    s.won=True
    s.ma_log.append(f"🏁 Race complete · Winner: R{s.ma_winner} · "
                    f"Paradoxes: {len(s.ma_paradox)}")
    yield "done"


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    global F_TITLE, F_HEAD, F_UI, F_SM, F_MONO, W, H

    pygame.init()
    screen = pygame.display.set_mode((1024, 768), pygame.RESIZABLE)
    pygame.display.set_caption("✨ Temporal Maze — Multi-Agent Negotiation ✨")
    # Optional: set icon if you have one
    # icon = pygame.image.load("icon.png")
    # pygame.display.set_icon(icon)
    clock = pygame.time.Clock()

    F_TITLE = pygame.font.SysFont("segoeui",  32, bold=True)
    F_HEAD  = pygame.font.SysFont("segoeui",  16, bold=False)
    F_UI    = pygame.font.SysFont("segoeui",  13)
    F_SM    = pygame.font.SysFont("segoeui",  11)
    F_MONO  = pygame.font.SysFont("monospace", 11, bold=True)

    SIDEBAR_W = 180
    SCOUT_MS  = 7
    SOLVE_MS  = 85
    EXEC_MS   = 115

    sel_diff = "Hard"
    sel_mode = "player"
    cur_scr = "title"
    state = GS()
    ai_gen = None
    ai_accum = 0.0
    frame = 0
    hover_id = ""
    title_hit_rects = {}
    shake_offset = (0, 0)
    shake_timer = 0

    def start():
        nonlocal cur_scr, ai_gen
        cfg = DIFFS[sel_diff]
        state.n = cfg["n"]
        state.T = cfg["T"]
        state.tw = cfg["tw"]
        state.diff = sel_diff
        state.mode = sel_mode
        new_level(state)
        cur_scr = "game"
        ai_gen = None

    def smsg(txt, col=None, dur=220):
        state.msg = txt
        state.msg_col = col or C["text3"]
        state.msg_timer = dur

    def pmove(dr, dc):
        if state.won or state.mode != "player": return
        nr, nc, nt = state.pr+dr, state.pc+dc, (state.pt+1)%state.T
        if walled(state.grid, state.temporal, state.n, state.T, nr, nc, nt):
            if dr == dc == 0:
                smsg("⚠️  Cannot wait here — a wall appears at the next time step!", C["warn"])
            else:
                smsg("🚫 Blocked! That cell is a wall at the next time step.", C["err"])
            return
        if dr == dc == 0: state.waits += 1
        state.pr, state.pc, state.pt = nr, nc, nt
        state.steps += 1
        state.view_t = nt
        state.trail.append((nr, nc))
        if len(state.trail) > 20: state.trail.pop(0)
        smsg("")
        if nr == state.n-1 and nc == state.n-1:
            state.won = True
            # Celebration particles on player win
            if state.particle_fx:
                spawn_particles(state.particles, W//2, H//2, C["green"], count=40, spread=3.0, life=3.0)
            state.shake_timer = 15  # Screen shake on win

    def do_hint():
        path = astar(state.grid, state.temporal, state.n, state.T)
        if not path:
            state.hint_txt = "⚠️  No solution exists from start.\nTry restarting."
            state.show_hint = True
            return
        twpts = [path[i][2] for i in range(1, len(path)) if path[i][:2] == path[i-1][:2]]
        if twpts:
            state.hint_txt = (
                f"✨ Optimal path: {len(path)} steps with {len(twpts)} time wait(s).\n"
                f"You need to WAIT at time step(s): t={', t='.join(map(str, twpts))}\n\n"
                f"💡 Strategy: navigate toward the blocked cell,\n"
                f"then press SPACE to wait — the wall opens at t+1.\n"
                f"🔄 Remember: every move also advances time by 1!")
        else:
            state.hint_txt = (
                f"✨ Optimal path: {len(path)} steps — NO time waits needed!\n"
                f"This is pure spatial navigation.\n"
                f"💡 Tip: look for the open corridor leading toward\n"
                f"the bottom-right exit cell (red).")
        state.show_hint = not state.show_hint

    def launch_single():
        nonlocal ai_gen
        if state.ai_running: return
        state.ai_running = True
        ai_gen = gen_single(state)

    def launch_multi():
        nonlocal ai_gen
        if state.ai_running: return
        state.ai_running = True
        state.ma_mode = True
        state.ma_pos = list(robot_starts(state.n))
        state.ma_done = [False]*NUM_R
        state.ma_winner = -1
        state.ma_trails = [[] for _ in range(NUM_R)]
        state.ma_paradox = []
        state.ma_log = []
        ai_gen = gen_multi(state)

    def reset_ai():
        nonlocal ai_gen
        state.ai_running = False
        state.ma_mode = False
        ai_gen = None
        state.scout_pos = []
        state.solver_pos = None
        state.path_set = set()
        state.ma_phase = ""
        state.ma_pos = list(robot_starts(state.n))
        state.ma_done = [False]*NUM_R
        state.ma_winner = -1
        state.ma_trails = [[] for _ in range(NUM_R)]
        state.ma_paradox = []
        state.ma_log = []
        state.won = False

    # Store previous toggle states for animation
    state._h_prev = state.show_hint
    state._p_prev = state.particle_fx
    state._f_prev = state.show_fps
    state._d_prev = state.debug_mode

    while True:
        W, H = screen.get_size()
        dt_ms = clock.tick(60)
        frame += 1
        state.anim_tick = frame

        mx_g, my_g = pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if cur_scr == "title":
                diffs = list(DIFFS.keys())
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN:
                        start()
                    if ev.key == pygame.K_TAB:
                        ml = ["player", "ai", "multi"]
                        sel_mode = ml[(ml.index(sel_mode)+1) % len(ml)]
                    if ev.key == pygame.K_LEFT:
                        idx = diffs.index(sel_diff)
                        sel_diff = diffs[max(0, idx-1)]
                    if ev.key == pygame.K_RIGHT:
                        idx = diffs.index(sel_diff)
                        sel_diff = diffs[min(len(diffs)-1, idx+1)]
                    if ev.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()
                    # Settings toggle
                    if ev.key == pygame.K_s:
                        state.show_settings = not state.show_settings
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for hid, (hx, hy, hw, hh2) in title_hit_rects.items():
                        if hx <= mx_g <= hx+hw and hy <= my_g <= hy+hh2:
                            if hid == "start":
                                start()
                            elif hid.startswith("diff_"):
                                sel_diff = hid[5:]
                            elif hid.startswith("mode_"):
                                sel_mode = hid[5:]

            else:  # game screen
                if ev.type == pygame.KEYDOWN:
                    k = ev.key
                    if k == pygame.K_q:
                        pygame.quit()
                        sys.exit()
                    if k == pygame.K_ESCAPE:
                        cur_scr = "title"
                    if k == pygame.K_r:
                        if state.mode == "player":
                            new_level(state)
                            ai_gen = None
                        else:
                            reset_ai()
                    if k == pygame.K_n and state.won:
                        new_level(state)
                        ai_gen = None
                        reset_ai()
                    # Settings toggle in game
                    if k == pygame.K_s:
                        state.show_settings = not state.show_settings
                    # Toggle particle FX
                    if k == pygame.K_p:
                        state.particle_fx = not state.particle_fx
                        state._p_prev = state.particle_fx
                    # Toggle FPS counter
                    if k == pygame.K_f:
                        state.show_fps = not state.show_fps
                        state._f_prev = state.show_fps
                    # Toggle debug mode
                    if k == pygame.K_d:
                        state.debug_mode = not state.debug_mode
                        state._d_prev = state.debug_mode
                    
                    if state.mode == "player":
                        if k in (pygame.K_UP, pygame.K_w): pmove(-1, 0)
                        if k in (pygame.K_DOWN, pygame.K_s): pmove(1, 0)
                        if k in (pygame.K_LEFT, pygame.K_a): pmove(0, -1)
                        if k in (pygame.K_RIGHT, pygame.K_d): pmove(0, 1)
                        if k == pygame.K_SPACE: pmove(0, 0)
                        if k == pygame.K_h: do_hint()
                        for ti in range(state.T):
                            if k == getattr(pygame, f"K_{ti}", None):
                                # Smooth transition to new time slice
                                if state.view_t != ti:
                                    state.target_view_t = ti
                                    state.view_transition = 1.0
                    elif state.mode == "ai":
                        if k == pygame.K_a: launch_single()
                    elif state.mode == "multi":
                        if k in (pygame.K_a, pygame.K_m): launch_multi()

                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # t-pill clicks with smooth transition
                    pill_x = W - state.T*46 - 8
                    for ti in range(state.T):
                        if pill_x+ti*46 <= mx_g <= pill_x+ti*46+40 and 24 <= my_g <= 46:
                            if state.view_t != ti:
                                state.target_view_t = ti
                                state.view_transition = 1.0
                    # Settings panel click detection
                    if state.show_settings:
                        pw, ph = 340, 240
                        px, py = (W-pw)//2, (H-ph)//2 - 20
                        # Close if clicked outside
                        if not (px <= mx_g <= px+pw and py <= my_g <= py+ph):
                            state.show_settings = False
                        else:
                            # Toggle options
                            options_y = py + 45
                            for i, (label, enabled, key, desc) in enumerate([
                                ("Show Hints", state.show_hint, "h", ""),
                                ("Particle FX", state.particle_fx, "p", ""),
                                ("Show FPS", state.show_fps, "f", ""),
                                ("Debug Mode", state.debug_mode, "d", ""),
                            ]):
                                y_pos = options_y + i * 36
                                switch_x = px + W - 70 - 180  # Approximate
                                if switch_x <= mx_g <= switch_x+50 and y_pos+4 <= my_g <= y_pos+26:
                                    if key == "h":
                                        state.show_hint = not state.show_hint
                                        state._h_prev = state.show_hint
                                    elif key == "p":
                                        state.particle_fx = not state.particle_fx
                                        state._p_prev = state.particle_fx
                                    elif key == "f":
                                        state.show_fps = not state.show_fps
                                        state._f_prev = state.show_fps
                                    elif key == "d":
                                        state.debug_mode = not state.debug_mode
                                        state._d_prev = state.debug_mode
                    # player maze click
                    elif state.mode == "player" and not state.won:
                        maze_x0 = SIDEBAR_W + 4
                        mah2 = H - HUD_H - BOT_H
                        maze_w = W - SIDEBAR_W - 8
                        cell2 = max(18, min(mah2//state.n, maze_w//state.n))
                        ox2 = maze_x0 + (maze_w - cell2*state.n)//2
                        oy2 = HUD_H + (mah2 - cell2*state.n)//2
                        cc2 = (mx_g - ox2) // cell2
                        cr2 = (my_g - oy2) // cell2
                        if 0 <= cr2 < state.n and 0 <= cc2 < state.n:
                            dr3 = cr2 - state.pr
                            dc3 = cc2 - state.pc
                            if abs(dr3) + abs(dc3) == 1:
                                pmove(int(math.copysign(1, dr3)) if dr3 else 0,
                                      int(math.copysign(1, dc3)) if dc3 else 0)
                            elif dr3 == dc3 == 0:
                                pmove(0, 0)

        # hover detection for title
        if cur_scr == "title":
            hover_id = ""
            for hid, (hx, hy, hw, hh2) in title_hit_rects.items():
                if hx <= mx_g <= hx+hw and hy <= my_g <= hy+hh2:
                    hover_id = hid
                    break

        # AI tick with enhanced timing
        if cur_scr == "game" and state.ai_running and ai_gen:
            ph = state.ma_phase
            tick = (SCOUT_MS if ph in ("", "scout", "gossip", "negotiate")
                   else EXEC_MS if ph == "execute" else SOLVE_MS)
            ai_accum += dt_ms
            if ai_accum >= tick:
                ai_accum = 0
                try:
                    next(ai_gen)
                except StopIteration:
                    state.ai_running = False
                    ai_gen = None

        # Message timer with fade
        if state.msg_timer > 0:
            state.msg_timer -= 1
        if state.msg_timer == 0 and state.msg and not state.won:
            state.msg = ""

        # Smooth time slice transition
        if state.view_transition > 0:
            state.view_transition -= 0.18
            if state.view_transition <= 0:
                state.view_transition = 0
                state.view_t = state.target_view_t if state.target_view_t is not None else state.view_t
            else:
                # Smooth interpolate with easing
                progress = 1 - state.view_transition
                eased = progress * progress * (3 - 2*progress)  # Smoothstep
                if state.target_view_t is not None:
                    state.view_t = int(state.view_t + (state.target_view_t - state.view_t) * eased)

        # Screen shake decay
        if state.shake_timer > 0:
            shake_offset, state.shake_timer = apply_screen_shake(shake_offset, 4, state.shake_timer)
        else:
            shake_offset = (0, 0)

        # Update particle FX toggle animation state
        state._h_prev = state.show_hint
        state._p_prev = state.particle_fx
        state._f_prev = state.show_fps
        state._d_prev = state.debug_mode

        # ── render ─────────────────────────────────────────────────────────
        # Apply screen shake to entire render
        render_surf = pygame.Surface((W, H))
        
        if cur_scr == "title":
            title_hit_rects = draw_title(render_surf, W, H, sel_diff, sel_mode, hover_id, frame)
            # Draw settings panel over title
            draw_settings_panel(render_surf, state, W, H, frame)
        else:
            render_surf.fill(C["bg"])
            # layout
            mah = H - HUD_H - BOT_H
            maze_x0 = SIDEBAR_W + 4
            maze_w = W - SIDEBAR_W - 8
            cell = max(18, min(mah//state.n, maze_w//state.n))
            ox = maze_x0 + (maze_w - cell*state.n)//2
            oy = HUD_H + (mah - cell*state.n)//2

            # sidebar with animation
            drect_animated(render_surf, C["panel"], (0, HUD_H, SIDEBAR_W, mah), r=0,
                        border=1, bcol=C["border"], frame=frame)
            draw_legend(render_surf, 4, HUD_H+6, SIDEBAR_W-8, frame)
            leg_h = len(LEGEND_ITEMS)*22 + 18
            ctrl_y = HUD_H + leg_h + 14
            draw_controls_panel(render_surf, 4, ctrl_y, SIDEBAR_W-8, state.mode, frame)
            ctrl_rows = {"player": 6, "ai": 4, "multi": 4}
            ctrl_h = ctrl_rows.get(state.mode, 4)*20 + 20
            if state.mode == "multi" and state.ma_phase:
                draw_robot_panel(render_surf, 4, ctrl_y+ctrl_h+8, SIDEBAR_W-8, state, frame)

            draw_hud(render_surf, state, W, frame)
            draw_maze(render_surf, state, ox, oy, cell, frame)
            draw_statusbar(render_surf, state, W, H, frame)

            # log panel
            if state.ma_log:
                log_y = oy + cell*state.n + 4
                log_w = W - SIDEBAR_W - 10
                if H - log_y - BOT_H > 40:
                    draw_log_panel(render_surf, state, maze_x0, log_y, log_w, frame)

            # idle prompt with animation
            if not state.ai_running and not state.won:
                prompt = {"ai": "Press  [A]  to run AI solver ✨",
                        "multi": "Press  [A]  to start multi-agent race 🏁"}.get(state.mode, "")
                if prompt:
                    pw2 = F_HEAD.size(prompt)[0] + 28
                    px2 = ox + (cell*state.n - pw2)//2
                    py2 = oy + cell*state.n//2 - 18
                    drect_animated(render_surf, C["panel2"], (px2, py2, pw2, 36), r=8,
                                border=1, bcol=C["accent"], pulse=True, frame=frame)
                    dtext(render_surf, prompt, F_HEAD, C["accent"], px2+pw2//2, py2+18, "center", pulse=True, frame=frame)

            draw_hint(render_surf, state, W, H, frame)
            draw_win(render_surf, state, W, H, frame)
            # Draw settings panel over game
            draw_settings_panel(render_surf, state, W, H, frame)

            # FPS counter (toggle with F)
            if state.show_fps:
                fps_text = f"FPS: {int(clock.get_fps())}"
                dtext(render_surf, fps_text, F_SM, C["text3"], 10, H-20)
            
            # Debug info
            if state.debug_mode:
                debug_info = [
                    f"View T: {state.view_t}/{state.T}",
                    f"Transition: {state.view_transition:.2f}",
                    f"Particles: {len(state.particles)}",
                ]
                for i, info in enumerate(debug_info):
                    dtext(render_surf, info, F_SM, C["text3"], 10, 20+i*16)

        # Blit with shake offset
        screen.blit(render_surf, shake_offset)
        pygame.display.flip()


if __name__ == "__main__":
    main()