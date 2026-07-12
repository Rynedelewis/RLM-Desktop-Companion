import os
import sys
import json
import re
import time
import pathlib
import requests

def locate_sv_path(wow_path):
    p = pathlib.Path(wow_path)
    if (p / "SavedVariables" / "RaidLootMatrix.lua").exists():
        return p / "SavedVariables"
    if p.name == "SavedVariables" and (p / "RaidLootMatrix.lua").exists():
        return p
    
    # Recursive search
    candidates = list(p.glob("**/SavedVariables/RaidLootMatrix.lua"))
    if candidates:
        return candidates[0].parent
        
    if p.name == "WTF":
        # Search under Account/
        candidates = list(p.glob("**/SavedVariables/RaidLootMatrix.lua"))
        if candidates:
            return candidates[0].parent
            
    return None

def extract_lua_table(content, start_pos):
    start_brace = content.find("{", start_pos)
    if start_brace == -1:
        return None
    brace_count = 1
    i = start_brace + 1
    while brace_count > 0 and i < len(content):
        c = content[i]
        if c == "{":
            brace_count += 1
        elif c == "}":
            brace_count -= 1
        i += 1
    return content[start_brace:i]

def get_rlm_profiles(wow_path):
    p = pathlib.Path(wow_path)
    candidates = list(p.glob("**/SavedVariables/RaidLootMatrix.lua"))
    all_keys = set()
    for lua_file in candidates:
        try:
            content = lua_file.read_text(encoding="utf-8", errors="replace")
            profile_keys = re.findall(r'\["([^"]+::[^"]+)"\]\s*=\s*\{', content)
            for pkey in profile_keys:
                start_idx = content.find(f'["{pkey}"]')
                if start_idx == -1:
                    continue
                profile_table = extract_lua_table(content, start_idx)
                if not profile_table:
                    continue
                roster_start = profile_table.find('["roster"]')
                if roster_start == -1:
                    continue
                roster_table = extract_lua_table(profile_table, roster_start)
                if not roster_table:
                    continue
                player_matches = re.finditer(r'\["([^"]+)"\]\s*=\s*\{', roster_table)
                active_count = 0
                for match in player_matches:
                    player_start = match.start()
                    player_table = extract_lua_table(roster_table, player_start)
                    if player_table:
                        if '["deleted"] = true' not in player_table and 'deleted = true' not in player_table:
                            active_count += 1
                    else:
                        active_count += 1
                if active_count > 0:
                    all_keys.add(pkey)
        except Exception:
            pass
    return sorted(list(all_keys))

def parse_profile_roster(text, profile_key):
    start_idx = text.find(f'["{profile_key}"]')
    if start_idx == -1:
        return []
        
    profile_table = extract_lua_table(text, start_idx)
    if not profile_table:
        return []
        
    roster_start = profile_table.find('["roster"]')
    if roster_start == -1:
        return []
        
    roster_table = extract_lua_table(profile_table, roster_start)
    if not roster_table:
        return []
        
    player_matches = re.finditer(r'\["([^"]+)"\]\s*=\s*\{', roster_table)
    
    active_players = []
    for match in player_matches:
        player_name = match.group(1)
        player_start = match.start()
        
        player_table = extract_lua_table(roster_table, player_start)
        if player_table:
            if '["deleted"] = true' not in player_table and 'deleted = true' not in player_table:
                active_players.append(player_name)
        else:
            active_players.append(player_name)
            
    return active_players

def format_lua_string(val):
    if val is None:
        return "nil"
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
    # Escape quotes
    escaped = str(val).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'"{escaped}"'

def build_lua_table(data, indent=0):
    ind = "  " * indent
    if data is None:
        return "nil"
    if isinstance(data, bool):
        return str(data).lower()
    if isinstance(data, (int, float)):
        return str(data)
    if isinstance(data, str):
        return format_lua_string(data)
    
    if isinstance(data, list):
        if not data:
            return "{}"
        lines = ["{"]
        for val in data:
            lines.append(f"{ind}  {build_lua_table(val, indent+1)},")
        lines.append(ind + "}")
        return "\n".join(lines)
        
    if isinstance(data, dict):
        if not data:
            return "{}"
        lines = ["{"]
        for key, val in data.items():
            key_part = f"[{format_lua_string(key)}]"
            lines.append(f"{ind}  {key_part} = {build_lua_table(val, indent+1)},")
        lines.append(ind + "}")
        return "\n".join(lines)
        
    return "nil"

def main():
    print("--- Starting WoW Audit Sync ---")
    
    # 1. Load config
    if getattr(sys, "frozen", False):
        addon_dir = pathlib.Path(sys.executable).parent
    else:
        addon_dir = pathlib.Path(__file__).parent
        
    config_path = addon_dir / "rlm_importer_config.json"
    
    if not config_path.exists():
        print(f"[ERROR] Config file not found at: {config_path}")
        return
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read config: {e}")
        return
        
    wow_path = config.get("wow_path", "")
    sync_targets = config.get("wowaudit_sync", [])
    
    if not wow_path:
        print("[ERROR] WoW WTF path is not configured. Please set it in RLM Importer UI.")
        return
        
    if not sync_targets:
        print("[INFO] No WoW Audit sync targets mapped. Skipping sync.")
        return
        
    p = pathlib.Path(wow_path)
    # Find all RaidLootMatrix.lua files under the WTF/Account folders
    candidates = list(p.glob("**/SavedVariables/RaidLootMatrix.lua"))
    if not candidates:
        print(f"[ERROR] Could not find any RaidLootMatrix.lua under path: {wow_path}")
        return

    # Read all files to map profile keys to their corresponding files
    file_contents = {}
    profile_to_file = {}
    for lua_file in candidates:
        try:
            content = lua_file.read_text(encoding="utf-8", errors="replace")
            file_contents[lua_file] = content
            # Extract profile keys
            keys = re.findall(r'\["([^"]+::[^"]+)"\]\s*=\s*\{', content)
            for k in keys:
                profile_to_file[k] = lua_file
        except Exception as e:
            print(f"[WARNING] Failed to pre-scan {lua_file}: {e}")

    # Group targets by their matching lua_file
    file_to_targets = {}
    for target in sync_targets:
        rlm_profile_cfg = target.get("rlm_profile_key", "").strip()
        if not rlm_profile_cfg:
            continue
        
        if " / " in rlm_profile_cfg:
            account_name, profile_key = rlm_profile_cfg.split(" / ", 1)
        else:
            account_name, profile_key = None, rlm_profile_cfg

        target_file = None
        if account_name:
            for f in candidates:
                if f.parent.parent.name == account_name:
                    target_file = f
                    break
        if not target_file:
            target_file = profile_to_file.get(profile_key) or candidates[0]

        if target_file not in file_to_targets:
            file_to_targets[target_file] = []
        file_to_targets[target_file].append((target, profile_key, rlm_profile_cfg))

    # Process files one by one
    for lua_file, targets_info in file_to_targets.items():
        print(f"\n>>> Syncing for file: {lua_file}")
        lua_content = file_contents.get(lua_file) or ""
        
        # Accumulator for this file's profiles
        sync_output = {
          "timestamp": int(time.time()),
          "profiles": {}
        }
        
        for target, rlm_profile, rlm_profile_cfg in targets_info:
            api_key = target.get("api_key", "").strip()
            team_name = target.get("wowaudit_team_name", "").strip()
            
            if not api_key or not rlm_profile:
                continue
                
            print(f"\nProcessing mapping: {team_name} -> {rlm_profile}")
            
            headers = {"Authorization": f"Bearer {api_key}"}
            base_url = "https://wowaudit.com/v1"
            
            # Query WoW Audit characters (roster)
            print("  Querying tracked roster...")
            try:
                r = requests.get(f"{base_url}/characters", headers=headers, timeout=10)
                if r.status_code != 200:
                    print(f"  [ERROR] Failed to fetch characters: {r.status_code}")
                    continue
                wa_roster = r.json()
            except Exception as e:
                print(f"  [ERROR] Characters query crashed: {e}")
                continue
                
            # Parse active characters (tracking)
            wa_active = {}
            for c in wa_roster:
                if c.get("status") == "tracking":
                    c_name = c.get("name")
                    c_realm = c.get("realm")
                    c_class = c.get("class", "").upper().replace(" ", "")
                    c_role = c.get("role", "").upper()
                    if c_role == "MELEE" or c_role == "RANGED":
                        c_role = "DAMAGER"
                        
                    full_name = f"{c_name}-{c_realm.replace(' ', '')}"
                    wa_active[full_name] = {
                        "name": c_name,
                        "realm": c_realm,
                        "class": c_class,
                        "role": c_role
                    }
                    
            # Parse local RLM roster
            local_roster = parse_profile_roster(lua_content, rlm_profile)
            print(f"  Local RLM active roster size: {len(local_roster)}")
            
            # Perform Diff
            additions = []
            reductions = []
            
            local_roster_set = {name.lower() for name in local_roster}
            for full_name, data in wa_active.items():
                if full_name.lower() not in local_roster_set:
                    additions.append({
                        "name": data["name"],
                        "realm": data["realm"],
                        "class": data["class"],
                        "role": data["role"]
                    })
                    
            wa_active_set = {name.lower() for name in wa_active.keys()}
            for full_name in local_roster:
                if full_name.lower() not in wa_active_set:
                    parts = full_name.split("-")
                    reductions.append({
                        "name": parts[0],
                        "realm": parts[1] if len(parts) > 1 else ""
                    })
                    
            print(f"  Roster Diff: +{len(additions)} additions, -{len(reductions)} reductions")
            
            # Query Wishlists
            print("  Querying wishlists...")
            wa_wishlists = {}
            try:
                r = requests.get(f"{base_url}/wishlists", headers=headers, timeout=10)
                if r.status_code == 200:
                    wishlist_data = r.json()
                    for c in wishlist_data.get("characters", []):
                        c_name = c.get("name")
                        c_realm = c.get("realm")
                        full_name = f"{c_name}-{c_realm.replace(' ', '')}"
                        
                        char_wishlist = []
                        for inst in c.get("instances", []):
                            inst_name = inst.get("name")
                            for diff in inst.get("difficulties", []):
                                diff_name = diff.get("difficulty")
                                wishlist = diff.get("wishlist", {})
                                for enc in wishlist.get("encounters", []):
                                    enc_name = enc.get("name")
                                    for item in enc.get("items", []):
                                        item_id = item.get("id")
                                        upgrade = item.get("upgrade_percentage", 0)
                                        if item_id and upgrade > 0:
                                            char_wishlist.append({
                                                "itemId": item_id,
                                                "difficulty": diff_name,
                                                "upgradePercent": upgrade,
                                                "boss": enc_name,
                                                "instance": inst_name
                                            })
                        if char_wishlist:
                            wa_wishlists[full_name] = char_wishlist
                else:
                    print(f"  [WARNING] Failed to fetch wishlists: {r.status_code}")
            except Exception as e:
                print(f"  [WARNING] Wishlists query failed: {e}")
                
            # Query Future Raids & Signups
            print("  Querying upcoming events...")
            wa_events = {}
            try:
                r = requests.get(f"{base_url}/raids", headers=headers, timeout=10)
                if r.status_code == 200:
                    raid_list = r.json().get("raids", [])
                    
                    import datetime
                    today = datetime.date.today()
                    min_date = today - datetime.timedelta(days=7)
                    max_date = today + datetime.timedelta(days=14)
                    
                    filtered_raids = []
                    for rd in raid_list:
                        r_date_str = rd.get("date")
                        try:
                            r_date = datetime.datetime.strptime(r_date_str, "%Y-%m-%d").date()
                            if min_date <= r_date <= max_date:
                                filtered_raids.append(rd)
                        except Exception:
                            continue
                            
                    print(f"  Found {len(raid_list)} upcoming raid events (syncing {len(filtered_raids)} within -7/+14 days).")
                    for rd in filtered_raids:
                        r_id = rd.get("id")
                        r_date = rd.get("date")
                        r_title = rd.get("title")
                        
                        detail_r = requests.get(f"{base_url}/raids/{r_id}", headers=headers, timeout=10)
                        if detail_r.status_code == 200:
                            detail = detail_r.json()
                            signups = []
                            for s in detail.get("signups", []):
                                char = s.get("character", {})
                                raw_status = s.get("status")
                                if not raw_status or not isinstance(raw_status, str):
                                    status = "Invited"
                                else:
                                    raw_lower = raw_status.strip().lower()
                                    if raw_lower in ["accepted", "approved", "signed_up", "present"]:
                                        status = "Accepted"
                                    elif raw_lower in ["declined", "absent", "rejected"]:
                                        status = "Declined"
                                    elif raw_lower in ["tentative", "maybe"]:
                                        status = "Tentative"
                                    else:
                                        status = "Invited"

                                signups.append({
                                    "name": char.get("name"),
                                    "realm": char.get("realm"),
                                    "class": char.get("class", "").upper().replace(" ", ""),
                                    "role": char.get("role", "").upper().replace("MELEE", "DAMAGER").replace("RANGED", "DAMAGER"),
                                    "status": status,
                                    "comment": s.get("comment")
                                })
                                
                            event_key = f"{r_title}|{r_date}"
                            wa_events[event_key] = {
                                "id": r_id,
                                "title": r_title,
                                "date": r_date,
                                "startTime": rd.get("start_time"),
                                "endTime": rd.get("end_time"),
                                "difficulty": rd.get("difficulty"),
                                "signups": signups
                            }
                else:
                    print(f"  [WARNING] Failed to fetch raids: {r.status_code}")
            except Exception as e:
                print(f"  [WARNING] Raids query failed: {e}")
                
            # Build profiles output block
            sync_output["profiles"][rlm_profile] = {
                "rosterChanges": {
                    "additions": additions,
                    "reductions": reductions
                },
                "wishlists": wa_wishlists,
                "upcomingEvents": wa_events
            }

        # Write this file's output back to SavedVariables
        print(f"\nWriting sync data back to SavedVariables for {lua_file}...")
        
        lua_sync_table = build_lua_table(sync_output, indent=0)
        lua_block = f"\nRaidLootMatrixWoWAuditSync = {lua_sync_table}\n"
        
        try:
            import datetime, shutil
            ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_path = lua_file.with_suffix(f".lua.backup_{ts_str}")
            shutil.copy2(lua_file, bak_path)
            
            idx = lua_content.rfind("\nRaidLootMatrixWoWAuditSync")
            if idx == -1:
                new_lua_content = lua_content.rstrip() + "\n" + lua_block
            else:
                new_lua_content = lua_content[:idx] + "\n" + lua_block
                
            lua_file.write_text(new_lua_content, encoding="utf-8")
            print(f"[SUCCESS] Sync data written to {lua_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save sync data to {lua_file}: {e}")
            
        # Write to static addon sync data file to allow direct updates via /reload without logout!
        try:
            # lua_file: _retail_/WTF/Account/<Account>/SavedVariables/RaidLootMatrix.lua
            # parents[4] -> _retail_
            retail_dir = lua_file.parents[4]
            addon_sync_file = retail_dir / "Interface" / "AddOns" / "RaidLootMatrix" / "sync" / "wowaudit_data.lua"
            addon_sync_file.parent.mkdir(parents=True, exist_ok=True)
            
            addon_sync_file.write_text(f"RaidLootMatrixWoWAuditSync = {lua_sync_table}\n", encoding="utf-8")
            print(f"[SUCCESS] Addon sync data file written to {addon_sync_file} (allows /reload updates!)")
        except Exception as e:
            print(f"[WARNING] Failed to write addon folder sync file: {e}")

if __name__ == "__main__":
    main()
