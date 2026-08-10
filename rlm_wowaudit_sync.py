import os
import sys
import json
import re
import time
import pathlib
import requests

import rlm_guild_providers
from rlm_guild_providers import PROVIDER_CLASSES, build_lua_table

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

def get_normalized_providers(config):
    """Normalize guild_providers list, auto-migrating legacy wowaudit_sync if necessary."""
    providers = config.get("guild_providers")
    if providers is not None:
        return providers

    # Fallback to legacy wowaudit_sync
    legacy = config.get("wowaudit_sync", [])
    normalized = []
    for item in legacy:
        normalized.append({
            "provider": "wowaudit",
            "name": item.get("wowaudit_team_name", "WoW Audit Team"),
            "api_key": item.get("api_key", ""),
            "rlm_profile_key": item.get("rlm_profile_key", ""),
            "sync_roster": True,
            "sync_calendar": True,
            "sync_wishlists": True
        })
    return normalized

def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print("--- Starting Guild Data Multi-Provider Sync ---")
    
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
        with open(config_path, "r", encoding="utf-8", errors="replace") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read config: {e}")
        return
        
    wow_path = config.get("wow_path", "")
    sync_targets = get_normalized_providers(config)
    
    if not wow_path:
        print("[ERROR] WoW WTF path is not configured. Please set it in RLM Importer UI.")
        return
        
    if not sync_targets:
        print("[INFO] No guild data sync targets mapped. Skipping sync.")
        return
        
    p = pathlib.Path(wow_path)
    candidates = list(p.glob("**/SavedVariables/RaidLootMatrix.lua"))
    if not candidates:
        print(f"[ERROR] Could not find any RaidLootMatrix.lua under path: {wow_path}")
        return

    file_contents = {}
    profile_to_file = {}
    for lua_file in candidates:
        try:
            content = lua_file.read_text(encoding="utf-8", errors="replace")
            file_contents[lua_file] = content
            keys = re.findall(r'\["([^"]+::[^"]+)"\]\s*=\s*\{', content)
            for k in keys:
                profile_to_file[k] = lua_file
        except Exception as e:
            print(f"[WARNING] Failed to pre-scan {lua_file}: {e}")

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

    for lua_file, targets_info in file_to_targets.items():
        print(f"\n>>> Syncing for file: {lua_file}")
        lua_content = file_contents.get(lua_file) or ""
        
        sync_output = {
          "timestamp": int(time.time()),
          "profiles": {}
        }
        
        for target, rlm_profile, rlm_profile_cfg in targets_info:
            provider_type = target.get("provider", "wowaudit").lower()
            api_key = target.get("api_key", "").strip()
            group_id = target.get("group_id", target.get("team_id"))
            team_name = target.get("name", "Guild Team").strip()
            
            sync_roster = target.get("sync_roster", True)
            sync_calendar = target.get("sync_calendar", True)
            sync_wishlists = target.get("sync_wishlists", False)
            sync_alts = target.get("sync_alts", True)
            
            if not api_key or not rlm_profile:
                continue
                
            print(f"Processing mapping [{provider_type.upper()}]: {team_name} -> {rlm_profile}")
            print(f"  Sync Scope: Roster={sync_roster}, Calendar={sync_calendar}, Alts={sync_alts}")
            
            provider_cls = PROVIDER_CLASSES.get(provider_type, rlm_guild_providers.WoWAuditProvider)
            
            # Fetch remote data from provider
            fetched = provider_cls.fetch_data(
                api_key=api_key,
                group_id=group_id,
                sync_roster=sync_roster,
                sync_calendar=sync_calendar,
                sync_wishlists=sync_wishlists,
                sync_alts=sync_alts
            )
            
            remote_roster = fetched.get("roster", [])
            remote_wishlists = fetched.get("wishlists", {})
            remote_events = fetched.get("upcomingEvents", {})
            
            # Perform roster diff if roster sync is enabled
            local_roster = parse_profile_roster(lua_content, rlm_profile)
            additions = []
            reductions = []
            
            if sync_roster and remote_roster:
                remote_active = {r["fullName"]: r for r in remote_roster}
                local_roster_set = {name.lower() for name in local_roster}
                
                for full_name, data in remote_active.items():
                    if full_name.lower() not in local_roster_set:
                        additions.append({
                            "name": data["name"],
                            "realm": data["realm"],
                            "class": data["class"],
                            "role": data["role"],
                            "isAlt": data.get("isAlt", False),
                            "mainName": data.get("mainName")
                        })
                        
                remote_active_set = {name.lower() for name in remote_active.keys()}
                for full_name in local_roster:
                    if full_name.lower() not in remote_active_set:
                        parts = full_name.split("-")
                        reductions.append({
                            "name": parts[0],
                            "realm": parts[1] if len(parts) > 1 else ""
                        })
                print(f"  Roster Diff: +{len(additions)} additions, -{len(reductions)} reductions")
            
            print(f"  Calendar Events Synced: {len(remote_events)}")

            sync_output["profiles"][rlm_profile] = {
                "provider": provider_type,
                "rosterChanges": {
                    "additions": additions,
                    "reductions": reductions
                },
                "wishlists": remote_wishlists,
                "upcomingEvents": remote_events
            }

        # Write sync output back to SavedVariables
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
            print(f"[SUCCESS] Sync data written to SavedVariables: {lua_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save sync data to {lua_file}: {e}")
            
        # Write to static addon sync data file for instant /reload in WoW
        try:
            retail_dir = None
            for parent in lua_file.parents:
                if parent.name in ["_retail_", "_classic_", "_beta_", "_ptr_", "_classic_era_"] or parent.name.startswith("_"):
                    retail_dir = parent
                    break
            if not retail_dir:
                retail_dir = lua_file.parents[4]
            addon_sync_file = retail_dir / "Interface" / "AddOns" / "RaidLootMatrix" / "sync" / "wowaudit_data.lua"
            addon_sync_file.parent.mkdir(parents=True, exist_ok=True)
            
            addon_sync_file.write_text(f"RaidLootMatrixWoWAuditSyncStatic = {lua_sync_table}\n", encoding="utf-8")
            print(f"[SUCCESS] Addon sync data file written to {addon_sync_file} (allows instant /reload updates!)")
        except Exception as e:
            print(f"[WARNING] Failed to write addon folder sync file: {e}")

    print("\n--- Guild Data Sync Completed Successfully! ---")

if __name__ == "__main__":
    main()
