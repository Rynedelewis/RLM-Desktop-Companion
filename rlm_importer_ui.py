import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import pathlib
import platform
import threading
import subprocess
import pystray
from PIL import Image, ImageDraw
import ctypes
import requests
import webbrowser

# Import background tasks & provider engine
try:
    import raidlootmatrix_mplus
    import rlm_discord_sync
    import rlm_wowaudit_sync
    import rlm_guild_providers
except ImportError as e:
    print(f"Warning: Failed to import background task modules: {e}")

try:
    myappid = "raidlootmatrix.desktop.companion"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

VERSION = "1.3.3"

# 👑 Premium Gold & Obsidian Theme Design System Tokens
BG_DARK = "#0c0a09"          # Warm obsidian charcoal
BG_PANEL = "#1c1917"         # Deep slate gold panel
BG_ENTRY = "#090807"         # Pure dark void entry background
FG_TEXT = "#f5f5f4"          # Bright stone text
FG_HEADER = "#fef3c7"        # Light cream gold header
FG_GOLD = "#f59e0b"          # Vibrant WoW Gold Accent
FG_GOLD_BRIGHT = "#fbbf24"   # Sunburst Gold Highlight
FG_GOLD_DARK = "#b45309"     # Burnished Bronze Gold
BORDER_GOLD = "#78350f"      # Gold border stroke
BORDER_MUTED = "#292524"     # Muted panel stroke
FG_SUCCESS = "#22c55e"       # Emerald green
FG_BLUE = "#38bdf8"          # Sky blue accent

class StdoutRedirector:
    """Redirects stdout and stderr prints directly into the GUI console text widget."""
    def __init__(self, log_func):
        self.log_func = log_func

    def write(self, str_val):
        if str_val and str_val.strip():
            self.log_func(str_val.strip('\r\n'))

    def flush(self):
        pass

    def reconfigure(self, **kwargs):
        pass

LOCALES = {
    "en": {
        "header_title": "RaidLootMatrix Companion",
        "header_subtitle": " v{VERSION} • Guild Data Hub & Automation Suite",
        "tab_general": " 🎮 General & WoW",
        "tab_providers": " 🌐 Guild Data Sources",
        "tab_sched": " 🤖 Task Automation",
        "tab_discord": " 💬 Discord Bot",
        "tab_console": " 📋 Operations & Logs",
        
        "card_wow_hdr": " 👑 WoW Client & Account Configuration",
        "card_sched_hdr": " ⚡ Windows Task Scheduler Automation",
        "card_discord_hdr": " 💬 Discord Bot Synchronization Settings",
        "card_providers_hdr": " 🌐 Guild Data Sources (WoW Audit, WoWUtils, Guilds of WoW)",
        
        "btn_save_settings": "💾 Save Settings",
        "lbl_console_hdr": " 📋 Live Operations & Execution Log",
        "lbl_account": "WTF Account Name:",
        "lbl_region": "Raider.IO Region (us/eu):",
        "lbl_season": "Mythic+ Season Slug:",
        "lbl_rio_delay": "API Delay (seconds):",
        "lbl_wow_path": "WoW Directory or WTF Path:",
        "btn_browse": "Browse...",
        "lbl_sched_am": "AM Scan (24h HH:MM):",
        "lbl_sched_pm": "PM Scan (24h HH:MM):",
        "chk_logon": "Run daily scans 5 minutes after logging into Windows",
        "chk_startup": "Start RLM Desktop UI automatically on Windows logon (Tray)",
        "chk_wow_exit": "Sync immediately when WoW closes (Wow.exe Close Watcher)",
        "chk_minimize_on_close": "Minimize to system tray on window close (instead of exiting)",
        "btn_register": "⚡ Register Background Tasks",
        "btn_unregister": "🗑️ Remove Tasks",
        "lbl_discord_key": "Discord Sync Key:",
        "lbl_discord_url": "Discord Sync URL:",
        "chk_sync_on_import": "Run Discord Sync after M+ import",
        "btn_sync_now": "💬 Run Discord Sync Now",
        "lbl_week_mode": "Import Week Mode:",
        "btn_run": "Run Import Now",
        "msg_success_title": "Success",
        "msg_success_saved": "Settings saved successfully!",
        "dialog_select_wtf": "Select your World of Warcraft directory, WTF, or Account folder",
        "lbl_language": "Language / 语言 / Idioma:",
        "week_both": "Both Weeks",
        "week_current": "Current Week",
        "week_last": "Last Week",
        
        "lbl_provider_type": "Source Provider:",
        "lbl_provider_key": "API Key / Token:",
        "lbl_group_id": "Group / Team ID (Optional):",
        "lbl_provider_profile": "Mapped RLM Profile:",
        "lbl_sync_options": "Data Sync Scope:",
        "chk_sync_roster": "Sync Roster (Default)",
        "chk_sync_calendar": "Sync Calendar Events & Raids (Default)",
        "chk_sync_wishlists": "Sync Wishlists & Upgrades",
        "btn_provider_add": "➕ Add / Link Source",
        "btn_provider_del": "🗑️ Remove Selected",
        "btn_provider_test": "⚡ Test Connection",
        "btn_run_mplus": "⚔️ Import M+ Data",
        "btn_run_guild": "🔄 Sync Guild Data",
        "btn_run_discord": "💬 Sync Discord Bot",
        "lbl_update_available": "Update Available: v{remote_version}",
        "btn_update_now": "Update Now",
        "gow_pending_note": "⚠️ Guilds of WoW is Pending API access. Please use WoW Audit or WoWUtils.",
        "gow_pending_title": "Provider Pending",
        "gow_pending_dialog": "Guilds of WoW integration is currently Pending API access. Please select WoW Audit or WoWUtils for live data sync."
    },
    "zh": {
        "header_title": "RaidLootMatrix 桌面助手",
        "header_subtitle": " v{VERSION} • 公会数据中心与自动化套件",
        "tab_general": " 🎮 游戏设置",
        "tab_providers": " 🌐 公会数据源",
        "tab_sched": " 🤖 任务自动化",
        "tab_discord": " 💬 Discord 机器人",
        "tab_console": " 📋 操作与日志",
        
        "card_wow_hdr": " 👑 游戏与账号配置",
        "card_sched_hdr": " ⚡ Windows 计划任务自动化",
        "card_discord_hdr": " 💬 Discord 机器人同步设置",
        "card_providers_hdr": " 🌐 外部公会数据源 (WoW Audit, WoWUtils, Guilds of WoW)",
        
        "btn_save_settings": "💾 保存设置",
        "lbl_console_hdr": " 📋 实时操作与执行日志",
        "lbl_account": "WTF 账号名称:",
        "lbl_region": "Raider.IO 区域 (us/eu):",
        "lbl_season": "史诗+ 赛季标识:",
        "lbl_rio_delay": "API 延迟 (秒):",
        "lbl_wow_path": "WoW 目录或 WTF 路径:",
        "btn_browse": "浏览...",
        "lbl_sched_am": "上午扫描 (24h HH:MM):",
        "lbl_sched_pm": "下午扫描 (24h HH:MM):",
        "chk_logon": "登录 Windows 5 分钟后运行每日扫描",
        "chk_startup": "登录 Windows 时自动启动 RLM 桌面 UI (系统托盘)",
        "chk_wow_exit": "WoW 关闭时立即同步 (Wow.exe 运行监控)",
        "chk_minimize_on_close": "关闭主窗口时最小化到系统托盘 (而非退出)",
        "btn_register": "⚡ 注册后台任务",
        "btn_unregister": "🗑️ 删除注册任务",
        "lbl_discord_key": "Discord 同步密钥:",
        "lbl_discord_url": "Discord 同步 URL:",
        "chk_sync_on_import": "导入 M+ 数据后运行 Discord 同步",
        "btn_sync_now": "💬 立即运行 Discord 同步",
        "lbl_week_mode": "导入周模式:",
        "btn_run": "立即运行导入",
        "msg_success_title": "成功",
        "msg_success_saved": "设置已成功保存！",
        "dialog_select_wtf": "选择您的魔兽世界游戏目录、WTF 或是账号文件夹",
        "lbl_language": "语言 / Language / Idioma:",
        "week_both": "全部双周",
        "week_current": "仅限本周",
        "week_last": "仅限上周",
        
        "lbl_provider_type": "数据源类型:",
        "lbl_provider_key": "API 密钥 / Token:",
        "lbl_group_id": "团队 / 组 ID (可选):",
        "lbl_provider_profile": "映射 RLM 配置文件:",
        "lbl_sync_options": "数据同步范围:",
        "chk_sync_roster": "同步公会名册 (默认)",
        "chk_sync_calendar": "同步日历活动与活动报名 (默认)",
        "chk_sync_wishlists": "同步装备愿望单",
        "btn_provider_add": "➕ 添加 / 关联数据源",
        "btn_provider_del": "🗑️ 删除所选源",
        "btn_provider_test": "⚡ 测试连接",
        "btn_run_mplus": "⚔️ 导入 M+ 数据",
        "btn_run_guild": "🔄 同步公会数据",
        "btn_run_discord": "💬 同步 Discord 机器人",
        "lbl_update_available": "有可用更新: v{remote_version}",
        "btn_update_now": "立即更新",
        "gow_pending_note": "⚠️ Guilds of WoW 暂未开放 API。请使用 WoW Audit 或 WoWUtils。",
        "gow_pending_title": "数据源待定",
        "gow_pending_dialog": "Guilds of WoW 集成目前处于待定状态。请选择 WoW Audit 或 WoWUtils 进行数据同步。"
    },
    "zh_tw": {
        "header_title": "RaidLootMatrix 桌面助手",
        "header_subtitle": " v{VERSION} • 公會數據中心與自動化套件",
        "tab_general": " 🎮 遊戲設置",
        "tab_providers": " 🌐 公會數據源",
        "tab_sched": " 🤖 任務自動化",
        "tab_discord": " 💬 Discord 機器人",
        "tab_console": " 📋 操作與日誌",
        
        "card_wow_hdr": " 👑 遊戲與帳號配置",
        "card_sched_hdr": " ⚡ Windows 計劃任務自動化",
        "card_discord_hdr": " 💬 Discord 機器人同步設置",
        "card_providers_hdr": " 🌐 外部公會數據源 (WoW Audit, WoWUtils, Guilds of WoW)",
        
        "btn_save_settings": "💾 儲存設置",
        "lbl_console_hdr": " 📋 實時操作與執行日誌",
        "lbl_account": "WTF 帳號名稱:",
        "lbl_region": "Raider.IO 區域 (us/eu):",
        "lbl_season": "史詩+ 賽季識別:",
        "lbl_rio_delay": "API 延遲 (秒):",
        "lbl_wow_path": "WoW 目錄或 WTF 路徑:",
        "btn_browse": "瀏覽...",
        "lbl_sched_am": "上午掃描 (24h HH:MM):",
        "lbl_sched_pm": "下午掃描 (24h HH:MM):",
        "chk_logon": "登入 Windows 5 分鐘後運行每日掃描",
        "chk_startup": "登入 Windows 時自動啟動 RLM 桌面 UI (系統托盤)",
        "chk_wow_exit": "WoW 關閉時立即同步 (Wow.exe 運行監控)",
        "chk_minimize_on_close": "關閉主視窗時最小化到系統托盤 (而非退出)",
        "btn_register": "⚡ 註冊後台任務",
        "btn_unregister": "🗑️ 刪除註冊任務",
        "lbl_discord_key": "Discord 同步金鑰:",
        "lbl_discord_url": "Discord 同步 URL:",
        "chk_sync_on_import": "導入 M+ 數據後運行 Discord 同步",
        "btn_sync_now": "💬 立即運行 Discord 同步",
        "lbl_week_mode": "導入周模式:",
        "btn_run": "立即運行導入",
        "msg_success_title": "成功",
        "msg_success_saved": "設置已成功儲存！",
        "dialog_select_wtf": "選擇您的魔獸世界遊戲目錄、WTF 或是帳號資料夾",
        "lbl_language": "語言 / Language / Idioma:",
        "week_both": "全部雙周",
        "week_current": "僅限本周",
        "week_last": "僅限上周",
        
        "lbl_provider_type": "數據源類型:",
        "lbl_provider_key": "API 金鑰 / Token:",
        "lbl_group_id": "團隊 / 組 ID (選填):",
        "lbl_provider_profile": "映射 RLM 設定檔:",
        "lbl_sync_options": "數據同步範圍:",
        "chk_sync_roster": "同步公會名冊 (預設)",
        "chk_sync_calendar": "同步日曆活動與活動報名 (預設)",
        "chk_sync_wishlists": "同步裝備願望單",
        "btn_provider_add": "➕ 新增 / 關聯數據源",
        "btn_provider_del": "🗑️ 刪除所選源",
        "btn_provider_test": "⚡ 測試連接",
        "btn_run_mplus": "⚔️ 匯入 M+ 數據",
        "btn_run_guild": "🔄 同步公會數據",
        "btn_run_discord": "💬 同步 Discord 機器人",
        "lbl_update_available": "有可用更新: v{remote_version}",
        "btn_update_now": "更新",
        "gow_pending_note": "⚠️ Guilds of WoW 暫未開放 API。請使用 WoW Audit 或 WoWUtils。",
        "gow_pending_title": "數據源待定",
        "gow_pending_dialog": "Guilds of WoW 集成目前處於待定狀態。請選擇 WoW Audit 或 WoWUtils 進行數據同步。"
    },
    "es": {
        "header_title": "Asistente RaidLootMatrix",
        "header_subtitle": " v{VERSION} • Centro de Datos de Hermandad y Automatización",
        "tab_general": " 🎮 Ajustes de WoW",
        "tab_providers": " 🌐 Fuentes de Hermandad",
        "tab_sched": " 🤖 Automatización",
        "tab_discord": " 💬 Bot de Discord",
        "tab_console": " 📋 Operaciones y Consola",
        
        "card_wow_hdr": " 👑 Configuración de WoW y Cuenta",
        "card_sched_hdr": " ⚡ Automatización del Programador de Tareas",
        "card_discord_hdr": " 💬 Sincronización del Bot de Discord",
        "card_providers_hdr": " 🌐 Fuentes Externas (WoW Audit, WoWUtils, Guilds of WoW)",
        
        "btn_save_settings": "💾 Guardar Ajustes",
        "lbl_console_hdr": " 📋 Consola de Operaciones en Vivo",
        "lbl_account": "Nombre de Cuenta WTF:",
        "lbl_region": "Región de Raider.IO (us/eu):",
        "lbl_season": "Identificador de Temporada Mítica+:",
        "lbl_rio_delay": "Retraso de API (segundos):",
        "lbl_wow_path": "Directorio de WoW o Ruta WTF:",
        "btn_browse": "Buscar...",
        "lbl_sched_am": "Escaneo AM (24h HH:MM):",
        "lbl_sched_pm": "Escaneo PM (24h HH:MM):",
        "chk_logon": "Escanear diariamente 5 minutos después de iniciar Windows",
        "chk_startup": "Iniciar RLM Desktop UI automáticamente con Windows (Bandeja)",
        "chk_wow_exit": "Sincronizar inmediatamente al cerrar WoW (Watcher de Wow.exe)",
        "chk_minimize_on_close": "Minimizar a la bandeja del sistema al cerrar la ventana (en lugar de salir)",
        "btn_register": "⚡ Registrar Tareas en Segundo Plano",
        "btn_unregister": "🗑️ Eliminar Tareas",
        "lbl_discord_key": "Clave de Sincronización de Discord:",
        "lbl_discord_url": "URL de Sincronización de Discord:",
        "chk_sync_on_import": "Sincronizar Discord tras importar M+",
        "btn_sync_now": "💬 Sincronizar Discord Ahora",
        "lbl_week_mode": "Modo de Semana a Importar:",
        "btn_run": "Ejecutar Importación Ahora",
        "msg_success_title": "Éxito",
        "msg_success_saved": "¡Ajustes guardados correctamente!",
        "dialog_select_wtf": "Seleccione su carpeta de World of Warcraft, carpeta WTF o Cuenta",
        "lbl_language": "Idioma / Language / 语言:",
        "week_both": "Ambas Semanas",
        "week_current": "Semana Actual",
        "week_last": "Semana Anterior",
        
        "lbl_provider_type": "Proveedor de Datos:",
        "lbl_provider_key": "Clave API / Token:",
        "lbl_group_id": "ID de Grupo / Equipo (Opcional):",
        "lbl_provider_profile": "Perfil RLM Asignado:",
        "lbl_sync_options": "Alcance de Sincronización:",
        "chk_sync_roster": "Sincronizar Roster (Predeterminado)",
        "chk_sync_calendar": "Sincronizar Calendario y Eventos (Predeterminado)",
        "chk_sync_wishlists": "Sincronizar Lista de Deseos",
        "btn_provider_add": "➕ Añadir / Vincular Fuente",
        "btn_provider_del": "🗑️ Eliminar Seleccionada",
        "btn_provider_test": "⚡ Probar Conexión",
        "btn_run_mplus": "⚔️ Importar Datos de Mítica+",
        "btn_run_guild": "🔄 Sincronizar Fuentes de Hermandad",
        "btn_run_discord": "💬 Sincronizar Bot de Discord",
        "lbl_update_available": "Update Available: v{remote_version}",
        "btn_update_now": "Actualizar Ahora",
        "gow_pending_note": "⚠️ Guilds of WoW está pendiente de API. Use WoW Audit o WoWUtils.",
        "gow_pending_title": "Proveedor Pendiente",
        "gow_pending_dialog": "La integración de Guilds of WoW está pendiente de acceso a API. Por favor, seleccione WoW Audit o WoWUtils para la sincronización."
    }
}

class RLMImporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RaidLootMatrix Companion - Gold Edition")
        self.root.geometry("980x700")
        self.root.minsize(880, 600)
        self.root.configure(bg=BG_DARK)

        # Configure global options for Tcl/Tk controls to eliminate white spots on dropdown popups & listboxes
        self.root.option_add('*Listbox.background', BG_ENTRY)
        self.root.option_add('*Listbox.foreground', FG_TEXT)
        self.root.option_add('*Listbox.selectBackground', FG_GOLD_DARK)
        self.root.option_add('*Listbox.selectForeground', FG_HEADER)
        self.root.option_add('*Listbox.font', ('Segoe UI', 9))
        self.root.option_add('*TCombobox*Listbox.background', BG_ENTRY)
        self.root.option_add('*TCombobox*Listbox.foreground', FG_TEXT)
        self.root.option_add('*TCombobox*Listbox.selectBackground', FG_GOLD_DARK)
        self.root.option_add('*TCombobox*Listbox.selectForeground', FG_HEADER)
        self.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 9))

        # Load Icon if available
        self.icon_path = pathlib.Path(__file__).parent / "rlm_icon.ico"
        if self.icon_path.exists():
            try:
                self.root.iconbitmap(str(self.icon_path))
            except Exception:
                pass

        self.config_path = pathlib.Path(__file__).parent / "rlm_importer_config.json"
        self.settings = self.load_settings()
        self.ensure_provider_schema()

        self.setup_styles()
        self.create_widgets()

        # Redirect stdout and stderr so all module prints stream live to the GUI console log
        sys.stdout = StdoutRedirector(self.log_message)
        sys.stderr = StdoutRedirector(self.log_message)

        self.log_message(f"RaidLootMatrix Companion v{VERSION} (Gold Edition) initialized successfully.")
        self.check_for_updates()

    def L(self, key):
        lang = self.settings.get("language", "en")
        loc = LOCALES.get(lang, LOCALES["en"])
        return loc.get(key, LOCALES["en"].get(key, key))

    def load_settings(self):
        defaults = {
            "language": "en",
            "region": "us",
            "wow_path": r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF",
            "rio_delay": 0.35,
            "schedule_am": "06:00",
            "schedule_pm": "18:00",
            "schedule_logon": True,
            "discord_sync_key": "",
            "discord_sync_url": "https://rlm-desktop-companion-production.up.railway.app/api/sync",
            "sync_on_import": True,
            "sync_on_wow_exit": True,
            "run_on_startup": True,
            "minimize_on_close": True,
            "season": "season-tww-2",
            "guild_providers": []
        }
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    defaults.update(cfg)
            except Exception as e:
                print(f"Error loading config JSON: {e}")
        return defaults

    def ensure_provider_schema(self):
        """Auto-migrate old wowaudit_sync entries into the new guild_providers schema."""
        if "guild_providers" not in self.settings or not isinstance(self.settings["guild_providers"], list):
            self.settings["guild_providers"] = []

        if "wowaudit_sync" in self.settings:
            existing_pairs = {(p.get("provider", "wowaudit"), p.get("rlm_profile_key", "")) for p in self.settings["guild_providers"]}
            for item in self.settings.get("wowaudit_sync", []):
                pkey = item.get("rlm_profile_key", "")
                if ("wowaudit", pkey) not in existing_pairs:
                    self.settings["guild_providers"].append({
                        "provider": "wowaudit",
                        "name": item.get("wowaudit_team_name", "WoW Audit Team"),
                        "api_key": item.get("api_key", ""),
                        "rlm_profile_key": pkey,
                        "sync_roster": True,
                        "sync_calendar": True,
                        "sync_wishlists": True
                    })
                    existing_pairs.add(("wowaudit", pkey))

    def check_for_updates(self):
        def task():
            try:
                headers = {
                    "User-Agent": getattr(rlm_guild_providers, "DEFAULT_USER_AGENT", "RLMCompanion/1.3.3"),
                    "Accept": "application/vnd.github.v3+json"
                }
                url = "https://api.github.com/repos/Rynedelewis/RLM-Desktop-Companion/releases/latest"
                r = requests.get(url, headers=headers, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    tag = data.get("tag_name", "").strip().lstrip("v")
                    if tag and tag > VERSION:
                        self.root.after(0, lambda: self.show_update_banner(tag, data.get("html_url")))
            except Exception as e:
                pass
        threading.Thread(target=task, daemon=True).start()

    def show_update_banner(self, remote_version, release_url):
        if hasattr(self, "header_frame"):
            update_frame = ttk.Frame(self.header_frame, style="Panel.TFrame")
            update_frame.pack(side="right", padx=10, pady=10)
            
            lbl = ttk.Label(update_frame, text=self.L("lbl_update_available").format(remote_version=remote_version), font=("Segoe UI", 9, "bold"), foreground="#fbbf24", style="Panel.TLabel")
            lbl.pack(side="left", padx=(5, 8))
            
            target_url = release_url or "https://github.com/Rynedelewis/RLM-Desktop-Companion/releases/latest"
            btn = ttk.Button(update_frame, text=self.L("btn_update_now"), style="GoldSave.TButton", command=lambda: webbrowser.open(target_url))
            btn.pack(side="right", padx=5)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Base Configuration
        self.style.configure(".", background=BG_DARK, foreground=FG_TEXT)
        self.style.configure("TFrame", background=BG_DARK)
        self.style.configure("Panel.TFrame", background=BG_PANEL, bordercolor=BORDER_GOLD, borderwidth=1, relief="solid")
        
        self.style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background=BG_PANEL, foreground=FG_HEADER, font=("Segoe UI", 11, "bold"))
        self.style.configure("Title.TLabel", background=BG_DARK, foreground=FG_GOLD, font=("Segoe UI", 16, "bold"))

        # Gold Theme Buttons
        self.style.configure("TButton", background=BG_PANEL, foreground=FG_TEXT, bordercolor=BORDER_GOLD, borderwidth=1, focuscolor=FG_GOLD, font=("Segoe UI", 9, "bold"))
        self.style.map("TButton", 
                       background=[("active", "#292524"), ("pressed", "#44403c")],
                       foreground=[("active", FG_GOLD_BRIGHT)])

        self.style.configure("Accent.TButton", background=FG_GOLD_DARK, foreground=FG_HEADER, bordercolor=FG_GOLD, borderwidth=1, font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", 
                       background=[("active", "#d97706"), ("pressed", "#92400e")],
                       foreground=[("active", "#ffffff")])

        self.style.configure("GoldSave.TButton", background="#d97706", foreground="#ffffff", bordercolor=FG_GOLD_BRIGHT, borderwidth=1, font=("Segoe UI", 10, "bold"))
        self.style.map("GoldSave.TButton", 
                       background=[("active", FG_GOLD), ("pressed", "#b45309")],
                       foreground=[("active", "#ffffff")])

        self.style.configure("TCheckbutton", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.map("TCheckbutton", background=[("active", BG_PANEL)], foreground=[("active", FG_GOLD_BRIGHT)])

        # Gold Notebook Tab Styling
        self.style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_TEXT, padding=[14, 8], font=("Segoe UI", 10, "bold"), bordercolor=BORDER_MUTED)
        self.style.map("TNotebook.Tab", 
                       background=[("selected", "#292524"), ("active", "#44403c")],
                       foreground=[("selected", FG_GOLD_BRIGHT), ("active", FG_HEADER)],
                       bordercolor=[("selected", FG_GOLD)])

        # Styled TCombobox for Gold dark theme
        self.style.configure("TCombobox", 
                             fieldbackground=BG_ENTRY, 
                             background=BG_PANEL, 
                             foreground=FG_TEXT,
                             selectbackground=FG_GOLD_DARK,
                             selectforeground=FG_HEADER,
                             bordercolor=BORDER_GOLD,
                             lightcolor=BORDER_GOLD,
                             darkcolor=BORDER_GOLD,
                             arrowcolor=FG_GOLD)
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", BG_ENTRY), ("focus", BG_ENTRY)],
                       foreground=[("readonly", FG_TEXT), ("focus", FG_TEXT)],
                       selectbackground=[("readonly", FG_GOLD_DARK)],
                       selectforeground=[("readonly", FG_HEADER)])

    def create_widgets(self):
        # Header banner frame with gold accent stroke
        self.header_frame = ttk.Frame(self.root, style="Panel.TFrame")
        self.header_frame.pack(fill="x", padx=15, pady=10)
        
        title_inner = ttk.Frame(self.header_frame, style="Panel.TFrame")
        title_inner.pack(side="left", padx=12, pady=10)

        self.lbl_title = ttk.Label(title_inner, text=self.L("header_title"), style="Title.TLabel")
        self.lbl_title.pack(side="left")
        self.lbl_subtitle = ttk.Label(title_inner, text=self.L("header_subtitle").format(VERSION=VERSION), font=("Segoe UI", 10, "italic"), foreground=FG_HEADER, style="Panel.TLabel")
        self.lbl_subtitle.pack(side="left", padx=6, pady=4)

        # Gold Save Button on Header Banner
        self.btn_save = ttk.Button(self.header_frame, text=self.L("btn_save_settings"), style="GoldSave.TButton", command=self.save_settings, width=22)
        self.btn_save.pack(side="right", padx=12, pady=10)

        # Main Notebook Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Tab 1: General & WoW Settings
        self.tab_general = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_general, text=self.L("tab_general"))
        self.build_tab_general(self.tab_general)

        # Tab 2: Guild Data Sources (Gold Edition!)
        self.tab_providers = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_providers, text=self.L("tab_providers"))
        self.build_tab_providers(self.tab_providers)

        # Tab 3: Automation
        self.tab_sched = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sched, text=self.L("tab_sched"))
        self.build_tab_sched(self.tab_sched)

        # Tab 4: Discord
        self.tab_discord = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_discord, text=self.L("tab_discord"))
        self.build_tab_discord(self.tab_discord)

        # Tab 5: Operations & Logs
        self.tab_console = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_console, text=self.L("tab_console"))
        self.build_tab_console(self.tab_console)

    def build_tab_general(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_card_wow_hdr = ttk.Label(card, text=self.L("card_wow_hdr"), style="Header.TLabel")
        self.lbl_card_wow_hdr.pack(fill="x", padx=15, pady=(15, 10))

        grid = ttk.Frame(card, style="Panel.TFrame")
        grid.pack(fill="x", padx=15, pady=5)

        # Language
        self.lbl_language = ttk.Label(grid, text=self.L("lbl_language"), style="Panel.TLabel")
        self.lbl_language.grid(row=0, column=0, sticky="w", pady=6)
        self.cb_language = ttk.Combobox(grid, values=["English", "简体中文", "繁體中文", "Español"], state="readonly", width=18)
        self.cb_language.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=6)
        lang = self.settings.get("language", "en")
        if lang == "zh": self.cb_language.set("简体中文")
        elif lang == "zh_tw": self.cb_language.set("繁體中文")
        elif lang == "es": self.cb_language.set("Español")
        else: self.cb_language.set("English")
        self.cb_language.bind("<<ComboboxSelected>>", self.on_language_changed)

        # Region
        self.lbl_region = ttk.Label(grid, text=self.L("lbl_region"), style="Panel.TLabel")
        self.lbl_region.grid(row=1, column=0, sticky="w", pady=6)
        self.cb_region = ttk.Combobox(grid, values=["us", "eu", "tw", "kr", "cn"], state="readonly", width=18)
        self.cb_region.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=6)
        self.cb_region.set(self.settings.get("region", "us"))

        # RIO API Delay
        self.lbl_rio_delay = ttk.Label(grid, text=self.L("lbl_rio_delay"), style="Panel.TLabel")
        self.lbl_rio_delay.grid(row=2, column=0, sticky="w", pady=6)
        self.ent_rio_delay = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1, width=20)
        self.ent_rio_delay.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=6)
        self.ent_rio_delay.insert(0, str(self.settings.get("rio_delay", 0.35)))

        # WoW Directory Selector
        self.lbl_wow_path = ttk.Label(grid, text=self.L("lbl_wow_path"), style="Panel.TLabel")
        self.lbl_wow_path.grid(row=3, column=0, sticky="w", pady=6)
        dir_frame = ttk.Frame(grid, style="Panel.TFrame")
        dir_frame.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=6)
        dir_frame.columnconfigure(0, weight=1)

        self.ent_wow_path = tk.Entry(dir_frame, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        self.ent_wow_path.grid(row=0, column=0, sticky="ew")
        self.ent_wow_path.insert(0, self.settings.get("wow_path", ""))

        self.btn_browse = ttk.Button(dir_frame, text=self.L("btn_browse"), command=self.browse_wow_directory, width=10)
        self.btn_browse.grid(row=0, column=1, padx=(6, 0))

        grid.columnconfigure(1, weight=1)

    def build_tab_providers(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_card_providers_hdr = ttk.Label(card, text=self.L("card_providers_hdr"), style="Header.TLabel")
        self.lbl_card_providers_hdr.pack(fill="x", padx=15, pady=(15, 10))

        grid = ttk.Frame(card, style="Panel.TFrame")
        grid.pack(fill="x", padx=15, pady=5)

        # Provider Selector
        self.lbl_provider_type = ttk.Label(grid, text=self.L("lbl_provider_type"), style="Panel.TLabel")
        self.lbl_provider_type.grid(row=0, column=0, sticky="w", pady=5)
        
        provider_frame = ttk.Frame(grid, style="Panel.TFrame")
        provider_frame.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)

        self.cb_provider_type = ttk.Combobox(provider_frame, values=["WoW Audit", "WoWUtils", "Guilds of WoW (Pending)"], state="readonly", width=25)
        self.cb_provider_type.pack(side="left")
        self.cb_provider_type.set("WoW Audit")
        self.cb_provider_type.bind("<<ComboboxSelected>>", self.on_provider_type_changed)

        self.lbl_gow_notice = ttk.Label(provider_frame, text=self.L("gow_pending_note"), font=("Segoe UI", 9, "italic"), foreground="#f59e0b", style="Panel.TLabel")

        # API Key
        self.lbl_provider_key = ttk.Label(grid, text=self.L("lbl_provider_key"), style="Panel.TLabel")
        self.lbl_provider_key.grid(row=1, column=0, sticky="w", pady=5)
        self.ent_provider_key = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        self.ent_provider_key.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)

        # Group / Team ID (Optional for WoWUtils)
        self.lbl_group_id = ttk.Label(grid, text=self.L("lbl_group_id"), style="Panel.TLabel")
        self.lbl_group_id.grid(row=2, column=0, sticky="w", pady=5)
        self.ent_group_id = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        self.ent_group_id.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=5)

        # RLM Profile Selector
        self.lbl_provider_profile = ttk.Label(grid, text=self.L("lbl_provider_profile"), style="Panel.TLabel")
        self.lbl_provider_profile.grid(row=3, column=0, sticky="w", pady=5)
        self.cb_provider_profile = ttk.Combobox(grid, state="readonly")
        self.cb_provider_profile.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=5)

        # Sync Scope Checkboxes (Default Roster & Calendar enabled)
        self.lbl_sync_options = ttk.Label(grid, text=self.L("lbl_sync_options"), style="Panel.TLabel")
        self.lbl_sync_options.grid(row=4, column=0, sticky="w", pady=5)

        chk_frame = ttk.Frame(grid, style="Panel.TFrame")
        chk_frame.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=5)

        self.var_sync_roster = tk.BooleanVar(value=True)
        self.chk_sync_roster = ttk.Checkbutton(chk_frame, text=self.L("chk_sync_roster"), variable=self.var_sync_roster)
        self.chk_sync_roster.pack(side="left", padx=(0, 10))

        self.var_sync_calendar = tk.BooleanVar(value=True)
        self.chk_sync_calendar = ttk.Checkbutton(chk_frame, text=self.L("chk_sync_calendar"), variable=self.var_sync_calendar)
        self.chk_sync_calendar.pack(side="left", padx=(0, 10))

        self.var_sync_wishlists = tk.BooleanVar(value=False)
        self.chk_sync_wishlists = ttk.Checkbutton(chk_frame, text=self.L("chk_sync_wishlists"), variable=self.var_sync_wishlists)
        self.chk_sync_wishlists.pack(side="left")

        grid.columnconfigure(1, weight=1)

        # Action Buttons
        btn_frame = ttk.Frame(card, style="Panel.TFrame")
        btn_frame.pack(fill="x", padx=15, pady=10)

        self.btn_provider_add = ttk.Button(btn_frame, text=self.L("btn_provider_add"), command=self.add_provider_mapping)
        self.btn_provider_add.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_provider_test = ttk.Button(btn_frame, text=self.L("btn_provider_test"), command=self.test_provider_connection)
        self.btn_provider_test.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_provider_del = ttk.Button(btn_frame, text=self.L("btn_provider_del"), command=self.del_provider_mapping)
        self.btn_provider_del.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Providers Listbox with Gold Selection Highlight
        self.lst_providers = tk.Listbox(card, bg=BG_ENTRY, fg=FG_TEXT, selectbackground=FG_GOLD_DARK, selectforeground=FG_HEADER, highlightbackground=BORDER_GOLD, relief="flat", height=6)
        self.lst_providers.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.ent_wow_path.bind("<FocusOut>", self.refresh_profile_dropdown)
        self.refresh_profile_dropdown()
        self.update_providers_listbox()

    def on_provider_type_changed(self, event=None):
        ptype = self.cb_provider_type.get().lower()
        if "guild" in ptype or "pending" in ptype:
            self.lbl_gow_notice.pack(side="left", padx=(10, 0))
        else:
            self.lbl_gow_notice.pack_forget()

    def build_tab_sched(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_card_sched_hdr = ttk.Label(card, text=self.L("card_sched_hdr"), style="Header.TLabel")
        self.lbl_card_sched_hdr.pack(fill="x", padx=15, pady=(15, 10))

        grid = ttk.Frame(card, style="Panel.TFrame")
        grid.pack(fill="x", padx=15, pady=5)

        self.lbl_sched_am = ttk.Label(grid, text=self.L("lbl_sched_am"), style="Panel.TLabel")
        self.lbl_sched_am.grid(row=0, column=0, sticky="w", pady=6)
        self.ent_sched_am = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1, width=12)
        self.ent_sched_am.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=6)
        self.ent_sched_am.insert(0, self.settings.get("schedule_am", "06:00"))

        self.lbl_sched_pm = ttk.Label(grid, text=self.L("lbl_sched_pm"), style="Panel.TLabel")
        self.lbl_sched_pm.grid(row=1, column=0, sticky="w", pady=6)
        self.ent_sched_pm = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1, width=12)
        self.ent_sched_pm.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=6)
        self.ent_sched_pm.insert(0, self.settings.get("schedule_pm", "18:00"))

        self.var_sched_logon = tk.BooleanVar(value=self.settings.get("schedule_logon", True))
        self.chk_logon = ttk.Checkbutton(grid, text=self.L("chk_logon"), variable=self.var_sched_logon)
        self.chk_logon.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        self.var_run_on_startup = tk.BooleanVar(value=self.settings.get("run_on_startup", True))
        self.chk_startup = ttk.Checkbutton(grid, text=self.L("chk_startup"), variable=self.var_run_on_startup)
        self.chk_startup.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)

        self.var_sync_on_wow_exit = tk.BooleanVar(value=self.settings.get("sync_on_wow_exit", True))
        self.chk_wow_exit = ttk.Checkbutton(grid, text=self.L("chk_wow_exit"), variable=self.var_sync_on_wow_exit)
        self.chk_wow_exit.grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        self.var_minimize_on_close = tk.BooleanVar(value=self.settings.get("minimize_on_close", True))
        self.chk_minimize_on_close = ttk.Checkbutton(grid, text=self.L("chk_minimize_on_close"), variable=self.var_minimize_on_close)
        self.chk_minimize_on_close.grid(row=5, column=0, columnspan=2, sticky="w", pady=6)

        task_btn_frame = ttk.Frame(card, style="Panel.TFrame")
        task_btn_frame.pack(fill="x", padx=15, pady=15)

        self.btn_register = ttk.Button(task_btn_frame, text=self.L("btn_register"), command=self.register_background_tasks)
        self.btn_register.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_unregister = ttk.Button(task_btn_frame, text=self.L("btn_unregister"), command=self.unregister_background_tasks)
        self.btn_unregister.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def build_tab_discord(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_card_discord_hdr = ttk.Label(card, text=self.L("card_discord_hdr"), style="Header.TLabel")
        self.lbl_card_discord_hdr.pack(fill="x", padx=15, pady=(15, 10))

        grid = ttk.Frame(card, style="Panel.TFrame")
        grid.pack(fill="x", padx=15, pady=5)

        self.lbl_discord_key = ttk.Label(grid, text=self.L("lbl_discord_key"), style="Panel.TLabel")
        self.lbl_discord_key.grid(row=0, column=0, sticky="w", pady=6)
        self.ent_discord_key = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        self.ent_discord_key.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)
        self.ent_discord_key.insert(0, self.settings.get("discord_sync_key", ""))

        self.var_sync_on_import = tk.BooleanVar(value=self.settings.get("sync_on_import", True))
        self.chk_sync_on_import = ttk.Checkbutton(grid, text=self.L("chk_sync_on_import"), variable=self.var_sync_on_import)
        self.chk_sync_on_import.grid(row=1, column=0, columnspan=2, sticky="w", pady=6)

        grid.columnconfigure(1, weight=1)

        self.btn_sync_now = ttk.Button(card, text=self.L("btn_sync_now"), style="Accent.TButton", command=self.trigger_discord_sync)
        self.btn_sync_now.pack(padx=15, pady=15, fill="x")

    def build_tab_console(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_console_hdr = ttk.Label(card, text=self.L("lbl_console_hdr"), style="Header.TLabel")
        self.lbl_console_hdr.pack(fill="x", padx=15, pady=(15, 10))

        action_bar = ttk.Frame(card, style="Panel.TFrame")
        action_bar.pack(fill="x", padx=15, pady=5)

        self.lbl_week_mode = ttk.Label(action_bar, text=self.L("lbl_week_mode"), style="Panel.TLabel")
        self.lbl_week_mode.pack(side="left", pady=4)
        
        vals = [self.L("week_both"), self.L("week_current"), self.L("week_last")]
        self.cb_week_mode = ttk.Combobox(action_bar, values=vals, state="readonly", width=12)
        self.cb_week_mode.set(self.L("week_both"))
        self.cb_week_mode.pack(side="left", padx=6)

        self.btn_run_mplus = ttk.Button(action_bar, text=self.L("btn_run_mplus"), style="Accent.TButton", command=self.trigger_live_import)
        self.btn_run_mplus.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_run_wowaudit = ttk.Button(action_bar, text=self.L("btn_run_guild"), style="Accent.TButton", command=self.trigger_wowaudit_sync)
        self.btn_run_wowaudit.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_run_discord = ttk.Button(action_bar, text=self.L("btn_run_discord"), command=self.trigger_discord_sync)
        self.btn_run_discord.pack(side="left", fill="x", expand=True, padx=4)

        console_frame = ttk.Frame(card, style="Panel.TFrame")
        console_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.txt_console = tk.Text(console_frame, bg="#090807", fg=FG_GOLD_BRIGHT, insertbackground=FG_GOLD_BRIGHT, 
                                   font=("Consolas", 9, "bold"), relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1, wrap="word")
        self.txt_console.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(console_frame, orient="vertical", command=self.txt_console.yview)
        scrollbar.pack(side="right", fill="y")
        self.txt_console.configure(yscrollcommand=scrollbar.set)

    def load_profile_choices(self):
        wow_path = self.ent_wow_path.get().strip() if hasattr(self, "ent_wow_path") else self.settings.get("wow_path", "")
        if not wow_path:
            return []
        try:
            return rlm_wowaudit_sync.locate_sv_path(wow_path) and rlm_wowaudit_sync.get_rlm_profiles(wow_path) or []
        except Exception:
            return []

    def refresh_profile_dropdown(self, event=None):
        raw_choices = self.load_profile_choices()
        self.profile_display_map = {}
        display_choices = []
        for raw in raw_choices:
            key = raw.split(" / ", 1)[1] if " / " in raw else raw
            if "::" in key:
                realm, profile = key.split("::", 1)
                parts = profile.rsplit("-", 1)
                display = f"{parts[0]} - {parts[1]}" if len(parts) == 2 else profile
            else:
                display = key
            self.profile_display_map[display] = raw
            display_choices.append(display)
            
        if hasattr(self, "cb_provider_profile"):
            self.cb_provider_profile.configure(values=display_choices)
            if display_choices:
                self.cb_provider_profile.set(display_choices[0])

    def update_providers_listbox(self):
        if not hasattr(self, "lst_providers"):
            return
        self.lst_providers.delete(0, tk.END)
        for p in self.settings.get("guild_providers", []):
            ptype = p.get("provider", "wowaudit").upper()
            name = p.get("name", "Guild")
            raw_prof = p.get("rlm_profile_key", "")
            profile = raw_prof.split("::")[-1] if raw_prof else "Default"
            scope = []
            if p.get("sync_roster", True): scope.append("Roster")
            if p.get("sync_calendar", True): scope.append("Calendar")
            if p.get("sync_wishlists", False): scope.append("Wishlists")
            scope_str = "+".join(scope) if scope else "None"
            self.lst_providers.insert(tk.END, f"[{ptype}] {name} ➔ {profile} ({scope_str})")

    def test_provider_connection(self):
        ptype_raw = self.cb_provider_type.get()
        ptype = ptype_raw.lower().replace(" ", "")
        
        if "guild" in ptype or "pending" in ptype:
            messagebox.showwarning(self.L("gow_pending_title"), self.L("gow_pending_dialog"))
            return

        key = self.ent_provider_key.get().strip()
        gid = self.ent_group_id.get().strip()
        if not key:
            messagebox.showerror("Error", "API Key is required to test connection.")
            return
        
        provider_cls = rlm_guild_providers.PROVIDER_CLASSES.get(ptype, rlm_guild_providers.WoWAuditProvider)
        ok, name, msg = provider_cls.test_connection(key, gid if gid else None)
        if ok:
            messagebox.showinfo("Success", f"Connection Successful!\nTarget: {name}")
            self.log_message(f"Provider test [{ptype.upper()}] succeeded: {name}")
        else:
            messagebox.showerror("Connection Failed", f"Could not connect: {msg}")

    def add_provider_mapping(self):
        ptype_display = self.cb_provider_type.get()
        ptype = ptype_display.lower().replace(" ", "")
        
        if "guild" in ptype or "pending" in ptype:
            messagebox.showwarning(self.L("gow_pending_title"), self.L("gow_pending_dialog"))
            return

        key = self.ent_provider_key.get().strip()
        gid = self.ent_group_id.get().strip()
        profile = self.cb_provider_profile.get().strip()

        if not key:
            messagebox.showerror("Error", "API Key is required.")
            return
        if not profile:
            messagebox.showerror("Error", "RLM Profile mapping is required.")
            return

        raw_profile = getattr(self, "profile_display_map", {}).get(profile, profile)
        providers_list = self.settings.setdefault("guild_providers", [])

        # Check if this team/profile is already linked to a source for this provider (1 team to 1 source mapping check)
        existing_idx = None
        for idx, existing in enumerate(providers_list):
            if existing.get("rlm_profile_key") == raw_profile and existing.get("provider") == ptype:
                existing_idx = idx
                break

        if existing_idx is not None:
            existing_name = providers_list[existing_idx].get("name", ptype_display)
            confirm = messagebox.askyesno(
                "Overwrite Existing Source Link?",
                f"The RLM profile '{profile}' is already linked to a {ptype_display} source ('{existing_name}').\n\n"
                f"Do you want to overwrite this existing link with the new API key / settings?"
            )
            if not confirm:
                return

        provider_cls = rlm_guild_providers.PROVIDER_CLASSES.get(ptype, rlm_guild_providers.WoWAuditProvider)
        ok, name, msg = provider_cls.test_connection(key, gid if gid else None)
        if not ok:
            messagebox.showerror("Connection Error", f"Connection test failed: {msg}")
            return

        new_entry = {
            "provider": ptype,
            "name": name if name else ptype_display,
            "api_key": key,
            "group_id": gid,
            "rlm_profile_key": raw_profile,
            "sync_roster": self.var_sync_roster.get(),
            "sync_calendar": self.var_sync_calendar.get(),
            "sync_wishlists": self.var_sync_wishlists.get()
        }

        if existing_idx is not None:
            providers_list[existing_idx] = new_entry
            self.log_message(f"Overwrote [{ptype.upper()}] source link for team/profile '{raw_profile}' with '{name}'")
        else:
            providers_list.append(new_entry)
            self.log_message(f"Mapped provider [{ptype.upper()}] '{name}' to profile '{raw_profile}'")

        self.update_providers_listbox()
        self.ent_provider_key.delete(0, tk.END)
        self.ent_group_id.delete(0, tk.END)

    def del_provider_mapping(self):
        sel = self.lst_providers.curselection()
        if not sel: return
        idx = sel[0]
        providers_list = self.settings.get("guild_providers", [])
        if 0 <= idx < len(providers_list):
            removed = providers_list.pop(idx)
            self.update_providers_listbox()
            self.log_message(f"Removed provider mapping: {removed.get('name')}")

    def save_settings(self):
        self.settings["region"] = self.cb_region.get().strip().lower()
        self.settings["wow_path"] = self.ent_wow_path.get().strip()
        try:
            self.settings["rio_delay"] = float(self.ent_rio_delay.get().strip())
        except ValueError:
            self.settings["rio_delay"] = 0.35

        self.settings["schedule_am"] = self.ent_sched_am.get().strip()
        self.settings["schedule_pm"] = self.ent_sched_pm.get().strip()
        self.settings["schedule_logon"] = self.var_sched_logon.get()
        self.settings["discord_sync_key"] = self.ent_discord_key.get().strip()
        self.settings["sync_on_import"] = self.var_sync_on_import.get()
        self.settings["sync_on_wow_exit"] = self.var_sync_on_wow_exit.get()
        self.settings["run_on_startup"] = self.var_run_on_startup.get()
        self.settings["minimize_on_close"] = self.var_minimize_on_close.get()

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.log_message("Settings saved successfully to config JSON.")
            messagebox.showinfo(self.L("msg_success_title"), self.L("msg_success_saved"))
        except Exception as e:
            self.log_message(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def browse_wow_directory(self):
        dir_selected = filedialog.askdirectory(title=self.L("dialog_select_wtf"), initialdir=r"C:\Program Files (x86)\World of Warcraft")
        if dir_selected:
            self.ent_wow_path.delete(0, tk.END)
            self.ent_wow_path.insert(0, os.path.normpath(dir_selected))

    def on_language_changed(self, event=None):
        lang_str = self.cb_language.get()
        new_lang = "en"
        if lang_str == "简体中文": new_lang = "zh"
        elif lang_str == "繁體中文": new_lang = "zh_tw"
        elif lang_str == "Español": new_lang = "es"

        self.settings["language"] = new_lang
        self.save_settings()

    def log_message(self, msg):
        if hasattr(self, "txt_console"):
            self.txt_console.insert(tk.END, f"{msg}\n")
            self.txt_console.see(tk.END)

    def trigger_live_import(self):
        def task():
            self.log_message("--- Starting Mythic+ Import ---")
            try:
                import raidlootmatrix_mplus
                raidlootmatrix_mplus.main()
                self.log_message("--- Mythic+ Import Completed ---")
            except Exception as e:
                self.log_message(f"Import Error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def trigger_wowaudit_sync(self):
        def task():
            self.log_message("--- Starting Guild Data Sync (All Sources) ---")
            try:
                import rlm_wowaudit_sync
                rlm_wowaudit_sync.main()
                self.log_message("--- Guild Data Sync Task Finished ---")
            except Exception as e:
                self.log_message(f"Sync Error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def trigger_discord_sync(self):
        def task():
            self.log_message("--- Starting Discord Sync ---")
            try:
                import rlm_discord_sync
                rlm_discord_sync.main()
                self.log_message("--- Discord Sync Finished ---")
            except Exception as e:
                self.log_message(f"Discord Sync Error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def register_background_tasks(self):
        self.log_message("Registering background Windows scheduled tasks...")
        messagebox.showinfo("Automation", self.L("msg_success_saved"))

    def unregister_background_tasks(self):
        self.log_message("Removing background Windows scheduled tasks...")

if __name__ == "__main__":
    root = tk.Tk()
    app = RLMImporterApp(root)
    root.mainloop()
