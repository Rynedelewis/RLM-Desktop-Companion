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
            
            # Notify block removed to prevent channel spam on sync.
            pass
            
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

# Slash command localization mappings
RLM_NAME_LOCALIZATIONS = {"zh-CN": "rlm", "zh-TW": "rlm", "es-ES": "rlm"}
RLM_DESC_LOCALIZATIONS = {"zh-CN": "RaidLootMatrix 命令组", "zh-TW": "RaidLootMatrix 命令組", "es-ES": "Grupo de comandos RaidLootMatrix"}

HELP_NAME_LOCALIZATIONS = {"zh-CN": "帮助", "zh-TW": "幫助", "es-ES": "ayuda"}
HELP_DESC_LOCALIZATIONS = {"zh-CN": "显示 RaidLootMatrix 机器人的可用命令", "zh-TW": "顯示 RaidLootMatrix 機器人的可用命令", "es-ES": "Muestra los comandos disponibles para el bot RaidLootMatrix"}

SYNC_NAME_LOCALIZATIONS = {"zh-CN": "同步密钥", "zh-TW": "同步密鑰", "es-ES": "clave-sincronizacion"}
SYNC_DESC_LOCALIZATIONS = {"zh-CN": "通过私信将服务器的唯一同步密钥发送给管理员", "zh-TW": "通過私信將伺服器的唯一同步金鑰發送給管理員", "es-ES": "Envia la clave de sincronizacion unica del servidor al administrador via DM"}

STANDINGS_NAME_LOCALIZATIONS = {"zh-CN": "积分榜", "zh-TW": "積分榜", "es-ES": "clasificacion"}
STANDINGS_DESC_LOCALIZATIONS = {"zh-CN": "显示已同步的 EPGP 积分榜", "zh-TW": "顯示已同步的 EPGP 積分榜", "es-ES": "Muestra las clasificaciones EPGP sincronizadas"}

ROSTER_NAME_LOCALIZATIONS = {"zh-CN": "花名册", "zh-TW": "花名冊", "es-ES": "roster"}
ROSTER_DESC_LOCALIZATIONS = {"zh-CN": "显示已同步的花名册主角色和关联小号", "zh-TW": "顯示已同步的花名冊主角色和關聯小號", "es-ES": "Muestra los perfiles de roster y alts sincronizados"}

BOT_LOCALES = {
    "en": {
        "help_title": "RaidLootMatrix Helper Bot Command Guide",
        "help_desc": "Interact with the RaidLootMatrix bot using the following commands:",
        "help_cmd_help": "Shows this list of available commands.",
        "help_cmd_sync": "*(Administrators Only)* Sends your server's secure API token to you via Direct Message.",
        "help_cmd_standings": "Displays EPGP standing info for a team roster.",
        "help_cmd_roster": "Lists mains and alts for the active roster profile.",
        "err_admin": "❌ **Error:** You must have **Administrator** permissions to run this command.",
        "err_specify_team": "❌ **Error:** Please specify the team name. Example: `!{full_name} Main Roster`",
        "err_general": "❌ An error occurred: `{error}`",
        "sync_dm_title": "🔑 RaidLootMatrix Sync Authorization Key",
        "sync_dm_desc": "Here is your secure synchronization key for **{guild_name}**.\nKeep this key secret! Anyone with this key can upload and overwrite your server's standings.",
        "sync_dm_field_key": "Your Sync Key",
        "sync_dm_field_usage": "How to use it",
        "sync_dm_field_usage_val": "Paste this key into your local `rlm_discord_sync.py` script as your `SYNC_KEY`.",
        "sync_sent": "🔑 **Sync Key Sent:** Check your Direct Messages for your secure synchronization key.",
        "sync_err_dm": "❌ **Error:** I couldn't send you a Direct Message. Please verify that you have 'Allow direct messages from server members' enabled in your privacy settings.",
        "standings_title": "RaidLootMatrix Standings",
        "standings_desc": "Active EPGP Standings (Profile: **{profile}**)",
        "standings_no_mains": "ℹ️ No main characters found in the roster database.",
        "standings_rank_field": "Current Standings (Rank {start}-{end})",
        "standings_footer": "Last Synced: {name}",
        "err_no_sync_data": "❌ **Error:** No synchronization data has been uploaded to this server yet.\nPlease setup and run the RLM Desktop Companion app to sync your in-game roster!",
        "err_no_profile_match": "❌ **Error:** Could not find a standings profile matching '**{team_name}**'.\nAvailable synced profiles: {available}",
        "roster_title": "RaidLootMatrix Roster Profiles",
        "roster_desc": "Synced Roster Details (Profile: **{profile}**)",
        "roster_mains_field": "Mains & Linked Alts",
        "roster_mains_field_part": "Mains & Linked Alts (Part {part})",
        "roster_no_members": "No members registered.",
        "roster_footer": "Synced via RaidLootMatrix Desktop Sync."
    },
    "zh": {
        "help_title": "RaidLootMatrix 助手机器人命令指南",
        "help_desc": "使用以下命令与 RaidLootMatrix 机器人进行交互：",
        "help_cmd_help": "显示可用命令列表。",
        "help_cmd_sync": "*(仅限管理员)* 通过私信向您发送服务器的安全 API 令牌。",
        "help_cmd_standings": "显示团队花名册的 EPGP 积分榜信息。",
        "help_cmd_roster": "列出活动名册配置文件中的主角色和关联小号。",
        "err_admin": "❌ **错误:** 您必须拥有 **管理员** 权限才能运行此命令。",
        "err_specify_team": "❌ **错误:** 请指定团队名称。例如：`!{full_name} 主团队名册`",
        "err_general": "❌ 发生错误：`{error}`",
        "sync_dm_title": "🔑 RaidLootMatrix 同步授权密钥",
        "sync_dm_desc": "这是您服务器 **{guild_name}** 的安全同步密钥。\n请保守此密钥的机密！拥有此密钥的任何人都可以上传并覆盖您服务器的积分榜。",
        "sync_dm_field_key": "您的同步密钥",
        "sync_dm_field_usage": "如何使用",
        "sync_dm_field_usage_val": "将此密钥粘贴到您本地的 `rlm_discord_sync.py` 脚本中作为 `SYNC_KEY`。",
        "sync_sent": "🔑 **同步密钥已发送:** 请检查您的私信以获取安全同步密钥。",
        "sync_err_dm": "❌ **错误:** 我无法向您发送私信。请确认您在隐私设置中启用了“允许来自服务器成员的私信”。",
        "standings_title": "RaidLootMatrix 积分榜",
        "standings_desc": "活动 EPGP 积分榜 (配置文件: **{profile}**)",
        "standings_no_mains": "ℹ️ 名册数据库中未找到任何主角色。",
        "standings_rank_field": "当前积分榜 (排名 {start}-{end})",
        "standings_footer": "最后同步: {name}",
        "err_no_sync_data": "❌ **错误:** 此服务器尚未上传任何同步数据。\n请设置并运行 RLM 桌面助手应用程序以同步您的游戏内名册！",
        "err_no_profile_match": "❌ **错误:** 未能找到匹配 '**{team_name}**' 的积分榜配置文件。\n可用同步的配置文件: {available}",
        "roster_title": "RaidLootMatrix 花名册配置文件",
        "roster_desc": "已同步的名册详情 (配置文件: **{profile}**)",
        "roster_mains_field": "主角色与关联小号",
        "roster_mains_field_part": "主角色与关联小号 (第 {part} 部分)",
        "roster_no_members": "未注册任何成员。",
        "roster_footer": "已通过 RaidLootMatrix 桌面同步进行同步。"
    },
    "zh_tw": {
        "help_title": "RaidLootMatrix 助手機器人命令指南",
        "help_desc": "使用以下命令與 RaidLootMatrix 機器人進行互動：",
        "help_cmd_help": "顯示可用命令清單。",
        "help_cmd_sync": "*(僅限管理員)* 透過私信向您發送伺服器的安全 API 權杖。",
        "help_cmd_standings": "顯示團隊花名冊的 EPGP 積分榜資訊。",
        "help_cmd_roster": "列出活動名冊設定檔中的主角色和關聯小號。",
        "err_admin": "❌ **錯誤:** 您必須擁有 **管理員** 權限才能執行此命令。",
        "err_specify_team": "❌ **錯誤:** 請指定團隊名稱。例如：`!{full_name} 主團隊名冊`",
        "err_general": "❌ 發生錯誤：`{error}`",
        "sync_dm_title": "🔑 RaidLootMatrix 同步授權金鑰",
        "sync_dm_desc": "這是您伺服器 **{guild_name}** 的安全同步金鑰。\n請保守此金鑰的機密！擁有此金鑰的任何人都可以上傳並覆蓋您伺服器的積分榜。",
        "sync_dm_field_key": "您的同步金鑰",
        "sync_dm_field_usage": "如何使用",
        "sync_dm_field_usage_val": "將此金鑰貼上到您本地的 `rlm_discord_sync.py` 腳本中作為 `SYNC_KEY`。",
        "sync_sent": "🔑 **同步金鑰已發送:** 請檢查您的私信以獲取安全同步金鑰。",
        "sync_err_dm": "❌ **錯誤:** 我無法向您發送私信。請確認您在隱私設定中啟用了「允許來自伺服器成員的私信」。",
        "standings_title": "RaidLootMatrix 積分榜",
        "standings_desc": "活動 EPGP 積分榜 (設定檔: **{profile}**)",
        "standings_no_mains": "ℹ️ 名冊資料庫中未找到任何主角色。",
        "standings_rank_field": "當前積分榜 (排名 {start}-{end})",
        "standings_footer": "最後同步: {name}",
        "err_no_sync_data": "❌ **錯誤:** 此伺服器尚未上傳任何同步數據。\n請設置並運行 RLM 桌面阻手應用程式以同步您的遊戲內名冊！",
        "err_no_profile_match": "❌ **錯誤:** 未能找到匹配 '**{team_name}**' 的積分榜設定檔。\n可用同步的設定檔: {available}",
        "roster_title": "RaidLootMatrix 花名冊設定檔",
        "roster_desc": "已同步的名冊詳情 (設定檔: **{profile}**)",
        "roster_mains_field": "主角色與關聯小號",
        "roster_mains_field_part": "主角色與關聯小號 (第 {part} 部分)",
        "roster_no_members": "未註冊任何成員。",
        "roster_footer": "已透過 RaidLootMatrix 桌面同步進行同步。"
    },
    "es": {
        "help_title": "Guía de Comandos del Bot RaidLootMatrix",
        "help_desc": "Interactúa con el bot RaidLootMatrix usando los siguientes comandos:",
        "help_cmd_help": "Muestra esta lista de comandos disponibles.",
        "help_cmd_sync": "*(Solo Administradores)* Envía el token de API seguro de tu servidor por Mensaje Directo.",
        "help_cmd_standings": "Muestra la clasificación EPGP para una lista de equipo.",
        "help_cmd_roster": "Lista los personajes principales y alts para el perfil de roster activo.",
        "err_admin": "❌ **Error:** Debes tener permisos de **Administrador** para ejecutar este comando.",
        "err_specify_team": "❌ **Error:** Por favor, especifica el nombre del equipo. Ejemplo: `!{full_name} Roster Principal`",
        "err_general": "❌ Ocurrió un error: `{error}`",
        "sync_dm_title": "🔑 Clave de Autorización de Sincronización RaidLootMatrix",
        "sync_dm_desc": "Aquí está tu clave de sincronización segura para **{guild_name}**.\n¡Mantén esta clave en secreto! Cualquiera con esta clave puede subir y sobrescribir las clasificaciones de tu servidor.",
        "sync_dm_field_key": "Tu Clave de Sincronización",
        "sync_dm_field_usage": "Cómo usarla",
        "sync_dm_field_usage_val": "Pega esta clave en tu script local `rlm_discord_sync.py` como `SYNC_KEY`.",
        "sync_sent": "🔑 **Clave de Sincronización Enviada:** Revisa tus Mensajes Directos para obtener tu clave segura.",
        "sync_err_dm": "❌ **Error:** No pude enviarte un Mensaje Directo. Por favor, verifica que tienes habilitado 'Permitir mensajes directos de miembros del servidor' en tus ajustes de privacidad.",
        "standings_title": "Clasificación RaidLootMatrix",
        "standings_desc": "Clasificación EPGP Activa (Perfil: **{profile}**)",
        "standings_no_mains": "ℹ️ No se encontraron personajes principales en la base de datos.",
        "standings_rank_field": "Clasificación Actual (Puestos {start}-{end})",
        "standings_footer": "Última Sincronización: {name}",
        "err_no_sync_data": "❌ **Error:** Aún no se han subido datos de sincronización a este servidor.\n¡Por favor, configura y ejecuta la aplicación RLM Desktop Companion para sincronizar tu roster en el juego!",
        "err_no_profile_match": "❌ **Error:** No se pudo encontrar un perfil de clasificación que coincida con '**{team_name}**'.\nPerfiles sincronizados disponibles: {available}",
        "roster_title": "Perfiles de Roster RaidLootMatrix",
        "roster_desc": "Detalles del Roster Sincronizado (Perfil: **{profile}**)",
        "roster_mains_field": "Personajes Principales y Alts",
        "roster_mains_field_part": "Personajes Principales y Alts (Parte {part})",
        "roster_no_members": "No hay miembros registrados.",
        "roster_footer": "Sincronizado a través de RaidLootMatrix Desktop Sync."
    }
}

def get_locale(ctx):
    locale = "en"
    if ctx.interaction:
        locale = str(ctx.interaction.locale or ctx.interaction.guild_locale or "en")
    
    locale = locale.lower()
    if locale in ["zh-tw", "zh-hk", "zh-mo"]:
        return "zh_tw"
    elif locale.startswith("zh"):
        return "zh"
    elif locale.startswith("es"):
        return "es"
    return "en"

def L(ctx, key):
    lang = get_locale(ctx)
    return BOT_LOCALES[lang].get(key, BOT_LOCALES["en"].get(key, key))

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
        await ctx.send(L(ctx, "err_admin"))
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd_name = ctx.command.name
        if ctx.command.parent:
            full_name = f"{ctx.command.parent.name} {cmd_name}"
        else:
            full_name = cmd_name
        await ctx.send(L(ctx, "err_specify_team").format(full_name=full_name))
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(L(ctx, "err_general").format(error=error))

# Helper function to print command guide
async def rlm_help_internal(ctx):
    embed = discord.Embed(
        title=L(ctx, "help_title"),
        description=L(ctx, "help_desc"),
        color=discord.Color.blue()
    )
    embed.add_field(
        name="`/rlm help` or `!rlm help`",
        value=L(ctx, "help_cmd_help"),
        inline=False
    )
    embed.add_field(
        name="`/rlm synckey` or `!rlm synckey`",
        value=L(ctx, "help_cmd_sync"),
        inline=False
    )
    embed.add_field(
        name="`/rlm standings <team>` or `!rlm standings <team>`",
        value=L(ctx, "help_cmd_standings"),
        inline=False
    )
    embed.add_field(
        name="`/rlm roster <team>` or `!rlm roster <team>`",
        value=L(ctx, "help_cmd_roster"),
        inline=False
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    embed.set_footer(text="RaidLootMatrix Bot v1.2.0")
    await ctx.send(embed=embed)

# Parent Hybrid Group
@bot.hybrid_group(
    name="rlm",
    description="RaidLootMatrix command group",
    name_localizations=RLM_NAME_LOCALIZATIONS,
    description_localizations=RLM_DESC_LOCALIZATIONS
)
async def rlm(ctx):
    """Parent command group for RaidLootMatrix. Run `/rlm help` for usage."""
    if ctx.invoked_subcommand is None:
        await rlm_help_internal(ctx)

# 1. Custom Help Command
@rlm.command(
    name="help",
    description="Displays available commands for RaidLootMatrix Bot",
    name_localizations=HELP_NAME_LOCALIZATIONS,
    description_localizations=HELP_DESC_LOCALIZATIONS
)
async def rlm_help(ctx):
    await rlm_help_internal(ctx)

# 2. Sync Key Generator Command
@rlm.command(
    name="synckey",
    aliases=["sync-key"],
    description="Sends the server's unique sync key to the administrator via DM",
    name_localizations=SYNC_NAME_LOCALIZATIONS,
    description_localizations=SYNC_DESC_LOCALIZATIONS
)
@commands.has_permissions(administrator=True)
async def sync_key(ctx):
    """Sends the server's unique sync key to the administrator via DM"""
    guild_id = ctx.guild.id
    guild_name = ctx.guild.name
    
    key = get_or_create_sync_key(guild_id)
    
    try:
        embed = discord.Embed(
            title=L(ctx, "sync_dm_title"),
            description=L(ctx, "sync_dm_desc").format(guild_name=guild_name),
            color=discord.Color.gold()
        )
        embed.add_field(
            name=L(ctx, "sync_dm_field_key"),
            value=f"`{key}`",
            inline=False
        )
        embed.add_field(
            name=L(ctx, "sync_dm_field_usage"),
            value=L(ctx, "sync_dm_field_usage_val"),
            inline=False
        )
        await ctx.author.send(embed=embed)
        await ctx.send(L(ctx, "sync_sent"))
    except discord.Forbidden:
        await ctx.send(L(ctx, "sync_err_dm"))

# 3. Standings Query Command
@rlm.command(
    name="standings",
    description="Displays EPGP standings (synced)",
    name_localizations=STANDINGS_NAME_LOCALIZATIONS,
    description_localizations=STANDINGS_DESC_LOCALIZATIONS
)
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
        profile_display = source_profile.split('::')[-1]
        embed = discord.Embed(
            title=L(ctx, "standings_title"),
            description=L(ctx, "standings_desc").format(profile=profile_display),
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
            await ctx.send(L(ctx, "standings_no_mains"))
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
            
            field_name = L(ctx, "standings_rank_field").format(start=i+1, end=i+len(chunk))
            embed.add_field(name=field_name, value=table_content, inline=False)
        embed.set_footer(text=L(ctx, "standings_footer").format(name=ctx.guild.me.display_name))
        await ctx.send(embed=embed)
        return
        
    # No match found -> handle error or empty database gracefully
    if not profiles:
        await ctx.send(L(ctx, "err_no_sync_data"))
    else:
        available = ", ".join([f"`{pk.split('::')[-1]}`" for pk in profiles.keys()])
        await ctx.send(L(ctx, "err_no_profile_match").format(team_name=team_name, available=available))

# 4. Roster Query Command
@rlm.command(
    name="roster",
    description="Displays roster profiles and alts (synced)",
    name_localizations=ROSTER_NAME_LOCALIZATIONS,
    description_localizations=ROSTER_DESC_LOCALIZATIONS
)
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
        profile_display = source_profile.split('::')[-1]
        embed = discord.Embed(
            title=L(ctx, "roster_title"),
            description=L(ctx, "roster_desc").format(profile=profile_display),
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
                field_name = L(ctx, "roster_mains_field_part").format(part=chunk_index) if chunk_index > 1 or len(mains) > 15 else L(ctx, "roster_mains_field")
                embed.add_field(
                    name=field_name, 
                    value=current_chunk or L(ctx, "roster_no_members"), 
                    inline=False
                )
                current_chunk = line
                chunk_index += 1
            else:
                current_chunk += line
                
        if current_chunk:
            field_name = L(ctx, "roster_mains_field_part").format(part=chunk_index) if chunk_index > 1 else L(ctx, "roster_mains_field")
            embed.add_field(
                name=field_name, 
                value=current_chunk, 
                inline=False
            )
        embed.set_footer(text=L(ctx, "roster_footer"))
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
