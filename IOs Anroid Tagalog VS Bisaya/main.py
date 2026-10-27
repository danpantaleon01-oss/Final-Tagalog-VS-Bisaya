import json
import os
import random
import sys
from pathlib import Path

import pygame
import images

WIDTH, HEIGHT = 1920, 1080
CELL = 40
FPS = int(images.content_value(["speed", "startFps"], 12))
FPS_CAP = int(images.content_value(["speed", "capFps"], 25))
RAMP_SCORE_PER_STEP = int(images.content_value(["speed", "rampScorePerStep"], 50))
if images.GAME_CONTENT:
    print(f"[Content] shared rules loaded: startFps={FPS} capFps={FPS_CAP} "
          f"rampEvery={RAMP_SCORE_PER_STEP} sway={images.SWAY_AMOUNT} "
          f"fill={images.PART_FILL_RATIO} frameCap={images.SNAKE_FRAME_CAP}")
else:
    print("[Content] shared/game_content.json missing — using fallback constants")
RENDER_FPS = 60  # M3: fixed render cadence — the arena redraws at this rate
                 # while the snake steps on an exact ms accumulator
def _per_user_file(name):
    """Per-user writable home for runtime state (scores.json, prefs.json).

    The game can be launched from a directory a normal user cannot write to
    (installed under C:\\Program Files, run from a mounted zip, a network
    share...). Writing state next to the executable there dies with
    PermissionError on first use. Prefer %LOCALAPPDATA%\\TagalogVsBisaya and
    fall back to the CWD (portable/dev runs, which can write).
    """
    base = os.environ.get("LOCALAPPDATA")
    if base:
        folder = Path(base) / "TagalogVsBisaya"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe = folder / ".write_test"
            probe.touch()
            probe.unlink()
            return folder / name
        except OSError:
            pass
    return Path(name)


def _scores_path():
    """Per-user writable home for the leaderboard."""
    return _per_user_file("scores.json")


SCORES_FILE = _scores_path()

# The board grid. Everything (movement, collision, food, drawing) derives its
# cell size from CELL, so the grid and the sprite cell can never drift apart.
COLS = WIDTH // CELL
ROWS = HEIGHT // CELL

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)

import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


SOUNDS_DIR = Path(resource_path("assets/audio"))

BG = (12, 13, 20)
BG_TOP = (26, 30, 53)
GRID = (255, 255, 255)
WHITE = (242, 243, 250)
GREEN = (63, 224, 127)
HEAD = (141, 255, 171)
RED = (255, 93, 93)
YELLOW = (255, 210, 70)
GRAY = (154, 160, 180)
BLUE = (90, 168, 255)
HEAD2 = (180, 215, 255)
PANEL = (16, 18, 30)
GOLD = (255, 210, 70)

def _find_sound(filename_stem):
    """Find a sound file by name, accepting common pygame mixer formats."""
    for ext in (".wav", ".ogg", ".mp3"):
        path = SOUNDS_DIR / f"{filename_stem}{ext}"
        if path.exists():
            return path
    return None


def load_sounds():
    """Load single-player and 2-player Tagalog/Bisaya sounds."""
    # Fixed effect stems, then every voice line the shared table lists
    # (VOICE_FILES already includes each team's classic blip).
    voice_stems = sorted({stem for stems in VOICE_FILES.values()
                          for stem in stems if stem})
    names = (
        "tagalog_eat", "tagalog_death", "tagalog_win",
        "bisaya_eat", "bisaya_death", "bisaya_win",
        *voice_stems,
    )
    sounds = {}
    for name in names:
        path = _find_sound(name)
        if path is None:
            sounds[name] = None
            print(f"[Audio] Missing: {SOUNDS_DIR / (name + '.wav/.ogg/.mp3')}")
            continue
        try:
            sounds[name] = pygame.mixer.Sound(str(path))
            sounds[name].set_volume(0.5)
            print(f"[Audio] Loaded: {path}")
        except pygame.error as exc:
            sounds[name] = None
            print(f"[Audio] Could not load {path}: {exc}")
    return sounds


def play_sound(sounds, name):
    if _muted:
        return
    sound = sounds.get(name) if sounds else None
    if sound is not None:
        sound.play()


# Voice-line rotation for rice eats. Single source: shared/game_content.json
# (web/game.js and flutter_app/lib/content.dart read the same file) — every
# bite plays ONE random sound from the team's full rotation (classic blip +
# voice lines) and the pop-up shows that sound's phrase, so text and audio
# always match. Desktop's table keeps the blip as the first entry.
VOICE_FILES = {}
VOICE_PHRASES = {}
for _team, _spec in images.GAME_CONTENT.get("voices", {}).items():
    if not isinstance(_spec, dict):
        continue
    _lines = [e for e in _spec.get("lines", []) if isinstance(e, dict)]
    _blip = _spec.get("blip", "")
    VOICE_FILES[_team] = ([_blip] if _blip else []) + [
        e.get("file", "") for e in _lines
    ]
    if _blip and _spec.get("blipPhrase"):
        VOICE_PHRASES[_blip] = _spec["blipPhrase"]
    for _entry in _lines:
        if _entry.get("file") and _entry.get("phrase"):
            VOICE_PHRASES[_entry["file"]] = _entry["phrase"]
# Crash protection mirrors: a mangled shared file must not silence the game.
VOICE_FILES.setdefault("tagalog", ["tagalog_eat", "tag-arman"])
VOICE_FILES.setdefault("bisaya", ["bisaya_eat", "bis-lami"])


def play_random_eat_sound(sounds, team):
    """Play one random eat sound from the team's rotation.

    Cuts any still-ringing eat sound first so phrases never overlap.
    Returns the phrase to pop up, or None when nothing is available.
    """
    if _muted:
        return None
    options = list(VOICE_FILES.get(team, ()))
    if not options or not sounds:
        return None
    pick = random.choice(options)
    try:
        last = sounds.get("_last_eat_channel")
        if last is not None:
            last.stop()
    except pygame.error:
        pass
    sound = sounds.get(pick)
    if sound is None:
        # A missing voice file must never silence a bite: fall back to blip.
        pick = "%s_eat" % team
        sound = sounds.get(pick)
    if sound is None:
        return None
    try:
        sounds["_last_eat_channel"] = sound.play()
    except pygame.error:
        pass
    return VOICE_PHRASES.get(pick)


LOBBY_MUSIC = Path(resource_path("assets/audio/bg_music_lobby.mp3"))


def lobby_music_start():
    """Play the lobby music on a loop. Falls back silently if the file or
    the mixer is unavailable."""
    if _muted:
        return
    if not pygame.mixer.get_init():
        return
    if not LOBBY_MUSIC.is_file():
        print(f"[Audio] Missing lobby music: {LOBBY_MUSIC}")
        return
    try:
        pygame.mixer.music.load(str(LOBBY_MUSIC))
        pygame.mixer.music.play(-1)  # -1 = loop forever
    except pygame.error as exc:
        print(f"[Audio] Could not play lobby music: {exc}")


def lobby_music_stop():
    """Stop the lobby music (fade out quickly so it doesn't cut abruptly)."""
    if pygame.mixer.get_init():
        pygame.mixer.music.fadeout(300)

# ── Sound mute (M key + HUD chip) ─────────────────────────────────────────
# Persisted in prefs.json alongside the player name so the choice survives
# restarts — mirroring the web (snake_prefs.muted) and mobile (snake_muted).

_muted = False


def set_muted(value):
    global _muted
    _muted = bool(value)


def toggle_muted():
    """Flip the mute preference and persist it. Returns the new state."""
    global _muted
    _muted = not _muted
    prefs = load_prefs()
    prefs["muted"] = _muted
    save_prefs(prefs)
    return _muted


def draw_mute_chip(screen, small):
    """Bottom-right chip shown only while sound is off."""
    chip = "MUTED  (M for sound)"
    draw_hud_chip(screen, small, chip,
                  (WIDTH - small.size(chip)[0] - 100, HEIGHT - 70), YELLOW)


def load_scores():
    data = _read_scores_file(SCORES_FILE)
    if data:
        return data
    # One-time migration: older builds kept the leaderboard next to the game
    # (CWD-relative). Adopt it so the player's history survives the move to
    # the per-user location.
    legacy = Path("scores.json")
    if legacy != SCORES_FILE and legacy.is_file():
        legacy_scores = _read_scores_file(legacy)
        if legacy_scores:
            save_scores(legacy_scores)
            return legacy_scores
    return []


def _read_scores_file(path):
    """Parse a leaderboard file. Missing/corrupt/unreadable = empty list."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, ValueError):
        # OSError covers FileNotFoundError + PermissionError on network or
        # locked-down installs; ValueError covers json.JSONDecodeError.
        return []


def save_scores(scores):
    """Never let a save failure kill a game-over screen (read-only CWD,
    full disk, removed device)."""
    try:
        with SCORES_FILE.open("w", encoding="utf-8") as f:
            json.dump(scores[:10], f, indent=2)
    except OSError as exc:
        print(f"[Scores] Could not save leaderboard: {exc}")


def add_score(scores, name, score):
    scores.append({"name": name[:12] or "Player", "score": score})
    scores.sort(key=lambda x: x["score"], reverse=True)
    save_scores(scores)


PREFS_FILE = _per_user_file("prefs.json")


def load_prefs():
    """Remembered QOL settings (player name, mute). Missing/corrupt = defaults."""
    try:
        with PREFS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_prefs(prefs):
    try:
        with PREFS_FILE.open("w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except OSError:
        pass


def best_score(scores):
    """Highest leaderboard score, or 0 when there are no scores yet."""
    if not scores:
        return 0
    try:
        return max(int(entry.get("score", 0)) for entry in scores)
    except (ValueError, TypeError, AttributeError):
        return 0


def draw_text(screen, font, text, pos, color=WHITE, center=False, shadow=True):
    rect = font.render(text, True, color).get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    if shadow:
        shade = font.render(text, True, (0, 0, 0))
        screen.blit(shade, rect.move(2, 2))
    screen.blit(font.render(text, True, color), rect)
    return rect


def draw_panel(screen, rect, radius=14, alpha=200):
    """Soft dark panel behind menus / HUD. Keeps custom bg images visible."""
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, (255, 255, 255, 28), panel.get_rect(), width=1, border_radius=radius)
    screen.blit(panel, rect.topleft)


def draw_hud_chip(screen, font, text, topleft, accent=GREEN):
    chip = font.render(text, True, WHITE)
    pad_x, pad_y = 20, 10
    rect = pygame.Rect(topleft[0], topleft[1],
                       chip.get_width() + pad_x * 2 + 14, chip.get_height() + pad_y * 2)
    bg = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(bg, (10, 12, 22, 190), bg.get_rect(), border_radius=999)
    pygame.draw.rect(bg, (255, 255, 255, 30), bg.get_rect(), width=1, border_radius=999)
    screen.blit(bg, rect.topleft)
    # accent dot
    pygame.draw.circle(screen, accent,
                       (rect.left + 20, rect.centery), 8)
    screen.blit(chip, (rect.left + 36, rect.top + pad_y))
    return rect


def random_food(snake):
    occupied = set(snake)
    free = [(x, y) for x in range(COLS) for y in range(ROWS)
            if (x, y) not in occupied]
    return random.choice(free) if free else None


def queue_turn(pending, committed, desired):
    """Direction to travel after `desired`, ignoring turns that are illegal.

    Two things are enforced:

    * Folding straight back on `committed` (the direction actually being
      travelled right now) is never allowed - that is the only turn that kills
      the snake, and it is rejected in single and two player mode alike.
    * Only one turn is taken per tick. Without this, two key presses inside the
      same tick chained into a 180 (up -> left -> down was accepted and drove
      the head into its own neck), because each press was compared against the
      previous queued turn instead of the direction on screen.
    """
    if pending != committed:
        return pending  # this tick already has a turn queued
    if desired not in (UP, DOWN, LEFT, RIGHT):
        return pending
    if desired == committed:
        return pending
    if desired == (-committed[0], -committed[1]):
        return pending
    return desired

_BG_CACHE = None
_MOTES = None

POPUP_WORDS = list(images.content_value(
    ["popup", "words"],
    ["SARAP!", "LAMI!", "YUMMY!", "NOM NOM!", "TAMIS!", "LAMON!", "+10",
     "SHEESH!"]))
_POPUP_FONT = None

def get_popup_font():
    global _POPUP_FONT
    if _POPUP_FONT is None:
        _POPUP_FONT = pygame.font.Font(None, 64)
    return _POPUP_FONT


def spawn_popup(popups, gx, gy, color=None, text=None):
    """Queue a Candy-Crush style floating word at grid cell (gx, gy).

    Pass `text` for a voice-line phrase (the pop-up shows exactly what is
    heard); otherwise a random word is picked as before.
    """
    import random as _r
    words = POPUP_WORDS
    text = text or words[_r.randrange(len(words))]
    # Assorted popup colors come from the shared rules too (one list on all
    # three platforms — desktop previously drifted at #ffaaaa / #aad7ff).
    _popup_hexes = images.content_value(["popup", "colors"], None)
    if isinstance(_popup_hexes, list) and _popup_hexes:
        try:
            palette = [tuple(int(str(h).lstrip("#")[i:i + 2], 16)
                             for i in (0, 2, 4)) for h in _popup_hexes]
        except ValueError:
            palette = [YELLOW, GREEN, WHITE, (255, 157, 157), (168, 212, 255)]
    else:
        palette = [YELLOW, GREEN, WHITE, (255, 157, 157), (168, 212, 255)]
    col = color if color is not None else palette[_r.randrange(len(palette))]
    font = get_popup_font()
    # dark outline baked under the text for readability on any bg
    base = font.render(text, True, col)
    outline = font.render(text, True, (0, 0, 0))
    popups.append({
        "x": gx * CELL + CELL // 2,
        "y": gy * CELL,
        "base": base, "outline": outline,
        "born": pygame.time.get_ticks(), "life": 950,
    })


def draw_popups(screen, popups, now=None):
    """Rise + pop-scale + fade floating eat words. Prunes expired in place."""
    import math
    if not popups:
        return
    if now is None:
        now = pygame.time.get_ticks()
    for p in popups[:]:
        age = now - p["born"]
        if age >= p["life"]:
            popups.remove(p)
            continue
        t = age / p["life"]
        rise = int(70 * t)
        scale = 1.0 + 0.6 * math.exp(-age / 130.0)
        alpha = 255 if t < 0.6 else int(255 * (1 - (t - 0.6) / 0.4))
        for key in ("outline", "base"):
            surf = p[key]
            w, h = surf.get_size()
            sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
            s = pygame.transform.smoothscale(surf, (sw, sh)) if (sw, sh) != (w, h) else surf.copy()
            s.set_alpha(alpha)
            # outline slightly larger behind base
            screen.blit(s, s.get_rect(center=(p["x"], p["y"] - rise)))


def _get_bg_surface():
    """Pre-rendered soft arena: gradient + glow + faint dots + vignette (no grid)."""
    global _BG_CACHE
    if _BG_CACHE is not None:
        return _BG_CACHE
    bg = pygame.Surface((WIDTH, HEIGHT)).convert()
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        r = int(BG_TOP[0] + (BG[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG[2] - BG_TOP[2]) * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))
    # soft center glow (layered translucent circles)
    glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cx, cy = WIDTH // 2, HEIGHT // 2
    for rad, a in ((560, 10), (440, 12), (320, 14)):
        pygame.draw.circle(glow, (90, 140, 255, a), (cx, cy), rad)
    for rad, a in ((420, 10), (300, 12)):
        pygame.draw.circle(glow, (63, 224, 127, a), (cx, cy), rad)
    bg.blit(glow, (0, 0))
    # faint dot lattice every 2 cells (calm, not a grid)
    dots = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for gy in range(0, HEIGHT // CELL + 1, 2):
        for gx in range(0, WIDTH // CELL + 1, 2):
            pygame.draw.circle(dots, (255, 255, 255, 16),
                               (gx * CELL, gy * CELL), 2)
    bg.blit(dots, (0, 0))
    # vignette: layered dark borders toward the edges
    vig = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    steps = 7
    for i in range(steps):
        a = 10 + i * 12
        inset = i * 46
        pygame.draw.rect(vig, (0, 0, 0, a),
                         (inset, inset, WIDTH - inset * 2, HEIGHT - inset * 2),
                         width=46, border_radius=28)
    bg.blit(vig, (0, 0))
    _BG_CACHE = bg
    return bg


def _get_motes():
    """Ambient floating dust/fireflies (normalized, wrap around screen)."""
    global _MOTES
    if _MOTES is not None:
        return _MOTES
    import random as _r
    tints = [(63, 224, 127), (90, 168, 255), (255, 210, 70)]
    motes = []
    for _ in range(45):
        motes.append({
            "x0": _r.random(), "y0": _r.random(),
            "vx": _r.uniform(-0.008, 0.012), "vy": _r.uniform(-0.010, 0.004),
            "r": _r.uniform(2.0, 4.5), "ph": _r.uniform(0, 6.28),
            "c": tints[_r.randrange(len(tints))],
        })
    _MOTES = motes
    return motes


def _draw_motes(screen, now):
    import math
    for m in _get_motes():
        t = now / 1000.0
        x = ((m["x0"] + m["vx"] * t) % 1.0) * WIDTH
        y = ((m["y0"] + m["vy"] * t) % 1.0) * HEIGHT
        tw = 0.5 + 0.5 * math.sin(t * 1.6 + m["ph"])
        a = int(26 + 54 * tw)
        rad = m["r"] * (0.8 + 0.4 * tw)
        halo = pygame.Surface((int(rad * 4), int(rad * 4)), pygame.SRCALPHA)
        c = m["c"]
        pygame.draw.circle(halo, (*c, a), (rad * 2, rad * 2), int(rad))
        screen.blit(halo, (x - rad * 2, y - rad * 2))


def draw_board(screen, ui=None, accent=GREEN):
    """Draw the game background (custom image if provided, else soft arena)."""
    if ui is not None and not ui.draw_background(screen):
        # dim custom artwork slightly so HUD chips stay readable
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 10, 18, 70))
        screen.blit(dim, (0, 0))
    else:
        screen.blit(_get_bg_surface(), (0, 0))
    _draw_motes(screen, pygame.time.get_ticks())
    # arena frame with accent glow
    pygame.draw.rect(screen, accent, (2, 2, WIDTH - 4, HEIGHT - 4), width=3, border_radius=14)


def draw_snake(screen, snake, assets, variants=None):
    """Draw a snake using its custom image assets (falls back to rectangles)."""
    images.draw_image_snake(screen, snake, assets, variants=variants)


def draw_food(screen, food, food_assets=None, time_ms=None):
    if time_ms is None:
        try:
            time_ms = pygame.time.get_ticks()
        except Exception:
            time_ms = 0
    if food:
        if food_assets is not None:
            # soft glow behind custom sprite so it pops on any background
            cx, cy = food[0] * CELL + CELL // 2, food[1] * CELL + CELL // 2
            glow = pygame.Surface((CELL * 2, CELL * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 90, 90, 60), (CELL, CELL), CELL - 1)
            screen.blit(glow, (cx - CELL, cy - CELL))
            food_assets.draw(screen, food, time_ms)
            return
        cx, cy = food[0] * CELL + CELL // 2, food[1] * CELL + CELL // 2
        pygame.draw.circle(screen, RED, (cx, cy), CELL // 2 - 2)
        pygame.draw.circle(screen, (255, 255, 255), (cx - 4, cy - 4), 3)

def get_name(screen, fonts, prompt="ENTER YOUR NAME", default="Player", ui=None):
    font, small = fonts
    name = default
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return name.strip() or default
                if event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.unicode.isprintable() and len(name) < 12:
                    name += event.unicode

        draw_board(screen, ui)
        draw_panel(screen, pygame.Rect(WIDTH // 2 - 560, 300, 1120, 420), radius=24)
        draw_text(screen, font, prompt, (WIDTH // 2, 380), YELLOW, True)
        draw_text(screen, font, name + "_", (WIDTH // 2, 520), WHITE, True)
        draw_text(screen, small, "Press ENTER to continue", (WIDTH // 2, 630), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


def leaderboard_screen(screen, fonts, scores, ui=None):
    font, small = fonts
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                return

        draw_board(screen, ui)
        draw_panel(screen, pygame.Rect(WIDTH // 2 - 520, 70, 1040, 880), radius=24)
        draw_text(screen, font, "LEADERBOARD", (WIDTH // 2, 125), YELLOW, True)
        draw_text(screen, small, "TOP 10 • THIS DEVICE", (WIDTH // 2, 190), GRAY, True)

        if not scores:
            draw_text(screen, small, "No scores yet.", (WIDTH // 2, 320), GRAY, True)
        else:
            for i, entry in enumerate(scores[:10]):
                y = 260 + i * 66
                row = pygame.Rect(WIDTH // 2 - 440, y - 12, 880, 56)
                if i == 0:
                    draw_panel(screen, row, radius=12, alpha=110)
                color = GOLD if i == 0 else WHITE
                medal = "★ " if i == 0 else ""
                draw_text(screen, small, f"{i + 1:>2}. {medal}{entry['name']:<12}", (640, y), color)
                draw_text(screen, small, str(entry["score"]), (1280, y), color)

        draw_text(screen, small, "Press ENTER or ESC to return", (WIDTH // 2, 990), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


def pause_menu(screen, fonts):
    """Freeze-frame pause overlay. Returns True to resume, False to quit the run.

    The current frame is captured before entering so the board stays visible
    behind the panel instead of being redrawn empty.
    """
    font, small = fonts
    clock = pygame.time.Clock()
    frozen = screen.copy()
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((8, 10, 18, 130))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False

        screen.blit(frozen, (0, 0))
        screen.blit(dim, (0, 0))
        draw_panel(screen, pygame.Rect(WIDTH // 2 - 460, 360, 920, 340), radius=24)
        draw_text(screen, font, "PAUSED", (WIDTH // 2, 450), YELLOW, True)
        draw_text(screen, small, "P / ENTER to resume • ESC to quit", (WIDTH // 2, 620), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


def game(screen, fonts, player, assets, sounds, ui=None, food_assets=None, best=0,
         team="tagalog"):
    font, small = fonts
    clock = pygame.time.Clock()

    snake = [(10, 10), (9, 10), (8, 10)]
    direction = RIGHT
    next_direction = direction
    variants = [0, 0, 0]  # per-segment look ids, kept parallel to `snake`
    food = random_food(snake)
    score = 0
    speed = FPS
    popups = []
    # M3: fixed-cadence rendering + ms-accumulator stepping.
    step_ms = 1000.0 / speed
    acc = 0.0
    last_ms = pygame.time.get_ticks()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.WINDOWFOCUSLOST:
                if not pause_menu(screen, fonts):
                    return score, False, False
                # The pause was one long frame for the accumulator; the
                # paused time must not replay as a burst of steps.
                last_ms = pygame.time.get_ticks()
                acc = 0.0

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    next_direction = queue_turn(next_direction, direction, UP)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    next_direction = queue_turn(next_direction, direction, DOWN)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    next_direction = queue_turn(next_direction, direction, LEFT)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    next_direction = queue_turn(next_direction, direction, RIGHT)
                elif event.key == pygame.K_p:
                    if not pause_menu(screen, fonts):
                        return score, False, False
                    last_ms = pygame.time.get_ticks()
                    acc = 0.0
                elif event.key == pygame.K_ESCAPE:
                    if not pause_menu(screen, fonts):
                        return score, False, False
                    last_ms = pygame.time.get_ticks()
                    acc = 0.0
                elif event.key == pygame.K_m:
                    toggle_muted()

        # ── Simulation on a ms accumulator (M3) ──
        # The step cadence is exact and independent of monitor refresh; the
        # arena is then redrawn every frame at RENDER_FPS so sway, motes, the
        # food pulse and popups animate continuously instead of jumping in
        # snake-fps chunks (web/Flutter already render this way).
        now = pygame.time.get_ticks()
        acc += now - last_ms
        last_ms = now
        acc = min(acc, step_ms * 4.0)  # long stalls never fast-forward steps

        while acc >= step_ms:
            acc -= step_ms
            direction = next_direction
            hx, hy = snake[0]
            nx, ny = hx + direction[0], hy + direction[1]

            new_head = (nx, ny)
            # The tail cell is vacated on this tick unless the snake is eating, so
            # it must not count as a wall for the head.
            will_eat = new_head == food
            hit_wall = not (0 <= nx < COLS and 0 <= ny < ROWS)
            body_to_check = snake if will_eat else snake[:-1]
            hit_self = new_head in body_to_check

            if hit_wall or hit_self:
                play_sound(sounds, f"{team}_death")
                return score, True, False

            snake.insert(0, new_head)

            if will_eat:
                phrase = play_random_eat_sound(sounds, "tagalog")
                variants.insert(0, random.randrange(1 << 30))
                spawn_popup(popups, new_head[0], new_head[1],
                            GREEN if phrase else None, phrase)
                score += 10
                speed = min(FPS_CAP, FPS + score // RAMP_SCORE_PER_STEP)
                step_ms = 1000.0 / speed
                food = random_food(snake)
                if food is None:
                    # Every cell of the board is a snake segment: the run is
                    # CLEARED. That is a victory, not a death.
                    play_sound(sounds, f"{team}_win")
                    return score, False, True
            else:
                snake.pop()
            # Self-healing: the variant list must track the snake 1:1. Repair any
            # disagreement instead of crashing (never let pop() see an empty list).
            while len(variants) > len(snake):
                variants.pop()
            while len(variants) < len(snake):
                variants.insert(0, 0)

        # ── Render every frame (decoupled from steps) ──
        draw_board(screen, ui)
        draw_food(screen, food, food_assets)
        draw_snake(screen, snake, assets, variants)
        draw_popups(screen, popups)
        draw_hud_chip(screen, small, f"{player}", (16, 14), GREEN)
        score_chip = f"Score: {score}"
        w = small.size(score_chip)[0] + 84
        draw_hud_chip(screen, small, score_chip, (WIDTH - w - 16, 14), YELLOW)
        best_chip = f"Best: {max(best, score)}"
        bw = small.size(best_chip)[0] + 84
        draw_hud_chip(screen, small, best_chip, ((WIDTH - bw) // 2, 14), BLUE)
        if _muted:
            draw_mute_chip(screen, small)
        pygame.display.flip()
        clock.tick(RENDER_FPS)


def two_player_game(screen, fonts, name1, name2, assets_p1, assets_p2, sounds, ui=None, food_assets=None, best=0):
    """Local 2-player mode. P1 = Arrow keys, P2 = WASD. Shared board, shared food."""
    font, small = fonts
    clock = pygame.time.Clock()

    cells_x, cells_y = COLS, ROWS

    p1 = {
        "snake": [(6, 10), (5, 10), (4, 10)],
        "variants": [0, 0, 0],
        "dir": RIGHT,
        "next_dir": RIGHT,
        "alive": True,
        "score": 0,
        "name": name1,
    }
    p2 = {
        "snake": [(cells_x - 7, 14), (cells_x - 6, 14), (cells_x - 5, 14)],
        "variants": [0, 0, 0],
        "dir": LEFT,
        "next_dir": LEFT,
        "alive": True,
        "score": 0,
        "name": name2,
    }

    occupied = set(p1["snake"]) | set(p2["snake"])
    food = random_food(occupied)
    speed = FPS
    popups = []
    # M3: fixed-cadence rendering + ms-accumulator stepping (see game()).
    step_ms = 1000.0 / speed
    acc = 0.0
    last_ms = pygame.time.get_ticks()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.WINDOWFOCUSLOST:
                if not pause_menu(screen, fonts):
                    return p1, p2
                # The pause was one long frame for the accumulator; the
                # paused time must not replay as a burst of steps.
                last_ms = pygame.time.get_ticks()
                acc = 0.0

            if event.type == pygame.KEYDOWN:
                # Player 1: arrow keys
                if event.key == pygame.K_UP:
                    p1["next_dir"] = queue_turn(p1["next_dir"], p1["dir"], UP)
                elif event.key == pygame.K_DOWN:
                    p1["next_dir"] = queue_turn(p1["next_dir"], p1["dir"], DOWN)
                elif event.key == pygame.K_LEFT:
                    p1["next_dir"] = queue_turn(p1["next_dir"], p1["dir"], LEFT)
                elif event.key == pygame.K_RIGHT:
                    p1["next_dir"] = queue_turn(p1["next_dir"], p1["dir"], RIGHT)
                # Player 2: WASD
                elif event.key == pygame.K_w:
                    p2["next_dir"] = queue_turn(p2["next_dir"], p2["dir"], UP)
                elif event.key == pygame.K_s:
                    p2["next_dir"] = queue_turn(p2["next_dir"], p2["dir"], DOWN)
                elif event.key == pygame.K_a:
                    p2["next_dir"] = queue_turn(p2["next_dir"], p2["dir"], LEFT)
                elif event.key == pygame.K_d:
                    p2["next_dir"] = queue_turn(p2["next_dir"], p2["dir"], RIGHT)
                elif event.key == pygame.K_p:
                    if not pause_menu(screen, fonts):
                        return p1, p2
                    last_ms = pygame.time.get_ticks()
                    acc = 0.0
                elif event.key == pygame.K_ESCAPE:
                    if not pause_menu(screen, fonts):
                        return p1, p2
                    last_ms = pygame.time.get_ticks()
                    acc = 0.0
                elif event.key == pygame.K_m:
                    toggle_muted()

        # ── Simulation on a ms accumulator (M3, see game()) ──
        now = pygame.time.get_ticks()
        acc += now - last_ms
        last_ms = now
        acc = min(acc, step_ms * 4.0)  # long stalls never fast-forward steps

        while acc >= step_ms:
            acc -= step_ms
            for p in (p1, p2):
                if p["alive"]:
                    p["dir"] = p["next_dir"]

            was_alive_p1 = p1["alive"]
            was_alive_p2 = p2["alive"]

            new_heads = {}
            for tag, p in (("p1", p1), ("p2", p2)):
                if not p["alive"]:
                    continue
                hx, hy = p["snake"][0]
                dx, dy = p["dir"]
                new_heads[tag] = (hx + dx, hy + dy)

            will_eat = {tag: (head == food) for tag, head in new_heads.items()}
            bodies_after_move = {
                tag: (p1 if tag == "p1" else p2)["snake"][:-1] if not will_eat[tag]
                else (p1 if tag == "p1" else p2)["snake"]
                for tag in new_heads
            }

            killed_by = {"p1": False, "p2": False}
            head_on_collision = False

            for tag, head in new_heads.items():
                p = p1 if tag == "p1" else p2
                nx, ny = head
                hit_wall = nx < 0 or nx >= cells_x or ny < 0 or ny >= cells_y
                other_tag = "p2" if tag == "p1" else "p1"
                other = p2 if tag == "p1" else p1
                hit_self = head in bodies_after_move[tag]
                hit_other = other["alive"] and head in bodies_after_move.get(other_tag, other["snake"])
                head_on = other["alive"] and other_tag in new_heads and new_heads[other_tag] == head

                if hit_wall or hit_self or hit_other or head_on:
                    p["alive"] = False

                if hit_other and not head_on:
                    other["alive"] = False
                    killed_by[other_tag] = True

                if head_on:
                    head_on_collision = True

            p1_died_now = was_alive_p1 and not p1["alive"]
            p2_died_now = was_alive_p2 and not p2["alive"]

            if head_on_collision:
                if p1_died_now:
                    play_sound(sounds, "tagalog_death")
                if p2_died_now:
                    play_sound(sounds, "bisaya_death")
            else:
                p1_death_suppressed = killed_by["p2"]
                p2_death_suppressed = killed_by["p1"]

                if p1_died_now and not p1_death_suppressed:
                    play_sound(sounds, "tagalog_death")
                if p2_died_now and not p2_death_suppressed:
                    play_sound(sounds, "bisaya_death")

            for tag, head in new_heads.items():
                p = p1 if tag == "p1" else p2
                if not p["alive"]:
                    continue
                p["snake"].insert(0, head)
                if will_eat[tag]:
                    p["variants"].insert(0, random.randrange(1 << 30))
                    if tag == "p1":
                        phrase = play_random_eat_sound(sounds, "tagalog")
                        spawn_popup(popups, head[0], head[1], GREEN, phrase)
                    else:
                        phrase = play_random_eat_sound(sounds, "bisaya")
                        spawn_popup(popups, head[0], head[1], BLUE, phrase)
                    p["score"] += 10
                    food = random_food(set(p1["snake"]) | set(p2["snake"]))
                    if food is None:
                        p1["alive"] = p2["alive"] = False
                else:
                    p["snake"].pop()
                # Self-healing: variant list must track the snake 1:1 (see game()).
                while len(p["variants"]) > len(p["snake"]):
                    p["variants"].pop()
                while len(p["variants"]) < len(p["snake"]):
                    p["variants"].insert(0, 0)

            speed = min(FPS_CAP,
                        FPS + (max(p1["score"], p2["score"])
                               // RAMP_SCORE_PER_STEP))
            step_ms = 1000.0 / speed
            if not p1["alive"] or not p2["alive"]:
                return p1, p2

        # ── Render every frame (decoupled from steps) ──
        draw_board(screen, ui, GREEN if p1["score"] >= p2["score"] else BLUE)
        draw_food(screen, food, food_assets)
        if p1["alive"]:
            draw_snake(screen, p1["snake"], assets_p1, p1["variants"])
        if p2["alive"]:
            draw_snake(screen, p2["snake"], assets_p2, p2["variants"])
        draw_popups(screen, popups)
        draw_hud_chip(screen, small, f"{p1['name']}: {p1['score']}", (16, 14), GREEN)
        right = f"{p2['name']}: {p2['score']}"
        draw_hud_chip(screen, small, right, (WIDTH - small.size(right)[0] - 100, 14), BLUE)
        best_chip = f"Best: {max(best, p1['score'], p2['score'])}"
        bw = small.size(best_chip)[0] + 84
        draw_hud_chip(screen, small, best_chip, ((WIDTH - bw) // 2, 14), GRAY)
        if _muted:
            draw_mute_chip(screen, small)
        if not p1["alive"]:
            draw_text(screen, small, f"{p1['name']} is out!", (WIDTH // 2, 14), RED, True)
        if not p2["alive"]:
            draw_text(screen, small, f"{p2['name']} is out!", (WIDTH // 2, 14), RED, True)
        pygame.display.flip()
        clock.tick(RENDER_FPS)


def two_player_game_over_screen(screen, fonts, p1, p2, ui=None, sounds=None):
    font, small = fonts
    clock = pygame.time.Clock()

    if p1["alive"] and not p2["alive"]:
        winner = p1
        result = f"{p1['name']} WINS!"
        color = GREEN
        play_sound(sounds, "tagalog_win")
    elif p2["alive"] and not p1["alive"]:
        winner = p2
        result = f"{p2['name']} WINS!"
        color = BLUE
        play_sound(sounds, "bisaya_win")
    elif p1["score"] > p2["score"]:
        winner = p1
        result = f"{p1['name']} WINS!"
        color = GREEN
        play_sound(sounds, "tagalog_win")
    elif p2["score"] > p1["score"]:
        winner = p2
        result = f"{p2['name']} WINS!"
        color = BLUE
        play_sound(sounds, "bisaya_win")
    else:
        result = "IT'S A TIE!"
        color = YELLOW
        winner = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    return False

        draw_board(screen, ui)
        draw_panel(screen, pygame.Rect(WIDTH // 2 - 560, 200, 1120, 600), radius=24)
        draw_text(screen, font, "GAME OVER", (WIDTH // 2, 270), RED, True)
        draw_text(screen, font, result, (WIDTH // 2, 390), color, True)
        if winner is not None:
            draw_text(screen, small, f"★ {winner['name']} score: {winner['score']}",
                      (WIDTH // 2, 500), WHITE, True)
        else:
            draw_text(screen, small, f"Tied score: {p1['score']}", (WIDTH // 2, 500), WHITE, True)
        draw_text(screen, small, f"{p1['name']}: {p1['score']}", (WIDTH // 2, 585), GREEN, True)
        draw_text(screen, small, f"{p2['name']}: {p2['score']}", (WIDTH // 2, 635), BLUE, True)
        draw_text(screen, small, "R for rematch • ENTER for menu", (WIDTH // 2, 745), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


def game_over_screen(screen, fonts, score, ui=None, new_best=False, won=False):
    """Result panel. Returns True for instant rematch (R), False for menu.

    A cleared board arrives with won=True and gets the gold YOU WIN
    treatment (plus the win sound, played at the moment of clearing)."""
    font, small = fonts
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    return False

        draw_board(screen, ui)
        draw_panel(screen, pygame.Rect(WIDTH // 2 - 520, 300, 1040, 420), radius=24)
        hint_y = 655
        if won:
            draw_text(screen, font, "YOU WIN", (WIDTH // 2, 395), YELLOW, True)
            draw_text(screen, small, "BOARD CLEARED!", (WIDTH // 2, 448), WHITE, True)
        else:
            draw_text(screen, font, "GAME OVER", (WIDTH // 2, 395), RED, True)
        draw_text(screen, font, f"★ Score: {score}", (WIDTH // 2, 522 if won else 505), WHITE, True)
        if new_best:
            if won:
                hint_y = 675
                draw_text(screen, small, "★ NEW BEST! ★", (WIDTH // 2, 612), YELLOW, True)
            else:
                draw_text(screen, small, "★ NEW BEST! ★", (WIDTH // 2, 585), YELLOW, True)
        draw_text(screen, small, "R to play again • ENTER for menu", (WIDTH // 2, hint_y), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


_fullscreen = True


def toggle_fullscreen(screen):
    """Switch between fullscreen and a windowed 1920x1080.

    Returns the NEW display surface. Call sites must reassign their `screen`
    with it: set_mode() invalidates the old surface, so keeping the stale
    one froze the game (everything kept blitting to a dead surface).
    """
    global _fullscreen
    _fullscreen = not _fullscreen
    if _fullscreen:
        return pygame.display.set_mode((WIDTH, HEIGHT),
                                       pygame.FULLSCREEN | pygame.SCALED)
    return pygame.display.set_mode((WIDTH, HEIGHT))


def main():
    # Low-latency mixer defaults, set before pygame.init() spins everything up.
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    
    icon_path = Path(resource_path("assets/icon.png"))
    if icon_path.is_file():
        game_icon = pygame.image.load(str(icon_path))
        pygame.display.set_icon(game_icon)

    # No audio output device must not mean "no game": every sound loader and
    # play call already degrades to a no-op when the mixer is unavailable.
    try:
        pygame.mixer.init()
    except pygame.error as exc:
        print(f"[Audio] mixer init failed — running without sound: {exc}")
    sounds = load_sounds()
    pygame.display.set_caption("Esneyk Geym")
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    font = pygame.font.Font(None, 110)
    small = pygame.font.Font(None, 54)
    fonts = (font, small)

    scores = load_scores()
    prefs = load_prefs()
    set_muted(prefs.get("muted") is True)

    assets_p1, assets_p2 = images.make_default_assets(CELL)
    ui = images.UIAssets((WIDTH, HEIGHT))
    food_assets = images.FoodAssets(CELL)

    while True:
        lobby_music_start()
        menu_items = ["1 PLAYER", "2 PLAYER", "LEADERBOARD", "EXIT"]
        button_labels = ["1_player", "2_player", "leaderboard", "exit"]
        selected = 0
        clock = pygame.time.Clock()
        menu_start, menu_spacing = 390, 112
        button_rects = [
            pygame.Rect(0, 0, 560, 96).move(WIDTH // 2 - 280, menu_start + i * menu_spacing - 48)
            for i in range(len(menu_items))
        ]

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.MOUSEMOTION:
                    for i, rect in enumerate(button_rects):
                        if rect.collidepoint(event.pos):
                            selected = i
                            break
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(button_rects):
                        if rect.collidepoint(event.pos):
                            selected = i
                            break
                    else:
                        break
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        screen = toggle_fullscreen(screen)
                    elif event.key == pygame.K_m:
                        if toggle_muted():
                            lobby_music_start()  # menu is on-screen: safe to start
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(menu_items)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(menu_items)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        break
            else:
                draw_board(screen, ui)
                draw_panel(screen, pygame.Rect(WIDTH // 2 - 540, 70, 1080, 900), alpha=215, radius=24)
                if not ui.draw_logo(screen, (WIDTH // 2, 220)):
                    draw_text(screen, font, "SNAKE VERSUS", (WIDTH // 2, 220), GREEN, True)
                draw_text(screen, small, "TAGALOG  ★  VS  ★  BISAYA", (WIDTH // 2, 290), GRAY, True)
                for i, item in enumerate(menu_items):
                    pos = (WIDTH // 2, menu_start + i * menu_spacing)
                    if not ui.draw_button(screen, button_labels[i], pos, i == selected):
                        chip = pygame.Rect(0, 0, 560, 90)
                        chip.center = pos
                        bg_col = (46, 160, 90, 230) if i == selected else (24, 27, 44, 230)
                        pygame.draw.rect(screen, bg_col, chip, border_radius=18)
                        pygame.draw.rect(screen,
                                         YELLOW if i == selected else (255, 255, 255, 40),
                                         chip, width=3 if i == selected else 1, border_radius=18)
                        marker = "▶ " if i == selected else ""
                        color = (255, 255, 255) if i != selected else YELLOW
                        draw_text(screen, font, marker + item, pos, color, True)
                draw_text(screen, small, "Arrows / WASD to navigate • ENTER to select • mouse OK • F11 fullscreen • P pauses • M mutes",
                          (WIDTH // 2, 990), GRAY, True)
                if _muted:
                    draw_mute_chip(screen, small)
                pygame.display.flip()
                clock.tick(30)
                continue

            choice = menu_items[selected]
            break

        if choice == "EXIT":
            pygame.quit()
            return
        if choice == "LEADERBOARD":
            leaderboard_screen(screen, fonts, scores, ui)
            continue

        if choice == "2 PLAYER":
            lobby_music_stop()
            name1 = get_name(screen, fonts, "PLAYER 1 (ARROWS) - ENTER NAME",
                             prefs.get("name") or "Player 1", ui)
            name2 = get_name(screen, fonts, "PLAYER 2 (WASD) - ENTER NAME", "Player 2", ui)
            while True:
                match_best = best_score(scores)
                p1, p2 = two_player_game(screen, fonts, name1, name2, assets_p1, assets_p2,
                                         sounds, ui, food_assets, match_best)

                # ONE row per match: the winner only; a tie records nothing.
                # Both players used to be written separately, so every match
                # flooded the device leaderboard with up to two rows.
                winner = None
                if p1["score"] > p2["score"]:
                    winner = p1
                elif p2["score"] > p1["score"]:
                    winner = p2
                if winner is not None and winner["score"] > 0:
                    add_score(scores, winner["name"], winner["score"])
                    scores = load_scores()

                if not two_player_game_over_screen(screen, fonts, p1, p2, ui, sounds):
                    break
            continue

        player = get_name(screen, fonts, ui=ui, default=prefs.get("name") or "Player")
        if player != prefs.get("name"):
            prefs["name"] = player
            save_prefs(prefs)
        while True:
            prev_best = best_score(scores)
            lobby_music_stop()
            score, died, won = game(screen, fonts, player, assets_p1, sounds,
                                    ui, food_assets, prev_best)

            is_best = score > 0 and score > prev_best
            if score > 0:
                add_score(scores, player, score)
                scores = load_scores()

            if died or won:
                if game_over_screen(screen, fonts, score, ui, is_best, won=won):
                    continue
            break


if __name__ == "__main__":
    main()
