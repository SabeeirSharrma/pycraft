# pycraft.py
# Minimal PyCraft prototype: tile-based world + simple farming + mining
# Requires pygame: pip install pygame

import pygame, sys, random, json, os
from pygame import Rect
from collections import defaultdict

# --- Config ---
TILE = 32
W, H = 20, 15  # tiles visible
SCREEN_W, SCREEN_H = W * TILE, H * TILE
MAP_W, MAP_H = 60, 40  # world size in tiles
FPS = 60

# Colors
COLORS = {
    "sky": (135, 206, 235),
    "grass": (80, 180, 70),
    "dirt": (120, 85, 60),
    "stone": (100, 100, 100),
    "wood": (120, 70, 20),
    "tilled": (160, 110, 60),
    "seedling": (120, 200, 100),
    "crop": (40, 160, 40),
    "player": (255, 220, 125),
    "night_overlay": (0, 0, 50, 120)
}

# Items
ITEMS = ["dirt", "stone", "wood", "seed", "hoe"]  # basic inventory types

# --- World functions ---
def generate_world(w, h):
    """Basic terrain: top layers grass, then dirt, then stone; scattered trees"""
    world = [["air" for _ in range(h)] for _ in range(w)]
    surface = int(h * 0.4 + random.randint(-2, 2))
    for x in range(w):
        ground = surface + int(2 * random.random())
        for y in range(h):
            if y < ground:
                world[x][y] = "air"
            elif y == ground:
                world[x][y] = "grass"
            elif y < ground + 4:
                world[x][y] = "dirt"
            else:
                world[x][y] = "stone"
    # Add simple trees: 5-7 blocks wood trunk + leaves as wood (simplified)
    for _ in range(w // 8):
        tx = random.randint(3, w - 4)
        # find surface y
        for y in range(h):
            if world[tx][y] == "grass":
                ground_y = y
                break
        # trunk
        height = random.randint(3, 5)
        for t in range(1, height + 1):
            if ground_y - t >= 0:
                world[tx][ground_y - t] = "wood"
        # leaves: surround top
        top = ground_y - height
        for lx in range(tx - 2, tx + 3):
            for ly in range(top - 2, top + 1):
                if 0 <= lx < w and 0 <= ly < h:
                    if world[lx][ly] == "air":
                        world[lx][ly] = "wood"
    return world

# --- Game classes ---
class Crop:
    """Represents a planted crop with growth stages based on days."""
    def __init__(self, planted_day, grow_days=3):
        self.planted_day = planted_day
        self.grow_days = grow_days

    def stage(self, current_day):
        days = current_day - self.planted_day
        return max(0, min(self.grow_days, days))

    def is_mature(self, current_day):
        return (current_day - self.planted_day) >= self.grow_days

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("PyCraft (Prototype)")
        self.clock = pygame.time.Clock()
        # world: 2D array [x][y]
        self.world = generate_world(MAP_W, MAP_H)
        # plants dict keyed by (x,y) => Crop
        self.plants = {}
        # player start near center
        self.player_x = MAP_W // 2
        self.player_y = 0
        # position player on surface
        for y in range(MAP_H):
            if self.world[self.player_x][y] in ("grass", "dirt"):
                self.player_y = y - 1
                break
        # camera (top-left tile coords)
        self.cam_x = max(0, self.player_x - W // 2)
        self.cam_y = max(0, self.player_y - H // 2)
        # inventory simple counts
        self.inventory = defaultdict(int)
        self.inventory["seed"] = 5
        self.inventory["hoe"] = 1
        self.inventory["dirt"] = 10
        self.inventory["stone"] = 2
        self.inventory["wood"] = 3
        self.selected = 0  # inventory slot index
        # day-time
        self.current_day = 1
        self.time_of_day = 8.0  # 0-24 hours
        # action cooldown
        self.action_cooldown = 0
        self.font = pygame.font.SysFont("Arial", 14)

    # --- World helpers ---
    def in_world(self, x, y):
        return 0 <= x < MAP_W and 0 <= y < MAP_H

    def tile_at(self, x, y):
        if not self.in_world(x, y): return "stone"
        return self.world[x][y]

    def set_tile(self, x, y, tile):
        if self.in_world(x, y):
            self.world[x][y] = tile

    # --- Gameplay actions ---
    def mine(self, tx, ty):
        """Break the block and add item to inventory."""
        if not self.in_world(tx, ty): return
        tile = self.world[tx][ty]
        if tile in ("air", "seedling", "crop"):
            return
        # drop one of that tile as item (simplified)
        self.inventory[tile] += 1
        # replace with air
        self.world[tx][ty] = "air"

    def place(self, tx, ty, item):
        """Place an item (dirt/wood/stone) if tile is air."""
        if not self.in_world(tx, ty): return
        if self.world[tx][ty] != "air": return
        if self.inventory[item] <= 0: return
        self.world[tx][ty] = item
        self.inventory[item] -= 1

    def till(self, tx, ty):
        """Tills grass/dirt into tilled soil if player has hoe."""
        if self.inventory["hoe"] <= 0: return
        if not self.in_world(tx, ty): return
        if self.world[tx][ty] in ("grass", "dirt"):
            self.world[tx][ty] = "tilled"

    def plant_seed(self, tx, ty):
        """Plant seed on tilled tile."""
        if self.inventory["seed"] <= 0: return
        if not self.in_world(tx, ty): return
        if self.world[tx][ty] == "tilled" and (tx, ty) not in self.plants:
            self.plants[(tx, ty)] = Crop(self.current_day, grow_days=3)
            self.inventory["seed"] -= 1

    def harvest(self, tx, ty):
        key = (tx, ty)
        if key in self.plants:
            crop = self.plants[key]
            if crop.is_mature(self.current_day):
                # give some yield
                self.inventory["seed"] += 2
                self.inventory["dirt"] += 1
                del self.plants[key]
                # tilled remains tilled
            else:
                # immature: nothing
                pass

    # --- Save/Load ---
    def save(self, filename="pycraft_save.json"):
        data = {
            "world": self.world,
            "plants": {f"{x},{y}": {"planted_day": c.planted_day, "grow_days": c.grow_days}
                       for (x, y), c in self.plants.items()},
            "player": {"x": self.player_x, "y": self.player_y, "day": self.current_day, "time": self.time_of_day},
            "inventory": dict(self.inventory)
        }
        with open(filename, "w") as f:
            json.dump(data, f)
        print("Saved to", filename)

    def load(self, filename="pycraft_save.json"):
        if not os.path.exists(filename):
            print("No save file.")
            return
        with open(filename, "r") as f:
            data = json.load(f)
        self.world = data.get("world", self.world)
        self.plants = {}
        for k, v in data.get("plants", {}).items():
            x, y = map(int, k.split(","))
            self.plants[(x, y)] = Crop(v["planted_day"], v["grow_days"])
        p = data.get("player", {})
        self.player_x = p.get("x", self.player_x)
        self.player_y = p.get("y", self.player_y)
        self.current_day = p.get("day", self.current_day)
        self.time_of_day = p.get("time", self.time_of_day)
        inv = data.get("inventory", {})
        self.inventory = defaultdict(int, inv)
        print("Loaded", filename)

    # --- Input and update ---
    def try_action_at_player(self):
        # action targets tile in front of player (we'll use below/around player)
        tx = self.player_x
        ty = self.player_y + 1
        sel_item = self.get_selected_item()
        # If there is a plant and mature -> harvest
        if (tx, ty) in self.plants and self.plants[(tx, ty)].is_mature(self.current_day):
            self.harvest(tx, ty)
            return
        # If selected is seed -> plant
        if sel_item == "seed":
            if self.world[tx][ty] == "tilled":
                self.plant_seed(tx, ty)
                return
        # If selected is dirt/wood/stone -> place
        if sel_item in ("dirt", "wood", "stone"):
            # place above ground (tile at player bottom)
            self.place(tx, ty, sel_item)
            return
        # otherwise mine block just below player foot (or in front)
        # try mining tile under foot first
        under = (self.player_x, self.player_y + 1)
        if self.in_world(*under) and self.world[under[0]][under[1]] != "air":
            self.mine(*under)
            return
        # fallback: mine tile at player pos
        if self.in_world(tx, ty) and self.world[tx][ty] != "air":
            self.mine(tx, ty)

    def get_selected_item(self):
        inv_keys = list(ITEMS)
        if self.selected < len(inv_keys):
            return inv_keys[self.selected]
        return None

    def update(self, dt):
        # simple day progression
        self.time_of_day += dt * 0.01  # scale so day passes reasonably fast
        if self.time_of_day >= 24.0:
            self.time_of_day -= 24.0
            self.current_day += 1
            # crops grow automatically by day count (handled by Crop)
        # cooldown decrement
        if self.action_cooldown > 0:
            self.action_cooldown = max(0, self.action_cooldown - dt)

        # Camera follow
        self.cam_x = min(max(0, self.player_x - W // 2), MAP_W - W)
        self.cam_y = min(max(0, self.player_y - H // 2), MAP_H - H)

    # --- Rendering ---
    def draw_tile(self, surface, tx, ty, tile):
        x = (tx - self.cam_x) * TILE
        y = (ty - self.cam_y) * TILE
        r = Rect(x, y, TILE, TILE)
        if tile == "air":
            # draw sky or nothing
            pygame.draw.rect(surface, COLORS["sky"], r)
        elif tile == "grass":
            pygame.draw.rect(surface, COLORS["dirt"], r)
            pygame.draw.rect(surface, COLORS["grass"], Rect(x, y, TILE, TILE // 2))
        elif tile == "dirt":
            pygame.draw.rect(surface, COLORS["dirt"], r)
        elif tile == "stone":
            pygame.draw.rect(surface, COLORS["stone"], r)
        elif tile == "wood":
            pygame.draw.rect(surface, COLORS["wood"], r)
        elif tile == "tilled":
            pygame.draw.rect(surface, COLORS["tilled"], r)
        else:
            pygame.draw.rect(surface, (200, 0, 200), r)  # unknown

    def render(self):
        surf = self.screen
        # background sky
        surf.fill(COLORS["sky"])
        # draw visible tiles
        for tx in range(self.cam_x, self.cam_x + W):
            for ty in range(self.cam_y, self.cam_y + H):
                if not self.in_world(tx, ty):
                    continue
                tile = self.world[tx][ty]
                self.draw_tile(surf, tx, ty, tile)
        # draw plants
        for (px, py), crop in self.plants.items():
            if not (self.cam_x <= px < self.cam_x + W and self.cam_y <= py < self.cam_y + H):
                continue
            x = (px - self.cam_x) * TILE
            y = (py - self.cam_y) * TILE
            stage = crop.stage(self.current_day)
            # draw small rectangle indicating growth stage
            h = int((stage + 1) / (crop.grow_days + 1) * (TILE - 6))
            pygame.draw.rect(surf, COLORS["seedling"] if stage < crop.grow_days else COLORS["crop"],
                             Rect(x + 6, y + TILE - 6 - h, TILE - 12, h))
        # draw grid optionally (disabled for clarity)
        # draw player
        px = (self.player_x - self.cam_x) * TILE
        py = (self.player_y - self.cam_y) * TILE
        pygame.draw.rect(surf, COLORS["player"], Rect(px+4, py+4, TILE-8, TILE-8), border_radius=4)
        # draw UI: inventory
        self.draw_ui()
        # day/night overlay
        if self.time_of_day < 6 or self.time_of_day > 18:
            # simple opacity based on how far from day
            night_factor = 0.0
            if self.time_of_day < 6:
                night_factor = (6 - self.time_of_day) / 6.0
            else:
                night_factor = (self.time_of_day - 18) / 6.0
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            alpha = min(180, int(120 * night_factor))
            overlay.fill((0, 0, 40, alpha))
            surf.blit(overlay, (0,0))

        pygame.display.flip()

    def draw_ui(self):
        surf = self.screen
        # inventory bar bottom
        bar_h = 48
        pygame.draw.rect(surf, (30,30,30), Rect(0, SCREEN_H - bar_h, SCREEN_W, bar_h))
        # draw item slots
        for i, item in enumerate(ITEMS[:8]):
            x = 8 + i * (TILE + 8)
            y = SCREEN_H - bar_h + 8
            slot = Rect(x, y, TILE, TILE)
            pygame.draw.rect(surf, (70,70,70), slot, border_radius=4)
            if i == self.selected:
                pygame.draw.rect(surf, (255,215,0), slot, 3, border_radius=4)
            # draw a simple icon: colored square + first letter
            col = COLORS.get(item, (200,200,200))
            pygame.draw.rect(surf, col, Rect(x+6, y+6, TILE-12, TILE-12), border_radius=3)
            # count
            count = str(self.inventory.get(item, 0))
            txt = self.font.render(count, True, (255,255,255))
            surf.blit(txt, (x + TILE - txt.get_width() - 2, y + TILE - txt.get_height() - 2))
            # label
            lbl = self.font.render(item[0].upper(), True, (240,240,240))
            surf.blit(lbl, (x + 4, y + 4))
        # day/time text
        dt_text = f"Day {self.current_day}  {int(self.time_of_day)}:00"
        t = self.font.render(dt_text, True, (240,240,240))
        surf.blit(t, (SCREEN_W - t.get_width() - 8, SCREEN_H - bar_h + 14))

    # --- Main loop ---
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key in (pygame.K_1, pygame.K_KP1):
                        self.selected = 0
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.selected = 1
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        self.selected = 2
                    elif event.key in (pygame.K_4, pygame.K_KP4):
                        self.selected = 3
                    elif event.key == pygame.K_SPACE:
                        if self.action_cooldown <= 0:
                            self.try_action_at_player()
                            self.action_cooldown = 200
                    elif event.key == pygame.K_e:
                        # till the tile below player
                        self.till(self.player_x, self.player_y + 1)
                    elif event.key == pygame.K_s:
                        self.save()
                    elif event.key == pygame.K_l:
                        self.load()
            # continuous key handling for movement
            keys = pygame.key.get_pressed()
            dx = 0
            dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
            # move player with collision: cannot move into non-air.
            nx = self.player_x + dx
            ny = self.player_y + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                # treat tiles occupied if not air (player can stand on air but we keep it simple)
                if self.world[nx][ny] == "air":
                    self.player_x = nx
                    self.player_y = ny
                else:
                    # if trying to step down onto grass/dirt, allow standing on top (y is smaller)
                    if dy > 0 and self.world[nx][ny] in ("grass","dirt","tilled","stone","wood"):
                        # stand above it if possible
                        if ny - 1 >= 0 and self.world[nx][ny - 1] == "air":
                            self.player_x = nx
                            self.player_y = ny - 1

            self.update(dt)
            self.render()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Game().run()
