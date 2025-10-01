#!/usr/bin/env python3
"""
pathfinder.py
Shortest-path on a PNG map using A*.
Usage:
  python pathfinder.py path/to/map.png [start_x,start_y] [goal_x,goal_y] [--use-cpp]

If --use-cpp is passed, the compiled pybind11 module `pathfinder_cpp` is used.
Otherwise, the original pure-Python A* implementation runs.
"""
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import heapq
import math
import time
import numpy as np

# -------------------------
# Configuration: edit this
# -------------------------
# Map color -> movement cost.
# Use RGB triples (0-255). 'inf' means impassable.
# Lower cost = faster / preferred route.
# Example mapping: white = road (cost 1), light gray = grass (1.5),
# green = forest (2.5), blue = water (impassable), black = obstacle
COLOR_COST_MAP = {
    (29,106,43): math.inf, 
    (29,29,27): math.inf,  
    (251,193,69): 1,       
    (146,145,145): math.inf, 
    (217,217,217): 1,      
    (190,182,0): math.inf, 
    (248,227,205): 1,
    (239,199,155): 1,
    (215,150,194): math.inf,
    (255,255,255): 1,
}
# How to treat pixels not exactly matching keys above:
# - If a pixel doesn't exactly match a color in the map, we'll find the nearest mapped color using Euclidean distance in RGB.
COLOR_MATCH_THRESHOLD = None # None => always map to nearest; set to a number 0..441 to require closeness.
# Use 8-neighbors (including diagonals)
DIAGONAL_MOVEMENT = True
# Path smoothing: set to True to run a simple line-of-sight simplifier (Ramer-Douglas-Peucker would be more advanced)
SIMPLIFY_PATH = True
SIMPLIFY_EPSILON = 1 # larger = more simplification

# -------------------------
# Optional C++ backend
# -------------------------
_HAS_CPP = False
try:
    import pathfinder_cpp  # pybind11 module you compiled from pathfinder.cpp
    _HAS_CPP = True
except Exception:
    pathfinder_cpp = None
    _HAS_CPP = False

# -------------------------
# Implementation details
# -------------------------
def rgb_distance(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

def build_cost_grid(im, color_cost_map, threshold=20):
    """
    Build a 2D numpy array of movement costs from image.
    im: PIL Image in RGB
    color_cost_map: dict {(r,g,b): cost}
    threshold: if not None, only map if nearest color distance <= threshold; else pixel is impassable.
    """
    w, h = im.size
    pixels = np.array(im.convert("RGB"))
    cost_grid = np.full((h, w), np.inf, dtype=float)
    mapped_colors = list(color_cost_map.keys())
    for y in range(h):
        for x in range(w):
            rgb = tuple(int(v) for v in pixels[y, x])
            if rgb in color_cost_map:
                cost_grid[y, x] = color_cost_map[rgb]
            else:
                # find nearest color
                dists = [rgb_distance(rgb, mc) for mc in mapped_colors]
                idx = int(np.argmin(dists))
                best = mapped_colors[idx]
                if threshold is None or dists[idx] <= threshold:
                    cost_grid[y, x] = color_cost_map[best]
                else:
                    cost_grid[y, x] = math.inf
    return cost_grid

def neighbors(x, y, w, h, diagonal=True):
    deltas = [(-1,0),(1,0),(0,-1),(0,1)]
    if diagonal:
        deltas += [(-1,-1),(-1,1),(1,-1),(1,1)]
    for dx,dy in deltas:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny, math.hypot(dx, dy) # returns step length (1 or sqrt(2))

def heuristic(a, b):
    # Euclidean heuristic (admissible)
    (x1, y1), (x2, y2) = a, b
    return math.hypot(x2 - x1, y2 - y1)

def a_star(cost_grid, start, goal, diagonal=True):
    h, w = cost_grid.shape
    sx, sy = start
    gx, gy = goal
    # If start/goal are impassable, bail
    if not math.isfinite(cost_grid[sy, sx]):
        raise ValueError("Start is impassable")
    if not math.isfinite(cost_grid[gy, gx]):
        raise ValueError("Goal is impassable")

    open_set = []
    # items in heap: (f_score, g_score, (x,y), parent_index)
    start_h = heuristic(start, goal)
    heapq.heappush(open_set, (start_h, 0.0, (sx, sy), None))
    came_from = {} # (x,y) -> parent (x,y)
    gscore = { (sx, sy): 0.0 }
    closed = set()

    while open_set:
        f, g, current, parent = heapq.heappop(open_set)
        if current in closed:
            continue
        came_from[current] = parent
        if current == (gx, gy):
            # reconstruct path
            path = []
            cur = current
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return path, gscore[current]
        closed.add(current)
        cx, cy = current
        for nx, ny, step_len in neighbors(cx, cy, w, h, diagonal):
            if not math.isfinite(cost_grid[ny, nx]):
                continue # blocked
            # movement cost to move onto neighbor: average of cell costs times step length
            # Another option: use cost of target cell only. We average here for smoother behaviour.
            move_cost = (cost_grid[cy, cx] + cost_grid[ny, nx]) / 2.0 * step_len
            tentative_g = gscore[current] + move_cost
            if (nx, ny) in gscore and tentative_g >= gscore[(nx, ny)]:
                continue
            gscore[(nx, ny)] = tentative_g
            fscore = tentative_g + heuristic((nx, ny), (gx, gy))
            heapq.heappush(open_set, (fscore, tentative_g, (nx, ny), current))
    return None, math.inf # no path

# Path simplification using line-of-sight check
def line_of_sight_clear(p1, p2, cost_grid):
    # Bresenham-like sampling between p1 and p2; ensure no impassable pixel intersects the segment.
    (x1, y1), (x2, y2) = p1, p2
    dx = x2 - x1
    dy = y2 - y1
    steps = int(max(abs(dx), abs(dy)))
    if steps == 0:
        return True
    for i in range(steps + 1):
        t = i / steps
        xi = int(round(x1 + dx * t))
        yi = int(round(y1 + dy * t))
        if not (0 <= xi < cost_grid.shape[1] and 0 <= yi < cost_grid.shape[0]):
            return False
        if not math.isfinite(cost_grid[yi, xi]):
            return False
    return True

def simplify_path(path, cost_grid):
    if len(path) <= 2:
        return path
    simplified = [path[0]]
    i = 0
    while i < len(path) - 1:
        # find farthest j such that line_of_sight_clear(i,j)
        j = len(path) - 1
        while j > i + 1:
            if line_of_sight_clear(path[i], path[j], cost_grid):
                break
            j -= 1
        simplified.append(path[j])
        i = j
    return simplified

# -------------------------
# Main CLI
# -------------------------

def parse_point(s, w, h):
    """Parse 'x,y' or 'x y' and clamp within image bounds."""
    if s is None:
        return None
    # Accept both comma and space separated
    if "," in s:
        parts = s.split(",")
    else:
        parts = s.split()  # will work for 'x y'
    if len(parts) != 2:
        raise ValueError(f"Expected a coordinate like 'x,y' but got '{s}'")
    x = int(parts[0]); y = int(parts[1])
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    return x, y

def main(
    fname: str,
    start: tuple = None,
    goal: tuple = None,
    use_cpp: bool = True,
    k: int = 3,                 # how many routes to try to find
    overlap_max: float = 0.50,  # max allowed Jaccard overlap with any accepted route
    mode: str = "penalize",     # "penalize" or "disjoint"
    penalty: float = 6.0,       # base penalty for "penalize" mode
    radius: int = 10,            # radius for penalty/masking around a path
    decay: float = 0.6          # penalty decays with distance in "penalize" mode
    ):
    """
    Run pathfinding on an image and return up to K diverse routes.

    :param fname: Path to the map image (PNG/JPG)
    :param start: Optional (x,y)
    :param goal : Optional (x,y)
    :param use_cpp: Use C++ A* if available
    :param k: number of diverse routes to find
    :param overlap_max: max Jaccard overlap allowed between any two kept routes
    :param mode: "penalize" (soft diversity) or "disjoint" (hard masking)
    :param penalty: base penalty to add near previous paths (penalize mode)
    :param radius: neighborhood radius used by penalty/masking
    :param decay: penalty decay factor with distance (0..1]
    """
    # --- optional import of external overlap helper ---
 
    import pythonextensions.overlap as _overlap_mod
    
   


    start_time = time.time()

    im = Image.open(fname).convert("RGB")
    w, h = im.size
    print(f"Loaded image {fname} ({w}x{h})")

    # --- Build cost grid -----------------------------------------------
    rgb     = np.asarray(im.convert("RGB"), dtype=np.uint8)
    palette = np.array(list(COLOR_COST_MAP.keys()), dtype=np.uint8)   # (K,3)
    costs   = np.array(list(COLOR_COST_MAP.values()), dtype=np.float64)
    thr     = -1.0 if COLOR_MATCH_THRESHOLD is None else float(COLOR_MATCH_THRESHOLD)

    print("Building cost grid from colors...")
    use_cpp_cost_builder = _HAS_CPP and hasattr(pathfinder_cpp, "build_cost_grid")
    if use_cpp_cost_builder:
        # Optional C++ build_cost_grid if you implemented it
        cost_grid = pathfinder_cpp.build_cost_grid(rgb, palette, costs, thr)
    else:
        cost_grid = build_cost_grid(im, COLOR_COST_MAP, threshold=COLOR_MATCH_THRESHOLD)

    # --- Defaults for start/goal ---------------------------------------
    start = start if start else (0, 0)
    goal  = goal  if goal  else (w - 1, h - 1)
    print(f"Start: {start}, Goal: {goal}")

    # --- A* backend picker ---------------------------------------------
    def _run_astar(grid):
        if use_cpp and _HAS_CPP:
            # pathfinder_cpp expects list-of-lists
            path_cpp, total_cost = pathfinder_cpp.a_star(grid.tolist(), start, goal, DIAGONAL_MOVEMENT)
            path = [(int(x), int(y)) for (x, y) in path_cpp] if path_cpp else None
            return path, total_cost
        else:
            return a_star(grid, start, goal, diagonal=DIAGONAL_MOVEMENT)

    # --- Find the first (shortest) route --------------------------------
    try:
        path0, cost0 = _run_astar(cost_grid)
    except ValueError as e:
        print("Error:", e)
        return

    if not path0:
        print("No path found.")
        return

    results = [{'path': path0, 'cost': cost0}]
    print(f"Route 1: nodes={len(path0)}, cost≈{cost0:.2f}")

    # --- Iteratively find more diverse routes ---------------------------
    for i in range(2, k + 1):
        # Start from the base grid each iteration (fresh penalties/masks)
        work_grid = cost_grid
        if mode == "penalize":
            # Apply soft penalties around *all* previously accepted paths
            for r in results:
                work_grid = _overlap_mod._penalize_cost_grid(work_grid, r['path'],
                                                base_penalty=penalty, radius=radius, decay=decay)
        elif mode == "disjoint":
            for r in results:
                work_grid = _overlap_mod._mask_out_path(work_grid, r['path'], radius=radius)
        else:
            raise ValueError("mode must be 'penalize' or 'disjoint'")

        cand_path, cand_cost = _run_astar(work_grid)
        if not cand_path:
            print(f"Route {i}: no path (stopping).")
            break

        # Check overlap against all accepted routes
        ok = all(_overlap_mod._jaccard_overlap(r['path'], cand_path) <= overlap_max for r in results)

        # In penalize mode we can try once with stronger settings if too similar
        if not ok and mode == "penalize":
            work_grid = cost_grid
            # escalate penalty / radius a bit
            for r in results:
                work_grid = _overlap_mod._penalize_cost_grid(work_grid, r['path'],
                                                base_penalty=penalty * 1.5, radius=radius + 1, decay=decay)
            cand_path, cand_cost = _run_astar(work_grid)
            if cand_path:
                ok = all(_overlap_mod._jaccard_overlap(r['path'], cand_path) <= overlap_max for r in results)

        if ok and cand_path:
            results.append({'path': cand_path, 'cost': cand_cost})
            print(f"Route {i}: nodes={len(cand_path)}, cost≈{cand_cost:.2f}")
        else:
            print(f"Route {i}: too similar (overlap > {overlap_max:.2f}); stopping.")
            break

    # --- Save images for all routes ------------------------------------
    
    if SIMPLIFY_PATH:
        for r in results:
            before = len(r['path'])
            r['path'] = simplify_path(r['path'], cost_grid)
            after = len(r['path'])
            print(f"Simplified route from {before} -> {after} nodes")
            
    draw_path_on_image(im, results, width=5)
    

    end_time = time.time()
    print(f"Took {end_time - start_time:.3f} seconds total")

    return results

# Visualization helper (unchanged)
def draw_path_on_image(im, results, outpath="./static/path_result.png", colors=[(255, 139, 13),(255, 0, 0),(45,16,255)], width=5, times = 1):
    print("trying to draw lines")
    
    im_rgb = im.convert("RGBA")
    font = ImageFont.truetype("arial.ttf", 16)
    
    for i, r in enumerate(results):
        color = colors[i%len(results)]
        print("::inside loop::")
        overlay = Image.new("RGBA", im.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        # path is list of (x,y)
        pts = [(x + 0.5, y + 0.5) for (x,y) in r['path']] # center of pixels
        if len(pts) >= 2:
            draw.line(pts, fill=color + (200,), width=width, joint='curve')
            
            # draw endpoints
            mid_idx = len(pts) // 2
            label_pos = pts[mid_idx]

            # draw label
            label = r.get("label", f"Route {i+1} ({r['cost']:.2f})")
            
            bbox = draw.textbbox(label_pos, label, font=font)
            x0, y0, x1, y1 = bbox

            # add some padding around text
            pad = 4
            rect_coords = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)

            # draw white rectangle with slight transparency
            draw.rectangle(rect_coords, fill=(255,255,255,200))
            # Write text
            draw.text(label_pos, label, fill=(0,0,0,255), font=font)
            
        if pts:
            r = max(2, width+2)
            draw.ellipse([pts[0][0]-r, pts[0][1]-r, pts[0][0]+r, pts[0][1]+r], fill=(0,255,0,255))
            draw.ellipse([pts[-1][0]-r, pts[-1][1]-r, pts[-1][0]+r, pts[-1][1]+r], fill=(0,0,255,255))
        im_rgb = Image.alpha_composite(im_rgb, overlay)
        
    im_rgb.save(outpath)
    print(f"Saved result to {outpath}")

if __name__ == "__main__":
    
    main()
    