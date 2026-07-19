import os
import sys
import asyncio

try:
    import discord
except ImportError:
    print("Error: The 'discord.py' library is required to run this script.")
    print("Please install it by running: pip install discord.py")
    input("\nPress Enter to exit...")
    sys.exit(1)

TOKEN = "MTUxOTQyNjU2MTM1MzE4NzQyOA.GFEY40.YZnrM7bJRPsgcDfX7JKASzoY9ORl2iulnoOUSQ"  # Replace this with your actual Bot Token
SERVER_NAME = "RaidLootMatrix Support"  # Replace if your server has a different name

class RLMSetupBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        
        # Find the guild/server
        guild = None
        if len(self.guilds) == 0:
            print("Error: The bot is not in any servers. Please invite the bot to your server first.")
            await self.close()
            return
            
        for g in self.guilds:
            if g.name.lower() == SERVER_NAME.lower() or len(self.guilds) == 1:
                guild = g
                break
                
        if not guild:
            print(f"Error: Could not find server named '{SERVER_NAME}'")
            print("Available servers:")
            for g in self.guilds:
                print(f" - {g.name}")
            await self.close()
            return

        print(f"Configuring server: {guild.name} ({guild.id})")

        # 1. Clean up default channels
        print("Cleaning up existing channels...")
        for channel in guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Could not delete channel {channel.name}: {e}")

        # 2. Create Roles
        print("Creating roles...")
        roles = {}
        role_colors = {
            "Developer": discord.Color.gold(),
            "Moderator": discord.Color.blue(),
            "RaidLootMatrix User": discord.Color.green(),
            "Ticket Support": discord.Color.dark_grey()  # Used for Ticket Tool bot
        }
        
        for role_name, color in role_colors.items():
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if not existing_role:
                roles[role_name] = await guild.create_role(
                    name=role_name, 
                    color=color, 
                    mentionable=True,
                    hoist=True
                )
            else:
                roles[role_name] = existing_role
        
        # 3. Setup Permission Overrides
        everyone = guild.default_role
        dev_role = roles["Developer"]
        mod_role = roles["Moderator"]
        support_role = roles["Ticket Support"]

        read_only_overrides = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=False, add_reactions=True),
            dev_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

        public_write_overrides = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True),
            dev_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # 4. Create Categories and Channels
        print("Creating categories and channels...")

        # --- CATEGORY: INFORMATION ---
        cat_info = await guild.create_category("📢 INFORMATION")
        await cat_info.set_permissions(everyone, read_messages=True, send_messages=False)

        ch_rules = await guild.create_text_channel("rules-and-faq", category=cat_info, overwrites=read_only_overrides)
        ch_announcements = await guild.create_text_channel("announcements", category=cat_info, overwrites=read_only_overrides)
        ch_downloads = await guild.create_text_channel("addon-download", category=cat_info, overwrites=read_only_overrides)

        # --- CATEGORY: COMMUNITY ---
        cat_comm = await guild.create_category("💬 COMMUNITY")
        ch_general = await guild.create_text_channel("general", category=cat_comm, overwrites=public_write_overrides)
        ch_showcase = await guild.create_text_channel("ui-showcase", category=cat_comm, overwrites=public_write_overrides)

        # --- CATEGORY: SUPPORT & HELP ---
        cat_support = await guild.create_category("🛠️ SUPPORT & HELP")
        ch_tickets = await guild.create_text_channel("open-a-ticket", category=cat_support, overwrites=read_only_overrides)
        ch_bugs = await guild.create_text_channel("bug-reports", category=cat_support, overwrites=public_write_overrides)
        ch_requests = await guild.create_text_channel("feature-requests", category=cat_support, overwrites=public_write_overrides)

        # --- CATEGORY: OFFICERS (PRIVATE) ---
        cat_private = await guild.create_category("🔒 OFFICERS ONLY")
        private_overrides = {
            everyone: discord.PermissionOverwrite(read_messages=False),
            dev_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ch_bot_setup = await guild.create_text_channel("bot-setup-links", category=cat_private, overwrites=private_overrides)
        ch_staff_chat = await guild.create_text_channel("staff-chat", category=cat_private, overwrites=private_overrides)

        # 5. Post Embed Templates and Guides
        print("Posting templates and announcements...")

        # --- DOWNLOAD LINK ---
        download_embed = discord.Embed(
            title="Download RaidLootMatrix (RLM)",
            description="Keep your addon and companion app updated to the latest versions to ensure smooth database syncing and encounter tracking.",
            color=discord.Color.gold()
        )
        download_embed.add_field(
            name="1. WoW Addon - CurseForge (Recommended)",
            value="[Download via CurseForge App or Web](https://www.curseforge.com/wow/addons/raidlootmatrix)",
            inline=False
        )
        download_embed.add_field(
            name="2. Desktop Companion (GitHub Releases)",
            value="[Download Latest RLM Companion (RLM_Companion.exe)](https://github.com/Rynedelewis/RLM-Desktop-Companion/releases/latest)\\n*Enables Mythic+ weekly run imports and real-time EPGP standings syncing to Discord.*",
            inline=False
        )
        download_embed.add_field(
            name="Manual Addon Installation",
            value="1. Download the zip file.\\n2. Extract it into your `World of Warcraft\\_retail_\\Interface\\AddOns` folder.\\n3. Type `/reload` in-game.",
            inline=False
        )
        await ch_downloads.send(embed=download_embed)

        # --- RULES & FAQ ---
        rules_embed = discord.Embed(
            title="RaidLootMatrix Discord Rules",
            description="Welcome to the RLM support and feedback community! Please follow these basic guidelines:",
            color=discord.Color.blue()
        )
        rules_embed.add_field(name="1. Be Respectful", value="Treat all developers, moderators, and users with courtesy.", inline=False)
        rules_embed.add_field(name="2. Constructive Discussions", value="Keep channels focused on RaidLootMatrix support, usage, and feedback.", inline=False)
        rules_embed.add_field(name="3. No Spam or Self-Promotion", value="Do not advertise other services or guilds here.", inline=False)
        await ch_rules.send(embed=rules_embed)

        faq_embed = discord.Embed(
            title="Frequently Asked Questions (FAQ)",
            description="Quick answers to common questions about RaidLootMatrix.",
            color=discord.Color.green()
        )
        faq_embed.add_field(
            name="Q: How do I select my active team?",
            value="A: Open the RLM window in-game, navigate to the **Create Team** tab, select your team from the left side list, and it will highlight green as **[Active]**.",
            inline=False
        )
        faq_embed.add_field(
            name="Q: How does database syncing work?",
            value="A: RLM uses internal WoW addon messaging channels. When you are in a party or raid group, the addon automatically synchronizes data (EP/GP edits, roll choices, roster settings) among all present officers.",
            inline=False
        )
        faq_embed.add_field(
            name="Q: Why are my checkboxes disabled or greyed out?",
            value="A: Roster checkboxes are disabled whenever **EPGP Tracking** is toggled OFF (or when you are solo). Click the **EPGP Tracking** slider at the top of the main window to unlock them when in a raid group.",
            inline=False
        )
        faq_embed.add_field(
            name="Q: How do I handle alts on the roster?",
            value="A: Right-click the alt's name on the roster page, choose **Add Alt**, and type the exact name of their main character. EPGP and stats will merge and attribute to the main character.",
            inline=False
        )
        await ch_rules.send(embed=faq_embed)

        # --- ANNOUNCEMENTS ---
        welcome_embed = discord.Embed(
            title="Welcome to RaidLootMatrix Support!",
            description="This server serves as the central hub for RLM releases, bug reports, and user support.\\n\\nKeep an eye on this channel for release notes and update alerts!",
            color=discord.Color.purple()
        )
        await ch_announcements.send(embed=welcome_embed)

        # --- BUG REPORT INSTRUCTIONS ---
        bug_embed = discord.Embed(
            title="How to Submit a Bug Report",
            description="Please copy and paste the template below when reporting a bug. Vague bug reports make it very hard to troubleshoot!",
            color=discord.Color.red()
        )
        bug_embed.add_field(
            name="Copy-Paste Template",
            value="```markdown\\n**RLM Version:** (e.g. v2.4.49)\\n**WoW Client:** (e.g. Retail / Classic / Cata)\\n**Description of Bug:**\\n**Steps to Reproduce:**\\n1.\\n2.\\n**Lua Error text (from BugSack/BugGrabber):**\\n```",
            inline=False
        )
        await ch_bugs.send(embed=bug_embed)

        # --- FEATURE REQUEST INSTRUCTIONS ---
        feature_embed = discord.Embed(
            title="Feature Request Guidelines",
            description="Have a suggestion for RaidLootMatrix? We'd love to hear it! Please format your request using the template below. Use reactions to upvote/downvote ideas!",
            color=discord.Color.teal()
        )
        feature_embed.add_field(
            name="Copy-Paste Template",
            value="```markdown\\n**Feature Description:**\\n**Why is this feature useful?**\\n**Additional Context / Mockups:**\\n```",
            inline=False
        )
        await ch_requests.send(embed=feature_embed)

        # --- TICKET INSTRUCTIONS ---
        ticket_embed = discord.Embed(
            title="1-on-1 Help & Ticket Support",
            description="If you need private help recovering a corrupted database, resolving persistent sync conflicts, or troubleshooting private guild details, you can open a support ticket.\\n\\nTo set this up, invite **Ticket Tool** to the server. (Links are provided in the private `#bot-setup-links` channel).",
            color=discord.Color.orange()
        )
        await ch_tickets.send(embed=ticket_embed)

        # --- BOT SETUP LINKS (PRIVATE FOR OWNER) ---
        setup_embed = discord.Embed(
            title="Guild Bots Invite Links",
            description="As the server administrator, you can invite these recommended bots to automate support ticketing and scheduler management. (Only administrators can invite bots).",
            color=discord.Color.dark_grey()
        )
        setup_embed.add_field(
            name="1. Ticket Tool (Private Support Tickets)",
            value="Allows users to click a button in `#open-a-ticket` and opens a private channel for them.\\n[Invite Ticket Tool Bot](https://tickettool.xyz/)",
            inline=False
        )
        setup_embed.add_field(
            name="2. Apollo (Raid Signups & Scheduling)",
            value="An excellent calendar event bot for scheduling signups and roster signups.\\n[Invite Apollo Bot](https://apollo.bot/)",
            inline=False
        )
        setup_embed.add_field(
            name="3. Dyno (Moderation and Auto-Responder)",
            value="Can be used for auto-responding to questions like 'how to install' or 'error' in `#general` chat.\\n[Invite Dyno Bot](https://dyno.gg/)",
            inline=False
        )
        await ch_bot_setup.send(embed=setup_embed)

        print("\\n" + "="*50)
        print("Configuration complete! Server has been fully built and populated.")
        print("="*50)
        await self.close()

if __name__ == "__main__":
    if TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("Error: You must replace 'YOUR_DISCORD_BOT_TOKEN_HERE' with your bot token in the script.")
        input("\nPress Enter to exit...")
        sys.exit(1)
        
    bot = RLMSetupBot()
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord Bot Token. Please double check the token in the script.")
    except Exception as e:
        print(f"Error occurred: {e}")
    
    input("\nPress Enter to exit...")
