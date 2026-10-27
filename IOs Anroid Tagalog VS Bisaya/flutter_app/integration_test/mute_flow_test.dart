// M2 integration verification (on-device, driver-driven — independent of the
// emulator's adb touch pipe):
//
//  1. A fresh boot plays with sound ON; tapping the HUD speaker mutes it and
//     writes PrefsStore.mutedKey = true.
//  2. A second boot restores the muted choice at startup: the HUD speaker
//     renders `volume_off` immediately (no tap needed).
//
// The win path itself is covered in test/widget_test.dart (board-fill logic)
// and was verified live on the web + desktop builds.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:tagalog_vs_bisaya/main.dart' as app;
import 'package:tagalog_vs_bisaya/scores.dart';

void _bootApp() {
  app.main();
}

/// Menu → PLAY → TAGALOG → START GAME. Minimal pumps only: the snake is
/// already running once START GAME happens and will hit a wall in a few
/// seconds, so the mute assertions must happen quickly after.
Future<void> _reachGame(WidgetTester tester, {int pumpMs = 250}) async {
  await tester.tap(find.textContaining('PLAY').first, warnIfMissed: true);
  await tester.pump(Duration(milliseconds: pumpMs));

  await tester.tap(find.textContaining('TAGALOG').first, warnIfMissed: true);
  await tester.pump(Duration(milliseconds: pumpMs));

  await tester.tap(find.text('START GAME').first, warnIfMissed: true);
  await tester.pump(Duration(milliseconds: pumpMs * 2));
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets('HUD mute toggles and persists the mute pref',
      (WidgetTester tester) async {
    // Fresh state for this phase: no remembered mute, default name/team.
    final sp = await SharedPreferences.getInstance();
    await sp.remove(PrefsStore.mutedKey);

    _bootApp();
    await tester.pump(const Duration(milliseconds: 900));

    await _reachGame(tester);

    expect(find.byIcon(Icons.volume_up), findsOneWidget,
        reason: 'fresh boot must start with sound audible (volume_up icon)');

    await tester.tap(find.byIcon(Icons.volume_up));
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.byIcon(Icons.volume_off), findsOneWidget,
        reason: 'after the tap the HUD speaker must flip to muted');
    expect(find.byIcon(Icons.volume_up), findsNothing);

    // The tap must have written the real persisted pref (plugin-backed).
    final sp2 = await SharedPreferences.getInstance();
    expect(sp2.getBool(PrefsStore.mutedKey), true,
        reason: 'the mute choice must survive a restart via PrefsStore');
  });

  testWidgets('boot restores the muted choice (volume_off icon)',
      (WidgetTester tester) async {
    // Phase 1 left muted=true on disk; this boot must restore it.
    final sp = await SharedPreferences.getInstance();
    expect(sp.getBool(PrefsStore.mutedKey), true,
        reason: 'precondition: phase 1 persisted muted=true');

    _bootApp();
    await tester.pump(const Duration(milliseconds: 900));

    await _reachGame(tester);

    expect(find.byIcon(Icons.volume_off), findsOneWidget,
        reason: 'the restored mute choice must show a muted speaker at boot');
    expect(find.byIcon(Icons.volume_up), findsNothing);

    // Leave the device unmuted for the user (restore polite defaults).
    await tester.tap(find.byIcon(Icons.volume_off));
    await tester.pump(const Duration(milliseconds: 250));
    expect(find.byIcon(Icons.volume_up), findsOneWidget);
    final sp2 = await SharedPreferences.getInstance();
    expect(sp2.getBool(PrefsStore.mutedKey), false);
  });
}
