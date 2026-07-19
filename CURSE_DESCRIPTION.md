# RaidLootMatrix (RLM)

**RaidLootMatrix (RLM)** is a comprehensive, all-in-one EPGP (Effort Points / Gear Points), loot tracking, and officer roster synchronization suite for World of Warcraft. Built for progression guilds, RLM streamlines loot distribution, automates guild member activity tracking, and links your game client with external tools like **Raider.IO** and **Discord** for ultimate coordination.

Unlike old EPGP addons, **RaidLootMatrix** includes a powerful desktop application and a custom Discord bot to automate Mythic+ weekly run tracking and present real-time EPGP standings directly in your guild's Discord server.

---

## 🚀 Key Features

### ⚖️ Advanced EPGP & Loot Tracking
* **Priority-Based Looting**: Automatically calculates a player's **Priority Ratio (PR = EP / GP)** to ensure loot goes to those who have earned it.
* **Granular EP Awards**: Award EP for **Raid Start, Raid End, Boss Kills, First Kills, Wipe Recovery**, or custom manual values.
* **Flexible GP Calculations**: Set GP costs based on item level (iLvl), slot types, and difficulty (Normal, Heroic, Mythic) with custom formulas.
* **Main & Alt Linking**: Pool EPGP across mains and alts seamlessly to encourage flexibility without losing priority.
* **Decay & Minimum GP**: Keep rosters active and competitive with configurable weekly EPGP decay rates and minimum GP floors.

### 🗳️ In-Game Loot Distribution UI
* **One-Click Loot Sessions**: Start a bidding/voting session for any item using `/rlm loot [Item Link]`.
* **Member Options**: Raiders can choose from custom options: **Need, Greed, Minor Upgrade, Offspec, or Pass**.
* **Officer Panel**: Master Looters see a prioritized list of bidders sorted by PR, their current EPGP standing, and roll outcomes.
* **Automated Awards**: Direct item distribution and automatic GP assignment upon award.

### 🔄 Peer-to-Peer Officer Synchronization
* **Database Mirroring**: Connected officers automatically synchronize their database tables in-game via a custom, secure communication protocol.
* **Conflict Resolution**: Built-in validation prevents accidental overwrites and merges data cleanly.
* **Backup Recovery**: Automated in-game and standalone backups of roster logs protect against data corruption.

### 🔑 Desktop Control Panel (Mythic+ & Discord Sync)
* **Raider.IO Integration**: Scrape your guild members' weekly Mythic+ runs directly from the Raider.IO API and import them to award EP for weekly key completion.
* **One-Click Scheduling**: Automatically set up a background scheduler task that runs silent imports on Windows startup or logon.
* **Clean UI**: A dedicated dark-themed desktop app to configure regions, account WTFs, seasons, and sync keys with ease.

### 🤖 Custom Discord Bot Integration
* **Live Leaderboards**: Query EPGP standings (`!standings`) and active roster structures (`!roster`) directly in your Discord server.
* **Secure Web Hook**: Synchronize your local WoW data to your Discord bot using a secure Authorization Key.
* **Automated Announcements**: The bot broadcasts a visual digest to your `#announcements` channel whenever standings are updated by an officer.

---

## 🛠️ Getting Started

### 1. In-game Setup
* Install **RaidLootMatrix** by putting it in your `Interface\AddOns` folder.
* Open the interface by typing `/rlm` or `/raidlootmatrix` in-game.
* Go to the **Settings** tab to configure your guild's base GP, decay percentage, and EP reward milestones.

### 2. Mythic+ Weekly Import Setup
Officers can automate Mythic+ EP awards using the companion Python desktop application:
1. Clone or download the companion tools repository from GitHub: `https://github.com/Rynedelewis/RLM-Desktop-Companion`
2. Run `Run RLM Importer UI.bat` inside the downloaded companion folder.
3. Select your WoW install path, your active region, and the current WoW season.
4. Configure your automated weekly runs import using the built-in task scheduler helper.
5. Open the in-game **Mplus** tab to review imported keys and bulk-award EPGP with a single button click.

### 3. Discord Sync Setup
To keep your guild members updated on Discord:
1. From your cloned/downloaded companion tools directory, host and start the Discord bot using `rlm_discord_bot.py`.
2. Invite the bot to your Discord server and type `!synckey` in an admin channel.
3. Paste the returned key into `rlm_discord_sync.py` in your companion tools directory.
4. Run `rlm_discord_sync.py` (or let your scheduled task handle it) to push EPGP standings directly into your Discord channel.

---

## ⌨️ Command Console

| Command | Action |
| :--- | :--- |
| `/rlm` | Opens the main RaidLootMatrix window. |
| `/rlm loot [Item Link]` | Begins a loot voting/bidding session for the linked item. |
| `/rlm sync` | Manually pulls active guild roster ranks and names from WoW. |
| `/rlm push` | Forces a database sync broadcast to other online guild officers. |
| `/rlm profile set [Name]` | Switch active roster databases (perfect for multi-team guilds). |
| `/rlm export history` | Exports your raid EPGP and loot logs in scrollable CSV/JSON format. |

---

## 📦 Dependencies & Bundled Libraries
RaidLootMatrix bundles the following high-performance libraries out-of-the-box (no separate installation needed):
* **LibStub** & **CallbackHandler-1.0** — Core library handling.
* **LibDataBroker-1.1** & **LibDBIcon-1.0** — Minimap button and broker integration.
* **AceComm-3.0** & **AceSerializer-3.0** — Secure database synchronization communications.
* **LibDeflate** — High-efficiency data compression for sync payloads.
