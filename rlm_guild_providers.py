"""
RaidLootMatrix - Multi-Source Guild Data Provider Engine
Supports pulling Roster, Calendar Events, and optional Wishlist data from:
- WoW Audit (wowaudit.com)
- WoWUtils / Viserio Cooldowns (wowutils.com / api.wowutils.com)
- Guilds of WoW (guildsofwow.com)
"""

import os
import sys
import json
import re
import time
import pathlib
import datetime
import requests

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 RLMCompanion/1.3.6"

def format_lua_string(val):
    if val is None:
        return "nil"
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
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

class WoWAuditProvider:
    """Fetcher for WoW Audit API (wowaudit.com)"""

    @staticmethod
    def test_connection(api_key, group_id=None):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json"
        }
        try:
            r = requests.get("https://wowaudit.com/v1/team", headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                team_name = data.get("name", "Unknown Team")
                realm = data.get("url", "").split("/")[-4] if "url" in data and len(data.get("url", "").split("/")) >= 4 else ""
                full_name = f"{team_name} ({realm.capitalize()})" if realm else team_name
                return True, full_name, "Success"
            elif r.status_code == 401:
                return False, None, "Invalid or expired API Key."
            elif r.status_code == 403:
                return False, None, "Access Forbidden. Ensure you are using a Team API Key."
            else:
                return False, None, f"HTTP Error {r.status_code}"
        except Exception as e:
            return False, None, f"Connection error: {e}"

    @staticmethod
    def fetch_data(api_key, group_id=None, sync_roster=True, sync_calendar=True, sync_wishlists=False, sync_alts=True):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json"
        }
        base_url = "https://wowaudit.com/v1"
        result = {
            "roster": [],
            "wishlists": {},
            "upcomingEvents": {}
        }

        # 1. Fetch Roster
        if sync_roster:
            try:
                r = requests.get(f"{base_url}/characters", headers=headers, timeout=10)
                if r.status_code == 200:
                    wa_roster = r.json()
                    for c in wa_roster:
                        if c.get("status") == "tracking":
                            c_name = c.get("name")
                            c_realm = c.get("realm", "")
                            c_class = c.get("class", "").upper().replace(" ", "")
                            c_role = c.get("role", "").upper()
                            if c_role in ["MELEE", "RANGED"]:
                                c_role = "DAMAGER"
                            
                            rank_str = str(c.get("rank", "")).lower()
                            is_alt = (rank_str == "alt")
                            
                            if is_alt and not sync_alts:
                                continue

                            result["roster"].append({
                                "name": c_name,
                                "realm": c_realm,
                                "class": c_class,
                                "role": c_role,
                                "fullName": f"{c_name}-{c_realm.replace(' ', '')}" if c_realm else c_name,
                                "isAlt": is_alt,
                                "mainName": None
                            })
            except Exception as e:
                print(f"  [ERROR] WoW Audit roster fetch failed: {e}")

        # 2. Fetch Wishlists
        if sync_wishlists:
            try:
                r = requests.get(f"{base_url}/wishlists", headers=headers, timeout=10)
                if r.status_code == 200:
                    wishlist_data = r.json()
                    for c in wishlist_data.get("characters", []):
                        c_name = c.get("name")
                        c_realm = c.get("realm", "")
                        full_name = f"{c_name}-{c_realm.replace(' ', '')}" if c_realm else c_name
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
                            result["wishlists"][full_name] = char_wishlist
            except Exception as e:
                print(f"  [ERROR] WoW Audit wishlists fetch failed: {e}")

        # 3. Fetch Calendar Raids & Signups (Filtered to -1 to +7 days)
        if sync_calendar:
            try:
                r = requests.get(f"{base_url}/raids", headers=headers, timeout=10)
                if r.status_code == 200:
                    raid_list = r.json().get("raids", [])
                    today = datetime.date.today()
                    min_date = today - datetime.timedelta(days=1)
                    max_date = today + datetime.timedelta(days=7)

                    for rd in raid_list:
                        r_date_str = rd.get("date")
                        try:
                            r_date = datetime.datetime.strptime(r_date_str, "%Y-%m-%d").date()
                            if not (min_date <= r_date <= max_date):
                                continue
                        except Exception:
                            continue

                        r_id = rd.get("id")
                        r_title = rd.get("title", "Raid Night")
                        detail_r = requests.get(f"{base_url}/raids/{r_id}", headers=headers, timeout=10)
                        signups = []
                        if detail_r.status_code == 200:
                            detail = detail_r.json()
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

                        event_key = f"{r_title}|{r_date_str}"
                        result["upcomingEvents"][event_key] = {
                            "id": r_id,
                            "title": r_title,
                            "date": r_date_str,
                            "startTime": rd.get("start_time"),
                            "endTime": rd.get("end_time"),
                            "difficulty": rd.get("difficulty"),
                            "signups": signups
                        }
            except Exception as e:
                print(f"  [ERROR] WoW Audit calendar fetch failed: {e}")

        return result


class WoWUtilsProvider:
    """Fetcher for WoWUtils / Viserio Cooldowns API (api.wowutils.com)"""

    @staticmethod
    def get_headers(api_key):
        return {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json"
        }

    @staticmethod
    def test_connection(api_key, group_id=None):
        headers = WoWUtilsProvider.get_headers(api_key)
        try:
            url = "https://api.wowutils.com/v1/groups"
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                body = r.json()
                groups = body.get("data", body) if isinstance(body, dict) else body
                if isinstance(groups, list) and groups:
                    target_g = groups[0]
                    if group_id:
                        for g in groups:
                            if str(g.get("groupId") or g.get("id")) == str(group_id):
                                target_g = g
                                break
                    g_name = target_g.get("name", f"Group {target_g.get('groupId') or target_g.get('id')}")
                    guild_info = target_g.get("guild", {})
                    if isinstance(guild_info, dict) and guild_info.get("realm"):
                        g_name = f"{g_name} ({guild_info.get('realm').capitalize()})"
                    return True, g_name, "Success"
                return True, "WoWUtils Account", "Success"
            elif r.status_code == 401:
                return False, None, "Invalid WoWUtils API Key."
            elif r.status_code == 403:
                return False, None, "Access Forbidden (Check API key permissions)."
            else:
                return False, None, f"HTTP Error {r.status_code}"
        except Exception as e:
            return False, None, f"Connection error: {e}"

    @staticmethod
    def fetch_data(api_key, group_id=None, sync_roster=True, sync_calendar=True, sync_wishlists=False, sync_alts=True):
        headers = WoWUtilsProvider.get_headers(api_key)
        base_url = "https://api.wowutils.com/v1"
        result = {
            "roster": [],
            "wishlists": {},
            "upcomingEvents": {}
        }

        # Determine target group ID if not provided
        if not group_id:
            try:
                r = requests.get(f"{base_url}/groups", headers=headers, timeout=8)
                if r.status_code == 200:
                    body = r.json()
                    groups = body.get("data", body) if isinstance(body, dict) else body
                    if isinstance(groups, list) and groups:
                        group_id = groups[0].get("groupId") or groups[0].get("id")
            except Exception:
                pass

        if not group_id:
            print("  [ERROR] WoWUtils group_id is required or could not be determined.")
            return result

        member_map = {}

        # 1. Fetch Roster
        try:
            r = requests.get(f"{base_url}/groups/{group_id}/roster", headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                members = data.get("members", [])
                for m in members:
                    mid = m.get("memberId")
                    main_slug = m.get("mainCharacter")
                    main_char_obj = None
                    chars = m.get("characters", [])
                    
                    for c in chars:
                        if isinstance(c, dict) and (c.get("playerId") == main_slug or c.get("status") == "main"):
                            main_char_obj = c
                            break
                    if not main_char_obj and chars and isinstance(chars[0], dict):
                        main_char_obj = chars[0]
                    
                    if mid and main_char_obj:
                        member_map[mid] = main_char_obj

                    main_full_name = None
                    if main_char_obj:
                        m_realm = main_char_obj.get("realm", "").replace(" ", "")
                        main_full_name = f"{main_char_obj.get('name')}-{m_realm}" if m_realm else main_char_obj.get('name')

                    if sync_roster:
                        for c in chars:
                            if isinstance(c, dict):
                                c_name = c.get("name")
                                c_realm = c.get("realm", "")
                                c_class = c.get("class", "").upper().replace(" ", "")
                                c_role = (c.get("role") or m.get("mainRole") or "").upper()
                                if c_role in ["MELEE", "RANGED"]:
                                    c_role = "DAMAGER"
                                
                                fullName = f"{c_name}-{c_realm.replace(' ', '')}" if c_realm else c_name
                                is_alt = (c.get("status") == "alt") or (main_full_name and fullName != main_full_name)
                                
                                if is_alt and not sync_alts:
                                    continue

                                if c_name:
                                    result["roster"].append({
                                        "name": c_name,
                                        "realm": c_realm,
                                        "class": c_class,
                                        "role": c_role,
                                        "fullName": fullName,
                                        "isAlt": is_alt,
                                        "mainName": main_full_name if is_alt else None
                                    })
        except Exception as e:
            print(f"  [ERROR] WoWUtils roster fetch failed: {e}")

        # 2. Fetch Calendar Events (Filtered to -1 to +7 days, deduplicated signups & cleaned realm names)
        if sync_calendar:
            try:
                r = requests.get(f"{base_url}/groups/{group_id}/calendar-events", headers=headers, timeout=10)
                if r.status_code == 200:
                    body = r.json()
                    events = body.get("data", body) if isinstance(body, dict) else body
                    if isinstance(events, list):
                        today = datetime.date.today()
                        min_date = today - datetime.timedelta(days=1)
                        max_date = today + datetime.timedelta(days=7)

                        for ev in events:
                            ev_id = ev.get("eventId") or ev.get("id")
                            ev_title = ev.get("name") or ev.get("title", "Guild Event")
                            ev_date_str = ev.get("date", "")[:10]
                            
                            try:
                                ev_date = datetime.datetime.strptime(ev_date_str, "%Y-%m-%d").date()
                                if not (min_date <= ev_date <= max_date):
                                    continue
                            except Exception:
                                continue

                            signups_map = {}
                            for s in ev.get("signups", []):
                                mid = s.get("memberId")
                                disp = str(s.get("displayName") or "").strip()
                                c_obj = member_map.get(mid)
                                
                                raw_name = c_obj.get("name") if c_obj else disp
                                raw_realm = c_obj.get("realm", "") if c_obj else ""

                                # If raw_name contains trailing '-Realm' (e.g. 'Dom-Dentarg'), split cleanly
                                if "-" in raw_name and not raw_realm:
                                    parts = raw_name.split("-", 1)
                                    c_name, c_realm = parts[0].strip(), parts[1].strip()
                                else:
                                    c_name, c_realm = raw_name.strip(), raw_realm.strip()

                                c_class = (c_obj.get("class") if c_obj else "").upper().replace(" ", "")
                                c_role = (s.get("role") or (c_obj.get("role") if c_obj else "") or "").upper().replace("MELEE", "DAMAGER").replace("RANGED", "DAMAGER")

                                raw_status = str(s.get("status", "")).strip().lower()
                                responded = bool(s.get("responded", False))

                                if not responded or raw_status == "pending":
                                    status = "Invited"
                                elif raw_status in ["present", "accepted", "confirmed", "signed_up", "approved"]:
                                    status = "Accepted"
                                elif raw_status in ["absent", "declined", "out", "rejected"]:
                                    status = "Declined"
                                elif raw_status in ["tentative", "maybe", "standby", "late", "bench"]:
                                    status = "Tentative"
                                else:
                                    status = "Invited"

                                char_key = c_name.lower()
                                
                                # Deduplication logic: prefer active/responded statuses over 'Invited'
                                new_entry = {
                                    "name": c_name,
                                    "realm": c_realm,
                                    "class": c_class,
                                    "role": c_role,
                                    "status": status,
                                    "comment": s.get("comment")
                                }
                                
                                if char_key not in signups_map:
                                    signups_map[char_key] = new_entry
                                else:
                                    existing = signups_map[char_key]
                                    if existing["status"] == "Invited" and status != "Invited":
                                        signups_map[char_key] = new_entry

                            event_key = f"{ev_title}|{ev_date_str}"
                            result["upcomingEvents"][event_key] = {
                                "id": ev_id,
                                "title": ev_title,
                                "date": ev_date_str,
                                "startTime": ev.get("startTime"),
                                "endTime": ev.get("endTime"),
                                "difficulty": ev.get("difficulty"),
                                "signups": list(signups_map.values())
                            }
            except Exception as e:
                print(f"  [WARNING] WoWUtils calendar-events fetch notice: {e}")

        return result


class GuildsOfWoWProvider:
    """Fetcher for Guilds of WoW API (guildsofwow.com)"""

    @staticmethod
    def test_connection(api_key, group_id=None):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json"
        }
        try:
            r = requests.get("https://guildsofwow.com/api/v1/guild", headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                g_name = data.get("name", "Guilds of WoW Guild")
                return True, g_name, "Success"
            elif r.status_code == 401:
                return False, None, "Invalid Guilds of WoW API key."
            else:
                return True, "Guilds of WoW", "Configured"
        except Exception as e:
            return False, None, f"Connection error: {e}"

    @staticmethod
    def fetch_data(api_key, group_id=None, sync_roster=True, sync_calendar=True, sync_wishlists=False):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json"
        }
        base_url = "https://guildsofwow.com/api/v1"
        result = {
            "roster": [],
            "wishlists": {},
            "upcomingEvents": {}
        }
        try:
            if sync_roster:
                r = requests.get(f"{base_url}/roster", headers=headers, timeout=10)
                if r.status_code == 200:
                    members = r.json()
                    for m in members:
                        c_name = m.get("name")
                        c_realm = m.get("realm", "")
                        is_alt = (m.get("is_alt") or m.get("rank") == "Alt")
                        if c_name:
                            result["roster"].append({
                                "name": c_name,
                                "realm": c_realm,
                                "class": m.get("class", "").upper(),
                                "role": m.get("role", "").upper(),
                                "fullName": f"{c_name}-{c_realm}" if c_realm else c_name,
                                "isAlt": is_alt,
                                "mainName": m.get("main_name") if is_alt else None
                            })
        except Exception as e:
            print(f"  [INFO] Guilds of WoW roster sync: {e}")

        return result

PROVIDER_CLASSES = {
    "wowaudit": WoWAuditProvider,
    "wowutils": WoWUtilsProvider,
    "guildsofwow": GuildsOfWoWProvider
}
