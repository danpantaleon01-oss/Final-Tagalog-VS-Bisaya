import 'dart:ui' as ui;

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Proves every art/sound file under assets/www/assets/ is actually
/// bundled (pubspec `assets/www/`) and decodable at runtime.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const pngs = [
    'assets/www/assets/icon.png',
    'assets/www/assets/food/785058659_1053053574250803_8373239390610118887_n.png',
    'assets/www/assets/p1/head.png',
    'assets/www/assets/p1/body.png',
    'assets/www/assets/p1/corner.png',
    'assets/www/assets/p1/tail.png',
    'assets/www/assets/p2/head.png',
    'assets/www/assets/p2/body.png',
    'assets/www/assets/p2/corner.png',
    'assets/www/assets/p2/tail.png',
  ];
  const mp3s = [
    'assets/www/assets/audio/bg_music_lobby.mp3',
    'assets/www/assets/audio/tagalog_eat.mp3',
    'assets/www/assets/audio/tagalog_death.mp3',
    'assets/www/assets/audio/tagalog_win.mp3',
    'assets/www/assets/audio/bisaya_eat.mp3',
    'assets/www/assets/audio/bisaya_death.mp3',
    'assets/www/assets/audio/bisaya_win.mp3',
    // voice lines for rice eats (tag- = Tagalog, bis- = Bisaya)
    'assets/www/assets/audio/tag-arman.mp3',
    'assets/www/assets/audio/tag-babalu.mp3',
    'assets/www/assets/audio/tag-nenegb.mp3',
    'assets/www/assets/audio/tag-tamis-malupiton.mp3',
    'assets/www/assets/audio/bis-lami.mp3',
    'assets/www/assets/audio/bis-sulit.mp3',
    'assets/www/assets/audio/bis-unlirice.mp3',
    'assets/www/assets/audio/bis-yummy.mp3',
  ];

  test('all sprite PNGs load and decode', () async {
    for (final key in pngs) {
      final data = await rootBundle.load(key);
      expect(data.lengthInBytes, greaterThan(0), reason: key);
      final codec =
          await ui.instantiateImageCodec(data.buffer.asUint8List());
      final frame = await codec.getNextFrame();
      expect(frame.image.width, greaterThan(0), reason: key);
      expect(frame.image.height, greaterThan(0), reason: key);
    }
  });

  test('all audio MP3s are bundled with bytes', () async {
    for (final key in mp3s) {
      final data = await rootBundle.load(key);
      expect(data.lengthInBytes, greaterThan(1000), reason: key);
    }
  });
}
