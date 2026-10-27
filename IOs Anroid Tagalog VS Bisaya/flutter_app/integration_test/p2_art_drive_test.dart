// Art-verification driver (M-art showcase): walks Menu → PLAY → BISAYA →
// START GAME, then holds the screen for ~9 real seconds while an external
// `adb shell screencap` loop records frames of the new p2 asset set
// (body/corner/tail, 128x128) rendering on the BISAYA board.
//
// Independent of the emulator's adb touch/key pipe, exactly like the mute
// flow test — WidgetTester taps go through the framework's own hit testing.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:tagalog_vs_bisaya/main.dart' as app;
import 'package:tagalog_vs_bisaya/scores.dart';

void _bootApp() {
  app.main();
}

Future<void> _reachGameAsBisaya(WidgetTester tester, {int pumpMs = 250}) async {
  await tester.tap(find.textContaining('PLAY').first, warnIfMissed: true);
  await tester.pump(Duration(milliseconds: pumpMs));

  await tester.tap(find.textContaining('BISAYA').first, warnIfMissed: true);
  await tester.pump(Duration(milliseconds: pumpMs));

  await tester.tap(find.text('START GAME').first, warnIfMissed: true);
  await tester.pump(Duration(milliseconds: pumpMs * 2));
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets('BISAYA gameplay renders the new p2 art (screenshot window)',
      (WidgetTester tester) async {
    _bootApp();
    await tester.pump(const Duration(milliseconds: 900));

    await _reachGameAsBisaya(tester);

    // MUTE FIRST, while the HUD speaker is guaranteed visible (in-game).
    // The over screen later restarts lobby music — but SoundService.start
    // no-ops while muted, and every play* call is muted-gated too — so no
    // audioplayers frame updater can be left dangling at dispose (that was
    // the "transient callback" teardown complaint on the previous runs).
    final speaker = find.byIcon(Icons.volume_up);
    expect(speaker.evaluate().isNotEmpty, isTrue,
        reason: 'HUD speaker visible while the game is running');
    await tester.tap(speaker.first);
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byIcon(Icons.volume_off), findsOneWidget,
        reason: 'mute applied before the screenshot window');

    // The snake starts heading straight into a wall (dead in ~1-2 s at the
    // 12 fps start pace) — too fast for external adb screencaps. Steer it:
    // the 1P D-pad arrow buttons are normal flat buttons, so alternating
    // up/down taps (~9 cells at 12 fps between taps) zigzag the snake
    // inside one column, away from walls. Guarded: on the over screen the
    // arrow row disappears and a miss must not fail the drive.
    Future<void> _steer(IconData icon) async {
      final f = find.byIcon(icon);
      final existed = f.evaluate().isNotEmpty;
      try {
        if (existed) {
          await tester.tap(f.first);
          await tester.pump(const Duration(milliseconds: 60));
        }
      } catch (e) {
        // Between-screens race (player death, overlay fade) — ignore.
      }
    }

    final up = Icons.arrow_upward;
    final down = Icons.arrow_downward;
    for (final icon in [up, down, up, down, up, down]) {
      await _steer(icon);
      await tester.pump(const Duration(milliseconds: 640));
    }

    // Brief pause for the external screencap loop; ripping onward while
    // audio is muted keeps dispose clean either way.
    await Future<void>.delayed(const Duration(seconds: 2));
    await tester.pump();

    // Restore the on-disk default so the user's next boot isn't silent:
    // only the PREF is cleared here, the (dead) session keeps its choice.
    final sp = await SharedPreferences.getInstance();
    await sp.remove(PrefsStore.mutedKey);
    await tester.pump(const Duration(milliseconds: 100));
  });
}
