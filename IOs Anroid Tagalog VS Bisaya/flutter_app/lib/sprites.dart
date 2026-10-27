import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'content.dart';

/// Loads the bundled snake/food PNGs (see `assets/www/assets/`) into
/// `dart:ui` images for the [BoardPainter]. Every file is optional —
/// anything missing logs to logcat and decodes to null, and the painter
/// falls back to vector rounded-rects so the game never breaks.
class SpriteSet {
  final ui.Image? head;
  final ui.Image? body;
  final ui.Image? corner;

  /// NOTE: only `tail.png` (the tapered spike) is used. `tail1.png` /
  /// `tail2.png` in the folder are body-style tiles, not tail frames —
  /// cycling them made the tail visibly morph into a body segment.
  final ui.Image? tail;

  /// All loaded body/corner looks (base file + numbered variants like
  /// `body_0.png`). The painter picks `frames[variantId % frames.length]`;
  /// single-file art yields a 1-entry list rendering exactly as before.
  final List<ui.Image> bodyFrames;
  final List<ui.Image> cornerFrames;

  const SpriteSet(
      {this.head,
      this.body,
      this.corner,
      this.tail,
      this.bodyFrames = const [],
      this.cornerFrames = const []});
}

const _base = 'assets/www/assets';

Future<ui.Image?> _loadOne(String key) async {
  try {
    final data = await rootBundle.load(key);
    final codec =
        await ui.instantiateImageCodec(data.buffer.asUint8List());
    final frame = await codec.getNextFrame();
    debugPrint('[Sprites] loaded $key '
        '${frame.image.width}x${frame.image.height}');
    return frame.image;
  } catch (e) {
    debugPrint('[Sprites] MISSING or undecodable $key ($e)');
    return null;
  }
}

/// Loads one team's set. [dir] is `p1` (Tagalog) or `p2` (Bisaya).
Future<SpriteSet> loadTeamSprites(String dir) async {
  final bodies = await _loadFrames(dir, 'body');
  final corners = await _loadFrames(dir, 'corner');
  return SpriteSet(
    head: await _loadOne('$_base/$dir/head.png'),
    body: bodies.isEmpty ? null : bodies.first,
    corner: corners.isEmpty ? null : corners.first,
    tail: await _loadOne('$_base/$dir/tail.png'),
    bodyFrames: bodies,
    cornerFrames: corners,
  );
}

/// Base file plus `<part>_0.png`, `<part>_1.png`, … (same convention as
/// desktop images.py and web/game.js). Single-file art → 1-frame list.
/// The frame cap comes from the shared rules table (animation.snakeFrameCap).
Future<List<ui.Image>> _loadFrames(String dir, String part) async {
  final cap = GameContent.snakeFrameCap;
  final frames = <ui.Image>[];
  final base = await _loadOne('$_base/$dir/$part.png');
  if (base != null) frames.add(base);
  for (var i = 0; i < cap; i++) {
    final f = await _loadOne('$_base/$dir/${part}_$i.png');
    if (f == null) break;
    frames.add(f);
  }
  return frames;
}

/// Food discovery by RULE instead of a hardcoded filename (M4): scan the
/// bundle manifest for any PNG under assets/food/ (alphabetical order,
/// like the desktop folder scan) and take the first that decodes; the
/// shared `food.known` list is the fallback for a manifest that cannot be
/// read. Renaming the food file therefore needs no code change anywhere.
Future<ui.Image?> loadFoodSprite() async {
  try {
    final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
    final foodKeys = manifest.listAssets().where((key) {
      return key.startsWith('$_base/food/') && key.endsWith('.png');
    }).toList()
      ..sort();
    for (final key in foodKeys) {
      final img = await _loadOne(key);
      if (img != null) return img;
    }
  } catch (e) {
    debugPrint('[Sprites] manifest scan failed — using food.known probes');
  }
  for (final name in GameContent.foodKnown) {
    final img = await _loadOne('$_base/food/$name');
    if (img != null) return img;
  }
  debugPrint('[Sprites] no food art found (vector fallback will be used)');
  return null;
}
