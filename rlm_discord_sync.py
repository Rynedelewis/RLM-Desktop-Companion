import os
import re
import sys
import json
import time
import platform
import pathlib

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

    def prompt_exit(code=1):
        if "--non-interactive" not in sys.argv:
            input("\nPress Enter to exit...")
        sys.exit(code)

    # 1. Load config file from the workspace directory
    if getattr(sys, 'frozen', False):
        addon_dir = pathlib.Path(sys.executable).parent
    else:
        addon_dir = pathlib.Path(__file__).parent
    config_path = addon_dir / "rlm_importer_config.json"
    wow_path = ""
    account = ""
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8", errors="replace") as f:
                cfg = json.load(f)
                wow_path = cfg.get("wow_path", "")
                account = cfg.get("account", "")
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

    # 4. Check Sync Key configuration
    if SYNC_KEY == "YOUR_SYNC_KEY_HERE" or not SYNC_KEY:
        print("❌ Error: You must set your secure SYNC_KEY in this script.")
        print("To get your sync key, type '!synckey' in your Discord server.")
        prompt_exit(1)

    # 5. Send data to Discord Bot API
    try:
        import requests
    except ImportError:
        print("Error: The 'requests' library is required to run this sync script.")
        print("Please install it by running: pip install requests")
        prompt_exit(1)

    payload = {
        "timestamp": int(time.time()),
        "profiles": all_profiles
    }
    
    headers = {
        "Authorization": SYNC_KEY,
        "Content-Type": "application/json"
    }

    print(f"\nUploading standings data to {SYNC_URL}...")
    try:
        response = requests.post(SYNC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            print("============================================================")
            print("🚀 Sync Successful! EPGP standings and rosters updated.")
            print("============================================================")
        else:
            print(f"❌ Sync Failed with status code: {response.status_code}")
            try:
                print(f"Error detail: {response.json().get('error', response.text)}")
            except Exception:
                print(f"Error detail: {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Sync Failed: Could not connect to the Discord Bot API server.")
        print(f"Make sure the Discord Bot is active, running, and listening at {SYNC_URL}.")
    except Exception as e:
        print(f"❌ Sync Failed: An unexpected error occurred: {e}")

    prompt_exit(0)

if __name__ == "__main__":
    main()
