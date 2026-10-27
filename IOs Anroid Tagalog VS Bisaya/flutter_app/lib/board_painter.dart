import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import 'content.dart';
import 'game_logic.dart';
import 'sprites.dart';

class Popup {
  final int gx;
  final int gy;
  final String text;
  final Color color;
  final int bornMs;
  final int lifeMs;
  // Extra spawn offset in CELL units (lets two pop-ups share one eat
  // without overlapping, e.g. voice phrase + classic-blip phrase).
  final double ox;
  final double oy;
  Popup(this.gx, this.gy, this.text, this.color, this.bornMs,
      {this.lifeMs = 950, this.ox = 0, this.oy = 0});
}

class Mote {
  final double x0, y0, vx, vy, r, ph;
  final Color color;
  Mote(this.x0, this.y0, this.vx, this.vy, this.r, this.ph, this.color);
}

List<Mote> makeMotes([int n = 42, int? seed]) {
  final rng = math.Random(seed ?? 7);
  // Mote tints come from the shared palette (green/blue/gold, M4).
  final tints = [
    GameContent.teamGreen,
    GameContent.teamBlue,
    GameContent.parseHexColor(GameContent.paletteHex('gold', '#ffd246')),
  ];
  return List.generate(n, (i) {
    return Mote(
      rng.nextDouble(),
      rng.nextDouble(),
      -0.008 + rng.nextDouble() * 0.02,
      -0.010 + rng.nextDouble() * 0.014,
      1.5 + rng.nextDouble() * 2.8,
      rng.nextDouble() * 6.28,
      tints[i % tints.length],
    );
  });
}

/// Draws the arena + snake + food + popups. Pure Canvas, 60fps-friendly.
class BoardPainter extends CustomPainter {
  final List<Vec> snake;
  final Vec? food;
  final int cols;
  final int rows;
  final bool isBisaya;
  final List<Mote> motes;
  final List<Popup> popups;
  final double nowMs;
  final SpriteSet? sprites; // team art (head/body/corner/tail); null = vector fallback
  final ui.Image? foodImage;
  final List<int> variants; // per-segment look ids, parallel to [snake]

  BoardPainter({
    required this.snake,
    required this.food,
    required this.cols,
    required this.rows,
    required this.isBisaya,
    required this.motes,
    required this.popups,
    required this.nowMs,
    this.sprites,
    this.foodImage,
    this.variants = const [],
  });

  Color get base =>
      isBisaya ? GameContent.teamBlue : GameContent.teamGreen;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final cellW = size.width / cols;
    final cellH = size.height / rows;
    final cell = math.min(cellW, cellH);
    final bw = cols * cell;
    final bh = rows * cell;
    final offX = (size.width - bw) / 2;
    final offY = (size.height - bh) / 2;

    _drawBackground(canvas, size);
    _drawPanel(canvas, offX, offY, bw, bh);
    _drawDots(canvas, offX, offY, cell);
    _drawMotes(canvas, size);
    _drawVignette(canvas, size);
    _drawFood(canvas, offX, offY, cell);
    _drawSnake(canvas, offX, offY, cell);
    _drawPopups(canvas, offX, offY, cell);
    _drawBorder(canvas, offX, offY, bw, bh);
  }

  void _drawBackground(Canvas canvas, Size size) {
    final g = Paint()
      ..shader = ui.Gradient.linear(
        Offset.zero,
        Offset(0, size.height),
        const [Color(0xFF1A1E35), Color(0xFF16182A), Color(0xFF0C0D14)],
        [0.0, 0.45, 1.0],
      );
    canvas.drawRect(Offset.zero & size, g);
    // soft center glow
    final rg = Paint()
      ..shader = ui.Gradient.radial(
        Offset(size.width / 2, size.height / 2),
        math.max(size.width, size.height) * 0.65,
        [
          const Color.fromARGB(18, 90, 140, 255),
          const Color.fromARGB(13, 63, 224, 127),
          const Color.fromARGB(0, 0, 0, 0),
        ],
        [0.0, 0.5, 1.0],
      );
    canvas.drawRect(Offset.zero & size, rg);
  }

  void _drawPanel(Canvas canvas, double ox, double oy, double bw, double bh) {
    final r = RRect.fromRectAndRadius(
        Rect.fromLTWH(ox - 8, oy - 8, bw + 16, bh + 16),
        const Radius.circular(14));
    canvas.drawRRect(
        r,
        Paint()
          ..color = const Color.fromARGB(184, 10, 11, 20)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18));
    canvas.drawRRect(
        r, Paint()..color = const Color.fromARGB(184, 10, 11, 20));
  }

  void _drawDots(Canvas canvas, double ox, double oy, double cell) {
    final p = Paint()..color = const Color.fromARGB(18, 255, 255, 255);
    for (var y = 0; y <= rows; y += 2) {
      for (var x = 0; x <= cols; x += 2) {
        canvas.drawCircle(Offset(ox + x * cell, oy + y * cell), 1.6, p);
      }
    }
  }

  void _drawMotes(Canvas canvas, Size size) {
    final t = nowMs / 1000.0;
    for (final m in motes) {
      final x = (((m.x0 + m.vx * t) % 1 + 1) % 1) * size.width;
      final y = (((m.y0 + m.vy * t) % 1 + 1) % 1) * size.height;
      final tw = 0.5 + 0.5 * math.sin(t * 1.6 + m.ph);
      final paint = Paint()
        ..color = m.color.withValues(alpha: 0.10 + 0.22 * tw)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
      canvas.drawCircle(
          Offset(x, y), m.r * (0.8 + 0.4 * tw), paint);
    }
  }

  void _drawVignette(Canvas canvas, Size size) {
    final vg = Paint()
      ..shader = ui.Gradient.radial(
        Offset(size.width / 2, size.height / 2),
        math.max(size.width, size.height) * 0.75,
        const [Color.fromARGB(0, 0, 0, 0), Color.fromARGB(107, 0, 0, 0)],
        [0.45, 1.0],
      );
    canvas.drawRect(Offset.zero & size, vg);
  }

  void _drawFood(Canvas canvas, double ox, double oy, double cell) {
    final f = food;
    if (f == null) return;
    final cx = ox + f.x * cell + cell / 2;
    final cy = oy + f.y * cell + cell / 2;
    final pulse = 1 + math.sin(nowMs / 280) * 0.07;
    if (foodImage != null) {
      final s = cell * pulse;
      // red glow behind the art, same as the vector fallback below
      canvas.drawCircle(
          Offset(cx, cy),
          (cell / 2 - 2) * pulse,
          Paint()
            ..color = const Color(0xFFFF5D5D)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12));
      canvas.save();
      canvas.translate(cx, cy);
      paintImage(
        canvas: canvas,
        rect: Rect.fromCenter(center: Offset.zero, width: s, height: s),
        image: foodImage!,
        fit: BoxFit.contain,
        filterQuality: FilterQuality.high,
      );
      canvas.restore();
      return;
    }
    final glow = Paint()
      ..color = const Color(0xFFFF5D5D)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
    canvas.drawCircle(Offset(cx, cy), (cell / 2 - 2) * pulse, glow);
    canvas.drawCircle(
        Offset(cx, cy), (cell / 2 - 2) * pulse, Paint()..color = const Color(0xFFFF5D5D));
    canvas.drawCircle(
        Offset(cx - cell * 0.12, cy - cell * 0.14),
        cell * 0.11,
        Paint()..color = const Color.fromARGB(140, 255, 255, 255));
  }

  double _smoothstep(double t) => t * t * (3 - 2 * t);

  /// Web/game.js blendDir: mixes this segment's direction towards the
  /// NEXT segment's at `t`, keeping the result normalized.
  (double, double) _blendDir(
      double dx, double dy, double tx, double ty, double t) {
    final len = math.sqrt(dx * dx + dy * dy);
    if (len == 0) return (tx, ty);
    final ux = tx * t + (dx / len) * (1 - t);
    final uy = ty * t + (dy / len) * (1 - t);
    var m = math.sqrt(ux * ux + uy * uy);
    if (m == 0) m = 1;
    return (ux / m, uy / m);
  }

  List<Offset> _sway(double cell) {
    final n = snake.length;
    final out = List<Offset>.generate(n, (_) => Offset.zero);
    if (n <= 1) return out;
    final dirs = <math.Point<int>>[];
    for (var i = 0; i < n; i++) {
      if (i == 0) {
        dirs.add(math.Point(snake[0].x - snake[1].x, snake[0].y - snake[1].y));
      } else {
        dirs.add(math.Point(snake[i].x - snake[i - 1].x, snake[i].y - snake[i - 1].y));
      }
    }
    // Web parity (M4): each interior segment leans into the bend it sits on
    // by blending its direction (and perpendicular) towards the NEXT
    // segment at smoothstep(shared sway.blendAt) — this is the web rule the
    // painter previously lacked. Heads and tails stay grid-locked.
    final perps = dirs
        .map((d) => math.Point<double>(-d.y.toDouble(), d.x.toDouble()))
        .toList();
    final phase = nowMs / 1000.0;
    final t = _smoothstep(GameContent.swayBlendAt);
    for (var i = 1; i < n - 1; i++) {
      var dx = dirs[i].x.toDouble();
      var dy = dirs[i].y.toDouble();
      var px = perps[i].x;
      var py = perps[i].y;
      if (i + 1 < n - 1) {
        final dxNext = dirs[i + 1].x.toDouble();
        final dyNext = dirs[i + 1].y.toDouble();
        (dx, dy) = _blendDir(dx, dy, dxNext, dyNext, t);
        (px, py) = _blendDir(px, py, perps[i + 1].x, perps[i + 1].y, t);
      }
      final ramp = i / (n - 1);
      final s = math.sin(phase * 4.2 - i * 0.5) *
          GameContent.swayAmount *
          cell *
          ramp;
      out[i] = Offset(px * s, py * s);
    }
    return out;
  }

  void _drawSnake(Canvas canvas, double ox, double oy, double cell) {
    if (snake.isEmpty) return;
    final sway = _sway(cell);
    final set = sprites;
    // tail -> body so the head paints on top
    for (var i = snake.length - 1; i >= 0; i--) {
      final p = snake[i];
      final o = i < sway.length ? sway[i] : Offset.zero;
      final cx = ox + p.x * cell + cell / 2 + o.dx;
      final cy = oy + p.y * cell + cell / 2 + o.dy;

      // ── Head: bundled face art (faces right), grid-locked, no sway ──
      if (i == 0) {
        Vec d = right;
        if (snake.length >= 2) {
          d = Vec(snake[0].x - snake[1].x, snake[0].y - snake[1].y);
        }
        if (set?.head != null) {
          _drawGlowDot(canvas, cx, cy, cell * 0.55, base);
          _drawImage(canvas, set!.head!, cx, cy - o.dy, cell * 1.2,
              _angleFor(d));
          continue;
        }
        final rect = Rect.fromCenter(
            center: Offset(cx, cy), width: cell, height: cell);
        _drawSegmentRect(canvas, rect, cell, isHead: true);
        _drawEyes(canvas, rect);
        continue;
      }

      // ── Tail: tapered spike; art tip points left, attach (+x) faces body ──
      if (i == snake.length - 1 && snake.length >= 2) {
        final tail = set?.tail;
        if (tail != null) {
          final to = Vec(snake[i - 1].x - p.x, snake[i - 1].y - p.y);
          _drawGlowDot(canvas, cx, cy, cell * 0.5, base);
          _drawImage(canvas, tail, cx, cy, cell * 1.1,
              math.atan2(to.y.toDouble(), to.x.toDouble()));
          continue;
        }
        _drawSegmentRect(
            canvas,
            Rect.fromCenter(center: Offset(cx, cy), width: cell, height: cell),
            cell);
        continue;
      }

      // ── Body / corner tiles, rotated onto the direction of travel ──
      // Same rule as desktop images.py (`frame("body", incoming)` +
      // `frame_corner`) and web/game.js (partAngle/cornerFor): p2's
      // striped tiles only line up with the snake when rotated, while
      // p1's symmetric blobs are unaffected by it.
      final a = Vec(p.x - snake[i - 1].x, p.y - snake[i - 1].y);
      final b = Vec(snake[i + 1].x - p.x, snake[i + 1].y - p.y);
      if (a != b) {
        final img = _variantFrame(set?.cornerFrames, i);
        if (img != null) {
          final t = _cornerTransform(a, b);
          _drawGlowDot(canvas, cx, cy, cell * 0.55, base);
          _drawImageEx(canvas, img, cx, cy, cell * 1.05, t.angle, t.mirror);
          continue;
        }
      } else {
        final img = _variantFrame(set?.bodyFrames, i);
        if (img != null) {
          _drawGlowDot(canvas, cx, cy, cell * 0.55, base);
          _drawImage(canvas, img, cx, cy, cell * 1.05, _bodyAngle(img, a));
          continue;
        }
      }
      _drawSegmentRect(
          canvas,
          Rect.fromCenter(center: Offset(cx, cy), width: cell, height: cell),
          cell);
    }
  }

  /// Frame for segment [i]: the segment's variant id mapped onto the
  /// loaded looks with modulo. Missing/short lists fall back to index 0.
  ui.Image? _variantFrame(List<ui.Image>? frames, int i) {
    if (frames == null || frames.isEmpty) return null;
    final id = i < variants.length ? variants[i] : 0;
    return frames[id % frames.length];
  }

  /// Corner rotation, ported from web/game.js cornerFor/partAngle for the
  /// same authored elbow (arms point left + down unrotated). [a]/[b] are
  /// the travel directions entering/leaving the segment.
  ({double angle, bool mirror}) _cornerTransform(Vec a, Vec b) {
    final mirror = _rightTurn(a) != b;
    var angle = _dirAngle(a);
    if (mirror) angle -= math.pi;
    return (angle: angle, mirror: mirror);
  }

  Vec _rightTurn(Vec d) {
    if (d == right) return down;
    if (d == down) return left;
    if (d == left) return up;
    return right; // up -> right
  }

  /// Body tiles carry their pattern along the vertical axis: rotate so the
  /// art's LONG axis runs with travel (tall art is pre-turned a quarter,
  /// like images.py `_normalize_horizontal`).
  double _bodyAngle(ui.Image img, Vec travel) {
    final base = _dirAngle(travel);
    if (img.height > img.width) return base - math.pi / 2;
    return base;
  }

  double _dirAngle(Vec d) {
    if (d == down) return math.pi / 2;
    if (d == left) return math.pi;
    if (d == up) return -math.pi / 2;
    return 0;
  }

  /// Art is authored facing right: right=0, down=+90°, left=180°, up=−90°.
  double _angleFor(Vec d) {
    if (d == down) return math.pi / 2;
    if (d == left) return math.pi;
    if (d == up) return -math.pi / 2;
    return 0;
  }

  /// Draws a sprite using the shared fit rule (see [_drawImageEx]):
  /// whole-cell stretch within the fill ratio, letterboxed beyond it.
  void _drawImage(Canvas canvas, ui.Image img, double cx, double cy,
      double size, double angle) {
    _drawImageEx(canvas, img, cx, cy, size, angle, false);
  }

  /// Shared fit rule (M4, ported from desktop images.py `_fit_cell` and
  /// web/game.js fitCell): art whose aspect stays within partFillRatio is
  /// stretched across the whole cell so consecutive segments meet flush;
  /// anything more elongated keeps its aspect and is letterboxed centred.
  /// Previously this painter was width-locked cover, which left the
  /// near-square p2 art a hair short of the cell instead of meeting it.
  void _drawImageEx(Canvas canvas, ui.Image img, double cx, double cy,
      double size, double angle, bool mirror) {
    final longSide = math.max(img.width, img.height);
    final shortSide = math.min(img.width, img.height);
    double dw, dh;
    if (shortSide > 0 && longSide / shortSide <= GameContent.partFillRatio) {
      dw = size;
      dh = size;
    } else {
      final scale = size / longSide;
      dw = img.width * scale;
      dh = img.height * scale;
    }
    canvas.save();
    canvas.translate(cx, cy);
    if (mirror) canvas.scale(-1, 1);
    canvas.rotate(angle);
    canvas.drawImageRect(
      img,
      Rect.fromLTWH(0, 0, img.width.toDouble(), img.height.toDouble()),
      Rect.fromCenter(center: Offset.zero, width: dw, height: dh),
      Paint()..filterQuality = FilterQuality.medium,
    );
    canvas.restore();
  }

  void _drawGlowDot(
      Canvas canvas, double cx, double cy, double r, Color color) {
    canvas.drawCircle(
        Offset(cx, cy),
        r,
        Paint()
          ..color = color.withValues(alpha: 0.35)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10));
  }

  void _drawSegmentRect(Canvas canvas, Rect rect, double cell,
      {bool isHead = false}) {
    final color = isHead
        ? (isBisaya ? const Color(0xFFB8D8FF) : const Color(0xFFC8FFE0))
        : base;
    final r = math.min(cell * 0.32, 8.0);
    final rr = RRect.fromRectAndRadius(rect.deflate(0.5), Radius.circular(r));
    final glow = Paint()
      ..color = color
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, isHead ? 12 : 7);
    canvas.drawRRect(rr, glow);
    canvas.drawRRect(rr, Paint()..color = color);
    // glossy highlight
    final hi = RRect.fromRectAndCorners(
      Rect.fromLTWH(rect.left + 1, rect.top + 1, rect.width - 2,
          (rect.height - 2) * 0.38),
      topLeft: Radius.circular(r),
      topRight: Radius.circular(r),
    );
    canvas.drawRRect(
        hi, Paint()..color = const Color.fromARGB(71, 255, 255, 255));
  }

  void _drawEyes(Canvas canvas, Rect rect) {
    // Face along travel dir when known.
    Vec d = right;
    if (snake.length >= 2) {
      d = Vec(snake[0].x - snake[1].x, snake[0].y - snake[1].y);
    }
    final cx = rect.center.dx;
    final cy = rect.center.dy;
    final e = rect.width * 0.13;
    final fwd = rect.width * 0.16;
    final side = rect.width * 0.20;
    double x1, y1, x2, y2;
    if (d == right) {
      x1 = cx + fwd;
      y1 = cy - side;
      x2 = cx + fwd;
      y2 = cy + side;
    } else if (d == left) {
      x1 = cx - fwd;
      y1 = cy - side;
      x2 = cx - fwd;
      y2 = cy + side;
    } else if (d == up) {
      x1 = cx - side;
      y1 = cy - fwd;
      x2 = cx + side;
      y2 = cy - fwd;
    } else {
      x1 = cx - side;
      y1 = cy + fwd;
      x2 = cx + side;
      y2 = cy + fwd;
    }
    final p = Paint()..color = const Color(0xFF0B0D14);
    canvas.drawCircle(Offset(x1, y1), e, p);
    canvas.drawCircle(Offset(x2, y2), e, p);
  }

  void _drawPopups(Canvas canvas, double ox, double oy, double cell) {
    for (final p in popups) {
      final age = nowMs - p.bornMs;
      if (age < 0 || age >= p.lifeMs) continue;
      final t = age / p.lifeMs;
      final rise = cell * 1.8 * t;
      final scale = 1 + 0.6 * math.exp(-age / 130.0);
      final alpha = t < 0.6 ? 1.0 : 1 - (t - 0.6) / 0.4;
      final cx = ox + p.gx * cell + cell / 2 + p.ox * cell;
      final cy = oy + p.gy * cell - rise + p.oy * cell;
      final size = math.max(15.0, cell * 0.85) * scale;
      final tp = TextPainter(
        text: TextSpan(
          text: p.text,
          style: TextStyle(
            fontSize: size,
            fontWeight: FontWeight.w900,
            color: p.color.withValues(alpha: alpha.clamp(0.0, 1.0)),
            shadows: const [
              Shadow(color: Colors.black, blurRadius: 8),
            ],
          ),
        ),
        textAlign: TextAlign.center,
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(cx - tp.width / 2, cy - tp.height / 2));
    }
  }

  void _drawBorder(Canvas canvas, double ox, double oy, double bw, double bh) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
          Rect.fromLTWH(ox - 1, oy - 1, bw + 2, bh + 2),
          const Radius.circular(9)),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = base.withValues(alpha: 0.45),
    );
  }

  @override
  bool shouldRepaint(covariant BoardPainter old) => true;
}
