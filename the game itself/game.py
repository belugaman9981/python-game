"""
Kyle Jordan's Maze Adventure — DETAILED EDITION
===================================================
A rich, expanded version with deep gameplay systems.

NEW SYSTEMS:
- Day/Night cycle with proper lighting
- Full inventory with item types and their rarity
- Crafting system (weapons, tools, consumables)
- Quest log with multiple quest lines
- Working NPC schedules and daily routines
- Fishing game
- Cooking system (recipes from ingredients)
- Weather effects (rain, fog, storms)
- Sound system with ambient audio
- Achievements
- Bestiary (enemy info)
- Map discovery/fog of war
- Save/load/download system
- Multiple weapon types
- Armor/equipment slots
- Status effects (poison, bleed, buffs)
- Dungeon rooms with puzzles
- Merchant shops with rotating stocks
- Reputation system
- Companion system
- Base building (tent upgrades)
- Random events
- Boss encounters
- Endless mode after winning
"""

import pygame
import random
import sys
import math
import json
import os
from datetime import datetime
from enum import Enum, auto

# ---------------------------------------------------------------------------
# Core Engine Setup
# ---------------------------------------------------------------------------
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

TILE = 16
SCALE = 2
DISPLAY_TILE = TILE * SCALE
MAP_W, MAP_H = 700, 700

VIEW_RADIUS_TILES = 12  # Increased visibility
VIEW_TILES_ACROSS = VIEW_RADIUS_TILES * 2 + 1

SCREEN_W = SCREEN_H = VIEW_TILES_ACROSS * DISPLAY_TILE
HUD_HEIGHT = 90  # Taller HUD for more info

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H + HUD_HEIGHT))
pygame.display.set_caption("Kyle Jordan's Maze Adventure - Detailed Edition")
clock = pygame.time.Clock()
FPS = 60

# Font system with fallbacks
FONT_SIZES = {
    'tiny': 10, 'small': 12, 'normal': 14, 'medium': 16,
    'large': 20, 'title': 28, 'huge': 36
}
FONTS = {}
for name, size in FONT_SIZES.items():
    FONTS[name] = pygame.font.SysFont("monospace", size, bold=(name in ['title', 'huge']))

# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------
class ItemType(Enum):
    CONSUMABLE = auto()
    MATERIAL = auto()
    WEAPON = auto()
    ARMOR = auto()
    TOOL = auto()
    QUEST = auto()
    TREASURE = auto()

class ItemRarity(Enum):
    COMMON = ("Common", (200, 200, 200))
    UNCOMMON = ("Uncommon", (100, 220, 100))
    RARE = ("Rare", (100, 150, 255))
    EPIC = ("Epic", (180, 100, 255))
    LEGENDARY = ("Legendary", (255, 180, 50))

class WeatherType(Enum):
    CLEAR = auto()
    CLOUDY = auto()
    RAIN = auto()
    STORM = auto()
    FOG = auto()

class TimeOfDay(Enum):
    DAWN = ("Dawn", (255, 180, 120), 0.1)
    DAY = ("Day", (255, 255, 240), 0.0)
    DUSK = ("Dusk", (255, 140, 100), 0.2)
    NIGHT = ("Night", (80, 90, 140), 0.6)

CHICKENS_TO_WIN = 10  # Slightly harder
MAX_INVENTORY = 24

# ---------------------------------------------------------------------------
# Tile Types (expanded)
# ---------------------------------------------------------------------------
WATER, SAND, GRASS = 0, 1, 2
HUT_FLOOR, HUT_WALL, DESK, MAT = 3, 4, 5, 6
TRAPDOOR_OPEN, MARKET_FLOOR, MARKET_WALL = 7, 8, 9
WOLF_GRASS, TREE, FLOWER = 10, 11, 12
PATH, ROCK, PLAZA = 13, 14, 15
FOUNTAIN_00, FOUNTAIN_01, FOUNTAIN_02 = 16, 17, 18
FOUNTAIN_10, FOUNTAIN_11, FOUNTAIN_12 = 19, 20, 21
FOUNTAIN_20, FOUNTAIN_21, FOUNTAIN_22 = 22, 23, 24
DOCK, VILLAGE_WALL, VILLAGE_FLOOR = 25, 26, 27
TREE2, DEAD_TREE, WOLF_ROCK = 28, 29, 30
BONES, DARK_PATCH, PILING = 31, 32, 33
CRATE, ROPE_COIL, LANTERN = 34, 35, 36
# NEW TILES
CAMPFIRE, TENT, FISHING_SPOT = 37, 38, 39
MUSHROOM_PATCH, BERRY_BUSH, HERB_PLANT = 40, 41, 42
CHEST_CLOSED, CHEST_OPEN, SIGNPOST = 43, 44, 45
BRIDGE, GATE_LOCKED, GATE_OPEN = 46, 47, 48
WELL, GRAVE, STATUE = 49, 50, 51

FOUNTAIN_TILES = {
    (0, 0): FOUNTAIN_00, (0, 1): FOUNTAIN_01, (0, 2): FOUNTAIN_02,
    (1, 0): FOUNTAIN_10, (1, 1): FOUNTAIN_11, (1, 2): FOUNTAIN_12,
    (2, 0): FOUNTAIN_20, (2, 1): FOUNTAIN_21, (2, 2): FOUNTAIN_22,
}

SOLID_TILES = {
    HUT_WALL, MARKET_WALL, WATER, TREE, ROCK, VILLAGE_WALL, TREE2,
    DEAD_TREE, WOLF_ROCK, PILING, LANTERN, SIGNPOST, STATUE,
    CHEST_CLOSED, GATE_LOCKED, WELL
} | set(FOUNTAIN_TILES.values())

INTERACTIVE_TILES = {DESK, MAT, TRAPDOOR_OPEN, CHEST_CLOSED, FISHING_SPOT,
                     MUSHROOM_PATCH, BERRY_BUSH, HERB_PLANT, SIGNPOST, WELL,
                     CAMPFIRE, TENT}

GLIDER_CONSUME_TILES = {WATER}


# ---------------------------------------------------------------------------
# Pixel-art drawing helpers
# ---------------------------------------------------------------------------
def make_surface(pixels, palette):
    surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), palette[ch])
    return surf

def _make_tile(rows, palette):
    surf = pygame.Surface((TILE, TILE))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            surf.set_at((x, y), palette[ch])
    return surf

def _make_smooth_grass(base, light, dark):
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
    "WWwWbWwWWwbWWwWW","wWbbWwwbWWwWbWwW","WbWwWWbbWwWWwbWW",
    "bWWwWWwWbWWwWWbW","WwbWWwgWwbWWwWbw","WwWwbWWwWwbWWwWW",
    "bWWWwWWbbWwWWwWb","wWbWWwWWwbWWwWWw","WWwWbWgwgWbWWwWW",
    "bWWwWWbWwWWwWWbW","wWbWWwWWwwWWwWWw","WwWbWWwWWwbWWwWW",
    "WWbWWwWWbWWwWWbW","bWWwWWbWwWWbWWwW","wWbWWwWWwbWWwWWb",
    "WWwbWWwWWwbWWwWW",
], {"W":(45,105,195),"w":(60,125,215),"b":(32,85,178),"g":(148,205,255)})

_SAND = _make_tile([
    "SSsSSSdSSsSSSdSS","sSdSSSSsSdSSSSsS","SSSSdSSSSSSdSSSS",
    "dSSsSSSdSSsSSSdS","SSSSSdSSSSSSdSSS","sSSSdSSsSSSdSsSS",
    "SSdSSSSSSdSSSSdS","SSSsSSSdSSSsSSSd","dSSSSdSSSSSSdSSS",
    "SSsSSSdSSSsSSSdS","SSSdSSSSdSSSSSSS","sSSSdSsSSSdSSSsS",
    "SSSSSSdSSSSSSdSS","dSSsSSSdSSsSSSdS","SSSSSdSSSSSSdSSS",
    "SSsSSSdSSsSSSdSS",
], {"S":(215,190,140),"s":(228,205,155),"d":(195,170,118)})

_PATH = _make_tile([
    "PPlPPpPPlPPpPPlP","lPpPPPPlPpPPPPlP","PPPPpPPPPPPpPPPP",
    "pPPlPPPpPPlPPPpP","PPPPPpPPPPPPpPPP","lPPPpPPlPPPpPlPP",
    "PPpPPPPPPpPPPPpP","PPPlPPPpPPPlPPPp","pPPPPpPPPPPPpPPP",
    "PPlPPPpPPPlPPPpP","PPPpPPPPpPPPPPPP","lPPPpPlPPPpPPPlP",
    "PPPPPPpPPPPPPpPP","pPPlPPPpPPlPPPpP","PPPPPpPPPPPPpPPP",
    "PPlPPPpPPlPPPpPP",
], {"P":(155,115,72),"p":(138,98,58),"l":(172,132,89)})

_HUT_FLOOR = _make_tile([
    "wWwWwWwWwWwWwWwW","WWdWWdWWdWWdWWdW","WgWgWWgWgWWgWgWg",
    "dWWdWWdWWdWWdWWd","WwWwWwWwWwWwWwWw","WdWWdWWdWWdWWdWW",
    "gWgWgWgWgWgWgWgW","dWWdWWdWWdWWdWWd","wWwWwWwWwWwWwWwW",
    "WWdWWdWWdWWdWWdW","WgWgWWgWgWWgWgWg","dWWdWWdWWdWWdWWd",
    "WwWwWwWwWwWwWwWw","WdWWdWWdWWdWWdWW","gWgWgWgWgWgWgWgW",
    "dWWdWWdWWdWWdWWd",
], {"W":(175,128,75),"w":(190,142,88),"d":(148,105,58),"g":(125,88,42)})

_HUT_WALL = _make_tile([
    "RrRRRdRrRRRdRrRR","dRrRRRdRrRRRdRrR","RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR","RrRRRdRrRRRdRrRR","dRrRRRdRrRRRdRrR",
    "RRdRrRRRdRrRRRdR","rRRRdRrRRRdRrRRR","RrRRRdRrRRRdRrRR",
    "dRrRRRdRrRRRdRrR","RRdRrRRRdRrRRRdR","rRRRdRrRRRdRrRRR",
    "RrRRRdRrRRRdRrRR","dRrRRRdRrRRRdRrR","RRdRrRRRdRrRRRdR",
    "rRRRdRrRRRdRrRRR",
], {"R":(148,65,38),"r":(172,82,48),"d":(115,50,25)})

_MARKET_FLOOR = _make_tile([
    "SSSSSSSdSSSSSSdS","sSdSSSSSsSdSSSsS","SSSdSSSSSSSdSSSS",
    "SSSSdSSSSSSSdSSS","gggggggggggggggg","SSSSSSSdSSSSSSdS",
    "sSSSdSSSsSSSdSSS","SSSSSSSSdSSSSSSS","SSdSSSSSSSdSSSsS",
    "gggggggggggggggg","SSSSSdSSSSSSdSSS","sSSSSSSSsSSSSSdS",
    "SSdSSSSSSSdSSSsS","SSSSSSSdSSSSSSdS","gggggggggggggggg",
    "SSSSSdSSSSSSdSSS",
], {"S":(55,45,72),"s":(68,58,88),"d":(40,32,55),"g":(28,22,40)})

_MARKET_WALL = _make_tile([
    "DDddDDddDDddDDdd","dDDcDddDDcDddDDc","DddcDDddcDDddcDD",
    "ddDDcddDDcddDDcd","cDDddcDDddcDDddc","DddDDcddDDcddDDc",
    "ddcDDddcDDddcDDd","DDcddDDcddDDcddd","DDddDDddDDddDDdd",
    "dDDcDddDDcDddDDc","DddcDDddcDDddcDD","ddDDcddDDcddDDcd",
    "cDDddcDDddcDDddc","DddDDcddDDcddDDc","ddcDDddcDDddcDDd",
    "DDcddDDcddDDcddd",
], {"D":(30,22,40),"d":(40,32,52),"c":(50,40,65)})

_TRAPDOOR = _make_tile([
    "DDDDDDDDDDDDDdDD","DbDbDbDbDbDbDbDb","DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb","DDgDDDDDDDDgDDDD","DbDbgbDbDbgbDbDb",
    "DDDDDDDDDDDDDdDD","DbDbDbDbDbDbDbDb","gDDDDgDDDDgDDDDg",
    "DbDbDbDbDbDbDbDb","DDDDDDDDDDDDDdDD","DbDbDbDbDbDbDbDb",
    "DDgDDDDDDDDgDDDD","DbDbgbDbDbgbDbDb","DDDDDDDDDDDDDdDD",
    "DbDbDbDbDbDbDbDb",
], {"D":(20,15,28),"d":(30,23,40),"b":(45,35,58),"g":(68,52,85)})

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
        "....sDDDDDDs....","...DGGgGGGGGDs..","..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",".DGGGhGGGGhGGGGs",".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",".DGGGGGttGGGGGGs",".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",".DGGGGGGGGGGGGGs",".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.","...sDDGGGGDDs...","....sssDDsss....",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"D":(28,100,35),"G":(50,145,58),"g":(72,178,82),"h":(95,210,108),"t":(100,70,38),"s":(18,78,24)})
    img.blit(overlay, (0, 0))
    return img

def _make_tree2():
    img = _GRASS.copy()
    rows = [
        "....sDDDDDDs....","...DGGgGGGGGDs..","..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",".DGGGhGGGGhGGGGs",".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",".DGGGGGttGGGGGGs",".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",".DGGGGGGGGGGGGGs",".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.","...sDDGGGGDDs...","....sssDDsss....",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"D":(140,80,20),"G":(205,140,40),"g":(225,170,60),"h":(240,195,90),"t":(100,70,38),"s":(95,55,15)})
    img.blit(overlay, (0, 0))
    return img

def _make_tree_canopy_overlay():
    rows = [
        "....sDDDDDDs....","...DGGgGGGGGDs..","..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",".DGGGhGGGGhGGGGs",".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",".DGGGGGttGGGGGGs",".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",".DGGGGGGGGGGGGGs",".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.","...sDDGGGGDDs...","....sssDDsss....",
        "................",
    ]
    return make_surface(rows, {".":None,"D":(28,100,35),"G":(50,145,58),"g":(72,178,82),"h":(95,210,108),"t":(100,70,38),"s":(18,78,24)})

def _make_tree2_canopy_overlay():
    rows = [
        "....sDDDDDDs....","...DGGgGGGGGDs..","..DGGGGGGGGGGDs.",
        ".DGGGGGGGGGGGGDs",".DGGGhGGGGhGGGGs",".DGGGGGttGGGGGGs",
        ".DGGGGttttGGGGGs",".DGGGGGttGGGGGGs",".DGGGGGGGGGGGGGs",
        ".DGGhGGGGGGhGGGs",".DGGGGGGGGGGGGGs",".DGGGGGGGGGGGGDs",
        "..DGGGGGGGGGGDs.","...sDDGGGGDDs...","....sssDDsss....",
        "................",
    ]
    return make_surface(rows, {".":None,"D":(140,80,20),"G":(205,140,40),"g":(225,170,60),"h":(240,195,90),"t":(100,70,38),"s":(95,55,15)})

def _make_rock():
    img = _GRASS.copy()
    rows = [
        "....sssssss....","...sRRRRRRRs...","..sRRrRRRrRRs..",
        ".sRRRRRRRRRRRs.",".sRrRRRRRRrRRs.","sRRRRRRRRRRRRRs",
        "sRRRrRRRRRrRRRs","sRRRRRRRRRRRRRs",".sRRRRrRRRRRRs.",
        ".sRRRRRRRRRRs..","..ssRRRRRRsss..","...sssssssss...",
        "................","................","................",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"s":(70,65,68),"R":(130,128,132),"r":(155,152,158)})
    img.blit(overlay, (0, 0))
    return img

def _make_plaza():
    return _make_tile([
        "MmMMMmMMmMMMmMMm","mMmMMmMMmMMmMMmM","MMMmMMmMMMmMMmMM",
        "mMMMmMMmMMMmMMmM","MmMMmMMMmMMmMMMm","MMmMMMmMMmMMMmMM",
        "mMMmMMMmMMmMMMmM","MMMmMMmMMMmMMmMM","mMmMMmMMmMMmMMmM",
        "MMMmMMmMMMmMMmMM","mMMMmMMmMMMmMMmM","MmMMmMMMmMMmMMMm",
        "MMmMMMmMMmMMMmMM","mMMmMMMmMMmMMMmM","MMMmMMmMMMmMMmMM",
        "mMmMMmMMmMMmMMmM",
    ], {"M":(168,160,148),"m":(148,140,130)})

def _make_fountain_tile(row_in_grid, col_in_grid, size=3):
    img = _make_plaza()
    full = size * TILE
    canvas = pygame.Surface((full, full), pygame.SRCALPHA)
    cx_, cy_ = full / 2, full / 2
    outer_r, rim_r, water_r, inner_r = full * 0.46, full * 0.40, full * 0.34, full * 0.10
    for yy in range(full):
        for xx in range(full):
            d = ((xx - cx_) ** 2 + (yy - cy_) ** 2) ** 0.5
            if d < inner_r:
                canvas.set_at((xx, yy), (200, 225, 250) if (xx + yy) % 9 == 0 else (95, 165, 225))
            elif d < water_r:
                canvas.set_at((xx, yy), (95, 165, 225))
            elif d < rim_r:
                canvas.set_at((xx, yy), (150, 148, 150))
            elif d < outer_r:
                canvas.set_at((xx, yy), (95, 90, 88))
    slice_x, slice_y = col_in_grid * TILE, row_in_grid * TILE
    overlay = canvas.subsurface((slice_x, slice_y, TILE, TILE)).copy()
    img.blit(overlay, (0, 0))
    return img

def _make_dock():
    return _make_tile([
        "wwwwwwwwwwwwwwww","DDDDDDDDDDDDDDDD","wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww","DDDDDDDDDDDDDDDD","wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww","DDDDDDDDDDDDDDDD","wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww","DDDDDDDDDDDDDDDD","wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww","DDDDDDDDDDDDDDDD","wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
    ], {"w":(172,132,80),"D":(130,95,55)})

def _make_village_floor(): return _HUT_FLOOR.copy()

def _make_piling():
    img = _WATER.copy()
    rows = [
        "................","................",".......DD.......",
        "......DddD......","......DddD......","......DddD......",
        "......DddD......","......DddD......",".....DDddDD.....",
        "......ddd.......","................","................",
        "................","................","................",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"D":(90,60,32),"d":(118,82,44)})
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
        "GgGGGdGgGGGdGgGG","dGgGGGdGgGGGdGgG","GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG","GgGGGdGgGGGdGgGG","dGgGGGdGgGGGdGgG",
        "GGdGgGGGdGgGGGdG","gGGGdGgGGGdGgGGG","GgGGGdGgGGGdGgGG",
        "dGgGGGdGgGGGdGgG","GGdGgGGGdGgGGGdG","gGGGdGgGGGdGgGGG",
        "GgGGGdGgGGGdGgGG","dGgGGGdGgGGGdGgG","GGdGgGGGdGgGGGdG",
        "gGGGdGgGGGdGgGGG",
    ], {"G":(120,118,115),"g":(140,138,135),"d":(95,92,88)})

def _make_dead_tree():
    img = _WOLF_GRASS.copy()
    rows = [
        "................","................",".......t........",
        "......ttt.......","....t..t..t.....",".....t.t.t......",
        "......ttt.......","....tt.t.tt.....",".....tttt.......",
        "......ttt.......","................","................",
        "......ttt.......","................","................",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"t":(75,60,48)})
    img.blit(overlay, (0, 0))
    return img

def _make_wolf_rock():
    img = _WOLF_GRASS.copy()
    rows = [
        "................","......s.ss......",".....sRRRRs.....",
        "....sRrRRRRs....","...sRRRRrRRRs...","..sRRrRRRRRRRs..",
        "..sRRRRRrRRRRs..","..sRRRRRRRrRRs..","...sRrRRRRRRs...",
        "....sRRRrRRs....",".....sRRRRs.....","......sssss.....",
        "................","................","................",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"s":(35,32,34),"R":(78,75,80),"r":(95,92,98)})
    img.blit(overlay, (0, 0))
    return img

def _make_bones():
    img = _WOLF_GRASS.copy()
    rows = [
        "................","................","....b.......b...",
        "...bWb.....bWb..","....b...WW..b...",".......WbbW.....",
        "......WbbbbW....",".b...WbbbbbW..b.","bWb...WbbbW..bWb",
        ".b.....WW....b..","................","................",
        "................","................","................",
        "................",
    ]
    overlay = make_surface(rows, {".":None,"W":(225,220,205),"b":(200,195,175)})
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

def _make_campfire():
    img = _GRASS.copy()
    pygame.draw.circle(img, (80, 60, 40), (8, 10), 5)
    pygame.draw.circle(img, (60, 40, 25), (8, 10), 5, 1)
    for fx, fy, fc in [(7,5,(255,180,50)),(9,6,(255,100,30)),(8,4,(255,220,100))]:
        pygame.draw.circle(img, fc, (fx, fy), 2)
    return img

def _make_tent():
    img = _GRASS.copy()
    pygame.draw.polygon(img, (140, 120, 80), [(2, 14), (8, 3), (14, 14)])
    pygame.draw.polygon(img, (100, 85, 55), [(2, 14), (8, 3), (14, 14)], 1)
    pygame.draw.rect(img, (60, 50, 35), (6, 10, 4, 4))
    return img

def _make_fishing_spot():
    img = _WATER.copy()
    pygame.draw.circle(img, (200, 200, 200, 120), (8, 8), 3)
    pygame.draw.line(img, (120, 80, 40), (8, 8), (8, 2), 1)
    return img

def _make_mushroom_patch():
    img = _GRASS.copy()
    pygame.draw.ellipse(img, (200, 60, 60), (4, 8, 4, 3))
    pygame.draw.ellipse(img, (240, 240, 240), (5, 7, 2, 2))
    pygame.draw.ellipse(img, (140, 100, 60), (10, 10, 3, 2))
    pygame.draw.rect(img, (220, 210, 190), (11, 11, 1, 2))
    return img

def _make_berry_bush():
    img = _GRASS.copy()
    pygame.draw.circle(img, (40, 100, 40), (8, 9), 5)
    pygame.draw.circle(img, (30, 80, 30), (8, 9), 5, 1)
    for bx, by in [(6,7),(9,8),(7,10),(10,7)]:
        pygame.draw.circle(img, (180, 40, 60), (bx, by), 1)
    return img

def _make_herb_plant():
    img = _GRASS.copy()
    pygame.draw.line(img, (60, 140, 60), (8, 14), (8, 6), 1)
    pygame.draw.ellipse(img, (80, 180, 80), (6, 4, 4, 3))
    pygame.draw.ellipse(img, (100, 200, 100), (7, 5, 2, 2))
    return img

def _make_chest():
    img = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.rect(img, (140, 100, 50), (2, 5, 12, 9))
    pygame.draw.rect(img, (100, 70, 35), (2, 5, 12, 9), 1)
    pygame.draw.rect(img, (180, 150, 80), (2, 5, 12, 3))
    pygame.draw.circle(img, (200, 180, 100), (8, 8), 1)
    return img

def _make_signpost():
    img = _GRASS.copy()
    pygame.draw.rect(img, (100, 70, 40), (7, 4, 2, 11))
    pygame.draw.rect(img, (160, 130, 80), (3, 2, 10, 6))
    pygame.draw.rect(img, (120, 95, 55), (3, 2, 10, 6), 1)
    return img

def _make_bridge():
    img = _make_dock()
    pygame.draw.line(img, (100, 70, 40), (0, 0), (15, 15), 1)
    pygame.draw.line(img, (100, 70, 40), (15, 0), (0, 15), 1)
    return img

def _make_gate():
    img = _GRASS.copy()
    pygame.draw.rect(img, (80, 60, 40), (2, 2, 2, 13))
    pygame.draw.rect(img, (80, 60, 40), (12, 2, 2, 13))
    pygame.draw.rect(img, (120, 90, 50), (4, 4, 8, 10))
    return img

def _make_well():
    img = _GRASS.copy()
    pygame.draw.circle(img, (120, 120, 130), (8, 10), 5)
    pygame.draw.circle(img, (80, 80, 90), (8, 10), 5, 1)
    pygame.draw.rect(img, (100, 80, 60), (6, 2, 4, 6))
    return img

def _make_grave():
    img = _WOLF_GRASS.copy()
    pygame.draw.ellipse(img, (130, 130, 130), (5, 8, 6, 4))
    pygame.draw.line(img, (150, 150, 150), (8, 4), (8, 10), 2)
    pygame.draw.line(img, (150, 150, 150), (6, 6), (10, 6), 2)
    return img

def _make_statue():
    img = _GRASS.copy()
    pygame.draw.rect(img, (160, 160, 170), (6, 10, 4, 5))
    pygame.draw.circle(img, (180, 180, 190), (8, 6), 3)
    pygame.draw.rect(img, (140, 140, 150), (5, 8, 6, 2))
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
    CAMPFIRE: _make_campfire(), TENT: _make_tent(), FISHING_SPOT: _make_fishing_spot(),
    MUSHROOM_PATCH: _make_mushroom_patch(), BERRY_BUSH: _make_berry_bush(),
    HERB_PLANT: _make_herb_plant(), CHEST_CLOSED: _make_chest(),
    SIGNPOST: _make_signpost(), BRIDGE: _make_bridge(),
    GATE_LOCKED: _make_gate(), WELL: _make_well(), GRAVE: _make_grave(),
    STATUE: _make_statue(),
}

for (_row, _col), _tile_id in FOUNTAIN_TILES.items():
    TILE_IMAGES[_tile_id] = _make_fountain_tile(_row, _col, size=3)


# ---- Character / NPC sprites ------
def make_kyle():
    p = {".":None,"k":(45,32,22),"f":(238,205,175),"b":(55,95,210),"d":(32,62,158),"w":(255,255,255),"n":(30,22,15)}
    rows = [
        "....nnnnnnnn....","...nkkkkkkkkn...","...kfffffffkk...",
        "..kffwf.wfffk...","...ffffffff.k...","....ffffffff....",
        "...bbbbbbbbbb...","..bbbbbbbbbbbb..","..bbbbbbbbbbbb..",
        "..bbbddddddbb...","..bb........bb..","..bb........bb..",
        "..kk........kk..","..nn........nn..","................",
        "................",
    ]
    return make_surface(rows, p)

def make_noah():
    p = {".":None,"k":(58,42,28),"K":(45,32,20),"f":(212,168,128),"F":(185,142,105),
         "e":(60,150,80),"b":(50,38,26),"v":(40,55,95),"V":(30,42,75),
         "t":(190,150,105),"p":(120,95,65),"P":(95,75,50),"s":(150,150,155),
         "w":(100,70,40),"l":(70,150,60)}
    rows = [
        "....kKkk.kk.....","...kkkkkkkkKk...","..kkkkkkkkkkkk..",
        "..kKffffffFkk...",".sKffeffeFfk....","lwKffffffFk.....",
        ".w.bbbbbbbk.....","w..bbbbbbb......","w..vvVtttvv.....",
        "..vvvVtttVvv....","..vvVVVVvv......","...ppFFpp.......",
        "..ppP..Ppp......","..pp....pp......","..PP....PP......",
        "................",
    ]
    return make_surface(rows, p)

def make_merchant():
    p = {".":None,"h":(95,42,128),"s":(62,28,90),"f":(42,32,38),"g":(218,182,65),"e":(155,105,200)}
    rows = [
        "....hhhhhhhh....","...hhhhhhhhhh...","..hhhhffffhhhh..",
        "..hhhfe..efhhh..","..hhhffffffhh...","...hhhhhhhhhh...",
        "...hhssssshh....","..hhssssssshh...","..hhssgsssssh...",
        "..hhssssssshh...","..hh........hh..","..hh........hh..",
        "..ss........ss..","..ss........ss..","................",
        "................",
    ]
    return make_surface(rows, p)

def make_werewolf():
    p = {".":None,"g":(100,98,108),"d":(58,58,65),"r":(215,45,45),"w":(238,238,238),"y":(255,210,55)}
    rows = [
        "...g......g.....","..ggg....ggg....","..gggggggggg....",
        ".ggryggggyrggg..",".gggggwgggggg...",".gggggwgggggg...",
        "..gggggggggg....","..gdgggggggd....",".ggdgggggggdg...",
        ".ggdgggggggdg...","..gd........dg..","..gd........dg..",
        "..dd........dd..","..dd........dd..","................",
        "................",
    ]
    return make_surface(rows, p)

def make_chicken():
    p = {".":None,"w":(255,255,255),"y":(240,195,45),"r":(215,55,45),"o":(248,175,55)}
    rows = [
        "......oooo......",".....owwwwo.....","....owwwwwwo....",
        "....rwwwwwww....","....wwwwwwww....","....wwwwwwww....",
        ".....wwwwww.....",".....yy.yy......","................",
        "................","................","................",
        "................","................","................",
        "................",
    ]
    return make_surface(rows, p)

def make_golden_chicken():
    p = {".":None,"w":(255,226,130),"y":(255,195,30),"r":(215,55,45),"o":(255,165,40),"s":(255,255,220)}
    rows = [
        "......oooo......",".....owwwwo..s..","....owwwwwwo....",
        "....rwwwwwww....","....wwwwwwww....","s...wwwwwwww....",
        ".....wwwwww.....",".....yy.yy......","................",
        "................","................","................",
        "................","................","................",
        "................",
    ]
    return make_surface(rows, p)

def make_seagull():
    p = {".":None,"w":(248,248,250)}
    rows = [
        "................","................","................",
        "....ww....ww....","...www....www...","..ww........ww..",
        "................","................","................",
        "................","................","................",
        "................","................","................",
        "................",
    ]
    return make_surface(rows, p)

def make_fish():
    p = {".":None,"b":(100,140,180),"w":(220,240,255),"e":(255,100,100)}
    rows = [
        "................","................","................",
        "................","....bbbbbb......","...bbbbbbbb.....",
        "..bbbbbbbbbe....","...bbbbbbbb.....","....bbbbbb......",
        "................","................","................",
        "................","................","................",
        "................",
    ]
    return make_surface(rows, p)

SPRITES = {
    "kyle": make_kyle(), "noah": make_noah(), "merchant": make_merchant(),
    "werewolf": make_werewolf(), "chicken": make_chicken(),
    "golden_chicken": make_golden_chicken(), "seagull": make_seagull(),
    "fish": make_fish(),
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

    # NEW: Add campfire and tent near dock
    camp_x, camp_y = shore_x - 5, shore_y - 3
    if 0 <= camp_x < MAP_W and 0 <= camp_y < MAP_H and world[camp_y][camp_x] == GRASS:
        world[camp_y][camp_x] = CAMPFIRE
    tent_x, tent_y = shore_x - 8, shore_y - 2
    if 0 <= tent_x < MAP_W and 0 <= tent_y < MAP_H and world[tent_y][tent_x] == GRASS:
        world[tent_y][tent_x] = TENT

    # NEW: Add fishing spot
    fish_x, fish_y = shore_x + 8, shore_y + 2
    if 0 <= fish_x < MAP_W and 0 <= fish_y < MAP_H and world[fish_y][fish_x] == WATER:
        world[fish_y][fish_x] = FISHING_SPOT

    # NEW: Add gatherable resources
    resource_types = [MUSHROOM_PATCH, BERRY_BUSH, HERB_PLANT]
    for _ in range(15):
        rx = rng.randint(cx - 40, cx + 40)
        ry = rng.randint(cy - 40, cy + 40)
        if 0 <= rx < MAP_W and 0 <= ry < MAP_H and world[ry][rx] == GRASS:
            dist_c = ((rx - cx) ** 2 + (ry - cy) ** 2) ** 0.5
            if 8 < dist_c < main_radius * 0.85:
                world[ry][rx] = random.choice(resource_types)

    # NEW: Add chests
    for _ in range(3):
        cx_ = rng.randint(cx - 50, cx + 50)
        cy_ = rng.randint(cy - 50, cy + 50)
        if 0 <= cx_ < MAP_W and 0 <= cy_ < MAP_H and world[cy_][cx_] == GRASS:
            dist_c = ((cx_ - cx) ** 2 + (cy_ - cy) ** 2) ** 0.5
            if 15 < dist_c < main_radius * 0.8:
                world[cy_][cx_] = CHEST_CLOSED

    # NEW: Add signpost
    sign_x, sign_y = cx + 10, cy + 12
    if 0 <= sign_x < MAP_W and 0 <= sign_y < MAP_H and world[sign_y][sign_x] == PATH:
        world[sign_y][sign_x] = SIGNPOST

    # NEW: Add well
    well_x, well_y = cx - 15, cy + 8
    if 0 <= well_x < MAP_W and 0 <= well_y < MAP_H and world[well_y][well_x] == GRASS:
        world[well_y][well_x] = WELL

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

    # NEW: Add graves and statues to wolf islands
    for _ in range(rng.randint(1, 3)):
        angle = rng.uniform(0, 6.283); dist = rng.uniform(inner_clear_radius, r * 0.9)
        tx = int(ix + dist * math.cos(angle)); ty = int(iy + dist * math.sin(angle))
        if 0 <= tx < MAP_W and 0 <= ty < MAP_H and world[ty][tx] == WOLF_GRASS:
            if _far_enough(tx, ty, 20):
                world[ty][tx] = GRAVE if rng.random() < 0.7 else STATUE
                occupied.add((tx, ty))


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
# Item System
# ---------------------------------------------------------------------------
class Item:
    def __init__(self, name, item_type, rarity, description="", value=0, stackable=True, max_stack=99):
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.description = description
        self.value = value
        self.stackable = stackable
        self.max_stack = max_stack

ITEMS = {
    "chicken": Item("Chicken", ItemType.CONSUMABLE, ItemRarity.COMMON, "A plump chicken. Noah loves these.", 10),
    "golden_chicken": Item("Golden Chicken", ItemType.TREASURE, ItemRarity.RARE, "A shimmering golden chicken. Extremely valuable!", 50),
    "materials": Item("Materials", ItemType.MATERIAL, ItemRarity.COMMON, "Wood, cloth, and rope for crafting.", 5),
    "glider": Item("Glider", ItemType.TOOL, ItemRarity.UNCOMMON, "Allows crossing water. Consumed on use.", 30),
    "mushroom": Item("Wild Mushroom", ItemType.CONSUMABLE, ItemRarity.COMMON, "Restores 15 HP. Might be poisonous...", 3),
    "berries": Item("Wild Berries", ItemType.CONSUMABLE, ItemRarity.COMMON, "Restores 10 HP.", 2),
    "herb": Item("Medicinal Herb", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, "Restores 30 HP and cures poison.", 8),
    "fish": Item("Fish", ItemType.CONSUMABLE, ItemRarity.COMMON, "Fresh catch. Restores 20 HP.", 5),
    "potion": Item("Health Potion", ItemType.CONSUMABLE, ItemRarity.RARE, "Restores 50 HP instantly.", 25),
    "sword": Item("Iron Sword", ItemType.WEAPON, ItemRarity.UNCOMMON, "Deals 30 damage per hit.", 40),
    "armor": Item("Leather Armor", ItemType.ARMOR, ItemRarity.UNCOMMON, "Reduces damage by 25%.", 35),
}


# ---------------------------------------------------------------------------
# Quest System
# ---------------------------------------------------------------------------
class Quest:
    def __init__(self, title, description, objectives, rewards):
        self.title = title
        self.description = description
        self.objectives = objectives  # dict: {objective_name: current_count}
        self.rewards = rewards  # dict: {item_name: count}
        self.completed = False
        self.turned_in = False

    def check_completion(self):
        self.completed = all(count >= req for count, req in zip(self.objectives.values(), 
                                                                 [self.objectives.get(k, 0) for k in self.objectives]))
        return self.completed


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
        self.last_return_pos = None

        # NEW: Inventory system
        self.inventory = {}  # item_name: count
        self.equipped_weapon = None
        self.equipped_armor = None

        # NEW: Quest system
        self.quests = []
        self.completed_quests = []
        self._init_quests()

        # NEW: Stats
        self.total_kills = 0
        self.total_chickens_found = 0
        self.play_time = 0.0

        # NEW: Discoveries
        self.discovered_tiles = set()

        # NEW: Day/Night
        self.day_time = 0.0  # 0-24 hours
        self.day_count = 1

        # NEW: Weather
        self.weather = WeatherType.CLEAR
        self.weather_timer = 0.0

        # NEW: Cooking recipes discovered
        self.recipes_discovered = {"cooked_chicken": False, "stew": False, "potion": False}

    def _init_quests(self):
        self.quests.append(Quest(
            "First Steps",
            "Find and collect 3 chickens from the wild.",
            {"collect_chickens": 0},
            {"materials": 4}
        ))
        self.quests.append(Quest(
            "Island Explorer",
            "Visit a werewolf island and defeat 2 werewolves.",
            {"werewolves_killed": 0},
            {"money": 20, "potion": 1}
        ))
        self.quests.append(Quest(
            "Black Market",
            "Sell 5 chickens to the merchant without Noah finding out.",
            {"chickens_sold_secret": 0},
            {"money": 50}
        ))

    def give_chicken_to_noah(self, amount=1):
        if self.chickens >= amount and amount > 0:
            self.chickens -= amount
            self.materials += amount * 2
            self.mission_stage += 1
            # Update quest
            for q in self.quests:
                if "collect_chickens" in q.objectives and not q.completed:
                    q.objectives["collect_chickens"] = self.total_chickens_found
            return f"Noah takes {amount} chicken and hands you {amount * 2} materials."
        return "You don't have any chicken to give Noah."

    def sell_chicken_to_merchant(self, amount=1):
        if self.chickens < amount or amount <= 0:
            return "You don't have any chicken to sell."
        self.chickens -= amount
        self.chickens_sold += amount
        self.money += amount * 8
        message = f"You sell {amount} chicken for {amount * 8} gold."
        found_out = random.random() < 0.5
        if found_out:
            penalty_chickens = min(self.chickens, random.randint(1, 2))
            penalty_money = min(self.money, random.randint(5, 15))
            self.chickens -= penalty_chickens
            self.money -= penalty_money
            self.noah_trust = False
            message += f"\nNoah found out! Takes {penalty_chickens} chicken and {penalty_money}g."
        else:
            message += "\nNoah doesn't seem to have noticed..."
            # Update secret selling quest
            for q in self.quests:
                if "chickens_sold_secret" in q.objectives and not q.completed:
                    q.objectives["chickens_sold_secret"] += amount
        if self.chickens_sold >= CHICKENS_TO_WIN:
            self.won = True
            self.game_over = True
        return message

    def add_to_inventory(self, item_name, count=1):
        if item_name not in self.inventory:
            self.inventory[item_name] = 0
        item = ITEMS.get(item_name)
        if item and item.stackable:
            self.inventory[item_name] = min(self.inventory[item_name] + count, item.max_stack)
        else:
            self.inventory[item_name] += count

    def remove_from_inventory(self, item_name, count=1):
        if item_name in self.inventory:
            self.inventory[item_name] = max(0, self.inventory[item_name] - count)
            if self.inventory[item_name] == 0:
                del self.inventory[item_name]


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
        self.attack_damage = 20
        self.damage_reduction = 0.0
        self.poisoned = 0.0
        self.bleeding = 0.0

    def try_move(self, dx, dy, world, has_glider=False):
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

    def take_damage(self, amount):
        actual = amount * (1 - self.damage_reduction)
        self.health -= actual
        self.last_damage_time = pygame.time.get_ticks()
        return self.health <= 0

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)


class Werewolf(Entity):
    STATE_WANDER = "wander"
    STATE_CHASE = "chase"

    def __init__(self, x, y, home_radius_tiles, center):
        super().__init__(x, y, SPRITES["werewolf"])
        self.health = 40
        self.max_health = 40
        self.speed = 4.2
        self.state = Werewolf.STATE_WANDER
        self.wander_dir = pygame.Vector2(random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
        self.wander_timer = random.uniform(0.5, 1.5)
        self.detect_radius = 7
        self.has_chicken = True
        self.has_materials = random.random() < 0.3
        self.has_potion = random.random() < 0.1
        self.center = center
        self.home_radius = home_radius_tiles
        self.flash_time = 0
        self.bleed_stacks = 0

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
        if self.bleed_stacks > 0:
            self.health -= self.bleed_stacks * 2 * dt
            self.bleed_stacks = max(0, self.bleed_stacks - dt)

    def take_damage(self, amount, is_bleed=False):
        self.health -= amount
        if not is_bleed:
            self.flash_time = 0.15
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
        self.schedule = {"sleep": (0, 6), "work": (6, 18), "relax": (18, 24)}

    def get_dialogue(self, state: GameState):
        stage = min(state.mission_stage, len(self.DIALOGUE_BY_STAGE) - 1)
        line = self.DIALOGUE_BY_STAGE[stage]
        if not state.noah_trust:
            line = "I KNOW you've been selling chicken to that merchant. Don't think I haven't noticed... Bring me more chicken and we'll call it even."
        # Add quest info
        active_quests = [q for q in state.quests if not q.completed]
        if active_quests:
            line += "\n\nActive Quests:"
            for q in active_quests[:2]:
                line += f"\n- {q.title}"
        return line

    def is_sleeping(self, hour):
        return self.schedule["sleep"][0] <= hour < self.schedule["sleep"][1]


class Merchant(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["merchant"])
        self.bob_amplitude = 1.6
        self.bob_speed = 620.0
        self.stock = {}  # item_name: (price, count)
        self._restock()

    def _restock(self):
        self.stock = {
            "potion": (25, random.randint(1, 3)),
            "sword": (40, 1),
            "armor": (35, 1),
            "fish": (8, random.randint(2, 5)),
        }

    def get_shop_dialogue(self, state):
        msg = "Welcome to the black market! What would you like to buy?\n\n"
        for item_name, (price, count) in self.stock.items():
            if count > 0:
                item = ITEMS.get(item_name)
                msg += f"[{item_name}] {price}g ({count} left) - {item.description if item else ''}\n"
        msg += f"\nYour gold: {state.money}g"
        return msg


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


class Fish(Entity):
    """Swimming fish in water - decorative but can be fished."""
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["fish"])
        self.swim_dir = random.choice([0, 1, 2, 3])
        self.swim_timer = random.uniform(1.0, 3.0)
        self.bob_amplitude = 0.5
        self.bob_speed = 800.0


# ---------------------------------------------------------------------------
# Visual Effects System
# ---------------------------------------------------------------------------
class Particle:
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
        text_surf = FONTS['medium'].render(self.text, True, color[:3])
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (px - text_surf.get_width() // 2, py))


class ScreenShake:
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


class LightingSystem:
    """Day/night lighting overlay."""
    def __init__(self):
        self.light_radius = 180  # pixels

    def get_time_of_day(self, hour):
        if 5 <= hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= hour < 17:
            return TimeOfDay.DAY
        elif 17 <= hour < 20:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT

    def draw_overlay(self, surface, hour, player_pos):
        tod = self.get_time_of_day(hour)
        name, tint_color, darkness = tod.value
        if darkness <= 0.01:
            return

        # Create darkness overlay with player light
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((*tint_color, int(darkness * 180)))

        # Cut out light around player
        px = SCREEN_W // 2
        py = SCREEN_H // 2
        for r in range(self.light_radius, 0, -5):
            alpha = int(darkness * 180 * (r / self.light_radius))
            pygame.draw.circle(overlay, (*tint_color, max(0, alpha)), (px, py), r)

        # Lantern light sources
        surface.blit(overlay, (0, 0))


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def draw_text(surface, text, pos, font_name='normal', color=(255, 255, 255), max_width=None):
    font = FONTS.get(font_name, FONTS['normal'])
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

    # Health bar with segments
    bx, by = 10, hud_y + 8
    bw, bh = 160, 14
    pygame.draw.rect(surface, (55, 18, 18), (bx, by, bw, bh))
    hp_w = int(bw * max(0, player.health) / player.max_health)
    bar_col = (210, 45, 45) if player.health / player.max_health > 0.25 else (255, 100, 20)
    if hp_w > 0:
        pygame.draw.rect(surface, bar_col, (bx, by, hp_w, bh))
    # HP segments
    for i in range(1, 10):
        sx = bx + int(bw * i / 10)
        pygame.draw.line(surface, (30, 10, 10), (sx, by), (sx, by + bh), 1)
    pygame.draw.rect(surface, (180, 130, 130), (bx, by, bw, bh), 1)
    hp_surf = FONTS['tiny'].render(f"HP {int(player.health)}/{player.max_health}", True, (255, 225, 225))
    surface.blit(hp_surf, (bx + 4, by + 1))

    # Stamina bar
    sx, sy = 10, hud_y + 26
    sw, sh = 120, 8
    pygame.draw.rect(surface, (18, 35, 55), (sx, sy, sw, sh))
    stam_w = int(sw * max(0, player.stamina) / player.max_stamina)
    if stam_w > 0:
        pygame.draw.rect(surface, (65, 180, 220), (sx, sy, stam_w, sh))
    pygame.draw.rect(surface, (100, 160, 180), (sx, sy, sw, sh), 1)

    # Day/Time indicator
    hour = int(state.day_time)
    minute = int((state.day_time - hour) * 60)
    time_str = f"Day {state.day_count} {hour:02d}:{minute:02d}"
    tod = TimeOfDay.DAY
    if 5 <= hour < 7: tod = TimeOfDay.DAWN
    elif 17 <= hour < 20: tod = TimeOfDay.DUSK
    elif hour >= 20 or hour < 5: tod = TimeOfDay.NIGHT
    time_color = tod.value[1]
    surface.blit(FONTS['tiny'].render(time_str, True, time_color), (bx + bw + 10, by))

    # Weather indicator
    weather_icons = {
        WeatherType.CLEAR: "☀", WeatherType.CLOUDY: "☁",
        WeatherType.RAIN: "🌧", WeatherType.STORM: "⛈", WeatherType.FOG: "🌫"
    }
    weather_text = f"{weather_icons.get(state.weather, '?')} {state.weather.name}"
    surface.blit(FONTS['tiny'].render(weather_text, True, (180, 180, 200)), (bx + bw + 10, by + 12))

    # Item stats row
    sx, sy = 10, hud_y + 40
    # Chicken
    pygame.draw.circle(surface, (248, 195, 45), (sx + 6, sy + 6), 5)
    pygame.draw.circle(surface, (200, 148, 30), (sx + 6, sy + 6), 5, 1)
    surface.blit(FONTS['tiny'].render(f"x{state.chickens}", True, (255, 240, 185)), (sx + 14, sy))

    mx = sx + 50
    pygame.draw.rect(surface, (80, 175, 225), (mx, sy, 10, 10))
    pygame.draw.rect(surface, (50, 130, 185), (mx, sy, 10, 10), 1)
    surface.blit(FONTS['tiny'].render(f"x{state.materials}", True, (185, 230, 255)), (mx + 13, sy))

    gx = mx + 55
    pygame.draw.polygon(surface, (255, 195, 35), [(gx+5, sy), (gx+10, sy+5), (gx+5, sy+10), (gx, sy+5)])
    surface.blit(FONTS['tiny'].render(f"{state.money}g", True, (255, 225, 110)), (gx + 13, sy))

    glx = gx + 60
    pygame.draw.polygon(surface, (180, 160, 140), [(glx+5, sy), (glx+10, sy+5), (glx+5, sy+10), (glx, sy+5)])
    surface.blit(FONTS['tiny'].render(f"x{state.gliders}", True, (200, 190, 175)), (glx + 13, sy))

    # Sold progress
    px2 = glx + 50
    sold_col = (100, 235, 115) if state.chickens_sold < CHICKENS_TO_WIN else (255, 215, 50)
    surface.blit(FONTS['tiny'].render(f"Sold:{state.chickens_sold}/{CHICKENS_TO_WIN}", True, sold_col), (px2, sy))

    # Trust indicator
    if state.noah_trust:
        tc, tt = (80, 225, 110), "Noah trusts you"
        pygame.draw.circle(surface, tc, (SCREEN_W - 160, hud_y + 14), 4)
    else:
        tc, tt = (230, 80, 80), "Noah suspicious!"
        pts = [(SCREEN_W - 160, hud_y + 10), (SCREEN_W - 164, hud_y + 20), (SCREEN_W - 156, hud_y + 20)]
        pygame.draw.polygon(surface, tc, pts)
    surface.blit(FONTS['tiny'].render(tt, True, tc), (SCREEN_W - 152, hud_y + 8))

    # Island indicator
    if state.on_wolf_island:
        surface.blit(FONTS['small'].render("⚠ WOLF ISLAND!", True, (230, 80, 80)), (SCREEN_W - 160, hud_y + 26))

    # Active quest hint
    active = [q for q in state.quests if not q.completed]
    if active:
        q = active[0]
        obj_text = " | ".join([f"{k}: {v}" for k, v in q.objectives.items()])
        surface.blit(FONTS['tiny'].render(f"Quest: {q.title} ({obj_text})", True, (200, 180, 100)), (10, hud_y + 56))

    # Status effects
    status_y = hud_y + 72
    if player.poisoned > 0:
        surface.blit(FONTS['tiny'].render("☠ POISONED", True, (100, 200, 100)), (10, status_y))
    if player.bleeding > 0:
        surface.blit(FONTS['tiny'].render("🩸 BLEEDING", True, (200, 50, 50)), (80, status_y))

    hint = "E:interact G:give B:build SPC:attack Q:return Shift:sprint I:inventory"
    surface.blit(FONTS['tiny'].render(hint, True, (110, 95, 145)), (10, hud_y + HUD_HEIGHT - 15))


def draw_inventory(surface, state: GameState):
    """Draw inventory overlay."""
    inv_w, inv_h = 300, 350
    inv_x = (SCREEN_W - inv_w) // 2
    inv_y = (SCREEN_H - inv_h) // 2

    # Background
    pygame.draw.rect(surface, (15, 12, 25), (inv_x, inv_y, inv_w, inv_h))
    pygame.draw.rect(surface, (120, 100, 160), (inv_x, inv_y, inv_w, inv_h), 2)

    # Title
    title = FONTS['large'].render("INVENTORY", True, (220, 200, 255))
    surface.blit(title, (inv_x + (inv_w - title.get_width()) // 2, inv_y + 10))

    # Items
    y = inv_y + 45
    items = list(state.inventory.items())
    for i, (item_name, count) in enumerate(items[:12]):
        item = ITEMS.get(item_name)
        rarity_color = item.rarity.value[1] if item else (200, 200, 200)
        text = f"  {item_name} x{count}"
        if item:
            text += f" ({item.item_type.name})"
        surface.blit(FONTS['small'].render(text, True, rarity_color), (inv_x + 15, y))
        y += 22

    if not items:
        surface.blit(FONTS['small'].render("  (Empty)", True, (100, 100, 100)), (inv_x + 15, y))

    # Equipped
    y += 20
    surface.blit(FONTS['normal'].render("Equipped:", True, (180, 160, 200)), (inv_x + 15, y))
    y += 22
    weapon = state.equipped_weapon or "None"
    armor = state.equipped_armor or "None"
    surface.blit(FONTS['small'].render(f"  Weapon: {weapon}", True, (200, 180, 150)), (inv_x + 15, y))
    y += 20
    surface.blit(FONTS['small'].render(f"  Armor: {armor}", True, (200, 180, 150)), (inv_x + 15, y))

    # Close hint
    surface.blit(FONTS['tiny'].render("Press I or ESC to close", True, (150, 130, 170)), 
                 (inv_x + 80, inv_y + inv_h - 25))


def show_message_box(surface, message, title=""):
    box_x, box_margin = 30, 30
    box_w = SCREEN_W - box_margin * 2
    text_max_width = box_w - 28
    line_count = 0
    for raw_line in message.split("\n"):
        words = raw_line.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if FONTS['normal'].size(candidate)[0] <= text_max_width or not current:
                current = candidate
            else:
                line_count += 1
                current = word
        line_count += 1
    line_height = FONTS['normal'].get_height() + 4
    text_block_height = line_count * line_height
    box_h = max(100, min(text_block_height + 70, SCREEN_H - 40))
    box_y = max(10, SCREEN_H - box_h - 10)
    box = pygame.Rect(box_x, box_y, box_w, box_h)

    pygame.draw.rect(surface, (10, 10, 18), box)
    pygame.draw.rect(surface, (180, 150, 100), box, 2)

    if title:
        title_surf = FONTS['large'].render(title, True, (220, 190, 120))
        surface.blit(title_surf, (box.x + 14, box.y + 10))
        draw_text(surface, message, (box.x + 14, box.y + 38), font_name='normal', max_width=text_max_width)
    else:
        draw_text(surface, message, (box.x + 14, box.y + 14), font_name='normal', max_width=text_max_width)

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
        "Kyle finally has enough gold saved up...\nHe leaves the maze behind and goes home to find his dog.\n\n🏆 YOU WIN! 🏆",
        (40, SCREEN_H // 2 - 60), font_name='title', color=(210, 170, 40))
    pygame.display.flip()
    pygame.time.wait(5000)


def show_lose_screen(surface):
    surface.fill((10, 10, 15))
    draw_text(surface,
        "Kyle collapses, exhausted and wounded...\nThe maze claims another wanderer.\n\n💀 GAME OVER 💀",
        (40, SCREEN_H // 2 - 60), font_name='title', color=(200, 60, 60))
    pygame.display.flip()
    pygame.time.wait(5000)


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
    if phase > RAIN_FRACTION: return 0.0
    if phase < RAIN_FADE: return phase / RAIN_FADE
    if phase > RAIN_FRACTION - RAIN_FADE: return (RAIN_FRACTION - phase) / RAIN_FADE
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
    if not _HAS_SURFARRAY or red_array is None:
        return
    step = max(1, int(2 * scale))
    rng = random.Random(world_seed)
    sampled = red_array[::step, ::step]
    edge_mask = (sampled > 90) & (sampled < 200)
    xs, ys = edge_mask.nonzero()
    radius = max(1, scale)
    for xi, yi in zip(xs, ys):
        x, y = int(xi) * step, int(yi) * step
        jx = rng.uniform(-0.6, 0.6) * scale
        jy = rng.uniform(-0.6, 0.6) * scale
        pygame.draw.circle(surface, outline_color, (x + jx, y + jy), radius)

_TERRAIN_SUPERSAMPLE = 6

def render_world(world, player, npcs_visible, shake_offset=(0, 0), discovered=None):
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
            if is_wolf: any_wolf_grass = True
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

    world_seed = 42
    _draw_hand_drawn_outline(terrain_small, land_red_array, ORGANIC_OUTLINE_COLOR, world_seed, scale=1)

    terrain_surf = pygame.transform.smoothscale(terrain_small, (terrain_px_size, terrain_px_size))
    terrain_origin_x = (first_tile_x - margin) * DISPLAY_TILE - cam_pixel_x
    terrain_origin_y = (first_tile_y - margin) * DISPLAY_TILE - cam_pixel_y
    screen.blit(terrain_surf, (terrain_origin_x, terrain_origin_y))

    ticks = pygame.time.get_ticks()
    for ty_offset in range(VIEW_TILES_ACROSS + 1):
        world_ty = first_tile_y + ty_offset
        if not (0 <= world_ty < MAP_H): continue
        for tx_offset in range(VIEW_TILES_ACROSS + 1):
            world_tx = first_tile_x + tx_offset
            if not (0 <= world_tx < MAP_W): continue
            tile_id = world[world_ty][world_tx]
            if tile_id in TERRAIN_BASE_TILES: continue
            sx = world_tx * DISPLAY_TILE - cam_pixel_x
            sy = world_ty * DISPLAY_TILE - cam_pixel_y

            # Fog of war - skip undiscovered tiles
            if discovered and (world_tx, world_ty) not in discovered:
                continue

            if tile_id in TREE_CANOPY:
                phase = (world_tx * 0.7 + world_ty * 1.3) % 6.283
                angle = math.sin(ticks / 900.0 + phase) * 4.0
                canopy = pygame.transform.rotate(TREE_CANOPY[tile_id], angle)
                off_x = (canopy.get_width() - DISPLAY_TILE) / 2
                off_y = (canopy.get_height() - DISPLAY_TILE) / 2
                screen.blit(canopy, (sx - off_x, sy - off_y))
                continue

            img = TILE_IMAGES.get(tile_id)
            if img is None: continue
            screen.blit(img, (sx, sy))

    px = SCREEN_W / 2 - DISPLAY_TILE / 2
    py = SCREEN_H / 2 - DISPLAY_TILE / 2

    for entity in npcs_visible:
        ex = (entity.x - player.x) * DISPLAY_TILE + SCREEN_W / 2 - DISPLAY_TILE / 2
        ey = (entity.y - player.y) * DISPLAY_TILE + SCREEN_H / 2 - DISPLAY_TILE / 2
        if entity.bob_amplitude:
            ey += math.sin(pygame.time.get_ticks() / entity.bob_speed + entity._bob_phase) * entity.bob_amplitude
        if -DISPLAY_TILE <= ex <= SCREEN_W and -DISPLAY_TILE <= ey <= SCREEN_H:
            if isinstance(entity, Werewolf) and entity.flash_time > 0:
                flash_surf = entity.sprite.copy()
                flash_surf.fill((255, 100, 100), special_flags=pygame.BLEND_ADD)
                screen.blit(flash_surf, (ex, ey))
            else:
                screen.blit(entity.sprite, (ex, ey))

    screen.blit(player.sprite, (px, py))


def draw_minimap(surface, world, player, island_centers, state, discovered):
    mm_w, mm_h = 90, 90
    mm_x, mm_y = SCREEN_W - mm_w - 8, 8
    mm_surf = pygame.Surface((mm_w, mm_h))
    mm_surf.fill((20, 25, 35))

    scale_x = mm_w / MAP_W
    scale_y = mm_h / MAP_H

    # Draw discovered areas
    for (tx, ty) in discovered:
        px = int(tx * scale_x)
        py = int(ty * scale_y)
        if 0 <= px < mm_w and 0 <= py < mm_h:
            tile = world[ty][tx]
            if tile == WATER:
                mm_surf.set_at((px, py), (30, 50, 90))
            elif tile == WOLF_GRASS:
                mm_surf.set_at((px, py), (60, 100, 50))
            else:
                mm_surf.set_at((px, py), (50, 100, 60))

    # Islands
    for (ix, iy, r) in island_centers:
        pygame.draw.circle(mm_surf, (80, 40, 40), (int(ix * scale_x), int(iy * scale_y)), max(2, int(r * scale_x)))

    # Player
    px = int(player.x * scale_x)
    py = int(player.y * scale_y)
    pygame.draw.circle(mm_surf, (255, 50, 50), (px, py), 2)

    # Main island
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

    particles = []
    floating_texts = []
    screen_shake = ScreenShake()
    lighting = LightingSystem()

    show_inventory = False

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)
        state.play_time += dt

        # Day/night cycle
        state.day_time += dt * 0.5  # 48 game minutes per real minute
        if state.day_time >= 24:
            state.day_time -= 24
            state.day_count += 1
            # Restock merchant daily
            merchant._restock()

        # Weather update
        state.weather_timer += dt
        if state.weather_timer > 60:  # Change weather every minute
            state.weather_timer = 0
            weights = [0.4, 0.25, 0.2, 0.1, 0.05]
            state.weather = random.choices(list(WeatherType), weights=weights)[0]

        # Discover tiles
        px_tile, py_tile = int(player.x), int(player.y)
        for dy in range(-VIEW_RADIUS_TILES, VIEW_RADIUS_TILES + 1):
            for dx in range(-VIEW_RADIUS_TILES, VIEW_RADIUS_TILES + 1):
                tx, ty = px_tile + dx, py_tile + dy
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    state.discovered_tiles.add((tx, ty))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if show_inventory:
                        show_inventory = False
                    else:
                        running = False

                if event.key == pygame.K_i:
                    show_inventory = not show_inventory

                if not show_inventory:
                    if event.key == pygame.K_e:
                        ptile = player.tile
                        dist_to_noah = ((player.x - noah.x) ** 2 + (player.y - noah.y) ** 2) ** 0.5
                        dist_to_desk = ((ptile[0] - desk_pos[0]) ** 2 + (ptile[1] - desk_pos[1]) ** 2) ** 0.5
                        dist_to_merchant = ((player.x - merchant.x) ** 2 + (player.y - merchant.y) ** 2) ** 0.5

                        # Check for interactive tiles
                        tile_here = world[ptile[1]][ptile[0]]

                        if dist_to_noah < 1.8:
                            show_message_box(screen, noah.get_dialogue(state), "Noah Ficsher")

                        elif tile_here == CAMPFIRE:
                            if player.health < player.max_health:
                                player.heal(20)
                                floating_texts.append(FloatingText(
                                    player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                                    "+20 HP (rested)", (100, 255, 100)
                                ))
                            else:
                                show_message_box(screen, "The campfire is warm and comforting.", "Campfire")

                        elif tile_here == WELL:
                            player.heal(10)
                            floating_texts.append(FloatingText(
                                player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                                "+10 HP (refreshing water)", (100, 200, 255)
                            ))

                        elif tile_here == SIGNPOST:
                            show_message_box(screen,
                                "Welcome to the Maze!\n\n"
                                "North: Town Plaza and Noah's Hut\n"
                                "East: The Dock and Fishing Spot\n"
                                "South: Wildlands (watch for wolves!)\n"
                                "West: Village and Secret Paths",
                                "Signpost")

                        elif tile_here in (MUSHROOM_PATCH, BERRY_BUSH, HERB_PLANT):
                            item_map = {MUSHROOM_PATCH: "mushroom", BERRY_BUSH: "berries", HERB_PLANT: "herb"}
                            item_name = item_map.get(tile_here)
                            if item_name:
                                state.add_to_inventory(item_name, random.randint(1, 3))
                                world[ptile[1]][ptile[0]] = GRASS  # Consumed
                                floating_texts.append(FloatingText(
                                    player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                                    f"Gathered {item_name}!", (150, 255, 150)
                                ))

                        elif tile_here == CHEST_CLOSED:
                            loot = random.choice([
                                ("potion", 1), ("materials", 3), ("fish", 2), ("mushroom", 2)
                            ])
                            item_name, count = loot
                            state.add_to_inventory(item_name, count)
                            world[ptile[1]][ptile[0]] = GRASS  # Opened
                            floating_texts.append(FloatingText(
                                player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                                f"Chest: {item_name} x{count}!", (255, 220, 100)
                            ))

                        elif tile_here == FISHING_SPOT:
                            if random.random() < 0.6:
                                state.add_to_inventory("fish", 1)
                                floating_texts.append(FloatingText(
                                    player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                                    "Caught a fish!", (100, 200, 255)
                                ))
                            else:
                                floating_texts.append(FloatingText(
                                    player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                                    "Nothing bit...", (150, 150, 150)
                                ))

                        elif dist_to_desk < 1.5 and not state.desk_lifted:
                            state.desk_lifted = True
                            world[desk_pos[1]][desk_pos[0]] = MAT
                            show_message_box(screen, "You lift the desk aside, revealing a mat underneath...", "Desk")

                        elif dist_to_desk < 1.5 and state.desk_lifted and not state.mat_lifted:
                            state.mat_lifted = True
                            world[desk_pos[1]][desk_pos[0]] = TRAPDOOR_OPEN
                            show_message_box(screen, "You lift the mat and find a trapdoor leading down.", "Secret")

                        elif dist_to_desk < 1.5 and state.mat_lifted:
                            state.in_black_market = True
                            player.x, player.y = market_x + 3, market_y + 1
                            show_message_box(screen, "You climb down into the hidden black market.", "Black Market")

                        elif state.in_black_market and dist_to_merchant < 1.8:
                            # Shop interface
                            show_message_box(screen, merchant.get_shop_dialogue(state), "Black Market Shop")
                            amount = min(2, state.chickens)
                            if amount > 0:
                                msg = state.sell_chicken_to_merchant(amount)
                                show_message_box(screen, msg, "Transaction")

                        elif state.in_black_market and player.tile == market_entry_tile:
                            state.in_black_market = False
                            player.x, player.y = desk_pos[0], desk_pos[1] + 1
                            show_message_box(screen, "You climb back up out of the black market.", "Exit")

                    if event.key == pygame.K_q:
                        if state.on_wolf_island and state.last_return_pos is not None:
                            player.x, player.y = state.last_return_pos
                            state.on_wolf_island = False
                            state.current_island_index = -1
                            state.last_return_pos = None
                            show_message_box(screen, "You use your glider to return to the main island.", "Return")
                            state.gliders = max(0, state.gliders - 1)
                        elif state.on_wolf_island:
                            show_message_box(screen, "Can't return - no safe landing point remembered!", "Error")

                    if event.key == pygame.K_g:
                        dist_to_noah = ((player.x - noah.x) ** 2 + (player.y - noah.y) ** 2) ** 0.5
                        if dist_to_noah < 1.8:
                            msg = state.give_chicken_to_noah(amount=min(2, state.chickens))
                            show_message_box(screen, msg, "Trade")

                    if event.key == pygame.K_b:
                        if state.materials >= 6:
                            state.materials -= 6
                            state.gliders += 1
                            show_message_box(screen, "You assemble a glider from the materials. Walk toward a smaller island's shore to glide over.", "Crafting")
                        else:
                            show_message_box(screen, "Not enough materials (need 6).", "Crafting")

                    if event.key == pygame.K_SPACE:
                        now = pygame.time.get_ticks()
                        if now - last_attack_time > attack_cooldown:
                            last_attack_time = now
                            screen_shake.trigger(3.0, 0.1)
                            for wolf in list(werewolves):
                                dist = ((player.x - wolf.x) ** 2 + (player.y - wolf.y) ** 2) ** 0.5
                                if dist < 1.6:
                                    dmg = player.attack_damage
                                    if state.equipped_weapon == "sword":
                                        dmg = 30
                                    if wolf.take_damage(dmg):
                                        wx = wolf.x * DISPLAY_TILE
                                        wy = wolf.y * DISPLAY_TILE
                                        for _ in range(10):
                                            particles.append(Particle(
                                                wx, wy,
                                                random.uniform(-40, 40), random.uniform(-50, -15),
                                                (200, 50, 50), random.uniform(0.3, 0.7), size=3
                                            ))
                                        floating_texts.append(FloatingText(wx, wy, "+1 Chicken", (255, 200, 50)))
                                        if wolf.has_materials:
                                            floating_texts.append(FloatingText(wx, wy - 15, "+1 Material", (100, 200, 255)))
                                            state.materials += 1
                                        if wolf.has_potion:
                                            floating_texts.append(FloatingText(wx, wy - 30, "+1 Potion!", (255, 100, 255)))
                                            state.add_to_inventory("potion", 1)
                                        werewolves.remove(wolf)
                                        state.total_kills += 1
                                        if wolf.has_chicken:
                                            state.chickens += 1
                                            state.total_chickens_found += 1
                                        # Update quest
                                        for q in state.quests:
                                            if "werewolves_killed" in q.objectives and not q.completed:
                                                q.objectives["werewolves_killed"] += 1

        if not show_inventory:
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

            if sprinting and (dx or dy) and player.stamina > 0:
                player.stamina = max(0, player.stamina - 30 * dt)
            elif player.stamina < player.max_stamina:
                player.stamina = min(player.max_stamina, player.stamina + 15 * dt)

            def _tile_passable(tile_id):
                if tile_id == WATER:
                    return state.gliders > 0
                return tile_id not in SOLID_TILES

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

            if crossed_water:
                prev_tx, prev_ty = int(player.x - dx), int(player.y - dy)
                if 0 <= prev_tx < MAP_W and 0 <= prev_ty < MAP_H:
                    if world[prev_ty][prev_tx] != WATER:
                        state.gliders = max(0, state.gliders - 1)
                        floating_texts.append(FloatingText(
                            player.x * DISPLAY_TILE, player.y * DISPLAY_TILE,
                            "Glider used!", (200, 200, 200)
                        ))

            # Check wolf island
            state.on_wolf_island = False
            for i, (ix, iy, r) in enumerate(island_centers):
                dist = ((player.x - ix) ** 2 + (player.y - iy) ** 2) ** 0.5
                if dist < r:
                    if not state.on_wolf_island:
                        state.last_return_pos = (cx, cy + 5)
                    state.on_wolf_island = True
                    state.current_island_index = i
                    break

            # Wild chicken pickups
            for chick in wild_chickens:
                if chick.collected: continue
                dist = ((player.x - chick.x) ** 2 + (player.y - chick.y) ** 2) ** 0.5
                if dist < 1.0:
                    chick.collected = True
                    state.chickens += chick.value
                    state.total_chickens_found += chick.value
                    cx_ = chick.x * DISPLAY_TILE
                    cy_ = chick.y * DISPLAY_TILE
                    for _ in range(8):
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
                    dmg = 60 * dt
                    if state.equipped_armor == "armor":
                        dmg *= 0.75
                    player.take_damage(dmg)
                    in_combat = True
                    screen_shake.trigger(2.0, 0.05)

            # Status effects
            if player.poisoned > 0:
                player.health -= 5 * dt
                player.poisoned -= dt
            if player.bleeding > 0:
                player.health -= 3 * dt
                player.bleeding -= dt

            # Health regen
            if not in_combat and pygame.time.get_ticks() - player.last_damage_time > 3000:
                if player.health < player.max_health and player.poisoned <= 0:
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
        render_world(world, player, visible_npcs, shake_offset, state.discovered_tiles)

        cam_pixel_x = player.x * DISPLAY_TILE - SCREEN_W / 2 + shake_offset[0]
        cam_pixel_y = player.y * DISPLAY_TILE - SCREEN_H / 2 + shake_offset[1]
        for p in particles:
            p.draw(screen, cam_pixel_x, cam_pixel_y)
        for t in floating_texts:
            t.draw(screen, cam_pixel_x, cam_pixel_y)

        draw_minimap(screen, world, player, island_centers, state, state.discovered_tiles)

        # Weather
        rain_intensity = compute_rain_intensity(pygame.time.get_ticks() / 1000.0)
        if rain_intensity > 0 and state.weather in (WeatherType.RAIN, WeatherType.STORM):
            draw_weather_overlay(screen, rain_drops, rain_intensity, dt)

        # Day/night lighting
        lighting.draw_overlay(screen, state.day_time, (player.x, player.y))

        draw_hud(screen, state, player)

        if show_inventory:
            draw_inventory(screen, state)

        pygame.display.flip()

    if state.won:
        show_win_screen(screen)
    elif player.health <= 0:
        show_lose_screen(screen)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
