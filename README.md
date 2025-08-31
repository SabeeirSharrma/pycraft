# pycraft (mini Minecraft-like in Python)

## Requirements
- Python 3.9+
- `pip install ursina`

## Run
```bash
python blockcraft.py
```

## Controls
- **WASD** move, **Mouse** look
- **Space** jump, **Shift** sprint
- **Left click** break block
- **Right click** place block (uses selected block from hotbar)
- **1–5** switch block type (Grass, Dirt, Stone, Wood, Glass)
- **E** toggle hotbar visibility
- **F5** save world to `world_save.json`
- **F9** load world
- **Esc** unlock cursor / quit menu

## Notes
- Terrain is generated dependency-free using simple sine/cosine hills.
- World saving stores every placed/removed block as JSON; for big worlds this can get large.
- Performance tips: reduce `CHUNK_SIZE`, `MAX_HEIGHT`, or tree density to speed things up.
- Want textures? Replace the default `'white_cube'` with your own PNG textures.
