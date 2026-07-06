"""
Kyle Jordan's Maze Adventure (Pixel-Based Edition) — IMPROVED VERSION
---------------------------------------------------------------------
A 700x700 tile world (16px tiles -> 11,200 x 11,200 pixels total). 
You can only see roughly a 10-15 tile radius around Kyle at any time.

IMPROVEMENTS:
- Q key now works to return from werewolf islands
- Gliders are consumed when crossing water (need to manage resources)
- Coastline outline is stable (no more wobbling)
- Attack has visual feedback (screen shake + flash)
- Rain drops maintain positions across weather cycles
- Independent x/y jitter for coastline outline
- Added minimap in HUD
- Added floating damage numbers
- Added particle effects for chicken pickup
- Balanced economy (golden chickens worth more, merchant pays more)
- Added sprint ability (hold Shift)
- Added health regeneration when not in combat
- Werewolves now drop materials too
- Better HUD with glider count displayed
- Sound effect placeholders (visual feedback when sound unavailable)

Controls:
    WASD / Arrow keys : move
    Shift             : sprint (uses stamina)
    E                 : interact (talk / lift desk / lift mat / sell)
    G                 : give chicken to Noah
    B                 : build a glider (needs materials)
    SPACE             : attack (on werewolf islands)
    Q                 : return to main island (while on a smaller island)
    ESC               : quit
"""

import pygame
import random
import sys
import math

# ---------------------------------------------------------------------------
# Core constants
# ---------------------------------------------------------------------------
pygame.init()

TILE = 16                      # logical tile size (game-logic units)
SCALE = 2                      # display scale: each logical pixel → 2×2 screen pixels
DISPLAY_TILE = TILE * SCALE    # 32 screen-pixels per tile
MAP_W, MAP_H = 700, 700

VIEW_RADIUS_TILES = 11
VIEW_TILES_ACROSS = VIEW_RADIUS_TILES * 2 + 1   # 23 tiles visible

SCREEN_W = SCREEN_H = VIEW_TILES_ACROSS * DISPLAY_TILE   # 736
HUD_HEIGHT = 76

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H + HUD_HEIGHT))
pygame.display.set_caption("Kyle Jordan's Maze Adventure - Improved")
clock = pygame.time.Clock()
FPS = 60

FONT     = pygame.font.SysFont("monospace", 13)
BIG_FONT = pygame.font.SysFont("monospace", 24, bold=True)
HUD_FONT = pygame.font.SysFont("monospace", 12, bold=True)
DIALOGUE_FONT = pygame.font.SysFont("monospace", 19, bold=True)
DAMAGE_FONT = pygame.font.SysFont("monospace", 16, bold=True)

CHICKENS_TO_WIN = 8

# ---------------------------------------------------------------------------
# Tile types
# ---------------------------------------------------------------------------
WATER         = 0
SAND          = 1
GRASS         = 2
HUT_FLOOR     = 3
HUT_WALL      = 4
DESK          = 5
MAT           = 6
TRAPDOOR_OPEN = 7
MARKET_FLOOR  = 8
MARKET_WALL   = 9
WOLF_GRASS    = 10
TREE          = 11
FLOWER        = 12
PATH          = 13
ROCK          = 14
PLAZA         = 15
FOUNTAIN_00, FOUNTAIN_01, FOUNTAIN_02 = 16, 17, 18
FOUNTAIN_10, FOUNTAIN_11, FOUNTAIN_12 = 19, 20, 21
FOUNTAIN_20, FOUNTAIN_21, FOUNTAIN_22 = 22, 23, 24
FOUNTAIN_TILES = {
    (0, 0): FOUNTAIN_00, (0, 1): FOUNTAIN_01, (0, 2): FOUNTAIN_02,
    (1, 0): FOUNTAIN_10, (1, 1): FOUNTAIN_11, (1, 2): FOUNTAIN_12,
    (2, 0): FOUNTAIN_20, (2, 1): FOUNTAIN_21, (2, 2): FOUNTAIN_22,
}
DOCK          = 25
VILLAGE_WALL  = 26
VILLAGE_FLOOR = 27
TREE2         = 28
DEAD_TREE     = 29
WOLF_ROCK     = 30
BONES         = 31
DARK_PATCH    = 32
PILING        = 33
CRATE         = 34
ROPE_COIL     = 35
LANTERN       = 36

SOLID_TILES = {
    HUT_WALL, MARKET_WALL, WATER, TREE, ROCK, VILLAGE_WALL, TREE2,
    DEAD_TREE, WOLF_ROCK, PILING, LANTERN,
} | set(FOUNTAIN_TILES.values())

# Tiles that consume a glider when walked on
GLIDER_CONSUME_TILES = {WATER}


# ---------------------------------------------------------------------------
# Pixel-art drawing helpers
# ---------------------------------------------------------------------------
def make_surface(pixels, palette):
    """Build a 16x16 SRCALPHA surface. '.' = transparent."""
    surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), palette[ch])
    return surf


def _make_tile(rows, palette):
    """Solid 16x16 tile from 16 rows of 16 palette characters."""
    surf = pygame.Surface((TILE, TILE))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            surf.set_at((x, y), palette[ch])
    return surf


# ---- Terrain tile art ------------------------------------------------------
def _make_smooth_grass(base, light, dark):
    """A smoother grass tile: mostly solid base color with a few soft,
    clustered highlight/shadow patches instead of per-pixel dither noise."""
    surf = pygame.Surface((TILE, TILE))
    surf.fill(base)
    rng = random.Random(hash((base, light, dark)) & 0xFFFFFFFF)
    for _ in range(3):
        cx_, cy_ = rng.randint(2, 13), rng.randint(2, 13)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) <= 1:
                    x, y = cx_ + dx, cy_ + dy
                    if 0 <= x < TILE and 0 <= y < TILE:
                        surf.set_at((x, y), light)
    for _ in range(2):
        cx_, cy_ = rng.randint(2, 13), rng.randint(2, 13)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) <= 1:
                    x, y = cx_ + dx, cy_ + dy
                    if 0 <= x < TILE and 0 <= y < TILE:
                        surf.set_at((x, y), dark)
    return surf

_GRASS = _make_smooth_grass((92, 178, 100), (108, 198, 118), (76, 156, 84))
_WOLF_GRASS = _make_smooth_grass((62, 134, 72), (74, 152, 84), (48, 112, 58))

_WATER = _make_tile([
    "WWwWbWwWWwbWWwWW", "wWbbWwwbWWwWbWwW", "WbWwWWbbWwWWwbWW",
    "bWWwWWwWbWWwWWbW", "WwbWWwgWwbWWwWbw", "WwWwbWWwWwbWWwWW",
    "bWWWwWWbbWwWWwWb", "wWbWWwWWwbWWwWWw", "WWwWbWgwgWbWWwWW",
    "bWWwWWbWwWWwWWbW", "wWbWWwWWwwWWwWWw", "WwWbWWwWWwbWWwWW",
    "WWbWWwWWbWWwWWbW", "bWWwWWbWwWWbWWwW", "wWbWWwWWwbWWwWWb",
    "WWwbWWwWWwbWWwWW",
], {"W": (45,105,195), "w": (60,125,215), "b": (32,85,178), "g": (148,205,255)})

_SAND = _make_tile([
    "SSsSSSdSSsSSSdSS", "sSdSSSSsSdSSSSsS", "SSSSdSSSSSSdSSSS",
    "dSSsSSSdSSsSSSdS", "SSSSSdSSSSSSdSSS", "sSSSdSSsSSSdSsSS",
    "SSdSSSSSSdSSSSdS", "SSSsSSSdSSSsSSSd", "dSSSSdSSSSSSdSSS",
    "SSsSSSdSSSsSSSdS", "SSSdSSSSdSSSSSSS", "sSSSdSsSSSdSSSsS",
    "SSSSSSdSSSSSSdSS", "dSSsSSSdSSsSSSdS", "SSSSSdSSSSSSdSSS",
    "SSsSSSdSSsSSSdSS",
], {"S": (215,190,140), "s": (228,205,155), "d": (195,170,118)})

_PATH = _make_tile([
    "PPlPPpPPlPPpPPlP", "lPpPPPPlPpPPPPlP", "PPPPpPPPPPPpPPPP",
    "pPPlPPPpPPlPPPpP", "PPPPPpPPPPPPpPPP", "lPPPpPPlPPPpPlPP",
    "PPpPPPPPPpPPPPpP", "PPPlPPPpPPPlPPPp", "pPPPPpPPPPPPpPPP",
    "PPlPPPpPPPlPPPpP", "PPPpPPPPpPPPPPPP", "lPPPpPlPPPpPPPlP",
    "PPPPPPpPPPPPPpPP", "pPPlPPPpPPlPPPpP", "PPPPPpPPPPPPpPPP",
    "PPlPPPpPPlPPPpPP",
], {"P": (155,115,72), "p": (138,98,58), "l": (172,132,89)})

_HUT_FLOOR = _make_tile([
    "wWwWwWwWwWwWwWwW", "WWdWWdWWdWWdWWdW", "WgWgWWgWgWWgWgWg",
    "dWWdWWdWWdWWdWWd", "WwWwWwWwWwWwWwWw", "WdWWdWWdWWdWWdWW",
    "gWgWgWgWgWgWgWgW", "dWWdWWdWWdWWdWWd", "wWwWwWwWwWwWwWwW",
    "WWdWWdWWdWWdWWdW", "WgWgWWgWgWWgWgWg", "dWWdWWdWWdWWdWWd",
    "WwWwWwWwWwWwWwWw", "WdWWdWWdWWdWWdWW", "gWgWgWgWgWgWgWgW",
    "dWWdWWdWWdWWdWWd",
], {"W": (175,128,75), "w": (190,142,88), "d": (148,105,58), "g": (125,88,42)})

_HUT_WALL = _make_tile([
    "RrRRRdRrRRRdRrRR", "dRrRRRdRrRRRdRrR", "RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR", "RrRRRdRrRRRdRrRR", "dRrRRRdRrRRRdRrR",
    "RRdRrRRRdRrRRRdR", "rRRRdRrRRRdRrRRR", "RrRRRdRrRRRdRrRR",
    "dRrRRRdRrRRRdRrR", "RRdRrRRRdRrRRRdR", "rRRRdRrRRRdRrRRR",
    "RrRRRdRrRRRdRrRR", "dRrRRRdRrRRRdRrR", "RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR",
], {"R": (148,65,38), "r": (172,82,48), "d": (115,50,25)})

_MARKET_FLOOR = _make_tile([
    "SSSSSSSdSSSSSSdS", "sSdSSSSSsSdSSSsS", "SSSdSSSSSSSdSSSS",
    "SSSSdSSSSSSSdSSS", "gggggggggggggggg", "SSSSSSSdSSSSSSdS",
    "sSSSdSSSsSSSdSSS", "SSSSSSSSdSSSSSSS", "SSdSSSSSSSdSSSsS",
    "gggggggggggggggg", "SSSSSdSSSSSSdSSS", "sSSSSSSSsSSSSSdS",
    "SSdSSSSSSSdSSSsS", "SSSSSSSdSSSSSSdS", "gggggggggggggggg",
    "SSSSSdSSSSSSdSSS",
], {"S": (55,45,72), "s": (68,58,88), "d": (40,32,55), "g": (28,22,40)})

_MARKET_WALL = _make_tile([
    "DDddDDddDDddDDdd", "dDDcDddDDcDddDDc", "DddcDDddcDDddcDD",
    "ddDDcddDDcddDDcd", "cDDddcDDddcDDddc", "DddDDcddDDcddDDc",
    "ddcDDddcDDddcDDd", "DDcddDDcddDDcddd", "DDddDDddDDddDDdd",
    "dDDcDddDDcDddDDc", "DddcDDddcDDddcDD", "ddDDcddDDcddDDcd",
    "cDDddcDDddcDDddc", "DddDDcddDDcddDDc", "ddcDDddcDDddcDDd",
    "DDcddDDcddDDcddd",
], {"D": (30,22,40), "d": (40,32,52), "c": (50,40,65)})

_TRAPDOOR = _make_tile([
    "DDDDDDDDDDDDDdDD", "DbDbDbDbDbDbDbDb", "DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb", "DDgDDDDDDDDgDDDD", "DbDbgbDbDbgbDbDb",
    "DDDDDDDDDDDDDdDD", "DbDbDbDbDbDbDbDb", "gDDDDgDDDDgDDDDg",
    "DbDbDbDbDbDbDbDb", "DDDDDDDDDDDDDdDD", "DbDbDbDbDbDbDbDb",
    "DDgDDDDDDDDgDDDD", "DbDbgbDbDbgbDbDb", "DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb",
], {"D": (20,15,28), "d": (30,23,40), "b": (45,35,58), "g": (68,52,85)})

def _make_desk():
    img = _HUT_FLOOR.copy()
    pygame.draw.rect(img, (90, 55, 30), (1, 4, 14, 10))
    pygame.draw.rect(img, (60, 35, 18), (1, 4, 14, 10), 1)
    pygame.draw.rect(img, (40, 25, 12), (2, 11, 3, 4))
    pygame.draw.rect(img, (40, 25, 12), (11, 11, 3, 4))
    return img

def _make_mat():
    img = _HUT_FLOOR.copy()
    pygame.draw.rect(img, (150, 40, 40), (2, 2, 12, 12))
    pygame.draw.rect(img, (110, 25, 25), (2, 2, 12, 12), 1)
    pygame.draw.line(img, (110, 25, 25), (2, 6), (14, 6))
    pygame.draw.line(img, (110, 25, 25), (2, 10), (14, 10))
    return img

def _make_flower():
    img = _GRASS.copy()
    img.set_at((7, 4), (252, 252, 252))
    img.set_at((6, 5), (252, 252, 252)); img.set_at((7, 5), (248, 215, 35)); img.set_at((8, 5), (252, 252, 252))
    img.set_at((7, 6), (252, 252, 252))
    img.set_at((3, 10), (252, 220, 240))
    img.set_at((2, 11), (252, 220, 240)); img.set_at((3, 11), (248, 165, 215)); img.set_at((4, 11), (252, 220, 240))
    img.set_at((3, 12), (252, 220, 240))
    return img

def _make_tree():
    img = _GRASS.copy()
    rows = [
        "....sDDDDDDs....", "...DGGgGGGGGDs..", "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs", ".DGGGhGGGGhGGGGs", ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs", ".DGGGGGttGGGGGGs", ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs", ".DGGGGGGGGGGGGGs", ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.", "...sDDGGGGDDs...", "....sssDDsss....",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "D": (28,100,35), "G": (50,145,58),
                                "g": (72,178,82), "h": (95,210,108), "t": (100,70,38), "s": (18,78,24)})
    img.blit(overlay, (0, 0))
    return img

def _make_tree2():
    img = _GRASS.copy()
    rows = [
        "....sDDDDDDs....", "...DGGgGGGGGDs..", "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs", ".DGGGhGGGGhGGGGs", ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs", ".DGGGGGttGGGGGGs", ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs", ".DGGGGGGGGGGGGGs", ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.", "...sDDGGGGDDs...", "....sssDDsss....",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "D": (140,80,20), "G": (205,140,40),
                                "g": (225,170,60), "h": (240,195,90), "t": (100,70,38), "s": (95,55,15)})
    img.blit(overlay, (0, 0))
    return img

def _make_tree_canopy_overlay():
    rows = [
        "....sDDDDDDs....", "...DGGgGGGGGDs..", "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs", ".DGGGhGGGGhGGGGs", ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs", ".DGGGGGttGGGGGGs", ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs", ".DGGGGGGGGGGGGGs", ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.", "...sDDGGGGDDs...", "....sssDDsss....",
        "................",
    ]
    return make_surface(rows, {".": None, "D": (28,100,35), "G": (50,145,58),
                               "g": (72,178,82), "h": (95,210,108), "t": (100,70,38), "s": (18,78,24)})

def _make_tree2_canopy_overlay():
    rows = [
        "....sDDDDDDs....", "...DGGgGGGGGDs..", "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs", ".DGGGhGGGGhGGGGs", ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs", ".DGGGGGttGGGGGGs", ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs", ".DGGGGGGGGGGGGGs", ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.", "...sDDGGGGDDs...", "....sssDDsss....",
        "................",
    ]
    return make_surface(rows, {".": None, "D": (140,80,20), "G": (205,140,40),
                               "g": (225,170,60), "h": (240,195,90), "t": (100,70,38), "s": (95,55,15)})

def _make_rock():
    img = _GRASS.copy()
    rows = [
        "....sssssss....", "...sRRRRRRRs...", "..sRRrRRRrRRs..",
        ".sRRRRRRRRRRRs.", ".sRrRRRRRRrRRs.", "sRRRRRRRRRRRRRs",
        "sRRRrRRRRRrRRRs", "sRRRRRRRRRRRRRs", ".sRRRRrRRRRRRs.",
        ".sRRRRRRRRRRs..", "..ssRRRRRRsss..", "...sssssssss...",
        "................", "................", "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "s": (70,65,68), "R": (130,128,132), "r": (155,152,158)})
    img.blit(overlay, (0, 0))
    return img

def _make_plaza():
    return _make_tile([
        "MmMMMmMMmMMMmMMm", "mMmMMmMMmMMmMMmM", "MMMmMMmMMMmMMmMM",
        "mMMMmMMmMMMmMMmM", "MmMMmMMMmMMmMMMm", "MMmMMMmMMmMMMmMM",
        "mMMmMMMmMMmMMMmM", "MMMmMMmMMMmMMmMM", "mMmMMmMMmMMmMMmM",
        "MMMmMMmMMMmMMmMM", "mMMMmMMmMMMmMMmM", "MmMMmMMMmMMmMMMm",
        "MMmMMMmMMmMMMmMM", "mMMmMMMmMMmMMMmM", "MMMmMMmMMMmMMmMM",
        "mMmMMmMMmMMmMMmM",
    ], {"M": (168,160,148), "m": (148,140,130)})

def _make_fountain_tile(row_in_grid, col_in_grid, size=3):
    img = _make_plaza()
    full = size * TILE
    canvas = pygame.Surface((full, full), pygame.SRCALPHA)
    cx_, cy_ = full / 2, full / 2
    outer_r = full * 0.46
    rim_r = full * 0.40
    water_r = full * 0.34
    inner_r = full * 0.10
    rim_color = (95, 90, 88)
    basin_color = (150, 148, 150)
    water_color = (95, 165, 225)
    sparkle_color = (200, 225, 250)
    for yy in range(full):
        for xx in range(full):
            d = ((xx - cx_) ** 2 + (yy - cy_) ** 2) ** 0.5
            if d < inner_r:
                canvas.set_at((xx, yy), sparkle_color if (xx + yy) % 9 == 0 else water_color)
            elif d < water_r:
                canvas.set_at((xx, yy), water_color)
            elif d < rim_r:
                canvas.set_at((xx, yy), basin_color)
            elif d < outer_r:
                canvas.set_at((xx, yy), rim_color)
    slice_x = col_in_grid * TILE
    slice_y = row_in_grid * TILE
    overlay = canvas.subsurface((slice_x, slice_y, TILE, TILE)).copy()
    img.blit(overlay, (0, 0))
    return img

def _make_dock():
    return _make_tile([
        "wwwwwwwwwwwwwwww", "DDDDDDDDDDDDDDDD", "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww", "DDDDDDDDDDDDDDDD", "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww", "DDDDDDDDDDDDDDDD", "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww", "DDDDDDDDDDDDDDDD", "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww", "DDDDDDDDDDDDDDDD", "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
    ], {"w": (172,132,80), "D": (130,95,55)})

def _make_village_floor():
    return _HUT_FLOOR.copy()

def _make_piling():
    img = _WATER.copy()
    rows = [
        "................", "................", ".......DD.......",
        "......DddD......", "......DddD......", "......DddD......",
        "......DddD......", "......DddD......", ".....DDddDD.....",
        "......ddd.......", "................", "................",
        "................", "................", "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "D": (90, 60, 32), "d": (118, 82, 44)})
    img.blit(overlay, (0, 0))
    return img

def _make_crate():
    img = _make_dock()
    pygame.draw.rect(img, (152, 110, 60), (3, 4, 10, 9))
    pygame.draw.rect(img, (108, 74, 38), (3, 4, 10, 9), 1)
    pygame.draw.line(img, (108, 74, 38), (3, 8), (12, 8))
    pygame.draw.line(img, (108, 74, 38), (8, 4), (8, 12))
    return img

def _make_rope_coil():
    img = _make_dock()
    pygame.draw.circle(img, (198, 170, 112), (8, 8), 5, 2)
    pygame.draw.circle(img, (198, 170, 112), (8, 8), 3, 1)
    pygame.draw.circle(img, (160, 130, 80), (8, 8), 1)
    return img

def _make_lantern():
    img = _make_plaza()
    halo = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    center = (8, 5)
    for r, alpha in ((6, 35), (4, 65), (2, 110)):
        pygame.draw.circle(halo, (255, 200, 110, alpha), center, r)
    img.blit(halo, (0, 0))
    pygame.draw.rect(img, (60, 45, 30), (7, 8, 2, 7))
    pygame.draw.rect(img, (40, 32, 24), (5, 3, 6, 5))
    pygame.draw.rect(img, (255, 225, 140), (6, 4, 4, 3))
    return img

def _make_village_wall():
    return _make_tile([
        "GgGGGdGgGGGdGgGG", "dGgGGGdGgGGGdGgG", "GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG", "GgGGGdGgGGGdGgGG", "dGgGGGdGgGGGdGgG",
        "GGdGgGGGdGgGGGdG", "gGGGdGgGGGdGgGGG", "GgGGGdGgGGGdGgGG",
        "dGgGGGdGgGGGdGgG", "GGdGgGGGdGgGGGdG", "gGGGdGgGGGdGgGGG",
        "GgGGGdGgGGGdGgGG", "dGgGGGdGgGGGdGgG", "GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG",
    ], {"G": (120,118,115), "g": (140,138,135), "d": (95,92,88)})

def _make_dead_tree():
    img = _WOLF_GRASS.copy()
    rows = [
        "................", "................", ".......t........",
        "......ttt.......", "....t..t..t.....", ".....t.t.t......",
        "......ttt.......", "....tt.t.tt.....", ".....tttt.......",
        "......ttt.......", "................", "................",
        "......ttt.......", "................", "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "t": (75, 60, 48)})
    img.blit(overlay, (0, 0))
    return img

def _make_wolf_rock():
    img = _WOLF_GRASS.copy()
    rows = [
        "................", "......s.ss......", ".....sRRRRs.....",
        "....sRrRRRRs....", "...sRRRRrRRRs...", "..sRRrRRRRRRRs..",
        "..sRRRRRrRRRRs..", "..sRRRRRRRrRRs..", "...sRrRRRRRRs...",
        "....sRRRrRRs....", ".....sRRRRs.....", "......sssss.....",
        "................", "................", "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "s": (35,32,34), "R": (78,75,80), "r": (95,92,98)})
    img.blit(overlay, (0, 0))
    return img

def _make_bones():
    img = _WOLF_GRASS.copy()
    rows = [
        "................", "................", "....b.......b...",
        "...bWb.....bWb..", "....b...WW..b...", ".......WbbW.....",
        "......WbbbbW....", ".b...WbbbbbW..b.", "bWb...WbbbW..bWb",
        ".b.....WW....b..", "................", "................",
        "................", "................", "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "W": (225, 220, 205), "b": (200, 195, 175)})
    img.blit(overlay, (0, 0))
    return img

def _make_dark_patch():
    img = _WOLF_GRASS.copy()
    rng = random.Random(99)
    for _ in range(40):
        x, y = rng.randint(1, 14), rng.randint(1, 14)
        shade = rng.randint(25, 45)
        img.set_at((x, y), (shade, shade - 5, shade - 8))
    return img

TILE_IMAGES = {
    GRASS: _GRASS, WOLF_GRASS: _WOLF_GRASS, WATER: _WATER, SAND: _SAND,
    PATH: _PATH, HUT_FLOOR: _HUT_FLOOR, HUT_WALL: _HUT_WALL,
    MARKET_FLOOR: _MARKET_FLOOR, MARKET_WALL: _MARKET_WALL,
    TRAPDOOR_OPEN: _TRAPDOOR, DESK: _make_desk(), MAT: _make_mat(),
    FLOWER: _make_flower(), TREE: _make_tree(), TREE2: _make_tree2(),
    ROCK: _make_rock(), PLAZA: _make_plaza(), DOCK: _make_dock(),
    VILLAGE_WALL: _make_village_wall(), VILLAGE_FLOOR: _make_village_floor(),
    DEAD_TREE: _make_dead_tree(), WOLF_ROCK: _make_wolf_rock(),
    BONES: _make_bones(), DARK_PATCH: _make_dark_patch(),
    PILING: _make_piling(), CRATE: _make_crate(), ROPE_COIL: _make_rope_coil(),
    LANTERN: _make_lantern(),
}

for (_row, _col), _tile_id in FOUNTAIN_TILES.items():
    TILE_IMAGES[_tile_id] = _make_fountain_tile(_row, _col, size=3)


# ---- Character / NPC sprites (16x16 pixel art, scaled 2× for display) ------
def make_kyle():
    p = {".": None, "k": (45, 32, 22), "f": (238, 205, 175),
         "b": (55, 95, 210), "d": (32, 62, 158), "w": (255, 255, 255), "n": (30, 22, 15)}
    rows = [
        "....nnnnnnnn....", "...nkkkkkkkkn...", "...kfffffffkk...",
        "..kffwf.wfffk...", "...ffffffff.k...", "....ffffffff....",
        "...bbbbbbbbbb...", "..bbbbbbbbbbbb..", "..bbbbbbbbbbbb..",
        "..bbbddddddbb...", "..bb........bb..", "..bb........bb..",
        "..kk........kk..", "..nn........nn..", "................",
        "................",
    ]
    return make_surface(rows, p)

def make_noah():
    p = {".": None, "k": (58, 42, 28), "K": (45, 32, 20), "f": (212, 168, 128),
         "F": (185, 142, 105), "e": (60, 150, 80), "b": (50, 38, 26),
         "v": (40, 55, 95), "V": (30, 42, 75), "t": (190, 150, 105),
         "p": (120, 95, 65), "P": (95, 75, 50), "s": (150, 150, 155),
         "w": (100, 70, 40), "l": (70, 150, 60)}
    rows = [
        "....kKkk.kk.....", "...kkkkkkkkKk...", "..kkkkkkkkkkkk..",
        "..kKffffffFkk...", ".sKffeffeFfk....", "lwKffffffFk.....",
        ".w.bbbbbbbk.....", "w..bbbbbbb......", "w..vvVtttvv.....",
        "..vvvVtttVvv....", "..vvVVVVvv......", "...ppFFpp.......",
        "..ppP..Ppp......", "..pp....pp......", "..PP....PP......",
        "................",
    ]
    return make_surface(rows, p)

def make_merchant():
    p = {".": None, "h": (95, 42, 128), "s": (62, 28, 90), "f": (42, 32, 38),
         "g": (218, 182, 65), "e": (155, 105, 200)}
    rows = [
        "....hhhhhhhh....", "...hhhhhhhhhh...", "..hhhhffffhhhh..",
        "..hhhfe..efhhh..", "..hhhffffffhh...", "...hhhhhhhhhh...",
        "...hhssssshh....", "..hhssssssshh...", "..hhssgsssssh...",
        "..hhssssssshh...", "..hh........hh..", "..hh........hh..",
        "..ss........ss..", "..ss........ss..", "................",
        "................",
    ]
    return make_surface(rows, p)

def make_werewolf():
    p = {".": None, "g": (100, 98, 108), "d": (58, 58, 65), "r": (215, 45, 45),
         "w": (238, 238, 238), "y": (255, 210, 55)}
    rows = [
        "...g......g.....", "..ggg....ggg....", "..gggggggggg....",
        ".ggryggggyrggg..", ".gggggwgggggg...", ".gggggwgggggg...",
        "..gggggggggg....", "..gdgggggggd....", ".ggdgggggggdg...",
        ".ggdgggggggdg...", "..gd........dg..", "..gd........dg..",
        "..dd........dd..", "..dd........dd..", "................",
        "................",
    ]
    return make_surface(rows, p)

def make_chicken():
    p = {".": None, "w": (255, 255, 255), "y": (240, 195, 45), "r": (215, 55, 45), "o": (248, 175, 55)}
    rows = [
        "......oooo......", ".....owwwwo.....", "....owwwwwwo....",
        "....rwwwwwww....", "....wwwwwwww....", "....wwwwwwww....",
        ".....wwwwww.....", ".....yy.yy......", "................",
        "................", "................", "................",
        "................", "................", "................",
        "................",
    ]
    return make_surface(rows, p)

def make_golden_chicken():
    p = {".": None, "w": (255, 226, 130), "y": (255, 195, 30), "r": (215, 55, 45),
         "o": (255, 165, 40), "s": (255, 255, 220)}
    rows = [
        "......oooo......", ".....owwwwo..s..", "....owwwwwwo....",
        "....rwwwwwww....", "....wwwwwwww....", "s...wwwwwwww....",
        ".....wwwwww.....", ".....yy.yy......", "................",
        "................", "................", "................",
        "................", "................", "................",
        "................",
    ]
    return make_surface(rows, p)

def make_seagull():
    p = {".": None, "w": (248, 248, 250)}
    rows = [
        "................", "................", "................",
        "....ww....ww....", "...www....www...", "..ww........ww..",
        "................", "................", "................",
        "................", "................", "................",
        "................", "................", "................",
        "................",
    ]
    return make_surface(rows, p)

SPRITES = {
    "kyle": make_kyle(), "noah": make_noah(), "merchant": make_merchant(),
    "werewolf": make_werewolf(), "chicken": make_chicken(),
    "golden_chicken": make_golden_chicken(), "seagull": make_seagull(),
}

for _k in list(TILE_IMAGES.keys()):
    TILE_IMAGES[_k] = pygame.transform.scale(TILE_IMAGES[_k], (DISPLAY_TILE, DISPLAY_TILE))
SPRITES = {k: pygame.transform.scale(v, (DISPLAY_TILE, DISPLAY_TILE)) for k, v in SPRITES.items()}

TREE_CANOPY = {
    TREE: pygame.transform.scale(_make_tree_canopy_overlay(), (DISPLAY_TILE, DISPLAY_TILE)),
    TREE2: pygame.transform.scale(_make_tree2_canopy_overlay(), (DISPLAY_TILE, DISPLAY_TILE)),
}


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------
def generate_world():
    world = [[WATER for _ in range(MAP_W)] for _ in range(MAP_H)]
    cx, cy = MAP_W // 2, MAP_H // 2
    main_radius = 70
    for y in range(MAP_H):
        for x in range(MAP_W):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d < main_radius:
                world[y][x] = GRASS
            elif d < main_radius + 4:
                world[y][x] = SAND
    island_centers = []
    for _ in range(5):
        angle = random.uniform(0, 6.283)
        dist = random.randint(140, 260)
        ix = int(cx + dist * random.uniform(0.8, 1.2) * (1 if random.random() < 0.5 else -1))
        iy = int(cy + dist * random.uniform(0.8, 1.2) * (1 if random.random() < 0.5 else -1))
        ix = max(20, min(MAP_W - 20, ix))
        iy = max(20, min(MAP_H - 20, iy))
        r = random.randint(12, 18)
        island_centers.append((ix, iy, r))
        for y in range(max(0, iy - r - 3), min(MAP_H, iy + r + 3)):
            for x in range(max(0, ix - r - 3), min(MAP_W, ix + r + 3)):
                d = ((x - ix) ** 2 + (y - iy) ** 2) ** 0.5
                if d < r:
                    world[y][x] = WOLF_GRASS
                elif d < r + 3:
                    world[y][x] = SAND
    return world, (cx, cy, main_radius), island_centers


def carve_hut(world, hx, hy):
    w, h = 5, 4
    for y in range(hy - 1, hy + h + 1):
        for x in range(hx - 1, hx + w + 1):
            on_border = (x == hx - 1 or x == hx + w or y == hy - 1 or y == hy + h)
            world[y][x] = HUT_WALL if on_border else HUT_FLOOR
    door_x, door_y = hx + w // 2, hy + h
    world[door_y][door_x] = HUT_FLOOR
    desk_pos = (hx + w // 2, hy + h // 2)
    world[desk_pos[1]][desk_pos[0]] = DESK
    return desk_pos


def carve_market_room(world, mx, my):
    w, h = 7, 6
    for y in range(my - 1, my + h + 1):
        for x in range(mx - 1, mx + w + 1):
            on_border = (x == mx - 1 or x == mx + w or y == my - 1 or y == my + h)
            world[y][x] = MARKET_WALL if on_border else MARKET_FLOOR


def carve_village_hut(world, vx, vy, w=4, h=4):
    for y in range(vy - 1, vy + h + 1):
        for x in range(vx - 1, vx + w + 1):
            on_border = (x == vx - 1 or x == vx + w or y == vy - 1 or y == vy + h)
            world[y][x] = VILLAGE_WALL if on_border else VILLAGE_FLOOR
    door_x, door_y = vx + w // 2, vy + h
    world[door_y][door_x] = VILLAGE_FLOOR


def carve_plaza(world, cx, cy, radius=9):
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d < radius:
                world[y][x] = PLAZA
    fountain_size = 3
    top_left_x = cx - fountain_size // 2
    top_left_y = cy - fountain_size // 2
    for row in range(fountain_size):
        for col in range(fountain_size):
            world[top_left_y + row][top_left_x + col] = FOUNTAIN_TILES[(row, col)]


def decorate_plaza_lanterns(world, cx, cy, offset=6):
    for ddx, ddy in ((offset, offset), (-offset, offset), (offset, -offset), (-offset, -offset)):
        lx, ly = cx + ddx, cy + ddy
        if 0 <= lx < MAP_W and 0 <= ly < MAP_H and world[ly][lx] == PLAZA:
            world[ly][lx] = LANTERN


def carve_dock(world, shore_x, shore_y, direction, length=10):
    dx, dy = direction
    x, y = shore_x, shore_y
    for _ in range(length):
        x += dx; y += dy
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            world[y][x] = DOCK
            px, py = x - dy, y + dx
            if 0 <= px < MAP_W and 0 <= py < MAP_H:
                world[py][px] = DOCK


def decorate_dock(world, shore_x, shore_y, direction, length=10):
    dx, dy = direction
    x, y = shore_x, shore_y
    for i in range(length):
        x += dx; y += dy
        outer1_x, outer1_y = x + dy, y - dx
        outer2_x, outer2_y = x - 2 * dy, y + 2 * dx
        if i % 3 == 1:
            if 0 <= outer1_x < MAP_W and 0 <= outer1_y < MAP_H and world[outer1_y][outer1_x] == WATER:
                world[outer1_y][outer1_x] = PILING
            if 0 <= outer2_x < MAP_W and 0 <= outer2_y < MAP_H and world[outer2_y][outer2_x] == WATER:
                world[outer2_y][outer2_x] = PILING
        if i == 2 and 0 <= x < MAP_W and 0 <= y < MAP_H and world[y][x] == DOCK:
            world[y][x] = CRATE
        if i == 5 and 0 <= x < MAP_W and 0 <= y < MAP_H and world[y][x] == DOCK:
            world[y][x] = ROPE_COIL


def _carve_straight_path(world, start, end):
    x, y = start
    ex, ey = end
    while abs(x - ex) > 1 or abs(y - ey) > 1:
        if abs(x - ex) >= abs(y - ey):
            x += 1 if ex > x else -1
        else:
            y += 1 if ey > y else -1
        for ddx, ddy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            nx2, ny2 = x + ddx, y + ddy
            if 0 <= nx2 < MAP_W and 0 <= ny2 < MAP_H and world[ny2][nx2] == GRASS:
                world[ny2][nx2] = PATH


def decorate_world(world, cx, cy, main_radius, hut_x, hut_y):
    rng = random.Random(7)
    plaza_x, plaza_y = cx, cy - 2
    carve_plaza(world, plaza_x, plaza_y, radius=9)
    decorate_plaza_lanterns(world, plaza_x, plaza_y)
    village_x, village_y = cx - 22, cy - 10
    carve_village_hut(world, village_x, village_y)
    player_start = (cx, cy + 5)
    _carve_straight_path(world, player_start, (plaza_x, plaza_y + 9))
    _carve_straight_path(world, (plaza_x, plaza_y), (hut_x + 2, hut_y + 5))
    _carve_straight_path(world, (plaza_x, plaza_y), (village_x + 2, village_y + 4))
    dock_angle = 0.9
    shore_x = int(cx + main_radius * 0.95 * math.cos(dock_angle))
    shore_y = int(cy + main_radius * 0.95 * math.sin(dock_angle))
    carve_dock(world, shore_x, shore_y, direction=(1, 0), length=12)
    decorate_dock(world, shore_x, shore_y, direction=(1, 0), length=12)
    _carve_straight_path(world, (cx, cy), (shore_x - 3, shore_y))
    rock_set = set()
    for _ in range(8000):
        rx = rng.randint(0, MAP_W - 1); ry = rng.randint(0, MAP_H - 1)
        if world[ry][rx] not in (GRASS, SAND): continue
        dist_c = ((rx - cx) ** 2 + (ry - cy) ** 2) ** 0.5
        if not (main_radius * 0.75 < dist_c < main_radius * 0.98): continue
        if any(((rx - ox) ** 2 + (ry - oy) ** 2) < 30 for ox, oy in rock_set): continue
        if world[ry][rx] == GRASS: world[ry][rx] = ROCK
        rock_set.add((rx, ry))
        if len(rock_set) >= 55: break
    tree_set = set()
    grove_centers = []
    for _ in range(10):
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(main_radius * 0.2, main_radius * 0.8)
        grove_centers.append((int(cx + dist * math.cos(angle)), int(cy + dist * math.sin(angle))))
    for (gx, gy) in grove_centers:
        use_alt_color = rng.random() < 0.4
        placed = 0; attempts = 0
        while placed < rng.randint(8, 16) and attempts < 200:
            attempts += 1
            tx = gx + rng.randint(-8, 8); ty = gy + rng.randint(-8, 8)
            if not (0 <= tx < MAP_W and 0 <= ty < MAP_H): continue
            if world[ty][tx] != GRASS: continue
            dist_c = ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5
            if dist_c < 12 or dist_c > main_radius * 0.92: continue
            if ((tx - hut_x) ** 2 + (ty - hut_y) ** 2) ** 0.5 < 12: continue
            if ((tx - village_x) ** 2 + (ty - village_y) ** 2) ** 0.5 < 10: continue
            if ((tx - plaza_x) ** 2 + (ty - plaza_y) ** 2) ** 0.5 < 11: continue
            if any(((tx - ox) ** 2 + (ty - oy) ** 2) < 9 for ox, oy in tree_set): continue
            world[ty][tx] = TREE2 if use_alt_color else TREE
            tree_set.add((tx, ty)); placed += 1
    flower_count = 0
    for _ in range(5000):
        fx = rng.randint(0, MAP_W - 1); fy = rng.randint(0, MAP_H - 1)
        if world[fy][fx] != GRASS: continue
        dist_c = ((fx - cx) ** 2 + (fy - cy) ** 2) ** 0.5
        if dist_c > main_radius * 0.85 or dist_c < 4: continue
        world[fy][fx] = FLOWER; flower_count += 1
        if flower_count >= 120: break
    return plaza_x, plaza_y, village_x, village_y, shore_x, shore_y


def decorate_wolf_island(world, ix, iy, r, seed=0):
    rng = random.Random(seed)
    inner_clear_radius = r * 0.55
    occupied = set()
    def _far_enough(x, y, min_dist_sq=9):
        return not any(((x - ox) ** 2 + (y - oy) ** 2) < min_dist_sq for ox, oy in occupied)
    dead_tree_count = rng.randint(4, 8)
    placed = 0; attempts = 0
    while placed < dead_tree_count and attempts < 150:
        attempts += 1
        angle = rng.uniform(0, 6.283); dist = rng.uniform(inner_clear_radius, r * 0.9)
        tx = int(ix + dist * math.cos(angle)); ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H): continue
        if world[ty][tx] != WOLF_GRASS: continue
        if not _far_enough(tx, ty, 16): continue
        world[ty][tx] = DEAD_TREE; occupied.add((tx, ty)); placed += 1
    rock_count = rng.randint(3, 6)
    placed = 0; attempts = 0
    while placed < rock_count and attempts < 150:
        attempts += 1
        angle = rng.uniform(0, 6.283); dist = rng.uniform(inner_clear_radius, r * 0.92)
        tx = int(ix + dist * math.cos(angle)); ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H): continue
        if world[ty][tx] != WOLF_GRASS: continue
        if not _far_enough(tx, ty, 16): continue
        world[ty][tx] = WOLF_ROCK; occupied.add((tx, ty)); placed += 1
    bone_count = rng.randint(2, 4)
    placed = 0; attempts = 0
    while placed < bone_count and attempts < 100:
        attempts += 1
        angle = rng.uniform(0, 6.283); dist = rng.uniform(0, r * 0.85)
        tx = int(ix + dist * math.cos(angle)); ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H): continue
        if world[ty][tx] != WOLF_GRASS: continue
        if not _far_enough(tx, ty, 12): continue
        world[ty][tx] = BONES; occupied.add((tx, ty)); placed += 1
    patch_count = rng.randint(3, 6)
    placed = 0; attempts = 0
    while placed < patch_count and attempts < 100:
        attempts += 1
        angle = rng.uniform(0, 6.283); dist = rng.uniform(0, r * 0.85)
        tx = int(ix + dist * math.cos(angle)); ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H): continue
        if world[ty][tx] != WOLF_GRASS: continue
        if not _far_enough(tx, ty, 10): continue
        world[ty][tx] = DARK_PATCH; occupied.add((tx, ty)); placed += 1


def spawn_wild_chickens(world, cx, cy, main_radius, hut_x, hut_y, village_x, village_y,
                          plaza_x, plaza_y, count=5, seed=42):
    rng = random.Random(seed)
    positions = []
    attempts = 0
    while len(positions) < count and attempts < 500:
        attempts += 1
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(main_radius * 0.15, main_radius * 0.8)
        wx = cx + dist * math.cos(angle); wy = cy + dist * math.sin(angle)
        tx, ty = int(wx), int(wy)
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H): continue
        if world[ty][tx] in SOLID_TILES: continue
        if world[ty][tx] not in (GRASS, PATH, FLOWER, PLAZA): continue
        if ((tx - hut_x) ** 2 + (ty - hut_y) ** 2) ** 0.5 < 8: continue
        if ((tx - village_x) ** 2 + (ty - village_y) ** 2) ** 0.5 < 8: continue
        if ((tx - plaza_x) ** 2 + (ty - plaza_y) ** 2) ** 0.5 < 6: continue
        if any(((tx - ox) ** 2 + (ty - oy) ** 2) < 25 for ox, oy in positions): continue
        positions.append((wx, wy))
    chickens = []
    for px, py in positions:
        if rng.random() < 0.2:
            chickens.append(GoldenChicken(px, py))
        else:
            chickens.append(WildChicken(px, py))
    return chickens


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.chickens = 0
        self.materials = 0
        self.gliders = 0
        self.chickens_sold = 0
        self.money = 0
        self.noah_trust = True
        self.mission_stage = 0
        self.desk_lifted = False
        self.mat_lifted = False
        self.in_black_market = False
        self.game_over = False
        self.won = False
        self.on_wolf_island = False
        self.current_island_index = -1
        self.last_return_pos = None  # Where player was before going to island

    def give_chicken_to_noah(self, amount=1):
        if self.chickens >= amount and amount > 0:
            self.chickens -= amount
            self.materials += amount * 2
            self.mission_stage += 1
            return f"Noah takes {amount} chicken and hands you {amount * 2} materials."
        return "You don't have any chicken to give Noah."

    def sell_chicken_to_merchant(self, amount=1):
        if self.chickens < amount or amount <= 0:
            return "You don't have any chicken to sell."
        self.chickens -= amount
        self.chickens_sold += amount
        self.money += amount * 8  # IMPROVED: better payout
        message = f"You sell {amount} chicken for {amount * 8} gold."
        if random.random() < 0.5:
            penalty_chickens = min(self.chickens, random.randint(1, 2))
            penalty_money = min(self.money, random.randint(5, 15))
            self.chickens -= penalty_chickens
            self.money -= penalty_money
            self.noah_trust = False
            message += (f"
Noah found out! Takes {penalty_chickens} chicken and {penalty_money}g.")
        else:
            message += "
Noah doesn't seem to have noticed..."
        if self.chickens_sold >= CHICKENS_TO_WIN:
            self.won = True
            self.game_over = True
        return message


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
class Entity:
    def __init__(self, x, y, sprite):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.bob_amplitude = 0.0
        self.bob_speed = 450.0
        self._bob_phase = random.uniform(0, 6.283)

    @property
    def tile(self):
        return int(self.x), int(self.y)


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["kyle"])
        self.speed = 10.8
        self.sprint_speed = 17.0
        self.health = 100
        self.max_health = 100
        self.stamina = 100
        self.max_stamina = 100
        self.last_damage_time = 0

    def try_move(self, dx, dy, world, has_glider=False):
        """IMPROVED: Now properly checks WATER tiles and requires gliders."""
        if dx:
            nx = self.x + dx
            tx, ty = int(nx), int(self.y)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                tile_id = world[ty][tx]
                if tile_id == WATER and not has_glider:
                    return False
                if tile_id not in SOLID_TILES:
                    self.x = nx
                    return True
        if dy:
            ny = self.y + dy
            tx, ty = int(self.x), int(ny)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                tile_id = world[ty][tx]
                if tile_id == WATER and not has_glider:
                    return False
                if tile_id not in SOLID_TILES:
                    self.y = ny
                    return True
        return False


class Werewolf(Entity):
    STATE_WANDER = "wander"
    STATE_CHASE = "chase"

    def __init__(self, x, y, home_radius_tiles, center):
        super().__init__(x, y, SPRITES["werewolf"])
        self.health = 40
        self.speed = 4.2
        self.state = Werewolf.STATE_WANDER
        self.wander_dir = pygame.Vector2(random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
        self.wander_timer = random.uniform(0.5, 1.5)
        self.detect_radius = 7
        self.has_chicken = True
        self.has_materials = random.random() < 0.3  # IMPROVED: 30% drop materials
        self.center = center
        self.home_radius = home_radius_tiles
        self.flash_time = 0  # For damage flash effect

    def update(self, player, dt):
        dist = ((self.x - player.x) ** 2 + (self.y - player.y) ** 2) ** 0.5
        self.state = Werewolf.STATE_CHASE if dist < self.detect_radius else Werewolf.STATE_WANDER
        if self.state == Werewolf.STATE_CHASE:
            dx, dy = player.x - self.x, player.y - self.y
            length = (dx ** 2 + dy ** 2) ** 0.5
            if length > 0:
                dx, dy = dx / length, dy / length
            self.x += dx * self.speed * dt
            self.y += dy * self.speed * dt
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self.wander_dir = pygame.Vector2(random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
                self.wander_timer = random.uniform(0.5, 1.5)
            self.x += self.wander_dir.x * self.speed * dt
            self.y += self.wander_dir.y * self.speed * dt
        cx, cy = self.center
        if ((self.x - cx) ** 2 + (self.y - cy) ** 2) ** 0.5 > self.home_radius:
            self.x += (cx - self.x) * min(1.0, 3 * dt)
            self.y += (cy - self.y) * min(1.0, 3 * dt)
        if self.flash_time > 0:
            self.flash_time -= dt

    def take_damage(self, amount):
        self.health -= amount
        self.flash_time = 0.15  # Flash red for 150ms
        return self.health <= 0


class Noah(Entity):
    DIALOGUE_BY_STAGE = [
        "Hey... you're new here, huh? Name's Noah Ficsher. Been stuck on this island forever. Bring me chicken (press G) and I'll set you up with materials to build a glider.",
        "Those smaller islands out there are crawling with werewolves. They guard the chickens, so you'll need to fight through them.",
        "Nice, you're getting the hang of it. Keep bringing me chicken and I'll keep helping you out.",
        "Something feels off... you wouldn't be selling chicken behind my back to that merchant, would you?",
    ]

    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["noah"])
        self.bob_amplitude = 2.0
        self.bob_speed = 500.0

    def get_dialogue(self, state: GameState):
        stage = min(state.mission_stage, len(self.DIALOGUE_BY_STAGE) - 1)
        line = self.DIALOGUE_BY_STAGE[stage]
        if not state.noah_trust:
            line = "I KNOW you've been selling chicken to that merchant. Don't think I haven't noticed... Bring me more chicken and we'll call it even."
        return line


class Merchant(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["merchant"])
        self.bob_amplitude = 1.6
        self.bob_speed = 620.0


class WildChicken(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["chicken"])
        self.collected = False
        self.value = 1
        self.bob_amplitude = 1.0
        self.bob_speed = 600.0


class GoldenChicken(WildChicken):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.sprite = SPRITES["golden_chicken"]
        self.value = 3
        self.bob_amplitude = 1.5
        self.bob_speed = 450.0


class Seagull(Entity):
    def __init__(self, center_x, center_y, radius, speed, phase=0.0):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.speed = speed
        self.angle = phase
        x = center_x + radius * math.cos(phase)
        y = center_y + radius * math.sin(phase) * 0.6
        super().__init__(x, y, SPRITES["seagull"])

    def update(self, dt):
        self.angle += self.speed * dt
        self.x = self.center_x + self.radius * math.cos(self.angle)
        self.y = self.center_y + self.radius * math.sin(self.angle) * 0.6


# ---------------------------------------------------------------------------
# Visual Effects System
# ---------------------------------------------------------------------------
class Particle:
    """A simple particle for visual effects."""
    def __init__(self, x, y, vx, vy, color, life, size=2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x, cam_y):
        alpha = int(255 * (self.life / self.max_life))
        color = (*self.color[:3], alpha)
        px = int(self.x - cam_x + SCREEN_W / 2)
        py = int(self.y - cam_y + SCREEN_H / 2)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (self.size, self.size), self.size)
        surface.blit(s, (px - self.size, py - self.size))


class FloatingText:
    """Damage numbers and pickup notifications."""
    def __init__(self, x, y, text, color, life=1.0):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = life
        self.max_life = life
        self.vy = -25

    def update(self, dt):
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x, cam_y):
        alpha = int(255 * (self.life / self.max_life))
        color = (*self.color[:3], alpha)
        px = int(self.x - cam_x + SCREEN_W / 2)
        py = int(self.y - cam_y + SCREEN_H / 2)
        text_surf = DAMAGE_FONT.render(self.text, True, color[:3])
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (px - text_surf.get_width() // 2, py))


class ScreenShake:
    """Screen shake effect for attacks and damage."""
    def __init__(self):
        self.intensity = 0.0
        self.duration = 0.0

    def trigger(self, intensity, duration):
        self.intensity = max(self.intensity, intensity)
        self.duration = max(self.duration, duration)

    def update(self, dt):
        if self.duration > 0:
            self.duration -= dt
            if self.duration <= 0:
                self.intensity = 0.0

    def get_offset(self):
        if self.duration <= 0:
            return (0, 0)
        return (random.uniform(-self.intensity, self.intensity),
                random.uniform(-self.intensity, self.intensity))


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def draw_text(surface, text, pos, font=FONT, color=(255, 255, 255), max_width=None):
    x, y = pos
    for line in text.split("\n"):
        if max_width is None:
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_height() + 2
            continue
        words = line.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if font.size(candidate)[0] <= max_width or not current:
                current = candidate
            else:
                surface.blit(font.render(current, True, color), (x, y))
                y += font.get_height() + 4
                current = word
        surface.blit(font.render(current, True, color), (x, y))
        y += font.get_height() + 4


def draw_hud(surface, state: GameState, player: Player):
    hud_y = SCREEN_H
    pygame.draw.rect(surface, (22, 18, 32), (0, hud_y, SCREEN_W, HUD_HEIGHT))
    pygame.draw.line(surface, (90, 65, 115), (0, hud_y), (SCREEN_W, hud_y), 2)

    # Health bar
    bx, by = 10, hud_y + 10
    bw, bh = 180, 16
    pygame.draw.rect(surface, (55, 18, 18), (bx, by, bw, bh))
    hp_w = int(bw * max(0, player.health) / player.max_health)
    bar_col = (210, 45, 45) if player.health / player.max_health > 0.25 else (255, 100, 20)
    if hp_w > 0:
        pygame.draw.rect(surface, bar_col, (bx, by, hp_w, bh))
    pygame.draw.rect(surface, (180, 130, 130), (bx, by, bw, bh), 1)
    hp_surf = HUD_FONT.render(f"HP {int(player.health)}/{player.max_health}", True, (255, 225, 225))
    surface.blit(hp_surf, (bx + 4, by + 2))

    # Stamina bar (NEW)
    sx, sy = 10, hud_y + 30
    sw, sh = 120, 8
    pygame.draw.rect(surface, (18, 35, 55), (sx, sy, sw, sh))
    stam_w = int(sw * max(0, player.stamina) / player.max_stamina)
    if stam_w > 0:
        pygame.draw.rect(surface, (65, 180, 220), (sx, sy, stam_w, sh))
    pygame.draw.rect(surface, (100, 160, 180), (sx, sy, sw, sh), 1)

    # Item stats row
    sx, sy = 10, hud_y + 44
    pygame.draw.circle(surface, (248, 195, 45), (sx + 7, sy + 7), 6)
    pygame.draw.circle(surface, (200, 148, 30), (sx + 7, sy + 7), 6, 1)
    surface.blit(HUD_FONT.render(f"x{state.chickens}", True, (255, 240, 185)), (sx + 16, sy + 1))

    mx = sx + 58
    pygame.draw.rect(surface, (80, 175, 225), (mx, sy + 1, 12, 12))
    pygame.draw.rect(surface, (50, 130, 185), (mx, sy + 1, 12, 12), 1)
    surface.blit(HUD_FONT.render(f"x{state.materials}", True, (185, 230, 255)), (mx + 15, sy + 1))

    gx = mx + 65
    pygame.draw.polygon(surface, (255, 195, 35), [(gx+6, sy), (gx+12, sy+6), (gx+6, sy+12), (gx, sy+6)])
    pygame.draw.polygon(surface, (200, 148, 20), [(gx+6, sy), (gx+12, sy+6), (gx+6, sy+12), (gx, sy+6)], 1)
    surface.blit(HUD_FONT.render(f"{state.money}g", True, (255, 225, 110)), (gx + 16, sy + 1))

    # Glider count (NEW - was missing!)
    glx = gx + 68
    pygame.draw.polygon(surface, (180, 160, 140), [(glx+6, sy), (glx+12, sy+6), (glx+6, sy+12), (glx, sy+6)])
    surface.blit(HUD_FONT.render(f"x{state.gliders}", True, (200, 190, 175)), (glx + 16, sy + 1))

    # Sold progress
    px2 = glx + 55
    sold_col = (100, 235, 115) if state.chickens_sold < CHICKENS_TO_WIN else (255, 215, 50)
    surface.blit(HUD_FONT.render(f"Sold:{state.chickens_sold}/{CHICKENS_TO_WIN}", True, sold_col), (px2, sy + 1))

    # Trust indicator
    if state.noah_trust:
        tc, tt = (80, 225, 110), "Noah trusts you"
        pygame.draw.circle(surface, tc, (SCREEN_W - 170, hud_y + 22), 5)
    else:
        tc, tt = (230, 80, 80), "Noah suspicious!"
        pts = [(SCREEN_W - 170, hud_y + 16), (SCREEN_W - 175, hud_y + 28), (SCREEN_W - 165, hud_y + 28)]
        pygame.draw.polygon(surface, tc, pts)
    surface.blit(HUD_FONT.render(tt, True, tc), (SCREEN_W - 158, hud_y + 16))

    # Island indicator (NEW)
    if state.on_wolf_island:
        surface.blit(HUD_FONT.render("WOLF ISLAND!", True, (230, 80, 80)), (SCREEN_W - 170, hud_y + 38))

    hint = "E:interact G:give B:build SPC:attack Q:return Shift:sprint"
    surface.blit(FONT.render(hint, True, (110, 95, 145)), (10, hud_y + HUD_HEIGHT - 17))


def show_message_box(surface, message):
    box_x, box_margin = 30, 30
    box_w = SCREEN_W - box_margin * 2
    text_max_width = box_w - 28
    line_count = 0
    for raw_line in message.split("\n"):
        words = raw_line.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if DIALOGUE_FONT.size(candidate)[0] <= text_max_width or not current:
                current = candidate
            else:
                line_count += 1
                current = word
        line_count += 1
    line_height = DIALOGUE_FONT.get_height() + 4
    text_block_height = line_count * line_height
    box_h = max(90, min(text_block_height + 56, SCREEN_H - 40))
    box_y = max(10, SCREEN_H - box_h - 10)
    box = pygame.Rect(box_x, box_y, box_w, box_h)
    pygame.draw.rect(surface, (10, 10, 15), box)
    pygame.draw.rect(surface, (255, 255, 255), box, 2)
    draw_text(surface, message, (box.x + 14, box.y + 14), font=DIALOGUE_FONT, max_width=text_max_width)
    draw_text(surface, "(press any key)", (box.x + 14, box.y + box.height - 24), color=(210, 170, 40))
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                waiting = False


def show_win_screen(surface):
    surface.fill((10, 10, 15))
    draw_text(surface,
        "Kyle finally has enough gold saved up...\nHe leaves the maze behind and goes home to find his dog.\n\nYOU WIN!",
        (40, SCREEN_H // 2 - 50), font=BIG_FONT, color=(210, 170, 40))
    pygame.display.flip()
    pygame.time.wait(4000)


def show_lose_screen(surface):
    surface.fill((10, 10, 15))
    draw_text(surface,
        "Kyle collapses, exhausted and wounded...\nThe maze claims another wanderer.\n\nGAME OVER",
        (40, SCREEN_H // 2 - 50), font=BIG_FONT, color=(200, 60, 60))
    pygame.display.flip()
    pygame.time.wait(4000)


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------
RAIN_PERIOD = 90.0
RAIN_FRACTION = 0.35
RAIN_FADE = 0.06


def make_rain_drops(count=70):
    return [[random.uniform(0, SCREEN_W), random.uniform(0, SCREEN_H),
             random.uniform(220, 340), random.uniform(8, 14)] for _ in range(count)]


def compute_rain_intensity(elapsed_seconds):
    phase = (elapsed_seconds % RAIN_PERIOD) / RAIN_PERIOD
    if phase > RAIN_FRACTION:
        return 0.0
    if phase < RAIN_FADE:
        return phase / RAIN_FADE
    if phase > RAIN_FRACTION - RAIN_FADE:
        return (RAIN_FRACTION - phase) / RAIN_FADE
    return 1.0


def draw_weather_overlay(surface, rain_drops, intensity, dt):
    tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    tint.fill((40, 55, 80, int(70 * intensity)))
    surface.blit(tint, (0, 0))
    alpha = int(170 * intensity)
    color = (200, 215, 235, alpha)
    for drop in rain_drops:
        drop[1] += drop[2] * dt
        if drop[1] > SCREEN_H:
            drop[1] = -10
            drop[0] = random.uniform(0, SCREEN_W)
        streak = pygame.Surface((2, int(drop[3])), pygame.SRCALPHA)
        streak.fill(color)
        surface.blit(streak, (drop[0], drop[1]))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
TERRAIN_BASE_TILES = {WATER, SAND, GRASS, WOLF_GRASS}

ORGANIC_WATER_COLOR = (51, 119, 200)
ORGANIC_LAND_COLOR = (99, 186, 107)
ORGANIC_WOLF_LAND_COLOR = (68, 145, 79)
ORGANIC_OUTLINE_COLOR = (54, 130, 64)
ORGANIC_WOLF_OUTLINE_COLOR = (38, 96, 48)

_TERRAIN_MARGIN = 2
_TERRAIN_GRID = VIEW_TILES_ACROSS + _TERRAIN_MARGIN * 2

try:
    import pygame.surfarray as _surfarray
    _HAS_SURFARRAY = True
except ImportError:
    _HAS_SURFARRAY = False


def _smooth_upscale_small(mask_surf, small_size):
    grid = mask_surf.get_width()
    cur = pygame.transform.smoothscale(mask_surf, (grid * 3, grid * 3))
    cur = pygame.transform.smoothscale(cur, (small_size, small_size))
    return cur


def _colored_layer_with_mask_alpha(mask_big, color, red_array=None):
    layer = pygame.Surface(mask_big.get_size(), pygame.SRCALPHA)
    layer.fill(color)
    if _HAS_SURFARRAY:
        if red_array is None:
            red_array = _surfarray.array_red(mask_big)
        alpha_view = _surfarray.pixels_alpha(layer)
        alpha_view[:, :] = red_array
        del alpha_view
    return layer


def _draw_hand_drawn_outline(surface, red_array, outline_color, world_seed, scale=1):
    """IMPROVED: Uses world_seed instead of origin_offset for stable coastline."""
    if not _HAS_SURFARRAY or red_array is None:
        return
    step = max(1, int(2 * scale))
    rng = random.Random(world_seed)  # Stable seed based on world, not camera
    sampled = red_array[::step, ::step]
    edge_mask = (sampled > 90) & (sampled < 200)
    xs, ys = edge_mask.nonzero()
    radius = max(1, scale)
    for xi, yi in zip(xs, ys):
        x, y = int(xi) * step, int(yi) * step
        # IMPROVED: Independent x/y jitter
        jx = rng.uniform(-0.6, 0.6) * scale
        jy = rng.uniform(-0.6, 0.6) * scale
        pygame.draw.circle(surface, outline_color, (x + jx, y + jy), radius)


_TERRAIN_SUPERSAMPLE = 6


def render_world(world, player, npcs_visible, shake_offset=(0, 0)):
    screen.fill((15, 10, 22))
    cam_pixel_x = player.x * DISPLAY_TILE - SCREEN_W / 2 + shake_offset[0]
    cam_pixel_y = player.y * DISPLAY_TILE - SCREEN_H / 2 + shake_offset[1]
    first_tile_x = math.floor(cam_pixel_x / DISPLAY_TILE)
    first_tile_y = math.floor(cam_pixel_y / DISPLAY_TILE)

    margin = _TERRAIN_MARGIN
    grid = _TERRAIN_GRID
    land_mask = pygame.Surface((grid, grid))
    wolf_mask = pygame.Surface((grid, grid))
    any_wolf_grass = False
    for gy in range(grid):
        world_ty = first_tile_y - margin + gy
        for gx in range(grid):
            world_tx = first_tile_x - margin + gx
            if 0 <= world_tx < MAP_W and 0 <= world_ty < MAP_H:
                tile_id = world[world_ty][world_tx]
            else:
                tile_id = WATER
            is_land = tile_id not in (WATER, DOCK, PILING)
            is_wolf = tile_id == WOLF_GRASS
            if is_wolf:
                any_wolf_grass = True
            land_mask.set_at((gx, gy), (255, 255, 255) if is_land else (0, 0, 0))
            wolf_mask.set_at((gx, gy), (255, 255, 255) if is_wolf else (0, 0, 0))

    small_size = grid * _TERRAIN_SUPERSAMPLE
    terrain_px_size = grid * DISPLAY_TILE

    land_small = _smooth_upscale_small(land_mask, small_size)
    land_red_array = _surfarray.array_red(land_small) if _HAS_SURFARRAY else None

    terrain_small = pygame.Surface((small_size, small_size))
    terrain_small.fill(ORGANIC_WATER_COLOR)
    land_layer = _colored_layer_with_mask_alpha(land_small, ORGANIC_LAND_COLOR, land_red_array)
    terrain_small.blit(land_layer, (0, 0))

    if any_wolf_grass:
        wolf_small = _smooth_upscale_small(wolf_mask, small_size)
        wolf_layer = _colored_layer_with_mask_alpha(wolf_small, ORGANIC_WOLF_LAND_COLOR)
        terrain_small.blit(wolf_layer, (0, 0))

    # IMPROVED: Stable world seed for coastline outline
    world_seed = 42  # Fixed seed for stable outline
    _draw_hand_drawn_outline(terrain_small, land_red_array, ORGANIC_OUTLINE_COLOR, world_seed, scale=1)

    terrain_surf = pygame.transform.smoothscale(terrain_small, (terrain_px_size, terrain_px_size))
    terrain_origin_x = (first_tile_x - margin) * DISPLAY_TILE - cam_pixel_x
    terrain_origin_y = (first_tile_y - margin) * DISPLAY_TILE - cam_pixel_y
    screen.blit(terrain_surf, (terrain_origin_x, terrain_origin_y))

    ticks = pygame.time.get_ticks()
    for ty_offset in range(VIEW_TILES_ACROSS + 1):
        world_ty = first_tile_y + ty_offset
        if not (0 <= world_ty < MAP_H):
            continue
        for tx_offset in range(VIEW_TILES_ACROSS + 1):
            world_tx = first_tile_x + tx_offset
            if not (0 <= world_tx < MAP_W):
                continue
            tile_id = world[world_ty][world_tx]
            if tile_id in TERRAIN_BASE_TILES:
                continue
            sx = world_tx * DISPLAY_TILE - cam_pixel_x
            sy = world_ty * DISPLAY_TILE - cam_pixel_y

            if tile_id in TREE_CANOPY:
                phase = (world_tx * 0.7 + world_ty * 1.3) % 6.283
                angle = math.sin(ticks / 900.0 + phase) * 4.0
                canopy = pygame.transform.rotate(TREE_CANOPY[tile_id], angle)
                off_x = (canopy.get_width() - DISPLAY_TILE) / 2
                off_y = (canopy.get_height() - DISPLAY_TILE) / 2
                screen.blit(canopy, (sx - off_x, sy - off_y))
                continue

            img = TILE_IMAGES.get(tile_id)
            if img is None:
                continue
            screen.blit(img, (sx, sy))

    px = SCREEN_W / 2 - DISPLAY_TILE / 2
    py = SCREEN_H / 2 - DISPLAY_TILE / 2

    for entity in npcs_visible:
        ex = (entity.x - player.x) * DISPLAY_TILE + SCREEN_W / 2 - DISPLAY_TILE / 2
        ey = (entity.y - player.y) * DISPLAY_TILE + SCREEN_H / 2 - DISPLAY_TILE / 2
        if entity.bob_amplitude:
            ey += math.sin(pygame.time.get_ticks() / entity.bob_speed + entity._bob_phase) * entity.bob_amplitude
        if -DISPLAY_TILE <= ex <= SCREEN_W and -DISPLAY_TILE <= ey <= SCREEN_H:
            # IMPROVED: Flash red when werewolf takes damage
            if isinstance(entity, Werewolf) and entity.flash_time > 0:
                flash_surf = entity.sprite.copy()
                flash_surf.fill((255, 100, 100), special_flags=pygame.BLEND_ADD)
                screen.blit(flash_surf, (ex, ey))
            else:
                screen.blit(entity.sprite, (ex, ey))

    screen.blit(player.sprite, (px, py))


def draw_minimap(surface, world, player, island_centers, state):
    """IMPROVED: Draw a small minimap in the corner."""
    mm_w, mm_h = 80, 80
    mm_x, mm_y = SCREEN_W - mm_w - 8, 8
    mm_surf = pygame.Surface((mm_w, mm_h))
    mm_surf.fill((20, 25, 35))

    scale_x = mm_w / MAP_W
    scale_y = mm_h / MAP_H

    for (ix, iy, r) in island_centers:
        pygame.draw.circle(mm_surf, (80, 40, 40), (int(ix * scale_x), int(iy * scale_y)), max(2, int(r * scale_x)))

    px = int(player.x * scale_x)
    py = int(player.y * scale_y)
    pygame.draw.circle(mm_surf, (255, 50, 50), (px, py), 2)

    # Draw main island
    cx, cy = MAP_W // 2, MAP_H // 2
    pygame.draw.circle(mm_surf, (60, 140, 70), (int(cx * scale_x), int(cy * scale_y)), max(3, int(70 * scale_x)))

    pygame.draw.rect(surface, (60, 60, 80), (mm_x - 2, mm_y - 2, mm_w + 4, mm_h + 4), 1)
    surface.blit(mm_surf, (mm_x, mm_y))


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
def main():
    state = GameState()
    world, (cx, cy, main_radius), island_centers = generate_world()

    hut_x, hut_y = cx + 20, cy - 15
    desk_pos = carve_hut(world, hut_x, hut_y)

    market_x, market_y = hut_x - 200, hut_y + 200
    if market_x < 5: market_x = 5
    if market_y > MAP_H - 10: market_y = MAP_H - 10
    carve_market_room(world, market_x, market_y)
    merchant_pos = (market_x + 3, market_y + 3)
    merchant = Merchant(*merchant_pos)

    plaza_x, plaza_y, village_x, village_y, shore_x, shore_y = decorate_world(world, cx, cy, main_radius, hut_x, hut_y)

    for i, (ix, iy, r) in enumerate(island_centers):
        decorate_wolf_island(world, ix, iy, r, seed=1000 + i)

    wild_chickens = spawn_wild_chickens(
        world, cx, cy, main_radius, hut_x, hut_y, village_x, village_y,
        plaza_x, plaza_y, count=5,
    )

    noah = Noah(cx - 5, cy)
    player = Player(cx, cy + 5)

    werewolves = []
    for (ix, iy, r) in island_centers:
        count = random.randint(2, 4)
        for _ in range(count):
            wx = ix + random.uniform(-r * 0.6, r * 0.6)
            wy = iy + random.uniform(-r * 0.6, r * 0.6)
            werewolves.append(Werewolf(wx, wy, r, (ix, iy)))

    last_attack_time = 0
    attack_cooldown = 400

    seagulls = [
        Seagull(shore_x, shore_y, radius=12 + i * 4, speed=0.3 + i * 0.07, phase=i * (6.283 / 4))
        for i in range(4)
    ]

    rain_drops = make_rain_drops()
    market_entry_tile = (market_x + 3, market_y + 1)

    # Visual effects
    particles = []
    floating_texts = []
    screen_shake = ScreenShake()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_e:
                    ptile = player.tile
                    dist_to_noah = ((player.x - noah.x) ** 2 + (player.y - noah.y) ** 2) ** 0.5
                    dist_to_desk = ((ptile[0] - desk_pos[0]) ** 2 + (ptile[1] - desk_pos[1]) ** 2) ** 0.5
                    dist_to_merchant = ((player.x - merchant.x) ** 2 + (player.y - merchant.y) ** 2) ** 0.5

                    if dist_to_noah < 1.8:
                        show_message_box(screen, noah.get_dialogue(state))

                    elif dist_to_desk < 1.5 and not state.desk_lifted:
                        state.desk_lifted = True
                        world[desk_pos[1]][desk_pos[0]] = MAT
                        show_message_box(screen, "You lift the desk aside, revealing a mat underneath...")

                    elif dist_to_desk < 1.5 and state.desk_lifted and not state.mat_lifted:
                        state.mat_lifted = True
                        world[desk_pos[1]][desk_pos[0]] = TRAPDOOR_OPEN
                        show_message_box(screen, "You lift the mat and find a trapdoor leading down.")

                    elif dist_to_desk < 1.5 and state.mat_lifted:
                        state.in_black_market = True
                        player.x, player.y = market_x + 3, market_y + 1
                        show_message_box(screen, "You climb down into the hidden black market.")

                    elif state.in_black_market and dist_to_merchant < 1.8:
                        amount = min(2, state.chickens)
                        msg = state.sell_chicken_to_merchant(amount)
                        show_message_box(screen, msg)

                    elif state.in_black_market and player.tile == market_entry_tile:
                        state.in_black_market = False
                        player.x, player.y = desk_pos[0], desk_pos[1] + 1
                        show_message_box(screen, "You climb back up out of the black market.")

                # IMPROVED: Q key now works to return from wolf islands
                if event.key == pygame.K_q:
                    if state.on_wolf_island and state.last_return_pos is not None:
                        player.x, player.y = state.last_return_pos
                        state.on_wolf_island = False
                        state.current_island_index = -1
                        state.last_return_pos = None
                        show_message_box(screen, "You use your glider to return to the main island.")
                        state.gliders = max(0, state.gliders - 1)  # Consume glider on return
                    elif state.on_wolf_island:
                        show_message_box(screen, "Can't return - no safe landing point remembered!")

                if event.key == pygame.K_g:
                    dist_to_noah = ((player.x - noah.x) ** 2 + (player.y - noah.y) ** 2) ** 0.5
                    if dist_to_noah < 1.8:
                        msg = state.give_chicken_to_noah(amount=min(2, state.chickens))
                        show_message_box(screen, msg)

                if event.key == pygame.K_b:
                    if state.materials >= 6:
                        state.materials -= 6
                        state.gliders += 1
                        show_message_box(screen, "You assemble a glider from the materials. Walk toward a smaller island's shore to glide over.")
                    else:
                        show_message_box(screen, "Not enough materials (need 6).")

                if event.key == pygame.K_SPACE:
                    now = pygame.time.get_ticks()
                    if now - last_attack_time > attack_cooldown:
                        last_attack_time = now
                        screen_shake.trigger(3.0, 0.1)  # IMPROVED: Screen shake on attack
                        for wolf in list(werewolves):
                            dist = ((player.x - wolf.x) ** 2 + (player.y - wolf.y) ** 2) ** 0.5
                            if dist < 1.6:
                                if wolf.take_damage(20):
                                    # IMPROVED: Spawn particles and floating text
                                    wx = wolf.x * DISPLAY_TILE
                                    wy = wolf.y * DISPLAY_TILE
                                    for _ in range(8):
                                        particles.append(Particle(
                                            wx, wy,
                                            random.uniform(-30, 30), random.uniform(-40, -10),
                                            (200, 50, 50), random.uniform(0.3, 0.6), size=2
                                        ))
                                    floating_texts.append(FloatingText(wx, wy, "+1 Chicken", (255, 200, 50)))
                                    if wolf.has_materials:
                                        floating_texts.append(FloatingText(wx, wy - 15, "+1 Material", (100, 200, 255)))
                                        state.materials += 1
                                    werewolves.remove(wolf)
                                    if wolf.has_chicken:
                                        state.chickens += 1

        # Movement
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = player.sprint_speed if sprinting and player.stamina > 0 else player.speed

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -speed * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = speed * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -speed * dt
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = speed * dt

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        # Stamina management
        if sprinting and (dx or dy) and player.stamina > 0:
            player.stamina = max(0, player.stamina - 30 * dt)
        elif player.stamina < player.max_stamina:
            player.stamina = min(player.max_stamina, player.stamina + 15 * dt)

        def _tile_passable(tile_id):
            if tile_id == WATER:
                return state.gliders > 0
            return tile_id not in SOLID_TILES

        # Track if player crossed water (consumed glider)
        crossed_water = False

        if dx:
            nx = player.x + dx
            tx, ty = int(nx), int(player.y)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                tile_id = world[ty][tx]
                if _tile_passable(tile_id):
                    if tile_id == WATER and state.gliders > 0:
                        crossed_water = True
                    player.x = nx

        if dy:
            ny = player.y + dy
            tx, ty = int(player.x), int(ny)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                tile_id = world[ty][tx]
                if _tile_passable(tile_id):
                    if tile_id == WATER and state.gliders > 0:
                        crossed_water = True
                    player.y = ny

        # IMPROVED: Consume glider when crossing water
        if crossed_water:
            # Check if we were on land before and now entering water
            prev_tx, prev_ty = int(player.x - dx), int(player.y - dy)
            if 0 <= prev_tx < MAP_W and 0 <= prev_ty < MAP_H:
                if world[prev_ty][prev_tx] != WATER:
                    state.gliders = max(0, state.gliders - 1)
                    floating_texts.append(FloatingText(
                        player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                        "Glider used!", (200, 200, 200)
                    ))

        # Check if on wolf island
        state.on_wolf_island = False
        for i, (ix, iy, r) in enumerate(island_centers):
            dist = ((player.x - ix) ** 2 + (player.y - iy) ** 2) ** 0.5
            if dist < r:
                if not state.on_wolf_island:
                    state.last_return_pos = (cx, cy + 5)  # Remember return point
                state.on_wolf_island = True
                state.current_island_index = i
                break

        # Wild chicken pickups
        for chick in wild_chickens:
            if chick.collected:
                continue
            dist = ((player.x - chick.x) ** 2 + (player.y - chick.y) ** 2) ** 0.5
            if dist < 1.0:
                chick.collected = True
                state.chickens += chick.value
                # IMPROVED: Particle effect on pickup
                cx_ = chick.x * DISPLAY_TILE
                cy_ = chick.y * DISPLAY_TILE
                for _ in range(6):
                    particles.append(Particle(
                        cx_, cy_, random.uniform(-20, 20), random.uniform(-30, -10),
                        (255, 220, 80), random.uniform(0.4, 0.8), size=2
                    ))
                text = "+1 Chicken" if chick.value == 1 else "+3 Golden Chicken!"
                floating_texts.append(FloatingText(cx_, cy_, text, (255, 220, 50)))

        # Werewolves
        in_combat = False
        for wolf in werewolves:
            wolf.update(player, dt)
            dist = ((player.x - wolf.x) ** 2 + (player.y - wolf.y) ** 2) ** 0.5
            if dist < 0.8:
                player.health -= 60 * dt
                player.last_damage_time = pygame.time.get_ticks()
                in_combat = True
                screen_shake.trigger(2.0, 0.05)

        # Health regeneration when not in combat for 3 seconds
        if not in_combat and pygame.time.get_ticks() - player.last_damage_time > 3000:
            if player.health < player.max_health:
                player.health = min(player.max_health, player.health + 5 * dt)

        # Seagulls
        for gull in seagulls:
            gull.update(dt)

        # Update effects
        screen_shake.update(dt)
        particles = [p for p in particles if p.update(dt)]
        floating_texts = [t for t in floating_texts if t.update(dt)]

        # Death check
        if player.health <= 0:
            player.health = 0
            state.game_over = True

        if state.game_over:
            running = False

        # Render
        visible_npcs = [noah]
        if state.in_black_market:
            visible_npcs.append(merchant)
        visible_npcs.extend(werewolves)
        visible_npcs.extend(chick for chick in wild_chickens if not chick.collected)
        visible_npcs.extend(seagulls)

        shake_offset = screen_shake.get_offset()
        render_world(world, player, visible_npcs, shake_offset)

        # Draw particles and floating text
        cam_pixel_x = player.x * DISPLAY_TILE - SCREEN_W / 2 + shake_offset[0]
        cam_pixel_y = player.y * DISPLAY_TILE - SCREEN_H / 2 + shake_offset[1]
        for p in particles:
            p.draw(screen, cam_pixel_x, cam_pixel_y)
        for t in floating_texts:
            t.draw(screen, cam_pixel_x, cam_pixel_y)

        # Minimap
        draw_minimap(screen, world, player, island_centers, state)

        rain_intensity = compute_rain_intensity(pygame.time.get_ticks() / 1000.0)
        if rain_intensity > 0:
            draw_weather_overlay(screen, rain_drops, rain_intensity, dt)

        draw_hud(screen, state, player)
        pygame.display.flip()

    if state.won:
        show_win_screen(screen)
    elif player.health <= 0:
        show_lose_screen(screen)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
