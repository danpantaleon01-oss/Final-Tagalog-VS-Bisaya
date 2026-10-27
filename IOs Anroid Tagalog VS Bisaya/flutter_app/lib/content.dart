import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Single source of truth (M4) for the rules shared with desktop
/// main.py/images.py and the PWA's game.js: the speed curve, animation
/// fps and frame caps, the part fit ratio, sway, the popup tables, the
/// voice phrases and the food discovery rule. The canonical file lives
/// at `shared/game_content.json` in the project root; sync_web_to_flutter.bat copies
/// it here (assets/game_content.json, declared in pubspec.yaml) and
/// hash-checks both copies, so drift dies at build time instead of inside
/// one platform.
///
/// Missing/corrupt copy = the fallbacks below, which mirror the canonical
/// values — the game must never break on a bundle problem.
class GameContent {
  GameContent._();

  static Map<String, dynamic> _data = const {};
  static bool loaded = false;

  static Future<void> load() async {
    try {
      final raw = await rootBundle.loadString('assets/game_content.json');
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        _data = decoded;
        loaded = true;
      }
    } catch (e) {
      debugPrint('[Content] assets/game_content.json missing/corrupt — '
          'using fallback constants');
    }
  }

  static dynamic _get(List<String> path, dynamic fallback) {
    Object? node = _data;
    for (final key in path) {
      if (node is! Map || !node.containsKey(key)) return fallback;
      node = node[key];
    }
    final value = node;
    return value ?? fallback;
  }

  /// Test hook: load the parsed shared data without the asset bundle, so
  /// `shared_content_test.dart` can pin the loaded path under a plain
  /// test binding (rootBundle is unavailable there).
  @visibleForTesting
  static void debugInject(Map<String, dynamic> data) {
    _data = data;
    loaded = true;
  }

  // ── speed: same curve on all three platforms ────────────────────────────
  // fps = min(capFps, startFps + score ~/ rampScorePerStep)
  static int get startFps => (_get(const ['speed', 'startFps'], 12) as num).toInt();
  static int get capFps => (_get(const ['speed', 'capFps'], 25) as num).toInt();
  static int get rampScorePerStep =>
      (_get(const ['speed', 'rampScorePerStep'], 50) as num).toInt();

  // ── animation ──
  static int get snakeFrameCap =>
      (_get(const ['animation', 'snakeFrameCap'], 16) as num).toInt();

  // ── part fit / sway ──
  static double get partFillRatio =>
      (_get(const ['part', 'fillRatio'], 3.0) as num).toDouble();
  static double get swayAmount =>
      (_get(const ['sway', 'amount'], 0.14) as num).toDouble();

  /// Segments lean into the bend they sit on: their direction blends
  /// towards the NEXT segment's direction at smoothstep(blendAt) — the
  /// web/game.js rule this class now shares.
  static double get swayBlendAt =>
      (_get(const ['sway', 'blendAt'], 0.45) as num).toDouble();

  // ── popups ──
  static List<String> get popupWords {
    final raw = _get(const ['popup', 'words'], _fallbackPopupWords);
    return (raw as List).map((e) => e.toString()).toList();
  }

  static List<String> get popupColors {
    final raw = _get(const ['popup', 'colors'], _fallbackPopupColors);
    return (raw as List).map((e) => e.toString()).toList();
  }

  /// Popup colors as [Color]s (hex strings in the shared file).
  static List<Color> get popupColorsUi =>
      popupColors.map(parseHexColor).toList();

  static int get popupLifeMs =>
      (_get(const ['popup', 'lifeMs'], 950) as num).toInt();

  // ── voices: file stem -> display phrase (both teams, blips included) ──
  static String? voicePhraseFor(String fileStem) {
    final voices = _get(const ['voices'], null);
    if (voices is! Map) return null;
    for (final spec in voices.values) {
      if (spec is! Map) continue;
      final blip = spec['blip'];
      if (blip == fileStem) {
        final phrase = spec['blipPhrase'];
        if (phrase is String && phrase.isNotEmpty) return phrase;
      }
      final lines = spec['lines'];
      if (lines is! List) continue;
      for (final entry in lines) {
        if (entry is Map && entry['file'] == fileStem) {
          final phrase = entry['phrase'];
          if (phrase is String && phrase.isNotEmpty) return phrase;
        }
      }
    }
    return null;
  }

  // ── food: discovery by rule; `known` doubles as the probe list for
  //    bundles whose manifest cannot be scanned ──
  static List<String> get foodKnown {
    final raw = _get(const ['food', 'known'], _fallbackFoodKnown);
    return (raw as List).map((e) => e.toString()).toList();
  }

  // ── palette (parsed from `palette` in the shared table) ──
  static String paletteHex(String key, String fallback) {
    final pal = _get(const ['palette'], null);
    if (pal is Map && pal[key] is String) return pal[key] as String;
    return fallback;
  }

  /// Team accents (BoardPainter glow/fallback + phrase-popup colors).
  static Color get teamGreen =>
      parseHexColor(paletteHex('green', '#3fe07f'));
  static Color get teamBlue => parseHexColor(paletteHex('blue', '#5aa8ff'));

  /// "#rrggbb" -> [Color]. Invalid input falls back to the popup gold so a
  /// hand-edited table can never crash a spawn.
  static Color parseHexColor(String hex) {
    var h = hex.trim().replaceFirst('#', '');
    if (h.length != 6) return const Color(0xFFFFD246);
    try {
      return Color(int.parse(h, radix: 16) | 0xFF000000);
    } on FormatException {
      return const Color(0xFFFFD246);
    }
  }

  static const List<String> _fallbackPopupWords = [
    'SARAP!',
    'LAMI!',
    'YUMMY!',
    'NOM NOM!',
    'TAMIS!',
    'LAMON!',
    '+10',
    'SHEESH!',
  ];

  static const List<String> _fallbackPopupColors = [
    '#ffd246',
    '#3fe07f',
    '#ffffff',
    '#ff9d9d',
    '#a8d4ff',
  ];

  static const List<String> _fallbackFoodKnown = [
    '785058659_1053053574250803_8373239390610118887_n.png',
    'food.png',
  ];
}
