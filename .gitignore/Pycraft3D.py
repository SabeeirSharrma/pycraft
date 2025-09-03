from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController  # kept for reference but not used
import json, os, math
from dataclasses import dataclass

app = Ursina(borderless=False)

# ------------------------- Config -------------------------
window.title = 'PyCraft - Mini Minecraft in Python (Ursina)'
window.color = color.rgb(160, 200, 255)
window.exit_button.enabled = True
window.fps_counter.enabled = True
mouse_sensitivity = Vec2(40, 40)

CHUNK_SIZE = 24    # world extents in +x/-x, +z/-z (generated at start)
MAX_HEIGHT = 6     # max hill height above base
BASE_Y = 0         # base ground level

SAVE_FILE = 'world_save.json'

# ---------------------- Block Types -----------------------
@dataclass(frozen=True)
class BlockType:
    name: str
    tint: color.__class__
    hardness: float
    transparent: bool = False

BLOCKS = [
    BlockType('Grass', color.rgb(106, 170, 100), 1.0),
    BlockType('Dirt',  color.rgb(134, 96, 67),  1.0),
    BlockType('Stone', color.rgb(125, 125, 125), 1.5),
    BlockType('Wood',  color.rgb(100, 70, 50),  1.2),
    BlockType('Glass', color.rgba(200, 220, 240, 120), 0.2, True),
]

current_block_index = 0

# ----------------------- World Store ----------------------
world = {}

def key_for(e):
    return (int(e.x), int(e.y), int(e.z))

# ----------------------- Entities -------------------------
sky = Sky()
AmbientLight(color=color.rgba(255,255,255,160))
sun = DirectionalLight()
sun.look_at(Vec3(1, -2, 1))

# UI: hotbar
hotbar_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(0,0,0,120),
                   origin=(0,0), position=(0,-.45), scale=(.6,.09), enabled=True)
hotbar_slots = []
for i in range(5):
    slot = Button(parent=camera.ui, scale=(.1,.09), position=(-.25 + i*.125, -.45),
                  color=color.rgba(255,255,255,40), model='quad', text=str(i+1))
    hotbar_slots.append(slot)

hotbar_sel = Entity(parent=camera.ui, model='wireframe_quad', scale=(.102,.092),
                    position=hotbar_slots[0].position, color=color.azure)

info_text = Text(parent=camera.ui, text='PyCraft  •  WASD move, LMB break, RMB place  •  1-5 select  •  F5 save / F9 load',
                 origin=(0,0), position=(0,.47), scale=1, background=True)

hand = Entity(parent=camera.ui, model='quad', texture='white_cube', color=color.rgb(230,230,230),
              scale=(.1,.1), position=(.55,-.35), rotation_z=-20, enabled=True)

# ----------------------- Voxel ----------------------------
class Voxel(Button):
    def __init__(self, position=(0,0,0), block_index=0):
        super().__init__(
            parent=scene,
            position=position,
            model='cube',
            origin_y=.5,
            texture='white_cube',
            color=BLOCKS[block_index].tint,
            highlight_color=color.rgb(255, 255, 0),
            collider='box',
        )
        self.block_index = block_index
        world[key_for(self)] = self.block_index

    def input(self, key):
        global current_block_index
        if self.hovered:
            if key == 'left mouse down':
                k = key_for(self)
                if k in world:
                    del world[k]
                destroy(self)
                punch()
            if key == 'right mouse down':
                if mouse.normal is not None:
                    pos = self.position + mouse.normal
                    place_block(pos, current_block_index)
                    punch()

def punch():
    hand.animate_position((.55, -.37), duration=.05, curve=curve.linear)
    hand.animate_position((.55, -.35), duration=.07, delay=.05, curve=curve.linear)

# ----------------------- Helpers --------------------------
def place_block(position, block_index):
    if not isinstance(position, Vec3):
        position = Vec3(*position)
    pos = Vec3(round(position.x), round(position.y), round(position.z))

    k = (int(pos.x), int(pos.y), int(pos.z))
    if k[1] < -20:  # safety floor
        return
    if k not in world:
        v = Voxel(position=pos, block_index=block_index)
        v.collider = None if BLOCKS[block_index].transparent else 'box'
        if BLOCKS[block_index].transparent:
            v.color = BLOCKS[block_index].tint
            v.texture = 'white_cube'

def height_at(x, z):
    return BASE_Y + int((math.sin(x*0.25) + math.cos(z*0.3))*0.5*MAX_HEIGHT)

def generate_world(radius=CHUNK_SIZE):
    for x in range(-radius, radius):
        for z in range(-radius, radius):
            y = height_at(x, z)
            place_block((x, y, z), 0)
            for dy in range(1, 4):
                place_block((x, y-dy, z), 1 if dy < 3 else 2)

def serialize_world():
    data = [{'x': x, 'y': y, 'z': z, 't': t} for (x,y,z), t in world.items()]
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    print(f'[Saved] {len(data)} blocks -> {SAVE_FILE}')

def load_world():
    if not os.path.exists(SAVE_FILE):
        print('[Load] No save found.')
        return
    for e in scene.entities[:]:
        if isinstance(e, Voxel):
            destroy(e)
    world.clear()
    with open(SAVE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        place_block((item['x'], item['y'], item['z']), item['t'])
    print(f'[Loaded] {len(data)} blocks from {SAVE_FILE}')

# ----------------------- Player (custom WASD controller) ---------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

class SimplePlayer(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # physics & movement params
        self.speed = 5.0
        self.sprint_speed = 8.0
        self.jump_speed = 5.0
        self.gravity = 20.0
        self.y_velocity = 0.0
        self.grounded = False
        self.camera_height = 1.6
        # attach camera
        camera.parent = self
        camera.position = Vec3(0, self.camera_height, 0)
        camera.rotation = Vec3(0,0,0)
        mouse.locked = True
        self.mouse_locked = True
        self._prev_space = False

    def update(self):
        # mouse look (yaw on player, pitch on camera)
        self.rotation_y += mouse.delta.x * mouse_sensitivity.x
        camera.rotation_x -= mouse.delta.y * mouse_sensitivity.y
        camera.rotation_x = clamp(camera.rotation_x, -85, 85)

        # movement vector from WASD (primary) and arrow keys (optional)
        move_dir = Vec3(0,0,0)
        forward = Vec3(math.sin(math.radians(self.rotation_y)), 0, math.cos(math.radians(self.rotation_y)))
        right = Vec3(forward.z, 0, -forward.x)  # perpendicular on XZ plane

        if held_keys['w'] or held_keys['up arrow']:
            move_dir += forward
        if held_keys['s'] or held_keys['down arrow']:
            move_dir -= forward
        if held_keys['d'] or held_keys['right arrow']:
            move_dir += right
        if held_keys['a'] or held_keys['left arrow']:
            move_dir -= right

        if move_dir.length() > 0:
            move_dir = move_dir.normalized()

        speed = self.sprint_speed if held_keys['shift'] else self.speed
        self.position += move_dir * speed * time.dt

        # simple ground detection by raycast downward
        ray_origin = self.world_position + Vec3(0, 0.5, 0)
        hit = raycast(ray_origin, Vec3(0, -1, 0), distance=1.2, ignore=(self,))
        if hit.hit and isinstance(hit.entity, Voxel):
            # if falling, snap to surface and zero velocity
            if self.y_velocity <= 0:
                self.y = hit.world_point.y + 0.01  # small offset so we're above the block
                self.y_velocity = 0
                self.grounded = True
        else:
            self.grounded = False

        # jump (space) - only when grounded
        space_pressed = held_keys['space']
        if space_pressed and not self._prev_space and self.grounded:
            self.y_velocity = self.jump_speed
            self.grounded = False
        self._prev_space = space_pressed

        # apply gravity
        self.y_velocity -= self.gravity * time.dt
        self.position += Vec3(0, self.y_velocity * time.dt, 0)

        # safety: reset if falling too far
        if self.y < -50:
            self.x = 0
            self.z = 0
            self.y = height_at(0, 0) + 5
            self.y_velocity = 0

player = SimplePlayer(position=Vec3(0, height_at(0,0)+2, 0), collider=None)

def input(key):
    global current_block_index
    # hotbar 1..5
    if key in ['1','2','3','4','5']:
        idx = int(key)-1
        current_block_index = max(0, min(len(BLOCKS)-1, idx))
        hotbar_sel.position = hotbar_slots[current_block_index].position

    # toggle hotbar
    if key == 'e':
        hotbar_bg.enabled = not hotbar_bg.enabled
        for s in hotbar_slots: s.enabled = hotbar_bg.enabled
        hotbar_sel.enabled = hotbar_bg.enabled

    # save / load
    if key == 'f5':
        serialize_world()
    if key == 'f9':
        load_world()

    # toggle mouse lock (Escape to unlock)
    if key == 'escape':
        mouse.locked = not mouse.locked
        player.mouse_locked = mouse.locked
        print('Mouse locked:' , mouse.locked)

# ------------------------ Start ---------------------------
generate_world(radius=CHUNK_SIZE)

def plant_tree(x, z):
    y = height_at(x, z) + 1
    for i in range(4):
        place_block((x, y+i, z), 3)
    for dx in range(-2,3):
        for dy in range(2,5):
            for dz in range(-2,3):
                if abs(dx)+abs(dy-3)+abs(dz) < 5:
                    place_block((x+dx, y+dy, z+dz), 4)

for tx in range(-CHUNK_SIZE+4, CHUNK_SIZE-4, 8):
    for tz in range(-CHUNK_SIZE+4, CHUNK_SIZE-4, 12):
        if (tx*13 + tz*7) % 5 == 0:
            plant_tree(tx, tz)

app.run()
