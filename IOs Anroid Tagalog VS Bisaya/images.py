"""Custom snake graphics helper.

Drop your own PNG images into the assets folder to replace the default
colored-rectangle snake. Each snake has its own sub-folder:

    assets/p1/    -> Player 1 (green snake)
    assets/p2/    -> Player 2 (blue snake)

The following files are recognised inside a snake folder. If a file is
missing, that part of the snake falls back to the default drawing.

    head.png     The snake head, drawn facing RIGHT.
    body.png     A straight body segment, drawn horizontal (pointing RIGHT).
    corner.png   A 90 degree bend in the body path.
    tail.png     The tail segment, taper (tip) facing LEFT, flat attach edge RIGHT.

Use a transparent background (.png) so the board shows through. Every image is
trimmed to its opaque pixels, scaled to cover exactly one board cell
(CELL x CELL) and rotated automatically to match the snake's direction, so a
straight run stays one unbroken ribbon and both kinds of bend line up with the
grid.

To give a snake custom colours for the fallback drawing (when images are
missing) set them in the SnakeAssets constructor below.
"""

import os
import json
import sys
from pathlib import Path

import pygame

DEFAULT_HEAD_COLOR = (80, 200, 120)
DEFAULT_BODY_COLOR = (40, 150, 80)
DEFAULT_TAIL_COLOR = (40, 150, 80)


# ── Shared rule tables (M4) ────────────────────────────────────────────────
# shared/game_content.json is the single source of truth for every value the
# three implementations (desktop / web / Flutter) must agree on: the speed
# curve, animation fps + frame caps, part fit ratio, sway, the popup tables,
# the voice tables and the food discovery rule. Each platform has a tiny
# loader (web: fetch in game.js; Flutter: lib/content.dart; here) and every
# consumer mirrors the canonical values as inline fallbacks, so a missing or
# mangled file degrades to the shipped defaults instead of breaking boot.
CONTENT_PATHS = ("game_content.json", "shared/game_content.json")


def _content_file():
    """The bundled copy first (PyInstaller onefile), then the repo copy."""
    bases = []
    try:
        bases.append(sys._MEIPASS)
    except AttributeError:
        pass
    bases.append(os.path.abspath(os.path.dirname(__file__)))
    bases.append(os.path.abspath("."))
    for base in bases:
        for name in CONTENT_PATHS:
            candidate = Path(base) / name
            if candidate.is_file():
                return candidate
    return None


def load_game_content():
    """Read + validate shared/game_content.json. {} when missing/corrupt."""
    path = _content_file()
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


GAME_CONTENT = load_game_content()


def content_value(path, fallback):
    """Nested lookup: content_value(["speed", "startFps"], 12)."""
    node = GAME_CONTENT
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return fallback
        node = node[key]
    return node if node is not None else fallback

# Part fit ratio: artwork is stretched across the whole cell up to this
# aspect ratio (shared as `part.fillRatio` in shared/game_content.json);
# anything more elongated is letterboxed instead of being inflated.
PART_FILL_RATIO = float(content_value(["part", "fillRatio"], 3.0))

# corner.png is authored as this elbow: the body enters through the LEFT edge
# travelling right (CORNER_IN) and leaves through the BOTTOM edge travelling
# down. Mirroring it gives the left-hand bend (CORNER_IN_FLIPPED); every other
# orientation is a rotation of one of those two, which keeps all four turns
# consistent instead of relying on a hand-written table per turn kind.
CORNER_IN = (1, 0)
CORNER_IN_FLIPPED = (-1, 0)

# Parts that have to run along the direction of travel. Their art may be
# authored pointing any way, so it is turned on load until its long axis runs
# horizontally - that is what makes consecutive segments meet flush.
HORIZONTAL_PARTS = ("body", "tail")

# Fraction of a cell the body slithers sideways. Kept well under 1/2 so the
# segments can never detach into the neighbouring cells. Shared as
# `sway.amount` in shared/game_content.json.
SWAY_AMOUNT = float(content_value(["sway", "amount"], 0.14))

# Snake-part animation cadence (Aseprite frame sequences) and the sanity cap
# on how many numbered `<part>_N.png` frames load per part. Shared as
# `animation.*` in shared/game_content.json (web/flutter use the same table).
SNAKE_ANIM_FPS = int(content_value(["animation", "snakeFps"], 8))
FOOD_ANIM_FPS = int(content_value(["animation", "foodFps"], 6))
SNAKE_FRAME_CAP = int(content_value(["animation", "snakeFrameCap"], 16))

# pygame angles are counter-clockwise on screen, so a right-facing image has to
# be turned +90 to face up and +270 to face down.
_CCW_TURNS = {
    ((1, 0), (0, -1)): 90,
    ((0, -1), (-1, 0)): 90,
    ((-1, 0), (0, 1)): 90,
    ((0, 1), (1, 0)): 90,
    ((1, 0), (-1, 0)): 180,
    ((-1, 0), (1, 0)): 180,
    ((0, -1), (0, 1)): 180,
    ((0, 1), (0, -1)): 180,
    ((1, 0), (0, 1)): 270,
    ((0, 1), (1, 0)): 270,
    ((-1, 0), (0, -1)): 270,
    ((0, -1), (1, 0)): 270,
}


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def _crop_transparent(surface, pad=0):
    """Cut away fully-transparent borders so the artwork fills the frame.

    The aspect ratio is deliberately left alone: forcing a square crop sliced
    the long body segments and the elbows in half, which is what stopped the
    artwork from lining up with the board grid. Callers pick the cell placement
    afterwards (see ``_fit_cell``). Returns the original surface when it has
    nothing to trim.
    """
    width, height = surface.get_size()
    if width == 0 or height == 0:
        return surface

    mask = pygame.mask.from_surface(surface)
    if mask.count() == 0:
        return surface

    rects = mask.get_bounding_rects()
    if not rects:
        return surface
    bounds = rects[0]
    for r in rects[1:]:
        bounds = bounds.union(r)

    left = max(bounds.left - pad, 0)
    top = max(bounds.top - pad, 0)
    right = min(bounds.right + pad, width)
    bottom = min(bounds.bottom + pad, height)

    cropped = surface.subsurface((left, top, right - left, bottom - top))
    return cropped.copy()


def _fit_cell(surface, cell, fill_ratio=PART_FILL_RATIO):
    """Scale artwork onto exactly one board cell.

    The art is stretched across the whole cell when its aspect ratio is within
    `fill_ratio`, which is what makes neighbouring segments meet: the head, the
    straights, the elbows and the tail all cover the same square, so a straight
    run is one unbroken ribbon instead of separated tiles.

    Anything more elongated than `fill_ratio` keeps its aspect ratio and is
    centred on the cell instead, so a long body bar is letterboxed rather than
    blown up into a square blob.
    """
    width, height = surface.get_size()
    if width <= 0 or height <= 0 or cell <= 0:
        return surface

    long_side = max(width, height)
    short_side = min(width, height)
    if short_side > 0 and long_side / short_side <= fill_ratio:
        return pygame.transform.smoothscale(surface, (cell, cell))

    scale = cell / float(long_side)
    return pygame.transform.smoothscale(
        surface,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
    )


def _normalize_horizontal(surface, min_ratio=1.25):
    """Turn *genuinely vertical* artwork horizontal.

    Body and tail art is authored with its flat attach edge on the RIGHT
    (+x, per the authoring notes above); `_rotated` then aligns +x with the
    direction of travel. Only art clearly taller than wide (aspect >=
    `min_ratio`) is rotated a quarter turn, so its long axis runs along
    travel. Near-square frames count as art slop, NOT vertical authoring --
    baking them sideways left a 90-degree mismatch against the +x compose,
    which is what made p1's tail render sideways at every direction.
    """
    width, height = surface.get_size()
    if height > width and width > 0 and height / width >= min_ratio:
        return pygame.transform.rotate(surface, 270)
    return surface


def _ccw_angle(source, target):
    """Counter-clockwise pygame rotation that points `source` at `target`."""
    if source == target:
        return 0
    return _CCW_TURNS.get((source, target), 0)


class SnakeAssets:
    """Loads and caches the graphics for one snake.

    head_color / body_color / tail_color are only used when the matching
    image file is missing (the default rectangle fallback).
    """

    ANIM_FPS = SNAKE_ANIM_FPS  # frames per second for Aseprite frame sequences

    def __init__(self, assets_dir, cell, head_color=DEFAULT_HEAD_COLOR,
                 body_color=DEFAULT_BODY_COLOR, tail_color=DEFAULT_TAIL_COLOR):
        self.cell = cell
        self.head_color = head_color
        self.body_color = body_color
        self.tail_color = tail_color
        self.sway = SWAY_AMOUNT
        self._base = Path(resource_path(assets_dir))

        # Cached rotated versions: part -> {(direction, frame_idx): surface}
        self._cached = {"head": {}, "body": {}, "tail": {}}
        # Corners need a mirror as well as a rotation: {(flip, angle, frame)}
        self._corner_cache = {}
        self._flip_cache = {}
        self._loaded = {}
        # Animation frames per part: part -> [surface, ...] (frame 0 = base)
        self.frames = {}

        self.head = self._load_frames("head")
        self.body = self._load_frames("body")
        self.corner = self._load_frames("corner")
        self.tail = self._load_frames("tail")

    def _place(self, part, raw):
        """Trim, orient and fit one raw frame onto a single board cell."""
        # No transparent padding: the art is scaled flush to the cell edge so
        # neighbouring segments meet without a seam.
        raw = _crop_transparent(raw, pad=0)
        if part in HORIZONTAL_PARTS:
            raw = _normalize_horizontal(raw)
        return _fit_cell(raw, self.cell, PART_FILL_RATIO)

    def _load_one(self, part, filename):
        """Load + place one PNG onto the grid cell. None if missing/unreadable."""
        path = self._base / filename
        if not path.is_file():
            return None
        try:
            raw = pygame.image.load(str(path))
            try:
                raw = raw.convert_alpha()
            except pygame.error:
                pass
        except pygame.error:
            return None
        return self._place(part, raw)

    def _load(self, part, filename):
        """Legacy single-file loader (kept for compatibility)."""
        surf = self._load_one(part, filename)
        if surf is not None:
            self._loaded[part] = surf
        return surf

    def _load_frames(self, part):
        """Load `<part>.png` plus `<part>_0.png`, `<part>_1.png`, … as animation.

        Single-file art keeps working: if no `_N` files exist the base
        `<part>.png` alone becomes the 1-frame animation.
        """
        frames = []
        base = self._load_one(part, f"{part}.png")
        if base is not None:
            frames.append(base)
        i = 0
        while True:
            f = self._load_one(part, f"{part}_{i}.png")
            if f is None:
                break
            frames.append(f)
            i += 1
            if i > SNAKE_FRAME_CAP:  # sanity cap from the shared rules table
                break
        # If only numbered frames exist (no base), use them as-is.
        self.frames[part] = frames
        first = frames[0] if frames else None
        if first is not None:
            self._loaded[part] = first
        return first

    def _frame_index(self, part, time_ms):
        frames = self.frames.get(part) or []
        if len(frames) <= 1:
            return 0
        return int(time_ms / (1000.0 / self.ANIM_FPS)) % len(frames)

    def _rotated(self, part, direction, time_ms=0):
        """Return the cached rotated surface for a part, direction and time.

        Images are authored facing right (1, 0). We rotate to match.
        """
        return self._rotated_idx(
            part, direction, self._frame_index(part, time_ms))

    def _rotated_idx(self, part, direction, idx):
        """Same as _rotated, but `idx` selects the frame directly.

        Used for per-segment visual variants: the game assigns every new
        segment a random variant id and the renderer maps it onto the
        loaded frames with modulo, so single-frame art renders unchanged.
        """
        frames = self.frames.get(part) or []
        if not frames:
            return None
        idx = idx % len(frames)
        key = (direction, idx)
        cache = self._cached[part]
        if key in cache:
            return cache[key]
        surface = frames[idx]
        angle = _ccw_angle(CORNER_IN, direction)
        rotated = pygame.transform.rotate(surface, angle) if angle else surface
        cache[key] = rotated
        return rotated

    def _flipped(self, surface):
        """Horizontally mirrored copy of a surface (cached by identity)."""
        key = id(surface)
        mirrored = self._flip_cache.get(key)
        if mirrored is None:
            mirrored = pygame.transform.flip(surface, True, False)
            self._flip_cache[key] = mirrored
        return mirrored

    def frame_corner(self, incoming, outgoing, time_ms=0, idx=None):
        """Corner sprite for a turn, or None when the turn is not a bend.

        A left-hand bend is the mirror image of the authored right-hand elbow,
        so it is flipped first and then turned by the same rule. Deriving the
        angle from `incoming` alone keeps all eight possible turns consistent,
        instead of hand-maintaining a lookup per turn kind.

        Pass `idx` for a per-segment visual variant; None keeps the global
        time-based animation.
        """
        frames = self.frames.get("corner") or []
        if not frames:
            return None
        flip, angle = _corner_orientation(incoming, outgoing)
        if angle is None:
            return None
        if idx is None:
            idx = self._frame_index("corner", time_ms)
        else:
            idx = idx % len(frames)
        key = (flip, angle, idx)
        surface = self._corner_cache.get(key)
        if surface is None:
            surface = frames[idx] if idx < len(frames) else frames[0]
            if flip:
                surface = self._flipped(surface)
            if angle:
                surface = pygame.transform.rotate(surface, angle)
            self._corner_cache[key] = surface
        return surface

    def frame_at(self, part, direction, idx):
        """Per-segment variant frame (visual-variety growth)."""
        return self._rotated_idx(part, direction, idx)

    def frame(self, part, direction, time_ms=0):
        """Public accessor for one animated+rotated frame (None if missing)."""
        return self._rotated(part, direction, time_ms)

    def register(self, part, surface):
        """Manually install a surface for a part (used by fallback drawing)."""
        self._loaded[part] = surface
        self.frames[part] = [surface]
        self._cached[part] = {}
        self._corner_cache.clear()
        self._flip_cache.clear()


def _dir_between(prev, curr):
    """Direction tuple from segment prev to segment curr."""
    return (curr[0] - prev[0], curr[1] - prev[1])


# Turning right / left from a given travel direction.
_RIGHT_TURN = {(1, 0): (0, 1), (0, 1): (-1, 0), (-1, 0): (0, -1), (0, -1): (1, 0)}
_LEFT_TURN = {(1, 0): (0, -1), (0, -1): (-1, 0), (-1, 0): (0, 1), (0, 1): (1, 0)}


def _is_right_turn(incoming, outgoing):
    """True if the snake turns right going from incoming to outgoing."""
    return _RIGHT_TURN.get(incoming) == outgoing


def _corner_orientation(incoming, outgoing):
    """Return (mirror_horizontally, ccw_angle) for a turn, or (False, None).

    `corner.png` is authored as flow entering the LEFT edge travelling right
    and leaving the BOTTOM edge travelling down. Mirroring that elbow turns it
    into the left-hand bend, and both hands are then rotated by the single rule
    "spin the art until its entering side faces `incoming`".
    """
    if incoming == outgoing:
        return False, None
    if _RIGHT_TURN.get(incoming) == outgoing:
        return False, _ccw_angle(CORNER_IN, incoming)
    if _LEFT_TURN.get(incoming) == outgoing:
        return True, _ccw_angle(CORNER_IN_FLIPPED, incoming)
    return False, None


def _corner_direction(incoming, outgoing):
    """Deprecated label helper kept for compatibility ("right" / "left" / None)."""
    if incoming == outgoing:
        return None
    if _RIGHT_TURN.get(incoming) == outgoing:
        return "right"
    if _LEFT_TURN.get(incoming) == outgoing:
        return "left"
    return None


def _rotate_corner(surface, kind, incoming):
    """Deprecated: rotate a corner elbow to enter along `incoming`.

    Kept so older callers keep working; new code should use
    ``SnakeAssets.frame_corner``, which mirrors left-hand bends correctly.
    """
    flip = kind == "left"
    if flip:
        surface = pygame.transform.flip(surface, True, False)
    authored_in = CORNER_IN_FLIPPED if flip else CORNER_IN
    return pygame.transform.rotate(surface, _ccw_angle(authored_in, incoming))


def _perpendicular(direction):
    """Unit vector 90 degrees to the left of `direction`."""
    dx, dy = direction
    if (dx, dy) == (0, 0):
        return 0.0, 0.0
    return float(-dy), float(dx)


def _sway_offsets(snake, time_ms, cell, amount=SWAY_AMOUNT):
    """Per-segment slither offsets, in pixels, head first.

    Visual only - the grid logic is untouched. Two details keep the body in one
    piece instead of snapping apart at every bend:

    * a segment's sideways direction is the average of the perpendiculars of
      the directions entering and leaving it, so a bend and both its straight
      neighbours sway the same way instead of in two perpendicular directions;
    * the wave ramps in smoothly from the head, which stays grid-locked so
      aiming and eating still line up exactly with the food cell.
    """
    import math

    n = len(snake)
    if n <= 1 or cell <= 0 or amount <= 0:
        return [(0.0, 0.0)] * n

    # Direction of travel of each segment, head first. The last entry repeats
    # the tail's own direction so the tail keeps a stable sideways axis.
    travel = [_dir_between(snake[i + 1], snake[i]) for i in range(n - 1)]
    travel.append(travel[-1] if travel else (1, 0))

    axis = []
    for i in range(n):
        ax, ay = _perpendicular(travel[i])
        bx, by = _perpendicular(travel[i + 1]) if i + 1 < n else (ax, ay)
        px, py = ax + bx, ay + by
        mag = math.hypot(px, py)
        axis.append((px / mag, py / mag) if mag > 1e-9 else (ax, ay))

    peak = cell * amount
    last = max(1, n - 1)
    offsets = []
    for i in range(n):
        t = i / float(last)
        ramp = t * t * (3.0 - 2.0 * t)  # smoothstep: locked at the head
        swing = math.sin(time_ms / 150.0 - i * 0.5) * peak * ramp
        ax, ay = axis[i]
        offsets.append((ax * swing, ay * swing))
    return offsets


def draw_image_snake(screen, snake, assets, time_ms=None, variants=None):
    """Draw a snake from images. Falls back to rectangles where images differ.

    snake:  list of (x, y) grid coordinates, head first.
    assets: a SnakeAssets instance.
    time_ms: clock for sway animation (defaults to pygame ticks).
    variants: optional per-segment variant ids (same length as snake). A new
        segment rolls a random id when the snake eats; the renderer maps it
        onto the loaded frames with modulo, so body/corner tiles vary along
        the snake while single-frame art renders exactly as before.
    """
    if not snake:
        return

    if time_ms is None:
        try:
            time_ms = pygame.time.get_ticks()
        except Exception:
            time_ms = 0
    cell = getattr(assets, "cell", 32)
    sway = getattr(assets, "sway", SWAY_AMOUNT)

    n = len(snake)
    offsets = _sway_offsets(snake, time_ms, cell, sway)

    # --- tail --------------------------------------------------------------
    if n >= 2:
        # Direction the tail points: away from the body, towards the head.
        d = _dir_between(snake[-1], snake[-2])
        ox, oy = offsets[-1]
        tail_img = assets.frame("tail", d, time_ms)
        if tail_img is not None:
            draw_cell_image(screen, tail_img, snake[-1], cell, ox, oy)
        else:
            _draw_fallback(screen, snake[-1], assets.tail_color, cell, ox, oy)
    else:
        # single segment: just the head
        _draw_fallback(screen, snake[0], assets.head_color, cell)
        return

    # --- body (between head and tail) --------------------------------------
    for i in range(1, n - 1):
        cell_pos = snake[i]
        incoming = _dir_between(snake[i - 1], cell_pos)
        outgoing = _dir_between(cell_pos, snake[i + 1])
        ox, oy = offsets[i]
        variant = variants[i] if variants and i < len(variants) else None

        if incoming != outgoing:
            corner = assets.frame_corner(incoming, outgoing, time_ms,
                                         idx=variant)
            if corner is not None:
                draw_cell_image(screen, corner, cell_pos, cell, ox, oy)
                continue

        if variant is None:
            body_img = assets.frame("body", incoming, time_ms)
        else:
            body_img = assets.frame_at("body", incoming, variant)
        if body_img is not None:
            draw_cell_image(screen, body_img, cell_pos, cell, ox, oy)
        else:
            _draw_fallback(screen, cell_pos, assets.body_color, cell, ox, oy)

    # --- head --------------------------------------------------------------
    # The head keeps its grid-locked offset so aim/eating stays precise.
    d = _dir_between(snake[0], snake[1]) if n >= 2 else (1, 0)
    ox, oy = offsets[0]
    head_img = assets.frame("head", d, time_ms)
    if head_img is not None:
        draw_cell_image(screen, head_img, snake[0], cell, ox, oy)
    else:
        _draw_fallback(screen, snake[0], assets.head_color, cell, ox, oy)


def draw_cell_image(screen, surface, grid_pos, cell, ox=0, oy=0):
    """Blit a surface centred on the cell at grid coordinates (+ sway px).

    `cell` is the board cell size, never the sprite's own size: a sprite that
    was letterboxed (or rotated out of a square) still has to land exactly on
    its grid square or the whole snake drifts off the board.
    """
    x, y = grid_pos
    w, h = surface.get_size()
    dest = pygame.Rect(int(round(x * cell)) + int(round(ox)),
                       int(round(y * cell)) + int(round(oy)), cell, cell)
    dest = dest.move(-(w - cell) // 2, -(h - cell) // 2)
    screen.blit(surface, dest)


def _draw_fallback(screen, grid_pos, color, cell, ox=0, oy=0):
    """Rectangle stand-in for a part that has no artwork.

    It covers the full cell (not an inset block) so a snake running entirely on
    fallbacks is still one continuous ribbon rather than a dotted line.
    """
    x, y = grid_pos
    radius = max(2, cell // 5)
    rect = pygame.Rect(int(round(x * cell + ox)), int(round(y * cell + oy)),
                       cell, cell)
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    # glossy highlight so the fallback still looks polished
    hi = pygame.Rect(rect.left + 2, rect.top + 2,
                     max(1, rect.width - 4), max(2, rect.height // 3))
    overlay = pygame.Surface(hi.size, pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 55))
    screen.blit(overlay, hi.topleft)
    pygame.draw.rect(screen, (0, 0, 0, 70), rect, width=1, border_radius=radius)


# Convenience: build assets for the two built-in snakes.
def make_default_assets(cell):
    return SnakeAssets("assets/p1", cell, (120, 255, 150), (80, 220, 120), (80, 220, 120)), \
           SnakeAssets("assets/p2", cell, (150, 200, 255), (90, 160, 250), (90, 160, 250))


class FoodAssets:
    """Loads the optional food artwork (supports animated frame sequences)."""

    ANIM_FPS = FOOD_ANIM_FPS

    def __init__(self, cell, folder=None, default_color=DEFAULT_HEAD_COLOR):
        self.cell = cell
        self.default_color = default_color
        self._image = None
        self.frames = []
        # Food discovery rule from the shared table: a folder scan (all PNGs
        # become frames in alphabetical order) when the platform can list
        # files; `food.known` + `food.probeCount` document the fallback
        # probing used where directory listing is unavailable (web).
        self.reload(folder or content_value(["food", "dir"], "assets/food"))

    def reload(self, folder="assets/food"):
        """Rescan the food folder. All PNGs become animation frames in order.

        Single-image food keeps working: 1 PNG = 1 static frame.
        For Aseprite: export frames as food_0.png, food_1.png, … (or any
        names — alphabetical order = play order).
        """
        images_found = []
        base = Path(resource_path(folder))
        if base.is_dir():
            images_found = sorted(base.glob("*.png"))
        if not images_found:
            legacy = Path(resource_path("assets/food.png"))
            if legacy.is_file():
                images_found = [legacy]
        self.frames = [s for s in
                       (_load_scaled_cell(p, self.cell) for p in images_found) if s]
        self._image = self.frames[0] if self.frames else None
        return self._image

    def frame(self, time_ms=0):
        if not self.frames:
            return None
        if len(self.frames) == 1:
            return self.frames[0]
        return self.frames[int(time_ms / (1000.0 / self.ANIM_FPS)) % len(self.frames)]

    def draw(self, screen, grid_pos, time_ms=0):
        """Draw the food centred in its grid cell. Returns True if drawn."""
        x, y = grid_pos
        img = self.frame(time_ms)
        if img is not None:
            # centre it: the artwork keeps its aspect ratio, so it is usually
            # narrower than the cell and must not sit off to one side
            screen.blit(img, img.get_rect(center=(x * self.cell + self.cell // 2,
                                                  y * self.cell + self.cell // 2)))
            return True
        pygame.draw.circle(
            screen, self.default_color,
            (x * self.cell + self.cell // 2, y * self.cell + self.cell // 2),
            self.cell // 2 - 2
        )
        return False


def _load_scaled_cell(path, cell):
    """Load an image, trimmed and fitted to one cell (aspect kept). None if missing."""
    p = Path(resource_path(str(path)))
    if not p.is_file():
        return None
    try:
        raw = pygame.image.load(str(p))
        try:
            raw = raw.convert_alpha()
        except pygame.error:
            pass
    except pygame.error:
        return None
    return _fit_cell(_crop_transparent(raw), cell)


class UIAssets:
    """Loads optional artwork for the background and main menu."""

    def __init__(self, size=(800, 600)):
        self.size = size
        self.backgrounds = []
        self.current = -1
        self.menu_background = self._load_menu_background()
        self.logo = _load_scaled("assets/menu/logo.png", max_w=size[0] - 80)
        self.buttons = {}
        for label in ("1_player", "2_player", "leaderboard", "exit"):
            self.buttons[label] = {
                "normal": _load_scaled(f"assets/menu/button_{label}.png", max_w=size[0] - 200),
                "selected": _load_scaled(f"assets/menu/button_{label}_selected.png", max_w=size[0] - 200),
            }
        self.reload_backgrounds()

    def reload_backgrounds(self):
        """Rescan the assets/background folder. Picks up any new .png files."""
        folder = Path(resource_path("assets/background"))
        self.backgrounds = []
        if folder.is_dir():
            files = sorted(folder.glob("*.png"))
            for path in files:
                img = _load_fitted(str(path), self.size)
                if img is not None:
                    self.backgrounds.append((path.name, img))
        if self.current < 0 and self.backgrounds:
            self.current = 0
        if self.current >= len(self.backgrounds):
            self.current = len(self.backgrounds) - 1 if self.backgrounds else -1

    def _load_menu_background(self):
        """The menu background is a file named menu.png in the background folder."""
        menu = Path(resource_path("assets/background/menu.png"))
        if menu.is_file():
            return _load_fitted(str(menu), self.size)
        legacy = Path(resource_path("assets/menu_background.png"))
        if legacy.is_file():
            return _load_fitted(str(legacy), self.size)
        return None

    def get_background(self, index):
        if 0 <= index < len(self.backgrounds):
            return self.backgrounds[index][1]
        return None

    def draw_background(self, screen, use_menu=False):
        img = self.menu_background if (use_menu and self.menu_background) else self.get_background(self.current)
        if img is not None:
            screen.blit(img, (0, 0))
            return False
        return True

    def draw_logo(self, screen, center):
        if self.logo is not None:
            rect = self.logo.get_rect(center=center)
            screen.blit(self.logo, rect)
            return True
        return False

    def draw_button(self, screen, label, center, selected):
        imgset = self.buttons.get(label)
        if not imgset:
            return False
        img = imgset["selected"] if selected else imgset["normal"]
        if img is None:
            img = imgset["selected"] if imgset["selected"] else imgset["normal"]
        if img is None:
            return False
        rect = img.get_rect(center=center)
        screen.blit(img, rect)
        return True


def _load_scaled(path, max_w=None, max_h=None):
    """Load an image, cropped and scaled to fit within max_w x max_h."""
    p = Path(resource_path(str(path)))
    if not p.is_file():
        return None
    try:
        raw = pygame.image.load(str(p))
        try:
            raw = raw.convert_alpha()
        except pygame.error:
            pass
    except pygame.error:
        return None
    raw = _crop_transparent(raw)
    w, h = raw.get_size()
    if max_w and w > max_w:
        h = int(h * max_w / w)
        w = max_w
    if max_h and h > max_h:
        w = int(w * max_h / h)
        h = max_h
    return pygame.transform.smoothscale(raw, (w, h))


def _load_fitted(path, target_size):
    """Load an image stretched to exactly fill target_size. None if missing."""
    p = Path(resource_path(str(path)))
    if not p.is_file():
        return None
    try:
        raw = pygame.image.load(str(p))
        try:
            raw = raw.convert_alpha()
        except pygame.error:
            pass
    except pygame.error:
        return None
    return pygame.transform.smoothscale(raw, target_size)