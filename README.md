# PyCraft 🧱

A simple **Minecraft-like sandbox game** written in pure **Python + Pygame**.  
PyCraft is a lightweight 2D side-scrolling voxel world where you can explore, jump, mine, place blocks, and save your world.  

![screenshot](https://via.placeholder.com/800x400.png?text=PyCraft+Screenshot)

---

## ✨ Features
- Procedurally generated infinite 2D terrain using Perlin-like noise
- Chunked world (loads/unloads dynamically as you move)
- Basic blocks: Grass, Dirt, Stone, Wood, Leaves
- Place and break blocks with the mouse
- Player movement with gravity, jumping, and collision
- Simple inventory (1–5 to switch block type)
- Save & load world to JSON (`S` and `L`)
- Day/night cycle with lighting and sky gradients
- Trees with trunks and leaves generated randomly

---

## 🎮 Controls

| Key / Mouse | Action |
|-------------|--------|
| **A / Left Arrow** | Move left |
| **D / Right Arrow** | Move right |
| **W / Space** | Jump |
| **Mouse Left** | Break block |
| **Mouse Right** | Place selected block |
| **1–5** | Select block type |
| **S** | Save world |
| **L** | Load world |
| **Esc / Q** | Quit game |

---

## 🚀 Installation & Running

### 1. Install Python
Make sure you have **Python 3.8+** installed.  
Check version:
```bash
python --version
