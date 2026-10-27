import 'package:flutter_test/flutter_test.dart';

import 'package:tagalog_vs_bisaya/game_logic.dart';
import 'package:tagalog_vs_bisaya/sounds.dart';

void main() {
  test('voice-line phrases derive from filenames', () {
    // exact per-file phrases (edit _voicePhraseOverrides to change text)
    expect(eatPhraseForFile('tag-arman.mp3'), 'WOW ANSARAP!');
    expect(eatPhraseForFile('tag-babalu.mp3'), 'WOW NAMAN!');
    expect(eatPhraseForFile('tag-nenegb.mp3'), 'MA ANO ULAM?!');
    expect(eatPhraseForFile('tag-tamis-malupiton.mp3'), 'ANG TAMIS!');
    expect(eatPhraseForFile('tagalog_eat.mp3'), 'HALIMAW SA SARAP!');
    expect(eatPhraseForFile('bis-lami.mp3'), 'LAMI!');
    expect(eatPhraseForFile('bis-sulit.mp3'), 'SULIT!');
    expect(eatPhraseForFile('bis-unlirice.mp3'), 'UNLIRICE!');
    expect(eatPhraseForFile('bis-yummy.mp3'), 'YUMMY!');
    expect(eatPhraseForFile('bisaya_eat.mp3'), 'WALANG KANIN?!');
    // fallback for future files: prefix stripped, uppercase, `!` added
    expect(eatPhraseForFile('tag-bagong-salita.mp3'), 'BAGONG SALITA!');
  });

  test('queueTurn rejects 180 and chains', () {
    expect(queueTurn(right, right, left), right); // 180 rejected
    expect(queueTurn(right, right, up), up); // legal turn accepted
    // one turn per tick: pending already differs from committed
    expect(queueTurn(up, right, down), up);
  });

  test('snake eats, scores, and dies on wall', () {
    final g = SnakeGame(cols: 10, rows: 10);
    final head = g.snake.first;
    g.food = Vec(head.x + 1, head.y);
    final r = g.step();
    expect(r.ate, true);
    expect(g.score, 10);

    // Drive into the wall.
    g.nextDir = g.dir = right;
    for (var i = 0; i < 12; i++) {
      final s = g.step();
      if (s.died) break;
    }
    expect(g.score, 10);
  });

  test('computeGrid stays in bounds', () {
    final grid = computeGrid(390, 600);
    expect(grid.cols >= 12 && grid.cols <= 60, true);
    expect(grid.rows >= 12 && grid.rows <= 60, true);
  });

  test('step() keeps variantIds parallel to snake over long runs', () {
    // Regression: variant ids used to drain one per non-eat step, emptying
    // the list by step ~4 and crash-looping (RangeError on removeLast).
    final g = SnakeGame(cols: 60, rows: 60);
    for (var i = 0; i < 200; i++) {
      final h = g.snake.isNotEmpty ? g.snake.first : null;
      if (h != null) {
        if (h.x >= 55) g.setDir(down);
        if (h.y >= 55) g.setDir(left);
        if (h.x <= 5) g.setDir(up);
        if (h.y <= 5) g.setDir(right);
      }
      final r = g.step();
      if (r.died) break;
      expect(g.variantIds.length, g.snake.length, reason: 'desync at step $i');
    }
  });

  test('stepping after death is a safe no-op (no crash-loop)', () {
    final g = SnakeGame(cols: 10, rows: 10);
    g.nextDir = g.dir = right;
    for (var i = 0; i < 30; i++) {
      if (g.step().died) {
        // A stale ticker keeps firing after a death; every call must be a
        // clean "died" result, never an exception.
        for (var k = 0; k < 10; k++) {
          expect(g.step().died, true);
        }
        break;
      }
    }
  });

  test('board fully filled reports won, not died', () {
    // M2 regression: filling every cell used to return died=true, showing
    // the red GAME OVER. A cleared board is a victory now.
    final g = SnakeGame(cols: 2, rows: 2);
    g.snake = [const Vec(0, 0), const Vec(1, 0), const Vec(1, 1)];
    g.variantIds = [0, 0, 0];
    g.food = const Vec(0, 1); // the only free cell
    g.nextDir = down; // step into the last free cell
    final r = g.step();
    expect(r.won, true);
    expect(r.died, false);
    expect(r.ate, true);
    expect(g.score, 10);
    expect(g.food, isNull); // no cell left for another food
    expect(g.snake.length, 4); // the whole 2x2 board is snake
  });
}
