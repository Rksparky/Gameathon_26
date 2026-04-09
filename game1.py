"""
Temporal Maze — Multi-Agent Negotiation Edition  (UI v2)
=========================================================
pip install pygame
python temporal_maze.py
"""

import pygame, sys, math, random, heapq, textwrap
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple

# ── palette ────────────────────────────────────────────────────────────────────
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

# ── maze logic ─────────────────────────────────────────────────────────────────
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


# ── state ──────────────────────────────────────────────────────────────────────
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
    anim_tick:int=0   # global frame counter for animations


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


# ── draw primitives ────────────────────────────────────────────────────────────
def drect(surf, color, rect, r=6, a=255, border=0, bcol=None):
    x,y,w,h = rect
    if a<255:
        ss=pygame.Surface((w,h),pygame.SRCALPHA)
        pygame.draw.rect(ss,(*color[:3],a),(0,0,w,h),border_radius=r)
        surf.blit(ss,(x,y))
    else:
        pygame.draw.rect(surf,color,rect,border_radius=r)
    if border and bcol:
        pygame.draw.rect(surf,bcol,rect,border,border_radius=r)


def dtext(surf, txt, fnt, color, x, y, anchor="topleft", shadow=False):
    if shadow:
        img=fnt.render(str(txt),True,(0,0,0))
        rc=img.get_rect(**{anchor:(x+1,y+1)})
        surf.blit(img,rc)
    img=fnt.render(str(txt),True,color)
    rc=img.get_rect(**{anchor:(x,y)})
    surf.blit(img,rc)
    return rc


def tri(surf, color, cx, cy, sz, lbl="", fnt=None):
    h=sz*0.86
    pts=[(int(cx),int(cy-h*0.56)),(int(cx+sz*0.46),int(cy+h*0.40)),(int(cx-sz*0.46),int(cy+h*0.40))]
    pygame.draw.polygon(surf,color,pts)
    # outline
    pygame.draw.polygon(surf,(0,0,0),pts,1)
    if lbl and fnt:
        img=fnt.render(lbl,True,(20,20,20))
        surf.blit(img,img.get_rect(center=(int(cx),int(cy+h*0.08))))


def draw_key_badge(surf, key_str, x, y):
    """Draw a keyboard key badge like [SPACE]"""
    w = F_SM.size(key_str)[0] + 10
    drect(surf, C["panel2"], (x,y,w,18), r=4, border=1, bcol=C["border2"])
    dtext(surf, key_str, F_SM, C["text2"], x+w//2, y+9, "center")
    return w


# ── legend strip ───────────────────────────────────────────────────────────────
LEGEND_ITEMS = [
    (C["cell_open"],  None,  "Open cell"),
    (C["cell_wall"],  None,  "Permanent wall"),
    (C["cell_temp"],  None,  "Time wall (blocked NOW)"),
    (C["cell_tint"],  None,  "Changes over time"),
    (C["cell_path"],  None,  "AI solution path"),
    (C["cell_start"], None,  "Start (S)"),
    (C["cell_exit"],  None,  "Exit (E)"),
]

def draw_legend(surf, x, y, W_panel):
    """Draw the colour legend in a sidebar panel."""
    drect(surf, C["panel"], (x,y,W_panel,len(LEGEND_ITEMS)*22+14), r=8,
          border=1, bcol=C["border"])
    dtext(surf,"Legend", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for i,(col,_,label) in enumerate(LEGEND_ITEMS):
        ry=y+18+i*22
        drect(surf, col, (x+8, ry+3, 14, 14), r=3)
        dtext(surf, label, F_SM, C["text3"], x+26, ry+4)


def draw_controls_panel(surf, x, y, W_panel, mode):
    """Draw mode-specific control reference."""
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
    drect(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"])
    dtext(surf,"Controls", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for i,(action,keys) in enumerate(rows):
        ry=y+20+i*20
        dtext(surf, action+":", F_SM, C["text3"], x+8, ry)
        dtext(surf, keys,       F_SM, C["accent"],x+W_panel-8, ry, "topright")


def draw_robot_panel(surf, x, y, W_panel, s:GS):
    """Draw robot status panel for multi-agent mode."""
    ph = NUM_R*38+20
    drect(surf, C["panel"], (x,y,W_panel,ph), r=8, border=1, bcol=C["border"])
    dtext(surf,"Robots", F_UI, C["text2"], x+W_panel//2, y+6, "center")
    for rid in range(NUM_R):
        ry=y+20+rid*38
        col=RCOLS[rid]
        # robot icon
        pygame.draw.circle(surf, col, (x+18,ry+14), 8)
        pygame.draw.circle(surf, (0,0,0), (x+18,ry+14), 8, 1)
        fnt=pygame.font.SysFont("monospace",9,bold=True)
        img=fnt.render(str(rid),True,(20,20,20))
        surf.blit(img,img.get_rect(center=(x+18,ry+14)))
        # name + status
        dtext(surf, f"R{rid} — {RNAMES[rid]}", F_SM, col, x+32, ry+2)
        if s.ma_done[rid]:
            status = "FINISHED" if rid!=s.ma_winner else "WINNER!"
            scol=C["green"] if rid==s.ma_winner else C["text3"]
        elif s.ma_phase=="execute" and rid<len(s.ma_paths) and s.ma_paths[rid]:
            pct=min(100,int(s.ma_step/max(1,len(s.ma_paths[rid]))*100))
            status=f"Running  {pct}%"
            scol=C["text2"]
        elif s.ma_phase in("negotiate",):
            nsteps=len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0
            status=f"Plan: {nsteps} steps" if nsteps else "No path"
            scol=C["text2"]
        else:
            status="Waiting"
            scol=C["text3"]
        dtext(surf, status, F_SM, scol, x+32, ry+17)
        # priority badge
        prio=["HIGH","MED","LOW"][rid]
        pc=C["green"] if rid==0 else (C["warn"] if rid==1 else C["text3"])
        dtext(surf, f"prio:{prio}", F_SM, pc, x+W_panel-8, ry+2, "topright")


# ── maze renderer ──────────────────────────────────────────────────────────────
def draw_maze(surf, s:GS, ox, oy, cell):
    n,T=s.n,s.T; g,tm=s.grid,s.temporal; vt=s.view_t
    ms=pygame.Surface((n*cell,n*cell),pygame.SRCALPHA)

    for r in range(n):
        for c in range(n):
            x,y=c*cell,r*cell
            blk=walled(g,tm,n,T,r,c,vt)
            op=r*n+c in s.path_set
            if blk:
                fill=C["cell_temp"] if not g[r][c] else C["cell_wall"]
            else:
                fill=C["cell_path"] if op else C["cell_open"]
            pygame.draw.rect(ms,fill,(x+1,y+1,cell-2,cell-2),border_radius=2)
            if not blk and tm[r][c]:
                tint=pygame.Surface((cell-2,cell-2),pygame.SRCALPHA)
                tint.fill((*C["cell_tint"],52))
                ms.blit(tint,(x+1,y+1))
            if r==0 and c==0:
                pygame.draw.rect(ms,C["cell_start"],(x+2,y+2,cell-4,cell-4),border_radius=2)
            if r==n-1 and c==n-1:
                pygame.draw.rect(ms,C["cell_exit"],(x+2,y+2,cell-4,cell-4),border_radius=2)

    for pr2,pc2 in s.ma_paradox:
        pf=pygame.Surface((cell-2,cell-2),pygame.SRCALPHA)
        pf.fill((*C["paradox"],140))
        ms.blit(pf,(pc2*cell+1,pr2*cell+1))

    for i in range(n+1):
        pygame.draw.line(ms,(*C["bg"],60),(i*cell,0),(i*cell,n*cell))
        pygame.draw.line(ms,(*C["bg"],60),(0,i*cell),(n*cell,i*cell))

    lf=pygame.font.SysFont("monospace",max(8,cell//4),bold=True)
    dtext(ms,"S",lf,(255,255,255),cell//2,cell//2,"center")
    dtext(ms,"E",lf,(255,255,255),(n-1)*cell+cell//2,(n-1)*cell+cell//2,"center")
    surf.blit(ms,(ox,oy))

    af=pygame.font.SysFont("monospace",max(6,cell//5),bold=True)

    for tr,tc in s.trail:
        ts=pygame.Surface((cell-4,cell-4),pygame.SRCALPHA)
        ts.fill((*C["r0"],32)); surf.blit(ts,(ox+tc*cell+2,oy+tr*cell+2))

    if s.mode=="player" and not s.won:
        tri(surf,C["r0"],ox+s.pc*cell+cell//2,oy+s.pr*cell+cell//2,
            max(8,int(cell*0.68)),"P",af)

    if s.solver_pos:
        tri(surf,C["r0"],ox+s.solver_pos[1]*cell+cell//2,
            oy+s.solver_pos[0]*cell+cell//2,max(8,int(cell*0.68)),"A",af)

    for sr2,sc2,st2,alpha in s.scout_pos:
        if st2!=vt: continue
        cx2=ox+sc2*cell+cell//2; cy2=oy+sr2*cell+cell//2
        rad=max(4,int(cell*0.22))
        ss2=pygame.Surface((rad*2+2,rad*2+2),pygame.SRCALPHA)
        pygame.draw.circle(ss2,(*C["r1"],int(alpha*255)),(rad+1,rad+1),rad)
        surf.blit(ss2,(cx2-rad-1,cy2-rad-1))

    if s.ma_phase:
        for rid in range(NUM_R):
            col=RCOLS[rid]
            for tr2,tc2 in s.ma_trails[rid]:
                ts2=pygame.Surface((cell-4,cell-4),pygame.SRCALPHA)
                ts2.fill((*col,28)); surf.blit(ts2,(ox+tc2*cell+2,oy+tr2*cell+2))
            if rid<len(s.ma_pos):
                pr3,pc3=s.ma_pos[rid]
                if s.ma_done[rid]:
                    pygame.draw.circle(surf,col,
                        (ox+pc3*cell+cell//2,oy+pr3*cell+cell//2),max(4,cell//5))
                    pygame.draw.circle(surf,(0,0,0),
                        (ox+pc3*cell+cell//2,oy+pr3*cell+cell//2),max(4,cell//5),1)
                else:
                    tri(surf,col,ox+pc3*cell+cell//2,oy+pr3*cell+cell//2,
                        max(8,int(cell*0.65)),str(rid),af)


# ── top HUD bar ────────────────────────────────────────────────────────────────
HUD_H = 52

def draw_hud(surf, s:GS, W):
    drect(surf, C["panel"], (0,0,W,HUD_H), r=0)
    pygame.draw.line(surf, C["border"], (0,HUD_H),(W,HUD_H))

    # left: stats or phase
    if s.mode=="player":
        stats=[("STEPS",str(s.steps)),("WAITS",str(s.waits)),
               (f"TIME","t="+str(s.view_t)),("PAR",str(s.par))]
        x=12
        for lbl,val in stats:
            drect(surf,C["panel2"],(x,8,56,36),r=6,border=1,bcol=C["border"])
            dtext(surf,lbl,F_SM,C["text3"],x+28,12,"center")
            dtext(surf,val,F_UI,C["text"],x+28,26,"center",shadow=True)
            x+=64
    else:
        # phase indicator
        PHASE_INFO={
            "scout":    (C["r1"],   "SCOUT",    "Mapping time slices"),
            "gossip":   (C["warn"], "GOSSIP",   "Sharing maps"),
            "negotiate":(C["r2"],   "NEGOTIATE","Planning paths"),
            "execute":  (C["green"],"EXECUTE",  "Racing to exit"),
            "done":     (C["green"],"DONE",     "Race complete"),
            "":         (C["text3"],"READY",    "Press A to start"),
        }
        ph=s.ma_phase; col,name,desc=PHASE_INFO.get(ph,PHASE_INFO[""])
        drect(surf,C["panel2"],(8,6,140,40),r=8,border=1,bcol=col)
        dtext(surf,name,F_HEAD,col,78,14,"center",shadow=True)
        dtext(surf,desc,F_SM,C["text3"],78,32,"center")
        # winner badge
        if s.ma_winner>=0:
            wc=RCOLS[s.ma_winner]
            drect(surf,C["win_bg"],(155,8,160,36),r=8,border=1,bcol=wc)
            dtext(surf,f"WINNER: R{s.ma_winner} ({RNAMES[s.ma_winner]})",
                  F_UI,wc,235,26,"center",shadow=True)

    # right: t-pills
    px=W - s.T*46 - 8
    dtext(surf,"TIME SLICE",F_SM,C["text3"],px-4,10,"topright")
    for t in range(s.T):
        on=(t==s.view_t)
        bg=C["accent"] if on else C["pill_off"]
        bc=C["accent"] if on else C["border"]
        drect(surf,bg,(px,24,40,22),r=11,border=1,bcol=bc)
        dtext(surf,f"t={t}",F_SM,C["text"] if on else C["text3"],px+20,35,"center")
        px+=46

    # centre: diff badge
    dtext(surf,f"{s.diff}  {s.n}×{s.n}  T={s.T}",F_SM,C["text3"],W//2,10,"center")
    dtext(surf,f"Seed #{s.seed & 0xFFFF:04X}",F_SM,C["text3"],W//2,26,"center")


# ── status bar (bottom) ────────────────────────────────────────────────────────
BOT_H = 28

def draw_statusbar(surf, s:GS, W, H):
    y=H-BOT_H
    drect(surf,C["panel"],(0,y,W,BOT_H),r=0)
    pygame.draw.line(surf,C["border"],(0,y),(W,y))

    if s.msg and s.msg_timer>0:
        dtext(surf, s.msg, F_SM, s.msg_col, W//2, y+7, "center")
    else:
        if s.mode=="player":
            parts=["[↑↓←→/WASD] Move","[SPACE] Wait","[H] Hint","[R] Restart","[ESC] Menu"]
        elif s.mode=="ai":
            parts=["[A] Run AI","[R] Reset","[ESC] Menu"]
        else:
            parts=["[A] Run race","[R] Reset","[ESC] Menu"]
        hint=" · ".join(parts)
        dtext(surf, hint, F_SM, C["text3"], W//2, y+7, "center")


# ── phase log panel ────────────────────────────────────────────────────────────
def draw_log_panel(surf, s:GS, x, y, w):
    if not s.ma_log: return
    lines=s.ma_log[-7:]
    ph=len(lines)*16+14
    drect(surf,C["panel"],(x,y,w,ph),r=8,border=1,bcol=C["border"])
    dtext(surf,"Event Log",F_SM,C["text3"],x+w//2,y+4,"center")
    for i,ln in enumerate(lines):
        col=C["green"] if "WINNER" in ln else (C["paradox"] if "PARADOX" in ln
            else (C["text2"] if ln.startswith("Phase") else C["text3"]))
        # truncate to fit
        max_chars=w//6
        if len(ln)>max_chars: ln=ln[:max_chars-2]+".."
        dtext(surf,ln,F_SM,col,x+6,y+14+i*16)


# ── hint overlay ───────────────────────────────────────────────────────────────
def draw_hint(surf, s:GS, W, H):
    if not s.show_hint or not s.hint_txt: return
    lines=s.hint_txt.split("\n")
    pw=min(W-60,540); ph=len(lines)*20+50
    px=(W-pw)//2; py=(H-ph)//2
    drect(surf,(0,0,0),(0,0,W,H),a=120)
    drect(surf,C["panel"],(px,py,pw,ph),r=12,border=2,bcol=C["accent"])
    dtext(surf,"HINT",F_HEAD,C["accent"],px+pw//2,py+10,"center")
    pygame.draw.line(surf,C["border"],(px+12,py+34),(px+pw-12,py+34))
    for i,ln in enumerate(lines):
        dtext(surf,ln,F_UI,C["text"],px+16,py+42+i*20)
    dtext(surf,"Press H to close",F_SM,C["text3"],px+pw//2,py+ph-16,"center")


# ── win / race-over overlay ────────────────────────────────────────────────────
def draw_win(surf, s:GS, W, H):
    if not s.won: return
    drect(surf,(0,0,0),(0,0,W,H),a=160)
    pw=min(W-40,520); ph=220 if s.mode=="player" else 260
    px=(W-pw)//2; py=(H-ph)//2
    drect(surf,C["win_bg"],(px,py,pw,ph),r=16,border=2,bcol=C["win_border"])

    if s.mode=="player":
        eff=round(s.par/max(s.steps,1)*100)
        grade="S" if eff>=100 else ("A" if eff>=85 else ("B" if eff>=70 else "C"))
        gcol={
            "S":(255,215,0),"A":C["green"],"B":C["warn"],"C":C["err"]
        }[grade]
        dtext(surf,"EXIT REACHED!",F_TITLE,C["win_border"],px+pw//2,py+18,"center",shadow=True)
        pygame.draw.line(surf,C["border"],(px+20,py+54),(px+pw-20,py+54))
        # stat boxes
        stat_data=[("STEPS",str(s.steps)),("WAITS",str(s.waits)),
                   ("OPTIMAL",str(s.par)),("EFF",f"{eff}%")]
        bw=(pw-40)//4
        for i,(lbl,val) in enumerate(stat_data):
            bx=px+20+i*(bw+4)
            drect(surf,C["panel2"],(bx,py+64,bw,52),r=8,border=1,bcol=C["border2"])
            dtext(surf,lbl,F_SM,C["text3"],bx+bw//2,py+70,"center")
            dtext(surf,val,F_HEAD,C["text"],bx+bw//2,py+86,"center",shadow=True)
        # grade
        drect(surf,gcol,(px+pw//2-30,py+130,60,50),r=10,border=2,bcol=gcol)
        dtext(surf,grade,pygame.font.SysFont("segoeui",36,bold=True),(20,20,20),
              px+pw//2,py+155,"center")
        dtext(surf,"GRADE",F_SM,C["text3"],px+pw//2,py+132,"center")
        # buttons hint
        dtext(surf,"[N] Next Level    [R] Retry    [ESC] Menu",
              F_UI,C["text3"],px+pw//2,py+196,"center")
    else:
        w=s.ma_winner
        title="RACE OVER!" if w>=0 else "RACE COMPLETE"
        dtext(surf,title,F_TITLE,C["win_border"],px+pw//2,py+18,"center",shadow=True)
        pygame.draw.line(surf,C["border"],(px+20,py+54),(px+pw-20,py+54))
        if w>=0:
            wc=RCOLS[w]
            drect(surf,C["panel2"],(px+pw//2-110,py+64,220,60),r=10,border=2,bcol=wc)
            pygame.draw.circle(surf,wc,(px+pw//2-70,py+94),18)
            dtext(surf,str(w),F_HEAD,(20,20,20),px+pw//2-70,py+94,"center")
            dtext(surf,f"ROBOT {w} WINS!",F_HEAD,wc,px+pw//2+10,py+80,"center",shadow=True)
            dtext(surf,RNAMES[w]+" team",F_SM,C["text3"],px+pw//2+10,py+104,"center")
        # all robots summary
        for rid in range(NUM_R):
            ry=py+140+rid*26
            col=RCOLS[rid]
            pygame.draw.circle(surf,col,(px+60,ry+10),8)
            status="WINNER!" if rid==w else ("Finished" if s.ma_done[rid] else "DNF")
            scol=C["green"] if rid==w else C["text2"]
            plen=len(s.ma_paths[rid]) if rid<len(s.ma_paths) and s.ma_paths[rid] else 0
            dtext(surf,f"R{rid} {RNAMES[rid]}:",F_UI,col,px+80,ry+3)
            dtext(surf,f"{status} · {plen} steps",F_SM,scol,px+210,ry+5)
        dtext(surf,"[N] Next    [R] Retry    [ESC] Menu",
              F_UI,C["text3"],px+pw//2,py+ph-22,"center")


# ── TITLE SCREEN ───────────────────────────────────────────────────────────────
def draw_title(surf, W, H, sel_diff, sel_mode, hover, frame):
    surf.fill(C["bg"])

    # animated particle dots (simple)
    rng2=random.Random(42)
    for _ in range(18):
        px2=int(rng2.random()*W)
        py2=int(rng2.random()*H*0.55)
        r2=rng2.randint(1,3)
        alpha=int(80+40*math.sin(frame*0.03+rng2.random()*6))
        ss=pygame.Surface((r2*2,r2*2),pygame.SRCALPHA)
        pygame.draw.circle(ss,(*C["accent"],alpha),(r2,r2),r2)
        surf.blit(ss,(px2-r2,py2-r2))

    # title
    dtext(surf,"TEMPORAL",F_TITLE,C["accent"],W//2,28,"center",shadow=True)
    dtext(surf,"MAZE",F_TITLE,C["text"],W//2,64,"center",shadow=True)
    dtext(surf,"Multi-Agent Negotiation Edition",F_UI,C["text3"],W//2,102,"center")

    pygame.draw.line(surf,C["border"],(W//2-160,118),(W//2+160,118))

    # ── HOW TO PLAY cards ──────────────────────────────────────────────────
    tw_cards=[ # (icon_color, title, body)
        (C["r0"],  "Move Through Space",
         "Use Arrow keys or WASD\nto navigate the grid.\nReach the RED exit cell."),
        (C["cell_temp"], "Time Walls",
         "Amber cells are blocked\nONLY at certain time steps.\nThey open as time advances!"),
        (C["accent"], "Wait = Time Travel",
         "Press SPACE to stay in\nplace. This advances time\nby 1 — opening new paths."),
        (C["r2"],  "Multi-Agent Race",
         "3 robots Scout, Gossip,\nNegotiate paths, then Race\nto the exit simultaneously."),
    ]
    cw2=int((W-60)//4); ch2=108
    for i,(icol,title2,body) in enumerate(tw_cards):
        cx2=20+i*(cw2+6); cy2=130
        on=(hover==f"card{i}")
        drect(surf,C["panel2"] if on else C["panel"],(cx2,cy2,cw2,ch2),
              r=10,border=1,bcol=C["accent"] if on else C["border"])
        # colour bar top
        drect(surf,icol,(cx2,cy2,cw2,5),r=3)
        dtext(surf,title2,F_UI,C["text"],cx2+cw2//2,cy2+14,"center",shadow=True)
        pygame.draw.line(surf,C["border"],(cx2+10,cy2+30),(cx2+cw2-10,cy2+30))
        for j,line in enumerate(body.split("\n")):
            dtext(surf,line,F_SM,C["text3"],cx2+cw2//2,cy2+36+j*17,"center")

    # ── DIFFICULTY selector ────────────────────────────────────────────────
    diffs=list(DIFFS.keys())
    dtext(surf,"SELECT DIFFICULTY",F_UI,C["text3"],W//2,248,"center")
    pygame.draw.line(surf,C["border"],(W//2-100,264),(W//2+100,264))

    dcw=int((W-40)//4); dch=72
    for i,d in enumerate(diffs):
        dcx=20+i*(dcw+5); dcy=270
        on=(d==sel_diff)
        bg=C["accent2"] if on else C["panel"]
        bc=C["accent"] if on else C["border"]
        drect(surf,bg,(dcx,dcy,dcw,dch),r=10,border=2 if on else 1,bcol=bc)
        info=DIFFS[d]
        dtext(surf,d,F_HEAD,C["text"] if on else C["text2"],dcx+dcw//2,dcy+8,"center",shadow=on)
        dtext(surf,f"{info['n']}×{info['n']}",F_UI,C["accent"] if on else C["text3"],
              dcx+dcw//2,dcy+28,"center")
        dtext(surf,f"{info['T']} time slices",F_SM,C["text3"],dcx+dcw//2,dcy+45,"center")
        dtext(surf,f"{int(info['tw']*100)}% walls",F_SM,C["text3"],dcx+dcw//2,dcy+59,"center")

    # ── MODE selector ─────────────────────────────────────────────────────
    dtext(surf,"SELECT MODE",F_UI,C["text3"],W//2,352,"center")
    pygame.draw.line(surf,C["border"],(W//2-100,368),(W//2+100,368))

    modes=[
        ("player","PLAY YOURSELF","Control the agent\nwith keyboard","Arrow/WASD + Space"),
        ("ai","WATCH AI","Single A* solver\nanimates the solution","Press A to run"),
        ("multi","MULTI-AGENT RACE","3 robots Scout→Gossip\n→Negotiate→Race","Press A to start"),
    ]
    mw=int((W-40)//3); mh=86
    for i,(m,mname,mdesc,mhint) in enumerate(modes):
        mcx=20+i*(mw+5); mcy=374
        on=(m==sel_mode)
        bg=C["accent2"] if on else C["panel"]
        bc=C["accent"] if on else C["border"]
        drect(surf,bg,(mcx,mcy,mw,mh),r=10,border=2 if on else 1,bcol=bc)
        dtext(surf,mname,F_HEAD,C["text"] if on else C["text2"],mcx+mw//2,mcy+8,"center",shadow=on)
        for j,line in enumerate(mdesc.split("\n")):
            dtext(surf,line,F_SM,C["text3"],mcx+mw//2,mcy+28+j*16,"center")
        dtext(surf,mhint,F_SM,C["accent"] if on else C["text3"],
              mcx+mw//2,mcy+mh-16,"center")

    # ── START button ───────────────────────────────────────────────────────
    bw2=200; bh2=46; bx2=(W-bw2)//2; by2=474
    on2=(hover=="start")
    drect(surf,C["accent"] if on2 else C["accent2"],(bx2,by2,bw2,bh2),r=12,
          border=2,bcol=C["accent"])
    dtext(surf,"START GAME",F_HEAD,(255,255,255),bx2+bw2//2,by2+bh2//2,"center",shadow=True)
    dtext(surf,"or press  Enter",F_SM,C["text3"],W//2,by2+bh2+8,"center")

    # ── keyboard shortcuts ─────────────────────────────────────────────────
    shortcuts=[
        ("Left / Right","Select difficulty"),
        ("Tab","Cycle mode"),
        ("Enter","Start game"),
    ]
    sy=540
    for k2,v2 in shortcuts:
        kw=F_SM.size(f"[{k2}]")[0]+10
        kx=W//2-180
        drect(surf,C["panel2"],(kx,sy,kw,18),r=4,border=1,bcol=C["border2"])
        dtext(surf,f"[{k2}]",F_SM,C["accent"],kx+kw//2,sy+9,"center")
        dtext(surf,v2,F_SM,C["text3"],kx+kw+8,sy+9,"midleft")
        sy+=22

    # ── return rects for hit-testing ───────────────────────────────────────
    hit_rects={}
    for i,d in enumerate(diffs):
        hit_rects[f"diff_{d}"]=(20+i*(dcw+5),270,dcw,dch)
    for i,(m,*_) in enumerate(modes):
        hit_rects[f"mode_{m}"]=(20+i*(mw+5),374,mw,mh)
    hit_rects["start"]=(bx2,by2,bw2,bh2)
    return hit_rects


# ── AI generators ──────────────────────────────────────────────────────────────
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
    s.msg=f"AI found path: {len(path)} steps, {tw2} time waits"
    s.msg_col=C["green"]; s.msg_timer=300
    for r,c,t in path:
        s.solver_pos=(r,c); s.view_t=t; yield "solve"
    s.won=True; s.solver_pos=(n-1,n-1)


def gen_multi(s:GS):
    n,T=s.n,s.T; g,tm=s.grid,s.temporal

    s.ma_phase="scout"
    s.ma_log=["Phase 1 — Scout: robots mapping time slices..."]
    slices_per=max(1,T//NUM_R)
    scout_maps={rid:set() for rid in range(NUM_R)}

    for t in range(T):
        owner=min(t//slices_per,NUM_R-1)
        for r in range(n):
            for c in range(n):
                s.scout_pos=[(a,b,d,max(0,e-0.06)) for a,b,d,e in s.scout_pos if e>0.02]
                s.scout_pos.append((r,c,t,1.0))
                if not walled(g,tm,n,T,r,c,t): scout_maps[owner].add((r,c,t))
                s.view_t=t; yield "scout"

    s.scout_pos=[]
    total2=sum(len(v) for v in scout_maps.values())
    s.ma_log.append(f"Scouts found {total2} open (r,c,t) cells total.")
    yield "scout_done"

    s.ma_phase="gossip"
    s.ma_log.append("Phase 2 — Gossip: broadcasting maps to all robots...")
    all_open: set=set()
    for v in scout_maps.values(): all_open|=v
    for rid in range(NUM_R): scout_maps[rid]=all_open
    s.ma_log.append(f"Gossip complete — each robot knows {len(all_open)} open cells.")
    yield "gossip"

    s.ma_phase="negotiate"
    s.ma_log.append("Phase 3 — Negotiate: priority planning (R0>R1>R2)...")
    paths,reserved=negotiate(g,tm,n,T)
    s.ma_paths=paths; s.ma_reserved=reserved
    for rid,path in enumerate(paths):
        if path:
            wt=sum(1 for i in range(1,len(path)) if path[i][:2]==path[i-1][:2])
            avoid=f"avoids R{',R'.join(str(j) for j in range(rid))}" if rid>0 else "conflict-free"
            s.ma_log.append(f"  R{rid}: {len(path)} steps, {wt} waits — {avoid}")
        else:
            s.ma_log.append(f"  R{rid}: no path — using best-effort")
    yield "negotiate"

    s.ma_phase="execute"
    s.ma_log.append("Phase 4 — Execute: robots racing simultaneously!")
    max_steps=max((len(p) for p in paths if p),default=0)

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
                s.ma_log.append(f"  PARADOX! R{rid} & R{other} collide at ({r},{c}) t={t}")
            occupied[(r,c)]=rid
            if r==n-1 and c==n-1 and not s.ma_done[rid]:
                s.ma_done[rid]=True
                if s.ma_winner<0:
                    s.ma_winner=rid
                    s.ma_log.append(f"  *** R{rid} ({RNAMES[rid]}) reaches exit — WINNER! ***")
        if all(s.ma_done): break
        yield "execute"

    for rid in range(NUM_R):
        if not s.ma_done[rid]: s.ma_done[rid]=True
    s.ma_phase="done"; s.ma_mode=False
    if s.ma_winner<0 and any(s.ma_done):
        s.ma_winner=next(i for i,d in enumerate(s.ma_done) if d)
    s.won=True
    s.ma_log.append(f"Race complete · Winner: R{s.ma_winner} · "
                    f"Paradoxes: {len(s.ma_paradox)}")
    yield "done"


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    global F_TITLE, F_HEAD, F_UI, F_SM, F_MONO

    pygame.init()
    screen=pygame.display.set_mode((960,720),pygame.RESIZABLE)
    pygame.display.set_caption("Temporal Maze — Multi-Agent Negotiation")
    clock=pygame.time.Clock()

    F_TITLE = pygame.font.SysFont("segoeui",  32, bold=True)
    F_HEAD  = pygame.font.SysFont("segoeui",  16, bold=False)
    F_UI    = pygame.font.SysFont("segoeui",  13)
    F_SM    = pygame.font.SysFont("segoeui",  11)
    F_MONO  = pygame.font.SysFont("monospace",11, bold=True)

    SIDEBAR_W = 170
    SCOUT_MS  = 7
    SOLVE_MS  = 85
    EXEC_MS   = 115

    sel_diff="Hard"; sel_mode="player"
    cur_scr="title"
    state=GS()
    ai_gen=None; ai_accum=0.0
    frame=0; hover_id=""
    title_hit_rects={}

    def start():
        nonlocal cur_scr, ai_gen
        cfg=DIFFS[sel_diff]
        state.n=cfg["n"]; state.T=cfg["T"]; state.tw=cfg["tw"]
        state.diff=sel_diff; state.mode=sel_mode
        new_level(state); cur_scr="game"; ai_gen=None

    def smsg(txt, col=None, dur=220):
        state.msg=txt; state.msg_col=col or C["text3"]; state.msg_timer=dur

    def pmove(dr,dc):
        if state.won or state.mode!="player": return
        nr,nc,nt=state.pr+dr,state.pc+dc,(state.pt+1)%state.T
        if walled(state.grid,state.temporal,state.n,state.T,nr,nc,nt):
            if dr==dc==0:
                smsg("Cannot wait here — a wall appears at the next time step!",C["warn"])
            else:
                smsg("Blocked! That cell is a wall at the next time step.",C["err"])
            return
        if dr==dc==0: state.waits+=1
        state.pr,state.pc,state.pt=nr,nc,nt
        state.steps+=1; state.view_t=nt
        state.trail.append((nr,nc))
        if len(state.trail)>20: state.trail.pop(0)
        smsg("")
        if nr==state.n-1 and nc==state.n-1: state.won=True

    def do_hint():
        path=astar(state.grid,state.temporal,state.n,state.T)
        if not path: state.hint_txt="No solution exists from start.\nTry restarting."; state.show_hint=True; return
        twpts=[path[i][2] for i in range(1,len(path)) if path[i][:2]==path[i-1][:2]]
        if twpts:
            state.hint_txt=(
                f"Optimal path: {len(path)} steps with {len(twpts)} time wait(s).\n"
                f"You need to WAIT at time step(s): t={', t='.join(map(str,twpts))}\n\n"
                f"Strategy: navigate toward the blocked cell,\n"
                f"then press SPACE to wait — the wall opens at t+1.\n"
                f"Remember: every move also advances time by 1!")
        else:
            state.hint_txt=(
                f"Optimal path: {len(path)} steps — NO time waits needed!\n"
                f"This is pure spatial navigation.\n"
                f"Tip: look for the open corridor leading toward\n"
                f"the bottom-right exit cell (red).")
        state.show_hint=not state.show_hint

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
        W,H=screen.get_size()
        dt_ms=clock.tick(60); frame+=1

        mx_g,my_g=pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()

            if cur_scr=="title":
                diffs=list(DIFFS.keys())
                if ev.type==pygame.KEYDOWN:
                    if ev.key==pygame.K_RETURN: start()
                    if ev.key==pygame.K_TAB:
                        ml=["player","ai","multi"]; sel_mode=ml[(ml.index(sel_mode)+1)%len(ml)]
                    if ev.key==pygame.K_LEFT:
                        idx=diffs.index(sel_diff); sel_diff=diffs[max(0,idx-1)]
                    if ev.key==pygame.K_RIGHT:
                        idx=diffs.index(sel_diff); sel_diff=diffs[min(len(diffs)-1,idx+1)]
                    if ev.key==pygame.K_q: pygame.quit(); sys.exit()
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    for hid,(hx,hy,hw,hh2) in title_hit_rects.items():
                        if hx<=mx_g<=hx+hw and hy<=my_g<=hy+hh2:
                            if hid=="start": start()
                            elif hid.startswith("diff_"): sel_diff=hid[5:]
                            elif hid.startswith("mode_"): sel_mode=hid[5:]

            else:  # game screen
                if ev.type==pygame.KEYDOWN:
                    k=ev.key
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

                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    # t-pill clicks
                    pill_x=W-state.T*46-8
                    for ti in range(state.T):
                        if pill_x+ti*46<=mx_g<=pill_x+ti*46+40 and 24<=my_g<=46:
                            state.view_t=ti
                    # player maze click
                    if state.mode=="player" and not state.won:
                        maze_x0=SIDEBAR_W+4; mah2=H-HUD_H-BOT_H
                        maze_w=W-SIDEBAR_W-8
                        cell2=max(18,min(mah2//state.n,maze_w//state.n))
                        ox2=maze_x0+(maze_w-cell2*state.n)//2
                        oy2=HUD_H+(mah2-cell2*state.n)//2
                        cc2=(mx_g-ox2)//cell2; cr2=(my_g-oy2)//cell2
                        if 0<=cr2<state.n and 0<=cc2<state.n:
                            dr3=cr2-state.pr; dc3=cc2-state.pc
                            if abs(dr3)+abs(dc3)==1:
                                pmove(int(math.copysign(1,dr3)) if dr3 else 0,
                                      int(math.copysign(1,dc3)) if dc3 else 0)
                            elif dr3==dc3==0: pmove(0,0)

        # hover detection for title
        if cur_scr=="title":
            hover_id=""
            for hid,(hx,hy,hw,hh2) in title_hit_rects.items():
                if hx<=mx_g<=hx+hw and hy<=my_g<=hy+hh2:
                    hover_id=hid; break

        # AI tick
        if cur_scr=="game" and state.ai_running and ai_gen:
            ph=state.ma_phase
            tick=(SCOUT_MS if ph in("","scout","gossip","negotiate")
                  else EXEC_MS if ph=="execute" else SOLVE_MS)
            ai_accum+=dt_ms
            if ai_accum>=tick:
                ai_accum=0
                try: next(ai_gen)
                except StopIteration:
                    state.ai_running=False; ai_gen=None

        if state.msg_timer>0: state.msg_timer-=1
        if state.msg_timer==0 and state.msg and not state.won: state.msg=""

        # ── render ─────────────────────────────────────────────────────────
        if cur_scr=="title":
            title_hit_rects=draw_title(screen,W,H,sel_diff,sel_mode,hover_id,frame)
        else:
            screen.fill(C["bg"])
            # layout
            mah=H-HUD_H-BOT_H
            maze_x0=SIDEBAR_W+4
            maze_w=W-SIDEBAR_W-8
            cell=max(18,min(mah//state.n,maze_w//state.n))
            ox=maze_x0+(maze_w-cell*state.n)//2
            oy=HUD_H+(mah-cell*state.n)//2

            # sidebar
            drect(screen,C["panel"],(0,HUD_H,SIDEBAR_W,mah),r=0,
                  border=1,bcol=C["border"])
            draw_legend(screen,4,HUD_H+6,SIDEBAR_W-8)
            leg_h=len(LEGEND_ITEMS)*22+18
            ctrl_y=HUD_H+leg_h+14
            draw_controls_panel(screen,4,ctrl_y,SIDEBAR_W-8,state.mode)
            ctrl_rows={"player":6,"ai":4,"multi":4}
            ctrl_h=ctrl_rows.get(state.mode,4)*20+20
            if state.mode=="multi" and state.ma_phase:
                draw_robot_panel(screen,4,ctrl_y+ctrl_h+8,SIDEBAR_W-8,state)

            draw_hud(screen,state,W)
            draw_maze(screen,state,ox,oy,cell)
            draw_statusbar(screen,state,W,H)

            # log
            if state.ma_log:
                log_y=oy+cell*state.n+4
                log_w=W-SIDEBAR_W-10
                if H-log_y-BOT_H>40:
                    draw_log_panel(screen,state,maze_x0,log_y,log_w)

            # idle prompt
            if not state.ai_running and not state.won:
                prompt={"ai":"Press  [A]  to run AI solver",
                        "multi":"Press  [A]  to start multi-agent race"}.get(state.mode,"")
                if prompt:
                    pw2=F_HEAD.size(prompt)[0]+24
                    px2=ox+(cell*state.n-pw2)//2; py2=oy+cell*state.n//2-16
                    drect(screen,C["panel2"],(px2,py2,pw2,32),r=8,
                          border=1,bcol=C["accent"])
                    dtext(screen,prompt,F_HEAD,C["accent"],px2+pw2//2,py2+16,"center")

            draw_hint(screen,state,W,H)
            draw_win(screen,state,W,H)

        pygame.display.flip()


if __name__=="__main__":
    main()