import 'dart:math';

import 'content.dart';

/// Pure game logic — no Flutter imports so it stays unit-testable.
/// Mirrors main.py / web/game.js: one turn per tick, never 180.
class Vec {
  final int x;
  final int y;
  const Vec(this.x, this.y);

  Vec operator +(Vec o) => Vec(x + o.x, y + o.y);

  @override
  bool operator ==(Object other) => other is Vec && other.x == x && other.y == y;

  @override
  int get hashCode => x * 100003 + y;

  String get key => '$x,$y';
}

const up = Vec(0, -1);
const down = Vec(0, 1);
const left = Vec(-1, 0);
const right = Vec(1, 0);

Vec opposite(Vec v) => Vec(-v.x, -v.y);

/// Port of main.py queue_turn: the direction in flight ([committed])
/// decides what is legal; a turn already queued for this tick is kept.
Vec queueTurn(Vec pending, Vec committed, Vec desired) {
  const legal = [up, down, left, right];
  if (!legal.contains(desired)) return pending;
  if (pending != committed) return pending; // one turn per tick
  if (desired == committed) return pending;
  if (desired == opposite(committed)) return pending;
  return desired;
}

class StepResult {
  final bool died;
  final bool ate;
  /// True when the snake filled the entire board — a victory, not a death.
  final bool won;
  const StepResult({required this.died, required this.ate, this.won = false});
}

class SnakeGame {
  List<Vec> snake;
  Vec dir;
  Vec nextDir;
  Vec? food;
  int score = 0;
  /// Per-segment look ids, kept parallel to [snake]. A new segment rolls a
  /// random id when the snake eats; renderers map it onto the loaded frames
  /// with modulo, so single-frame art renders exactly as before.
  List<int> variantIds = [];
  final int cols;
  final int rows;
  final Random _rng;

  SnakeGame({required this.cols, required this.rows, Random? rng})
      : _rng = rng ?? Random(),
        snake = [],
        dir = right,
        nextDir = right {
    final cx = cols ~/ 2;
    final cy = rows ~/ 2;
    snake = [Vec(cx, cy), Vec(cx - 1, cy), Vec(cx - 2, cy)];
    variantIds = [0, 0, 0];
    dir = right;
    nextDir = right;
    food = randomFood();
  }

  int get stepMs {
    // Speed curve from the shared rules table (M4): desktop, web and the
    // app agree on one curve. GameContent falls back to the canonical
    // constants when the shared file is missing, so unit tests without a
    // Flutter binding still run.
    final fps = min(GameContent.capFps,
        GameContent.startFps + score ~/ GameContent.rampScorePerStep);
    return (1000 / fps).round();
  }

  Vec? randomFood() {
    final occupied = snake.toSet();
    final free = <Vec>[];
    for (var x = 0; x < cols; x++) {
      for (var y = 0; y < rows; y++) {
        final v = Vec(x, y);
        if (!occupied.contains(v)) free.add(v);
      }
    }
    if (free.isEmpty) return null;
    return free[_rng.nextInt(free.length)];
  }

  StepResult step() {
    // A consumed snake has nothing left to step: end the run instead of
    // throwing (a stale ticker can keep calling step() after death, which
    // used to crash-loop every ~stepMs with RangeError).
    if (snake.isEmpty) return const StepResult(died: true, ate: false);
    // Self-healing: the per-segment look ids must stay parallel to the snake
    // 1:1 (desktop main.py keeps the same guard). Repair any drift here so
    // removeLast()/indexing can never see a mis-sized list.
    while (variantIds.length > snake.length) {
      variantIds.removeLast();
    }
    while (variantIds.length < snake.length) {
      variantIds.add(_rng.nextInt(1 << 30));
    }
    dir = nextDir;
    final head = snake.first;
    final n = Vec(head.x + dir.x, head.y + dir.y);
    final hitWall = n.x < 0 || n.x >= cols || n.y < 0 || n.y >= rows;
    final willEat = food != null && n == food;
    final body = willEat ? snake : snake.sublist(0, snake.length - 1);
    final hitSelf = body.contains(n);
    if (hitWall || hitSelf) return const StepResult(died: true, ate: false);
    snake.insert(0, n);
    // The new head segment rolls its own look id on EVERY step (not just on
    // eats — the original only rolled on eats, so ids drained one per normal
    // step and emptied the list); on a normal move the popped tail segment
    // also drops its id. This keeps [variantIds] parallel to [snake] 1:1.
    variantIds.insert(0, _rng.nextInt(1 << 30));
    if (willEat) {
      score += 10;
      food = randomFood();
      // Every cell of the board is now a snake segment: the run is CLEARED.
      // Victory, not death — _endGame(won: true) shows the gold YOU WIN.
      if (food == null) {
        return const StepResult(died: false, ate: true, won: true);
      }
      return const StepResult(died: false, ate: true);
    }
    snake.removeLast();
    variantIds.removeLast();
    return const StepResult(died: false, ate: false);
  }

  void setDir(Vec v) {
    nextDir = queueTurn(nextDir, dir, v);
  }
}

/// Grid size from available board pixels. Same "~26px per cell" rule as web.
({int cols, int rows}) computeGrid(double w, double h) {
  int clamp(int v) => v.clamp(12, 60);
  final cols = clamp((w / 26).round());
  final rows = clamp((h / 26).round());
  return (cols: cols, rows: rows);
}
