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
            title="📢 RaidLootMatrix Companion v1.5.5 - Update & Stability Notice",
            description=(
                "Hey everyone! 👋 Thanks for your patience while we worked through a few initial launch hiccups with the new standalone desktop companion.\n\n"
                "We've been hard at work troubleshooting and squashing startup & packaging bugs over the last few iterations, and we're happy to report that **v1.5.5 is now live and stable**! 🎉\n\n"
                "✨ **v1.5.5 Update Highlights:**\n"
                "• **100% Self-Contained Executable:** Run directly anywhere on your PC without missing DLL errors or extra folders.\n"
                "• **Seamless In-App Auto-Updates:** Future updates can now be downloaded and applied with a single click right from inside the app.\n"
                "• **Full Gold & Obsidian UI Branding:** Polished titlebars, taskbar icons, and dark theme modals.\n\n"
                "📥 **Download & Upgrade to v1.5.5:**\n"
                "If you experienced any errors on earlier 1.5.x builds, grab the fresh **v1.5.5** executable directly from GitHub Releases:\n"
                "👉 **[Download RLM Companion v1.5.5 on GitHub](https://github.com/Rynedelewis/RLM-Desktop-Companion/releases/tag/v1.5.5)**\n\n"
                "Happy raiding and key pushing! ⚔️"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="RaidLootMatrix Helper Bot • Official Announcement")

        await target_ch.send(embed=embed)
        print(f"[SUCCESS] Posted announcement to #{target_ch.name}!")
        await self.close()

if __name__ == "__main__":
    token = load_bot_token()
    if not token:
        print("Error: Could not load DISCORD_BOT_TOKEN from .env")
        sys.exit(1)
    
    bot = AnnouncementBot()
    bot.run(token)
