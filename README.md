# RaidLootMatrix Desktop Companion & Discord Bot

This repository contains the companion desktop tools and Discord integration suite for the **RaidLootMatrix (RLM)** World of Warcraft addon. 

These tools allow guild officers to:
1. **Scrape Raider.IO** weekly Mythic+ runs for the entire roster and import them directly into WoW to automate EP awards.
2. **Synchronize EPGP standings** to a custom Discord Bot.
3. **Query EPGP standings** and active rosters directly inside Discord using bot commands (`!standings`, `!roster`).

---

## 🚀 Companion Tool Ecosystem

* **`rlm_importer_ui.py`**: A Tkinter dark-theme GUI control panel to configure your WoW directory, region, account name, and setup automated tasks.
* **`raidlootmatrix_mplus.py`**: Queries the Raider.IO API for your active roster players' runs for the current/last reset week and writes them into your WoW SavedVariables.
* **`rlm_discord_sync.py`**: Parses your WoW SavedVariables roster and EPGP values, pushing them to your Discord bot's sync server.
* **`rlm_discord_bot.py`**: A custom Discord bot that hosts an API web server (aiohttp) to receive standings data, notifies guild channels on sync, and handles member commands.

---

## 📋 Prerequisites

* **Python 3.10+** installed on your system.
* **Required Libraries**: Install dependencies using pip:
  ```bash
  pip install requests discord.py aiohttp
  ```

---

## 🛠️ Setup Instructions

### 1. Mythic+ Weekly Import Setup
1. Double-click `Run RLM Importer UI.bat` to launch the Desktop Control Panel.
2. Enter your **Account Name** (WTF subfolder name), **Region** (us/eu), and **Season** slug.
3. Browse and select your **World of Warcraft WTF SavedVariables directory** (e.g., `_retail_\WTF\Account\<YourAccountName>\SavedVariables`).
4. Click **Save Settings**.
5. Use the **Task Scheduler** section to set up automatic, silent background imports (runs on logon/startup).
6. In-game, open the `/rlm` interface, go to the **Mplus** page, and click **Award EP** to distribute points based on your settings.

### 2. Discord bot & Standing Sync Setup
1. Invite your bot to your Discord server (ensure it has permissions to send messages and embed links).
2. Host `rlm_discord_bot.py` on a server or your local machine (listens on port `8080` by default).
3. Type `!synckey` in an administrator Discord channel to receive your secure API Authorization Key via DM.
4. Open `rlm_discord_sync.py` and paste your key into the `SYNC_KEY` configuration constant near the top.
5. Run `rlm_discord_sync.py` to push your standings to Discord. The bot will automatically post a standing summary in your `#announcements` or `#general` channel.

---

## 🤖 Discord Bot Commands

* `!rlmhelp` / `!help` — Lists all available bot commands.
* `!standings [team]` — Displays EPGP priority ratios and standings for the top 25 main characters.
* `!roster [team]` — Lists active characters, classes, and main/alt relationships.
* `!synckey` — *(Admins Only)* Sends the server's unique sync key via DM.

---

## 📊 Data Flow & SavedVariables Injection

The companion app acts as a bridge between web APIs and your local World of Warcraft client.

### 1. Mythic+ Data (`raidlootmatrix_mplus.py`)
* **Grabs**: Character run profiles from the **Raider.IO API** for all active roster members. It extracts the dungeon name, key level, timed status, and completion timestamp.
* **Injects**: Writes this raw run data into `RaidLootMatrixMplusImport` inside your WoW SavedVariables file:
  `WTF\Account\<AccountName>\SavedVariables\RaidLootMatrix.lua`.
* *Note*: The companion app does *not* modify EPGP values directly. Point calculations are performed in-game by the addon using the imported run log.

### 2. WoW Audit Data (`rlm_wowaudit_sync.py`)
* **Grabs**: Roster additions/reductions, wishlists, and upcoming raid event schedules (dates, start/end times, difficulty, signups, and RSVP statuses) from the **WoW Audit API**.
* **Injects**: Writes this data into `RaidLootMatrixWoWAuditSync` inside your local SavedVariables, and also saves it to `Interface\AddOns\RaidLootMatrix\sync\wowaudit_data.lua` as `RaidLootMatrixWoWAuditSyncStatic`. This second write enables loading the data in-game with a simple `/reload` command, bypassing WoW logout requirements.

---

## 📅 WoW Audit & In-Game Calendar Sync Guide

You can easily commit your WoW Audit and Discord calendar events directly into the Blizzard in-game calendar using the RaidLootMatrix addon UI:

1. **Perform a Desktop Sync**: Launch the companion app and perform a WoW Audit sync (or let the automated scheduler handle it). This fetches upcoming raids and sign-ups.
2. **Load the Addon**: Log in to World of Warcraft (or type `/reload` if you are already logged in).
3. **Open the Calendar Tab**: Type `/rlm` in chat and click the **Calendar** tab. You will see a list of upcoming WoW Audit events (within a -7 to +14 day window).
4. **Create or Sync Events**:
   * **If the event does not exist in-game**: Select the event and click **Sync Event** (or **Create Event**). The addon will open the WoW Calendar, create a Player Event, set the correct title/description, and sequentially invite all players who signed up on WoW Audit (with a 2.2s delay to prevent connection rate-limiting).
   * **If the event already exists**: Select it and click **Sync RSVPs**. The addon will scan the in-game invite list, automatically invite any missing players, and set their in-game RSVPs (Accepted, Declined, Tentative) to match their WoW Audit signup status.

