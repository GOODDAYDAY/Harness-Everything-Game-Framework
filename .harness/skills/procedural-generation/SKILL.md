---
name: procedural-generation
description: Use when implementing procedural generation — noise-based terrain, BSP dungeons, cellular automata caves, wave function collapse, and seeded randomness in Godot 4.3+
---

# Procedural Generation in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **2d-essentials** for TileMapLayer usage, **3d-essentials** for 3D terrain meshes, **math-essentials** for vectors and transforms, **godot-optimization** for chunk loading and performance.

---

## 1. Seeded Randomness

Always use seeds for reproducible generation. This enables shareable seeds, replay, and deterministic testing.

### GDScript

```gdscript
# RandomNumberGenerator — per-instance, seedable
var rng := RandomNumberGenerator.new()

func generate_level(level_seed: int) -> void:
    rng.seed = level_seed

    var width: int = rng.randi_range(20, 40)
    var height: int = rng.randi_range(15, 30)
    var enemy_count: int = rng.randi_range(3, 8)
    var treasure_chance: float = rng.randf_range(0.05, 0.15)

# AVOID: Global randf()/randi() — not reproducible across calls
# USE: rng.randf(), rng.randi(), rng.randf_range(), rng.randi_range()
```

### C#

```csharp
private RandomNumberGenerator _rng = new();

public void GenerateLevel(ulong levelSeed)
{
    _rng.Seed = levelSeed;

    int width = _rng.RandiRange(20, 40);
    int height = _rng.RandiRange(15, 30);
    int enemyCount = _rng.RandiRange(3, 8);
    float treasureChance = _rng.RandfRange(0.05f, 0.15f);
}
```

> **Tip:** Generate a seed from a string for shareable level codes: `var seed: int = "MyLevel".hash()`

---

## 2. Noise-Based Generation (FastNoiseLite)

Godot's built-in `FastNoiseLite` resource provides Simplex, Perlin, Cellular, and Value noise.

### Basic Noise Map

```gdscript
var noise := FastNoiseLite.new()

func setup_noise(gen_seed: int) -> void:
    noise.seed = gen_seed
    noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
    noise.frequency = 0.02           # lower = larger features
    noise.fractal_type = FastNoiseLite.FRACTAL_FBM
    noise.fractal_octaves = 4        # detail layers
    noise.fractal_lacunarity = 2.0   # frequency multiplier per octave
    noise.fractal_gain = 0.5         # amplitude multiplier per octave

func get_height(x: int, y: int) -> float:
    # Returns -1.0 to 1.0
    return noise.get_noise_2d(float(x), float(y))
```

```csharp
private FastNoiseLite _noise = new();

public void SetupNoise(int genSeed)
{
    _noise.Seed = genSeed;
    _noise.NoiseType = FastNoiseLite.NoiseTypeEnum.SimplexSmooth;
    _noise.Frequency = 0.02f;
    _noise.FractalType = FastNoiseLite.FractalTypeEnum.Fbm;
    _noise.FractalOctaves = 4;
    _noise.FractalLacunarity = 2.0f;
    _noise.FractalGain = 0.5f;
}

public float GetHeight(int x, int y) => _noise.GetNoise2D(x, y);
```

### Noise Type Reference

| Type | Character | Use For |
|------|-----------|---------|
| `TYPE_SIMPLEX_SMOOTH` | Smooth, organic | Terrain height, clouds, temperature |
| `TYPE_PERLIN` | Classic smooth | Similar to Simplex, slightly different artifacts |
| `TYPE_CELLULAR` | Voronoi cells | Cave systems, biome boundaries, crystal patterns |
| `TYPE_VALUE` | Blocky, aliased | Retro terrain, pixel-art maps |
| `TYPE_VALUE_CUBIC` | Smoothed blocky | Smoother value noise |

### 2D Terrain with TileMapLayer

```gdscript
extends Node2D

@onready var tile_map: TileMapLayer = $TileMapLayer

var noise := FastNoiseLite.new()
var width: int = 80
var height: int = 60

func _ready() -> void:
    noise.seed = 42
    noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
    noise.frequency = 0.05
    generate_map()

func generate_map() -> void:
    for x in width:
        for y in height:
            var value: float = noise.get_noise_2d(float(x), float(y))
            var tile_coords: Vector2i = _noise_to_tile(value)
            tile_map.set_cell(Vector2i(x, y), 0, tile_coords)  # source_id=0

func _noise_to_tile(value: float) -> Vector2i:
    # Map noise value (-1 to 1) to tile atlas coordinates
    if value < -0.3:
        return Vector2i(0, 0)   # deep water
    elif value < -0.1:
        return Vector2i(1, 0)   # shallow water
    elif value < 0.2:
        return Vector2i(2, 0)   # grass
    elif value < 0.5:
        return Vector2i(3, 0)   # forest
    else:
        return Vector2i(4, 0)   # mountain
```

```csharp
public partial class TerrainGenerator : Node2D
{
    private TileMapLayer _tileMap;
    private FastNoiseLite _noise = new();
    private int _width = 80, _height = 60;

    public override void _Ready()
    {
        _tileMap = GetNode<TileMapLayer>("TileMapLayer");
        _noise.Seed = 42;
        _noise.NoiseType = FastNoiseLite.NoiseTypeEnum.SimplexSmooth;
        _noise.Frequency = 0.05f;
        GenerateMap();
    }

    private void GenerateMap()
    {
        for (int x = 0; x < _width; x++)
            for (int y = 0; y < _height; y++)
            {
                float value = _noise.GetNoise2D(x, y);
                Vector2I tileCoords = NoiseToTile(value);
                _tileMap.SetCell(new Vector2I(x, y), 0, tileCoords);
            }
    }

    private Vector2I NoiseToTile(float value) => value switch
    {
        < -0.3f => new(0, 0),
        < -0.1f => new(1, 0),
        < 0.2f  => new(2, 0),
        < 0.5f  => new(3, 0),
        _       => new(4, 0),
    };
}
```

---

## 3. BSP Dungeon Generation

Binary Space Partitioning recursively splits a rectangle into rooms, then connects them with corridors. Produces classic roguelike dungeon layouts.

### GDScript

```gdscript
class_name BSPDungeon
extends RefCounted

var rng := RandomNumberGenerator.new()
var min_room_size: int = 5
var rooms: Array[Rect2i] = []

func generate(bounds: Rect2i, gen_seed: int) -> Array[Rect2i]:
    rng.seed = gen_seed
    rooms.clear()
    _split(bounds)
    return rooms

func _split(area: Rect2i) -> void:
    # Stop splitting if area is small enough to be a room
    if area.size.x <= min_room_size * 2 and area.size.y <= min_room_size * 2:
        # Shrink to create room with margins
        var room := Rect2i(
            area.position + Vector2i(1, 1),
            area.size - Vector2i(2, 2)
        )
        if room.size.x >= min_room_size and room.size.y >= min_room_size:
            rooms.append(room)
        return

    # Choose split direction based on aspect ratio
    var split_horizontal: bool
    if area.size.x > area.size.y * 1.25:
        split_horizontal = false  # split vertically (wide room)
    elif area.size.y > area.size.x * 1.25:
        split_horizontal = true   # split horizontally (tall room)
    else:
        split_horizontal = rng.randi() % 2 == 0

    if split_horizontal:
        var split_y: int = rng.randi_range(
            area.position.y + min_room_size,
            area.end.y - min_room_size
        )
        _split(Rect2i(area.position, Vector2i(area.size.x, split_y - area.position.y)))
        _split(Rect2i(Vector2i(area.position.x, split_y), Vector2i(area.size.x, area.end.y - split_y)))
    else:
        var split_x: int = rng.randi_range(
            area.position.x + min_room_size,
            area.end.x - min_room_size
        )
        _split(Rect2i(area.position, Vector2i(split_x - area.position.x, area.size.y)))
        _split(Rect2i(Vector2i(split_x, area.position.y), Vector2i(area.end.x - split_x, area.size.y)))
```

### Connecting Rooms with Corridors

```gdscript
func connect_rooms(tile_map: TileMapLayer, floor_tile: Vector2i) -> void:
    for i in range(rooms.size() - 1):
        var center_a: Vector2i = rooms[i].position + rooms[i].size / 2
        var center_b: Vector2i = rooms[i + 1].position + rooms[i + 1].size / 2

        # L-shaped corridor: horizontal then vertical
        if rng.randi() % 2 == 0:
            _carve_horizontal(tile_map, center_a.x, center_b.x, center_a.y, floor_tile)
            _carve_vertical(tile_map, center_a.y, center_b.y, center_b.x, floor_tile)
        else:
            _carve_vertical(tile_map, center_a.y, center_b.y, center_a.x, floor_tile)
            _carve_horizontal(tile_map, center_a.x, center_b.x, center_b.y, floor_tile)

func _carve_horizontal(tile_map: TileMapLayer, x1: int, x2: int, y: int, tile: Vector2i) -> void:
    for x in range(mini(x1, x2), maxi(x1, x2) + 1):
        tile_map.set_cell(Vector2i(x, y), 0, tile)

func _carve_vertical(tile_map: TileMapLayer, y1: int, y2: int, x: int, tile: Vector2i) -> void:
    for y in range(mini(y1, y2), maxi(y1, y2) + 1):
        tile_map.set_cell(Vector2i(x, y), 0, tile)
```

### C#

```csharp
public partial class BSPDungeon : RefCounted
{
    private RandomNumberGenerator _rng = new();
    private int _minRoomSize = 5;
    public Godot.Collections.Array<Rect2I> Rooms { get; } = new();

    public Godot.Collections.Array<Rect2I> Generate(Rect2I bounds, ulong genSeed)
    {
        _rng.Seed = genSeed;
        Rooms.Clear();
        Split(bounds);
        return Rooms;
    }

    private void Split(Rect2I area)
    {
        if (area.Size.X <= _minRoomSize * 2 && area.Size.Y <= _minRoomSize * 2)
        {
            var room = new Rect2I(
                area.Position + new Vector2I(1, 1),
                area.Size - new Vector2I(2, 2)
            );
            if (room.Size.X >= _minRoomSize && room.Size.Y >= _minRoomSize)
                Rooms.Add(room);
            return;
        }

        bool splitHorizontal;
        if (area.Size.X > area.Size.Y * 1.25f)
            splitHorizontal = false;
        else if (area.Size.Y > area.Size.X * 1.25f)
            splitHorizontal = true;
        else
            splitHorizontal = _rng.Randi() % 2 == 0;

        if (splitHorizontal)
        {
            int splitY = _rng.RandiRange(
                area.Position.Y + _minRoomSize,
                area.End.Y - _minRoomSize
            );
            Split(new Rect2I(area.Position, new Vector2I(area.Size.X, splitY - area.Position.Y)));
            Split(new Rect2I(new Vector2I(area.Position.X, splitY), new Vector2I(area.Size.X, area.End.Y - splitY)));
        }
        else
        {
            int splitX = _rng.RandiRange(
                area.Position.X + _minRoomSize,
                area.End.X - _minRoomSize
            );
            Split(new Rect2I(area.Position, new Vector2I(splitX - area.Position.X, area.Size.Y)));
            Split(new Rect2I(new Vector2I(splitX, area.Position.Y), new Vector2I(area.End.X - splitX, area.Size.Y)));
        }
    }

    public void ConnectRooms(TileMapLayer tileMap, Vector2I floorTile)
    {
        for (int i = 0; i < Rooms.Count - 1; i++)
        {
            Vector2I centerA = Rooms[i].Position + Rooms[i].Size / 2;
            Vector2I centerB = Rooms[i + 1].Position + Rooms[i + 1].Size / 2;

            if (_rng.Randi() % 2 == 0)
            {
                CarveHorizontal(tileMap, centerA.X, centerB.X, centerA.Y, floorTile);
                CarveVertical(tileMap, centerA.Y, centerB.Y, centerB.X, floorTile);
            }
            else
            {
                CarveVertical(tileMap, centerA.Y, centerB.Y, centerA.X, floorTile);
                CarveHorizontal(tileMap, centerA.X, centerB.X, centerB.Y, floorTile);
            }
        }
    }

    private static void CarveHorizontal(TileMapLayer tileMap, int x1, int x2, int y, Vector2I tile)
    {
        for (int x = Mathf.Min(x1, x2); x <= Mathf.Max(x1, x2); x++)
            tileMap.SetCell(new Vector2I(x, y), 0, tile);
    }

    private static void CarveVertical(TileMapLayer tileMap, int y1, int y2, int x, Vector2I tile)
    {
        for (int y = Mathf.Min(y1, y2); y <= Mathf.Max(y1, y2); y++)
            tileMap.SetCell(new Vector2I(x, y), 0, tile);
    }
}
```

---

## 4. Cellular Automata (Cave Generation)

Simulates natural-looking caves by iterating a simple rule: a cell becomes wall if most of its neighbors are walls.

### GDScript

```gdscript
class_name CaveGenerator
extends RefCounted

var rng := RandomNumberGenerator.new()

func generate(width: int, height: int, gen_seed: int, fill_chance: float = 0.45, iterations: int = 5) -> Array[Array]:
    rng.seed = gen_seed

    # Step 1: Random fill
    var grid: Array[Array] = []
    for y in height:
        var row: Array[bool] = []
        for x in width:
            # true = wall, false = floor
            var is_edge: bool = x == 0 or y == 0 or x == width - 1 or y == height - 1
            row.append(is_edge or rng.randf() < fill_chance)
        grid.append(row)

    # Step 2: Smooth with cellular automata rules
    for _i in iterations:
        grid = _smooth(grid, width, height)

    return grid

func _smooth(grid: Array[Array], width: int, height: int) -> Array[Array]:
    var new_grid: Array[Array] = []
    for y in height:
        var row: Array[bool] = []
        for x in width:
            var wall_count: int = _count_neighbors(grid, x, y, width, height)
            # Rule: become wall if 5+ of 9 cells (self + 8 neighbors) are walls
            row.append(wall_count >= 5)
        new_grid.append(row)
    return new_grid

func _count_neighbors(grid: Array[Array], cx: int, cy: int, width: int, height: int) -> int:
    var count: int = 0
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            var nx: int = cx + dx
            var ny: int = cy + dy
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                count += 1  # out of bounds counts as wall
            elif grid[ny][nx]:
                count += 1
    return count
```

### Usage with TileMapLayer

```gdscript
func apply_cave_to_tilemap(tile_map: TileMapLayer, grid: Array[Array]) -> void:
    var wall_tile := Vector2i(0, 0)
    var floor_tile := Vector2i(1, 0)

    for y in grid.size():
        for x in grid[y].size():
            var tile := wall_tile if grid[y][x] else floor_tile
            tile_map.set_cell(Vector2i(x, y), 0, tile)
```

### C#

```csharp
public partial class CaveGenerator : RefCounted
{
    private RandomNumberGenerator _rng = new();

    public bool[][] Generate(int width, int height, ulong genSeed, float fillChance = 0.45f, int iterations = 5)
    {
        _rng.Seed = genSeed;

        // Step 1: Random fill
        bool[][] grid = new bool[height][];
        for (int y = 0; y < height; y++)
        {
            grid[y] = new bool[width];
            for (int x = 0; x < width; x++)
            {
                bool isEdge = x == 0 || y == 0 || x == width - 1 || y == height - 1;
                grid[y][x] = isEdge || _rng.Randf() < fillChance;
            }
        }

        // Step 2: Smooth with cellular automata rules
        for (int i = 0; i < iterations; i++)
            grid = Smooth(grid, width, height);

        return grid;
    }

    private static bool[][] Smooth(bool[][] grid, int width, int height)
    {
        bool[][] newGrid = new bool[height][];
        for (int y = 0; y < height; y++)
        {
            newGrid[y] = new bool[width];
            for (int x = 0; x < width; x++)
            {
                int wallCount = CountNeighbors(grid, x, y, width, height);
                // Rule: become wall if 5+ of 9 cells (self + 8 neighbors) are walls
                newGrid[y][x] = wallCount >= 5;
            }
        }
        return newGrid;
    }

    private static int CountNeighbors(bool[][] grid, int cx, int cy, int width, int height)
    {
        int count = 0;
        for (int dy = -1; dy <= 1; dy++)
            for (int dx = -1; dx <= 1; dx++)
            {
                int nx = cx + dx, ny = cy + dy;
                if (nx < 0 || ny < 0 || nx >= width || ny >= height)
                    count++;  // out of bounds counts as wall
                else if (grid[ny][nx])
                    count++;
            }
        return count;
    }
}

public static void ApplyCaveToTilemap(TileMapLayer tileMap, bool[][] grid)
{
    var wallTile = new Vector2I(0, 0);
    var floorTile = new Vector2I(1, 0);

    for (int y = 0; y < grid.Length; y++)
        for (int x = 0; x < grid[y].Length; x++)
            tileMap.SetCell(new Vector2I(x, y), 0, grid[y][x] ? wallTile : floorTile);
}
```

---

## 5. Wave Function Collapse (WFC) — Concept

WFC generates patterns by collapsing tile possibilities based on adjacency constraints. It produces visually coherent results from a small set of rules.

### Core Algorithm (Simplified)

```gdscript
class_name SimpleWFC
extends RefCounted

# Each cell holds a set of possible tile indices
var grid: Array[Array] = []   # grid[y][x] = Array[int] (possible tiles)
var rules: Dictionary = {}     # rules[tile_id] = {"up": [...], "down": [...], "left": [...], "right": [...]}
var rng := RandomNumberGenerator.new()

func setup(width: int, height: int, tile_count: int, gen_seed: int) -> void:
    rng.seed = gen_seed
    grid.clear()
    for y in height:
        var row: Array[Array] = []
        for x in width:
            var possibilities: Array[int] = []
            for t in tile_count:
                possibilities.append(t)
            row.append(possibilities)
        grid.append(row)

func collapse() -> bool:
    while true:
        # Find cell with fewest possibilities (lowest entropy)
        var min_cell := Vector2i(-1, -1)
        var min_count := 999
        for y in grid.size():
            for x in grid[y].size():
                var count: int = grid[y][x].size()
                if count > 1 and count < min_count:
                    min_count = count
                    min_cell = Vector2i(x, y)

        if min_cell == Vector2i(-1, -1):
            return true  # all collapsed — success

        # Collapse: pick a random possibility
        var cell: Array[int] = grid[min_cell.y][min_cell.x]
        if cell.is_empty():
            return false  # contradiction — no valid tiles
        var chosen: int = cell[rng.randi() % cell.size()]
        grid[min_cell.y][min_cell.x] = [chosen]

        # Propagate constraints to neighbors
        _propagate(min_cell)

    return true

func _propagate(pos: Vector2i) -> void:
    var stack: Array[Vector2i] = [pos]
    while not stack.is_empty():
        var current: Vector2i = stack.pop_back()
        var current_tiles: Array[int] = grid[current.y][current.x]

        for dir in [Vector2i(0, -1), Vector2i(0, 1), Vector2i(-1, 0), Vector2i(1, 0)]:
            var neighbor: Vector2i = current + dir
            if neighbor.x < 0 or neighbor.y < 0 or neighbor.y >= grid.size() or neighbor.x >= grid[0].size():
                continue

            var dir_name: String = _dir_to_name(dir)
            var allowed: Array[int] = []
            for tile in current_tiles:
                if rules.has(tile) and rules[tile].has(dir_name):
                    for allowed_tile in rules[tile][dir_name]:
                        if allowed_tile not in allowed:
                            allowed.append(allowed_tile)

            var neighbor_tiles: Array[int] = grid[neighbor.y][neighbor.x]
            var new_tiles: Array[int] = neighbor_tiles.filter(func(t: int) -> bool: return t in allowed)

            if new_tiles.size() < neighbor_tiles.size():
                grid[neighbor.y][neighbor.x] = new_tiles
                stack.append(neighbor)

func _dir_to_name(dir: Vector2i) -> String:
    if dir == Vector2i(0, -1): return "up"
    if dir == Vector2i(0, 1):  return "down"
    if dir == Vector2i(-1, 0): return "left"
    return "right"
```

### C#

```csharp
public partial class SimpleWFC : RefCounted
{
    // grid[y][x] = list of possible tile indices
    private List<int>[][] _grid = [];
    // rules[tileId]["up"|"down"|"left"|"right"] = list of allowed neighbour tile ids
    private Godot.Collections.Dictionary<int, Godot.Collections.Dictionary<string, Godot.Collections.Array<int>>> _rules = new();
    private RandomNumberGenerator _rng = new();

    public void Setup(int width, int height, int tileCount, ulong genSeed)
    {
        _rng.Seed = genSeed;
        _grid = new List<int>[height][];
        for (int y = 0; y < height; y++)
        {
            _grid[y] = new List<int>[width];
            for (int x = 0; x < width; x++)
            {
                _grid[y][x] = new List<int>();
                for (int t = 0; t < tileCount; t++)
                    _grid[y][x].Add(t);
            }
        }
    }

    public bool Collapse()
    {
        while (true)
        {
            // Find cell with fewest possibilities (lowest entropy)
            var minCell = new Vector2I(-1, -1);
            int minCount = 999;
            for (int y = 0; y < _grid.Length; y++)
                for (int x = 0; x < _grid[y].Length; x++)
                {
                    int count = _grid[y][x].Count;
                    if (count > 1 && count < minCount)
                    {
                        minCount = count;
                        minCell = new Vector2I(x, y);
                    }
                }

            if (minCell == new Vector2I(-1, -1))
                return true;  // all collapsed — success

            // Collapse: pick a random possibility
            var cell = _grid[minCell.Y][minCell.X];
            if (cell.Count == 0)
                return false;  // contradiction — no valid tiles
            int chosen = cell[(int)(_rng.Randi() % (uint)cell.Count)];
            _grid[minCell.Y][minCell.X] = [chosen];

            // Propagate constraints to neighbors
            Propagate(minCell);
        }
    }

    private void Propagate(Vector2I pos)
    {
        var stack = new Stack<Vector2I>();
        stack.Push(pos);
        while (stack.Count > 0)
        {
            var current = stack.Pop();
            var currentTiles = _grid[current.Y][current.X];

            foreach (var dir in new[] { new Vector2I(0, -1), new Vector2I(0, 1), new Vector2I(-1, 0), new Vector2I(1, 0) })
            {
                var neighbor = current + dir;
                if (neighbor.X < 0 || neighbor.Y < 0 || neighbor.Y >= _grid.Length || neighbor.X >= _grid[0].Length)
                    continue;

                string dirName = DirToName(dir);
                var allowed = new HashSet<int>();
                foreach (int tile in currentTiles)
                    if (_rules.TryGetValue(tile, out var tileRules) && tileRules.TryGetValue(dirName, out var allowedTiles))
                        foreach (int allowedTile in allowedTiles)
                            allowed.Add(allowedTile);

                var neighborTiles = _grid[neighbor.Y][neighbor.X];
                var newTiles = neighborTiles.Where(t => allowed.Contains(t)).ToList();

                if (newTiles.Count < neighborTiles.Count)
                {
                    _grid[neighbor.Y][neighbor.X] = newTiles;
                    stack.Push(neighbor);
                }
            }
        }
    }

    private static string DirToName(Vector2I dir)
    {
        if (dir == new Vector2I(0, -1)) return "up";
        if (dir == new Vector2I(0, 1))  return "down";
        if (dir == new Vector2I(-1, 0)) return "left";
        return "right";
    }
}
```

> **For production WFC**, consider the community addon [godot-wfc](https://github.com/AlexeyBond/godot-wfc) which provides editor integration, TileMap support, and 3D grid WFC.

---

## 6. Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Same level every time | Not seeding the RNG | Set `rng.seed` before generation |
| Different results on different platforms | Using global `randf()` / `randi()` | Use a dedicated `RandomNumberGenerator` instance |
| Noise looks blocky | Frequency too high | Lower `frequency` (try 0.01–0.05) |
| Caves are all wall or all floor | `fill_chance` too extreme or too few iterations | Use fill_chance 0.40–0.50 and 4–6 iterations |
| BSP rooms overlap | Split position too close to edge | Ensure `min_room_size` buffer in split calculation |
| WFC contradiction (no valid tile) | Adjacency rules too restrictive | Add more allowed neighbors or implement backtracking |
| Generation takes too long | Processing entire map in one frame | Use `await get_tree().process_frame` to spread across frames, or use a thread |

---

## 7. Implementation Checklist

- [ ] All generation uses a seedable `RandomNumberGenerator`, never global `randf()`/`randi()`
- [ ] Seeds are stored with save data so levels can be reproduced
- [ ] `FastNoiseLite` frequency and octaves are tuned for the game's tile/world scale
- [ ] Large generation is spread across frames or run on a thread to avoid freezing
- [ ] Generated TileMapLayer content uses terrain autotiling when possible (not hardcoded tile coords)
- [ ] BSP dungeons verify all rooms are connected before finalizing
- [ ] Cave generation runs a flood-fill to ensure reachability between key points
- [ ] Player spawn point is validated to be on a floor tile, not inside a wall
