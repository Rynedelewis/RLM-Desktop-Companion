import os
import sys
import json
import secrets
import asyncio
import discord
from discord.ext import commands
from aiohttp import web

# Load local .env file if it exists (for local testing/hosting)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "DISCORD_BOT_TOKEN":
                        os.environ["DISCORD_BOT_TOKEN"] = v.strip().strip('"').strip("'")
    except Exception:
        pass

TOKEN = os.environ.get("DISCORD_BOT_TOKEN") or "YOUR_DISCORD_BOT_TOKEN_HERE"
DB_FILE = os.environ.get("RLM_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "rlm_bot_db.json"))

# Helper functions to load/save JSON database
def load_db():
    if not os.path.exists(DB_FILE):
        return {"guilds": {}}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"guilds": {}}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        print(f"Error saving database: {e}")

def get_or_create_sync_key(guild_id):
    db = load_db()
    guild_id_str = str(guild_id)
    if guild_id_str not in db["guilds"]:
        db["guilds"][guild_id_str] = {}
    
    guild_data = db["guilds"][guild_id_str]
    if "sync_key" not in guild_data or not guild_data["sync_key"]:
        # Generate a secure 16-character hex token
        guild_data["sync_key"] = f"rlm_key_{secrets.token_hex(8)}"
        save_db(db)
    
    return guild_data["sync_key"]

def get_guild_by_sync_key(key):
    db = load_db()
    for guild_id, data in db["guilds"].items():
        if data.get("sync_key") == key:
            return guild_id
    return None

def update_guild_data(guild_id, payload):
    db = load_db()
    guild_id_str = str(guild_id)
    if guild_id_str not in db["guilds"]:
        db["guilds"][guild_id_str] = {}
    
    db["guilds"][guild_id_str]["profiles"] = payload.get("profiles", {})
    db["guilds"][guild_id_str]["last_sync"] = payload.get("timestamp", 0)
    save_db(db)

# Custom Bot class to integrate the HTTP sync API server into the event loop
class RLMHelperBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.site = None

    async def setup_hook(self):
        # Start HTTP server concurrently in the background
        self.loop.create_task(self.start_http_server())

    async def start_http_server(self):
        app = web.Application()
        app.add_routes([
            web.post('/api/sync', self.handle_sync_post),
            web.get('/terms', self.handle_terms),
            web.get('/privacy', self.handle_privacy)
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Bind dynamically to the port assigned by the cloud provider, defaulting to 8080
        port = int(os.environ.get("PORT", 8080))
        self.site = web.TCPSite(runner, '0.0.0.0', port)
        await self.site.start()
        print(f"HTTP Sync API server started on http://0.0.0.0:{port}")

    async def handle_sync_post(self, request):
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return web.json_response({"error": "Missing Authorization header"}, status=401)
            
            # Find the guild corresponding to this key
            guild_id = get_guild_by_sync_key(auth_header)
            if not guild_id:
                return web.json_response({"error": "Invalid Authorization token"}, status=403)
            
            payload = await request.json()
            update_guild_data(guild_id, payload)
            
            # Notify in the server channel
            guild = self.get_guild(int(guild_id))
            if guild:
                channel = discord.utils.get(guild.text_channels, name="announcements")
                if not channel:
                    channel = discord.utils.get(guild.text_channels, name="general")
                
                if channel:
                    embed = discord.Embed(
                        title="🔄 RaidLootMatrix Standing Synced",
                        description=(
                            "The guild's EPGP standings and rosters have been successfully "
                            "updated via the desktop sync client."
                        ),
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Use !standings or !roster to view the live data.")
                    await channel.send(embed=embed)
            
            return web.json_response({"success": True, "message": "EPGP data synced successfully!"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_terms(self, request):
        html = """
        <html>
        <head>
            <title>RaidLootMatrix Helper - Terms of Service</title>
            <style>
                body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }
                h1 { color: #ff9900; }
                h2 { color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
            </style>
        </head>
        <body>
            <h1>Terms of Service</h1>
            <p><strong>Effective Date: June 2026</strong></p>
            <p>Welcome to RaidLootMatrix Helper ("the Bot"). By adding the Bot to your Discord server or using its commands, you agree to these Terms of Service.</p>
            
            <h2>1. Permitted Use</h2>
            <p>The Bot is designed to sync and display EPGP (Effort Points / Gear Points) standings and rosters for World of Warcraft guilds. You agree to use the Bot only for its intended gaming utility purposes.</p>
            
            <h2>2. No Warranties</h2>
            <p>The Bot is provided "as is" and "as available". We do not guarantee that the Bot will be completely error-free or online 24/7.</p>
            
            <h2>3. Limitation of Liability</h2>
            <p>In no event shall the developers or hosts of the Bot be held liable for any damages resulting from the use or inability to use the Bot.</p>
            
            <h2>4. Modifications</h2>
            <p>We reserve the right to update these terms at any time. Continued use of the Bot constitutes acceptance of the updated terms.</p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_privacy(self, request):
        html = """
        <html>
        <head>
            <title>RaidLootMatrix Helper - Privacy Policy</title>
            <style>
                body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }
                h1 { color: #2ecc71; }
                h2 { color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
            </style>
        </head>
        <body>
            <h1>Privacy Policy</h1>
            <p><strong>Effective Date: June 2026</strong></p>
            <p>Your privacy is important to us. This Privacy Policy describes how RaidLootMatrix Helper ("the Bot") handles data.</p>
            
            <h2>1. Information We Collect</h2>
            <p>The Bot collects and stores:</p>
            <ul>
                <li>Discord Guild (Server) IDs to link roster data.</li>
                <li>Character names, classes, EPGP values (Effort Points, Gear Points), and Alt/Main relationships uploaded from your World of Warcraft addon files.</li>
            </ul>
            
            <h2>2. How We Use Information</h2>
            <p>This information is used strictly to display EPGP standings and roster lists inside your Discord server when users run the corresponding commands.</p>
            
            <h2>3. Data Retention and Security</h2>
            <p>We store this data in a secure database on our hosting provider (Railway). We do not share, sell, or distribute this data to any third parties.</p>
            
            <h2>4. Data Deletion</h2>
            <p>If you wish to delete your server's EPGP data, you can contact the bot host or remove the bot from your server. Data associated with your server will be deleted upon request.</p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

# Initialize bot with default intents (no privileged Server Members intent required!)
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

bot = RLMHelperBot(command_prefix="!", intents=intents)
bot.remove_command('help')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("RLM Helper Bot is active and running!")
    print("Command prefix is set to '!'")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s) globally.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")
    # Permissions=85056 corresponds to: View Channels, Send Messages, Embed Links, Read History, Add Reactions. No admin rights.
    print(f"Invite Link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=85056&scope=bot%20applications.commands")
    print("="*60)

# Command Error Handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Error:** You must have **Administrator** permissions to run this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd_name = ctx.command.name
        if ctx.command.parent:
            full_name = f"{ctx.command.parent.name} {cmd_name}"
        else:
            full_name = cmd_name
        await ctx.send(f"❌ **Error:** Please specify the team name. Example: `!{full_name} Main Roster`")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(f"❌ An error occurred: `{error}`")

# Helper function to print command guide
async def rlm_help_internal(ctx):
    embed = discord.Embed(
        title="RaidLootMatrix Helper Bot Command Guide",
        description="Interact with the RaidLootMatrix bot using the following commands:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="`/rlm help` or `!rlm help`",
        value="Shows this list of available commands.",
        inline=False
    )
    embed.add_field(
        name="`/rlm synckey` or `!rlm synckey`",
        value="*(Administrators Only)* Sends your server's secure API token to you via Direct Message.",
        inline=False
    )
    embed.add_field(
        name="`/rlm standings <team>` or `!rlm standings <team>`",
        value="Displays EPGP standing info for a team roster.",
        inline=False
    )
    embed.add_field(
        name="`/rlm roster <team>` or `!rlm roster <team>`",
        value="Lists mains and alts for the active roster profile.",
        inline=False
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    embed.set_footer(text="RaidLootMatrix Bot v1.2.0")
    await ctx.send(embed=embed)

# Parent Hybrid Group
@bot.hybrid_group(name="rlm", description="RaidLootMatrix command group")
async def rlm(ctx):
    """Parent command group for RaidLootMatrix. Run `/rlm help` for usage."""
    if ctx.invoked_subcommand is None:
        await rlm_help_internal(ctx)

# 1. Custom Help Command
@rlm.command(name="help", description="Displays available commands for RaidLootMatrix Bot")
async def rlm_help(ctx):
    await rlm_help_internal(ctx)

# 2. Sync Key Generator Command
@rlm.command(name="synckey", aliases=["sync-key"], description="Sends the server's unique sync key to the administrator via DM")
@commands.has_permissions(administrator=True)
async def sync_key(ctx):
    """Sends the server's unique sync key to the administrator via DM"""
    guild_id = ctx.guild.id
    guild_name = ctx.guild.name
    
    key = get_or_create_sync_key(guild_id)
    
    try:
        embed = discord.Embed(
            title="🔑 RaidLootMatrix Sync Authorization Key",
            description=(
                f"Here is your secure synchronization key for **{guild_name}**.\n"
                "Keep this key secret! Anyone with this key can upload and overwrite "
                "your server's standings."
            ),
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Your Sync Key",
            value=f"`{key}`",
            inline=False
        )
        embed.add_field(
            name="How to use it",
            value="Paste this key into your local `rlm_discord_sync.py` script as your `SYNC_KEY`.",
            inline=False
        )
        await ctx.author.send(embed=embed)
        await ctx.send("🔑 **Sync Key Sent:** Check your Direct Messages for your secure synchronization key.")
    except discord.Forbidden:
        await ctx.send(
            "❌ **Error:** I couldn't send you a Direct Message. "
            "Please verify that you have 'Allow direct messages from server members' enabled in your privacy settings."
        )

# 3. Standings Query Command
@rlm.command(name="standings", description="Displays EPGP standings (synced)")
@discord.app_commands.describe(team_name="The name of the team roster to query")
async def standings(ctx, *, team_name: str):
    """Displays EPGP standings (synced)"""
    print(f"DEBUG: standings called. ctx.guild.id={ctx.guild.id}, ctx.guild.name={ctx.guild.name}, team_name={team_name}")
    db = load_db()
    guild_id_str = str(ctx.guild.id)
    
    guild_entry = db["guilds"].get(guild_id_str, {})
    profiles = guild_entry.get("profiles", {})
    
    active_roster = None
    source_profile = None
    
    if profiles:
        # Look for a specific profile match
        for profile_key, profile_data in profiles.items():
            if team_name.lower() in profile_key.lower():
                active_roster = profile_data
                source_profile = profile_key
                break
    
    # If we have synced data, render it!
    if active_roster:
        embed = discord.Embed(
            title="RaidLootMatrix Standings",
            description=f"Active EPGP Standings (Profile: **{source_profile.split('::')[-1]}**)",
            color=discord.Color.gold()
        )
        
        # Sort players by PR descending (EP / GP)
        player_list = []
        for name, data in active_roster.items():
            if data.get("isAlt", False):
                continue  # Standings show main characters
            ep = data.get("ep", 0)
            gp = data.get("gp", 1)  # avoid division by zero
            pr = ep / max(1, gp)
            player_list.append((name, data.get("class", "Unknown"), ep, gp, pr))
        
        player_list.sort(key=lambda x: x[4], reverse=True)
        
        if not player_list:
            await ctx.send("ℹ️ No main characters found in the roster database.")
            return

        # Limit to top 45 players max to fit within embed limits
        top_players = player_list[:45]
        
        chunk_size = 15
        for i in range(0, len(top_players), chunk_size):
            chunk = top_players[i:i+chunk_size]
            table_content = "```\nName            Class             EP      GP      PR\n"
            table_content += "-" * 52 + "\n"
            for name, cl, ep, gp, pr in chunk:
                clean_name = name.split("-")[0]
                table_content += f"{clean_name:<15} {cl:<17} {int(ep):<7} {int(gp):<7} {pr:.2f}\n"
            table_content += "```"
            
            field_name = f"Current Standings (Rank {i+1}-{i+len(chunk)})"
            embed.add_field(name=field_name, value=table_content, inline=False)
        embed.set_footer(text=f"Last Synced: {ctx.guild.me.display_name}")
        await ctx.send(embed=embed)
        return
        
    # No match found -> handle error or empty database gracefully
    if not profiles:
        await ctx.send(
            "❌ **Error:** No synchronization data has been uploaded to this server yet.\n"
            "Please setup and run the RLM Desktop Companion app to sync your in-game roster!"
        )
    else:
        available = ", ".join([f"`{pk.split('::')[-1]}`" for pk in profiles.keys()])
        await ctx.send(
            f"❌ **Error:** Could not find a standings profile matching '**{team_name}**'.\n"
            f"Available synced profiles: {available}"
        )

# 4. Roster Query Command
@rlm.command(name="roster", description="Displays roster profiles and alts (synced)")
@discord.app_commands.describe(team_name="The name of the team roster to query")
async def roster(ctx, *, team_name: str):
    """Displays roster profiles and alts (synced)"""
    print(f"DEBUG: roster called. ctx.guild.id={ctx.guild.id}, ctx.guild.name={ctx.guild.name}, team_name={team_name}")
    db = load_db()
    guild_id_str = str(ctx.guild.id)
    
    guild_entry = db["guilds"].get(guild_id_str, {})
    profiles = guild_entry.get("profiles", {})
    
    active_roster = None
    source_profile = None
    
    if profiles:
        # Look for a specific profile match
        for profile_key, profile_data in profiles.items():
            if team_name.lower() in profile_key.lower():
                active_roster = profile_data
                source_profile = profile_key
                break
                
    if active_roster:
        embed = discord.Embed(
            title="RaidLootMatrix Roster Profiles",
            description=f"Synced Roster Details (Profile: **{source_profile.split('::')[-1]}**)",
            color=discord.Color.green()
        )
        
        # Group alts by main character
        mains = {}
        for name, data in active_roster.items():
            if data.get("isAlt", False):
                main_name = data.get("mainName", "")
                if main_name:
                    mains.setdefault(main_name, []).append(name)
            else:
                mains.setdefault(name, [])
        
        # Format and chunk the mains & alts output to fit within the 1024-char limit per field
        current_chunk = ""
        chunk_index = 1
        
        for main, alts in sorted(mains.items()):
            clean_main = main.split("-")[0]
            main_class = active_roster.get(main, {}).get("class", "Unknown")
            
            if alts:
                clean_alts = ", ".join([a.split("-")[0] for a in alts])
                line = f"• **{clean_main}** ({main_class}) — *Alts: {clean_alts}*\n"
            else:
                line = f"• **{clean_main}** ({main_class})\n"
            
            if len(current_chunk) + len(line) > 1000:
                embed.add_field(
                    name=f"Mains & Linked Alts (Part {chunk_index})" if chunk_index > 1 or len(mains) > 15 else "Mains & Linked Alts", 
                    value=current_chunk or "No members registered.", 
                    inline=False
                )
                current_chunk = line
                chunk_index += 1
            else:
                current_chunk += line
                
        if current_chunk:
            embed.add_field(
                name=f"Mains & Linked Alts (Part {chunk_index})" if chunk_index > 1 else "Mains & Linked Alts", 
                value=current_chunk, 
                inline=False
            )
        embed.set_footer(text="Synced via RaidLootMatrix Desktop Sync.")
        await ctx.send(embed=embed)
        return
 
    # No match found -> handle error or empty database gracefully
    if not profiles:
        await ctx.send(
            "❌ **Error:** No synchronization data has been uploaded to this server yet.\n"
            "Please setup and run the RLM Desktop Companion app to sync your in-game roster!"
        )
    else:
        available = ", ".join([f"`{pk.split('::')[-1]}`" for pk in profiles.keys()])
        await ctx.send(
            f"❌ **Error:** Could not find a roster profile matching '**{team_name}**'.\n"
            f"Available synced profiles: {available}"
        )

if __name__ == "__main__":
    if TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE" or not TOKEN:
        print("Error: You must replace the TOKEN variable with your actual bot token.")
        input("\nPress Enter to exit...")
        sys.exit(1)
        
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord Bot Token.")
    except discord.errors.ClientException as ce:
        print(f"Client Error occurred: {ce}")
    except Exception as e:
        print(f"Error occurred: {e}")
            
    input("\nPress Enter to exit...")
