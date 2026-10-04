import json
import random
import sys
from pathlib import Path

import pygame
import os
import sys 
import images

WIDTH, HEIGHT = 800, 600
CELL = 20
FPS = 12
SCORES_FILE = Path("scores.json")

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

# ─── UPDATE YOUR PATHS USING THE FUNCTION ABOVE ───
# Example for your music and asset folders:
music_file = resource_path("music.mp3")
scores_file = resource_path("scores.json")
# If loading an image inside assets:
icon_file = resource_path(os.path.join("assets", "icon.png"))


SOUNDS_DIR = Path(resource_path("assets/audio"))

BG = (18, 18, 24)
GRID = (30, 30, 38)
WHITE = (240, 240, 245)
GREEN = (80, 220, 120)
HEAD = (120, 255, 150)
RED = (245, 80, 80)
YELLOW = (255, 210, 70)
GRAY = (150, 150, 160)
BLUE = (90, 160, 250)
HEAD2 = (150, 200, 255)

def _find_sound(filename_stem):
    """Find a sound file by name, accepting common pygame mixer formats."""
    for ext in (".wav", ".ogg", ".mp3"):
        path = SOUNDS_DIR / f"{filename_stem}{ext}"
        if path.exists():
            return path
    return None


def load_sounds():
    """Load single-player and 2-player Tagalog/Bisaya sounds."""
    names = (
        "tagalog_eat", "tagalog_death", "tagalog_win",
        "bisaya_eat", "bisaya_death", "bisaya_win",
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
    sound = sounds.get(name) if sounds else None
    if sound is not None:
        sound.play()


LOBBY_MUSIC = Path(resource_path("assets/audio/bg_music_lobby.mp3"))


def lobby_music_start():
    """Play the lobby music on a loop. Falls back silently if the file or
    the mixer is unavailable."""
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

def load_scores():
    try:
        with SCORES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_scores(scores):
    with SCORES_FILE.open("w", encoding="utf-8") as f:
        json.dump(scores[:10], f, indent=2)


def add_score(scores, name, score):
    scores.append({"name": name[:12] or "Player", "score": score})
    scores.sort(key=lambda x: x["score"], reverse=True)
    save_scores(scores)


def draw_text(screen, font, text, pos, color=WHITE, center=False):
    surface = font.render(text, True, color)
    rect = surface.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    screen.blit(surface, rect)


def random_food(snake):
    cells_x = WIDTH // CELL
    cells_y = HEIGHT // CELL
    free = [(x, y) for x in range(cells_x) for y in range(cells_y)
            if (x, y) not in snake]
    return random.choice(free) if free else None

def draw_board(screen, ui=None):
    """Draw the game background (custom image if provided, else grid)."""
    if ui is not None and not ui.draw_background(screen):
        return
    screen.fill(BG)
    for x in range(0, WIDTH, CELL):
        pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL):
        pygame.draw.line(screen, GRID, (0, y), (WIDTH, y))


def draw_snake(screen, snake, assets):
    """Draw a snake using its custom image assets (falls back to rectangles)."""
    images.draw_image_snake(screen, snake, assets)


def draw_food(screen, food, food_assets=None):
    if food:
        if food_assets is not None:
            food_assets.draw(screen, food)
            return
        x, y = food
        pygame.draw.circle(
            screen, RED,
            (x * CELL + CELL // 2, y * CELL + CELL // 2),
            CELL // 2 - 2
        )

def get_name(screen, fonts, prompt="ENTER YOUR NAME", default="Player", ui=None):
    font, small = fonts
    name = ""
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

        if ui is None or ui.draw_background(screen):
            screen.fill(BG)
        draw_text(screen, font, prompt, (WIDTH // 2, 210), YELLOW, True)
        draw_text(screen, font, name + "_", (WIDTH // 2, 290), WHITE, True)
        draw_text(screen, small, "Press ENTER to continue", (WIDTH // 2, 350), GRAY, True)
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

        if ui is None or ui.draw_background(screen):
            screen.fill(BG)
        draw_text(screen, font, "LEADERBOARD", (WIDTH // 2, 70), YELLOW, True)

        if not scores:
            draw_text(screen, small, "No scores yet.", (WIDTH // 2, 180), GRAY, True)
        else:
            for i, entry in enumerate(scores[:10]):
                y = 135 + i * 38
                draw_text(screen, small, f"{i + 1:>2}. {entry['name']:<12}", (250, y))
                draw_text(screen, small, str(entry["score"]), (550, y))

        draw_text(screen, small, "Press ENTER or ESC to return", (WIDTH // 2, 550), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


def game(screen, fonts, player, assets, sounds, ui=None, food_assets=None):
    font, small = fonts
    clock = pygame.time.Clock()

    snake = [(10, 10), (9, 10), (8, 10)]
    direction = (1, 0)
    next_direction = direction
    food = random_food(snake)
    score = 0
    speed = FPS

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w) and direction != (0, 1):
                    next_direction = (0, -1)
                elif event.key in (pygame.K_DOWN, pygame.K_s) and direction != (0, -1):
                    next_direction = (0, 1)
                elif event.key in (pygame.K_LEFT, pygame.K_a) and direction != (1, 0):
                    next_direction = (-1, 0)
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and direction != (-1, 0):
                    next_direction = (1, 0)
                elif event.key == pygame.K_ESCAPE:
                    return score, False

        direction = next_direction
        hx, hy = snake[0]
        nx, ny = hx + direction[0], hy + direction[1]

        hit_wall = nx < 0 or nx >= WIDTH // CELL or ny < 0 or ny >= HEIGHT // CELL
        new_head = (nx, ny)
        will_eat = new_head == food
        body_to_check = snake if will_eat else snake[:-1]
        hit_self = new_head in body_to_check

        if hit_wall or hit_self:
            play_sound(sounds, "tagalog_death")
            return score, True

        snake.insert(0, new_head)

        if will_eat:
            play_sound(sounds, "tagalog_eat")
            score += 10
            speed = min(25, FPS + score // 50)
            food = random_food(snake)
            if food is None:
                return score, True
        else:
            snake.pop()

        draw_board(screen, ui)
        draw_food(screen, food, food_assets)
        draw_snake(screen, snake, assets)
        draw_text(screen, small, f"Player: {player}", (10, 8))
        draw_text(screen, small, f"Score: {score}", (WIDTH - 150, 8))
        pygame.display.flip()
        clock.tick(speed)


def two_player_game(screen, fonts, name1, name2, assets_p1, assets_p2, sounds, ui=None, food_assets=None):
    """Local 2-player mode. P1 = Arrow keys, P2 = WASD. Shared board, shared food."""
    font, small = fonts
    clock = pygame.time.Clock()

    cells_x = WIDTH // CELL
    cells_y = HEIGHT // CELL

    p1 = {
        "snake": [(6, 10), (5, 10), (4, 10)],
        "dir": (1, 0),
        "next_dir": (1, 0),
        "alive": True,
        "score": 0,
        "name": name1,
    }
    p2 = {
        "snake": [(cells_x - 7, 14), (cells_x - 6, 14), (cells_x - 5, 14)],
        "dir": (-1, 0),
        "next_dir": (-1, 0),
        "alive": True,
        "score": 0,
        "name": name2,
    }

    occupied = set(p1["snake"]) | set(p2["snake"])
    food = random_food(occupied)
    speed = FPS

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Player 1: arrow keys
                if event.key == pygame.K_UP and p1["dir"] != (0, 1):
                    p1["next_dir"] = (0, -1)
                elif event.key == pygame.K_DOWN and p1["dir"] != (0, -1):
                    p1["next_dir"] = (0, 1)
                elif event.key == pygame.K_LEFT and p1["dir"] != (1, 0):
                    p1["next_dir"] = (-1, 0)
                elif event.key == pygame.K_RIGHT and p1["dir"] != (-1, 0):
                    p1["next_dir"] = (1, 0)
                # Player 2: WASD
                elif event.key == pygame.K_w and p2["dir"] != (0, 1):
                    p2["next_dir"] = (0, -1)
                elif event.key == pygame.K_s and p2["dir"] != (0, -1):
                    p2["next_dir"] = (0, 1)
                elif event.key == pygame.K_a and p2["dir"] != (1, 0):
                    p2["next_dir"] = (-1, 0)
                elif event.key == pygame.K_d and p2["dir"] != (-1, 0):
                    p2["next_dir"] = (1, 0)
                elif event.key == pygame.K_ESCAPE:
                    return p1, p2

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
                if tag == "p1":
                    play_sound(sounds, "tagalog_eat")
                else:
                    play_sound(sounds, "bisaya_eat")
                p["score"] += 10
                food = random_food(set(p1["snake"]) | set(p2["snake"]))
                if food is None:
                    p1["alive"] = p2["alive"] = False
            else:
                p["snake"].pop()

        speed = min(25, FPS + (max(p1["score"], p2["score"]) // 50))

        if not p1["alive"] or not p2["alive"]:
            return p1, p2

        draw_board(screen, ui)
        draw_food(screen, food, food_assets)
        if p1["alive"]:
            draw_snake(screen, p1["snake"], assets_p1)
        if p2["alive"]:
            draw_snake(screen, p2["snake"], assets_p2)
        draw_text(screen, small, f"{p1['name']} (Arrows): {p1['score']}", (10, 8), GREEN)
        draw_text(screen, small, f"{p2['name']} (WASD): {p2['score']}", (WIDTH - 260, 8), BLUE)
        if not p1["alive"]:
            draw_text(screen, small, f"{p1['name']} is out!", (WIDTH // 2, 8), RED, True)
        if not p2["alive"]:
            draw_text(screen, small, f"{p2['name']} is out!", (WIDTH // 2, 8), RED, True)
        pygame.display.flip()
        clock.tick(speed)


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
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    return

        if ui is None or ui.draw_background(screen):
            screen.fill(BG)
        draw_text(screen, font, "GAME OVER", (WIDTH // 2, 150), RED, True)
        draw_text(screen, font, result, (WIDTH // 2, 215), color, True)
        if winner is not None:
            draw_text(screen, small, f"{winner['name']} score: {winner['score']}",
                      (WIDTH // 2, 275), WHITE, True)
        else:
            draw_text(screen, small, f"Tied score: {p1['score']}", (WIDTH // 2, 275), WHITE, True)
        draw_text(screen, small, f"{p1['name']}: {p1['score']}", (WIDTH // 2, 320), GREEN, True)
        draw_text(screen, small, f"{p2['name']}: {p2['score']}", (WIDTH // 2, 350), BLUE, True)
        draw_text(screen, small, "Press ENTER to return to the menu", (WIDTH // 2, 410), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


def game_over_screen(screen, fonts, score, ui=None):
    font, small = fonts
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return
                if event.key == pygame.K_ESCAPE:
                    return

        if ui is None or ui.draw_background(screen):
            screen.fill(BG)
        draw_text(screen, font, "GAME OVER", (WIDTH // 2, 220), RED, True)
        draw_text(screen, font, f"Score: {score}", (WIDTH // 2, 285), WHITE, True)
        draw_text(screen, small, "Press ENTER to return to the menu", (WIDTH // 2, 350), GRAY, True)
        pygame.display.flip()
        clock.tick(30)


_fullscreen = True


def toggle_fullscreen(screen):
    """Switch between fullscreen and a windowed 800x600. Returns True if
    now in fullscreen."""
    global _fullscreen
    _fullscreen = not _fullscreen
    if _fullscreen:
        screen = pygame.display.set_mode((WIDTH, HEIGHT),
                                         pygame.FULLSCREEN | pygame.SCALED)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    return _fullscreen


def main():
    pygame.init()
    
    icon_path = Path(resource_path("assets/icon.png"))
    if icon_path.is_file():
        game_icon = pygame.image.load(str(icon_path))
        pygame.display.set_icon(game_icon)

    pygame.mixer.init()
    sounds = load_sounds()
    pygame.display.set_caption("Esneyk Geym")
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    font = pygame.font.Font(None, 48)
    small = pygame.font.Font(None, 30)
    fonts = (font, small)

    scores = load_scores()

    assets_p1, assets_p2 = images.make_default_assets(CELL)
    ui = images.UIAssets((WIDTH, HEIGHT))
    food_assets = images.FoodAssets(CELL)

    while True:
        lobby_music_start()
        menu_items = ["1 PLAYER", "2 PLAYER", "LEADERBOARD", "EXIT"]
        button_labels = ["1_player", "2_player", "leaderboard", "exit"]
        selected = 0
        clock = pygame.time.Clock()
        menu_start, menu_spacing = 200, 62
        button_rects = [
            pygame.Rect(0, 0, 300, 54).move(WIDTH // 2 - 150, menu_start + i * menu_spacing - 27)
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
                        toggle_fullscreen(screen)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(menu_items)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(menu_items)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        break
            else:
                if ui is None or ui.draw_background(screen, use_menu=True):
                    screen.fill(BG)
                if not ui.draw_logo(screen, (WIDTH // 2, 130)):
                    draw_text(screen, font, "SNAKE VERSUS", (WIDTH // 2, 130), GREEN, True)
                for i, item in enumerate(menu_items):
                    pos = (WIDTH // 2, menu_start + i * menu_spacing)
                    if not ui.draw_button(screen, button_labels[i], pos, i == selected):
                        color = YELLOW if i == selected else WHITE
                        draw_text(screen, font, item, pos, color, True)
                draw_text(screen, small, "Arrow keys / WASD to navigate • ENTER to select • click with the mouse",
                          (WIDTH // 2, 550), GRAY, True)
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
            name1 = get_name(screen, fonts, "PLAYER 1 (ARROWS) - ENTER NAME", "Player 1", ui)
            name2 = get_name(screen, fonts, "PLAYER 2 (WASD) - ENTER NAME", "Player 2", ui)
            p1, p2 = two_player_game(screen, fonts, name1, name2, assets_p1, assets_p2, sounds, ui, food_assets)

            if p1["score"] > 0:
                add_score(scores, p1["name"], p1["score"])
            if p2["score"] > 0:
                add_score(scores, p2["name"], p2["score"])
            if p1["score"] > 0 or p2["score"] > 0:
                scores = load_scores()

            two_player_game_over_screen(screen, fonts, p1, p2, ui, sounds)
            continue

        player = get_name(screen, fonts, ui=ui)
        lobby_music_stop()
        score, died = game(screen, fonts, player, assets_p1, sounds, ui, food_assets)

        if score > 0:
            add_score(scores, player, score)
            scores = load_scores()

        if died:
            game_over_screen(screen, fonts, score, ui)


if __name__ == "__main__":
    main()
