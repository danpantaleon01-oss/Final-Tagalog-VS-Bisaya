"""Custom snake graphics helper.

Drop your own PNG images into the assets folder to replace the default
colored-rectangle snake. Each snake has its own sub-folder:

    assets/p1/    -> Player 1 (green snake)
    assets/p2/    -> Player 2 (blue snake)

The following files are recognised inside a snake folder. If a file is
missing, that part of the snake falls back to the default drawing.

    head.png     The snake head, drawn facing RIGHT.
    body.png     A straight body segment, drawn horizontal (pointing RIGHT).
    corner.png   A 90 degree bend in the body.
    tail.png     The tail segment, drawn facing LEFT.

Use a transparent background (.png) so the board shows through. Each image
is scaled to fit one board cell (CELL x CELL pixels) and rotated
automatically to match the snake's direction.

To give a snake custom colours for the fallback drawing (when images are
missing) set them in the SnakeAssets constructor below.
"""

import os
import sys
from pathlib import Path

import pygame

DEFAULT_HEAD_COLOR = (80, 200, 120)
DEFAULT_BODY_COLOR = (40, 150, 80)
DEFAULT_TAIL_COLOR = (40, 150, 80)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def _crop_transparent(surface):
    """Cut away fully-transparent borders so the artwork fills the frame.

    Also enforces a square, centered crop so images scale cleanly into a cell
    without distortion. Returns the cropped surface (or the original if it has
    no transparency or is already fully opaque across its bounds).
    """
    width, height = surface.get_size()
    if width == 0 or height == 0:
        return surface

    mask = pygame.mask.from_surface(surface)
    if mask.count() == 0:
        return surface

    rect = mask.get_bounding_rects()
    if not rect:
        return surface
    bounds = rect[0]
    for r in rect[1:]:
        bounds = bounds.union(r)

    # Pad by a pixel so antialiased edges aren't clipped.
    pad = 1
    left = max(bounds.left - pad, 0)
    top = max(bounds.top - pad, 0)
    right = min(bounds.right + pad, width)
    bottom = min(bounds.bottom + pad, height)

    cropped = surface.subsurface((left, top, right - left, bottom - top))

    # Enforce a square crop (center on the longer axis) so the final scale to a
    # square cell doesn't distort.
    cw, ch = cropped.get_size()
    side = max(cw, ch)
    if cw == ch:
        return cropped
    if cw > ch:
        extra = (cw - ch) // 2
        return cropped.subsurface((extra, 0, ch, ch))
    else:
        extra = (ch - cw) // 2
        return cropped.subsurface((0, extra, cw, cw))


class SnakeAssets:
    """Loads and caches the graphics for one snake.

    head_color / body_color / tail_color are only used when the matching
    image file is missing (the default rectangle fallback).
    """

    def __init__(self, assets_dir, cell, head_color=DEFAULT_HEAD_COLOR,
                 body_color=DEFAULT_BODY_COLOR, tail_color=DEFAULT_TAIL_COLOR):
        self.cell = cell
        self.head_color = head_color
        self.body_color = body_color
        self.tail_color = tail_color
        self._base = Path(resource_path(assets_dir))

        # Cached rotated versions: part -> {direction: surface}
        self._cached = {"head": {}, "body": {}, "corner": {}, "tail": {}}
        self._loaded = {}

        self.head = self._load("head", "head.png")
        self.body = self._load("body", "body.png")
        self.corner = self._load("corner", "corner.png")
        self.tail = self._load("tail", "tail.png")

    def _load(self, part, filename):
        """Load one image file, cropped and scaled to a cell. None if missing."""
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
        raw = _crop_transparent(raw)
        surface = pygame.transform.smoothscale(raw, (self.cell, self.cell))
        self._loaded[part] = surface
        return surface

    def _rotated(self, part, direction):
        """Return the cached rotated surface for a part and direction tuple.

        Images are authored facing right (1, 0). We rotate to match.
        """
        cache = self._cached[part]
        if direction in cache:
            return cache[direction]
        surface = self._loaded.get(part)
        if surface is None:
            return None
        # Angles for facing directions (right is the authored 0-degree image).
        # pygame rotates counterclockwise on screen, so a right-facing image
        # must be turned 270 to point down and 90 to point up.
        angles = {
            (1, 0): 0,      # right
            (0, -1): 90,    # up
            (-1, 0): 180,   # left
            (0, 1): 270,    # down
        }
        angle = angles.get(direction, 0)
        rotated = pygame.transform.rotate(surface, angle)
        cache[direction] = rotated
        return rotated

    def register(self, part, surface):
        """Manually install a surface for a part (used by fallback drawing)."""
        self._loaded[part] = surface
        self._cached[part] = {}


def _is_right(v):
    return v == (1, 0)


def _is_left(v):
    return v == (-1, 0)


def _is_up(v):
    return v == (0, -1)


def _is_down(v):
    return v == (0, 1)


def _dir_between(prev, curr):
    """Direction tuple from segment prev to segment curr."""
    return (curr[0] - prev[0], curr[1] - prev[1])


def _corner_direction(incoming, outgoing):
    """Return a header-corner image rotation label for a right turn.

    incoming = direction from previous segment -> this segment
    outgoing = direction from this segment -> next segment

    Returns None for a straight line, else a string key.
    """
    right = {
        (1, 0): (0, 1), (0, 1): (-1, 0),
        (-1, 0): (0, -1), (0, -1): (1, 0),
    }
    left = {
        (1, 0): (0, -1), (0, -1): (-1, 0),
        (-1, 0): (0, 1), (0, 1): (1, 0),
    }
    if right.get(incoming) == outgoing:
        return "right"
    if left.get(incoming) == outgoing:
        return "left"
    return None


def _rotate_corner(surface, kind, incoming):
    """Rotate a corner image (authored as a right turn from -> down) to match."""
    # Corner image authors should draw it as: entering from the left, exiting
    # downward ("right turn" when facing right). We rotate around that.
    base = {
        "right": {
            # authored turn: right -> down
            (1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270,
        },
        "left": {
            # authored turn mirrored: right -> up
            (1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): 270,
        },
    }
    angle = base[kind].get(incoming, 0)
    return pygame.transform.rotate(surface, angle)


def draw_image_snake(screen, snake, assets):
    """Draw a snake from images. Falls back to rectangles where images differ.

    snake:  list of (x, y) grid coordinates, head first.
    assets: a SnakeAssets instance.
    """
    if not snake:
        return

    n = len(snake)

    # --- tail --------------------------------------------------------------
    if n >= 2:
        prev = snake[-1]
        curr = snake[-2]
        d = _dir_between(prev, curr)  # direction tail points (away from body)
        tail_img = assets._rotated("tail", d)
        if tail_img is not None:
            draw_cell_image(screen, tail_img, snake[-1])
        else:
            _draw_fallback(screen, snake[-1], assets.tail_color)
    else:
        # single segment: just the head
        _draw_fallback(screen, snake[0], assets.head_color)
        return

    # --- body (between head and tail) --------------------------------------
    for i in range(1, n - 1):
        xi, yi = snake[i]
        prev = snake[i - 1]
        nxt = snake[i + 1]
        incoming = _dir_between(prev, (xi, yi))
        outgoing = _dir_between((xi, yi), nxt)

        corner = None
        if incoming != outgoing and assets.corner is not None:
            # A corner; author it as a right turn from -> down or up depending.
            right_map = {(1, 0): (0, 1), (0, 1): (-1, 0), (-1, 0): (0, -1), (0, -1): (1, 0)}
            if right_map.get(incoming) == outgoing:
                corner = _rotate_corner(assets.corner, "right", incoming)
            else:
                corner = _rotate_corner(assets.corner, "left", incoming)

        if corner is not None:
            draw_cell_image(screen, corner, (xi, yi))
        else:
            body_img = assets._rotated("body", incoming)
            if body_img is not None:
                draw_cell_image(screen, body_img, (xi, yi))
            else:
                _draw_fallback(screen, (xi, yi), assets.body_color)

    # --- head --------------------------------------------------------------
    if n >= 2:
        d = _dir_between(snake[0], snake[1])
    else:
        d = (1, 0)
    head_img = assets._rotated("head", d)
    if head_img is not None:
        draw_cell_image(screen, head_img, snake[0])
    else:
        _draw_fallback(screen, snake[0], assets.head_color)


def draw_cell_image(screen, surface, grid_pos):
    """Blit a surface onto the cell at grid coordinates."""
    x, y = grid_pos
    screen.blit(surface, (x * surface.get_width(), y * surface.get_height()))


def _draw_fallback(screen, grid_pos, color):
    from main import CELL
    x, y = grid_pos
    rect = pygame.Rect(x * CELL + 2, y * CELL + 2, CELL - 4, CELL - 4)
    pygame.draw.rect(screen, color, rect, border_radius=5)


# Convenience: build assets for the two built-in snakes.
def make_default_assets(cell):
    return SnakeAssets("assets/p1", cell, (120, 255, 150), (80, 220, 120), (80, 220, 120)), \
           SnakeAssets("assets/p2", cell, (150, 200, 255), (90, 160, 250), (90, 160, 250))


class FoodAssets:
    """Loads the optional food artwork."""

    def __init__(self, cell, folder="assets/food", default_color=DEFAULT_HEAD_COLOR):
        self.cell = cell
        self.default_color = default_color
        self._image = None
        self.reload(folder)

    def reload(self, folder="assets/food"):
        """Rescan the food folder and pick the first available image."""
        images_found = []
        base = Path(resource_path(folder))
        if base.is_dir():
            images_found = sorted(base.glob("*.png"))
        if not images_found:
            legacy = Path(resource_path("assets/food.png"))
            if legacy.is_file():
                images_found = [legacy]
        self._image = _load_scaled_cell(images_found[0], self.cell) if images_found else None
        return self._image

    def draw(self, screen, grid_pos):
        """Draw the food at a grid coordinate. Returns True if drawn."""
        x, y = grid_pos
        if self._image is not None:
            screen.blit(self._image, (x * self.cell, y * self.cell))
            return True
        pygame.draw.circle(
            screen, self.default_color,
            (x * self.cell + self.cell // 2, y * self.cell + self.cell // 2),
            self.cell // 2 - 2
        )
        return False


def _load_scaled_cell(path, cell):
    """Load an image, cropped and scaled to fill one square cell. None if missing."""
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
    return pygame.transform.smoothscale(raw, (cell, cell))


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