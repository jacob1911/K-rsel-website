import math
# ---- Diversity helpers ------------------------------------------------
def _jaccard_overlap(path_a, path_b):
    """Return Jaccard overlap between two paths (as sets of (x,y))."""
    sa, sb = set(path_a), set(path_b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def _penalize_cost_grid(base_cost_grid, path, base_penalty=5.0, radius=3, decay=0.6):
    """
    Return a new cost grid with added penalties around the given path.
    Penalty at distance d <= radius is base_penalty * (decay ** d).
    """
    H, W = base_cost_grid.shape
    penalized = base_cost_grid.copy()
    for (x, y) in path:
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    d = math.hypot(dx, dy)
                    if d <= radius and math.isfinite(penalized[ny, nx]):
                        penalized[ny, nx] += base_penalty * (decay ** d)
    return penalized

def _mask_out_path(base_cost_grid, path, radius=0):
    """
    Return a new cost grid where cells along the path (and within radius)
    are set to inf (hard disjointness). Keeps start/goal as passable.
    """
    H, W = base_cost_grid.shape
    masked = base_cost_grid.copy()
    if not path:
        return masked
    start = path[0]
    goal = path[-1]
    for (x, y) in path:
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    # keep endpoints always passable
                    if (nx, ny) == start or (nx, ny) == goal:
                        continue
                    masked[ny, nx] = math.inf

