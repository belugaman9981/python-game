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

# ---------------------------------------------------------------------------
# Core constants
# ---------------------------------------------------------------------------
pygame.init()

TILE = 16                      # every tile and character sprite is 16x16
MAP_W, MAP_H = 700, 700        # world size in TILES (11,200 x 11,200 px)

VIEW_RADIUS_TILES = 13         # ~10-15 tile radius of visibility, as requested
VIEW_TILES_ACROSS = VIEW_RADIUS_TILES * 2 + 1  # tiles visible across the screen

SCREEN_SIZE = VIEW_TILES_ACROSS * TILE   # window matches the visible radius exactly
SCREEN_W = SCREEN_H = SCREEN_SIZE
HUD_HEIGHT = 56

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H + HUD_HEIGHT))
pygame.display.set_caption("Kyle Jordan's Maze Adventure")
clock = pygame.time.Clock()
FPS = 60

FONT = pygame.font.SysFont("arial", 16)
BIG_FONT = pygame.font.SysFont("arial", 30, bold=True)

CHICKENS_TO_WIN = 8

# ---------------------------------------------------------------------------
# Tile types
# ---------------------------------------------------------------------------
WATER = 0
SAND = 1
GRASS = 2
HUT_FLOOR = 3
HUT_WALL = 4
DESK = 5
MAT = 6
TRAPDOOR_OPEN = 7
MARKET_FLOOR = 8
MARKET_WALL = 9
WOLF_GRASS = 10  # grass tile on the werewolf islands (kept separate for clarity)

SOLID_TILES = {HUT_WALL, MARKET_WALL, WATER}  # can't walk through these


# ---------------------------------------------------------------------------
# Tiny 16x16 pixel-art drawing helpers
# ---------------------------------------------------------------------------
def make_surface(pixels, palette):
    """Build a 16x16 surface from a 16x16 grid of palette-index characters."""
    surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), palette[ch])
    return surf


def solid_tile(color):
    surf = pygame.Surface((TILE, TILE))
    surf.fill(color)
    return surf


# ---- Terrain tiles (simple, since they're backgrounds) --------------------
TILE_IMAGES = {
    WATER: solid_tile((40, 90, 190)),
    SAND: solid_tile((220, 200, 140)),
    GRASS: solid_tile((70, 165, 90)),
    WOLF_GRASS: solid_tile((55, 120, 70)),
    HUT_FLOOR: solid_tile((160, 120, 80)),
    HUT_WALL: solid_tile((110, 75, 45)),
    MARKET_FLOOR: solid_tile((60, 45, 70)),
    MARKET_WALL: solid_tile((35, 25, 45)),
    TRAPDOOR_OPEN: solid_tile((20, 15, 25)),
}

# Add a touch of texture (speckles) to water/grass so it doesn't look completely flat
def add_speckles(img, dot_color, count=6, seed_extra=0):
    rnd = random.Random(hash((id(img), seed_extra)) & 0xFFFFFFFF)
    img = img.copy()
    for _ in range(count):
        x, y = rnd.randint(0, TILE - 1), rnd.randint(0, TILE - 1)
        img.set_at((x, y), dot_color)
    return img


TILE_IMAGES[WATER] = add_speckles(TILE_IMAGES[WATER], (70, 130, 220), 5)
TILE_IMAGES[GRASS] = add_speckles(TILE_IMAGES[GRASS], (90, 185, 110), 5)
TILE_IMAGES[WOLF_GRASS] = add_speckles(TILE_IMAGES[WOLF_GRASS], (40, 95, 55), 5)
TILE_IMAGES[SAND] = add_speckles(TILE_IMAGES[SAND], (235, 215, 160), 4)


# ---- Desk sprite (sits on hut floor) --------------------------------------
def make_desk():
    img = TILE_IMAGES[HUT_FLOOR].copy()
    pygame.draw.rect(img, (90, 55, 30), (1, 4, 14, 10))
    pygame.draw.rect(img, (60, 35, 18), (1, 4, 14, 10), 1)
    pygame.draw.rect(img, (40, 25, 12), (2, 11, 3, 4))
    pygame.draw.rect(img, (40, 25, 12), (11, 11, 3, 4))
    return img


def make_mat():
    img = TILE_IMAGES[HUT_FLOOR].copy()
    pygame.draw.rect(img, (150, 40, 40), (2, 2, 12, 12))
    pygame.draw.rect(img, (110, 25, 25), (2, 2, 12, 12), 1)
    pygame.draw.line(img, (110, 25, 25), (2, 6), (14, 6))
    pygame.draw.line(img, (110, 25, 25), (2, 10), (14, 10))
    return img


TILE_IMAGES[DESK] = make_desk()
TILE_IMAGES[MAT] = make_mat()


# ---- Character / NPC sprites (16x16 pixel art) -----------------------------
def make_kyle():
    # Kyle: blue shirt, brown hair, simple stance
    p = {
        ".": None, "k": (40, 30, 20), "f": (235, 200, 170),
        "b": (50, 90, 200), "d": (30, 60, 150), "w": (255, 255, 255),
    }
    rows = [
        "....kkkkkkkk....",
        "...kkkkkkkkkk...",
        "...kffffffffk...",
        "..kfffwfwfffk...",
        "...ffffffffff...",
        "....ffffffff....",
        "...bbbbbbbbbb...",
        "..bbbbbbbbbbbb..",
        "..bbbbbbbbbbbb..",
        "..bbbddddddbb...",
        "..bb........bb..",
        "..bb........bb..",
        "..kk........kk..",
        "..kk........kk..",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_noah():
    # Noah: green hoodie, 18-year-old, slightly tired-looking
    p = {
        ".": None, "k": (60, 45, 30), "f": (225, 190, 160),
        "g": (50, 140, 80), "d": (30, 100, 55), "w": (255, 255, 255),
    }
    rows = [
        "....kkkkkkkk....",
        "...kkkkkkkkkk...",
        "...kffffffffk...",
        "..kfffwfwfffk...",
        "...ffffffffff...",
        "....ffffffff....",
        "...gggggggggg...",
        "..gggggggggggg..",
        "..gggggggggggg..",
        "..ggdddddddgg...",
        "..gg........gg..",
        "..gg........gg..",
        "..kk........kk..",
        "..kk........kk..",
        "................",
        "................",
    ]
    return make_surface(rows, p)


def make_merchant():
    # Merchant: purple cloak, hood up (mysterious black-market vibe)
    p = {
        ".": None, "h": (90, 40, 120), "s": (60, 25, 85),
        "f": (40, 30, 35), "g": (210, 175, 60),
    }
    rows = [
        "....hhhhhhhh....",
        "...hhhhhhhhhh...",
        "..hhhhffffhhhh..",
        "..hhhff..ffhhh..",
        "..hhhffffffhh...",
        "...hhhhhhhhh....",
        "...hhssssshh....",
        "..hhssssssshh...",
        "..hhssgsssshh...",
        "..hhsssssssh....",
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
        ".": None, "g": (95, 95, 100), "d": (55, 55, 60),
        "r": (210, 40, 40), "w": (235, 235, 235),
    }
    rows = [
        "...g......g.....",
        "..ggg....ggg....",
        "..gggggggggg....",
        ".ggrgggggrggg...",
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
    p = {".": None, "w": (255, 255, 255), "y": (240, 190, 40), "r": (210, 50, 40)}
    rows = [
        "................",
        "......wwww......",
        ".....wwwwww.....",
        ".....wwwwww.....",
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
    ]
    return make_surface(rows, p)


SPRITES = {
    "kyle": make_kyle(),
    "noah": make_noah(),
    "merchant": make_merchant(),
    "werewolf": make_werewolf(),
    "chicken": make_chicken(),
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
    mat inside that hide the entrance to the black market below."""
    w, h = 5, 4
    for y in range(hy - 1, hy + h + 1):
        for x in range(hx - 1, hx + w + 1):
            on_border = (
                x == hx - 1 or x == hx + w or y == hy - 1 or y == hy + h
            )
            world[y][x] = HUT_WALL if on_border else HUT_FLOOR

    desk_pos = (hx + w // 2, hy + h // 2)
    world[desk_pos[1]][desk_pos[0]] = DESK
    return desk_pos


def carve_market_room(world, mx, my):
    """A small hidden room (drawn far from the surface map visually, but for
    simplicity we carve it directly beneath the hut's coordinates on the
    same grid, accessed only once the trapdoor is open)."""
    w, h = 7, 6
    for y in range(my - 1, my + h + 1):
        for x in range(mx - 1, mx + w + 1):
            on_border = (
                x == mx - 1 or x == mx + w or y == my - 1 or y == my + h
            )
            world[y][x] = MARKET_WALL if on_border else MARKET_FLOOR


# ---------------------------------------------------------------------------
# Game state
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

    @property
    def tile(self):
        return int(self.x), int(self.y)


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, SPRITES["kyle"])
        self.speed = 0.18  # tiles per frame
        self.health = 100
        self.max_health = 100

    def try_move(self, dx, dy, world):
        nx, ny = self.x + dx, self.y + dy
        tx, ty = int(nx), int(ny)
        if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
            if world[ty][tx] not in SOLID_TILES:
                self.x, self.y = nx, ny


class Werewolf(Entity):
    STATE_WANDER = "wander"
    STATE_CHASE = "chase"

    def __init__(self, x, y, home_radius_tiles, center):
        super().__init__(x, y, SPRITES["werewolf"])
        self.health = 40
        self.speed = 0.07
        self.state = Werewolf.STATE_WANDER
        self.wander_dir = pygame.Vector2(random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
        self.wander_timer = random.randint(30, 90)
        self.detect_radius = 7  # tiles
        self.has_chicken = True
        self.center = center
        self.home_radius = home_radius_tiles

    def update(self, player):
        dist = ((self.x - player.x) ** 2 + (self.y - player.y) ** 2) ** 0.5
        self.state = Werewolf.STATE_CHASE if dist < self.detect_radius else Werewolf.STATE_WANDER

        if self.state == Werewolf.STATE_CHASE:
            dx, dy = player.x - self.x, player.y - self.y
            length = (dx ** 2 + dy ** 2) ** 0.5
            if length > 0:
                dx, dy = dx / length, dy / length
            self.x += dx * self.speed
            self.y += dy * self.speed
        else:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.wander_dir = pygame.Vector2(
                    random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                )
                self.wander_timer = random.randint(30, 90)
            self.x += self.wander_dir.x * self.speed
            self.y += self.wander_dir.y * self.speed

        # keep roughly on its home island
        cx, cy = self.center
        if ((self.x - cx) ** 2 + (self.y - cy) ** 2) ** 0.5 > self.home_radius:
            self.x += (cx - self.x) * 0.05
            self.y += (cy - self.y) * 0.05

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


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def draw_text(surface, text, pos, font=FONT, color=(255, 255, 255)):
    x, y = pos
    for line in text.split("\n"):
        surface.blit(font.render(line, True, color), (x, y))
        y += font.get_height() + 2


def draw_hud(surface, state: GameState, player: Player):
    pygame.draw.rect(surface, (15, 15, 20), (0, SCREEN_H, SCREEN_W, HUD_HEIGHT))
    draw_text(
        surface,
        f"Chicken: {state.chickens}  Materials: {state.materials}  "
        f"Gold: {state.money}  Sold: {state.chickens_sold}/{CHICKENS_TO_WIN}  "
        f"HP: {player.health}",
        (8, SCREEN_H + 6),
    )
    trust_text = "Noah trusts you" if state.noah_trust else "Noah is suspicious of you"
    trust_color = (90, 220, 110) if state.noah_trust else (230, 80, 80)
    draw_text(surface, trust_text, (8, SCREEN_H + 28), color=trust_color)


def show_message_box(surface, message):
    box = pygame.Rect(40, SCREEN_H - 130, SCREEN_W - 80, 110)
    pygame.draw.rect(surface, (10, 10, 15), box)
    pygame.draw.rect(surface, (255, 255, 255), box, 2)
    draw_text(surface, message, (box.x + 14, box.y + 14))
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


# ---------------------------------------------------------------------------
# Rendering: only draw tiles within the visibility radius (camera-based)
# ---------------------------------------------------------------------------
def render_world(world, player, npcs_visible):
    screen.fill((0, 0, 0))

    cam_tile_x = int(player.x) - VIEW_RADIUS_TILES
    cam_tile_y = int(player.y) - VIEW_RADIUS_TILES

    for screen_ty in range(VIEW_TILES_ACROSS):
        world_ty = cam_tile_y + screen_ty
        if not (0 <= world_ty < MAP_H):
            continue
        for screen_tx in range(VIEW_TILES_ACROSS):
            world_tx = cam_tile_x + screen_tx
            if not (0 <= world_tx < MAP_W):
                continue
            tile_id = world[world_ty][world_tx]
            img = TILE_IMAGES.get(tile_id, TILE_IMAGES[WATER])
            screen.blit(img, (screen_tx * TILE, screen_ty * TILE))

    # player is always drawn at the screen center
    px = (player.x - cam_tile_x) * TILE - TILE / 2
    py = (player.y - cam_tile_y) * TILE - TILE / 2

    # draw NPCs/werewolves relative to camera
    for entity in npcs_visible:
        ex = (entity.x - cam_tile_x) * TILE - TILE / 2
        ey = (entity.y - cam_tile_y) * TILE - TILE / 2
        if -TILE <= ex <= SCREEN_W and -TILE <= ey <= SCREEN_H:
            screen.blit(entity.sprite, (ex, ey))

    screen.blit(player.sprite, (px, py))
    return cam_tile_x, cam_tile_y


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

    # Track whether the trapdoor area has been "stepped into" to flag market state
    market_entry_tile = (market_x + 3, market_y + 1)

    running = True
    while running:
        clock.tick(FPS)

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
            dx = -player.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = player.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -player.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = player.speed

        if dx and dy:  # normalize diagonal movement
            dx *= 0.7071
            dy *= 0.7071

        # Crossing onto WATER is blocked unless Kyle has a glider, in which
        # case he "glides" across automatically.
        nx, ny = player.x + dx, player.y + dy
        tx, ty = int(nx), int(ny)
        if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
            target_tile = world[ty][tx]
            if target_tile == WATER and state.gliders <= 0:
                pass  # can't cross water without a glider
            elif target_tile in SOLID_TILES and target_tile != WATER:
                pass  # walls block movement
            else:
                player.x, player.y = nx, ny

        # ---------------- werewolves ----------------
        for wolf in werewolves:
            wolf.update(player)
            dist = ((player.x - wolf.x) ** 2 + (player.y - wolf.y) ** 2) ** 0.5
            if dist < 0.8:
                player.health -= 1

        if state.game_over:
            running = False

        # ---------------- render ----------------
        visible_npcs = [noah]
        if state.in_black_market:
            visible_npcs.append(merchant)
        visible_npcs.extend(werewolves)

        render_world(world, player, visible_npcs)
        draw_hud(screen, state, player)

        hint = "E: interact   G: give chicken to Noah   B: build glider   SPACE: attack"
        draw_text(screen, hint, (8, SCREEN_H + HUD_HEIGHT - 18), color=(210, 170, 40))

        pygame.display.flip()

    if state.won:
        show_win_screen(screen)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()