"""
Kyle Jordan's Maze Adventure (Tile-Based Edition)
---------------------------------------------------
A 700x700 tile world (16px tiles -> 11,200 x 11,200 pixels total).
You can only see roughly a 10-15 tile radius around Kyle at any time.

Story:
    Kyle Jordan loves chicken and is stuck in a magical maze. There's a
    main island, plus a hut hiding a secret black market underneath it.
    Noah Ficsher (18) has been stuck here forever and acts as Kyle's
    guide -- bring him chicken and he gives you materials/gliders to
    reach smaller islands, which are guarded by werewolves.

    Kyle can instead sneak chicken to the wandering Black Market
    Merchant, hidden under a hut: lift the desk, then lift the mat
    underneath it, to reveal the way down. Selling chicken there is
    risky -- 50/50 chance Noah finds out and penalizes Kyle.

    Win condition: sell enough chicken to the merchant, then Kyle goes
    home to find his dog.

Controls:
    WASD / Arrow keys : move
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
pygame.display.set_caption("Kyle Jordan's Maze Adventure")
clock = pygame.time.Clock()
FPS = 60

FONT     = pygame.font.SysFont("monospace", 13)
BIG_FONT = pygame.font.SysFont("monospace", 24, bold=True)
HUD_FONT = pygame.font.SysFont("monospace", 12, bold=True)
DIALOGUE_FONT = pygame.font.SysFont("monospace", 19, bold=True)

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
TREE          = 11   # impassable tree canopy
FLOWER        = 12   # walkable grass with decorative flower
PATH          = 13   # dirt path (walkable)
ROCK          = 14   # impassable boulder
PLAZA         = 15   # stone plaza tile (town square)
FOUNTAIN_00, FOUNTAIN_01, FOUNTAIN_02 = 16, 17, 18
FOUNTAIN_10, FOUNTAIN_11, FOUNTAIN_12 = 19, 20, 21
FOUNTAIN_20, FOUNTAIN_21, FOUNTAIN_22 = 22, 23, 24
FOUNTAIN_TILES = {
    (0, 0): FOUNTAIN_00, (0, 1): FOUNTAIN_01, (0, 2): FOUNTAIN_02,
    (1, 0): FOUNTAIN_10, (1, 1): FOUNTAIN_11, (1, 2): FOUNTAIN_12,
    (2, 0): FOUNTAIN_20, (2, 1): FOUNTAIN_21, (2, 2): FOUNTAIN_22,
}
DOCK          = 25   # wooden dock planks (walkable, over water)
VILLAGE_WALL  = 26   # second building's wall
VILLAGE_FLOOR = 27   # second building's floor
TREE2         = 28   # alternate-colored impassable tree canopy
DEAD_TREE     = 29   # impassable bare/dead tree, for werewolf islands
WOLF_ROCK     = 30   # impassable jagged dark boulder, for werewolf islands
BONES         = 31   # walkable wolf-grass with scattered bones (decorative)
DARK_PATCH    = 32   # walkable scorched/dark grass patch (decorative)
PILING        = 33   # impassable wooden post poking out of the water (decorative, next to docks)
CRATE         = 34   # walkable dock decoration (wooden crate sitting on the planks)
ROPE_COIL     = 35   # walkable dock decoration (coiled rope sitting on the planks)
LANTERN       = 36   # impassable lamp post with a baked-in warm glow (plaza decoration)

SOLID_TILES = {
    HUT_WALL, MARKET_WALL, WATER, TREE, ROCK, VILLAGE_WALL, TREE2,
    DEAD_TREE, WOLF_ROCK, PILING, LANTERN,
} | set(FOUNTAIN_TILES.values())


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
    # A couple of soft light patches
    for _ in range(3):
        cx_, cy_ = rng.randint(2, 13), rng.randint(2, 13)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) <= 1:
                    x, y = cx_ + dx, cy_ + dy
                    if 0 <= x < TILE and 0 <= y < TILE:
                        surf.set_at((x, y), light)
    # A couple of soft shadow patches
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
    "WWwWbWwWWwbWWwWW",
    "wWbbWwwbWWwWbWwW",
    "WbWwWWbbWwWWwbWW",
    "bWWwWWwWbWWwWWbW",
    "WwbWWwgWwbWWwWbw",
    "WwWwbWWwWwbWWwWW",
    "bWWWwWWbbWwWWwWb",
    "wWbWWwWWwbWWwWWw",
    "WWwWbWgwgWbWWwWW",
    "bWWwWWbWwWWwWWbW",
    "wWbWWwWWwwWWwWWw",
    "WwWbWWwWWwbWWwWW",
    "WWbWWwWWbWWwWWbW",
    "bWWwWWbWwWWbWWwW",
    "wWbWWwWWwbWWwWWb",
    "WWwbWWwWWwbWWwWW",
], {"W": (45,105,195), "w": (60,125,215), "b": (32,85,178), "g": (148,205,255)})

_SAND = _make_tile([
    "SSsSSSdSSsSSSdSS",
    "sSdSSSSsSdSSSSsS",
    "SSSSdSSSSSSdSSSS",
    "dSSsSSSdSSsSSSdS",
    "SSSSSdSSSSSSdSSS",
    "sSSSdSSsSSSdSsSS",
    "SSdSSSSSSdSSSSdS",
    "SSSsSSSdSSSsSSSd",
    "dSSSSdSSSSSSdSSS",
    "SSsSSSdSSSsSSSdS",
    "SSSdSSSSdSSSSSSS",
    "sSSSdSsSSSdSSSsS",
    "SSSSSSdSSSSSSdSS",
    "dSSsSSSdSSsSSSdS",
    "SSSSSdSSSSSSdSSS",
    "SSsSSSdSSsSSSdSS",
], {"S": (215,190,140), "s": (228,205,155), "d": (195,170,118)})

_PATH = _make_tile([
    "PPlPPpPPlPPpPPlP",
    "lPpPPPPlPpPPPPlP",
    "PPPPpPPPPPPpPPPP",
    "pPPlPPPpPPlPPPpP",
    "PPPPPpPPPPPPpPPP",
    "lPPPpPPlPPPpPlPP",
    "PPpPPPPPPpPPPPpP",
    "PPPlPPPpPPPlPPPp",
    "pPPPPpPPPPPPpPPP",
    "PPlPPPpPPPlPPPpP",
    "PPPpPPPPpPPPPPPP",
    "lPPPpPlPPPpPPPlP",
    "PPPPPPpPPPPPPpPP",
    "pPPlPPPpPPlPPPpP",
    "PPPPPpPPPPPPpPPP",
    "PPlPPPpPPlPPPpPP",
], {"P": (155,115,72), "p": (138,98,58), "l": (172,132,89)})

_HUT_FLOOR = _make_tile([
    "wWwWwWwWwWwWwWwW",
    "WWdWWdWWdWWdWWdW",
    "WgWgWWgWgWWgWgWg",
    "dWWdWWdWWdWWdWWd",
    "WwWwWwWwWwWwWwWw",
    "WdWWdWWdWWdWWdWW",
    "gWgWgWgWgWgWgWgW",
    "dWWdWWdWWdWWdWWd",
    "wWwWwWwWwWwWwWwW",
    "WWdWWdWWdWWdWWdW",
    "WgWgWWgWgWWgWgWg",
    "dWWdWWdWWdWWdWWd",
    "WwWwWwWwWwWwWwWw",
    "WdWWdWWdWWdWWdWW",
    "gWgWgWgWgWgWgWgW",
    "dWWdWWdWWdWWdWWd",
], {"W": (175,128,75), "w": (190,142,88), "d": (148,105,58), "g": (125,88,42)})

_HUT_WALL = _make_tile([
    "RrRRRdRrRRRdRrRR",
    "dRrRRRdRrRRRdRrR",
    "RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR",
    "RrRRRdRrRRRdRrRR",
    "dRrRRRdRrRRRdRrR",
    "RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR",
    "RrRRRdRrRRRdRrRR",
    "dRrRRRdRrRRRdRrR",
    "RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR",
    "RrRRRdRrRRRdRrRR",
    "dRrRRRdRrRRRdRrR",
    "RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR",
], {"R": (148,65,38), "r": (172,82,48), "d": (115,50,25)})

_MARKET_FLOOR = _make_tile([
    "SSSSSSSdSSSSSSdS",
    "sSdSSSSSsSdSSSsS",
    "SSSdSSSSSSSdSSSS",
    "SSSSdSSSSSSSdSSS",
    "gggggggggggggggg",
    "SSSSSSSdSSSSSSdS",
    "sSSSdSSSsSSSdSSS",
    "SSSSSSSSdSSSSSSS",
    "SSdSSSSSSSdSSSsS",
    "gggggggggggggggg",
    "SSSSSdSSSSSSdSSS",
    "sSSSSSSSsSSSSSdS",
    "SSdSSSSSSSdSSSsS",
    "SSSSSSSdSSSSSSdS",
    "gggggggggggggggg",
    "SSSSSdSSSSSSdSSS",
], {"S": (55,45,72), "s": (68,58,88), "d": (40,32,55), "g": (28,22,40)})

_MARKET_WALL = _make_tile([
    "DDddDDddDDddDDdd",
    "dDDcDddDDcDddDDc",
    "DddcDDddcDDddcDD",
    "ddDDcddDDcddDDcd",
    "cDDddcDDddcDDddc",
    "DddDDcddDDcddDDc",
    "ddcDDddcDDddcDDd",
    "DDcddDDcddDDcddd",
    "DDddDDddDDddDDdd",
    "dDDcDddDDcDddDDc",
    "DddcDDddcDDddcDD",
    "ddDDcddDDcddDDcd",
    "cDDddcDDddcDDddc",
    "DddDDcddDDcddDDc",
    "ddcDDddcDDddcDDd",
    "DDcddDDcddDDcddd",
], {"D": (30,22,40), "d": (40,32,52), "c": (50,40,65)})

_TRAPDOOR = _make_tile([
    "DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb",
    "DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb",
    "DDgDDDDDDDDgDDDD",
    "DbDbgbDbDbgbDbDb",
    "DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb",
    "gDDDDgDDDDgDDDDg",
    "DbDbDbDbDbDbDbDb",
    "DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb",
    "DDgDDDDDDDDgDDDD",
    "DbDbgbDbDbgbDbDb",
    "DDDDDDDDDDDDDdDD",
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
    """Grass tile with two tiny pixel-art flowers."""
    img = _GRASS.copy()
    # White daisy at (7, 5)
    img.set_at((7, 4), (252, 252, 252))
    img.set_at((6, 5), (252, 252, 252)); img.set_at((7, 5), (248, 215, 35)); img.set_at((8, 5), (252, 252, 252))
    img.set_at((7, 6), (252, 252, 252))
    # Pink flower at (3, 11)
    img.set_at((3, 10), (252, 220, 240))
    img.set_at((2, 11), (252, 220, 240)); img.set_at((3, 11), (248, 165, 215)); img.set_at((4, 11), (252, 220, 240))
    img.set_at((3, 12), (252, 220, 240))
    return img

def _make_tree():
    """Round tree canopy viewed from above, blended onto a grass base so the
    transparent corners don't show through as black."""
    img = _GRASS.copy()
    rows = [
        "....sDDDDDDs....",
        "...DGGgGGGGGDs..",
        "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",
        ".DGGGhGGGGhGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.",
        "...sDDGGGGDDs...",
        "....sssDDsss....",
        "................",
    ]
    overlay = make_surface(rows, {
        ".": None,
        "D": (28,100,35), "G": (50,145,58), "g": (72,178,82),
        "h": (95,210,108), "t": (100,70,38), "s": (18,78,24),
    })
    img.blit(overlay, (0, 0))
    return img

def _make_tree2():
    """An autumn/golden-colored canopy variant, blended onto a grass base."""
    img = _GRASS.copy()
    rows = [
        "....sDDDDDDs....",
        "...DGGgGGGGGDs..",
        "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",
        ".DGGGhGGGGhGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.",
        "...sDDGGGGDDs...",
        "....sssDDsss....",
        "................",
    ]
    overlay = make_surface(rows, {
        ".": None,
        "D": (140,80,20), "G": (205,140,40), "g": (225,170,60),
        "h": (240,195,90), "t": (100,70,38), "s": (95,55,15),
    })
    img.blit(overlay, (0, 0))
    return img

def _make_tree_canopy_overlay():
    """Just the transparent-background canopy shape for TREE, with no
    grass baked in -- used for the wind-sway animation so a rotated tree
    reveals the organic terrain's grass underneath instead of dragging a
    mismatched flat-grass square along with it."""
    rows = [
        "....sDDDDDDs....",
        "...DGGgGGGGGDs..",
        "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",
        ".DGGGhGGGGhGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.",
        "...sDDGGGGDDs...",
        "....sssDDsss....",
        "................",
    ]
    return make_surface(rows, {
        ".": None,
        "D": (28,100,35), "G": (50,145,58), "g": (72,178,82),
        "h": (95,210,108), "t": (100,70,38), "s": (18,78,24),
    })

def _make_tree2_canopy_overlay():
    """Same idea as _make_tree_canopy_overlay(), for the autumn/golden
    TREE2 variant."""
    rows = [
        "....sDDDDDDs....",
        "...DGGgGGGGGDs..",
        "..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",
        ".DGGGhGGGGhGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",
        ".DGGGGGttGGGGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",
        ".DGGGGGGGGGGGGGs",
        ".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.",
        "...sDDGGGGDDs...",
        "....sssDDsss....",
        "................",
    ]
    return make_surface(rows, {
        ".": None,
        "D": (140,80,20), "G": (205,140,40), "g": (225,170,60),
        "h": (240,195,90), "t": (100,70,38), "s": (95,55,15),
    })


def _make_rock():
    """A grey boulder sitting on grass, impassable."""
    img = _GRASS.copy()
    rows = [
        "....sssssss....",
        "...sRRRRRRRs...",
        "..sRRrRRRrRRs..",
        ".sRRRRRRRRRRRs.",
        ".sRrRRRRRRrRRs.",
        "sRRRRRRRRRRRRRs",
        "sRRRrRRRRRrRRRs",
        "sRRRRRRRRRRRRRs",
        ".sRRRRrRRRRRRs.",
        ".sRRRRRRRRRRs..",
        "..ssRRRRRRsss..",
        "...sssssssss...",
        "................",
        "................",
        "................",
        "................",
    ]
    palette = {".": None, "s": (70,65,68), "R": (130,128,132), "r": (155,152,158)}
    overlay = make_surface(rows, palette)
    img.blit(overlay, (0, 0))
    return img

def _make_plaza():
    """Stone-paved plaza tile, walkable, for the town square."""
    return _make_tile([
        "MmMMMmMMmMMMmMMm",
        "mMmMMmMMmMMmMMmM",
        "MMMmMMmMMMmMMmMM",
        "mMMMmMMmMMMmMMmM",
        "MmMMmMMMmMMmMMMm",
        "MMmMMMmMMmMMMmMM",
        "mMMmMMMmMMmMMMmM",
        "MMMmMMmMMMmMMmMM",
        "mMmMMmMMmMMmMMmM",
        "MMMmMMmMMMmMMmMM",
        "mMMMmMMmMMMmMMmM",
        "MmMMmMMMmMMmMMMm",
        "MMmMMMmMMmMMMmMM",
        "mMMmMMMmMMmMMMmM",
        "MMMmMMmMMMmMMmMM",
        "mMmMMmMMmMMmMMmM",
    ], {"M": (168,160,148), "m": (148,140,130)})

def _make_fountain_tile(row_in_grid, col_in_grid, size=3):
    """Builds ONE 16x16 tile that is a piece of a larger size x size fountain,
    so the full fountain reads as a single round basin instead of `size*size`
    repeated copies of the same image. (row_in_grid, col_in_grid) is this
    tile's position within the fountain (0-indexed)."""
    img = _make_plaza()

    # Work in a "logical" 16*size x 16*size canvas, draw the whole basin once,
    # then crop out just this tile's slice.
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
            # else: leave transparent so the plaza tile shows through

    slice_x = col_in_grid * TILE
    slice_y = row_in_grid * TILE
    overlay = canvas.subsurface((slice_x, slice_y, TILE, TILE)).copy()
    img.blit(overlay, (0, 0))
    return img

def _make_dock():
    """Wooden dock planks, walkable, used to extend paths out over water."""
    return _make_tile([
        "wwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDD",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDD",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDD",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDD",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDD",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
    ], {"w": (172,132,80), "D": (130,95,55)})

def _make_village_floor():
    img = _HUT_FLOOR.copy()
    return img

def _make_piling():
    """A wooden post poking up out of the water, for visual detail
    alongside the dock. Sits on a tile that's otherwise plain water, so it
    doesn't introduce any new collision behavior beyond what water already
    has (blocked without a glider)."""
    img = _WATER.copy()
    rows = [
        "................",
        "................",
        ".......DD.......",
        "......DddD......",
        "......DddD......",
        "......DddD......",
        "......DddD......",
        "......DddD......",
        ".....DDddDD.....",
        "......ddd.......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "D": (90, 60, 32), "d": (118, 82, 44)})
    img.blit(overlay, (0, 0))
    return img

def _make_crate():
    """A wooden crate sitting on the dock -- purely decorative, drawn on
    top of the regular dock-plank art."""
    img = _make_dock()
    pygame.draw.rect(img, (152, 110, 60), (3, 4, 10, 9))
    pygame.draw.rect(img, (108, 74, 38), (3, 4, 10, 9), 1)
    pygame.draw.line(img, (108, 74, 38), (3, 8), (12, 8))
    pygame.draw.line(img, (108, 74, 38), (8, 4), (8, 12))
    return img

def _make_rope_coil():
    """A coiled rope resting on the dock -- purely decorative."""
    img = _make_dock()
    pygame.draw.circle(img, (198, 170, 112), (8, 8), 5, 2)
    pygame.draw.circle(img, (198, 170, 112), (8, 8), 3, 1)
    pygame.draw.circle(img, (160, 130, 80), (8, 8), 1)
    return img

def _make_lantern():
    """A lamp post for the plaza, with a soft warm halo baked right into
    the tile art so it doesn't need any per-frame lighting pass."""
    img = _make_plaza()
    halo = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    center = (8, 5)
    for r, alpha in ((6, 35), (4, 65), (2, 110)):
        pygame.draw.circle(halo, (255, 200, 110, alpha), center, r)
    img.blit(halo, (0, 0))
    pygame.draw.rect(img, (60, 45, 30), (7, 8, 2, 7))       # post
    pygame.draw.rect(img, (40, 32, 24), (5, 3, 6, 5))        # lamp housing
    pygame.draw.rect(img, (255, 225, 140), (6, 4, 4, 3))     # lit glass
    return img

def _make_village_wall():
    """A second building's wall, in a different stone tone than the merchant's hut."""
    return _make_tile([
        "GgGGGdGgGGGdGgGG",
        "dGgGGGdGgGGGdGgG",
        "GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG",
        "GgGGGdGgGGGdGgGG",
        "dGgGGGdGgGGGdGgG",
        "GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG",
        "GgGGGdGgGGGdGgGG",
        "dGgGGGdGgGGGdGgG",
        "GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG",
        "GgGGGdGgGGGdGgGG",
        "dGgGGGdGgGGGdGgG",
        "GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG",
    ], {"G": (120,118,115), "g": (140,138,135), "d": (95,92,88)})

def _make_dead_tree():
    """A bare, leafless tree -- impassable, used on werewolf islands for a
    wilder/more menacing feel than the main island's lush canopies."""
    img = _WOLF_GRASS.copy()
    rows = [
        "................",
        "................",
        ".......t........",
        "......ttt.......",
        "....t..t..t.....",
        ".....t.t.t......",
        "......ttt.......",
        "....tt.t.tt.....",
        ".....tttt.......",
        "......ttt.......",
        "................",
        "................",
        "......ttt.......",
        "................",
        "................",
        "................",
    ]
    overlay = make_surface(rows, {".": None, "t": (75, 60, 48)})
    img.blit(overlay, (0, 0))
    return img

def _make_wolf_rock():
    """A jagged, dark boulder for werewolf islands -- sharper and darker
    than the main island's rounded rocks, to feel more dangerous."""
    img = _WOLF_GRASS.copy()
    rows = [
        "................",
        "......s.ss......",
        ".....sRRRRs.....",
        "....sRrRRRRs....",
        "...sRRRRrRRRs...",
        "..sRRrRRRRRRRs..",
        "..sRRRRRrRRRRs..",
        "..sRRRRRRRrRRs..",
        "...sRrRRRRRRs...",
        "....sRRRrRRs....",
        ".....sRRRRs.....",
        "......sssss.....",
        "................",
        "................",
        "................",
        "................",
    ]
    palette = {".": None, "s": (35,32,34), "R": (78,75,80), "r": (95,92,98)}
    overlay = make_surface(rows, palette)
    img.blit(overlay, (0, 0))
    return img

def _make_bones():
    """Wolf-grass with a scattered bone pile -- walkable decoration hinting
    at past victims."""
    img = _WOLF_GRASS.copy()
    rows = [
        "................",
        "................",
        "....b.......b...",
        "...bWb.....bWb..",
        "....b...WW..b...",
        ".......WbbW.....",
        "......WbbbbW....",
        ".b...WbbbbbW..b.",
        "bWb...WbbbW..bWb",
        ".b.....WW....b..",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]
    palette = {".": None, "W": (225, 220, 205), "b": (200, 195, 175)}
    overlay = make_surface(rows, palette)
    img.blit(overlay, (0, 0))
    return img

def _make_dark_patch():
    """A scorched/dark patch of wolf-grass -- walkable, purely decorative,
    suggests werewolf activity (old fire pit, claw-torn earth, etc)."""
    img = _WOLF_GRASS.copy()
    rng = random.Random(99)
    for _ in range(40):
        x, y = rng.randint(1, 14), rng.randint(1, 14)
        shade = rng.randint(25, 45)
        img.set_at((x, y), (shade, shade - 5, shade - 8))
    return img

TILE_IMAGES = {
    GRASS:        _GRASS,
    WOLF_GRASS:   _WOLF_GRASS,
    WATER:        _WATER,
    SAND:         _SAND,
    PATH:         _PATH,
    HUT_FLOOR:    _HUT_FLOOR,
    HUT_WALL:     _HUT_WALL,
    MARKET_FLOOR: _MARKET_FLOOR,
    MARKET_WALL:  _MARKET_WALL,
    TRAPDOOR_OPEN:_TRAPDOOR,
    DESK:         _make_desk(),
    MAT:          _make_mat(),
    FLOWER:       _make_flower(),
    TREE:         _make_tree(),
    TREE2:        _make_tree2(),
    ROCK:         _make_rock(),
    PLAZA:        _make_plaza(),
    DOCK:         _make_dock(),
    VILLAGE_WALL: _make_village_wall(),
    VILLAGE_FLOOR:_make_village_floor(),
    DEAD_TREE:    _make_dead_tree(),
    WOLF_ROCK:    _make_wolf_rock(),
    BONES:        _make_bones(),
    DARK_PATCH:   _make_dark_patch(),
    PILING:       _make_piling(),
    CRATE:        _make_crate(),
    ROPE_COIL:    _make_rope_coil(),
    LANTERN:      _make_lantern(),
}

# Register the 3x3 fountain as 9 distinct tiles, each a slice of one
# cohesive round basin, rather than 9 copies of the same image.
for (_row, _col), _tile_id in FOUNTAIN_TILES.items():
    TILE_IMAGES[_tile_id] = _make_fountain_tile(_row, _col, size=3)


# ---- Character / NPC sprites (16x16 pixel art, scaled 2× for display) ------
def make_kyle():
    p = {
        ".": None, "k": (45, 32, 22), "f": (238, 205, 175),
        "b": (55, 95, 210), "d": (32, 62, 158), "w": (255, 255, 255),
        "n": (30, 22, 15),
    }
    rows = [
        "....nnnnnnnn....",
        "...nkkkkkkkkn...",
        "...kfffffffkk...",
        "..kffwf.wfffk...",
        "...ffffffff.k...",
        "....ffffffff....",
        "...bbbbbbbbbb...",
        "..bbbbbbbbbbbb..",
        "..bbbbbbbbbbbb..",
        "..bbbddddddbb...",
        "..bb........bb..",
        "..bb........bb..",
        "..kk........kk..",
        "..nn........nn..",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_noah():
    """Wild-haired survivor look, based on a reference image: messy brown
    hair, beard, green eyes, dark open vest over a tan torso, and a spear
    with a leaf-wrapped tip held to his side."""
    p = {
        ".": None,
        "k": (58, 42, 28),    # hair
        "K": (45, 32, 20),    # hair shadow
        "f": (212, 168, 128),  # face/skin
        "F": (185, 142, 105),  # skin shadow
        "e": (60, 150, 80),   # green eyes
        "b": (50, 38, 26),    # beard
        "v": (40, 55, 95),    # dark blue vest
        "V": (30, 42, 75),    # vest shadow
        "t": (190, 150, 105),  # tan torso/undershirt
        "p": (120, 95, 65),   # pants
        "P": (95, 75, 50),    # pants shadow
        "s": (150, 150, 155),  # spear head (metal)
        "w": (100, 70, 40),   # spear shaft (wood)
        "l": (70, 150, 60),   # leaf
    }
    rows = [
        "....kKkk.kk.....",
        "...kkkkkkkkKk...",
        "..kkkkkkkkkkkk..",
        "..kKffffffFkk...",
        ".sKffeffeFfk....",
        "lwKffffffFk.....",
        ".w.bbbbbbbk.....",
        "w..bbbbbbb......",
        "w..vvVtttvv.....",
        "..vvvVtttVvv....",
        "..vvVVVVvv......",
        "...ppFFpp.......",
        "..ppP..Ppp......",
        "..pp....pp......",
        "..PP....PP......",
        "................",
    ]
    return make_surface(rows, p)


def make_merchant():
    p = {
        ".": None, "h": (95, 42, 128), "s": (62, 28, 90),
        "f": (42, 32, 38), "g": (218, 182, 65), "e": (155, 105, 200),
    }
    rows = [
        "....hhhhhhhh....",
        "...hhhhhhhhhh...",
        "..hhhhffffhhhh..",
        "..hhhfe..efhhh..",
        "..hhhffffffhh...",
        "...hhhhhhhhhh...",
        "...hhssssshh....",
        "..hhssssssshh...",
        "..hhssgsssssh...",
        "..hhssssssshh...",
        "..hh........hh..",
        "..hh........hh..",
        "..ss........ss..",
        "..ss........ss..",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_werewolf():
    p = {
        ".": None, "g": (100, 98, 108), "d": (58, 58, 65),
        "r": (215, 45, 45), "w": (238, 238, 238), "y": (255, 210, 55),
    }
    rows = [
        "...g......g.....",
        "..ggg....ggg....",
        "..gggggggggg....",
        ".ggryggggyrggg..",
        ".gggggwgggggg...",
        ".gggggwgggggg...",
        "..gggggggggg....",
        "..gdgggggggd....",
        ".ggdgggggggdg...",
        ".ggdgggggggdg...",
        "..gd........dg..",
        "..gd........dg..",
        "..dd........dd..",
        "..dd........dd..",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_chicken():
    p = {".": None, "w": (255, 255, 255), "y": (240, 195, 45), "r": (215, 55, 45), "o": (248, 175, 55)}
    rows = [
        "......oooo......",
        ".....owwwwo.....",
        "....owwwwwwo....",
        "....rwwwwwww....",
        "....wwwwwwww....",
        "....wwwwwwww....",
        ".....wwwwww.....",
        ".....yy.yy......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_golden_chicken():
    """A rarer, shinier chicken variant -- same silhouette as the regular
    chicken, recolored gold with a small sparkle, worth more chicken when
    collected."""
    p = {".": None, "w": (255, 226, 130), "y": (255, 195, 30), "r": (215, 55, 45),
         "o": (255, 165, 40), "s": (255, 255, 220)}
    rows = [
        "......oooo......",
        ".....owwwwo..s..",
        "....owwwwwwo....",
        "....rwwwwwww....",
        "....wwwwwwww....",
        "s...wwwwwwww....",
        ".....wwwwww.....",
        ".....yy.yy......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_seagull():
    """A small gull silhouette in flight -- two simple wing strokes, no
    body detail needed since it reads fine at this scale while circling."""
    p = {".": None, "w": (248, 248, 250)}
    rows = [
        "................",
        "................",
        "................",
        "....ww....ww....",
        "...www....www...",
        "..ww........ww..",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]
    return make_surface(rows, p)


SPRITES = {
    "kyle":     make_kyle(),
    "noah":     make_noah(),
    "merchant": make_merchant(),
    "werewolf": make_werewolf(),
    "chicken":  make_chicken(),
    "golden_chicken": make_golden_chicken(),
    "seagull":  make_seagull(),
}

# Scale all tiles and sprites up to DISPLAY_TILE (32 px) for crisp pixel-art look
for _k in list(TILE_IMAGES.keys()):
    TILE_IMAGES[_k] = pygame.transform.scale(TILE_IMAGES[_k], (DISPLAY_TILE, DISPLAY_TILE))
SPRITES = {k: pygame.transform.scale(v, (DISPLAY_TILE, DISPLAY_TILE)) for k, v in SPRITES.items()}

# Canopy-only overlays (transparent background, no baked grass) for the
# wind-sway tree animation -- kept separate from TILE_IMAGES so rotating
# one doesn't drag a mismatched flat-grass square along with it.
TREE_CANOPY = {
    TREE: pygame.transform.scale(_make_tree_canopy_overlay(), (DISPLAY_TILE, DISPLAY_TILE)),
    TREE2: pygame.transform.scale(_make_tree2_canopy_overlay(), (DISPLAY_TILE, DISPLAY_TILE)),
}


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------
def generate_world():
    """Builds a 700x700 tile grid: an ocean with a big main island plus a
    few smaller werewolf islands scattered around it."""
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

    # Scatter a few smaller werewolf islands around the main island
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
    """Carves a small 5x4 hut on the main island at (hx, hy), with a desk and
    mat inside that hide the entrance to the black market below.

    BUGFIX: this used to wall off the hut completely with no doorway, so
    there was no way to walk inside and reach the desk. Now leaves a gap
    in the middle of the south wall as an entrance."""
    w, h = 5, 4
    for y in range(hy - 1, hy + h + 1):
        for x in range(hx - 1, hx + w + 1):
            on_border = (
                x == hx - 1 or x == hx + w or y == hy - 1 or y == hy + h
            )
            world[y][x] = HUT_WALL if on_border else HUT_FLOOR

    # Doorway: open a gap in the south wall so Kyle can actually get inside.
    door_x, door_y = hx + w // 2, hy + h
    world[door_y][door_x] = HUT_FLOOR

    desk_pos = (hx + w // 2, hy + h // 2)
    world[desk_pos[1]][desk_pos[0]] = DESK
    return desk_pos


def carve_market_room(world, mx, my):
    w, h = 7, 6
    for y in range(my - 1, my + h + 1):
        for x in range(mx - 1, mx + w + 1):
            on_border = (
                x == mx - 1 or x == mx + w or y == my - 1 or y == my + h
            )
            world[y][x] = MARKET_WALL if on_border else MARKET_FLOOR


def carve_village_hut(world, vx, vy, w=4, h=4):
    """A second, smaller building near the plaza -- just for visual variety,
    no interaction tied to it (yet). Also fixed to have a doorway, matching
    the merchant hut fix."""
    for y in range(vy - 1, vy + h + 1):
        for x in range(vx - 1, vx + w + 1):
            on_border = (
                x == vx - 1 or x == vx + w or y == vy - 1 or y == vy + h
            )
            world[y][x] = VILLAGE_WALL if on_border else VILLAGE_FLOOR
    door_x, door_y = vx + w // 2, vy + h
    world[door_y][door_x] = VILLAGE_FLOOR


def carve_plaza(world, cx, cy, radius=9):
    """Stone town-square plaza with a fountain centerpiece, near the
    middle of the main island."""
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d < radius:
                world[y][x] = PLAZA

    # Place the fountain as one cohesive 3x3 block of distinct tiles (each
    # tile is a slice of a single round basin) instead of repeating one
    # fountain image across multiple tiles.
    fountain_size = 3
    top_left_x = cx - fountain_size // 2
    top_left_y = cy - fountain_size // 2
    for row in range(fountain_size):
        for col in range(fountain_size):
            world[top_left_y + row][top_left_x + col] = FOUNTAIN_TILES[(row, col)]


def decorate_plaza_lanterns(world, cx, cy, offset=6):
    """Places four lamp posts around the plaza, diagonally offset from the
    fountain so they don't sit on the cardinal paths leading in/out."""
    for ddx, ddy in ((offset, offset), (-offset, offset), (offset, -offset), (-offset, -offset)):
        lx, ly = cx + ddx, cy + ddy
        if 0 <= lx < MAP_W and 0 <= ly < MAP_H and world[ly][lx] == PLAZA:
            world[ly][lx] = LANTERN


def carve_dock(world, shore_x, shore_y, direction, length=10):
    """Extends a straight line of dock tiles out over the water from a
    point near the shore, in the given (dx, dy) direction."""
    dx, dy = direction
    x, y = shore_x, shore_y
    for _ in range(length):
        x += dx
        y += dy
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            world[y][x] = DOCK
            # widen the dock by one tile perpendicular to its direction
            px, py = x - dy, y + dx
            if 0 <= px < MAP_W and 0 <= py < MAP_H:
                world[py][px] = DOCK


def decorate_dock(world, shore_x, shore_y, direction, length=10):
    """Adds purely visual detail to a dock built by carve_dock(): wooden
    pilings poking out of the water on both open edges, plus a crate and a
    coil of rope resting on the planks. None of this changes gameplay --
    pilings occupy water tiles that were already impassable without a
    glider, and the crate/rope are drawn on tiles that stay walkable."""
    dx, dy = direction
    x, y = shore_x, shore_y
    for i in range(length):
        x += dx
        y += dy

        # The two open-water tiles just outside the 2-tile-wide dock band
        # (mirrors the perpendicular offset carve_dock uses to widen the dock).
        outer1_x, outer1_y = x + dy, y - dx
        outer2_x, outer2_y = x - 2 * dy, y + 2 * dx

        if i % 3 == 1:
            if 0 <= outer1_x < MAP_W and 0 <= outer1_y < MAP_H and world[outer1_y][outer1_x] == WATER:
                world[outer1_y][outer1_x] = PILING
            if 0 <= outer2_x < MAP_W and 0 <= outer2_y < MAP_H and world[outer2_y][outer2_x] == WATER:
                world[outer2_y][outer2_x] = PILING

        # A crate near the shore end and a rope coil a bit further out,
        # placed only if that tile is still plain dock (don't overwrite).
        if i == 2 and 0 <= x < MAP_W and 0 <= y < MAP_H and world[y][x] == DOCK:
            world[y][x] = CRATE
        if i == 5 and 0 <= x < MAP_W and 0 <= y < MAP_H and world[y][x] == DOCK:
            world[y][x] = ROPE_COIL


def _carve_straight_path(world, start, end):
    """Carves a walkable PATH line (3 tiles wide) between two points on GRASS."""
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
    """Add a town plaza, a second building, a dock, coastal rocks, paths,
    and tree/flower groves to the main island for visual richness."""
    rng = random.Random(7)

    # --- town plaza with fountain, placed between player start and hut ---
    plaza_x, plaza_y = cx, cy - 2
    carve_plaza(world, plaza_x, plaza_y, radius=9)
    decorate_plaza_lanterns(world, plaza_x, plaza_y)

    # --- a second village building near the plaza, opposite the merchant hut ---
    village_x, village_y = cx - 22, cy - 10
    carve_village_hut(world, village_x, village_y)

    # --- paths connecting player start -> plaza -> hut -> village ---
    player_start = (cx, cy + 5)
    _carve_straight_path(world, player_start, (plaza_x, plaza_y + 9))
    _carve_straight_path(world, (plaza_x, plaza_y), (hut_x + 2, hut_y + 5))
    _carve_straight_path(world, (plaza_x, plaza_y), (village_x + 2, village_y + 4))

    # --- a dock poking out into the water from the southeast shoreline ---
    dock_angle = 0.9  # radians, points toward southeast-ish shore
    shore_x = int(cx + main_radius * 0.95 * math.cos(dock_angle))
    shore_y = int(cy + main_radius * 0.95 * math.sin(dock_angle))
    carve_dock(world, shore_x, shore_y, direction=(1, 0), length=12)
    decorate_dock(world, shore_x, shore_y, direction=(1, 0), length=12)
    _carve_straight_path(world, (cx, cy), (shore_x - 3, shore_y))

    # --- scatter rocks near the coastline (echoes a rocky/canyon edge) ---
    rock_set = set()
    for _ in range(8000):
        rx = rng.randint(0, MAP_W - 1)
        ry = rng.randint(0, MAP_H - 1)
        if world[ry][rx] != GRASS and world[ry][rx] != SAND:
            continue
        dist_c = ((rx - cx) ** 2 + (ry - cy) ** 2) ** 0.5
        if not (main_radius * 0.75 < dist_c < main_radius * 0.98):
            continue
        if any(((rx - ox) ** 2 + (ry - oy) ** 2) < 30 for ox, oy in rock_set):
            continue
        if world[ry][rx] == GRASS:
            world[ry][rx] = ROCK
        rock_set.add((rx, ry))
        if len(rock_set) >= 55:
            break

    # --- tree groves: pick a handful of grove centers, cluster trees around them ---
    tree_set = set()
    grove_centers = []
    for _ in range(10):
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(main_radius * 0.2, main_radius * 0.8)
        gx = int(cx + dist * math.cos(angle))
        gy = int(cy + dist * math.sin(angle))
        grove_centers.append((gx, gy))

    for (gx, gy) in grove_centers:
        use_alt_color = rng.random() < 0.4
        trees_in_grove = rng.randint(8, 16)
        attempts = 0
        placed = 0
        while placed < trees_in_grove and attempts < 200:
            attempts += 1
            tx = gx + rng.randint(-8, 8)
            ty = gy + rng.randint(-8, 8)
            if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
                continue
            if world[ty][tx] != GRASS:
                continue
            dist_c = ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5
            if dist_c < 12 or dist_c > main_radius * 0.92:
                continue
            if ((tx - hut_x) ** 2 + (ty - hut_y) ** 2) ** 0.5 < 12:
                continue
            if ((tx - village_x) ** 2 + (ty - village_y) ** 2) ** 0.5 < 10:
                continue
            if ((tx - plaza_x) ** 2 + (ty - plaza_y) ** 2) ** 0.5 < 11:
                continue
            if any(((tx - ox) ** 2 + (ty - oy) ** 2) < 9 for ox, oy in tree_set):
                continue
            world[ty][tx] = TREE2 if use_alt_color else TREE
            tree_set.add((tx, ty))
            placed += 1

    # --- scatter flowers across open grass ---
    flower_count = 0
    for _ in range(5000):
        fx = rng.randint(0, MAP_W - 1)
        fy = rng.randint(0, MAP_H - 1)
        if world[fy][fx] != GRASS:
            continue
        dist_c = ((fx - cx) ** 2 + (fy - cy) ** 2) ** 0.5
        if dist_c > main_radius * 0.85 or dist_c < 4:
            continue
        world[fy][fx] = FLOWER
        flower_count += 1
        if flower_count >= 120:
            break

    return plaza_x, plaza_y, village_x, village_y, shore_x, shore_y


def decorate_wolf_island(world, ix, iy, r, seed=0):
    """Add dead trees, jagged rocks, bone piles, and dark scorched patches to
    a werewolf island, in a wilder/more menacing style than the main island.

    Decoration is kept to the outer ring of the island (beyond ~55% of its
    radius) so the center stays clear for werewolf chasing and combat.
    """
    rng = random.Random(seed)
    inner_clear_radius = r * 0.55

    occupied = set()

    def _far_enough(x, y, min_dist_sq=9):
        return not any(((x - ox) ** 2 + (y - oy) ** 2) < min_dist_sq for ox, oy in occupied)

    # --- dead trees, scattered around the outer ring ---
    dead_tree_count = rng.randint(4, 8)
    placed = 0
    attempts = 0
    while placed < dead_tree_count and attempts < 150:
        attempts += 1
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(inner_clear_radius, r * 0.9)
        tx = int(ix + dist * math.cos(angle))
        ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
            continue
        if world[ty][tx] != WOLF_GRASS:
            continue
        if not _far_enough(tx, ty, 16):
            continue
        world[ty][tx] = DEAD_TREE
        occupied.add((tx, ty))
        placed += 1

    # --- jagged rocks, scattered around the outer ring ---
    rock_count = rng.randint(3, 6)
    placed = 0
    attempts = 0
    while placed < rock_count and attempts < 150:
        attempts += 1
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(inner_clear_radius, r * 0.92)
        tx = int(ix + dist * math.cos(angle))
        ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
            continue
        if world[ty][tx] != WOLF_GRASS:
            continue
        if not _far_enough(tx, ty, 16):
            continue
        world[ty][tx] = WOLF_ROCK
        occupied.add((tx, ty))
        placed += 1

    # --- bone piles, walkable decoration, anywhere on the island ---
    bone_count = rng.randint(2, 4)
    placed = 0
    attempts = 0
    while placed < bone_count and attempts < 100:
        attempts += 1
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(0, r * 0.85)
        tx = int(ix + dist * math.cos(angle))
        ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
            continue
        if world[ty][tx] != WOLF_GRASS:
            continue
        if not _far_enough(tx, ty, 12):
            continue
        world[ty][tx] = BONES
        occupied.add((tx, ty))
        placed += 1

    # --- dark scorched patches, walkable, anywhere on the island ---
    patch_count = rng.randint(3, 6)
    placed = 0
    attempts = 0
    while placed < patch_count and attempts < 100:
        attempts += 1
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(0, r * 0.85)
        tx = int(ix + dist * math.cos(angle))
        ty = int(iy + dist * math.sin(angle))
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
            continue
        if world[ty][tx] != WOLF_GRASS:
            continue
        if not _far_enough(tx, ty, 10):
            continue
        world[ty][tx] = DARK_PATCH
        occupied.add((tx, ty))
        placed += 1


def spawn_wild_chickens(world, cx, cy, main_radius, hut_x, hut_y, village_x, village_y,
                          plaza_x, plaza_y, count=5, seed=42):
    """Scatters a few loose, pickupable chickens around the main island so
    the player has a way to bootstrap their very first materials/glider
    without needing to already have a glider to reach the werewolf islands.

    Avoids water, solid tiles, and the interiors of buildings/the plaza.
    """
    rng = random.Random(seed)
    positions = []
    attempts = 0
    while len(positions) < count and attempts < 500:
        attempts += 1
        angle = rng.uniform(0, 6.283)
        dist = rng.uniform(main_radius * 0.15, main_radius * 0.8)
        wx = cx + dist * math.cos(angle)
        wy = cy + dist * math.sin(angle)
        tx, ty = int(wx), int(wy)
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
            continue
        if world[ty][tx] in SOLID_TILES:
            continue
        if world[ty][tx] not in (GRASS, PATH, FLOWER, PLAZA):
            continue
        if ((tx - hut_x) ** 2 + (ty - hut_y) ** 2) ** 0.5 < 8:
            continue
        if ((tx - village_x) ** 2 + (ty - village_y) ** 2) ** 0.5 < 8:
            continue
        if ((tx - plaza_x) ** 2 + (ty - plaza_y) ** 2) ** 0.5 < 6:
            continue
        if any(((tx - ox) ** 2 + (ty - oy) ** 2) < 25 for ox, oy in positions):
            continue
        positions.append((wx, wy))

    chickens = []
    for i, (px, py) in enumerate(positions):
        # Roughly 1 in 5 wild chickens is the rarer golden variant.
        if rng.random() < 0.2:
            chickens.append(GoldenChicken(px, py))
        else:
            chickens.append(WildChicken(px, py))
    return chickens



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

    def give_chicken_to_noah(self, amount=1):
        if self.chickens >= amount and amount > 0:
            self.chickens -= amount
            self.materials += amount * 2
            self.mission_stage += 1
            return f"Noah takes {amount} chicken and hands you materials."
        return "You don't have any chicken to give Noah."

    def sell_chicken_to_merchant(self, amount=1):
        if self.chickens < amount or amount <= 0:
            return "You don't have any chicken to sell."

        self.chickens -= amount
        self.chickens_sold += amount
        self.money += amount * 5
        message = f"You sell {amount} chicken to the merchant for {amount * 5} gold."

        if random.random() < 0.5:
            penalty_chickens = min(self.chickens, random.randint(1, 2))
            penalty_money = min(self.money, random.randint(5, 10))
            self.chickens -= penalty_chickens
            self.money -= penalty_money
            self.noah_trust = False
            message += (
                f"\nNoah found out! He takes {penalty_chickens} chicken "
                f"and {penalty_money} gold as a penalty."
            )
        else:
            message += "\nNoah doesn't seem to have noticed... this time."

        if self.chickens_sold >= CHICKENS_TO_WIN:
            self.won = True
            self.game_over = True

        return message


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
class Entity:
    def __init__(self, x, y, sprite):
        self.x = x  # tile coordinates (float, for smooth movement)
        self.y = y
        self.sprite = sprite
        # Idle-bob animation support (opt-in via bob_amplitude > 0). Each
        # entity gets its own random phase so multiple bobbing NPCs don't
        # all sway in perfect unison.
        self.bob_amplitude = 0.0  # screen pixels
        self.bob_speed = 450.0    # ms per cycle
        self._bob_phase = random.uniform(0, 6.283)

    @property
    def tile(self):
        return int(self.x), int(self.y)


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["kyle"])
        self.speed = 10.8  # tiles per second
        self.health = 100
        self.max_health = 100

    def try_move(self, dx, dy, world):
        """Moves along X and Y independently, so bumping into a wall on one
        axis doesn't also block movement along the other axis (this is what
        lets Kyle slide smoothly along walls/coastlines instead of getting
        fully stopped when a diagonal step would clip a solid tile corner)."""
        if dx:
            nx = self.x + dx
            tx, ty = int(nx), int(self.y)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H and world[ty][tx] not in SOLID_TILES:
                self.x = nx
        if dy:
            ny = self.y + dy
            tx, ty = int(self.x), int(ny)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H and world[ty][tx] not in SOLID_TILES:
                self.y = ny


class Werewolf(Entity):
    STATE_WANDER = "wander"
    STATE_CHASE = "chase"

    def __init__(self, x, y, home_radius_tiles, center):
        super().__init__(x, y, SPRITES["werewolf"])
        self.health = 40
        self.speed = 4.2  # tiles per second
        self.state = Werewolf.STATE_WANDER
        self.wander_dir = pygame.Vector2(random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
        self.wander_timer = random.uniform(0.5, 1.5)  # seconds
        self.detect_radius = 7  # tiles
        self.has_chicken = True
        self.center = center
        self.home_radius = home_radius_tiles

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
                self.wander_dir = pygame.Vector2(
                    random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                )
                self.wander_timer = random.uniform(0.5, 1.5)
            self.x += self.wander_dir.x * self.speed * dt
            self.y += self.wander_dir.y * self.speed * dt

        # keep roughly on its home island
        cx, cy = self.center
        if ((self.x - cx) ** 2 + (self.y - cy) ** 2) ** 0.5 > self.home_radius:
            self.x += (cx - self.x) * min(1.0, 3 * dt)
            self.y += (cy - self.y) * min(1.0, 3 * dt)

    def take_damage(self, amount):
        self.health -= amount
        return self.health <= 0


class Noah(Entity):
    DIALOGUE_BY_STAGE = [
        "Hey... you're new here, huh? Name's Noah Ficsher. Been stuck on this "
        "island forever. Bring me chicken (press G) and I'll set you up with "
        "materials to build a glider.",
        "Those smaller islands out there are crawling with werewolves. "
        "They guard the chickens, so you'll need to fight through them.",
        "Nice, you're getting the hang of it. Keep bringing me chicken and "
        "I'll keep helping you out.",
        "Something feels off... you wouldn't be selling chicken behind my "
        "back to that merchant, would you?",
    ]

    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["noah"])
        self.bob_amplitude = 2.0
        self.bob_speed = 500.0

    def get_dialogue(self, state: GameState):
        stage = min(state.mission_stage, len(self.DIALOGUE_BY_STAGE) - 1)
        line = self.DIALOGUE_BY_STAGE[stage]
        if not state.noah_trust:
            line = (
                "I KNOW you've been selling chicken to that merchant. "
                "Don't think I haven't noticed... Bring me more chicken "
                "and we'll call it even."
            )
        return line


class Merchant(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["merchant"])
        self.bob_amplitude = 1.6
        self.bob_speed = 620.0


class WildChicken(Entity):
    """A loose chicken wandering the main island that Kyle can walk up to
    and pick up (press E) -- this bootstraps the very first chicken(s) so
    the Noah/glider loop has something to start from."""
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["chicken"])
        self.collected = False
        self.value = 1


class GoldenChicken(WildChicken):
    """A rare, shinier chicken variant worth more when collected. Harder
    to come by -- spawn_wild_chickens only makes a small fraction of the
    scattered chickens golden."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.sprite = SPRITES["golden_chicken"]
        self.value = 3


class Seagull(Entity):
    """A gull that lazily circles over the coastline near the dock --
    purely decorative: no collision, no interactions, just atmosphere."""
    def __init__(self, center_x, center_y, radius, speed, phase=0.0):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.speed = speed  # radians per second
        self.angle = phase
        x = center_x + radius * math.cos(phase)
        y = center_y + radius * math.sin(phase) * 0.6
        super().__init__(x, y, SPRITES["seagull"])

    def update(self, dt):
        self.angle += self.speed * dt
        self.x = self.center_x + self.radius * math.cos(self.angle)
        # Flattened ellipse so the flight path reads more like a gull
        # circling low over the water than a perfect orbit.
        self.y = self.center_y + self.radius * math.sin(self.angle) * 0.6


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def draw_text(surface, text, pos, font=FONT, color=(255, 255, 255), max_width=None):
    """Renders text at pos. If max_width is given, long lines are word-wrapped
    to fit within that pixel width (in addition to respecting '\\n')."""
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
    # Dark parchment panel
    pygame.draw.rect(surface, (22, 18, 32), (0, hud_y, SCREEN_W, HUD_HEIGHT))
    pygame.draw.line(surface, (90, 65, 115), (0, hud_y), (SCREEN_W, hud_y), 2)

    # --- Health bar ---
    bx, by = 10, hud_y + 10
    bw, bh = 180, 16
    pygame.draw.rect(surface, (55, 18, 18), (bx, by, bw, bh))
    hp_w = int(bw * max(0, player.health) / player.max_health)
    bar_col = (210, 45, 45) if player.health / player.max_health > 0.25 else (255, 100, 20)
    if hp_w > 0:
        pygame.draw.rect(surface, bar_col, (bx, by, hp_w, bh))
    pygame.draw.rect(surface, (180, 130, 130), (bx, by, bw, bh), 1)
    hp_surf = HUD_FONT.render(f"HP  {int(player.health)}/{player.max_health}", True, (255, 225, 225))
    surface.blit(hp_surf, (bx + 4, by + 2))

    # --- Item stats row ---
    sx, sy = 10, hud_y + 34
    # Chicken (golden circle)
    pygame.draw.circle(surface, (248, 195, 45), (sx + 7, sy + 7), 6)
    pygame.draw.circle(surface, (200, 148, 30), (sx + 7, sy + 7), 6, 1)
    surface.blit(HUD_FONT.render(f"x{state.chickens}", True, (255, 240, 185)), (sx + 16, sy + 1))

    # Materials (blue square)
    mx = sx + 58
    pygame.draw.rect(surface, (80, 175, 225), (mx, sy + 1, 12, 12))
    pygame.draw.rect(surface, (50, 130, 185), (mx, sy + 1, 12, 12), 1)
    surface.blit(HUD_FONT.render(f"x{state.materials}", True, (185, 230, 255)), (mx + 15, sy + 1))

    # Gold (yellow diamond)
    gx = mx + 65
    pygame.draw.polygon(surface, (255, 195, 35),
                        [(gx+6, sy), (gx+12, sy+6), (gx+6, sy+12), (gx, sy+6)])
    pygame.draw.polygon(surface, (200, 148, 20),
                        [(gx+6, sy), (gx+12, sy+6), (gx+6, sy+12), (gx, sy+6)], 1)
    surface.blit(HUD_FONT.render(f"{state.money}g", True, (255, 225, 110)), (gx + 16, sy + 1))

    # Sold progress
    px2 = gx + 68
    sold_col = (100, 235, 115) if state.chickens_sold < CHICKENS_TO_WIN else (255, 215, 50)
    surface.blit(HUD_FONT.render(f"Sold:{state.chickens_sold}/{CHICKENS_TO_WIN}", True, sold_col),
                 (px2, sy + 1))

    # Trust indicator (right side)
    if state.noah_trust:
        tc, tt = (80, 225, 110), "Noah trusts you"
        pygame.draw.circle(surface, tc, (SCREEN_W - 170, hud_y + 22), 5)
    else:
        tc, tt = (230, 80, 80), "Noah suspicious!"
        pts = [(SCREEN_W - 170, hud_y + 16), (SCREEN_W - 175, hud_y + 28), (SCREEN_W - 165, hud_y + 28)]
        pygame.draw.polygon(surface, tc, pts)
    surface.blit(HUD_FONT.render(tt, True, tc), (SCREEN_W - 158, hud_y + 16))

    # Controls hint
    hint = "E:talk/interact  G:give  B:glider  SPC:attack  Q:return"
    surface.blit(FONT.render(hint, True, (110, 95, 145)), (10, hud_y + HUD_HEIGHT - 17))


def show_message_box(surface, message):
    box_x, box_margin = 30, 30
    box_w = SCREEN_W - box_margin * 2
    text_max_width = box_w - 28  # leave padding on both sides

    # Pre-compute wrapped line count so the box is tall enough for the text.
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
    box_h = text_block_height + 56  # padding + room for the "press any key" hint
    box_h = max(box_h, 90)
    box_h = min(box_h, SCREEN_H - 40)  # never grow taller than the screen allows
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
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                waiting = False


def show_win_screen(surface):
    surface.fill((10, 10, 15))
    draw_text(
        surface,
        "Kyle finally has enough gold saved up...\n"
        "He leaves the maze behind and goes home to find his dog.\n\nYOU WIN!",
        (40, SCREEN_H // 2 - 50),
        font=BIG_FONT,
        color=(210, 170, 40),
    )
    pygame.display.flip()
    pygame.time.wait(4000)


def show_lose_screen(surface):
    """New: shown when Kyle's HP drops to 0 (previously nothing happened
    on death -- the game just kept running with negative HP)."""
    surface.fill((10, 10, 15))
    draw_text(
        surface,
        "Kyle collapses, exhausted and wounded...\n"
        "The maze claims another wanderer.\n\nGAME OVER",
        (40, SCREEN_H // 2 - 50),
        font=BIG_FONT,
        color=(200, 60, 60),
    )
    pygame.display.flip()
    pygame.time.wait(4000)


# ---------------------------------------------------------------------------
# Weather: a slow, purely cosmetic rain cycle. No gameplay effect -- doesn't
# touch movement, combat, or visibility radius. Just a screen-space tint plus
# some falling streaks that fade in and out over a long cycle.
# ---------------------------------------------------------------------------
RAIN_PERIOD = 90.0     # seconds for one full cycle
RAIN_FRACTION = 0.35   # portion of the cycle that's actually raining
RAIN_FADE = 0.06        # fraction of the cycle used to fade rain in/out


def make_rain_drops(count=70):
    """Screen-space raindrops (not tied to world coordinates -- a common,
    cheap approximation that still reads fine at this resolution)."""
    return [
        [random.uniform(0, SCREEN_W), random.uniform(0, SCREEN_H),
         random.uniform(220, 340), random.uniform(8, 14)]
        for _ in range(count)
    ]


def compute_rain_intensity(elapsed_seconds):
    """Returns 0..1: how hard it's raining right now, easing in/out at the
    edges of the rain window instead of switching on/off abruptly."""
    phase = (elapsed_seconds % RAIN_PERIOD) / RAIN_PERIOD
    if phase > RAIN_FRACTION:
        return 0.0
    if phase < RAIN_FADE:
        return phase / RAIN_FADE
    if phase > RAIN_FRACTION - RAIN_FADE:
        return (RAIN_FRACTION - phase) / RAIN_FADE
    return 1.0


def draw_weather_overlay(surface, rain_drops, intensity, dt):
    """Draws a subtle blue-grey tint plus falling rain streaks over the
    game viewport (not the HUD). Called only while intensity > 0."""
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
# Rendering: only draw tiles within the visibility radius (camera-based)
# ---------------------------------------------------------------------------
TERRAIN_BASE_TILES = {WATER, SAND, GRASS, WOLF_GRASS}

# Flat colors for the organic terrain look (replacing the old textured tiles
# for water/grass/sand specifically -- everything else keeps its pixel art).
ORGANIC_WATER_COLOR = (51, 119, 200)
ORGANIC_LAND_COLOR = (99, 186, 107)
ORGANIC_WOLF_LAND_COLOR = (68, 145, 79)
ORGANIC_OUTLINE_COLOR = (54, 130, 64)
ORGANIC_WOLF_OUTLINE_COLOR = (38, 96, 48)

# Margin (in tiles) added around the visible viewport when building the
# coastline mask, so the smoothing pass has context beyond the screen edge.
_TERRAIN_MARGIN = 2
_TERRAIN_GRID = VIEW_TILES_ACROSS + _TERRAIN_MARGIN * 2

try:
    import pygame.surfarray as _surfarray
    _HAS_SURFARRAY = True
except ImportError:
    _HAS_SURFARRAY = False


def _smooth_upscale(mask_surf, final_size):
    """Two-step smoothscale up to final_size -- softer than one jump, cheaper
    than three. Tuned for a per-frame performance budget."""
    grid = mask_surf.get_width()
    cur = pygame.transform.smoothscale(mask_surf, (grid * 4, grid * 4))
    cur = pygame.transform.smoothscale(cur, (final_size, final_size))
    return cur


def _colored_layer_with_mask_alpha(mask_big, color, red_array=None):
    """Returns an RGBA surface filled with `color`, whose per-pixel alpha is
    taken from mask_big's brightness (white=opaque, black=transparent).
    If red_array is provided, it's used directly instead of recomputing."""
    layer = pygame.Surface(mask_big.get_size(), pygame.SRCALPHA)
    layer.fill(color)
    if _HAS_SURFARRAY:
        if red_array is None:
            red_array = _surfarray.array_red(mask_big)
        alpha_view = _surfarray.pixels_alpha(layer)
        alpha_view[:, :] = red_array
        del alpha_view
    else:
        # Fallback without numpy: hard-edged but still flat-colored.
        layer.set_colorkey(None)
    return layer


def _draw_hand_drawn_outline(surface, red_array, outline_color, origin_offset, scale=1):
    """Draws a wobbly, hand-drawn-style stroke along the coastline by
    sampling the mask's edge contour at intervals around each land blob
    and connecting the points with slightly jittered line segments.
    `red_array` is the land mask's precomputed array_red (avoids recomputing).
    `scale` adjusts step/circle size for whatever resolution `surface` is at."""
    if not _HAS_SURFARRAY or red_array is None:
        return
    step = max(1, int(2 * scale))  # px spacing between edge samples
    rng = random.Random(int(origin_offset[0] * 7 + origin_offset[1] * 13))

    sampled = red_array[::step, ::step]  # vectorized downsample, no Python loop
    edge_mask = (sampled > 90) & (sampled < 200)
    xs, ys = edge_mask.nonzero()
    # array_red is indexed [x, y], so nonzero() gives (x_idx, y_idx) in that order.
    radius = max(1, scale)
    for xi, yi in zip(xs, ys):
        x, y = int(xi) * step, int(yi) * step
        jitter = rng.uniform(-0.6, 0.6) * scale
        pygame.draw.circle(surface, outline_color, (x + jitter, y + jitter), radius)


_TERRAIN_SUPERSAMPLE = 6  # internal samples-per-tile for the blur/mask pass
                          # (kept well below DISPLAY_TILE=32 so the expensive
                          # numpy/blur work happens on a much smaller canvas)


def _smooth_upscale_small(mask_surf, small_size):
    """Two-step smoothscale from the tile-grid mask up to small_size (the
    cheap intermediate supersampled resolution, NOT full screen size)."""
    grid = mask_surf.get_width()
    cur = pygame.transform.smoothscale(mask_surf, (grid * 3, grid * 3))
    cur = pygame.transform.smoothscale(cur, (small_size, small_size))
    return cur


def render_world(world, player, npcs_visible):
    screen.fill((15, 10, 22))

    # Fractional camera: player sprite is always centered on screen.
    # cam_pixel_x/y = world-pixel coordinate of the viewport's top-left corner.
    cam_pixel_x = player.x * DISPLAY_TILE - SCREEN_W / 2
    cam_pixel_y = player.y * DISPLAY_TILE - SCREEN_H / 2

    # First tile that touches the viewport (floor so partial left/top tiles show)
    first_tile_x = math.floor(cam_pixel_x / DISPLAY_TILE)
    first_tile_y = math.floor(cam_pixel_y / DISPLAY_TILE)

    # ---- Organic terrain pass: smooth, flat-colored water/grass/wolf-grass ----
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

    # Do the expensive blur/numpy work at a much smaller intermediate size --
    # the blur already softens detail, so doing this at full DISPLAY_TILE
    # resolution would be wasted work. We upscale to full size at the very
    # end with one cheap smoothscale call.
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

    # Hand-drawn-style wobbly outline along each coastline, drawn at the
    # small resolution too (cheap, and the wobble scales up fine).
    _draw_hand_drawn_outline(terrain_small, land_red_array, ORGANIC_OUTLINE_COLOR,
                              (first_tile_x, first_tile_y), scale=1)

    # One cheap final upscale to full screen resolution.
    terrain_surf = pygame.transform.smoothscale(terrain_small, (terrain_px_size, terrain_px_size))

    # Blit the organic terrain onto the screen, offset so the margin tiles
    # line up correctly with the rest of the (non-terrain) tile rendering.
    terrain_origin_x = (first_tile_x - margin) * DISPLAY_TILE - cam_pixel_x
    terrain_origin_y = (first_tile_y - margin) * DISPLAY_TILE - cam_pixel_y
    screen.blit(terrain_surf, (terrain_origin_x, terrain_origin_y))

    # ---- Structure/decoration pass: huts, paths, trees, rocks, etc. ----
    # (mostly unchanged from before -- still drawn as regular pixel-art tiles,
    # skipping the base terrain tiles since the organic pass already covered
    # them -- except trees, which get a gentle wind-sway rotation instead of
    # a static blit.)
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
                # Small continuous rotation driven by a sine wave; each
                # tree's phase comes from its world position so a whole
                # grove doesn't sway in perfect unison.
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

    # Player sprite is always centered on screen
    px = SCREEN_W / 2 - DISPLAY_TILE / 2
    py = SCREEN_H / 2 - DISPLAY_TILE / 2

    # NPCs / enemies relative to the fractional camera
    for entity in npcs_visible:
        ex = (entity.x - player.x) * DISPLAY_TILE + SCREEN_W / 2 - DISPLAY_TILE / 2
        ey = (entity.y - player.y) * DISPLAY_TILE + SCREEN_H / 2 - DISPLAY_TILE / 2
        if entity.bob_amplitude:
            ey += math.sin(pygame.time.get_ticks() / entity.bob_speed + entity._bob_phase) * entity.bob_amplitude
        if -DISPLAY_TILE <= ex <= SCREEN_W and -DISPLAY_TILE <= ey <= SCREEN_H:
            screen.blit(entity.sprite, (ex, ey))

    screen.blit(player.sprite, (px, py))


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
def main():
    state = GameState()
    world, (cx, cy, main_radius), island_centers = generate_world()

    # Place the hut near the main island center, slightly offset
    hut_x, hut_y = cx + 20, cy - 15
    desk_pos = carve_hut(world, hut_x, hut_y)

    # The hidden black market room shares the same grid but is only ever
    # entered (and rendered as "current area") once the trapdoor is open --
    # we place it far enough away that it doesn't visually overlap the hut.
    market_x, market_y = hut_x - 200, hut_y + 200
    if market_x < 5:
        market_x = 5
    if market_y > MAP_H - 10:
        market_y = MAP_H - 10
    carve_market_room(world, market_x, market_y)
    merchant_pos = (market_x + 3, market_y + 3)
    merchant = Merchant(*merchant_pos)

    # Decorate the main island with trees, flowers, and a dirt path
    plaza_x, plaza_y, village_x, village_y, shore_x, shore_y = decorate_world(world, cx, cy, main_radius, hut_x, hut_y)

    # Decorate each werewolf island with dead trees, jagged rocks, bones, etc.
    for i, (ix, iy, r) in enumerate(island_centers):
        decorate_wolf_island(world, ix, iy, r, seed=1000 + i)

    # Scatter a few loose, pickupable chickens on the main island so the
    # player has a way to bootstrap their first materials/glider.
    wild_chickens = spawn_wild_chickens(
        world, cx, cy, main_radius, hut_x, hut_y, village_x, village_y,
        plaza_x, plaza_y, count=5,
    )

    # Noah stands near the main island center
    noah = Noah(cx - 5, cy)

    # Player starts at the center of the main island
    player = Player(cx, cy + 5)

    # Build werewolves for each smaller island
    werewolves = []
    for (ix, iy, r) in island_centers:
        count = random.randint(2, 4)
        for _ in range(count):
            wx = ix + random.uniform(-r * 0.6, r * 0.6)
            wy = iy + random.uniform(-r * 0.6, r * 0.6)
            werewolves.append(Werewolf(wx, wy, r, (ix, iy)))

    last_attack_time = 0
    attack_cooldown = 400  # ms

    # A handful of gulls lazily circling over the water near the dock.
    seagulls = [
        Seagull(shore_x, shore_y, radius=12 + i * 4, speed=0.3 + i * 0.07, phase=i * (6.283 / 4))
        for i in range(4)
    ]

    rain_drops = make_rain_drops()

    # Track whether the trapdoor area has been "stepped into" to flag market state
    market_entry_tile = (market_x + 3, market_y + 1)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)  # cap to prevent huge jumps after lag spikes

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
                        show_message_box(
                            screen,
                            "You lift the desk aside, revealing a mat underneath...",
                        )

                    elif dist_to_desk < 1.5 and state.desk_lifted and not state.mat_lifted:
                        state.mat_lifted = True
                        world[desk_pos[1]][desk_pos[0]] = TRAPDOOR_OPEN
                        show_message_box(
                            screen,
                            "You lift the mat and find a trapdoor leading down. "
                            "This must be how Kyle reaches the black market...",
                        )

                    elif dist_to_desk < 1.5 and state.mat_lifted:
                        # Teleport player into the black market room
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

                if event.key == pygame.K_g:
                    dist_to_noah = ((player.x - noah.x) ** 2 + (player.y - noah.y) ** 2) ** 0.5
                    if dist_to_noah < 1.8:
                        msg = state.give_chicken_to_noah(amount=min(2, state.chickens))
                        show_message_box(screen, msg)

                if event.key == pygame.K_b:
                    if state.materials >= 6:
                        state.materials -= 6
                        state.gliders += 1
                        show_message_box(
                            screen,
                            "You assemble a glider from the materials. "
                            "Walk toward a smaller island's shore to glide over.",
                        )
                    else:
                        show_message_box(screen, "Not enough materials (need 6).")

                if event.key == pygame.K_SPACE:
                    now = pygame.time.get_ticks()
                    if now - last_attack_time > attack_cooldown:
                        last_attack_time = now
                        for wolf in list(werewolves):
                            dist = ((player.x - wolf.x) ** 2 + (player.y - wolf.y) ** 2) ** 0.5
                            if dist < 1.6:
                                if wolf.take_damage(20):
                                    werewolves.remove(wolf)
                                    if wolf.has_chicken:
                                        state.chickens += 1

        # ---------------- movement ----------------
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -player.speed * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = player.speed * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -player.speed * dt
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = player.speed * dt

        if dx and dy:  # normalize diagonal movement
            dx *= 0.7071
            dy *= 0.7071

        # Crossing onto WATER is blocked unless Kyle has a glider, in which
        # case he "glides" across automatically. X and Y are resolved as two
        # SEPARATE checks (instead of one combined int(nx), int(ny) check)
        # so Kyle can slide smoothly along a wall/coastline edge instead of
        # getting fully stopped whenever a diagonal step clips a solid
        # tile's corner.
        def _tile_passable(tile_id):
            if tile_id == WATER:
                return state.gliders > 0
            return tile_id not in SOLID_TILES

        if dx:
            nx = player.x + dx
            tx, ty = int(nx), int(player.y)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H and _tile_passable(world[ty][tx]):
                player.x = nx

        if dy:
            ny = player.y + dy
            tx, ty = int(player.x), int(ny)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H and _tile_passable(world[ty][tx]):
                player.y = ny

        # ---------------- wild chicken pickups (main island) ----------------
        for chick in wild_chickens:
            if chick.collected:
                continue
            dist = ((player.x - chick.x) ** 2 + (player.y - chick.y) ** 2) ** 0.5
            if dist < 1.0:
                chick.collected = True
                state.chickens += chick.value

        # ---------------- werewolves ----------------
        for wolf in werewolves:
            wolf.update(player, dt)
            dist = ((player.x - wolf.x) ** 2 + (player.y - wolf.y) ** 2) ** 0.5
            if dist < 0.8:
                player.health -= 60 * dt

        # ---------------- seagulls ----------------
        for gull in seagulls:
            gull.update(dt)

        # ---------------- death check (new: previously HP could go below
        # 0 forever with no game-over handling at all) ----------------
        if player.health <= 0:
            player.health = 0
            state.game_over = True

        if state.game_over:
            running = False

        # ---------------- render ----------------
        visible_npcs = [noah]
        if state.in_black_market:
            visible_npcs.append(merchant)
        visible_npcs.extend(werewolves)
        visible_npcs.extend(chick for chick in wild_chickens if not chick.collected)
        visible_npcs.extend(seagulls)

        render_world(world, player, visible_npcs)

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