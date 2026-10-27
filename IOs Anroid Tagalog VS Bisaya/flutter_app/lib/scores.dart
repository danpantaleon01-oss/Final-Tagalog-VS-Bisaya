import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class ScoreEntry {
  final String name;
  final int score;
  const ScoreEntry(this.name, this.score);

  Map<String, dynamic> toJson() => {'name': name, 'score': score};

  static ScoreEntry fromJson(Map<String, dynamic> j) =>
      ScoreEntry((j['name'] ?? 'Player').toString(), (j['score'] ?? 0) as int);
}

class ScoreStore {
  static const key = 'snake_scores';

  static Future<List<ScoreEntry>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(key);
    if (raw == null) return [];
    try {
      final list = (jsonDecode(raw) as List)
          .map((e) => ScoreEntry.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
      list.sort((a, b) => b.score.compareTo(a.score));
      return list.take(10).toList();
    } catch (_) {
      return [];
    }
  }

  /// Returns 0-based rank of the new entry, or -1 when score <= 0.
  static Future<int> add(String name, int score) async {
    if (score <= 0) return -1;
    final prefs = await SharedPreferences.getInstance();
    final all = await load();
    final clean = name.trim().isEmpty ? 'Player' : name.trim();
    final entry = ScoreEntry(
        clean.length > 12 ? clean.substring(0, 12) : clean, score);
    all.add(entry);
    all.sort((a, b) => b.score.compareTo(a.score));
    final top = all.take(10).toList();
    await prefs.setString(
        key, jsonEncode(top.map((e) => e.toJson()).toList()));
    return top.indexOf(entry);
  }
}

/// Remembered QOL prefs (player name + team). Mirrors desktop prefs.json
/// and the PWA's snake_prefs localStorage entry.
class PrefsStore {
  static const nameKey = 'snake_name';
  static const teamKey = 'snake_team';
  static const mutedKey = 'snake_muted';

  static Future<({String name, String? team, bool muted})> load() async {
    final prefs = await SharedPreferences.getInstance();
    return (
      name: prefs.getString(nameKey) ?? 'Player',
      team: prefs.getString(teamKey),
      muted: prefs.getBool(mutedKey) ?? false,
    );
  }

  static Future<void> save(String name, String team,
      {bool muted = false}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(nameKey, name);
    await prefs.setString(teamKey, team);
    await prefs.setBool(mutedKey, muted);
  }
}
