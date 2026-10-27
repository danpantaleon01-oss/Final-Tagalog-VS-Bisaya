import 'dart:math';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'content.dart';

/// Fallback display phrases (used only when the shared rules file is
/// missing or a file appears that is not in it — new files then fall
/// back to: strip the `tag-`/`bis-` prefix and extension, separators to
/// spaces, uppercase, `!` at the end).
const _voicePhraseOverrides = {
  'tag-arman.mp3': 'WOW ANSARAP!',
  'tag-babalu.mp3': 'WOW NAMAN!',
  'tag-nenegb.mp3': 'MA ANO ULAM?!',
  'tag-tamis-malupiton.mp3': 'ANG TAMIS!',
  'tagalog_eat.mp3': 'HALIMAW SA SARAP!',
  'bis-lami.mp3': 'LAMI!',
  'bis-sulit.mp3': 'SULIT!',
  'bis-unlirice.mp3': 'UNLIRICE!',
  'bis-yummy.mp3': 'YUMMY!',
  'bisaya_eat.mp3': 'WALANG KANIN?!',
};

String eatPhraseForFile(String filename) {
  // Shared rules first (M4): one phrase table for all three platforms,
  // keyed by the file stem ("tag-arman" — no extension).
  final stem = filename.replaceAll(RegExp(r'\.mp3$', caseSensitive: false), '');
  final shared = GameContent.voicePhraseFor(stem);
  if (shared != null) return shared;
  // Fallback phrase table (kept identical to the shared table in case the
  // bundled game_content.json is missing) and then the generic heuristic.
  final hit = _voicePhraseOverrides[filename];
  if (hit != null) return hit;
  var s = filename;
  final dash = s.indexOf('-');
  if (dash >= 0) s = s.substring(dash + 1);
  s = s.replaceAll(RegExp(r'\.mp3$', caseSensitive: false), '');
  s = s.replaceAll(RegExp(r'[-_]+'), ' ').trim().toUpperCase();
  if (!RegExp(r'[!?.]$').hasMatch(s)) s = '$s!';
  return s;
}

/// Wraps lobby music + per-team eat/death/win effects.
/// Asset dir is `assets/www/assets/audio/` (declared explicitly in
/// pubspec — Flutter does not pick up nested subtrees implicitly), so the
/// [AssetSource] paths below resolve e.g. to
/// `assets/www/assets/audio/tagalog_eat.mp3`.
///
/// Latency note: the eat blip fires on every food pickup, so each team's
/// eat clip gets a dedicated [AudioPool] — players pre-loaded with the
/// asset, so firing is a `resume()` on a prepared player instead of a
/// full stop → resolve → prepare cycle (which caused the audible lag,
/// and a bare `seek(0) + resume()` without the pool stayed silent).
class SoundService {
  final AudioPlayer _music = AudioPlayer();
  // Death/win are rare (and the game is already over), so one shared
  // player with plain play() is fine for them.
  final AudioPlayer _fx = AudioPlayer();
  AudioPool? _eatTagalog;
  AudioPool? _eatBisaya;
  bool _musicOn = false;
  bool _muted = false;

  // ── NEW (additive): per-file voice lines for rice eats ──
  // Discovered at runtime from the bundle: every
  // `assets/www/assets/audio/tag-*.mp3` belongs to Tagalog, every
  // `bis-*.mp3` to Bisaya. Files added to the folder later are picked
  // up automatically — no code change needed. One AudioPool per file
  // keeps firing instant (same pattern as the eat pools above).
  // Nothing below touches the existing pools/files/methods.
  final Map<String, AudioPool> _linePools = {};
  final List<String> _tagLines = [];
  final List<String> _bisLines = [];
  final Random _rng = Random();
  static const _bundleAudio = 'assets/www/assets/audio/';

  static const _prefix = 'www/assets/audio/';
  static const files = [
    'bg_music_lobby.mp3',
    'tagalog_eat.mp3',
    'tagalog_death.mp3',
    'tagalog_win.mp3',
    'bisaya_eat.mp3',
    'bisaya_death.mp3',
    'bisaya_win.mp3',
  ];

  /// Preps everything at startup so first play has no lag and any
  /// missing bundle entry shows up in logcat immediately as `[Audio]`.
  Future<void> preload() async {
    try {
      await _music.setVolume(0.4);
      await _fx.setVolume(0.6);
      _eatTagalog = await AudioPool.createFromAsset(
        path: '${_prefix}tagalog_eat.mp3',
        maxPlayers: 3,
        minPlayers: 2,
      );
      _eatBisaya = await AudioPool.createFromAsset(
        path: '${_prefix}bisaya_eat.mp3',
        maxPlayers: 3,
        minPlayers: 2,
      );
      debugPrint('[Audio] eat pools ready');
      final cache = AudioCache(prefix: 'assets/$_prefix');
      await cache.loadAll(files);
      debugPrint('[Audio] preloaded ${files.length} clips');
      await _discoverVoiceLines(); // NEW: additive, old clips untouched
    } catch (e) {
      debugPrint('[Audio] preload FAILED: $e');
    }
  }

  /// Master mute (HUD speaker, persisted in PrefsStore). Stops the lobby
  /// music immediately and makes every play* call a no-op until unmuted.
  Future<void> setMuted(bool muted) async {
    _muted = muted;
    if (muted) {
      await stopLobbyMusic();
    }
  }

  /// NEW: scans the bundle for `tag-*.mp3` / `bis-*.mp3` voice lines and
  /// warms one pool per file. Purely additive — old pools/files/methods
  /// above are not modified.
  Future<void> _discoverVoiceLines() async {
    try {
      final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
      final found = manifest.listAssets().where((key) {
        if (!key.startsWith(_bundleAudio)) return false;
        final base = key.split('/').last;
        return base.endsWith('.mp3') &&
            (base.startsWith('tag-') || base.startsWith('bis-'));
      }).toList()
        ..sort();
      for (final key in found) {
        final base = key.split('/').last;
        final pool = await AudioPool.createFromAsset(
          path: key.substring('assets/'.length),
          maxPlayers: 3,
          // Two warmed players so a line that overlaps the previous one
          // still starts instantly instead of preparing mid-bite (the
          // old "delayed" symptom).
          minPlayers: 2,
        );
        _linePools[key] = pool;
        if (base.startsWith('tag-')) {
          _tagLines.add(key);
        } else {
          _bisLines.add(key);
        }
      }
      debugPrint('[Audio] voice lines: '
          '${_tagLines.length} tagalog, ${_bisLines.length} bisaya');
    } catch (e) {
      debugPrint('[Audio] voice-line discovery FAILED: $e');
    }
  }

  /// NEW: plays ONE random eat sound from the full rotation for the team:
  /// the classic blip plus every discovered tag-/bis- voice line, each
  /// with an equal chance. Returns its display phrase for the pop-up
  /// (null when nothing is available). Any still-ringing eat sound is
  /// cut first so sounds never layer over each other.
  Future<StopFunction>? _lastEatStop;

  Future<String?> playRandomEatSound(String team) async {
    if (_muted) return null;
    try {
      final isBisaya = team == 'bisaya';
      final options = <({AudioPool pool, String phrase, double volume})>[];
      final classicPool = isBisaya ? _eatBisaya : _eatTagalog;
      if (classicPool != null) {
        options.add((
          pool: classicPool,
          phrase: eatPhraseForFile(
              isBisaya ? 'bisaya_eat.mp3' : 'tagalog_eat.mp3'),
          volume: 0.6,
        ));
      }
      for (final key in (isBisaya ? _bisLines : _tagLines)) {
        final pool = _linePools[key];
        if (pool != null) {
          options.add((
            pool: pool,
            phrase: eatPhraseForFile(key.split('/').last),
            volume: 0.7,
          ));
        }
      }
      if (options.isEmpty) return null;
      final pick = options[_rng.nextInt(options.length)];
      final prev = _lastEatStop;
      _lastEatStop = null;
      if (prev != null) {
        try {
          await (await prev)();
        } catch (_) {}
      }
      final stop = await pick.pool.start(volume: pick.volume);
      _lastEatStop = Future.value(stop);
      return pick.phrase;
    } catch (e) {
      debugPrint('[Audio] random eat sound failed ($e)');
      return null;
    }
  }

  /// NEW: display phrase for the classic per-team eat blip
  /// (`tagalog_eat.mp3` / `bisaya_eat.mp3`), for its own pop-up.
  String oldEatPhrase(String team) => eatPhraseForFile(
      team == 'bisaya' ? 'bisaya_eat.mp3' : 'tagalog_eat.mp3');

  Future<void> playEat(String team) async {
    if (_muted) return;
    try {
      final pool = team == 'bisaya' ? _eatBisaya : _eatTagalog;
      if (pool == null) {
        debugPrint('[Audio] eat pool not ready yet, skipping');
        return;
      }
      await pool.start(volume: 0.6);
    } catch (e) {
      debugPrint('[Audio] eat play failed ($e)');
    }
  }

  Future<void> _playFx(String file) async {
    if (_muted) return;
    try {
      await _fx.stop();
      await _fx.play(AssetSource('$_prefix$file'), volume: 0.6);
    } catch (e) {
      debugPrint('[Audio] play failed $_prefix$file ($e)');
    }
  }

  Future<void> playDeath(String team) => _playFx('${team}_death.mp3');
  Future<void> playWin(String team) => _playFx('${team}_win.mp3');

  Future<void> startLobbyMusic() async {
    if (_muted || _musicOn) return;
    _musicOn = true;
    try {
      await _music.setReleaseMode(ReleaseMode.loop);
      await _music.play(AssetSource('${_prefix}bg_music_lobby.mp3'));
    } catch (e) {
      debugPrint('[Audio] lobby music failed ($e)');
      _musicOn = false;
    }
  }

  Future<void> stopLobbyMusic() async {
    _musicOn = false;
    try {
      await _music.stop();
    } catch (e) {
      debugPrint('[Audio] lobby stop failed ($e)');
    }
  }

  Future<void> dispose() async {
    try {
      await _music.dispose();
      await _fx.dispose();
      await _eatTagalog?.dispose();
      await _eatBisaya?.dispose();
      for (final pool in _linePools.values) {
        await pool.dispose();
      }
    } catch (_) {}
  }
}
