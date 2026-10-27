import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'board_painter.dart';
import 'content.dart';
import 'game_logic.dart';
import 'scores.dart';
import 'sounds.dart';
import 'sprites.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  // M4: the shared rules table (speed curve, sway, popups, voices…) must be
  // resident before any widget reads GameContent.
  await GameContent.load();
  runApp(const TagalogVsBisayaApp());
}

class TagalogVsBisayaApp extends StatelessWidget {
  const TagalogVsBisayaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tagalog vs Bisaya',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        scaffoldBackgroundColor: const Color(0xFF0C0D14),
      ),
      home: const GameHome(),
    );
  }
}

enum Screen { menu, select, name, playing, over }

class GameHome extends StatefulWidget {
  const GameHome({super.key});

  @override
  State<GameHome> createState() => _GameHomeState();
}

class _GameHomeState extends State<GameHome> with WidgetsBindingObserver {
  Screen _screen = Screen.menu;
  bool _showLeaderboard = false;
  String _team = 'tagalog'; // tagalog | bisaya
  String? _rememberedTeam; // last-picked team from prefs (null = fresh)
  String _playerName = 'Player';
  final _nameCtrl = TextEditingController(text: 'Player');
  final _focus = FocusNode();
  final _sounds = SoundService();

  SnakeGame? _game;
  Timer? _ticker;
  int _nowMs = 0;
  int _lastStepMs = 0;
  final List<Popup> _popups = [];
  late final List<Mote> _motes = makeMotes();
  bool _paused = false;
  bool _muted = false;
  Offset? _dragStart;

  List<ScoreEntry> _scores = [];
  int _lastRank = -1;
  int _lastScore = 0;
  bool _lastWon = false;
  int _runBest = 0; // leaderboard best at run start (HUD reference)

  // Bundled art (assets/www/assets/p1|p2|food). Null until loaded;
  // the painter falls back to vector rects meanwhile.
  Map<String, SpriteSet>? _spriteSets;
  ui.Image? _foodImage;

  bool get _isBisaya => _team == 'bisaya';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _sounds.startLobbyMusic();
    _sounds.preload();
    _refreshScores();
    _loadSprites();
    _loadPrefs();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ticker?.cancel();
    _nameCtrl.dispose();
    _focus.dispose();
    _sounds.dispose();
    super.dispose();
  }

  /// Auto-pause when the app leaves the foreground (mirrors desktop
  /// focus-loss pause and the PWA's visibilitychange pause).
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if ((state == AppLifecycleState.paused ||
            state == AppLifecycleState.inactive ||
            state == AppLifecycleState.hidden) &&
        _screen == Screen.playing &&
        !_paused &&
        mounted) {
      setState(() => _paused = true);
    }
  }

  /// Remembered name + team (mirrors desktop prefs.json).
  Future<void> _loadPrefs() async {
    final prefs = await PrefsStore.load();
    if (!mounted) return;
    setState(() {
      _playerName = prefs.name;
      _nameCtrl.text = prefs.name;
      _muted = prefs.muted;
      if (prefs.team == 'tagalog' || prefs.team == 'bisaya') {
        _team = prefs.team!;
        _rememberedTeam = prefs.team;
      }
    });
    // The lobby music may already be running from initState; enforce the
    // restored mute choice right away.
    await _sounds.setMuted(_muted);
  }

  Future<void> _refreshScores() async {
    final s = await ScoreStore.load();
    if (mounted) setState(() => _scores = s);
  }

  Future<void> _loadSprites() async {
    final sets = <String, SpriteSet>{
      'tagalog': await loadTeamSprites('p1'),
      'bisaya': await loadTeamSprites('p2'),
    };
    final food = await loadFoodSprite();
    if (mounted) {
      setState(() {
        _spriteSets = sets;
        _foodImage = food;
      });
    }
  }

  /// EXIT on the main menu. [SystemNavigator.pop] is advisory on some
  /// devices/emulators (and its future may never complete — so it must
  /// NOT be awaited), so force-terminate as a fallback. This is a
  /// sideloaded demo, not a Play Store release.
  void _exitApp() {
    debugPrint('[App] EXIT tapped — closing');
    try {
      // ignore: unawaited_futures
      SystemNavigator.pop();
    } catch (e) {
      debugPrint('[App] SystemNavigator.pop failed ($e)');
    }
    Future.delayed(const Duration(milliseconds: 400), () {
      debugPrint('[App] EXIT fallback: exit(0)');
      exit(0);
    });
  }

  // ── Flow ──────────────────────────────────────────────────────────

  void _goSelect() => setState(() => _screen = Screen.select);

  void _pickTeam(String team) {
    setState(() {
      _team = team;
      _screen = Screen.name;
    });
  }

  void _startGame() {
    final size = MediaQuery.of(context).size;
    final boardW = size.width - 16;
    // Reserve space for HUD (~64) + D-pad (~190) + padding.
    final boardH = max(240.0, size.height - 300);
    final grid = computeGrid(boardW, boardH);
    final name = _nameCtrl.text.trim();
    final playerName = name.isEmpty ? 'Player' : name;
    // ignore: unawaited_futures
    PrefsStore.save(playerName, _team, muted: _muted);
    final runBest =
        _scores.isEmpty ? 0 : _scores.map((s) => s.score).reduce(max);
    setState(() {
      _playerName = playerName;
      _runBest = runBest;
      _rememberedTeam = _team;
      _game = SnakeGame(cols: grid.cols, rows: grid.rows);
      _popups.clear();
      _paused = false;
      _screen = Screen.playing;
      _nowMs = DateTime.now().millisecondsSinceEpoch;
      _lastStepMs = _nowMs;
    });
    _sounds.stopLobbyMusic();
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(milliseconds: 33), _tick);
  }

  Future<void> _tick(Timer t) async {
    if (_screen != Screen.playing || _paused) return;
    final now = DateTime.now().millisecondsSinceEpoch;
    final g = _game;
    if (g == null) return;
    if (now - _lastStepMs >= g.stepMs) {
      _lastStepMs = now;
      final res = g.step();
      if (res.ate) {
        // ONE random eat sound from the full rotation (classic blip +
        // all tag-/bis- voice lines) + its phrase pop-up. Old random
        // pop-up stays as the fallback when no sound is available.
        final phrase = await _sounds.playRandomEatSound(_team);
        if (!mounted) return;
        final head = g.snake.first;
        _spawnPopup(head.x, head.y, text: phrase);
      }
      if (res.died || res.won) {
        await _endGame(won: res.won);
        return;
      }
    }
    // Prune expired popups.
    _popups.removeWhere((p) => now - p.bornMs >= p.lifeMs);
    if (mounted) setState(() => _nowMs = now);
  }

  void _spawnPopup(int gx, int gy,
      {String? text, Color? color, double dyCells = 0}) {
    final rng = Random();
    final popupWords = GameContent.popupWords;
    var word = popupWords[rng.nextInt(popupWords.length)];
    var isPhrase = false;
    if (text != null && text.isNotEmpty) {
      word = text;
      isPhrase = true;
    }
    // Voice-line phrases pop in the team's own color; classic random
    // words keep their assorted colors as before (both from the shared
    // rules table). An explicit color (e.g. gold for the classic-blip
    // phrase) wins over both.
    final Color c = color ??
        (isPhrase
            ? (_isBisaya ? GameContent.teamBlue : GameContent.teamGreen)
            : GameContent.popupColorsUi[rng.nextInt(
                GameContent.popupColorsUi.length)]);
    _popups.add(Popup(
      gx,
      gy,
      word,
      c,
      DateTime.now().millisecondsSinceEpoch,
      lifeMs: GameContent.popupLifeMs,
      oy: dyCells,
    ));
  }

  Future<void> _endGame({bool won = false}) async {
    _ticker?.cancel();
    final g = _game;
    final score = g?.score ?? 0;
    if (won) {
      // Board fully cleared: victory sound + gold screen (see _buildGameOver).
      _sounds.playWin(_team);
    } else {
      _sounds.playDeath(_team);
    }
    final rank = await ScoreStore.add(_playerName, score);
    await _refreshScores();
    _sounds.startLobbyMusic();
    if (!mounted) return;
    setState(() {
      _lastScore = score;
      _lastRank = rank;
      _lastWon = won;
      _screen = Screen.over;
    });
  }

  void _quitToMenu() {
    _ticker?.cancel();
    _sounds.startLobbyMusic();
    setState(() => _screen = Screen.menu);
  }

  void _setDir(Vec v) {
    _game?.setDir(v);
  }

  // ── Input ─────────────────────────────────────────────────────────

  KeyEventResult _onKey(FocusNode node, KeyEvent e) {
    if (e is! KeyDownEvent && e is! KeyRepeatEvent) {
      return KeyEventResult.ignored;
    }
    final k = e.logicalKey;
    // P toggles pause (playing <-> paused), mirroring desktop + PWA.
    if (k == LogicalKeyboardKey.keyP) {
      if (_screen == Screen.playing) {
        setState(() => _paused = !_paused);
        return KeyEventResult.handled;
      }
      return KeyEventResult.ignored;
    }
    // R = instant rematch from game-over (same name + team).
    if (k == LogicalKeyboardKey.keyR) {
      if (_screen == Screen.over) {
        _startGame();
        return KeyEventResult.handled;
      }
      return KeyEventResult.ignored;
    }
    if (_screen != Screen.playing) return KeyEventResult.ignored;
    if (k == LogicalKeyboardKey.arrowUp || k == LogicalKeyboardKey.keyW) {
      _setDir(up);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.arrowDown || k == LogicalKeyboardKey.keyS) {
      _setDir(down);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.arrowLeft || k == LogicalKeyboardKey.keyA) {
      _setDir(left);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.arrowRight || k == LogicalKeyboardKey.keyD) {
      _setDir(right);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.escape) {
      // ESC pauses (resume via P / ▶, quit via ✕) — same as desktop + PWA.
      setState(() => _paused = true);
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  // ── Build ─────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Focus(
      focusNode: _focus,
      autofocus: true,
      onKeyEvent: _onKey,
      child: Scaffold(
        backgroundColor: const Color(0xFF0C0D14),
        body: SafeArea(
          child: Stack(
            children: [
              _buildBody(),
              if (_showLeaderboard) _buildLeaderboardOverlay(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    switch (_screen) {
      case Screen.menu:
        return _buildMenu();
      case Screen.select:
        return _buildSelect();
      case Screen.name:
        return _buildName();
      case Screen.playing:
        return _buildGame();
      case Screen.over:
        return _buildGameOver();
    }
  }

  // ── Menu ──

  Widget _buildMenu() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'MIDTERMS EDITION',
              style: TextStyle(
                  letterSpacing: 4, fontSize: 12, color: Color(0xFF9AA0B4),
                  fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            ShaderMask(
              shaderCallback: (r) => const LinearGradient(
                colors: [Color(0xFFD8FFE6), Color(0xFF3FE07F), Color(0xFF1D9E52)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ).createShader(r),
              child: const Text(
                'SNAKE\nVERSUS',
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 56, fontWeight: FontWeight.w900,
                    height: 0.95, color: Colors.white),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('TAGALOG',
                      style: TextStyle(
                          color: GameContent.teamGreen,
                          fontWeight: FontWeight.w800, fontSize: 13)),
                  _VsChip(),
                  Text('BISAYA',
                      style: TextStyle(
                          color: GameContent.teamBlue,
                          fontWeight: FontWeight.w800, fontSize: 13)),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _menuButton('▶  PLAY', primary: true, onTap: _goSelect),
            const SizedBox(height: 12),
            _menuButton('🏆  LEADERBOARD',
                onTap: () => setState(() => _showLeaderboard = true)),
            const SizedBox(height: 12),
            _menuButton('EXIT',
                ghost: true,
                onTap: _exitApp),
            const SizedBox(height: 16),
            const Text(
              'Swipe to move  •  WASD / arrows + P pause on desktop',
              style: TextStyle(color: Color(0xFF9AA0B4), fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSelect() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('STEP 1 / 2',
                style: TextStyle(letterSpacing: 4, fontSize: 12,
                    color: Color(0xFF9AA0B4), fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            const Text('CHOOSE YOUR SNAKE',
                style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900,
                    color: Color(0xFFFFD246))),
            const SizedBox(height: 24),
            _menuButton('🟢  TAGALOG${_rememberedTeam == 'tagalog' ? '  ✓' : ''}',
                onTap: () => _pickTeam('tagalog')),
            const SizedBox(height: 12),
            _menuButton('🔵  BISAYA${_rememberedTeam == 'bisaya' ? '  ✓' : ''}',
                onTap: () => _pickTeam('bisaya')),
            const SizedBox(height: 12),
            _menuButton('← BACK',
                ghost: true, onTap: () => setState(() => _screen = Screen.menu)),
          ],
        ),
      ),
    );
  }

  Widget _buildName() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('STEP 2 / 2',
                style: TextStyle(letterSpacing: 4, fontSize: 12,
                    color: Color(0xFF9AA0B4), fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            const Text('ENTER YOUR NAME',
                style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900,
                    color: Color(0xFFFFD246))),
            const SizedBox(height: 8),
            Text(
              _isBisaya ? 'Playing as 🔵 BISAYA' : 'Playing as 🟢 TAGALOG',
              style: TextStyle(
                  color: _isBisaya
                      ? GameContent.teamBlue
                      : GameContent.teamGreen,
                  fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: 320,
              child: TextField(
                controller: _nameCtrl,
                maxLength: 12,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 24, fontWeight: FontWeight.w800),
                decoration: InputDecoration(
                  hintText: 'Player',
                  counterText: '',
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.07),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14)),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(
                        color: Color(0xFF3FE07F), width: 2),
                  ),
                ),
                textInputAction: TextInputAction.go,
                onSubmitted: (_) => _startGame(),
              ),
            ),
            const SizedBox(height: 16),
            _menuButton('START GAME', primary: true, onTap: _startGame),
            const SizedBox(height: 12),
            _menuButton('← BACK',
                ghost: true,
                onTap: () => setState(() => _screen = Screen.select)),
            const SizedBox(height: 12),
            const Text('Max 12 characters — shown on the leaderboard',
                style: TextStyle(color: Color(0xFF9AA0B4), fontSize: 13)),
          ],
        ),
      ),
    );
  }

  // ── Game ──

  Widget _buildGame() {
    final g = _game;
    if (g == null) return const Center(child: CircularProgressIndicator());
    final accent =
        _isBisaya ? GameContent.teamBlue : GameContent.teamGreen;
    return Column(
      children: [
        // HUD — chips sit inside Flexible+FittedBox so they shrink on narrow
        // phones / long names / big scores instead of overflowing the row
        // (the M2 mute button made this row genuinely tight).
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(
            children: [
              Flexible(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: _chip(
                      '●  $_playerName',
                      accent),
                ),
              ),
              Flexible(
                flex: 2,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerRight,
                  child: _chip('Score: ${g.score} · Best: ${max(_runBest, g.score)}',
                      const Color(0xFFFFD246)),
                ),
              ),
              IconButton(
                tooltip: _muted ? 'Unmute sound' : 'Mute sound',
                onPressed: () async {
                  final next = !_muted;
                  setState(() => _muted = next);
                  await _sounds.setMuted(next);
                  // ignore: unawaited_futures
                  PrefsStore.save(_playerName, _team, muted: next);
                },
                icon: Icon(_muted ? Icons.volume_off : Icons.volume_up,
                    color: Colors.white70),
              ),
              IconButton(
                tooltip: _paused ? 'Resume' : 'Pause',
                onPressed: () => setState(() => _paused = !_paused),
                icon: Icon(_paused ? Icons.play_arrow : Icons.pause,
                    color: Colors.white70),
              ),
              IconButton(
                tooltip: 'Quit',
                onPressed: _quitToMenu,
                icon: const Icon(Icons.close, color: Colors.white70),
              ),
            ],
          ),
        ),
        // Board (swipe to steer)
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: GestureDetector(
              onPanStart: (d) => _dragStart = d.globalPosition,
              onPanUpdate: (d) {
                final s = _dragStart;
                if (s == null) return;
                final dx = d.globalPosition.dx - s.dx;
                final dy = d.globalPosition.dy - s.dy;
                if (dx.abs() < 24 && dy.abs() < 24) return;
                if (dx.abs() > dy.abs()) {
                  _setDir(dx > 0 ? right : left);
                } else {
                  _setDir(dy > 0 ? down : up);
                }
                _dragStart = d.globalPosition;
              },
              onPanEnd: (_) => _dragStart = null,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: CustomPaint(
                  painter: BoardPainter(
                    snake: g.snake,
                    food: g.food,
                    cols: g.cols,
                    rows: g.rows,
                    isBisaya: _isBisaya,
                    motes: _motes,
                    popups: List.of(_popups),
                    nowMs: _nowMs.toDouble(),
                    sprites: _spriteSets?[_team],
                    foodImage: _foodImage,
                    variants: g.variantIds,
                  ),
                  child: Container(),
                ),
              ),
            ),
          ),
        ),
        if (_paused)
          const Padding(
            padding: EdgeInsets.all(4),
            child: Text('PAUSED — tap ▶ to resume',
                style: TextStyle(color: Color(0xFFFFD246),
                    fontWeight: FontWeight.w700)),
          ),
        // D-pad
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _dpadBtn(Icons.arrow_upward, () => _setDir(up)),
              const SizedBox(width: 8),
              Column(
                children: [
                  const SizedBox(height: 0),
                  Row(
                    children: [
                      _dpadBtn(Icons.arrow_back, () => _setDir(left)),
                      const SizedBox(width: 56),
                      _dpadBtn(Icons.arrow_forward, () => _setDir(right)),
                    ],
                  ),
                ],
              ),
              const SizedBox(width: 8),
              _dpadBtn(Icons.arrow_downward, () => _setDir(down)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _dpadBtn(IconData icon, VoidCallback onTap) {
    return Material(
      color: const Color(0xFF262A42),
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: SizedBox(
          width: 64,
          height: 56,
          child: Icon(icon, color: Colors.white, size: 28),
        ),
      ),
    );
  }

  Widget _chip(String text, Color dot) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      decoration: BoxDecoration(
        color: const Color.fromARGB(184, 12, 14, 24),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
              width: 9,
              height: 9,
              decoration: BoxDecoration(
                  color: dot,
                  shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: dot, blurRadius: 8)])),
          const SizedBox(width: 8),
          Text(text,
              style: const TextStyle(
                  fontWeight: FontWeight.w700, fontSize: 14)),
        ],
      ),
    );
  }

  // ── Game over ──

  Widget _buildGameOver() {
    final isBest = _lastRank == 0 && _lastScore > 0;
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_lastWon ? 'YOU WIN' : 'GAME OVER',
                style: TextStyle(
                    fontSize: 40,
                    fontWeight: FontWeight.w900,
                    color: _lastWon
                        ? const Color(0xFFFFD246)
                        : const Color(0xFFFF5D5D))),
            if (_lastWon) const SizedBox(height: 10),
            if (_lastWon)
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xFFFFD246)),
                    borderRadius: BorderRadius.circular(999)),
                child: const Text('BOARD CLEARED',
                    style: TextStyle(
                        color: Color(0xFFFFD246),
                        fontWeight:
                            FontWeight.w800,
                        letterSpacing: 2,
                        fontSize: 13)),
              ),
            const SizedBox(height: 12),
            if (isBest)
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                    color: const Color(0xFFFFD246),
                    borderRadius: BorderRadius.circular(999)),
                child: const Text('★ NEW BEST ★',
                    style: TextStyle(
                        color: Color(0xFF06130C),
                        fontWeight: FontWeight.w800,
                        letterSpacing: 2, fontSize: 13)),
              ),
            if (isBest) const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(999),
                border:
                    Border.all(color: Colors.white.withValues(alpha: 0.09)),
              ),
              child: Text('★ Score: $_lastScore',
                  style: const TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w900)),
            ),
            const SizedBox(height: 8),
            Text('$_playerName • ${_team.toUpperCase()}',
                style: const TextStyle(color: Color(0xFF9AA0B4))),
            const SizedBox(height: 24),
            _menuButton('↻  PLAY AGAIN', primary: true, onTap: _startGame),
            const SizedBox(height: 12),
            _menuButton('MAIN MENU', ghost: true, onTap: _quitToMenu),
            const SizedBox(height: 12),
            const Text('R for instant rematch',
                style: TextStyle(color: Color(0xFF9AA0B4), fontSize: 13)),
          ],
        ),
      ),
    );
  }

  // ── Leaderboard ──

  Widget _buildLeaderboardOverlay() {
    return Container(
      color: const Color.fromARGB(200, 9, 10, 17),
      child: Center(
        child: Container(
          width: 380,
          constraints: const BoxConstraints(maxHeight: 520),
          margin: const EdgeInsets.symmetric(horizontal: 24),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF161826),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('TOP 10 • THIS DEVICE',
                  style: TextStyle(letterSpacing: 2, fontSize: 12,
                      color: Color(0xFF9AA0B4), fontWeight: FontWeight.w800)),
              const SizedBox(height: 4),
              const Text('LEADERBOARD',
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900,
                      color: Color(0xFFFFD246))),
              const SizedBox(height: 12),
              Flexible(
                child: _scores.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.all(24),
                        child: Text('No scores yet.',
                            style: TextStyle(color: Color(0xFF9AA0B4))),
                      )
                    : ListView.builder(
                        shrinkWrap: true,
                        itemCount: _scores.length,
                        itemBuilder: (c, i) {
                          final s = _scores[i];
                          final first = i == 0;
                          return Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 10),
                            decoration: BoxDecoration(
                              color: first
                                  ? const Color(0xFFFFD246)
                                      .withValues(alpha: 0.14)
                                  : (i.isOdd
                                      ? Colors.white.withValues(alpha: 0.03)
                                      : Colors.transparent),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                Text('${i + 1}. ${first ? '★ ' : ''}${s.name}',
                                    style: TextStyle(
                                        fontWeight: FontWeight.w700,
                                        color: first
                                            ? const Color(0xFFFFD246)
                                            : Colors.white)),
                                const Spacer(),
                                Text('${s.score}',
                                    style: TextStyle(
                                        fontWeight: FontWeight.w700,
                                        color: first
                                            ? const Color(0xFFFFD246)
                                            : Colors.white)),
                              ],
                            ),
                          );
                        },
                      ),
              ),
              const SizedBox(height: 12),
              _menuButton('← BACK',
                  ghost: true,
                  onTap: () => setState(() => _showLeaderboard = false)),
            ],
          ),
        ),
      ),
    );
  }

  // ── Shared button ──

  Widget _menuButton(String label,
      {bool primary = false, bool ghost = false, required VoidCallback onTap}) {
    final bg = primary
        ? const LinearGradient(
            colors: [Color(0xFF5FF596), Color(0xFF22B45E)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter)
        : const LinearGradient(
            colors: [Color(0xFF262A42), Color(0xFF191C2E)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter);
    return SizedBox(
      width: 320,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: ghost ? null : bg,
          color: ghost ? Colors.white.withValues(alpha: 0.05) : null,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: primary
                  ? Colors.white.withValues(alpha: 0.35)
                  : Colors.white.withValues(alpha: 0.12)),
          boxShadow: ghost
              ? null
              : const [
                  BoxShadow(color: Colors.black54, offset: Offset(0, 6),
                      blurRadius: 0),
                ],
        ),
        child: TextButton(
          onPressed: () {
            _focus.requestFocus();
            onTap();
          },
          style: TextButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 15)),
          child: Text(label,
              style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1,
                  color: primary ? const Color(0xFF06130C) : Colors.white)),
        ),
      ),
    );
  }
}

class _VsChip extends StatelessWidget {
  const _VsChip();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 10),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      decoration: BoxDecoration(
          color: const Color(0xFFFFD246),
          borderRadius: BorderRadius.circular(999)),
      child: const Text('VS',
          style: TextStyle(
              color: Color(0xFF191200),
              fontSize: 12, fontWeight: FontWeight.w800)),
    );
  }
}
