from __future__ import annotations

import json
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PLAYERS_PATH = APP_DIR / "players.json"
MAX_LESSON_NUMBER = 36


def normalize_achievement_awards(values):
    normalized = {}
    if isinstance(values, dict):
        iterable = values.items()
    elif isinstance(values, list):
        iterable = ((value.get("id") if isinstance(value, dict) else value, True) for value in values)
    else:
        return normalized

    for achievement_id, awarded in iterable:
        if not isinstance(achievement_id, str):
            continue
        achievement_id = achievement_id.strip()
        if achievement_id == "total_perfection":
            achievement_id = "totally_perfect"
        if achievement_id:
            normalized[achievement_id] = bool(awarded)
    return normalized


def normalize_lesson_numbers(values):
    if not isinstance(values, list):
        return []
    return sorted(
        {
            value
            for value in values
            if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_LESSON_NUMBER
        }
    )


def latest_stats_perfect_lesson(player):
    stats = player.get("last_mission_stats")
    if not isinstance(stats, dict):
        return None
    lesson_number = stats.get("lesson_number")
    if (
        isinstance(lesson_number, int)
        and not isinstance(lesson_number, bool)
        and stats.get("won")
        and stats.get("hits_taken", 0) == 0
        and stats.get("inaccurate_inputs", 0) == 0
    ):
        return lesson_number
    return None


def migrate_player(player):
    if not isinstance(player, dict):
        return False
    changed = False
    achievements = normalize_achievement_awards(player.get("achievements", {}))
    if achievements != player.get("achievements", {}):
        player["achievements"] = achievements
        changed = True
    perfect_lessons = normalize_lesson_numbers(player.get("perfect_lessons", []))
    latest_perfect = latest_stats_perfect_lesson(player)
    if latest_perfect is not None and latest_perfect not in perfect_lessons:
        perfect_lessons.append(latest_perfect)
        perfect_lessons.sort()
    if "perfect_lessons" not in player or perfect_lessons != player.get("perfect_lessons", []):
        player["perfect_lessons"] = perfect_lessons
        changed = True
    if "last_mission_stats" not in player or not isinstance(player.get("last_mission_stats"), dict):
        player["last_mission_stats"] = {}
        changed = True
    achievement_points = player.pop("achievement_points", 0)
    if isinstance(achievement_points, int) and not isinstance(achievement_points, bool) and achievement_points > 0:
        lifetime_score = player.get("lifetime_score", 0)
        if not isinstance(lifetime_score, int) or isinstance(lifetime_score, bool):
            lifetime_score = 0
        player["lifetime_score"] = max(0, lifetime_score) + achievement_points
        changed = True
    return changed


def migrate():
    if not PLAYERS_PATH.exists():
        print(f"No local players.json found at {PLAYERS_PATH}")
        return
    try:
        players = json.loads(PLAYERS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse {PLAYERS_PATH}: {exc}") from exc
    if not isinstance(players, list):
        raise SystemExit(f"{PLAYERS_PATH} must contain a JSON list")
    migrated = sum(1 for player in players if migrate_player(player))
    if migrated:
        PLAYERS_PATH.write_text(json.dumps(players, indent=2), encoding="utf-8")
    print(f"Migrated {migrated} local player rows in {PLAYERS_PATH}")


if __name__ == "__main__":
    migrate()
