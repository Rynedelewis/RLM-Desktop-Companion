import os
import sys
import asyncio
import discord

ENV_PATH = r"C:\Users\rynec\OneDrive\Documents\RLM-Desktop-Companion\.env"
TARGET_GUILD_ID = 1519423163321290783

def load_bot_token():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "DISCORD_BOT_TOKEN":
                        return v.strip().strip('"').strip("'")
    return None

class AnnouncementBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        guild = self.get_guild(TARGET_GUILD_ID)
        if not guild:
            print(f"Error: Bot is not in guild with ID {TARGET_GUILD_ID}")
            await self.close()
            return

        target_ch = discord.utils.get(guild.text_channels, name="announcements") or discord.utils.get(guild.text_channels, name="announcement")
        if not target_ch:
            print("Available text channels:")
            for ch in guild.text_channels:
                print(f" - #{ch.name}")
            target_ch = discord.utils.get(guild.text_channels, name="general")

        if not target_ch:
            print("Error: Could not find suitable announcement channel.")
            await self.close()
            return

        print(f"Posting announcement to #{target_ch.name}...")

        embed = discord.Embed(
            title="📢 RaidLootMatrix Companion v1.5.0 Released!",
            description=(
                "Hey everyone! 👋 We just dropped **RaidLootMatrix Desktop Companion v1.5.0**!\n\n"
                "Starting with v1.5.0, we're transitioning to a brand-new, self-contained **Windows Setup Installer** (`.exe`) and **macOS Package** (`.dmg`) hosted directly on GitHub!\n\n"
                "✨ **What's New in v1.5.0:**\n"
                "• **Standalone Setup Installer:** Easy single-click installation with Start Menu shortcuts and full Windows uninstaller integration.\n"
                "• **Automated Discord Standings & M+ Leaderboards:** The bot now automatically formats, posts, and updates pinned EPGP Standings and Mythic+ Leaderboards in your server channels!\n"
                "• **Clean Channel Scoping:** Dropdowns remain completely blank until a valid Sync Key is linked to your team.\n\n"
                "📥 **How to Download & Upgrade:**\n"
                "Head over to our official GitHub Releases page to download the latest setup file:\n"
                "👉 **[Download RLM Companion v1.5.0 on GitHub Releases](https://github.com/Rynedelewis/RLM-Desktop-Companion/releases/tag/v1.5.0)**\n\n"
                "Happy raiding and key pushing! ⚔️"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="RaidLootMatrix Helper Bot • Official Announcement")

        await target_ch.send(embed=embed)
        print(f"🟢 Successfully posted announcement to #{target_ch.name}!")
        await self.close()

if __name__ == "__main__":
    token = load_bot_token()
    if not token:
        print("Error: Could not load DISCORD_BOT_TOKEN from .env")
        sys.exit(1)
    
    bot = AnnouncementBot()
    bot.run(token)
