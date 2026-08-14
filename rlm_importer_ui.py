import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys

# Self-healing PyInstaller environment cleanup
meipass_env = os.environ.get("_MEIPASS")
if meipass_env and not os.path.exists(meipass_env):
    os.environ.pop("_MEIPASS", None)
    os.environ.pop("_MEIPASS2", None)

import time
import pathlib
import platform
import tempfile
import threading
import subprocess
import pystray
try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
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

VERSION = "1.7.8"

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
        "chk_sync_alts": "Include Alt Characters (Default)",
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

        if getattr(sys, "frozen", False):
            self.app_dir = pathlib.Path(sys.executable).parent
            meipass = pathlib.Path(getattr(sys, "_MEIPASS", self.app_dir))
        else:
            self.app_dir = pathlib.Path(__file__).parent
            meipass = self.app_dir

        # Load Icon if available (both .ico and .png formats for titlebar and taskbar)
        self.icon_path = next((p for p in [meipass / "rlm_icon.ico", self.app_dir / "rlm_icon.ico"] if p and p.exists()), None)
        self.png_icon_path = next((p for p in [meipass / "rlm_icon.png", self.app_dir / "rlm_icon.png"] if p and p.exists()), None)
        self.tk_icon = None

        if self.icon_path and self.icon_path.exists():
            try:
                self.root.iconbitmap(default=str(self.icon_path))
                self.root.iconbitmap(str(self.icon_path))
            except Exception:
                pass

        if self.png_icon_path and PIL_AVAILABLE:
            try:
                img = Image.open(self.png_icon_path)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.tk_icon)
            except Exception:
                pass

        self.config_path = self.app_dir / "rlm_importer_config.json"
        self.settings = self.load_settings()
        self.team_settings_data = self.settings.get("team_discord_settings", {})
        self.ensure_provider_schema()

        self.apply_window_icon(self.root)

        self.setup_styles()
        self.create_widgets()

        # Redirect stdout and stderr so all module prints stream live to the GUI console log
        sys.stdout = StdoutRedirector(self.log_message)
        sys.stderr = StdoutRedirector(self.log_message)

        self.log_message(f"RaidLootMatrix Companion v{VERSION} (Gold Edition) initialized successfully.")
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.check_for_updates()

    def apply_window_icon(self, window):
        if hasattr(self, "icon_path") and self.icon_path and self.icon_path.exists():
            try:
                window.iconbitmap(default=str(self.icon_path))
                window.iconbitmap(str(self.icon_path))
            except Exception:
                pass
        if hasattr(self, "tk_icon") and self.tk_icon:
            try:
                window.iconphoto(True, self.tk_icon)
            except Exception:
                pass

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
        """Auto-migrate old wowaudit_sync entries into the new guild_providers schema once."""
        if "guild_providers" not in self.settings or not isinstance(self.settings["guild_providers"], list):
            self.settings["guild_providers"] = []

        if self.settings.get("migrated_legacy_wowaudit"):
            return

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
                        "sync_alts": True
                    })
                    existing_pairs.add(("wowaudit", pkey))

        self.settings["migrated_legacy_wowaudit"] = True
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def check_for_updates(self, manual=False):
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
                        download_url = f"https://github.com/Rynedelewis/RLM-Desktop-Companion/releases/download/v{tag}/RLM_Companion_Setup_v{tag}.exe"
                        for asset in data.get("assets", []):
                            aname = asset.get("name", "").lower()
                            if "setup" in aname and aname.endswith(".exe"):
                                download_url = asset.get("browser_download_url")
                                break
                            elif aname == "rlm_companion.exe":
                                download_url = asset.get("browser_download_url")
                            elif aname.endswith(".exe"):
                                download_url = asset.get("browser_download_url")
                        self.root.after(0, lambda: self.show_update_banner(tag, download_url))
                        self.root.after(500, lambda: self.show_update_popup(tag, download_url))
                    elif manual:
                        self.root.after(0, lambda: self.show_toast_banner(f"✅ You are running the latest version (v{VERSION})!"))
                elif manual:
                    self.root.after(0, lambda: self.show_toast_banner("Could not check for updates. Please try again later.", toast_type="error"))
            except Exception as e:
                if manual:
                    self.root.after(0, lambda err=e: self.show_toast_banner(f"Update check failed: {err}", toast_type="error"))
            finally:
                # Schedule recurring automatic check every 6 hours (21,600,000 ms)
                try:
                    self.root.after(21600000, lambda: self.check_for_updates(manual=False))
                except Exception:
                    pass
        threading.Thread(target=task, daemon=True).start()

    def show_update_banner(self, remote_version, download_url):
        if hasattr(self, "header_action_frame"):
            if hasattr(self, "btn_update_header") and self.btn_update_header:
                try:
                    self.btn_update_header.destroy()
                except Exception:
                    pass
            
            self.btn_update_header = ttk.Button(
                self.header_action_frame, 
                text=f"🚀 Update to v{remote_version}", 
                style="Accent.TButton", 
                command=lambda: self.download_and_apply_update(download_url, remote_version)
            )
            self.btn_update_header.pack(side="right", padx=(0, 10))

    def show_update_popup(self, remote_version, download_url):
        try:
            win = tk.Toplevel(self.root)
            win.title("🚀 Update Available")
            win.geometry("520x290")
            win.resizable(False, False)
            win.configure(bg=BG_DARK)
            win.transient(self.root)
            win.grab_set()
            self.apply_window_icon(win)

            card = ttk.Frame(win, style="Panel.TFrame")
            card.pack(fill="both", expand=True, padx=12, pady=12)

            lbl_hdr = ttk.Label(card, text=f"🚀 RaidLootMatrix Companion v{remote_version} Available!", style="Header.TLabel", foreground=FG_GOLD_BRIGHT)
            lbl_hdr.pack(anchor="w", padx=15, pady=(15, 8))

            lbl_msg = ttk.Label(
                card, 
                text=f"A new version of RaidLootMatrix Companion (v{remote_version}) is ready!\n\n"
                     f"Click 'Update & Restart Now' to automatically download and launch v{remote_version}.\n"
                     f"No manual file extraction or re-configuration is required.",
                style="Panel.TLabel",
                wraplength=480,
                justify="left"
            )
            lbl_msg.pack(anchor="w", padx=15, pady=(0, 15))

            btn_frame = ttk.Frame(card, style="Panel.TFrame")
            btn_frame.pack(fill="x", padx=15, pady=(10, 0))

            btn_do_update = ttk.Button(
                btn_frame, 
                text="🚀 Update & Restart Now", 
                style="Accent.TButton", 
                command=lambda: [win.destroy(), self.download_and_apply_update(download_url, remote_version)]
            )
            btn_do_update.pack(side="right", padx=(8, 0))

            btn_later = ttk.Button(btn_frame, text="Remind Me Later", style="TButton", command=win.destroy)
            btn_later.pack(side="right")
        except Exception as e:
            pass

    def download_and_apply_update(self, download_url, remote_version):
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Downloading Update...")
        progress_win.geometry("450x160")
        progress_win.resizable(False, False)
        progress_win.configure(bg=BG_DARK)
        progress_win.transient(self.root)
        progress_win.grab_set()
        self.apply_window_icon(progress_win)

        card = ttk.Frame(progress_win, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=12, pady=12)

        lbl = ttk.Label(card, text=f"Downloading RaidLootMatrix Companion v{remote_version}...", style="Header.TLabel", foreground=FG_GOLD_BRIGHT)
        lbl.pack(anchor="w", padx=15, pady=(15, 8))

        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(card, variable=progress_var, maximum=100)
        progress_bar.pack(fill="x", padx=15, pady=5)

        lbl_status = ttk.Label(card, text="Connecting to GitHub...", style="Panel.TLabel")
        lbl_status.pack(anchor="w", padx=15, pady=(5, 10))

        def worker():
            try:
                headers = {"User-Agent": getattr(rlm_guild_providers, "DEFAULT_USER_AGENT", "RLMCompanion/1.3.3")}
                r = requests.get(download_url, headers=headers, stream=True, timeout=30)
                total_size = int(r.headers.get('content-length', 0))
                
                is_zip = download_url.lower().endswith(".zip")
                is_setup = "setup" in download_url.lower() and download_url.lower().endswith(".exe")

                temp_dir = pathlib.Path(tempfile.gettempdir())
                
                if is_setup:
                    download_filename = "RLM_Companion_update_setup.exe"
                elif is_zip:
                    download_filename = "RLM_Companion_update.zip"
                else:
                    download_filename = "RLM_Companion_update.exe"

                target_file = temp_dir / download_filename
                downloaded = 0

                with open(target_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = (downloaded / total_size) * 100.0
                                mb_down = downloaded / (1024 * 1024)
                                mb_tot = total_size / (1024 * 1024)
                                progress_win.after(0, lambda p=pct, d=mb_down, t=mb_tot: [
                                    progress_var.set(p),
                                    lbl_status.configure(text=f"Downloaded {d:.1f} MB / {t:.1f} MB ({p:.0f}%)")
                                ])

                progress_win.after(0, lambda: lbl_status.configure(text="Download complete! Restarting application..."))
                time.sleep(1)

                batch_path = temp_dir / "apply_update.bat"
                target_exe_name = pathlib.Path(sys.executable).name if getattr(sys, "frozen", False) else "RLM_Companion.exe"
                app_dir_str = str(self.app_dir)
                target_file_str = str(target_file)
                installed_exe_str = str(self.app_dir / target_exe_name)

                if is_setup:
                    batch_content = f"""@echo off
set "_MEIPASS="
set "_MEIPASS2="
taskkill /F /IM "{target_exe_name}" > NUL 2>&1
timeout /t 4 /nobreak > NUL
start "" /wait "{target_file_str}" /DIR="{app_dir_str}" /FORCECLOSEAPPLICATIONS /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
timeout /t 2 /nobreak > NUL
del /f "{target_file_str}" > NUL 2>&1
powershell -Command "Remove-Item Env:\\_MEIPASS -ErrorAction SilentlyContinue; Remove-Item Env:\\_MEIPASS2 -ErrorAction SilentlyContinue; Start-Process '{installed_exe_str}'"
del /f "%~f0" > NUL
"""
                else:
                    batch_content = f"""@echo off
set "_MEIPASS="
set "_MEIPASS2="
taskkill /F /IM "{target_exe_name}" > NUL 2>&1
timeout /t 3 /nobreak > NUL
cd /d "{app_dir_str}"
if exist "_internal" rmdir /s /q "_internal" > NUL 2>&1
if exist "{target_file_str}" (
    if "{download_filename}"=="RLM_Companion_update.zip" (
        powershell -Command "Expand-Archive -Path '{target_file_str}' -DestinationPath '.' -Force" > NUL 2>&1
        del /f "{target_file_str}" > NUL 2>&1
    ) else (
        copy /y "{target_file_str}" "{target_exe_name}" > NUL
        del /f "{target_file_str}" > NUL
    )
)
if exist "_internal" rmdir /s /q "_internal" > NUL 2>&1
timeout /t 1 /nobreak > NUL
powershell -Command "Remove-Item Env:\\_MEIPASS -ErrorAction SilentlyContinue; Remove-Item Env:\\_MEIPASS2 -ErrorAction SilentlyContinue; Start-Process '{target_exe_name}'"
del /f "%~f0" > NUL
"""
                batch_path.write_text(batch_content, encoding="utf-8")
                
                # Clean _MEIPASS from env so child process does not inherit stale PyInstaller temp path
                clean_env = os.environ.copy()
                clean_env.pop("_MEIPASS", None)
                clean_env.pop("_MEIPASS2", None)

                # Launch batch updater detached from temp directory and exit current app
                subprocess.Popen(["cmd.exe", "/c", str(batch_path)], cwd=str(temp_dir), env=clean_env)
                progress_win.after(100, self.exit_app)

            except Exception as e:
                progress_win.after(0, lambda err=e: messagebox.showerror("Update Error", f"Failed to download update: {err}"))
                progress_win.after(0, progress_win.destroy)

        threading.Thread(target=worker, daemon=True).start()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Base Configuration
        self.style.configure(".", background=BG_DARK, foreground=FG_TEXT)
        self.style.configure("TFrame", background=BG_DARK)
        self.style.configure("Panel.TFrame", background=BG_PANEL, bordercolor=BORDER_GOLD, borderwidth=1, relief="solid")
        self.style.configure("HeaderAction.TFrame", background=BG_PANEL, borderwidth=0)
        
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

        # Header Action Buttons Frame (borderless container)
        self.header_action_frame = ttk.Frame(self.header_frame, style="HeaderAction.TFrame")
        self.header_action_frame.pack(side="right", padx=12, pady=10)

        # Gold Save Button on Header Banner
        self.btn_save = ttk.Button(self.header_action_frame, text=self.L("btn_save_settings"), style="GoldSave.TButton", command=self.save_settings, width=18)
        self.btn_save.pack(side="right")

        # Check for Updates Button on Header Banner
        self.btn_check_update = ttk.Button(self.header_action_frame, text="🔄 Check Updates", style="TButton", command=lambda: self.check_for_updates(manual=True))
        self.btn_check_update.pack(side="right", padx=(0, 8))

        # Save Confirmation Label on Header Banner
        self.lbl_save_status = ttk.Label(self.header_action_frame, text="", font=("Segoe UI", 10, "bold"), foreground=FG_GOLD_BRIGHT, style="Panel.TLabel")
        self.lbl_save_status.pack(side="right", padx=(0, 15))
        self._toast_timer = None

        # Main Notebook Tabs (Top Half)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="x", expand=False, padx=15, pady=(0, 5))

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

        # Permanent Static Operations & Console Execution Log Panel (Bottom Half)
        self.static_console_frame = ttk.Frame(self.root, style="Panel.TFrame")
        self.static_console_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.build_static_console(self.static_console_frame)

    def show_toast_banner(self, message, toast_type="success"):
        if not hasattr(self, "lbl_save_status"):
            return
        
        fg_color = FG_GOLD_BRIGHT if toast_type == "success" else "#e74c3c"
        icon = "✨" if toast_type == "success" else "⚠️"
        
        self.lbl_save_status.configure(text=f"{icon} {message}", foreground=fg_color)
        
        if getattr(self, "_toast_timer", None):
            self.root.after_cancel(self._toast_timer)
            
        self._toast_timer = self.root.after(3500, lambda: self.lbl_save_status.configure(text=""))

    def flash_save_button(self):
        if hasattr(self, "btn_save"):
            orig_text = self.L("btn_save_settings")
            self.btn_save.configure(text="✓ Saved Successfully!")
            self.root.after(1800, lambda: self.btn_save.configure(text=orig_text))

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

        # WoW Directory Selector
        self.lbl_wow_path = ttk.Label(grid, text=self.L("lbl_wow_path"), style="Panel.TLabel")
        self.lbl_wow_path.grid(row=2, column=0, sticky="w", pady=6)
        dir_frame = ttk.Frame(grid, style="Panel.TFrame")
        dir_frame.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=6)
        dir_frame.columnconfigure(0, weight=1)

        self.ent_wow_path = tk.Entry(dir_frame, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        self.ent_wow_path.grid(row=0, column=0, sticky="ew")
        self.ent_wow_path.insert(0, self.settings.get("wow_path", ""))

        self.btn_browse = ttk.Button(dir_frame, text=self.L("btn_browse"), command=self.browse_wow_directory, width=10)
        self.btn_browse.grid(row=0, column=1, padx=(6, 0))

        grid.columnconfigure(1, weight=1)

    def build_tab_providers(self, parent):
        container = ttk.Frame(parent, style="Panel.TFrame")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_card_providers_hdr = ttk.Label(container, text="🌐 Guild Data Sources & External Integrations", style="Header.TLabel")
        self.lbl_card_providers_hdr.pack(fill="x", padx=5, pady=(5, 10))

        # 2-Part Grid Container
        grid_container = ttk.Frame(container, style="Panel.TFrame")
        grid_container.pack(fill="both", expand=True, padx=5, pady=5)
        grid_container.columnconfigure(0, weight=1)
        grid_container.columnconfigure(1, weight=1)
        grid_container.rowconfigure(0, weight=1)

        # LEFT CARD: Add / Connect New Data Source Action Panel
        card_left = ttk.Frame(grid_container, style="Panel.TFrame", relief="solid", borderwidth=1)
        card_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=5)

        lbl_left_hdr = ttk.Label(card_left, text="➕ Connect New Guild Data Source", font=("Segoe UI", 11, "bold"), foreground=FG_GOLD_BRIGHT, style="Panel.TLabel")
        lbl_left_hdr.pack(anchor="w", padx=15, pady=(15, 8))

        lbl_desc = ttk.Label(card_left, text="Connect your guild management providers to sync rosters, calendar events, and alts into World of Warcraft:\n\n• WoWUtils: Automated Roster, Calendar & Alts Sync\n• WoW Audit: API Roster & Calendar Sync\n• Raider.IO: Mythic+ Scores & Dungeon Summaries", font=("Segoe UI", 9), foreground=FG_TEXT, justify="left", wrap=320, style="Panel.TLabel")
        lbl_desc.pack(anchor="w", padx=15, pady=(0, 15))

        self.btn_open_add_modal = ttk.Button(card_left, text="➕ Connect New Data Source", style="Accent.TButton", command=self.open_add_provider_modal)
        self.btn_open_add_modal.pack(anchor="w", padx=15, pady=(10, 15))

        # RIGHT CARD: Configured Connections List & Actions
        card_right = ttk.Frame(grid_container, style="Panel.TFrame", relief="solid", borderwidth=1)
        card_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=5)

        lbl_right_hdr = ttk.Label(card_right, text="📋 Active Guild Data Connections", font=("Segoe UI", 11, "bold"), foreground=FG_GOLD_BRIGHT, style="Panel.TLabel")
        lbl_right_hdr.pack(anchor="w", padx=15, pady=(15, 8))

        self.lst_providers = tk.Listbox(card_right, bg=BG_ENTRY, fg=FG_TEXT, selectbackground=FG_GOLD_DARK, selectforeground=FG_HEADER, highlightbackground=BORDER_GOLD, relief="flat", height=6)
        self.lst_providers.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        btn_frame = ttk.Frame(card_right, style="Panel.TFrame")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_provider_edit = ttk.Button(btn_frame, text="✏️ Edit Connection", command=self.open_edit_provider_modal)
        self.btn_provider_edit.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_provider_test = ttk.Button(btn_frame, text="🧪 Test", command=self.test_provider_connection)
        self.btn_provider_test.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_provider_del = ttk.Button(btn_frame, text="🗑️ Remove", command=self.del_provider_mapping)
        self.btn_provider_del.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.update_providers_listbox()

    def open_add_provider_modal(self):
        self.open_provider_modal(edit_idx=None)

    def open_edit_provider_modal(self):
        sel = self.lst_providers.curselection()
        if not sel:
            self.show_toast_banner("Please select a data source connection to edit.", toast_type="error")
            return
        self.open_provider_modal(edit_idx=sel[0])

    def open_provider_modal(self, edit_idx=None):
        providers_list = self.settings.get("guild_providers", [])
        is_edit = edit_idx is not None and 0 <= edit_idx < len(providers_list)
        p_data = providers_list[edit_idx] if is_edit else {}

        win = tk.Toplevel(self.root)
        win.title("✏️ Edit Guild Data Connection" if is_edit else "➕ Connect New Guild Data Source")
        win.geometry("540x460")
        win.resizable(False, False)
        win.configure(bg=BG_DARK)
        win.transient(self.root)
        win.grab_set()
        self.apply_window_icon(win)

        card = ttk.Frame(win, style="Panel.TFrame")
        card.pack(fill="both", expand=True, padx=15, pady=15)

        lbl_hdr = ttk.Label(card, text="✏️ Edit Connection Details" if is_edit else "➕ Configure Data Source Connection", style="Header.TLabel")
        lbl_hdr.pack(fill="x", padx=15, pady=(15, 10))

        grid = ttk.Frame(card, style="Panel.TFrame")
        grid.pack(fill="x", padx=15, pady=5)
        grid.columnconfigure(1, weight=1)

        # 1. Provider Type
        lbl_type = ttk.Label(grid, text="Data Source Provider:", style="Panel.TLabel")
        lbl_type.grid(row=0, column=0, sticky="w", pady=6)
        
        p_frame = ttk.Frame(grid, style="Panel.TFrame")
        p_frame.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=6)

        cb_type = ttk.Combobox(p_frame, values=["WoWUtils", "WoW Audit", "Guilds of WoW (Pending)"], state="readonly", width=26)
        cb_type.pack(side="left")
        
        init_type = p_data.get("provider", "wowutils").lower()
        cb_type.set("WoWUtils" if init_type == "wowutils" else ("WoW Audit" if init_type == "wowaudit" else "WoWUtils"))

        # 2. API Token / Key
        lbl_key = ttk.Label(grid, text="API Token / Key:", style="Panel.TLabel")
        lbl_key.grid(row=1, column=0, sticky="w", pady=6)
        ent_key = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        ent_key.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)
        ent_key.insert(0, p_data.get("api_key", ""))

        # 3. Group / Team ID
        lbl_group = ttk.Label(grid, text="Group / Team ID (Optional):", style="Panel.TLabel")
        lbl_group.grid(row=2, column=0, sticky="w", pady=6)
        ent_group = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        ent_group.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=6)
        ent_group.insert(0, p_data.get("group_id", ""))

        # 4. RLM Profile Selector
        lbl_prof = ttk.Label(grid, text="Target RLM Team Roster:", style="Panel.TLabel")
        lbl_prof.grid(row=3, column=0, sticky="w", pady=6)
        
        profile_choices = self.load_profile_choices()
        cb_prof = ttk.Combobox(grid, values=profile_choices, state="readonly" if profile_choices else "normal")
        cb_prof.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=6)
        
        init_raw_prof = p_data.get("rlm_profile_key", "")
        init_disp = next((disp for disp, raw in getattr(self, "profile_display_map", {}).items() if raw == init_raw_prof), init_raw_prof)
        if init_disp and init_disp in profile_choices:
            cb_prof.set(init_disp)
        elif profile_choices:
            cb_prof.set(profile_choices[0])

        # 5. Sync Scope Checkboxes
        lbl_scope = ttk.Label(grid, text="Sync Scope Options:", style="Panel.TLabel")
        lbl_scope.grid(row=4, column=0, sticky="w", pady=6)

        chk_f = ttk.Frame(grid, style="Panel.TFrame")
        chk_f.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=6)

        var_r = tk.BooleanVar(value=p_data.get("sync_roster", True))
        chk_r = ttk.Checkbutton(chk_f, text="Roster", variable=var_r)
        chk_r.pack(side="left", padx=(0, 10))

        var_c = tk.BooleanVar(value=p_data.get("sync_calendar", True))
        chk_c = ttk.Checkbutton(chk_f, text="Calendar", variable=var_c)
        chk_c.pack(side="left", padx=(0, 10))

        var_a = tk.BooleanVar(value=p_data.get("sync_alts", True))
        chk_a = ttk.Checkbutton(chk_f, text="Alts", variable=var_a)
        chk_a.pack(side="left", padx=(0, 10))

        var_m = tk.BooleanVar(value=p_data.get("sync_mplus", True))
        chk_m = ttk.Checkbutton(chk_f, text="Mythic+", variable=var_m)
        chk_m.pack(side="left")

        # Modal Action Buttons
        modal_btn_frame = ttk.Frame(card, style="Panel.TFrame")
        modal_btn_frame.pack(fill="x", padx=15, pady=(15, 10))

        def save_modal_connection():
            selected_type = cb_type.get().lower()
            provider_id = "wowutils" if "utils" in selected_type else ("wowaudit" if "audit" in selected_type else "wowutils")
            api_key = ent_key.get().strip()
            group_id = ent_group.get().strip()
            selected_disp_prof = cb_prof.get().strip()
            raw_prof_key = getattr(self, "profile_display_map", {}).get(selected_disp_prof, selected_disp_prof)

            if not api_key:
                self.show_toast_banner("Please enter a valid API Key / Token.", toast_type="error")
                return

            team_name = selected_disp_prof if selected_disp_prof else "Guild Team"
            provider_entry = {
                "provider": provider_id,
                "name": team_name,
                "api_key": api_key,
                "group_id": group_id,
                "rlm_profile_key": raw_prof_key,
                "sync_roster": var_r.get(),
                "sync_calendar": var_c.get(),
                "sync_alts": var_a.get(),
                "sync_mplus": var_m.get()
            }

            if is_edit:
                providers_list[edit_idx] = provider_entry
                self.log_message(f"Updated data connection for '{team_name}' [{provider_id}]")
            else:
                providers_list.append(provider_entry)
                self.log_message(f"Added new data connection for '{team_name}' [{provider_id}]")

            self.settings["guild_providers"] = providers_list
            self.save_settings()
            self.update_providers_listbox()
            win.destroy()

        def test_modal_connection():
            selected_type = cb_type.get().lower()
            provider_id = "wowutils" if "utils" in selected_type else "wowaudit"
            api_key = ent_key.get().strip()
            group_id = ent_group.get().strip()

            if not api_key:
                self.show_toast_banner("Please enter an API key to test.", toast_type="error")
                return

            def task():
                try:
                    if provider_id == "wowutils":
                        res = rlm_guild_providers.test_wowutils_connection(api_key)
                    else:
                        res = rlm_guild_providers.test_wowaudit_connection(api_key, group_id)
                    
                    if res.get("success"):
                        gname = res.get("guild_name") or res.get("team_name") or "Connected Guild"
                        self.root.after(0, lambda: self.show_toast_banner(f"Connected to '{gname}'!"))
                    else:
                        err = res.get("error", "Failed")
                        self.root.after(0, lambda: self.show_toast_banner(f"Connection Failed: {err}", toast_type="error"))
                except Exception as e:
                    self.root.after(0, lambda: self.show_toast_banner(f"Test Error: {e}", toast_type="error"))

            threading.Thread(target=task, daemon=True).start()

        btn_save_m = ttk.Button(modal_btn_frame, text="💾 Save Connection", style="Accent.TButton", command=save_modal_connection)
        btn_save_m.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_test_m = ttk.Button(modal_btn_frame, text="🧪 Test Connection", command=test_modal_connection)
        btn_test_m.pack(side="left", fill="x", expand=True, padx=5)

        btn_cancel_m = ttk.Button(modal_btn_frame, text="Cancel", command=win.destroy)
        btn_cancel_m.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def on_provider_checkbox_toggled(self):
        sel = self.lst_providers.curselection()
        if sel:
            idx = sel[0]
            providers_list = self.settings.get("guild_providers", [])
            if 0 <= idx < len(providers_list):
                providers_list[idx]["sync_roster"] = self.var_sync_roster.get()
                providers_list[idx]["sync_calendar"] = self.var_sync_calendar.get()
                providers_list[idx]["sync_alts"] = self.var_sync_alts.get()
                self.update_providers_listbox()
                self.lst_providers.selection_set(idx)
                self.save_settings()
                source_name = providers_list[idx].get('name', 'Guild')
                self.log_message(f"Updated sync options for source '{source_name}'")
                self.show_toast_banner(f"Updated sync options for provider '{source_name}'!")

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
        container = ttk.Frame(parent, style="Panel.TFrame")
        container.pack(fill="x", padx=10, pady=5)

        card = ttk.Frame(container, style="Panel.TFrame", relief="solid", borderwidth=1)
        card.pack(fill="x", padx=5, pady=5)

        # Header Row: Title & Active Team Selector
        top_bar = ttk.Frame(card, style="Panel.TFrame")
        top_bar.pack(fill="x", padx=12, pady=(10, 4))

        lbl_hdr = ttk.Label(top_bar, text="💬 Discord Bot Integration", font=("Segoe UI", 11, "bold"), foreground=FG_GOLD_BRIGHT, style="Panel.TLabel")
        lbl_hdr.pack(side="left")

        profile_choices = self.load_profile_choices()
        if not profile_choices:
            profile_choices = ["Default Guild Team"]

        lbl_team = ttk.Label(top_bar, text="Active Guild Team:", font=("Segoe UI", 9, "bold"), style="Panel.TLabel")
        lbl_team.pack(side="left", padx=(20, 6))

        self.cb_active_team = ttk.Combobox(top_bar, values=profile_choices, state="readonly", width=48)
        self.cb_active_team.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.cb_active_team.set(profile_choices[0])
        self.cb_active_team.bind("<<ComboboxSelected>>", self._on_team_selected)

        # Settings Grid
        grid_t = ttk.Frame(card, style="Panel.TFrame")
        grid_t.pack(fill="x", padx=12, pady=4)
        grid_t.columnconfigure(1, weight=1)

        # Row 0: Discord Sync Key + Fetch Channels Button
        lbl_key = ttk.Label(grid_t, text="Discord Sync Key:", style="Panel.TLabel")
        lbl_key.grid(row=0, column=0, sticky="w", pady=4)

        k_frame = ttk.Frame(grid_t, style="Panel.TFrame")
        k_frame.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)
        k_frame.columnconfigure(0, weight=1)

        self.ent_team_key = tk.Entry(k_frame, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_GOLD_BRIGHT, relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1)
        self.ent_team_key.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.ent_team_key.bind("<FocusOut>", lambda e: [self._save_current_team_view(), self.save_settings()])
        self.ent_team_key.bind("<KeyRelease>", lambda e: self._save_current_team_view())

        self.btn_team_fetch = ttk.Button(k_frame, text="🔄 Fetch Channels", command=self.fetch_channels_for_active_team, width=20)
        self.btn_team_fetch.grid(row=0, column=1, sticky="e")

        # Row 1: Connection Status Label
        self.lbl_team_status = ttk.Label(grid_t, text="⚠️ Enter Sync Key and click 'Fetch Channels' to load Discord dropdowns.", font=("Segoe UI", 9), foreground="#f39c12", style="Panel.TLabel")
        self.lbl_team_status.grid(row=1, column=0, columnspan=4, sticky="w", pady=(1, 4))

        # Row 2: EPGP Channel & Schedule
        lbl_epgp_c = ttk.Label(grid_t, text="EPGP Channel:", style="Panel.TLabel")
        lbl_epgp_c.grid(row=2, column=0, sticky="w", pady=4)
        self.cb_team_epgp_ch = ttk.Combobox(grid_t, values=[], width=22)
        self.cb_team_epgp_ch.grid(row=2, column=1, sticky="w", padx=(8, 15), pady=4)
        self.cb_team_epgp_ch.bind("<<ComboboxSelected>>", lambda e: [self._save_current_team_view(), self.save_settings()])
        self.cb_team_epgp_ch.bind("<FocusOut>", lambda e: [self._save_current_team_view(), self.save_settings()])

        lbl_epgp_s = ttk.Label(grid_t, text="EPGP Schedule:", style="Panel.TLabel")
        lbl_epgp_s.grid(row=2, column=2, sticky="w", pady=4)
        self.cb_team_epgp_sched = ttk.Combobox(grid_t, values=["On Roster/Loot Sync", "Post-Raid (On WoW Exit)", "Every 12 Hours", "Daily", "Disabled"], state="readonly", width=22)
        self.cb_team_epgp_sched.grid(row=2, column=3, sticky="w", padx=(8, 0), pady=4)
        self.cb_team_epgp_sched.bind("<<ComboboxSelected>>", lambda e: [self._save_current_team_view(), self.save_settings()])

        # Row 3: Mythic+ Channel & Schedule
        lbl_mplus_c = ttk.Label(grid_t, text="Mythic+ Channel:", style="Panel.TLabel")
        lbl_mplus_c.grid(row=3, column=0, sticky="w", pady=4)
        self.cb_team_mplus_ch = ttk.Combobox(grid_t, values=[], width=22)
        self.cb_team_mplus_ch.grid(row=3, column=1, sticky="w", padx=(8, 15), pady=4)
        self.cb_team_mplus_ch.bind("<<ComboboxSelected>>", lambda e: [self._save_current_team_view(), self.save_settings()])
        self.cb_team_mplus_ch.bind("<FocusOut>", lambda e: [self._save_current_team_view(), self.save_settings()])

        lbl_mplus_s = ttk.Label(grid_t, text="Mythic+ Schedule:", style="Panel.TLabel")
        lbl_mplus_s.grid(row=3, column=2, sticky="w", pady=4)
        self.cb_team_mplus_sched = ttk.Combobox(grid_t, values=["Tuesday Post-Reset (Default)", "Daily", "On M+ Import", "Disabled"], state="readonly", width=22)
        self.cb_team_mplus_sched.grid(row=3, column=3, sticky="w", padx=(8, 0), pady=4)
        self.cb_team_mplus_sched.bind("<<ComboboxSelected>>", lambda e: [self._save_current_team_view(), self.save_settings()])

        # Row 4: Checkboxes & Sync Button
        opts_bar = ttk.Frame(card, style="Panel.TFrame")
        opts_bar.pack(fill="x", padx=12, pady=(6, 10))

        self.var_sync_on_import = tk.BooleanVar(value=self.settings.get("sync_on_import", True))
        chk_imp = ttk.Checkbutton(opts_bar, text=self.L("chk_sync_on_import"), variable=self.var_sync_on_import)
        chk_imp.pack(side="left", padx=(0, 15))

        self.var_pin_update_mode = tk.BooleanVar(value=self.settings.get("pin_update_mode", True))
        chk_pin = ttk.Checkbutton(opts_bar, text="Edit Pinned Message Mode", variable=self.var_pin_update_mode)
        chk_pin.pack(side="left")

        self.btn_sync_now = ttk.Button(opts_bar, text=self.L("btn_sync_now"), style="Accent.TButton", command=self.trigger_discord_sync)
        self.btn_sync_now.pack(side="right")

        # Initialize Team Settings Map from Config JSON
        self.team_settings_data = self.settings.get("team_discord_settings", {})
        self.current_team_key = getattr(self, "profile_display_map", {}).get(profile_choices[0], profile_choices[0])

        # Load initial team view
        self._load_team_view(self.current_team_key)

    def build_static_console(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame")
        card.pack(fill="both", expand=True)

        self.lbl_console_hdr = ttk.Label(card, text="📋 Live Operations & Execution Log", style="Header.TLabel")
        self.lbl_console_hdr.pack(fill="x", padx=12, pady=(8, 4))

        action_bar = ttk.Frame(card, style="Panel.TFrame")
        action_bar.pack(fill="x", padx=12, pady=3)

        self.btn_run_mplus = ttk.Button(action_bar, text=self.L("btn_run_mplus"), style="Accent.TButton", command=self.trigger_live_import)
        self.btn_run_mplus.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_run_wowaudit = ttk.Button(action_bar, text=self.L("btn_run_guild"), style="Accent.TButton", command=self.trigger_wowaudit_sync)
        self.btn_run_wowaudit.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_run_discord = ttk.Button(action_bar, text=self.L("btn_run_discord"), command=self.trigger_discord_sync)
        self.btn_run_discord.pack(side="left", fill="x", expand=True, padx=(4, 0))

        console_frame = ttk.Frame(card, style="Panel.TFrame")
        console_frame.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self.txt_console = tk.Text(console_frame, bg="#090807", fg=FG_GOLD_BRIGHT, insertbackground=FG_GOLD_BRIGHT, 
                                   font=("Consolas", 9, "bold"), relief="flat", highlightbackground=BORDER_GOLD, highlightthickness=1, height=7, wrap="word")
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
            if p.get("sync_alts", True): scope.append("Alts")
            if p.get("sync_mplus", True): scope.append("M+")
            scope_str = "+".join(scope) if scope else "None"
            
            epgp_ch = p.get("epgp_channel", "epgp-standings")
            mplus_ch = p.get("mplus_channel", "mplus-leaderboard")
            key_override = " (Custom Key)" if p.get("discord_sync_key") else ""
            
            self.lst_providers.insert(tk.END, f"[{ptype}] {name} ➔ {profile} ({scope_str}) | Discord: #{epgp_ch} & #{mplus_ch}{key_override}")

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

        # Check listbox selection for editing selected link
        sel = self.lst_providers.curselection()
        existing_idx = sel[0] if sel else None

        if existing_idx is None:
            # Check if this team/profile is already linked to a source for this provider
            for idx, existing in enumerate(providers_list):
                if existing.get("rlm_profile_key") == raw_profile and existing.get("provider") == ptype:
                    existing_idx = idx
                    break

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
            "sync_alts": self.var_sync_alts.get()
        }

        if existing_idx is not None and 0 <= existing_idx < len(providers_list):
            providers_list[existing_idx] = new_entry
            self.log_message(f"Updated [{ptype.upper()}] source link for team/profile '{raw_profile}' with '{name}'")
        else:
            providers_list.append(new_entry)
            self.log_message(f"Mapped provider [{ptype.upper()}] '{name}' to profile '{raw_profile}'")

        self.update_providers_listbox()
        self.save_settings()
        self.ent_provider_key.delete(0, tk.END)
        self.ent_group_id.delete(0, tk.END)
        if hasattr(self, "btn_provider_add"):
            self.btn_provider_add.configure(text=self.L("btn_provider_add"))

    def del_provider_mapping(self):
        sel = self.lst_providers.curselection()
        if not sel: return
        idx = sel[0]
        providers_list = self.settings.get("guild_providers", [])
        if 0 <= idx < len(providers_list):
            removed = providers_list.pop(idx)
            removed_profile = removed.get("rlm_profile_key")
            removed_provider = removed.get("provider")

            if "wowaudit_sync" in self.settings and isinstance(self.settings["wowaudit_sync"], list):
                self.settings["wowaudit_sync"] = [
                    item for item in self.settings["wowaudit_sync"]
                    if not (item.get("rlm_profile_key") == removed_profile and removed_provider == "wowaudit")
                ]

            self.update_providers_listbox()
            self.save_settings()
            self.ent_provider_key.delete(0, tk.END)
            self.ent_group_id.delete(0, tk.END)
            if hasattr(self, "btn_provider_add"):
                self.btn_provider_add.configure(text=self.L("btn_provider_add"))
            self.log_message(f"Removed provider mapping: {removed.get('name')}")

    def save_settings(self):
        self.settings["region"] = self.cb_region.get().strip().lower()
        self.settings["wow_path"] = self.ent_wow_path.get().strip()
        if hasattr(self, "ent_rio_delay"):
            try:
                self.settings["rio_delay"] = float(self.ent_rio_delay.get().strip())
            except ValueError:
                self.settings["rio_delay"] = 0.35
        else:
            self.settings["rio_delay"] = float(self.settings.get("rio_delay", 0.35))

        self.settings["schedule_am"] = self.ent_sched_am.get().strip()
        self.settings["schedule_pm"] = self.ent_sched_pm.get().strip()
        self.settings["schedule_logon"] = self.var_sched_logon.get()
        self.settings["discord_sync_key"] = ""
        self.settings["sync_on_import"] = self.var_sync_on_import.get()
        self.settings["sync_on_wow_exit"] = self.var_sync_on_wow_exit.get()
        self.settings["run_on_startup"] = self.var_run_on_startup.get()
        self.settings["minimize_on_close"] = self.var_minimize_on_close.get()

        if hasattr(self, "cb_epgp_channel"):
            self.settings["epgp_channel"] = self.cb_epgp_channel.get().strip()
        if hasattr(self, "cb_epgp_schedule"):
            self.settings["epgp_schedule"] = self.cb_epgp_schedule.get().strip()
        if hasattr(self, "cb_mplus_channel"):
            self.settings["mplus_channel"] = self.cb_mplus_channel.get().strip()
        if hasattr(self, "cb_mplus_schedule"):
            self.settings["mplus_schedule"] = self.cb_mplus_schedule.get().strip()
        if hasattr(self, "var_pin_update_mode"):
            self.settings["pin_update_mode"] = self.var_pin_update_mode.get()

        # Save per-team discord settings
        self._save_current_team_view()
        self.settings["team_discord_settings"] = getattr(self, "team_settings_data", {})

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.log_message("Settings saved successfully to config JSON.")
            self.flash_save_button()
            self.show_toast_banner("Settings and Guild Team configurations saved successfully!")
        except Exception as e:
            self.log_message(f"Error saving settings: {e}")
            self.show_toast_banner(f"Failed to save settings: {e}", toast_type="error")

    def _save_current_team_view(self):
        if hasattr(self, "current_team_key") and self.current_team_key:
            if not hasattr(self, "team_settings_data") or self.team_settings_data is None:
                self.team_settings_data = self.settings.get("team_discord_settings", {})
            
            key_val = self.ent_team_key.get().strip() if hasattr(self, "ent_team_key") else ""
            entry = {
                "discord_sync_key": key_val,
                "epgp_channel": self.cb_team_epgp_ch.get().strip() if hasattr(self, "cb_team_epgp_ch") else "",
                "mplus_channel": self.cb_team_mplus_ch.get().strip() if hasattr(self, "cb_team_mplus_ch") else "",
                "epgp_schedule": self.cb_team_epgp_sched.get().strip() if hasattr(self, "cb_team_epgp_sched") else "",
                "mplus_schedule": self.cb_team_mplus_sched.get().strip() if hasattr(self, "cb_team_mplus_sched") else ""
            }
            self.team_settings_data[self.current_team_key] = entry
            short_key = self.current_team_key.split("::")[-1]
            self.team_settings_data[short_key] = entry
            self.settings["team_discord_settings"] = self.team_settings_data

    def _load_team_view(self, team_key):
        self.current_team_key = team_key
        display_name = next((disp for disp, raw in getattr(self, "profile_display_map", {}).items() if raw == team_key), team_key)
        if hasattr(self, "lbl_team_hdr"):
            self.lbl_team_hdr.configure(text=f"Discord Bot Settings: {display_name}")

        p_data = getattr(self, "team_settings_data", {}).get(team_key, {}) or {}
        key_val = p_data.get("discord_sync_key", "").strip()
        epgp_ch = p_data.get("epgp_channel", "").strip()
        epgp_sch = p_data.get("epgp_schedule", "Post-Raid (On WoW Exit)")
        mplus_ch = p_data.get("mplus_channel", "").strip()
        mplus_sch = p_data.get("mplus_schedule", "Tuesday Post-Reset (Default)")

        if hasattr(self, "ent_team_key"):
            self.ent_team_key.delete(0, tk.END)
            if key_val:
                self.ent_team_key.insert(0, key_val)

        # Dropdowns should be completely BLANK unless a Discord sync key is linked & channels loaded
        if key_val and key_val != "YOUR_SYNC_KEY_HERE":
            default_epgp_vals = [epgp_ch] if epgp_ch else []
            default_mplus_vals = [mplus_ch] if mplus_ch else []

            if hasattr(self, "cb_team_epgp_ch"):
                self.cb_team_epgp_ch.configure(values=default_epgp_vals)
                self.cb_team_epgp_ch.set(epgp_ch)

            if hasattr(self, "cb_team_mplus_ch"):
                self.cb_team_mplus_ch.configure(values=default_mplus_vals)
                self.cb_team_mplus_ch.set(mplus_ch)

            self.fetch_channels_for_active_team()
        else:
            if hasattr(self, "cb_team_epgp_ch"):
                self.cb_team_epgp_ch.configure(values=[])
                self.cb_team_epgp_ch.set("")

            if hasattr(self, "cb_team_mplus_ch"):
                self.cb_team_mplus_ch.configure(values=[])
                self.cb_team_mplus_ch.set("")

            if hasattr(self, "lbl_team_status"):
                self.lbl_team_status.configure(text="⚠️ Enter Sync Key and click 'Fetch Channels' to load Discord dropdowns.", foreground="#f39c12")

        if hasattr(self, "cb_team_epgp_sched"):
            self.cb_team_epgp_sched.set(epgp_sch)

        if hasattr(self, "cb_team_mplus_sched"):
            self.cb_team_mplus_sched.set(mplus_sch)

    def _on_team_selected(self, event=None):
        self._save_current_team_view()
        selected_disp = self.cb_active_team.get().strip()
        raw_key = getattr(self, "profile_display_map", {}).get(selected_disp, selected_disp)
        self._load_team_view(raw_key)

    def fetch_channels_for_active_team(self):
        team_key = getattr(self, "current_team_key", "")
        key = self.ent_team_key.get().strip() if hasattr(self, "ent_team_key") else ""
        sync_url = self.settings.get("discord_sync_url", "https://rlm-desktop-companion-production.up.railway.app/api/sync")
        
        if not key or key == "YOUR_SYNC_KEY_HERE":
            if hasattr(self, "lbl_team_status"):
                self.lbl_team_status.configure(text="⚠️ Please enter your Discord Sync Key first.", foreground="#e67e22")
            if hasattr(self, "cb_team_epgp_ch"):
                self.cb_team_epgp_ch.configure(values=[])
                self.cb_team_epgp_ch.set("")
            if hasattr(self, "cb_team_mplus_ch"):
                self.cb_team_mplus_ch.configure(values=[])
                self.cb_team_mplus_ch.set("")
            return

        if hasattr(self, "lbl_team_status"):
            self.lbl_team_status.configure(text="⏳ Querying Discord Bot server channels...", foreground=FG_GOLD_BRIGHT)

        base_url = sync_url.rsplit("/api/", 1)[0] if "/api/" in sync_url else sync_url
        channels_url = f"{base_url}/api/channels"
        headers = {"Authorization": key, "Content-Type": "application/json", "User-Agent": getattr(rlm_guild_providers, "DEFAULT_USER_AGENT", "RLMCompanion/1.3.7")}
        
        def task():
            try:
                r = requests.get(channels_url, headers=headers, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    channels_list = [item.get("name") for item in data.get("channels", []) if item.get("name")]
                    guild_name = data.get("guild_name", "Discord Server")
                    msg = f"🟢 Connected to '{guild_name}' ({len(channels_list)} real channels loaded!)"
                    self.root.after(0, lambda: self._on_active_team_channels_fetched(team_key, True, channels_list, msg))
                else:
                    err_msg = r.json().get("error", "Key mismatch or bot not in server.") if r.headers.get("content-type") == "application/json" else f"HTTP {r.status_code}"
                    status_text = f"⚠️ Server response: {err_msg} (Type !synckey in your Discord server)."
                    self.root.after(0, lambda: self._on_active_team_channels_fetched(team_key, False, [], status_text))
            except Exception as e:
                self.root.after(0, lambda: self._on_active_team_channels_fetched(team_key, False, [], f"⚠️ Connection notice: {e}"))
                
        threading.Thread(target=task, daemon=True).start()

    def _on_active_team_channels_fetched(self, target_team_key, success, channels_list, status_msg):
        if getattr(self, "current_team_key", "") != target_team_key:
            return

        if hasattr(self, "lbl_team_status"):
            fg = FG_GOLD_BRIGHT if success else "#f39c12"
            self.lbl_team_status.configure(text=status_msg, foreground=fg)
            
        if success and channels_list:
            if hasattr(self, "cb_team_epgp_ch"):
                self.cb_team_epgp_ch.configure(values=channels_list)
                current_e = self.cb_team_epgp_ch.get()
                if not current_e or current_e not in channels_list:
                    match_e = next((c for c in channels_list if "epgp" in c.lower() or "standings" in c.lower()), channels_list[0])
                    self.cb_team_epgp_ch.set(match_e)
                
            if hasattr(self, "cb_team_mplus_ch"):
                self.cb_team_mplus_ch.configure(values=channels_list)
                current_m = self.cb_team_mplus_ch.get()
                if not current_m or current_m not in channels_list:
                    match_m = next((c for c in channels_list if "mplus" in c.lower() or "leaderboard" in c.lower() or "keys" in c.lower()), channels_list[0])
                    self.cb_team_mplus_ch.set(match_m)
        else:
            if hasattr(self, "cb_team_epgp_ch"):
                self.cb_team_epgp_ch.configure(values=[])
                self.cb_team_epgp_ch.set("")
            if hasattr(self, "cb_team_mplus_ch"):
                self.cb_team_mplus_ch.configure(values=[])
                self.cb_team_mplus_ch.set("")

    def _on_channels_fetched(self, success, channels_list, status_msg):
        if hasattr(self, "lbl_channel_status"):
            fg = FG_GOLD_BRIGHT if success else "#e74c3c"
            self.lbl_channel_status.configure(text=status_msg, foreground=fg)
            
        if success and channels_list:
            if hasattr(self, "cb_epgp_channel"):
                self.cb_epgp_channel.configure(values=channels_list)
                current = self.cb_epgp_channel.get()
                if not current or current not in channels_list:
                    match = next((c for c in channels_list if "epgp" in c.lower() or "standings" in c.lower()), channels_list[0])
                    self.cb_epgp_channel.set(match)
                    
            if hasattr(self, "cb_mplus_channel"):
                self.cb_mplus_channel.configure(values=channels_list)
                current = self.cb_mplus_channel.get()
                if not current or current not in channels_list:
                    match = next((c for c in channels_list if "mplus" in c.lower() or "leaderboard" in c.lower() or "keys" in c.lower()), channels_list[0])
                    self.cb_mplus_channel.set(match)

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
        try:
            self._save_current_team_view()
            self.save_settings()
        except Exception:
            pass
        def task():
            if hasattr(self, "btn_run_mplus") and self.btn_run_mplus:
                self.root.after(0, lambda: self.btn_run_mplus.configure(text="⌛ Importing M+ Data...", state="disabled"))
            self.log_message("--- Starting Mythic+ Import ---")
            error_occurred = None
            try:
                import importlib
                import raidlootmatrix_mplus
                importlib.reload(raidlootmatrix_mplus)
                raidlootmatrix_mplus.main()
                self.log_message("--- Mythic+ Import Completed ---")
            except Exception as e:
                error_occurred = str(e)
                self.log_message(f"Import Error: {e}")

            if hasattr(self, "btn_run_mplus") and self.btn_run_mplus:
                self.root.after(0, lambda: self.btn_run_mplus.configure(text=self.L("btn_run_mplus"), state="normal"))

            if not error_occurred:
                should_sync = True
                if hasattr(self, "var_sync_on_import"):
                    should_sync = self.var_sync_on_import.get()
                if should_sync:
                    self.log_message("Triggering automatic Discord Sync after M+ import...")
                    self.trigger_discord_sync()

        threading.Thread(target=task, daemon=True).start()

    def trigger_wowaudit_sync(self):
        def task():
            self.log_message("--- Starting Guild Data Sync (All Sources) ---")
            try:
                import importlib
                import rlm_wowaudit_sync
                importlib.reload(rlm_wowaudit_sync)
                rlm_wowaudit_sync.main()
                self.log_message("--- Guild Data Sync Task Finished ---")
            except Exception as e:
                self.log_message(f"Sync Error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def trigger_discord_sync(self):
        try:
            self._save_current_team_view()
            self.save_settings()
        except Exception:
            pass
        def task():
            if hasattr(self, "btn_sync_now") and self.btn_sync_now:
                self.root.after(0, lambda: self.btn_sync_now.configure(text="⌛ Syncing Discord Bot...", state="disabled"))
            if hasattr(self, "btn_run_discord") and self.btn_run_discord:
                self.root.after(0, lambda: self.btn_run_discord.configure(text="⌛ Syncing...", state="disabled"))
            if hasattr(self, "lbl_discord_status") and self.lbl_discord_status:
                self.root.after(0, lambda: self.lbl_discord_status.configure(text="🟢 Uploading EPGP standings and rosters to Discord Bot...", foreground="#34d399"))
            
            self.log_message("--- Starting Discord Sync ---")
            error_occurred = None
            try:
                import importlib
                import rlm_discord_sync
                importlib.reload(rlm_discord_sync)
                if "--force" not in sys.argv:
                    sys.argv.append("--force")
                rlm_discord_sync.main()
                self.log_message("--- Discord Sync Finished ---")
            except Exception as e:
                error_occurred = str(e)
                self.log_message(f"Discord Sync Error: {e}")

            if hasattr(self, "btn_sync_now") and self.btn_sync_now:
                self.root.after(0, lambda: self.btn_sync_now.configure(text=self.L("btn_sync_now"), state="normal"))
            if hasattr(self, "btn_run_discord") and self.btn_run_discord:
                self.root.after(0, lambda: self.btn_run_discord.configure(text=self.L("btn_run_discord"), state="normal"))

            if hasattr(self, "lbl_discord_status") and self.lbl_discord_status:
                if error_occurred:
                    self.root.after(0, lambda: self.lbl_discord_status.configure(text=f"❌ Sync Error: {error_occurred}", foreground="#ef4444"))
                else:
                    self.root.after(0, lambda: self.lbl_discord_status.configure(text="✅ Discord Sync Completed Successfully!", foreground="#fbbf24"))

            if error_occurred:
                self.root.after(0, lambda err=error_occurred: self.show_toast_banner(f"Discord Sync Error: {err}", toast_type="error"))
            else:
                self.root.after(0, lambda: self.show_toast_banner("Discord Sync Completed Successfully!"))

        threading.Thread(target=task, daemon=True).start()

    def register_background_tasks(self):
        self.log_message("Registering background Windows scheduled tasks...")
        messagebox.showinfo("Automation", self.L("msg_success_saved"))

    def unregister_background_tasks(self):
        self.log_message("Removing background Windows scheduled tasks...")

    def create_tray_icon(self):
        try:
            image = None
            if hasattr(self, "icon_path") and self.icon_path and self.icon_path.exists():
                image = Image.open(str(self.icon_path))
            else:
                image = Image.new('RGB', (64, 64), color=(245, 158, 11))
                draw = ImageDraw.Draw(image)
                draw.rectangle([16, 16, 48, 48], fill=(120, 53, 15))

            menu = pystray.Menu(
                pystray.MenuItem("Open RLM Companion", lambda icon, item: self.root.after(0, self.show_window), default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("⚔️ Import M+ Data", lambda icon, item: self.root.after(0, self.trigger_live_import)),
                pystray.MenuItem("🔄 Sync Guild Data", lambda icon, item: self.root.after(0, self.trigger_wowaudit_sync)),
                pystray.MenuItem("💬 Sync Discord Bot", lambda icon, item: self.root.after(0, self.trigger_discord_sync)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit RLM Companion", lambda icon, item: self.root.after(0, self.exit_app))
            )
            self.tray_icon = pystray.Icon("RLMCompanion", image, "RaidLootMatrix Companion", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Tray icon error: {e}")

    def on_window_close(self):
        if self.settings.get("minimize_on_close", True):
            self.hide_to_tray()
        else:
            self.exit_app()

    def hide_to_tray(self):
        self.root.withdraw()
        if not hasattr(self, "tray_icon") or self.tray_icon is None:
            self.create_tray_icon()
        self.log_message("Minimized to system tray. Double-click the tray icon to reopen.")

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit_app(self):
        if hasattr(self, "tray_icon") and self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = RLMImporterApp(root)
    root.mainloop()
