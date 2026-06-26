#!/usr/bin/env python3
"""
raidlootmatrix_mplus.py — Mythic+ Weekly Run Import Script
=================================================
Reads active roster from RaidLootMatrix SavedVariables, fetches each player's
M+ runs for the current/last reset week from Raider.IO, and writes raw
run data into RaidLootMatrixMplusImport for in-game EP calculation.

EP is calculated IN-GAME by the addon using Settings -> Mythic+ values.
This script only fetches and stores raw run data (level, timed, dungeon,
roster extras, timestamp).

Usage:
  python raidlootmatrix_mplus.py                     # current week
  python raidlootmatrix_mplus.py --week last         # last completed week
  python raidlootmatrix_mplus.py --week both         # both last + current
  python raidlootmatrix_mplus.py --dry-run           # print results, don't write
  python raidlootmatrix_mplus.py --sv <path>         # override SavedVariables path
  python raidlootmatrix_mplus.py --account <NAME>    # override account name

Requires: pip install requests
"""

import argparse
import datetime
import json
import math
import os
import pathlib
import platform
import re
import sys
import time

# Force UTF-8 output on Windows to avoid charmap errors
if sys.platform == "win32" and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Run:  pip install requests")
    sys.exit(1)

def is_wow_running():
    try:
        import subprocess
        system = platform.system()
        if system == "Windows":
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Wow.exe", "/NH"],
                                    capture_output=True, text=True, check=False)
            return "Wow.exe" in result.stdout
        elif system == "Darwin":
            result = subprocess.run(["pgrep", "-f", "World of Warcraft"],
                                    capture_output=True, text=True, check=False)
            return bool(result.stdout.strip())
    except Exception:
        pass
    return False

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
# Default fallback configuration constants
DEFAULT_ACCOUNT      = "APSU14RYNE"
DEFAULT_REGION       = "us"
DEFAULT_SEASON       = "season-tww-2"
DEFAULT_RIO_DELAY    = 0.35
MAX_RUNS_PER_PLAYER  = 200    # Raider.IO supports up to ~250; grab as much history as possible

# Load dynamic configurations if config JSON exists
if getattr(sys, 'frozen', False):
    addon_dir = pathlib.Path(sys.executable).parent
else:
    addon_dir = pathlib.Path(__file__).parent
config_path = addon_dir / "rlm_importer_config.json"
config_data = {}
if config_path.exists():
    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"[WARNING] Failed to load config from {config_path}: {e}")

ACCOUNT = config_data.get("account", DEFAULT_ACCOUNT)
REGION = config_data.get("region", DEFAULT_REGION)
SEASON = config_data.get("season", DEFAULT_SEASON)
RIO_DELAY = float(config_data.get("rio_delay", DEFAULT_RIO_DELAY))

# Realm slug mapping: WoW format → Raider.IO slug
REALM_SLUGS = {
    "Illidan":        "illidan",
    "Area52":         "area-52",
    "Whisperwind":    "whisperwind",
    "Tichondrius":    "tichondrius",
    "Magtheridon":    "magtheridon",
    "Sargeras":       "sargeras",
    "Proudmoore":     "proudmoore",
    "Dentarg":        "dentarg",
    "Deathwing":      "deathwing",
    "Stormrage":      "stormrage",
    "Hyjal":          "hyjal",
    "Dragonmaw":      "dragonmaw",
}

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
def get_sv_path(account=None, override=None):
    if override:
        return pathlib.Path(override)
    
    # Try dynamic configuration path from config_data first
    custom_path = config_data.get("wow_path")
    if custom_path:
        p = pathlib.Path(custom_path)
        if (p / "RaidLootMatrix.lua").exists():
            return p
        if (p / "SavedVariables" / "RaidLootMatrix.lua").exists():
            return p / "SavedVariables"
        if p.name == "SavedVariables":
            return p
        # If it's a path to Account, we append SavedVariables
        return p / "SavedVariables"

    acct = account or ACCOUNT
    system = platform.system()
    if system == "Windows":
        base = pathlib.Path(r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account")
    elif system == "Darwin":
        base = pathlib.Path.home() / "Library/Application Support/World of Warcraft/_retail_/WTF/Account"
    else:
        raise RuntimeError(f"Unsupported OS: {system}. Use --sv to specify path manually.")
    return base / acct / "SavedVariables"

# ─────────────────────────────────────────────────────────────────────────────
# Week calculation (M+ resets Tuesday 09:00 US Eastern = 15:00 UTC)
# ─────────────────────────────────────────────────────────────────────────────
RESET_WEEKDAY  = 1   # Tuesday (Monday=0)
RESET_HOUR_UTC = 15  # 15:00 UTC

def last_reset_utc():
    """Return the UTC datetime of the most recently completed reset."""
    now = datetime.datetime.now(datetime.timezone.utc)
    days_since = (now.weekday() - RESET_WEEKDAY) % 7
    candidate = (now - datetime.timedelta(days=days_since)).replace(
        hour=RESET_HOUR_UTC, minute=0, second=0, microsecond=0)
    if candidate > now:
        candidate -= datetime.timedelta(weeks=1)
    return candidate

def current_reset_utc():
    """Return the start of the currently active M+ week."""
    return last_reset_utc()

def prev_reset_utc():
    """Return the start of the week BEFORE the current one."""
    return last_reset_utc() - datetime.timedelta(weeks=1)

def next_reset_utc(reset_start):
    return reset_start + datetime.timedelta(weeks=1)

def get_week_start(ts):
    """Return the M+ reset Tuesday datetime for the week containing a unix timestamp."""
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    days_since_reset = (dt.weekday() - RESET_WEEKDAY) % 7
    candidate = (dt - datetime.timedelta(days=days_since_reset)).replace(
        hour=RESET_HOUR_UTC, minute=0, second=0, microsecond=0)
    if candidate > dt:
        candidate -= datetime.timedelta(weeks=1)
    return candidate

# ─────────────────────────────────────────────────────────────────────────────
# Lua SavedVariables parser
# ─────────────────────────────────────────────────────────────────────────────
def parse_sv(sv_path):
    """
    Extract active roster and mplus config from RaidLootMatrix.lua.
    Returns: (roster: list of "Name-Realm", config: dict)
    Config is used for terminal EP preview only — EP is calculated in-game.
    """
    lua_file = sv_path / "RaidLootMatrix.lua"
    if not lua_file.exists():
        raise FileNotFoundError(f"RaidLootMatrix.lua not found at: {lua_file}")

    with open(lua_file, encoding="utf-8") as f:
        text = f.read()

    # ── Active roster (non-deleted entries with ep/gp) ────────────────────
    roster = []
    entry_pattern = re.compile(
        r'\["([A-Z][^"]*-[A-Za-z][^"]+)"\]\s*=\s*\{([^{}]*?)\},',
        re.DOTALL
    )
    for m in entry_pattern.finditer(text):
        name, body = m.group(1), m.group(2)
        if '"deleted"' in body:
            continue
        if '["ep"]' in body or '["gp"]' in body:
            roster.append(name)

    # ── M+ config (for terminal preview only) ─────────────────────────────
    mplus_block_m = re.search(r'\["mplus"\]\s*=\s*\{([^{}]*?)\}', text, re.DOTALL)
    mplus_text = mplus_block_m.group(1) if mplus_block_m else ""

    def mp_num(key, default):
        m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*([0-9.]+)', mplus_text)
        return float(m.group(1)) if m else default

    def mp_bool(key, default):
        m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*(true|false)', mplus_text)
        if not m: return default
        return m.group(1) == "true"

    def mp_str(key, default):
        m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*"([^"]*)"', mplus_text)
        return m.group(1) if m else default

    config = {
        "enabled":        mp_bool("enabled",        False),
        "baseEP":         int(mp_num("baseEP",       100)),
        "perLevel":       int(mp_num("perLevel",     5)),
        "minLevel":       int(mp_num("minLevel",     2)),
        "maxLevel":       int(mp_num("maxLevel",     12)),
        "untimedEnabled": mp_bool("untimedEnabled",  True),
        "untimedPct":     int(mp_num("untimedPct",   100)),
        "weeklyCap":      int(mp_num("weeklyCap",    0)),
        "rosterBonus1":   mp_str("rosterBonus1",     "0%"),
        "rosterBonus2":   mp_str("rosterBonus2",     "0%"),
        "rosterBonus3":   mp_str("rosterBonus3",     "0%"),
        "rosterBonus4":   mp_str("rosterBonus4",     "0%"),
    }

    return roster, config

# ─────────────────────────────────────────────────────────────────────────────
# EP preview calculation (terminal display only — NOT written to file)
# ─────────────────────────────────────────────────────────────────────────────
def parse_bonus(bonus_str, subtotal):
    s = str(bonus_str).strip()
    if "%" in s:
        pct = float(re.sub(r"[^0-9.]", "", s) or "0")
        return math.floor(subtotal * (pct / 100))
    return math.floor(float(s or "0"))

def calc_ep_preview(level, timed, roster_extras, config):
    """Calculate EP for terminal preview. Not written to Lua."""
    if level < config["minLevel"]:
        return 0
    clamped  = min(level, config["maxLevel"])
    subtotal = config["baseEP"] + clamped * config["perLevel"]
    extras   = max(0, min(roster_extras, 4))
    if extras > 0:
        bonus_ep = parse_bonus(config.get(f"rosterBonus{extras}", "0"), subtotal)
        subtotal += bonus_ep
    if not timed:
        if not config["untimedEnabled"]:
            return 0
        subtotal = math.floor(subtotal * (config["untimedPct"] / 100))
    return int(subtotal)

# ─────────────────────────────────────────────────────────────────────────────
# Raider.IO API
# ─────────────────────────────────────────────────────────────────────────────
def realm_to_slug(realm):
    if realm in REALM_SLUGS:
        return REALM_SLUGS[realm]
    return realm.lower().replace(" ", "-").replace("'", "")

def fetch_runs(name, realm, max_recent=MAX_RUNS_PER_PLAYER):
    """Fetch M+ runs via Raider.IO profile endpoint. Retries up to 3 times on error."""
    slug = realm_to_slug(realm)
    url  = "https://raider.io/api/v1/characters/profile"
    params = {
        "region": REGION,
        "realm":  slug,
        "name":   name,
        "fields": f"mythic_plus_recent_runs:{max_recent},mythic_plus_weekly_highest_level_runs,mythic_plus_best_runs",
    }
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 404:
                print(f"  [not found on Raider.IO]", end=" ")
                return []
            r.raise_for_status()
            data = r.json()
            break  # success
        except Exception as e:
            if attempt < 2:
                wait = 2 ** attempt  # 1s, 2s
                print(f"  [retry {attempt+1}/3 after {e}]", end=" ")
                time.sleep(wait)
            else:
                print(f"  [API error after 3 attempts: {e}]", end=" ")
                return []
    else:
        return []

    seen, runs = set(), []

    def add_runs(run_list):
        for run in (run_list or []):
            dungeon_raw  = run.get("dungeon", {})
            dungeon_id   = dungeon_raw.get("id", 0) if isinstance(dungeon_raw, dict) else 0
            dungeon_name = (dungeon_raw.get("name") or dungeon_raw.get("short_name") or "Unknown") \
                           if isinstance(dungeon_raw, dict) else str(dungeon_raw)
            completed_str = run.get("completed_at", "")
            if not completed_str:
                continue
            try:
                dt = datetime.datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
                ts = dt.timestamp()
            except Exception:
                continue
            key = (completed_str, dungeon_id, run.get("mythic_level", 0))
            if key in seen:
                continue
            seen.add(key)
            run["_dungeon_name"] = dungeon_name
            run["_ts"]           = ts
            runs.append(run)

    add_runs(data.get("mythic_plus_recent_runs") or [])
    add_runs(data.get("mythic_plus_weekly_highest_level_runs") or [])
    add_runs(data.get("mythic_plus_best_runs") or [])
    return runs

def norm_key(key):
    """
    Normalize 'Name-Realm' for cross-referencing.
    Strips spaces/hyphens/apostrophes from the realm part so that
    Raider.IO's 'Area 52' matches WoW's 'Area52', etc.
    """
    parts = key.split("-", 1)
    if len(parts) == 2:
        return parts[0].lower() + "-" + re.sub(r"[^a-z0-9]", "", parts[1].lower())
    return key.lower()

def parse_rio_run(rio_run):
    """Extract raw fields from a Raider.IO run entry."""
    roster_raw   = rio_run.get("roster", []) or []
    roster_names = set()
    for member in roster_raw:
        char       = member.get("character", {})
        char_name  = char.get("name", "")
        realm_info = char.get("realm", {})
        char_realm = realm_info.get("name", "") if isinstance(realm_info, dict) else str(realm_info)
        if char_name and char_realm:
            # Normalize realm so "Area 52" == "Area52" == "area-52" etc.
            roster_names.add(char_name.lower() + "-" + re.sub(r"[^a-z0-9]", "", char_realm.lower()))

    dungeon_name = rio_run.get("_dungeon_name") or "Unknown"
    return {
        "dungeon": dungeon_name,
        "level":   rio_run.get("mythic_level") or 0,
        "timed":   (rio_run.get("num_keystone_upgrades") or 0) > 0,
        "roster":  roster_names,  # normalized keys
        "ts":      int(rio_run.get("_ts", 0)),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Lua writer
# ─────────────────────────────────────────────────────────────────────────────
def lua_str(s):
    return '"' + str(s).replace('"', '\\"') + '"'

def load_history(sv_path):
    """Load existing week history from JSON sidecar."""
    json_path = sv_path / "RaidLootMatrixMplusHistory.json"
    if json_path.exists():
        try:
            with open(json_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def read_applied_flags(sv_path):
    """Read applied=true flags from RaidLootMatrix.lua to preserve them on re-import."""
    rc_path = sv_path / "RaidLootMatrix.lua"
    flags   = {}
    if not rc_path.exists():
        return flags
    try:
        text  = rc_path.read_text(encoding="utf-8", errors="replace")
        idx   = text.rfind("RaidLootMatrixMplusImport")
        if idx == -1:
            return flags
        block = text[idx:]
        for m in re.finditer(r'\["(\d{4}-\d{2}-\d{2})"\].*?applied\s*=\s*(true|false)', block, re.DOTALL):
            flags[m.group(1)] = (m.group(2) == "true")
    except Exception:
        pass
    return flags

def write_sidecar(sv_path, week_start, awards, lock=False):
    """
    Write raw run data to RaidLootMatrixMplusImport in RaidLootMatrix.lua.
    awards = list of {player, highest, details: [{dungeon, level, timed, rosterExtras, ts}]}
    EP values are NOT written — the addon calculates EP in-game from Settings.
    Past weeks are locked on first write and never overwritten on subsequent runs.
    """
    week_str  = week_start.strftime("%Y-%m-%d")
    json_path = sv_path / "RaidLootMatrixMplusHistory.json"

    history       = load_history(sv_path)
    applied_flags = read_applied_flags(sv_path)

    # Build new week entry (raw runs only, no EP)
    new_week = {
        "week":       week_str,
        "generated":  int(time.time()),
        "applied":    applied_flags.get(week_str, False),
        "finalized":  lock,   # True only when written AFTER the week's reset passed
        "awards":     sorted(awards, key=lambda a: -a.get("run_count", 0)),
    }
    history[week_str] = new_week

    # Never prune — keep all history unless manually cleared
    # (user can delete RaidLootMatrixMplusHistory.json to reset)

    # Save JSON sidecar
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    # Build Lua block — raw runs only, EP calculated in-game
    lines = [
        "RaidLootMatrixMplusImport = {",
        "  -- Raw Raider.IO run data. EP is calculated in-game from Settings -> Mythic+.",
        "  weeks = {",
    ]

    for wk_str in sorted(history.keys(), reverse=True):
        wk = history[wk_str]
        lines.append(f"    [{lua_str(wk_str)}] = {{")
        lines.append(f"      week      = {lua_str(wk_str)},")
        lines.append(f"      generated = {wk.get('generated', 0)},")
        lines.append(f"      applied   = {str(wk.get('applied', False)).lower()},")
        lines.append(f"      awards    = {{")
        for award in wk.get("awards", []):
            lines.append("        {")
            lines.append(f"          player  = {lua_str(award['player'])},")
            lines.append(f"          highest = {award.get('highest', 0)},")
            lines.append(f"          details = {{")
            for d in award.get("details", []):
                lines.append(
                    f"            {{dungeon={lua_str(d['dungeon'])}, level={d['level']}, "
                    f"timed={str(d['timed']).lower()}, rosterExtras={d.get('rosterExtras', 0)}, "
                    f"ts={d.get('ts', 0)}}},")
            lines.append(f"          }},")
            lines.append("        },")
        lines.append(f"      }},")
        lines.append(f"    }},")

    lines.append("  },")
    lines.append("}")

    lua_block = "\n".join(lines)

    # Inject into RaidLootMatrix.lua
    rc_path = sv_path / "RaidLootMatrix.lua"

    # Warn if WoW is running — simultaneous writes cause file corruption
    try:
        import subprocess
        is_running = False
        system = platform.system()
        if system == "Windows":
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Wow.exe", "/NH"],
                                    capture_output=True, text=True, check=False)
            if "Wow.exe" in result.stdout:
                is_running = True
        elif system == "Darwin":
            result = subprocess.run(["pgrep", "-f", "World of Warcraft"],
                                    capture_output=True, text=True, check=False)
            if result.stdout.strip():
                is_running = True

        if is_running:
            print("\n[WARNING] World of Warcraft is running.")
            print("          Writing M+ data while WoW is open can corrupt SavedVariables.")
            print("          Close WoW first, or do /reload after this script finishes.\n")
    except Exception:
        pass

    # Always back up before writing (timestamped so nothing is ever overwritten)
    import datetime, shutil
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = rc_path.with_suffix(f".lua.backup_{ts}")
    shutil.copy2(rc_path, bak_path)

    rc_text = rc_path.read_text(encoding="utf-8", errors="replace")
    idx = rc_text.rfind("\nRaidLootMatrixMplusImport")
    if idx == -1:
        rc_text = rc_text.rstrip() + "\n" + lua_block + "\n"
    else:
        rc_text = rc_text[:idx] + "\n" + lua_block + "\n"
    rc_path.write_text(rc_text, encoding="utf-8")

    return rc_path

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RaidLootMatrix Mythic+ Weekly Run Import")
    parser.add_argument("--week",       choices=["last", "current", "both", "all"], default="all",
                        help="Which week(s): all (default, auto-detects from data), current, last, both")
    parser.add_argument("--reprocess",  action="store_true",
                        help="Force re-import of locked past weeks (ignores freeze-on-import)")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Print results but don't write the file")
    parser.add_argument("--sv",      help="Override SavedVariables directory path")
    parser.add_argument("--account", default=ACCOUNT,
                        help=f"WoW account name (default: {ACCOUNT})")
    args = parser.parse_args()

    # Defer import if WoW is running and this is a scheduled background execution
    if not args.dry_run and os.environ.get("RAIDLOOTMATRIX_SCHEDULED") == "1":
        if is_wow_running():
            print("[Scheduler] World of Warcraft is currently running. Deferring import until game closes...")
            while is_wow_running():
                time.sleep(30)
            print("[Scheduler] World of Warcraft exit detected. Resuming import...")

    # Resolve WTF Account paths
    sv_paths = []
    if args.sv:
        sv_paths = [pathlib.Path(args.sv)]
    elif args.account and args.account != DEFAULT_ACCOUNT:
        # User specified a particular account via command line
        custom_path = config_data.get("wow_path")
        base_dir = None
        if custom_path:
            p = pathlib.Path(custom_path)
            if p.name == "Account" or p.parent.name == "WTF":
                base_dir = p
            elif p.parent.name == "Account":
                base_dir = p.parent
            else:
                base_dir = p
        
        if not base_dir:
            system = platform.system()
            if system == "Windows":
                base_dir = pathlib.Path(r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account")
            elif system == "Darwin":
                base_dir = pathlib.Path.home() / "Library/Application Support/World of Warcraft/_retail_/WTF/Account"
        
        if base_dir:
            sv_paths = [base_dir / args.account / "SavedVariables"]
        else:
            raise RuntimeError(f"Could not find WTF Account path for account {args.account}")
    else:
        # Default: scan WTF/Account folder to process ALL accounts containing RaidLootMatrix
        custom_path = config_data.get("wow_path")
        base_dir = None
        if custom_path:
            p = pathlib.Path(custom_path)
            # If they selected a specific account folder, process only that one
            if (p / "RaidLootMatrix.lua").exists():
                sv_paths = [p]
            elif (p / "SavedVariables" / "RaidLootMatrix.lua").exists():
                sv_paths = [p / "SavedVariables"]
            elif p.name == "SavedVariables":
                sv_paths = [p]
            else:
                base_dir = p
        
        if not sv_paths:
            if not base_dir:
                system = platform.system()
                if system == "Windows":
                    base_dir = pathlib.Path(r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account")
                elif system == "Darwin":
                    base_dir = pathlib.Path.home() / "Library/Application Support/World of Warcraft/_retail_/WTF/Account"
            
            if base_dir and base_dir.exists():
                # Check if it's actually a single account folder
                if (base_dir / "SavedVariables" / "RaidLootMatrix.lua").exists():
                    sv_paths = [base_dir / "SavedVariables"]
                else:
                    # Scan all subdirectories for SavedVariables/RaidLootMatrix.lua
                    for item in base_dir.iterdir():
                        if item.is_dir():
                            sv_file = item / "SavedVariables" / "RaidLootMatrix.lua"
                            if sv_file.exists():
                                sv_paths.append(item / "SavedVariables")
            
            # Fallback if no paths found: use default account from config/cli
            if not sv_paths:
                acct = args.account or ACCOUNT
                if base_dir:
                    sv_paths = [base_dir / acct / "SavedVariables"]
                else:
                    raise RuntimeError("Could not find WoW Account directory. Please configure WTF path in RLM Importer UI.")

    print(f"Discovered {len(sv_paths)} account(s) to process:")
    for p in sv_paths:
        print(f"  - {p.parent.name} ({p})")

    # 1. Parse rosters across all accounts to build unified fetch list
    combined_roster = set()
    account_rosters = {} # sv_path -> roster
    account_configs = {} # sv_path -> config
    
    for path in sv_paths:
        try:
            roster, config = parse_sv(path)
            account_rosters[path] = roster
            account_configs[path] = config
            combined_roster.update(roster)
        except Exception as e:
            print(f"[WARNING] Failed to parse SavedVariables at {path}: {e}")

    if not combined_roster:
        print("No active players found in any rosters. Exiting.")
        return

    # 2. Fetch all recent runs once per player in the combined roster
    print(f"\nFetching Raider.IO data for {len(combined_roster)} unique players")
    print(f"(requesting 20 recent runs to cover {'both weeks' if args.week == 'both' else 'this week'})...\n")

    player_all_runs = {}
    for player_key in sorted(combined_roster):
        m = re.match(r"^([A-Za-z\xf8\xe6\xe5\xc3-\xfa]+)-(.+)$", player_key)
        if not m:
            print(f"  ? Cannot parse: {player_key}")
            continue
        name, realm = m.group(1), m.group(2)
        print(f"  {name}-{realm}...", end=" ", flush=True)
        all_runs = fetch_runs(name, realm, max_recent=20)
        player_all_runs[player_key] = (name, realm, all_runs)
        print(f"{len(all_runs)} total runs found")
        time.sleep(RIO_DELAY)

    # ── Cross-reference table: who ran together? ──────────────────────────────
    def run_bucket(dungeon_name, level, ts):
        return (dungeon_name.lower().strip(), int(level), round(int(ts) / 120))

    run_membership = {}
    for pkey, (_, _, all_runs) in player_all_runs.items():
        for raw in all_runs:
            ts  = int(raw.get("_ts", 0))
            dng = raw.get("_dungeon_name", "Unknown")
            lvl = raw.get("mythic_level", 0)
            bk  = run_bucket(dng, lvl, ts)
            run_membership.setdefault(bk, set()).add(pkey)

    # 3. Process each week window and save back to each account
    now_utc       = datetime.datetime.now(datetime.timezone.utc)
    curr_start = current_reset_utc()
    
    # Auto-detect weeks present in data
    if args.week == "all":
        week_starts = {curr_start}
        for _, (_, _, pruns) in player_all_runs.items():
            for raw in pruns:
                ts = int(raw.get("_ts", 0))
                if ts > 0:
                    ws = get_week_start(ts)
                    if ws <= curr_start:
                        week_starts.add(ws)
        week_windows = sorted(
            [(ws, next_reset_utc(ws), ws.strftime("%Y-%m-%d")) for ws in week_starts],
            key=lambda x: x[0], reverse=True
        )
    elif args.week == "both":
        prev_start = prev_reset_utc()
        week_windows = [
            (curr_start, next_reset_utc(curr_start), "current"),
            (prev_start, curr_start,                 "previous"),
        ]
    elif args.week == "last":
        prev_start = prev_reset_utc()
        week_windows = [(prev_start, curr_start, "previous")]
    else:
        week_windows = [(curr_start, next_reset_utc(curr_start), "current")]

    # Loop over accounts to perform individual writing
    for sv_path in sv_paths:
        roster = account_rosters.get(sv_path)
        config = account_configs.get(sv_path)
        if not roster or not config:
            continue

        print(f"\n=======================================================")
        print(f"ACCOUNT: {sv_path.parent.name}")
        print(f"=======================================================")
        
        existing_hist = load_history(sv_path)
        last_out_path = None

        for ws, we, wlabel in week_windows:
            week_str = ws.strftime("%Y-%m-%d")
            is_past = we < now_utc

            if is_past and not args.reprocess:
                finalized = existing_hist.get(week_str, {}).get("finalized", False)
                if finalized:
                    print(f"\n-- Week {week_str} [finalized — skipping] -------")
                    continue

            print(f"\n-- Processing week {week_str} [{wlabel}] -------")

            awards = []
            for player_key in roster:
                if player_key not in player_all_runs:
                    continue
                name, realm, all_runs = player_all_runs[player_key]
                week_runs = [r for r in all_runs
                             if ws.timestamp() <= r.get("_ts", 0) < we.timestamp()]

                preview_ep = 0
                highest = 0
                details = []

                for raw in week_runs:
                    run = parse_rio_run(raw)
                    bk = run_bucket(run["dungeon"], run["level"], run["ts"])
                    members = run_membership.get(bk, set())
                    # Only count group members who are in THIS account's roster
                    roster_members = members.intersection(roster)
                    extras = max(0, min(len(roster_members) - 1, 4))

                    ep_preview = calc_ep_preview(run["level"], run["timed"], extras, config)
                    preview_ep += ep_preview

                    if run["level"] > highest:
                        highest = run["level"]

                    details.append({
                        "dungeon": run["dungeon"],
                        "level": run["level"],
                        "timed": run["timed"],
                        "rosterExtras": extras,
                        "ts": run["ts"]
                    })

                if week_runs:
                    if config["weeklyCap"] > 0 and preview_ep > config["weeklyCap"]:
                        preview_ep = config["weeklyCap"]

                    awards.append({
                        "player": player_key,
                        "run_count": len(week_runs),
                        "highest": highest,
                        "details": details,
                        "_preview_ep": preview_ep
                    })

            # Terminal summary (preview EP shown, clearly labeled)
            active = [a for a in awards if a["run_count"] > 0]
            total_pool = sum(a["_preview_ep"] for a in awards)
            print(f"  {len(active)}/{len(roster)} players with runs | EP pool preview: {total_pool}")
            for a in sorted(awards, key=lambda x: -x["_preview_ep"]):
                ep_str = f"{a['_preview_ep']:>5} EP (preview)" if a["_preview_ep"] > 0 else f"{'—':>5}         "
                print(f"  {a['player']:<32} {ep_str}  {a['run_count']} runs")

            if not args.dry_run:
                # Strip _preview_ep before writing (not part of data contract)
                clean_awards = [{k: v for k, v in a.items() if k != "_preview_ep"} for a in awards]
                # Lock completed past weeks so roster changes never retroactively alter them
                last_out_path = write_sidecar(sv_path, ws, clean_awards, lock=is_past)

        # If every week was skipped (all locked) we still need to write the Lua from JSON
        if not args.dry_run and last_out_path is None:
            last_out_path = write_sidecar(sv_path, curr_start,
                                          existing_hist.get(curr_start.strftime("%Y-%m-%d"), {}).get("awards", []),
                                          lock=False)

        if args.dry_run:
            print("\n[DRY RUN] No file written.")
        else:
            print(f"\nWrote: {last_out_path}  (raw run data in RaidLootMatrixMplusImport)")
            print("EP will be calculated in-game from Settings -> Mythic+.")
            print("Log in (or /reload) with an officer and open the Mythic+ tab.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "-" * 55)
        # isatty() alone is unreliable under Task Scheduler (stdin stays a tty even in hidden windows).
        # The batch file sets RAIDLOOTMATRIX_SCHEDULED=1 for all automated runs.
        is_scheduled = os.environ.get("RAIDLOOTMATRIX_SCHEDULED") == "1"
        if sys.stdin.isatty() and not is_scheduled:
            input("Press Enter to close...")

