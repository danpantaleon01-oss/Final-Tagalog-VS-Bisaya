import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:tagalog_vs_bisaya/content.dart';

/// M4 anti-drift: the app's rule constants must agree with the canonical
/// `shared/game_content.json` (the web copy is byte-identical via the sync
/// script; the desktop loads the canonical file directly). These tests pin
/// the agreement from the Flutter side, so a one-sided edit to either the
/// shared file or these fallbacks fails `flutter test` at build time.
///
/// NOTE: under the plain test binding GameContent serves its fallback
/// constants (rootBundle needs a fully loaded asset channel), so these
/// assertions prove the equivalence of the canonical file AND the in-code
/// fallbacks — exactly the invariant that keeps the game identical even
/// when a bundle loses the shared file.
void main() {
  final canonical =
      File('../shared/game_content.json').readAsStringSync();

  test('web copy is byte-identical to the canonical shared file', () {
    final webCopy = File('../web/game_content.json').readAsStringSync();
    expect(webCopy, canonical,
        reason: 'web/game_content.json drifted from shared/game_content.json — '
            're-run sync_web_to_flutter.bat');
  });

  test('speed curve agrees with the shared table', () {
    final speed = data()['speed'] as Map;
    expect(GameContent.startFps, (speed['startFps'] as num).toInt());
    expect(GameContent.capFps, (speed['capFps'] as num).toInt());
    expect(GameContent.rampScorePerStep,
        (speed['rampScorePerStep'] as num).toInt());
  });

  test('animation caps and part/sway rules agree', () {
    final anim = data()['animation'] as Map;
    expect(GameContent.snakeFrameCap, (anim['snakeFrameCap'] as num).toInt());
    final part = data()['part'] as Map;
    expect(GameContent.partFillRatio, (part['fillRatio'] as num).toDouble());
    final sway = data()['sway'] as Map;
    expect(GameContent.swayAmount, (sway['amount'] as num).toDouble());
    expect(GameContent.swayBlendAt, (sway['blendAt'] as num).toDouble());
  });

  test('popup words, colors and life agree', () {
    final popup = data()['popup'] as Map;
    expect(GameContent.popupWords, (popup['words'] as List).map((e) => e.toString()));
    expect(
        GameContent.popupColors, (popup['colors'] as List).map((e) => e.toString()));
    expect(GameContent.popupLifeMs, (popup['lifeMs'] as num).toInt());
  });

  test('every voice file in the shared table resolves to its phrase', () {
    // The voice lookup needs the LOADED table (sounds.dart carries the
    // fallback list itself), so inject the parsed canonical file here —
    // the same path the device takes after GameContent.load().
    GameContent.debugInject(
        jsonDecode(File('../shared/game_content.json').readAsStringSync())
            as Map<String, dynamic>);
    final voices = data()['voices'] as Map;
    for (final entry in voices.entries) {
      final spec = entry.value as Map;
      final blip = spec['blip'] as String;
      expect(GameContent.voicePhraseFor(blip), spec['blipPhrase'],
          reason: 'blip phrase for "$blip" drifted');
      for (final line in (spec['lines'] as List)) {
        final file = line['file'] as String;
        expect(GameContent.voicePhraseFor(file), line['phrase'],
            reason: 'phrase for "$file" drifted');
      }
    }
    // Teardown for subsequent tests: back to the fallback state.
    GameContent.debugInject(const {});
  });

  test('food discovery probes agree', () {
    final food = data()['food'] as Map;
    expect(GameContent.foodKnown, (food['known'] as List).map((e) => e.toString()));
  });
}

Map<String, dynamic> data() =>
    jsonDecode(File('../shared/game_content.json').readAsStringSync())
        as Map<String, dynamic>;
