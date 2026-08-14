import os
import re
import sys
import json
import time
import platform
import pathlib
import requests

# Default config fallback path
if getattr(sys, 'frozen', False):
    _addon_dir = pathlib.Path(sys.executable).parent
else:
    _addon_dir = pathlib.Path(__file__).parent
_config_file = _addon_dir / "rlm_importer_config.json"
_sync_key = ""
_sync_url = "https://rlm-desktop-companion-production.up.railway.app/api/sync"

if _config_file.exists():
    try:
        with open(_config_file, "r", encoding="utf-8") as _f:
            _cfg = json.load(_f)
            _sync_key = _cfg.get("discord_sync_key", "")
            _sync_url = _cfg.get("discord_sync_url", "https://rlm-desktop-companion-production.up.railway.app/api/sync")
    except Exception:
        pass

# Paste your secure sync key here (retrieve it by typing !synckey in your Discord server)
SYNC_KEY = _sync_key or "YOUR_SYNC_KEY_HERE"

# The API URL of your running Discord Bot
SYNC_URL = _sync_url

# ─────────────────────────────────────────────────────────────────────────────
# LUA SAVEDVARIABLES PARSER
# ─────────────────────────────────────────────────────────────────────────────
def extract_block(text, start_pos):
    idx = text.find('{', start_pos)
    if idx == -1:
        return None, start_pos
    
    count = 1
    pos = idx + 1
    length = len(text)
    while pos < length and count > 0:
        char = text[pos]
        if char == '{':
            count += 1
        elif char == '}':
            count -= 1
        pos += 1
    if count == 0:
        return text[idx:pos], pos
    return None, start_pos

def parse_lua_saved_variables(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"RaidLootMatrix.lua file not found at: {file_path}")
        
    print(f"Reading database file: {file_path}")
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        
    # Remove single line comments
    content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
    
    # Locate RaidLootMatrixDB variable
    db_idx = content.find("RaidLootMatrixDB")
    if db_idx == -1:
        # Fallback in case of variable name variations
        db_idx = content.find("EPGP_RC_DB")
        if db_idx == -1:
            # Final fallback search
            db_match = re.search(r'\w+DB', content)
            if db_match:
                db_idx = db_match.start()
            else:
                raise ValueError("Could not find any database table (RaidLootMatrixDB) in the Lua file.")
            
    db_block, _ = extract_block(content, db_idx)
    if not db_block:
        raise ValueError("Failed to extract RaidLootMatrixDB block.")
    
    # Extract the guild table block
    guild_idx = db_block.find('["guild"]')
    if guild_idx == -1:
        raise ValueError("Could not find the 'guild' roster table inside your RaidLootMatrix data.")
        
    guild_block, _ = extract_block(db_block, guild_idx)
    if not guild_block:
        raise ValueError("Failed to extract guild block.")
    
    # Extract profiles
    profiles = {}
    # Profile keys are formatted as: ["Realm-Name::Profile-Name"] = { ... }
    profile_pattern = re.compile(r'\["([^"]+::[^"]+)"\]\s*=')
    
    for pm in profile_pattern.finditer(guild_block):
        profile_key = pm.group(1)
        profile_text, _ = extract_block(guild_block, pm.end())
        if not profile_text:
            continue
        
        # Find the ["roster"] section in the profile
        roster_idx = profile_text.find('["roster"]')
        if roster_idx == -1:
            continue
            
        roster_text, _ = extract_block(profile_text, roster_idx)
        if not roster_text:
            continue
        
        # Player entries are formatted as: ["PlayerName-Realm"] = { ... }
        player_pattern = re.compile(r'\["([^"]+-[^"]+)"\]\s*=')
        
        roster = {}
        for pl_m in player_pattern.finditer(roster_text):
            player_name = pl_m.group(1)
            player_text, _ = extract_block(roster_text, pl_m.end())
            if not player_text:
                continue
            
            ep = 0.0
            gp = 0.0
            player_class = "Unknown"
            is_alt = False
            main_name = ""
            deleted = False
            
            # ep
            ep_m = re.search(r'\["ep"\]\s*=\s*([0-9.-]+)', player_text)
            if ep_m: ep = float(ep_m.group(1))
            
            # gp
            gp_m = re.search(r'\["gp"\]\s*=\s*([0-9.-]+)', player_text)
            if gp_m: gp = float(gp_m.group(1))
            
            # class
            class_m = re.search(r'\["class"\]\s*=\s*"([^"]+)"', player_text)
            if class_m: player_class = class_m.group(1)
            
            # isAlt
            alt_m = re.search(r'\["isAlt"\]\s*=\s*(true|false)', player_text)
            if alt_m: is_alt = alt_m.group(1) == "true"
            
            # mainName
            main_m = re.search(r'\["mainName"\]\s*=\s*"([^"]+)"', player_text)
            if main_m: main_name = main_m.group(1)
            
            # deleted
            del_m = re.search(r'\["deleted"\]\s*=\s*(true|false)', player_text)
            if del_m: deleted = del_m.group(1) == "true"
            
            if not deleted:
                roster[player_name] = {
                    "ep": ep,
                    "gp": gp,
                    "class": player_class,
                    "isAlt": is_alt,
                    "mainName": main_name
                }
        
        if roster:
            profiles[profile_key] = roster
            
    return profiles

def extract_raid_end_timestamps(file_path):
    """Extract highest 'Raid End' timestamp for each profile from RaidLootMatrix.lua."""
    timestamps = {}
    if not os.path.exists(file_path):
        return timestamps
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        profile_pattern = re.compile(r'\["([^"]+::[^"]+)"\]\s*=')
        for pm in profile_pattern.finditer(content):
            profile_key = pm.group(1)
            profile_text, _ = extract_block(content, pm.end())
            if not profile_text:
                continue

            max_ts = 0
            # Match any EP history entry logged for ending a raid (Raid Complete, Raid End, End Raid, etc.)
            for match in re.finditer(r'\["reason"\]\s*=\s*"(Raid Complete|Raid End|End Raid|Raid Ended|Raid Complete \([^"]+\))".*?\["timestamp"\]\s*=\s*(\d+)', profile_text, re.DOTALL):
                ts = int(match.group(2))
                if ts > max_ts:
                    max_ts = ts
            
            for match in re.finditer(r'\["raidend"\]\s*=\s*true.*?\["timestamp"\]\s*=\s*(\d+)', profile_text, re.DOTALL):
                ts = int(match.group(1))
                if ts > max_ts:
                    max_ts = ts

            if max_ts > 0:
                timestamps[profile_key] = max_ts
    except Exception as e:
        print(f"[WARNING] Could not parse raid end timestamps: {e}")
    return timestamps

# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLIENT LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("="*60)
    print(" RaidLootMatrix Desktop Sync Client (Method 2)")
    print("="*60)

    # Force UTF-8 on Windows
    if sys.platform == "win32" and sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    def prompt_exit(code=0):
        if "--non-interactive" not in sys.argv and sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            try:
                input("\nPress Enter to exit...")
            except Exception:
                pass
        if code != 0:
            sys.exit(code)

    # 1. Load config file from the workspace directory
    if getattr(sys, 'frozen', False):
        addon_dir = pathlib.Path(sys.executable).parent
    else:
        addon_dir = pathlib.Path(__file__).parent
    config_path = addon_dir / "rlm_importer_config.json"
    wow_path = ""
    account = ""
    cfg = {}
    
    sync_key = _sync_key
    sync_url = _sync_url
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8", errors="replace") as f:
                cfg = json.load(f)
                wow_path = cfg.get("wow_path", "")
                account = cfg.get("account", "")
                sync_key = cfg.get("discord_sync_key", sync_key)
                sync_url = cfg.get("discord_sync_url", sync_url)
        except Exception as e:
            print(f"[WARNING] Failed to load config from {config_path}: {e}")

    # 2. Resolve SavedVariables paths
    sv_files = []
    if wow_path:
        p = pathlib.Path(wow_path)
        if p.exists():
            if p.name == "SavedVariables" and (p / "RaidLootMatrix.lua").exists():
                sv_files = [p / "RaidLootMatrix.lua"]
            elif (p / "SavedVariables" / "RaidLootMatrix.lua").exists():
                sv_files = [p / "SavedVariables" / "RaidLootMatrix.lua"]
            else:
                try:
                    for match in p.glob("**/SavedVariables/RaidLootMatrix.lua"):
                        if match.is_file():
                            sv_files.append(match)
                except Exception as e:
                    print(f"[WARNING] Recursive search error: {e}")

    if not sv_files:
        # Fallback to default WoW installations if nothing found yet
        system = platform.system()
        default_dir = None
        if system == "Windows":
            default_dir = pathlib.Path(r"C:\Program Files (x86)\World of Warcraft")
        elif system == "Darwin":
            default_dir = pathlib.Path.home() / "Library/Application Support/World of Warcraft"
        
        if default_dir and default_dir.exists():
            try:
                for match in default_dir.glob("**/SavedVariables/RaidLootMatrix.lua"):
                    if match.is_file():
                        sv_files.append(match)
            except Exception:
                pass

    if not sv_files:
        print("❌ Error: Could not locate your 'RaidLootMatrix.lua' SavedVariables file.")
        print("To fix this, please run 'Run RLM Importer UI.bat' first and configure your")
        print("World of Warcraft directory or WTF Path in the settings.")
        prompt_exit(1)

    # 3. Parse EPGP and Roster data across all accounts
    all_profiles = {}
    try:
        for sv_file in sv_files:
            profiles = parse_lua_saved_variables(sv_file)
            for p_key, roster in profiles.items():
                if p_key not in all_profiles:
                    all_profiles[p_key] = {}
                for char_name, char_data in roster.items():
                    all_profiles[p_key][char_name] = char_data
                    
        if not all_profiles:
            print("❌ Error: No EPGP profiles or rosters found in the file(s).")
            prompt_exit(1)
            
        print(f"Successfully parsed {len(all_profiles)} database profiles across all accounts.")
        for p_key, roster in all_profiles.items():
            print(f" - Profile '{p_key.split('::')[-1]}' ({len(roster)} characters)")

    except Exception as e:
        print(f"❌ Error parsing Lua SavedVariables: {e}")
        prompt_exit(1)

    # 3b. Check Post-Raid Raid End timestamp deduplication if running on WoW Exit
    is_post_raid_trigger = "--post-raid" in sys.argv
    last_posted_ends = cfg.get("last_posted_raid_end_timestamps", {})
    new_posted_ends = dict(last_posted_ends)

    if is_post_raid_trigger and "--force" not in sys.argv:
        has_new_raid_end = False
        for sv_file in sv_files:
            raid_ends = extract_raid_end_timestamps(sv_file)
            for p_key, latest_ts in raid_ends.items():
                last_ts = last_posted_ends.get(p_key, 0)
                if latest_ts > last_ts:
                    has_new_raid_end = True
                    new_posted_ends[p_key] = latest_ts

        if not has_new_raid_end and last_posted_ends:
            print("ℹ️ Post-Raid Sync skipped: No new 'Raid End' event detected since last post.")
            prompt_exit(0)

    # 4. Check per-team Sync Keys and upload standings for each configured team
    team_settings = cfg.get("team_discord_settings", {})
    synced_any = False

    # Build Mythic+ leaderboard summary for active roster
    mplus_leaderboard = {}
    try:
        import raidlootmatrix_mplus
        print("Fetching Mythic+ scores and dungeon summaries from Raider.IO...")
        for p_key, roster in all_profiles.items():
            mplus_leaderboard[p_key] = []
            for char_name in list(roster.keys())[:30]:
                if "-" in char_name:
                    cname, crealm = char_name.split("-", 1)
                else:
                    cname, crealm = char_name, "Whisperwind"
                
                runs = raidlootmatrix_mplus.fetch_runs(cname, crealm, max_recent=5)
                highest_level = max([r.get("mythic_level", 0) for r in runs], default=0)
                mplus_leaderboard[p_key].append({
                    "name": char_name,
                    "highest_level": highest_level,
                    "recent_runs": [
                        {
                            "dungeon": r.get("_dungeon_name", "Unknown"),
                            "level": r.get("mythic_level", 0),
                            "timed": (r.get("num_keystone_upgrades", 0) > 0)
                        } for r in runs[:3]
                    ]
                })
    except Exception as e:
        print(f"[WARNING] Could not fetch Raider.IO M+ leaderboard data: {e}")

    for profile_key, roster in all_profiles.items():
        p_cfg = team_settings.get(profile_key, {})
        if not p_cfg:
            for tk, tval in team_settings.items():
                if tk and (tk in profile_key or profile_key in tk or tk.split("::")[-1] in profile_key):
                    p_cfg = tval
                    break

        team_key = p_cfg.get("discord_sync_key") or (sync_key if sync_key != "YOUR_SYNC_KEY_HERE" else "")
        if not team_key:
            for tval in team_settings.values():
                k_candidate = tval.get("discord_sync_key", "").strip()
                if k_candidate and k_candidate != "YOUR_SYNC_KEY_HERE":
                    team_key = k_candidate
                    break
        display_name = profile_key.split("::")[-1]

        if not team_key:
            print(f"ℹ️ Skipping team '{display_name}': No Sync Key set for this team in Discord Bot tab.")
            continue

        team_profiles = {profile_key: roster}
        team_mplus = {profile_key: mplus_leaderboard.get(profile_key, [])}

        payload = {
            "timestamp": int(time.time()),
            "profiles": team_profiles,
            "epgp_channel": p_cfg.get("epgp_channel", cfg.get("epgp_channel", "epgp-standings")),
            "epgp_schedule": p_cfg.get("epgp_schedule", cfg.get("epgp_schedule", "Post-Raid (On WoW Exit)")),
            "mplus_channel": p_cfg.get("mplus_channel", cfg.get("mplus_channel", "mplus-leaderboard")),
            "mplus_schedule": p_cfg.get("mplus_schedule", cfg.get("mplus_schedule", "Tuesday Post-Reset (Default)")),
            "pin_update_mode": cfg.get("pin_update_mode", True),
            "mplus_leaderboard": team_mplus
        }

        headers = {
            "Authorization": team_key,
            "Content-Type": "application/json"
        }

        print(f"\nUploading standings data for team '{display_name}' to {sync_url}...")
        try:
            response = requests.post(sync_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"🚀 Sync Successful for team '{display_name}'!")
                synced_any = True
            else:
                print(f"❌ Sync Failed for team '{display_name}' with status code: {response.status_code}")
                try:
                    print(f"Error detail: {response.json().get('error', response.text)}")
                except Exception:
                    print(f"Error detail: {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"❌ Sync Failed for team '{display_name}': Could not connect to Discord Bot API server.")
        except Exception as e:
            print(f"❌ Sync Failed for team '{display_name}': {e}")

    if synced_any and new_posted_ends:
        cfg["last_posted_raid_end_timestamps"] = new_posted_ends
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    prompt_exit(0)

if __name__ == "__main__":
    main()
