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

# Import background tasks to package them into the standalone executable
try:
    import raidlootmatrix_mplus
    import rlm_discord_sync
    import rlm_wowaudit_sync
except ImportError as e:
    # Fallback/logging if running locally and missing dependencies
    print(f"Warning: Failed to import background task modules: {e}")

try:
    # Set unique AppUserModelID so Windows taskbar displays the correct custom window icon
    myappid = "raidlootmatrix.desktop.companion"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

VERSION = "1.2.0"

LOCALES = {
    "en": {
        "header_title": "RLM Importer",
        "header_subtitle": " v{VERSION} • Raider.IO Mythic+ Settings & Automation Hub",
        "card_wow_hdr": " WoW & Account Settings",
        "card_sched_hdr": " Background Task Automation",
        "card_discord_hdr": " Discord Bot Sync Settings",
        "btn_save_settings": "Save Current Settings",
        "lbl_console_hdr": " Import Action & Console Logs",
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
        "btn_register": "Register Background Tasks",
        "btn_unregister": "Remove Tasks",
        "lbl_discord_key": "Discord Sync Key:",
        "lbl_discord_url": "Discord Sync URL:",
        "chk_sync_on_import": "Run Discord Sync after M+ import",
        "btn_sync_now": "Run Discord Sync Now",
        "lbl_week_mode": "Import Week Mode:",
        "btn_run": "Run Import Now",
        "msg_success_title": "Success",
        "msg_success_saved": "Settings saved successfully!",
        "msg_restart_title": "Restart Required",
        "msg_restart_body": "Language changed. Please restart the application to apply the language settings.",
        "dialog_select_wtf": "Select your World of Warcraft directory, WTF, or Account folder",
        "lbl_language": "Language / 语言 / Idioma:",
        "week_both": "Both Weeks",
        "week_current": "Current Week",
        "week_last": "Last Week",
        "card_wowaudit_hdr": " WoW Audit Integration Settings",
        "lbl_wowaudit_key": "WoW Audit API Key:",
        "lbl_wowaudit_profile": "RLM Profile:",
        "btn_wowaudit_add": "Add Team Mapping",
        "btn_wowaudit_del": "Remove Selected Team",
        "wowaudit_err_invalid_key": "API Key is required.",
        "wowaudit_err_fetch_failed": "Failed to fetch team details. Check your key and connection.",
        "wowaudit_err_unauthorized": "Invalid or expired API key. Double check that you copied the key correctly.",
        "wowaudit_err_forbidden": "Access Forbidden. Make sure you are using a 'Team API Key' (from Team Settings > Exports), not a 'Personal API Key'.",
        "wowaudit_err_not_found": "Team not found. Please verify your WoW Audit configuration.",
        "wowaudit_err_http_generic": "WoW Audit returned an unexpected HTTP error ({code}).",
        "btn_run_mplus": "Import M+ Data",
        "btn_run_wowaudit": "Sync WoW Audit",
        "btn_run_discord": "Sync Discord Bot",
        "lbl_update_available": "Update Available: {remote_version}",
        "btn_update_now": "Update Now",
        "title_app_update": "App Update",
        "lbl_updating_status": "Updating to {tag_name}...\nPlease do not close the app.",
        "wowaudit_err_profile_required": "RLM Profile is required.",
        "wowaudit_err_already_mapped": "This profile is already mapped to a team.",
        "automation_info_title": "Automation Task Info",
        "automation_err_os": "Background task automation controls (schtasks) are only supported on Windows.\nOn macOS, you can configure plist or launchd actions.",
        "automation_err_win_only": "Controls are only supported on Windows.",
        "automation_success_title": "Tasks Updated",
        "automation_success_msg": "Scheduled Tasks updated in Task Scheduler!",
        "automation_removed_title": "Tasks Removed",
        "automation_removed_msg": "RaidLootMatrix scheduled tasks removed.",
        "update_complete_title": "Update Complete",
        "update_complete_msg": "The application has been updated to the latest version.\nPlease restart the application to apply the update.",
        "update_failed_title": "Update Failed",
        "update_failed_msg": "Could not perform automatic update:\n{err}\n\nYou can download the update manually from GitHub.",
        "chk_minimize_on_close": "Minimize to system tray on window close (instead of exiting)"
    },
    "zh": {
        "header_title": "RLM 导入器",
        "header_subtitle": " v{VERSION} • Raider.IO 史诗+ 设置与自动化中心",
        "card_wow_hdr": " 游戏与账号设置",
        "card_sched_hdr": " 后台任务自动化",
        "card_discord_hdr": " Discord 机器人同步设置",
        "btn_save_settings": "保存当前设置",
        "lbl_console_hdr": " 导入操作与控制台日志",
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
        "btn_register": "注册后台任务",
        "btn_unregister": "删除注册任务",
        "lbl_discord_key": "Discord 同步密钥:",
        "lbl_discord_url": "Discord 同步 URL:",
        "chk_sync_on_import": "导入 M+ 数据后运行 Discord 同步",
        "btn_sync_now": "立即运行 Discord 同步",
        "lbl_week_mode": "导入周模式:",
        "btn_run": "立即运行导入",
        "msg_success_title": "成功",
        "msg_success_saved": "设置已成功保存！",
        "msg_restart_title": "需要重启",
        "msg_restart_body": "语言已更改。请重新启动应用程序以应用语言设置。",
        "dialog_select_wtf": "选择您的魔兽世界游戏目录、WTF 或是账号文件夹",
        "lbl_language": "语言 / Language / Idioma:",
        "week_both": "全部双周",
        "week_current": "仅限本周",
        "week_last": "仅限上周",
        "card_wowaudit_hdr": " WoW Audit 集成设置",
        "lbl_wowaudit_key": "WoW Audit API 密钥:",
        "lbl_wowaudit_profile": "RLM 配置文件:",
        "btn_wowaudit_add": "添加团队映射",
        "btn_wowaudit_del": "删除所选团队",
        "wowaudit_err_invalid_key": "需要 API 密钥。",
        "wowaudit_err_fetch_failed": "获取团队信息失败。请检查密钥和连接。",
        "wowaudit_err_unauthorized": "无效或过期的 API 密钥。请仔细检查您的密钥是否正确。",
        "wowaudit_err_forbidden": "拒绝访问。请确保使用的是“团队 API 密钥”（在团队设置 > 导出中生成），而非“个人 API 密钥”。",
        "wowaudit_err_not_found": "未找到团队。请验证您的 WoW Audit 配置。",
        "wowaudit_err_http_generic": "WoW Audit 返回了异常的 HTTP 错误 ({code})。",
        "btn_run_mplus": "导入 M+ 数据",
        "btn_run_wowaudit": "同步 WoW Audit",
        "btn_run_discord": "同步 Discord 机器人",
        "lbl_update_available": "有可用更新: {remote_version}",
        "btn_update_now": "立即更新",
        "title_app_update": "应用程序更新",
        "lbl_updating_status": "正在更新至 {tag_name}...\n请勿关闭应用程序。",
        "wowaudit_err_profile_required": "需要 RLM 配置文件。",
        "wowaudit_err_already_mapped": "此配置文件已映射到团队。",
        "automation_info_title": "自动化任务信息",
        "automation_err_os": "后台任务自动化控制 (schtasks) 仅在 Windows 上受支持。\n在 macOS 上，您可以配置 plist 或 launchd 操作。",
        "automation_err_win_only": "控制项仅在 Windows 上受支持。",
        "automation_success_title": "任务已更新",
        "automation_success_msg": "计划任务已在任务计划程序中更新！",
        "automation_removed_title": "任务已删除",
        "automation_removed_msg": "RaidLootMatrix 计划任务已删除。",
        "update_complete_title": "更新完成",
        "update_complete_msg": "应用程序已更新至最新版本。\n请重新启动应用程序以应用更新。",
        "update_failed_title": "更新失败",
        "update_failed_msg": "无法执行自动更新:\n{err}\n\n您可以从 GitHub 手动下载更新。",
        "chk_minimize_on_close": "关闭主窗口时最小化到系统托盘 (而非退出)"
    },
    "zh_tw": {
        "header_title": "RLM 導入器",
        "header_subtitle": " v{VERSION} • Raider.IO 史詩+ 設置與自動化中心",
        "card_wow_hdr": " 遊戲與帳號設置",
        "card_sched_hdr": " 後台任務自動化",
        "card_discord_hdr": " Discord 機器人同步設置",
        "btn_save_settings": "儲存目前設置",
        "lbl_console_hdr": " 導入操作與主控台日誌",
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
        "btn_register": "註冊後台任務",
        "btn_unregister": "刪除註冊任務",
        "lbl_discord_key": "Discord 同步金鑰:",
        "lbl_discord_url": "Discord 同步 URL:",
        "chk_sync_on_import": "導入 M+ 數據後運行 Discord 同步",
        "btn_sync_now": "立即運行 Discord 同步",
        "lbl_week_mode": "導入周模式:",
        "btn_run": "立即運行導入",
        "msg_success_title": "成功",
        "msg_success_saved": "設置已成功儲存！",
        "msg_restart_title": "需要重啟",
        "msg_restart_body": "語言已變更。請重新啟動應用程式以套用語言設置。",
        "dialog_select_wtf": "選擇您的魔獸世界遊戲目錄、WTF 或是帳號資料夾",
        "lbl_language": "語言 / Language / Idioma:",
        "week_both": "全部雙周",
        "week_current": "僅限本周",
        "week_last": "僅限上周",
        "card_wowaudit_hdr": " WoW Audit 整合設置",
        "lbl_wowaudit_key": "WoW Audit API 金鑰:",
        "lbl_wowaudit_profile": "RLM 設定檔:",
        "btn_wowaudit_add": "新增團隊映射",
        "btn_wowaudit_del": "刪除所選團隊",
        "wowaudit_err_invalid_key": "需要 API 金鑰。",
        "wowaudit_err_fetch_failed": "獲取團隊信息失敗。請檢查金鑰和連接。",
        "wowaudit_err_unauthorized": "無效或過期的 API 金鑰。請仔細檢查您的金鑰是否正確。",
        "wowaudit_err_forbidden": "拒絕存取。請確保使用的是「團隊 API 金鑰」（在團隊設定 > 匯出中生成），而非「個人 API 金鑰」。",
        "wowaudit_err_not_found": "未找到團隊。請驗證您的 WoW Audit 配置。",
        "wowaudit_err_http_generic": "WoW Audit 返回了異常的 HTTP 錯誤 ({code})。",
        "btn_run_mplus": "匯入 M+ 數據",
        "btn_run_wowaudit": "同步 WoW Audit",
        "btn_run_discord": "同步 Discord 機器人",
        "lbl_update_available": "有可用更新: {remote_version}",
        "btn_update_now": "立即更新",
        "title_app_update": "應用程式更新",
        "lbl_updating_status": "正在更新至 {tag_name}...\n請勿關閉應用程式。",
        "wowaudit_err_profile_required": "需要 RLM 設定檔。",
        "wowaudit_err_already_mapped": "此設定檔已映射至團隊。",
        "automation_info_title": "自動化任務資訊",
        "automation_err_os": "後台任務自動化控制 (schtasks) 僅在 Windows 上受支援。\n在 macOS 上，您可以設定 plist 或 launchd 動作。",
        "automation_err_win_only": "控制項僅在 Windows 上受支援。",
        "automation_success_title": "任務已更新",
        "automation_success_msg": "計劃任務已在任務計劃程序中更新！",
        "automation_removed_title": "任務已刪除",
        "automation_removed_msg": "RaidLootMatrix 計劃任務已刪除。",
        "update_complete_title": "更新完成",
        "update_complete_msg": "應用程式已更新至最新版本。\n請重新啟動應用程式以套用更新。",
        "update_failed_title": "更新失敗",
        "update_failed_msg": "無法執行自動更新:\n{err}\n\n您可以從 GitHub 手動下載更新。",
        "chk_minimize_on_close": "關閉主視窗時最小化到系統托盤 (而非退出)"
    },
    "es": {
        "header_title": "Importador RLM",
        "header_subtitle": " v{VERSION} • Centro de Automatización y Ajustes Mítica+ de Raider.IO",
        "card_wow_hdr": " Configuración de WoW y Cuenta",
        "card_sched_hdr": " Automatización de Tareas en Segundo Plano",
        "card_discord_hdr": " Sincronización del Bot de Discord",
        "btn_save_settings": "Guardar Ajustes Actuales",
        "lbl_console_hdr": " Operaciones de Importación y Consola",
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
        "btn_register": "Registrar Tareas en Segundo Plano",
        "btn_unregister": "Eliminar Tareas",
        "lbl_discord_key": "Clave de Sincronización de Discord:",
        "lbl_discord_url": "URL de Sincronización de Discord:",
        "chk_sync_on_import": "Sincronizar Discord tras importar M+",
        "btn_sync_now": "Sincronizar Discord Ahora",
        "lbl_week_mode": "Modo de Semana a Importar:",
        "btn_run": "Ejecutar Importación Ahora",
        "msg_success_title": "Éxito",
        "msg_success_saved": "¡Ajustes guardados correctamente!",
        "msg_restart_title": "Reinicio Requerido",
        "msg_restart_body": "Idioma cambiado. Por favor, reinicie la aplicación para aplicar los ajustes de idioma.",
        "dialog_select_wtf": "Seleccione su carpeta de World of Warcraft, carpeta WTF o Cuenta",
        "lbl_language": "Idioma / Language / 语言:",
        "week_both": "Ambas Semanas",
        "week_current": "Semana Actual",
        "week_last": "Semana Anterior",
        "card_wowaudit_hdr": " Configuración de Integración de WoW Audit",
        "lbl_wowaudit_key": "Clave API de WoW Audit:",
        "lbl_wowaudit_profile": "Perfil RLM:",
        "btn_wowaudit_add": "Añadir Asignación de Equipo",
        "btn_wowaudit_del": "Eliminar Equipo Seleccionado",
        "wowaudit_err_invalid_key": "Se requiere la clave API.",
        "wowaudit_err_fetch_failed": "Error al obtener los detalles del equipo. Compruebe la clave y la conexión.",
        "wowaudit_err_unauthorized": "Clave API inválida o expirada. Compruebe que copió la clave correctamente.",
        "wowaudit_err_forbidden": "Acceso Prohibido. Asegúrese de estar usando una 'Clave API de Equipo' (en Ajustes de Equipo > Exportaciones), no una 'Clave API Personal'.",
        "wowaudit_err_not_found": "Equipo no encontrado. Verifique la configuración de su WoW Audit.",
        "wowaudit_err_http_generic": "WoW Audit devolvió un error HTTP inesperado ({code}).",
        "btn_run_mplus": "Importar Datos de Mítica+",
        "btn_run_wowaudit": "Sincronizar WoW Audit",
        "btn_run_discord": "Sincronizar Bot de Discord",
        "lbl_update_available": "Actualización Disponible: {remote_version}",
        "btn_update_now": "Actualizar Ahora",
        "title_app_update": "Actualización de la Aplicación",
        "lbl_updating_status": "Actualizando a {tag_name}...\nPor favor, no cierre la aplicación.",
        "wowaudit_err_profile_required": "Se requiere el perfil RLM.",
        "wowaudit_err_already_mapped": "Este perfil ya está asignado a un equipo.",
        "automation_info_title": "Información de Tareas Automáticas",
        "automation_err_os": "Los controles de automatización de tareas en segundo plano (schtasks) solo son compatibles con Windows.\nEn macOS, ya que se pueden configurar acciones plist o launchd.",
        "automation_err_win_only": "Los controles solo son compatibles con Windows.",
        "automation_success_title": "Tareas Actualizadas",
        "automation_success_msg": "¡Tareas programadas actualizadas en el Programador de tareas!",
        "automation_removed_title": "Tareas Eliminadas",
        "automation_removed_msg": "Tareas programadas de RaidLootMatrix eliminadas.",
        "update_complete_title": "Actualización Completada",
        "update_complete_msg": "La aplicación se ha actualizado a la última versión.\nPor favor, reinicie la aplicación para aplicar la actualización.",
        "update_failed_title": "Actualización Fallida",
        "update_failed_msg": "No se pudo realizar la actualización automática:\n{err}\n\nPuede descargar la actualización manualmente desde GitHub.",
        "chk_minimize_on_close": "Minimizar a la bandeja del sistema al cerrar la ventana (en lugar de salir)"
    }
}

CONSOLE_PHRASES = {
    "en": {
        "start_importer": "--- Starting Mythic+ Importer Process ---",
        "executing": "Executing: ",
        "importer_finished": "Importer finished with exit code ",
        "importer_success": "Mythic+ data updated! Log into WoW and open /rlm UI to apply changes.",
        "start_auto_sync": "--- Running Automatic Discord RLM Sync ---",
        "sync_finished": "Sync finished with exit code ",
        "process_crashed": "Process crashed: ",
        "start_sync": "--- Starting Discord RLM Sync Process ---",
        "shortcut_success": "Desktop shortcut created successfully.",
        "tasks_updated": "Scheduled Tasks updated in Task Scheduler!",
        "tasks_removed": "RaidLootMatrix scheduled tasks removed.",
        "lang_changed": "Language changed to: ",
        "settings_saved": "Settings saved successfully to config JSON.",
        "discovered_accts": "Discovered {} account(s) to process:",
        "running_rio": "Running Raider.IO api query for roster...",
        "roster_complete": "Roster fetch complete.",
        "uploading_standings": "Uploading standings data to ",
        "sync_success": "🚀 Sync Successful! EPGP standings and rosters updated.",
        "sync_failed": "❌ Sync Failed with status code: ",
        "reading_db": "Reading database file: ",
        "parsing_epgp": "Parsing EPGP and Roster data...",
        "wow_running": "World of Warcraft is currently running. Deferring import until game closes...",
        "wow_exit": "World of Warcraft exit detected. Resuming import...",
        "deferring": "Deferring import until game closes...",
        "control_panel_loaded": "RLM Importer control panel loaded.",
        "working_directory": "Working directory:",
        "sync_client_header": "RaidLootMatrix Desktop Sync Client (Method 2)",
        "successfully_parsed": "Successfully parsed {} database profiles.",
        "profile_characters": " - Profile '{}' ({} characters)",
        "wow_running_warn": "[WARNING] World of Warcraft is running.",
        "corrupt_warn_1": "          Writing M+ data while WoW is open can corrupt SavedVariables.",
        "corrupt_warn_2": "          Close WoW first, or do /reload after this script finishes.",
        "no_active_players": "No active players found in any rosters. Exiting.",
        "fetching_rio_data": "Fetching Raider.IO data for {} unique players",
        "requesting_runs": "(requesting 20 recent runs to cover {})",
        "runs_found": "{} total runs found",
        "account_hdr": "ACCOUNT: {}",
        "processing_week": "-- Processing week {} [{}] -------",
        "players_runs_pool": "  {} / {} players with runs | EP pool preview: {}",
        "dry_run_no_file": "[DRY RUN] No file written.",
        "wrote_file": "Wrote: {}",
        "ep_calculated": "EP will be calculated in-game from Settings -> Mythic+.",
        "log_in_reload": "Log in (or /reload) with an officer and open the Mythic+ tab.",
        "parse_failed_warn": "[WARNING] Failed to parse SavedVariables at {}",
        "wowaudit_contacting": "Contacting WoW Audit to fetch team details...",
        "wowaudit_sync_finished": "WoW Audit Sync finished with exit code {}",
        "wowaudit_start_sync": "--- Starting WoW Audit Sync ---",
        "tray_minimized_info": "Minimized to system tray. Double-click the tray icon to reopen.",
        "task_already_active": "[INFO] An import/sync task is already active. Skipping request.",
        "tasks_register_start": "--- Registering Scheduled Tasks ---",
        "tasks_remove_start": "--- Removing Scheduled Tasks ---",
        "task_create_success": "SUCCESS: Created task: {}",
        "task_delete_success": "SUCCESS: Deleted task: {}",
        "task_create_failed": "FAILED: Task: {}\nError: {}",
        "task_not_found": "INFO: Task {} was not found or already deleted.",
        "startup_shortcut_success": "Windows startup shortcut registered successfully.",
        "startup_shortcut_removed": "Windows startup shortcut removed.",
        "err_desktop_shortcut": "Could not create desktop shortcut: {}",
        "err_create_startup": "Error creating startup shortcut: {}",
        "err_remove_startup": "Error removing startup shortcut: {}",
        "err_save_settings": "Error saving settings: {}",
        "err_execution": "Execution Error: {}",
        "err_silent_runner": "Failed to generate silent runner: {}",
        "err_watcher_vbs": "Failed to generate watcher VBS: {}",
        "err_tray_start": "[ERROR] Failed to start system tray icon: {}",
        "discord_sync_finished": "Discord sync finished with exit code {}"
    },
    "zh": {
        "start_importer": "--- 启动史诗+导入程序 ---",
        "executing": "正在执行: ",
        "importer_finished": "导入器完成，退出代码为 ",
        "importer_success": "史诗+数据已更新！登录 WoW 并打开 /rlm UI 以应用更改。",
        "start_auto_sync": "--- 正在运行 Discord 自动同步 ---",
        "sync_finished": "同步完成，退出代码为 ",
        "process_crashed": "程序崩溃: ",
        "start_sync": "--- 启动 Discord 同步程序 ---",
        "shortcut_success": "桌面快捷方式创建成功。",
        "tasks_updated": "计划任务已在任务计划程序中更新！",
        "tasks_removed": "RaidLootMatrix 计划任务已删除。",
        "lang_changed": "语言更改为: ",
        "settings_saved": "设置成功保存到配置 JSON。",
        "discovered_accts": "发现 {} 个要处理的账号:",
        "running_rio": "正在为名册运行 Raider.IO API 查询...",
        "roster_complete": "名册获取完成。",
        "uploading_standings": "正在上传积分榜数据至 ",
        "sync_success": "🚀 同步成功！EPGP 积分榜与名册已更新。",
        "sync_failed": "❌ 同步失败，状态代码: ",
        "reading_db": "正在读取数据库文件: ",
        "parsing_epgp": "正在解析 EPGP 与名册数据...",
        "wow_running": "魔兽世界目前正在运行。推迟导入直到游戏关闭...",
        "wow_exit": "检测到魔兽世界退出。恢复导入...",
        "deferring": "推迟导入直到游戏关闭...",
        "control_panel_loaded": "RLM 导入器控制面板已加载。",
        "working_directory": "工作目录:",
        "sync_client_header": "RaidLootMatrix 桌面同步客户端 (方法 2)",
        "successfully_parsed": "成功解析了 {} 个数据库配置表。",
        "profile_characters": " - 配置表 '{}' ({} 个角色)",
        "wow_running_warn": "[警告] 魔兽世界正在运行。",
        "corrupt_warn_1": "          当 WoW 打开时写入 M+ 数据可能会损坏 SavedVariables。",
        "corrupt_warn_2": "          请先关闭 WoW，或者在此脚本完成后执行 /reload。",
        "no_active_players": "在任何名册中均未发现活跃玩家。退出中。",
        "fetching_rio_data": "正在为 {} 位唯一玩家获取 Raider.IO 数据",
        "requesting_runs": "(请求最近 20 次大米运行以覆盖 {})",
        "runs_found": "总共找到 {} 次运行记录",
        "account_hdr": "账号: {}",
        "processing_week": "-- 正在处理周 {} [{}] -------",
        "players_runs_pool": "  {} / {} 位有运行记录的玩家 | EP 预览点数: {}",
        "dry_run_no_file": "[模拟运行] 未写入任何文件。",
        "wrote_file": "写入文件: {}",
        "ep_calculated": "EP 将在游戏内的 设置 -> 史诗+ 中进行计算。",
        "log_in_reload": "用官员角色登录游戏（或执行 /reload），并打开史诗+选项卡。",
        "parse_failed_warn": "[警告] 无法解析位于 {} 的 SavedVariables",
        "wowaudit_contacting": "正在联系 WoW Audit 获取团队详情...",
        "wowaudit_sync_finished": "WoW Audit 同步完成，退出代码为 {}",
        "wowaudit_start_sync": "--- 开始同步 WoW Audit ---",
        "tray_minimized_info": "已最小化到系统托盘。双击托盘图标重新打开。",
        "task_already_active": "[信息] 导入/同步任务已在运行中。跳过当前请求。",
        "tasks_register_start": "--- 正在注册计划任务 ---",
        "tasks_remove_start": "--- 正在删除计划任务 ---",
        "task_create_success": "成功: 已创建任务: {}",
        "task_delete_success": "成功: 已删除任务: {}",
        "task_create_failed": "失败: 任务: {}\n错误: {}",
        "task_not_found": "提示: 计划任务 {} 未找到或已被删除。",
        "startup_shortcut_success": "Windows 开机自启快捷方式注册成功。",
        "startup_shortcut_removed": "Windows 开机自启快捷方式已删除。",
        "err_desktop_shortcut": "无法创建桌面快捷方式: {}",
        "err_create_startup": "创建自启快捷方式时出错: {}",
        "err_remove_startup": "删除自启快捷方式时出错: {}",
        "err_save_settings": "保存设置时出错: {}",
        "err_execution": "执行错误: {}",
        "err_silent_runner": "生成静默运行器失败: {}",
        "err_watcher_vbs": "生成监视器 VBS 失败: {}",
        "err_tray_start": "[错误] 启动系统托盘图标失败: {}",
        "discord_sync_finished": "Discord 同步完成，退出代码为 {}"
    },
    "zh_tw": {
        "start_importer": "--- 啟動史詩+導入程序 ---",
        "executing": "正在執行: ",
        "importer_finished": "導入器完成，退出代碼為 ",
        "importer_success": "史詩+數據已更新！登入 WoW 並打開 /rlm UI 以套用變更。",
        "start_auto_sync": "--- 正在運行 Discord 自動同步 ---",
        "sync_finished": "同步完成，退出代碼為 ",
        "process_crashed": "程序崩潰: ",
        "start_sync": "--- 啟動 Discord 同步程序 ---",
        "shortcut_success": "桌面快捷方式建立成功。",
        "tasks_updated": "計劃任務已在任務計劃程序中更新！",
        "tasks_removed": "RaidLootMatrix 計劃任務已刪除。",
        "lang_changed": "語言變更為: ",
        "settings_saved": "設置成功儲存到配置 JSON。",
        "discovered_accts": "發現 {} 個要處理的帳號:",
        "running_rio": "正在為名冊運行 Raider.IO API 查詢...",
        "roster_complete": "名冊獲取完成。",
        "uploading_standings": "正在上傳積分榜數據至 ",
        "sync_success": "🚀 同步成功！EPGP 積分榜與名冊已更新。",
        "sync_failed": "❌ 同步失敗，狀態代碼: ",
        "reading_db": "正在讀取資料庫檔案: ",
        "parsing_epgp": "正在解析 EPGP 與名冊數據...",
        "wow_running": "魔獸世界目前正在運行。推遲導入直到遊戲關閉...",
        "wow_exit": "檢測到魔獸世界退出。恢復導入...",
        "deferring": "推遲導入直到遊戲關閉...",
        "control_panel_loaded": "RLM 導入器控制面板已載入。",
        "working_directory": "工作目錄:",
        "sync_client_header": "RaidLootMatrix 桌面同步用戶端 (方法 2)",
        "successfully_parsed": "成功解析了 {} 個資料庫配置表。",
        "profile_characters": " - 配置表 '{}' ({} 個角色)",
        "wow_running_warn": "[警告] 魔獸世界正在運行。",
        "corrupt_warn_1": "          當 WoW 打開時寫入 M+ 數據可能會損壞 SavedVariables。",
        "corrupt_warn_2": "          請先關閉 WoW，或者在此腳本完成後執行 /reload。",
        "no_active_players": "在 any 名冊中均未發現活躍玩家。退出中。",
        "fetching_rio_data": "正在為 {} 位唯一玩家獲取 Raider.IO 數據",
        "requesting_runs": "(請求最近 20 次大米運行以覆蓋 {})",
        "runs_found": "總共找到 {} 次運行記錄",
        "account_hdr": "帳號: {}",
        "processing_week": "-- 正在處理周 {} [{}] -------",
        "players_runs_pool": "  {} / {} 位有運行記錄的玩家 | EP 預覽點數: {}",
        "dry_run_no_file": "[模擬運行] 未寫入 any 檔案。",
        "wrote_file": "寫入檔案: {}",
        "ep_calculated": "EP 將在游戏內的 設置 -> 史詩+ 中進行計算。",
        "log_in_reload": "用官員角色登入遊戲（或執行 /reload），並打開史詩+索引標籤。",
        "parse_failed_warn": "[警告] 無法解析位於 {} 的 SavedVariables",
        "wowaudit_contacting": "正在聯繫 WoW Audit 獲取團隊詳情...",
        "wowaudit_sync_finished": "WoW Audit 同步完成，退出代碼為 {}",
        "wowaudit_start_sync": "--- 開始同步 WoW Audit ---",
        "tray_minimized_info": "已最小化到系統托盤。雙擊托盤圖標重新打開。",
        "task_already_active": "[資訊] 匯入/同步任務已在執行中。跳過當前請求。",
        "tasks_register_start": "--- 正在註冊計劃任務 ---",
        "tasks_remove_start": "--- 正在刪除計劃任務 ---",
        "task_create_success": "成功: 已建立任務: {}",
        "task_delete_success": "成功: 已刪除任務: {}",
        "task_create_failed": "失敗: 任務: {}\n錯誤: {}",
        "task_not_found": "提示: 計劃任務 {} 未找到或已被刪除。",
        "startup_shortcut_success": "Windows 開機自啟捷徑註冊成功。",
        "startup_shortcut_removed": "Windows 開機自啟捷徑已刪除。",
        "err_desktop_shortcut": "無法建立桌面捷徑: {}",
        "err_create_startup": "建立自啟捷徑時出錯: {}",
        "err_remove_startup": "刪除自啟捷徑時出錯: {}",
        "err_save_settings": "儲存設置時出錯: {}",
        "err_execution": "執行錯誤: {}",
        "err_silent_runner": "生成靜默運行器失敗: {}",
        "err_watcher_vbs": "生成監視器 VBS 失敗: {}",
        "err_tray_start": "[錯誤] 啟動系統托盤圖標失敗: {}",
        "discord_sync_finished": "Discord 同步完成，退出代碼為 {}"
    },
    "es": {
        "start_importer": "--- Iniciando el Proceso de Importador Mítica+ ---",
        "executing": "Ejecutando: ",
        "importer_finished": "Importador finalizado con código de salida ",
        "importer_success": "¡Datos de Mítica+ actualizados! Inicia sesión en WoW y abre /rlm UI para aplicar cambios.",
        "start_auto_sync": "--- Ejecutando Sincronización Automática de Discord ---",
        "sync_finished": "Sincronización finalizada con código de salida ",
        "process_crashed": "Proceso colapsado: ",
        "start_sync": "--- Iniciando Proceso de Sincronización de Discord ---",
        "shortcut_success": "Acceso directo en el escritorio creado con éxito.",
        "tasks_updated": "¡Tareas programadas actualizadas en el Programador de tareas!",
        "tasks_removed": "Tareas programadas de RaidLootMatrix eliminadas.",
        "lang_changed": "Idioma cambiado a: ",
        "settings_saved": "Ajustes guardados correctamente en el JSON de configuración.",
        "discovered_accts": "Se descubrieron {} cuenta(s) para procesar:",
        "running_rio": "Ejecutando consulta de API de Raider.IO para el roster...",
        "roster_complete": "Búsqueda de roster completada.",
        "uploading_standings": "Subiendo datos de posiciones a ",
        "sync_success": "🚀 ¡Sincronización Exitosa! Posiciones de EPGP y rosters actualizados.",
        "sync_failed": "❌ Sincronización Fallida con código de estado: ",
        "reading_db": "Leyendo archivo de base de datos: ",
        "parsing_epgp": "Analizando datos de EPGP y Roster...",
        "wow_running": "World of Warcraft se está ejecutando actualmente. Posponiendo importación...",
        "wow_exit": "Salida de World of Warcraft detectada. Reanudando importación...",
        "deferring": "Posponiendo importación hasta que el juego se cierre...",
        "control_panel_loaded": "Panel de control del importador RLM cargado.",
        "working_directory": "Directorio de trabajo:",
        "sync_client_header": "Cliente de Sincronización de Escritorio RaidLootMatrix (Método 2)",
        "successfully_parsed": "Se analizaron con éxito {} perfiles de base de datos.",
        "profile_characters": " - Perfil '{}' ({} personajes)",
        "wow_running_warn": "[ADVERTENCIA] World of Warcraft se está ejecutando.",
        "corrupt_warn_1": "          Escribir datos de M+ mientras WoW está abierto puede corromper SavedVariables.",
        "corrupt_warn_2": "          Cierre WoW primero, o haga /reload después de que termine este script.",
        "no_active_players": "No se encontraron jugadores activos en ningún roster. Saliendo.",
        "fetching_rio_data": "Obteniendo datos de Raider.IO para {} jugadores únicos",
        "requesting_runs": "(solicitando 20 carreras recientes para cubrir {})",
        "runs_found": "Se encontraron {} carreras en total",
        "account_hdr": "CUENTA: {}",
        "processing_week": "-- Procesando semana {} [{}] -------",
        "players_runs_pool": "  {} / {} jugadores con carreras | Vista previa de EP: {}",
        "dry_run_no_file": "[DRY RUN] No se escribió ningún archivo.",
        "wrote_file": "Escrito: {}",
        "ep_calculated": "El EP se calculará dentro del juego desde Ajustes -> Mítica+.",
        "log_in_reload": "Inicie sesión (o haga /reload) con un oficial y abra la pestaña de Mítica+.",
        "parse_failed_warn": "[ADVERTENCIA] Error al analizar SavedVariables en {}",
        "wowaudit_contacting": "Contactando con WoW Audit para obtener detalles del equipo...",
        "wowaudit_sync_finished": "Sincronización de WoW Audit finalizada con código de salida {}",
        "wowaudit_start_sync": "--- Iniciando Sincronización de WoW Audit ---",
        "tray_minimized_info": "Minimizado en la bandeja del sistema. Doble clic para volver a abrir.",
        "task_already_active": "[INFO] Ya hay una tarea de importación/sincronización activa. Omitiendo solicitud.",
        "tasks_register_start": "--- Registrando Tareas Programadas ---",
        "tasks_remove_start": "--- Eliminando Tareas Programadas ---",
        "task_create_success": "ÉXITO: Tarea creada: {}",
        "task_delete_success": "ÉXITO: Tarea eliminada: {}",
        "task_create_failed": "ERROR: Tarea: {}\nError: {}",
        "task_not_found": "INFO: La tarea {} no fue encontrada o ya fue eliminada.",
        "startup_shortcut_success": "Acceso directo de inicio de Windows registrado con éxito.",
        "startup_shortcut_removed": "Acceso directo de inicio de Windows de RLM Companion al iniciar Windows eliminado.",
        "err_desktop_shortcut": "No se pudo crear el acceso directo del escritorio: {}",
        "err_create_startup": "Error al crear el acceso directo de inicio: {}",
        "err_remove_startup": "Error al eliminar el acceso directo de inicio: {}",
        "err_save_settings": "Error al guardar los ajustes: {}",
        "err_execution": "Error de ejecución: {}",
        "err_silent_runner": "Error al generar el ejecutor silencioso: {}",
        "err_watcher_vbs": "Error al generar el VBS del watcher: {}",
        "err_tray_start": "[ERROR] Error al iniciar el icono de la bandeja del sistema: {}",
        "discord_sync_finished": "Sincronización de Discord finalizada con código de salida {}"
    }
}

def translate_line(line, old_lang, new_lang):
    if old_lang == new_lang:
        return line
        
    old_phrases = CONSOLE_PHRASES.get(old_lang, CONSOLE_PHRASES["en"])
    new_phrases = CONSOLE_PHRASES.get(new_lang, CONSOLE_PHRASES["en"])
    
    import re
    
    stripped_line = line.strip()
    
    for key, old_text in old_phrases.items():
        new_text = new_phrases[key]
        old_text_stripped = old_text.strip()
        new_text_stripped = new_text.strip()
        
        # Case A: Templated strings with {}
        if "{}" in old_text_stripped:
            pattern_str = "^" + re.escape(old_text_stripped).replace(r"\{\}", r"(.*?)") + "$"
            try:
                match = re.match(pattern_str, stripped_line)
                if match:
                    groups = match.groups()
                    result = new_text_stripped
                    for g in groups:
                        # Translate inner keywords if matched (e.g. both weeks / this week)
                        if g == "both weeks":
                            if new_lang == "zh": g = "双周"
                            elif new_lang == "zh_tw": g = "全部雙周"
                            elif new_lang == "es": g = "ambas semanas"
                        elif g == "this week":
                            if new_lang == "zh": g = "本周"
                            elif new_lang == "zh_tw": g = "本周"
                            elif new_lang == "es": g = "esta semana"
                        result = result.replace("{}", g, 1)
                    
                    # Restore original leading/trailing whitespace
                    leading = line[:len(line) - len(line.lstrip())]
                    trailing = line[len(line.rstrip()):]
                    return leading + result + trailing
            except Exception:
                pass
                
        # Case B: Prefix match
        elif old_text_stripped.endswith(" ") or old_text_stripped.endswith(":") or old_text_stripped.endswith("...") or old_text_stripped.endswith("/"):
            if stripped_line.startswith(old_text_stripped):
                suffix = stripped_line[len(old_text_stripped):]
                result = new_text_stripped + suffix
                leading = line[:len(line) - len(line.lstrip())]
                trailing = line[len(line.rstrip()):]
                return leading + result + trailing
                
        # Case C: Exact match
        elif stripped_line == old_text_stripped:
            leading = line[:len(line) - len(line.lstrip())]
            trailing = line[len(line.rstrip()):]
            return leading + new_text_stripped + trailing
            
        # Case D: Substring match
        elif old_text_stripped in stripped_line:
            result = stripped_line.replace(old_text_stripped, new_text_stripped)
            leading = line[:len(line) - len(line.lstrip())]
            trailing = line[len(line.rstrip()):]
            return leading + result + trailing
            
    return line

import socket
SINGLE_INSTANCE_PORT = 55919

def check_single_instance(app_instance_callback=None):
    try:
        # Try to bind to localhost port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.listen(1)
        
        # We got the lock! Start a background thread to listen for wake signals
        def listen_for_wake():
            while True:
                try:
                    conn, addr = s.connect_accept_wait_loop() if False else s.accept()
                    conn.close()
                    # Wake up callback
                    if app_instance_callback:
                        app_instance_callback()
                except Exception:
                    break
                    
        t = threading.Thread(target=listen_for_wake, daemon=True)
        t.start()
        return s # Keep socket open for the lifetime of the process
    except socket.error:
        # Binding failed -> another instance is already running!
        try:
            # Connect to the existing instance to wake it up
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
            s2.close()
        except Exception:
            pass
        # Exit immediately
        sys.exit(0)

# ─────────────────────────────────────────────────────────────────────────────
# UI Styling Constants
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK = "#1e1e1e"
BG_PANEL = "#252526"
BG_ENTRY = "#2d2d30"
FG_TEXT = "#d4d4d4"
FG_ACCENT = "#ffcc00"
FG_HEADER = "#ff9900"
BORDER_COLOR = "#3f3f46"

def auto_detect_language():
    try:
        import locale
        sys_lang = locale.getlocale()[0] or locale.getdefaultlocale()[0]
        if sys_lang:
            sys_lang = sys_lang.lower()
            if sys_lang.startswith("zh") or "chinese" in sys_lang:
                if any(x in sys_lang for x in ["tw", "hk", "mo", "taiwan", "hong kong", "macau", "traditional"]):
                    return "zh_tw"
                return "zh"
            elif sys_lang.startswith("es") or "spanish" in sys_lang:
                return "es"
    except Exception:
        pass
    
    try:
        import ctypes
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        primary_lang = lang_id & 0x3ff
        sub_lang = (lang_id >> 10) & 0x3f
        if primary_lang == 0x04:
            if sub_lang in [0x02, 0x03, 0x05]: # TW, HK, MO
                return "zh_tw"
            return "zh"
        elif primary_lang == 0x0a:
            return "es"
    except Exception:
        pass
        
    return "en"

# Resolve pythonw path and subprocess flags for silent background execution
sub_kwargs = {}
if sys.platform == "win32":
    sub_kwargs["creationflags"] = 0x08000000

def get_pythonw_path():
    python_dir = os.path.dirname(sys.executable)
    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw_exe):
        return pythonw_exe
    return "pythonw"

class RLMImporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RLM Importer — Desktop Control Panel")
        self.root.geometry("1624x600")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(1400, 560)

        # Configure Combobox dropdown listbox popup styling
        self.root.option_add("*TCombobox*Listbox.background", BG_ENTRY)
        self.root.option_add("*TCombobox*Listbox.foreground", FG_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#3e3e42")
        self.root.option_add("*TCombobox*Listbox.selectForeground", FG_ACCENT)
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        # Config paths
        if getattr(sys, 'frozen', False):
            self.addon_dir = pathlib.Path(sys.executable).parent
        else:
            self.addon_dir = pathlib.Path(__file__).parent
        self.config_path = self.addon_dir / "rlm_importer_config.json"
        
        # Load existing settings
        self.settings = self.load_settings()

        # Build UI Elements
        self.setup_styles()
        self.create_widgets()
        
        # Log init
        self.log_message("RLM Importer control panel loaded.")
        self.log_message(f"Working directory: {self.addon_dir}")

        # Generate custom logo icon if missing
        self.icon_path_png = self.addon_dir / "rlm_icon.png"
        self.icon_path_ico = self.addon_dir / "rlm_icon.ico"
        self.logo_source = self.addon_dir / "rlm_logo_source.png"
        
        if not self.icon_path_ico.exists() or not self.icon_path_png.exists():
            try:
                if self.logo_source.exists():
                    img = Image.open(self.logo_source)
                    img = img.convert("RGBA")
                    datas = img.getdata()
                    new_data = []
                    for item in datas:
                        if item[0] < 20 and item[1] < 20 and item[2] < 20:
                            new_data.append((0, 0, 0, 0))
                        else:
                            new_data.append(item)
                    img.putdata(new_data)
                    
                    # Resize to 128x128 for high-quality window/tray icon
                    img_png = img.resize((128, 128), Image.Resampling.LANCZOS)
                else:
                    img = self.create_tray_image()
                    img_png = img
                
                img_png.save(self.icon_path_png)
                img.save(self.icon_path_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            except Exception as e:
                print(f"Failed to generate icons: {e}")

        # Set window icon bitmap (Windows native)
        if self.icon_path_ico.exists():
            try:
                self.root.iconbitmap(str(self.icon_path_ico))
            except Exception as e:
                # Fallback to PNG iconphoto if iconbitmap fails
                try:
                    icon_img = tk.PhotoImage(file=str(self.icon_path_png))
                    self.root.iconphoto(True, icon_img)
                except Exception:
                    pass

        # Create desktop shortcut if missing
        desktop_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
        # Clean up old shortcut if it exists to avoid caching and clutter
        old_shortcut = os.path.join(desktop_dir, "RLM Companion.lnk")
        if os.path.exists(old_shortcut):
            try:
                os.remove(old_shortcut)
            except Exception:
                pass
                
        desktop_shortcut = os.path.join(desktop_dir, "RLM Desktop Companion.lnk")
        if not os.path.exists(desktop_shortcut):
            self.create_desktop_shortcut()

        # Intercept closing action to hide to system tray
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Check for updates in the background
        self.check_for_updates()

        # Start background system tray loop
        try:
            self.start_tray_icon()
        except Exception as e:
            self.log_message(f"[ERROR] Failed to start system tray icon: {e}")

    def L(self, key):
        lang = self.settings.get("language", "en")
        if lang not in LOCALES:
            lang = "en"
        return LOCALES[lang].get(key, LOCALES["en"].get(key, key))

    def load_settings(self):
        defaults = {
            "language": auto_detect_language(),
            "region": "",
            "wow_path": "",
            "rio_delay": 0.35,
            "schedule_am": "06:00",
            "schedule_pm": "18:00",
            "schedule_logon": True,
            "discord_sync_key": "",
            "discord_sync_url": "https://rlm-desktop-companion-production.up.railway.app/api/sync",
            "sync_on_import": True,
            "sync_on_wow_exit": True,
            "run_on_startup": True,
            "minimize_on_close": True
        }
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                print(f"Failed to read config file: {e}")
        return defaults

    def on_language_changed(self, event=None):
        try:
            lang_val = self.cb_language.get()
            if lang_val == "简体中文":
                new_lang = "zh"
            elif lang_val == "繁體中文":
                new_lang = "zh_tw"
            elif lang_val == "Español":
                new_lang = "es"
            else:
                new_lang = "en"
            
            old_lang = self.settings.get("language", "en")
            if old_lang != new_lang:
                self.settings["language"] = new_lang
                # Save language preference immediately
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=2)
                self.log_message(f"Language changed to: {new_lang}")
                
                # Dynamically refresh all UI translations
                self.refresh_ui_translations()
                self.translate_console_content(old_lang, new_lang)
        except Exception as e:
            import traceback
            err_msg = f"Error changing language: {e}\n{traceback.format_exc()}"
            self.log_message(err_msg)
            messagebox.showerror("Language Error", err_msg)

    def translate_console_content(self, old_lang, new_lang):
        if old_lang == new_lang:
            return
        
        content = self.txt_console.get("1.0", tk.END)
        lines = content.splitlines()
        translated_lines = []
        
        old_phrases = CONSOLE_PHRASES.get(old_lang, CONSOLE_PHRASES["en"])
        new_phrases = CONSOLE_PHRASES.get(new_lang, CONSOLE_PHRASES["en"])
        
        for line in lines:
            translated = line
            for key, old_text in old_phrases.items():
                new_text = new_phrases[key]
                
                if key == "discovered_accts":
                    import re
                    pattern = re.escape(old_text).replace(r"\{\}", r"(\d+)")
                    match = re.match(pattern, line)
                    if match:
                        num = match.group(1)
                        translated = new_text.replace("{}", num)
                        break
                elif line.strip() == old_text.strip():
                    translated = new_text
                    break
                elif line.startswith(old_text):
                    suffix = line[len(old_text):]
                    translated = new_text + suffix
                    break
                elif old_text in line:
                    translated = line.replace(old_text, new_text)
                    break
            
            translated_lines.append(translated)
        
        self.txt_console.delete("1.0", tk.END)
        self.txt_console.insert("1.0", "\n".join(translated_lines) + "\n")
        self.txt_console.see(tk.END)

    def refresh_ui_translations(self):
        # 1. Update Title and Headers
        self.lbl_title.configure(text=self.L("header_title"))
        self.lbl_subtitle.configure(text=self.L("header_subtitle").format(VERSION=VERSION))
        self.lbl_card_wow_hdr.configure(text=self.L("card_wow_hdr"))
        self.lbl_card_sched_hdr.configure(text=self.L("card_sched_hdr"))
        self.lbl_card_discord_hdr.configure(text=self.L("card_discord_hdr"))
        if hasattr(self, "lbl_card_wowaudit_hdr"):
            self.lbl_card_wowaudit_hdr.configure(text=self.L("card_wowaudit_hdr"))
            self.lbl_wowaudit_key.configure(text=self.L("lbl_wowaudit_key"))
            self.lbl_wowaudit_profile.configure(text=self.L("lbl_wowaudit_profile"))
            self.btn_wowaudit_add.configure(text=self.L("btn_wowaudit_add"))
            self.btn_wowaudit_del.configure(text=self.L("btn_wowaudit_del"))
        self.lbl_console_hdr.configure(text=self.L("lbl_console_hdr"))
        self.btn_save.configure(text=self.L("btn_save_settings"))

        # 2. Card 1 (WoW Config)
        self.lbl_language.configure(text=self.L("lbl_language"))
        self.lbl_region.configure(text=self.L("lbl_region"))
        self.lbl_rio_delay.configure(text=self.L("lbl_rio_delay"))
        self.lbl_wow_path.configure(text=self.L("lbl_wow_path"))
        self.btn_browse.configure(text=self.L("btn_browse"))

        # 3. Card 2 (Scheduler)
        self.lbl_sched_am.configure(text=self.L("lbl_sched_am"))
        self.lbl_sched_pm.configure(text=self.L("lbl_sched_pm"))
        self.chk_logon.configure(text=self.L("chk_logon"))
        self.chk_startup.configure(text=self.L("chk_startup"))
        self.chk_wow_exit.configure(text=self.L("chk_wow_exit"))
        self.chk_minimize_on_close.configure(text=self.L("chk_minimize_on_close"))
        self.btn_register.configure(text=self.L("btn_register"))
        self.btn_unregister.configure(text=self.L("btn_unregister"))

        # 4. Card 3 (Discord Sync)
        self.lbl_discord_key.configure(text=self.L("lbl_discord_key"))
        self.chk_sync_on_import.configure(text=self.L("chk_sync_on_import"))
        self.btn_sync_now.configure(text=self.L("btn_sync_now"))

        # 5. Card 4 (Console control bar)
        self.lbl_week_mode.configure(text=self.L("lbl_week_mode"))
        self.btn_run_mplus.configure(text=self.L("btn_run_mplus"))
        self.btn_run_wowaudit.configure(text=self.L("btn_run_wowaudit"))
        self.btn_run_discord.configure(text=self.L("btn_run_discord"))

        # Update week mode Combobox options and preserve selection
        current_code = self.get_week_code()
        self.cb_week_mode['values'] = [self.L("week_both"), self.L("week_current"), self.L("week_last")]
        if current_code == "current":
            self.cb_week_mode.set(self.L("week_current"))
        elif current_code == "last":
            self.cb_week_mode.set(self.L("week_last"))
        else:
            self.cb_week_mode.set(self.L("week_both"))

    def save_settings(self):
        # Gather inputs
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
        # self.settings["discord_sync_url"] is preserved from loaded settings, not read from widget
        self.settings["sync_on_import"] = self.var_sync_on_import.get()
        self.settings["sync_on_wow_exit"] = self.var_sync_on_wow_exit.get()
        self.settings["run_on_startup"] = self.var_run_on_startup.get()
        self.settings["minimize_on_close"] = self.var_minimize_on_close.get()
        self.update_startup_shortcut()

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.log_message("Settings saved successfully to config JSON.")
            messagebox.showinfo(self.L("msg_success_title"), self.L("msg_success_saved"))
        except Exception as e:
            self.log_message(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure standard widgets colors
        self.style.configure(".", background=BG_DARK, foreground=FG_TEXT)
        self.style.configure("TFrame", background=BG_DARK)
        self.style.configure("Panel.TFrame", background=BG_PANEL, borderwidth=1, relief="solid")
        
        self.style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background=BG_PANEL, foreground=FG_HEADER, font=("Segoe UI", 11, "bold"))
        self.style.configure("Title.TLabel", background=BG_DARK, foreground=FG_ACCENT, font=("Segoe UI", 15, "bold"))

        self.style.configure("TButton", background=BG_PANEL, foreground=FG_TEXT, borderwidth=1, focuscolor=FG_ACCENT, font=("Segoe UI", 9))
        self.style.map("TButton", 
                       background=[("active", "#3e3e42"), ("pressed", "#505054")],
                       foreground=[("active", FG_ACCENT)])

        self.style.configure("Accent.TButton", background=BG_PANEL, foreground=FG_ACCENT, borderwidth=1, font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", 
                       background=[("active", "#3e3e42")],
                       foreground=[("active", FG_ACCENT)])

        self.style.configure("TCheckbutton", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.map("TCheckbutton", background=[("active", BG_PANEL)], foreground=[("active", FG_ACCENT)])

        # TCombobox Styling for Dark Mode
        self.style.configure("TCombobox", 
                             fieldbackground=BG_ENTRY, 
                             background=BG_PANEL, 
                             foreground=FG_TEXT,
                             selectbackground="#3e3e42",
                             selectforeground=FG_ACCENT,
                             bordercolor=BORDER_COLOR,
                             lightcolor=BORDER_COLOR,
                             darkcolor=BORDER_COLOR,
                             arrowcolor=FG_TEXT)
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", BG_ENTRY), ("focus", BG_ENTRY)],
                       foreground=[("readonly", FG_TEXT), ("focus", FG_TEXT)],
                       selectbackground=[("readonly", "#3e3e42")],
                       selectforeground=[("readonly", FG_ACCENT)])

    def create_widgets(self):
        # Header banner
        self.header_frame = ttk.Frame(self.root)
        self.header_frame.pack(fill="x", padx=15, pady=10)
        
        self.lbl_title = ttk.Label(self.header_frame, text=self.L("header_title"), style="Title.TLabel")
        self.lbl_title.pack(side="left")
        self.lbl_subtitle = ttk.Label(self.header_frame, text=self.L("header_subtitle").format(VERSION=VERSION), font=("Segoe UI", 10, "italic"))
        self.lbl_subtitle.pack(side="left", padx=5, pady=4)

        # Main Layout frame (left = options, right = console logs)
        main_pane = ttk.Frame(self.root)
        main_pane.pack(fill="both", expand=True, padx=15, pady=5)

        # Column 1 (Left): WoW Settings & Scheduler
        col1 = ttk.Frame(main_pane)
        col1.pack(side="left", fill="both", padx=(0, 10))

        # Card 1: WoW & Account Config
        card_wow = ttk.Frame(col1, style="Panel.TFrame")
        card_wow.pack(fill="x", pady=(0, 10))
        
        self.lbl_card_wow_hdr = ttk.Label(card_wow, text=self.L("card_wow_hdr"), style="Header.TLabel")
        self.lbl_card_wow_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_wow_settings_fields(card_wow)

        # Card 2: Background Task Scheduler Automation
        card_sched = ttk.Frame(col1, style="Panel.TFrame")
        card_sched.pack(fill="x", pady=(0, 10))
        
        self.lbl_card_sched_hdr = ttk.Label(card_sched, text=self.L("card_sched_hdr"), style="Header.TLabel")
        self.lbl_card_sched_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_scheduler_fields(card_sched)

        # Save Button Card
        card_save = ttk.Frame(col1, style="Panel.TFrame")
        card_save.pack(fill="x")
        
        self.btn_save = ttk.Button(card_save, text=self.L("btn_save_settings"), command=self.save_settings, width=30)
        self.btn_save.pack(padx=10, pady=10, fill="x")

        # Column 2 (Middle): Discord & WoW Audit
        col2 = ttk.Frame(main_pane)
        col2.pack(side="left", fill="both", padx=(0, 10))

        # Card 3: Discord Bot Sync Settings
        card_discord = ttk.Frame(col2, style="Panel.TFrame")
        card_discord.pack(fill="x", pady=(0, 10))
        
        self.lbl_card_discord_hdr = ttk.Label(card_discord, text=self.L("card_discord_hdr"), style="Header.TLabel")
        self.lbl_card_discord_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_discord_sync_fields(card_discord)

        # Card 4: WoW Audit Integration Settings
        card_wowaudit = ttk.Frame(col2, style="Panel.TFrame")
        card_wowaudit.pack(fill="x", pady=(0, 10))
        
        self.lbl_card_wowaudit_hdr = ttk.Label(card_wowaudit, text=self.L("card_wowaudit_hdr"), style="Header.TLabel")
        self.lbl_card_wowaudit_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_wowaudit_sync_fields(card_wowaudit)

        # Column 3 (Right): Console/Console Log Card
        right_col = ttk.Frame(main_pane, style="Panel.TFrame")
        right_col.pack(side="right", fill="both", expand=True)

        self.lbl_console_hdr = ttk.Label(right_col, text=self.L("lbl_console_hdr"), style="Header.TLabel")
        self.lbl_console_hdr.pack(fill="x", padx=10, pady=(10, 5))

        self.create_console_view(right_col)

    def create_wow_settings_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # Language Selection
        self.lbl_language = ttk.Label(grid, text=self.L("lbl_language"), style="Panel.TLabel")
        self.lbl_language.grid(row=0, column=0, sticky="w", pady=4)
        self.cb_language = ttk.Combobox(grid, values=["English", "简体中文", "繁體中文", "Español"], state="readonly", width=15)
        self.cb_language.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=4)
        
        lang = self.settings.get("language", "en")
        if lang == "zh":
            self.cb_language.set("简体中文")
        elif lang == "zh_tw":
            self.cb_language.set("繁體中文")
        elif lang == "es":
            self.cb_language.set("Español")
        else:
            self.cb_language.set("English")
            
        self.cb_language.bind("<<ComboboxSelected>>", self.on_language_changed)

        # Region Dropdown
        self.lbl_region = ttk.Label(grid, text=self.L("lbl_region"), style="Panel.TLabel")
        self.lbl_region.grid(row=1, column=0, sticky="w", pady=4)
        self.cb_region = ttk.Combobox(grid, values=["", "us", "eu", "tw", "kr", "cn"], state="readonly", width=15)
        self.cb_region.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)
        self.cb_region.set(self.settings.get("region", ""))

        # RIO API Delay
        self.lbl_rio_delay = ttk.Label(grid, text=self.L("lbl_rio_delay"), style="Panel.TLabel")
        self.lbl_rio_delay.grid(row=2, column=0, sticky="w", pady=4)
        self.ent_rio_delay = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_rio_delay.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_rio_delay.insert(0, str(self.settings["rio_delay"]))

        # WoW Directory Selector
        self.lbl_wow_path = ttk.Label(grid, text=self.L("lbl_wow_path"), style="Panel.TLabel")
        self.lbl_wow_path.grid(row=3, column=0, sticky="w", pady=4)
        dir_frame = ttk.Frame(grid, style="Panel.TFrame")
        dir_frame.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)
        dir_frame.columnconfigure(0, weight=1)

        self.ent_wow_path = tk.Entry(dir_frame, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_wow_path.grid(row=0, column=0, sticky="ew")
        self.ent_wow_path.insert(0, self.settings["wow_path"])

        self.btn_browse = ttk.Button(dir_frame, text=self.L("btn_browse"), command=self.browse_wow_directory, width=8)
        self.btn_browse.grid(row=0, column=1, padx=(5, 0))

        grid.columnconfigure(1, weight=1)

    def create_scheduler_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # AM Run Time
        self.lbl_sched_am = ttk.Label(grid, text=self.L("lbl_sched_am"), style="Panel.TLabel")
        self.lbl_sched_am.grid(row=0, column=0, sticky="w", pady=4)
        self.ent_sched_am = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, width=10)
        self.ent_sched_am.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=4)
        self.ent_sched_am.insert(0, self.settings["schedule_am"])

        # PM Run Time
        self.lbl_sched_pm = ttk.Label(grid, text=self.L("lbl_sched_pm"), style="Panel.TLabel")
        self.lbl_sched_pm.grid(row=1, column=0, sticky="w", pady=4)
        self.ent_sched_pm = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, width=10)
        self.ent_sched_pm.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)
        self.ent_sched_pm.insert(0, self.settings["schedule_pm"])

        # Run on Logon Trigger
        self.var_sched_logon = tk.BooleanVar(value=self.settings["schedule_logon"])
        self.chk_logon = ttk.Checkbutton(grid, text=self.L("chk_logon"), variable=self.var_sched_logon)
        self.chk_logon.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        # Run UI on Startup
        self.var_run_on_startup = tk.BooleanVar(value=self.settings.get("run_on_startup", True))
        self.chk_startup = ttk.Checkbutton(grid, text=self.L("chk_startup"), variable=self.var_run_on_startup)
        self.chk_startup.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)

        # Sync on WoW Exit
        self.var_sync_on_wow_exit = tk.BooleanVar(value=self.settings.get("sync_on_wow_exit", True))
        self.chk_wow_exit = ttk.Checkbutton(grid, text=self.L("chk_wow_exit"), variable=self.var_sync_on_wow_exit)
        self.chk_wow_exit.grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        # Minimize on Close Option
        self.var_minimize_on_close = tk.BooleanVar(value=self.settings.get("minimize_on_close", True))
        self.chk_minimize_on_close = ttk.Checkbutton(grid, text=self.L("chk_minimize_on_close"), variable=self.var_minimize_on_close)
        self.chk_minimize_on_close.grid(row=5, column=0, columnspan=2, sticky="w", pady=6)

        # OS Task Register Actions
        task_action_frame = ttk.Frame(parent, style="Panel.TFrame")
        task_action_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.btn_register = ttk.Button(task_action_frame, text=self.L("btn_register"), command=self.register_background_tasks)
        self.btn_register.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_unregister = ttk.Button(task_action_frame, text=self.L("btn_unregister"), command=self.unregister_background_tasks)
        self.btn_unregister.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def create_discord_sync_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # Sync Key
        self.lbl_discord_key = ttk.Label(grid, text=self.L("lbl_discord_key"), style="Panel.TLabel")
        self.lbl_discord_key.grid(row=0, column=0, sticky="w", pady=4)
        self.ent_discord_key = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_discord_key.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_discord_key.insert(0, self.settings.get("discord_sync_key", ""))

        # Checkbutton to auto-sync on import
        self.var_sync_on_import = tk.BooleanVar(value=self.settings.get("sync_on_import", True))
        self.chk_sync_on_import = ttk.Checkbutton(grid, text=self.L("chk_sync_on_import"), variable=self.var_sync_on_import)
        self.chk_sync_on_import.grid(row=1, column=0, columnspan=2, sticky="w", pady=6)

        grid.columnconfigure(1, weight=1)

        # Button inside Card 3 to run sync now
        self.btn_sync_now = ttk.Button(parent, text=self.L("btn_sync_now"), command=self.trigger_discord_sync)
        self.btn_sync_now.pack(padx=10, pady=(5, 10), fill="x")

    def load_profile_choices(self):
        wow_path = self.ent_wow_path.get().strip()
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
            # Drop the account prefix if present in the raw choice
            key = raw.split(" / ", 1)[1] if " / " in raw else raw
            
            if "::" in key:
                realm, profile = key.split("::", 1)
                parts = profile.rsplit("-", 1)
                if len(parts) == 2:
                    display = f"{parts[0]} - {parts[1]}"
                else:
                    display = profile
            else:
                display = key
            
            self.profile_display_map[display] = raw
            display_choices.append(display)
            
        self.cb_wowaudit_profile.configure(values=display_choices)
        if display_choices:
            self.cb_wowaudit_profile.set(display_choices[0])
        else:
            self.cb_wowaudit_profile.set("")

    def create_wowaudit_sync_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # API Key Input
        self.lbl_wowaudit_key = ttk.Label(grid, text=self.L("lbl_wowaudit_key"), style="Panel.TLabel")
        self.lbl_wowaudit_key.grid(row=0, column=0, sticky="w", pady=4)
        self.ent_wowaudit_key = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_wowaudit_key.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        # RLM Profile Selection Dropdown
        self.lbl_wowaudit_profile = ttk.Label(grid, text=self.L("lbl_wowaudit_profile"), style="Panel.TLabel")
        self.lbl_wowaudit_profile.grid(row=1, column=0, sticky="w", pady=4)
        
        self.cb_wowaudit_profile = ttk.Combobox(grid, state="readonly")
        self.cb_wowaudit_profile.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)

        grid.columnconfigure(1, weight=1)

        # Binding WoW Path edit box changes to refresh the dropdown choices
        self.ent_wow_path.bind("<FocusOut>", self.refresh_profile_dropdown)

        # Buttons Frame
        btn_frame = ttk.Frame(parent, style="Panel.TFrame")
        btn_frame.pack(fill="x", padx=10, pady=(5, 5))

        self.btn_wowaudit_add = ttk.Button(btn_frame, text=self.L("btn_wowaudit_add"), command=self.add_wowaudit_mapping)
        self.btn_wowaudit_add.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_wowaudit_del = ttk.Button(btn_frame, text=self.L("btn_wowaudit_del"), command=self.del_wowaudit_mapping)
        self.btn_wowaudit_del.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Mappings Listbox
        self.lst_wowaudit_teams = tk.Listbox(parent, bg=BG_ENTRY, fg=FG_TEXT, selectbackground=FG_ACCENT, selectforeground=BG_DARK, highlightbackground=BORDER_COLOR, relief="flat", height=4)
        self.lst_wowaudit_teams.pack(fill="x", padx=10, pady=(5, 10))

        # Load current mappings
        self.update_wowaudit_listbox()
        self.refresh_profile_dropdown()

    def update_wowaudit_listbox(self):
        self.lst_wowaudit_teams.delete(0, tk.END)
        for t in self.settings.get("wowaudit_sync", []):
            team_name = t.get("wowaudit_team_name", "Unknown")
            raw_prof = t.get("rlm_profile_key", "")
            profile = raw_prof.split("::")[-1]
            parts = profile.rsplit("-", 1)
            if len(parts) == 2:
                profile_fmt = f"{parts[0]} - {parts[1]}"
            else:
                profile_fmt = profile
            self.lst_wowaudit_teams.insert(tk.END, f"{team_name} ➔ {profile_fmt}")

    def add_wowaudit_mapping(self):
        api_key = self.ent_wowaudit_key.get().strip()
        profile = self.cb_wowaudit_profile.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", self.L("wowaudit_err_invalid_key"))
            return
        if not profile:
            messagebox.showerror("Error", self.L("wowaudit_err_profile_required"))
            return
            
        self.log_message(f"Contacting WoW Audit to fetch team details...")
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            r = requests.get("https://wowaudit.com/v1/team", headers=headers, timeout=5)
            if r.status_code == 200:
                team_data = r.json()
                team_name = team_data.get("name", "Unknown")
                realm = team_data.get("url", "").split("/")[-4] if "url" in team_data else ""
                full_team_name = f"{team_name} ({realm.capitalize()})" if realm else team_name
                
                # Map back the display string to the raw profile key
                raw_profile = getattr(self, "profile_display_map", {}).get(profile, profile)
                
                sync_list = self.settings.setdefault("wowaudit_sync", [])
                for existing in sync_list:
                    if existing.get("rlm_profile_key") == raw_profile:
                        messagebox.showerror("Error", self.L("wowaudit_err_already_mapped"))
                        return
                        
                sync_list.append({
                    "api_key": api_key,
                    "wowaudit_team_name": full_team_name,
                    "rlm_profile_key": raw_profile
                })
                self.update_wowaudit_listbox()
                self.ent_wowaudit_key.delete(0, tk.END)
                self.log_message(f"Mapped team '{full_team_name}' to profile '{raw_profile}' successfully.")
            elif r.status_code == 401:
                messagebox.showerror("Error", self.L("wowaudit_err_unauthorized"))
            elif r.status_code == 403:
                messagebox.showerror("Error", self.L("wowaudit_err_forbidden"))
            elif r.status_code == 404:
                messagebox.showerror("Error", self.L("wowaudit_err_not_found"))
            else:
                messagebox.showerror("Error", self.L("wowaudit_err_http_generic").format(code=r.status_code))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to WoW Audit: {e}")

    def del_wowaudit_mapping(self):
        sel = self.lst_wowaudit_teams.curselection()
        if not sel:
            return
        idx = sel[0]
        sync_list = self.settings.get("wowaudit_sync", [])
        if 0 <= idx < len(sync_list):
            removed = sync_list.pop(idx)
            self.update_wowaudit_listbox()
            self.log_message(f"Removed mapping for team '{removed.get('wowaudit_team_name')}'")

    def set_action_buttons_state(self, state):
        for btn_name in ["btn_run_mplus", "btn_run_wowaudit", "btn_run_discord", "btn_sync_now"]:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(state=state)

    def create_console_view(self, parent):
        action_bar = ttk.Frame(parent, style="Panel.TFrame")
        action_bar.pack(fill="x", padx=10, pady=5)

        self.lbl_week_mode = ttk.Label(action_bar, text=self.L("lbl_week_mode"), style="Panel.TLabel")
        self.lbl_week_mode.pack(side="left", pady=4)
        
        vals = [self.L("week_both"), self.L("week_current"), self.L("week_last")]
        self.cb_week_mode = ttk.Combobox(action_bar, values=vals, state="readonly", width=11)
        self.cb_week_mode.set(self.L("week_both"))
        self.cb_week_mode.pack(side="left", padx=5)

        self.btn_run_mplus = ttk.Button(action_bar, text=self.L("btn_run_mplus"), style="Accent.TButton", command=self.trigger_live_import)
        self.btn_run_mplus.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_run_wowaudit = ttk.Button(action_bar, text=self.L("btn_run_wowaudit"), command=self.trigger_wowaudit_sync)
        self.btn_run_wowaudit.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_run_discord = ttk.Button(action_bar, text=self.L("btn_run_discord"), command=self.trigger_discord_sync)
        self.btn_run_discord.pack(side="left", fill="x", expand=True, padx=4)

        # Console Text Box
        console_frame = ttk.Frame(parent, style="Panel.TFrame")
        console_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.txt_console = tk.Text(console_frame, bg="#0d0d0d", fg=FG_TEXT, insertbackground=FG_TEXT, 
                                   font=("Consolas", 9), relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap="word")
        self.txt_console.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(console_frame, orient="vertical", command=self.txt_console.yview)
        scrollbar.pack(side="right", fill="y")
        self.txt_console.configure(yscrollcommand=scrollbar.set)

    def browse_wow_directory(self):
        dir_selected = filedialog.askdirectory(title=self.L("dialog_select_wtf"), initialdir="C:\\Program Files (x86)\\World of Warcraft")
        if dir_selected:
            self.ent_wow_path.delete(0, tk.END)
            self.ent_wow_path.insert(0, os.path.normpath(dir_selected))

    def log_message(self, msg):
        lang = self.settings.get("language", "en")
        if lang != "en":
            en_phrases = CONSOLE_PHRASES["en"]
            target_phrases = CONSOLE_PHRASES.get(lang, CONSOLE_PHRASES["en"])
            
            for key, en_text in en_phrases.items():
                target_text = target_phrases[key]
                if key == "discovered_accts":
                    import re
                    pattern = re.escape(en_text).replace(r"\{\}", r"(\d+)")
                    match = re.match(pattern, msg)
                    if match:
                        num = match.group(1)
                        msg = target_text.replace("{}", num)
                        break
                elif msg.strip() == en_text.strip():
                    msg = target_text
                    break
                elif msg.startswith(en_text):
                    suffix = msg[len(en_text):]
                    msg = target_text + suffix
                    break
                elif en_text in msg:
                    msg = msg.replace(en_text, target_text)
                    break
                    
        self.txt_console.insert(tk.END, f"{msg}\n")
        self.txt_console.see(tk.END)

    def get_week_code(self):
        val = self.cb_week_mode.get()
        if val == self.L("week_current"):
            return "current"
        elif val == self.L("week_last"):
            return "last"
        return "both"

    def trigger_live_import(self):
        # Concurrency check
        if str(self.btn_run_mplus.cget("state")) == "disabled":
            self.log_message("\n[INFO] An import/sync task is already active. Skipping request.")
            return

        # Save first before running to ensure python reads latest fields
        self.save_settings()

        self.set_action_buttons_state("disabled")
        self.log_message("\n--- Starting Mythic+ Importer Process ---")
        
        week_mode = self.get_week_code()
        script_file = self.addon_dir / "raidlootmatrix_mplus.py"

        def worker():
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-mplus", "--week", week_mode]
            else:
                cmd = [get_pythonw_path(), str(script_file), "--week", week_mode]
            self.log_message(f"Executing: {' '.join(cmd)}")
            try:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    bufsize=1,
                    universal_newlines=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=0x08000000 if sys.platform == "win32" else 0
                )
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self.log_message(line.rstrip())
                
                process.wait()
                self.log_message(f"Importer finished with exit code {process.returncode}")
                if process.returncode == 0:
                    self.log_message("Mythic+ data updated! Log into WoW and open /rlm UI to apply changes.")
                    
                    if self.var_sync_on_import.get():
                        self.log_message("\n--- Running Automatic Discord RLM Sync ---")
                        sync_script = self.addon_dir / "rlm_discord_sync.py"
                        if getattr(sys, 'frozen', False):
                            sync_cmd = [sys.executable, "--run-sync", "--non-interactive"]
                        else:
                            sync_cmd = [get_pythonw_path(), str(sync_script), "--non-interactive"]
                        self.log_message(f"Executing: {' '.join(sync_cmd)}")
                        sync_proc = subprocess.Popen(
                            sync_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True,
                            encoding="utf-8",
                            errors="replace",
                            creationflags=0x08000000 if sys.platform == "win32" else 0
                        )
                        while True:
                            line = sync_proc.stdout.readline()
                            if not line:
                                break
                            self.log_message(line.rstrip())
                        sync_proc.wait()
                        self.log_message(f"Discord sync finished with exit code {sync_proc.returncode}")
            except Exception as e:
                self.log_message(f"Process crashed: {e}")
            finally:
                self.root.after(0, lambda: self.set_action_buttons_state("normal"))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def trigger_wowaudit_sync(self):
        # Concurrency check
        if str(self.btn_run_wowaudit.cget("state")) == "disabled":
            self.log_message("\n[INFO] An import/sync task is already active. Skipping request.")
            return

        # Save first before running to ensure python reads latest fields
        self.save_settings()

        self.set_action_buttons_state("disabled")
        self.log_message("\n--- Starting WoW Audit Sync ---")
        
        script_file = self.addon_dir / "rlm_wowaudit_sync.py"

        def worker():
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-wowaudit"]
            else:
                cmd = [get_pythonw_path(), str(script_file)]
            self.log_message(f"Executing: {' '.join(cmd)}")
            try:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    bufsize=1,
                    universal_newlines=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=0x08000000 if sys.platform == "win32" else 0
                )
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self.log_message(line.rstrip())
                
                process.wait()
                self.log_message(f"WoW Audit Sync finished with exit code {process.returncode}")
            except Exception as e:
                self.log_message(f"Process crashed: {e}")
            finally:
                self.root.after(0, lambda: self.set_action_buttons_state("normal"))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def trigger_discord_sync(self):
        # Concurrency check
        if str(self.btn_run_discord.cget("state")) == "disabled":
            self.log_message("\n[INFO] An import/sync task is already active. Skipping request.")
            return

        # Save first before running to ensure python reads latest fields
        self.save_settings()

        self.set_action_buttons_state("disabled")
        self.log_message("\n--- Starting Discord RLM Sync Process ---")
        
        script_file = self.addon_dir / "rlm_discord_sync.py"
        
        def worker():
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-sync", "--non-interactive"]
            else:
                cmd = [get_pythonw_path(), str(script_file), "--non-interactive"]
            self.log_message(f"Executing: {' '.join(cmd)}")
            try:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    bufsize=1,
                    universal_newlines=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=0x08000000 if sys.platform == "win32" else 0
                )
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self.log_message(line.rstrip())
                
                process.wait()
                self.log_message(f"Sync finished with exit code {process.returncode}")
            except Exception as e:
                self.log_message(f"Process crashed: {e}")
            finally:
                self.root.after(0, lambda: self.set_action_buttons_state("normal"))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def register_background_tasks(self):
        if platform.system() != "Windows":
            messagebox.showinfo(self.L("automation_info_title"), self.L("automation_err_os"))
            return

        # Setup variables
        am_time = self.ent_sched_am.get().strip()
        pm_time = self.ent_sched_pm.get().strip()
        silent_bat = self.addon_dir / "raidlootmatrix_mplus_silent.bat"
        task_folder = "RaidLootMatrix"

        # Generate/overwrite the silent batch runner
        try:
            mplus_py = self.addon_dir / "raidlootmatrix_mplus.py"
            sync_py = self.addon_dir / "rlm_discord_sync.py"
            wowaudit_py = self.addon_dir / "rlm_wowaudit_sync.py"
            with open(silent_bat, "w", encoding="utf-8") as f:
                f.write('@echo off\n')
                f.write('set RAIDLOOTMATRIX_SCHEDULED=1\n')
                if getattr(sys, 'frozen', False):
                    f.write(f'"{sys.executable}" --run-mplus --week both > "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                    if self.var_sync_on_import.get():
                        f.write(f'"{sys.executable}" --run-sync --non-interactive >> "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                    f.write(f'"{sys.executable}" --run-wowaudit >> "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                else:
                    f.write(f'"{get_pythonw_path()}" "{mplus_py}" --week both > "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                    if self.var_sync_on_import.get():
                        f.write(f'"{get_pythonw_path()}" "{sync_py}" --non-interactive >> "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                    f.write(f'"{get_pythonw_path()}" "{wowaudit_py}" >> "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
        except Exception as e:
            self.log_message(f"Failed to generate silent runner: {e}")
            return

        self.log_message("\n--- Registering Scheduled Tasks ---")
        
        # Helper to execute task commands
        def run_task_cmd(cmd_args, desc):
            try:
                res = subprocess.run(cmd_args, capture_output=True, text=True,
                                     creationflags=0x08000000 if sys.platform == "win32" else 0)
                if res.returncode == 0:
                    self.log_message(f"SUCCESS: Created task: {desc}")
                else:
                    self.log_message(f"FAILED: Task: {desc}\nError: {res.stderr.strip()}")
            except Exception as e:
                self.log_message(f"Execution Error: {e}")

        vbs_runner = self.addon_dir / "raidlootmatrix_mplus_run.vbs"

        # Task 1: AM Time
        cmd_am = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - Daily AM", "/tr", f"wscript.exe \"{vbs_runner}\"", "/sc", "DAILY", "/st", am_time, "/f"]
        run_task_cmd(cmd_am, f"Daily at {am_time}")

        # Task 2: PM Time
        cmd_pm = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - Daily PM", "/tr", f"wscript.exe \"{vbs_runner}\"", "/sc", "DAILY", "/st", pm_time, "/f"]
        run_task_cmd(cmd_pm, f"Daily at {pm_time}")

        # Task 3: Logon if enabled
        if self.var_sched_logon.get():
            cmd_logon = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - At Logon", "/tr", f"wscript.exe \"{vbs_runner}\"", "/sc", "ONLOGON", "/delay", "0005:00", "/f"]
            run_task_cmd(cmd_logon, "At logon (5 min delay)")
        else:
            # Delete if disabled
            subprocess.run(["schtasks", "/delete", "/tn", f"{task_folder}\\M+ Import - At Logon", "/f"], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)

        # Task 4: WoW Watcher
        watcher_vbs = self.addon_dir / "raidlootmatrix_watcher_run.vbs"
        if self.var_sync_on_wow_exit.get():
            # Generate VBScript to run watcher silently
            vbs_script = (
                "' raidlootmatrix_watcher_run.vbs\n"
                "' Launches RLM_Companion.exe --watch-wow with a completely hidden window.\n"
                "Dim shell, fso, scriptDir, exe\n"
                "Set shell = CreateObject(\"WScript.Shell\")\n"
                "Set fso = CreateObject(\"Scripting.FileSystemObject\")\n"
                "scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)\n\n"
                "If fso.FileExists(scriptDir & \"\\RLM_Companion.exe\") Then\n"
                "    exe = \"\"\"\" & scriptDir & \"\\RLM_Companion.exe\"\" --watch-wow\"\n"
                "Else\n"
                "    exe = \"pythonw \"\"\" & scriptDir & \"\\rlm_importer_ui.py\"\" --watch-wow\"\n"
                "End If\n\n"
                "shell.Run exe, 0, False\n"
                "Set shell = Nothing\n"
                "Set fso = Nothing\n"
            )
            try:
                with open(watcher_vbs, "w", encoding="utf-8") as f:
                    f.write(vbs_script)
            except Exception as e:
                self.log_message(f"Failed to generate watcher VBS: {e}")

            cmd_watcher = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - WoW Watcher", "/tr", f"wscript.exe \"{watcher_vbs}\"", "/sc", "ONLOGON", "/f"]
            run_task_cmd(cmd_watcher, "WoW Watcher (runs on WoW exit)")
            
            # Start it immediately so they don't need to log out/in
            subprocess.run(["schtasks", "/run", "/tn", f"{task_folder}\\M+ Import - WoW Watcher"], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)
        else:
            # Delete task and cleanup file
            subprocess.run(["schtasks", "/delete", "/tn", f"{task_folder}\\M+ Import - WoW Watcher", "/f"], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)
            if watcher_vbs.exists():
                try:
                    os.remove(watcher_vbs)
                except Exception:
                    pass

        messagebox.showinfo(self.L("automation_success_title"), self.L("automation_success_msg"))

    def unregister_background_tasks(self):
        if platform.system() != "Windows":
            messagebox.showinfo(self.L("automation_info_title"), self.L("automation_err_win_only"))
            return

        self.log_message("\n--- Removing Scheduled Tasks ---")
        task_folder = "RaidLootMatrix"
        
        tasks = [
            f"{task_folder}\\M+ Import - Daily AM",
            f"{task_folder}\\M+ Import - Daily PM",
            f"{task_folder}\\M+ Import - At Logon",
            f"{task_folder}\\M+ Import - WoW Watcher"
        ]

        for t in tasks:
            try:
                res = subprocess.run(["schtasks", "/delete", "/tn", t, "/f"], capture_output=True, text=True,
                                     creationflags=0x08000000 if sys.platform == "win32" else 0)
                if res.returncode == 0:
                    self.log_message(f"SUCCESS: Deleted task: {t}")
                else:
                    self.log_message(f"INFO: Task {t} was not found or already deleted.")
            except Exception as e:
                self.log_message(f"Execution Error: {e}")

        # Cleanup watcher VBScript
        watcher_vbs = self.addon_dir / "raidlootmatrix_watcher_run.vbs"
        if watcher_vbs.exists():
            try:
                os.remove(watcher_vbs)
            except Exception:
                pass

        messagebox.showinfo(self.L("automation_removed_title"), self.L("automation_removed_msg"))

    def create_tray_image(self):
        # Generate a clean 64x64 transparent icon
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        # Gold circular border
        dc.ellipse([6, 6, 58, 58], outline=(255, 204, 0, 255), width=4)
        # Gold inner square
        dc.rectangle([18, 18, 46, 46], fill=(255, 204, 0, 255))
        # Transparent center details
        dc.rectangle([26, 26, 38, 38], fill=(0, 0, 0, 0))
        return image

    def start_tray_icon(self):
        # Define menu items
        menu = pystray.Menu(
            pystray.MenuItem("Open Control Panel", self.show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Run M+ Import Now", lambda: self.root.after(0, self.trigger_live_import)),
            pystray.MenuItem("Run Discord Sync Now", lambda: self.root.after(0, self.trigger_discord_sync)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit RLM Companion", self.quit_app)
        )
        
        # Load custom icon if available, otherwise generate fallback
        if self.icon_path_png.exists():
            try:
                image = Image.open(self.icon_path_png)
            except Exception:
                image = self.create_tray_image()
        else:
            image = self.create_tray_image()
            
        self.tray_icon = pystray.Icon("RLM Companion", image, "RLM Desktop Companion", menu)
        
        # Run tray loop in a background daemon thread
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def hide_window(self):
        if self.settings.get("minimize_on_close", True):
            # Hide the main Tkinter window
            self.root.withdraw()
            self.log_message("Minimized to system tray. Double-click the tray icon to reopen.")
        else:
            self.quit_app()

    def show_window(self, icon=None, item=None):
        # Restore the Tkinter window safely from tray thread
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self, icon=None, item=None):
        # Fully shutdown everything
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def update_startup_shortcut(self):
        startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        vbs_path = os.path.join(startup_dir, "RLM_Desktop_Companion_Startup.vbs")
        
        if self.settings.get("run_on_startup", True):
            try:
                if getattr(sys, 'frozen', False):
                    # Compiled EXE runs itself directly
                    run_cmd = f'"""{sys.executable}"""'
                else:
                    # Dev mode runs pythonw.exe
                    python_dir = os.path.dirname(sys.executable)
                    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
                    if not os.path.exists(pythonw_exe):
                        pythonw_exe = "pythonw.exe"
                    run_cmd = f'"""{pythonw_exe}"" ""{self.addon_dir / "rlm_importer_ui.py"}"""'
                
                with open(vbs_path, "w", encoding="utf-8") as f:
                    f.write(f'Set WshShell = CreateObject("WScript.Shell")\n')
                    f.write(f'WshShell.Run {run_cmd}, 0, False\n')
                self.log_message("Windows startup shortcut registered successfully.")
            except Exception as e:
                self.log_message(f"Error creating startup shortcut: {e}")
        else:
            if os.path.exists(vbs_path):
                try:
                    os.remove(vbs_path)
                    self.log_message("Windows startup shortcut removed.")
                except Exception as e:
                    self.log_message(f"Error removing startup shortcut: {e}")

    def create_desktop_shortcut(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_lnk = os.path.join(desktop_dir, "RLM Desktop Companion.lnk")
        
        if getattr(sys, 'frozen', False):
            # Compiled EXE shortcut points directly to itself
            target_path = sys.executable
            arguments = ""
        else:
            # Dev mode shortcut points to pythonw.exe
            python_dir = os.path.dirname(sys.executable)
            pythonw_exe = os.path.join(python_dir, "pythonw.exe")
            if not os.path.exists(pythonw_exe):
                pythonw_exe = "pythonw.exe"
            target_path = pythonw_exe
            arguments = f'"""{self.addon_dir / "rlm_importer_ui.py"}"""'
            
        vbs_script = (
            f'Set WshShell = CreateObject("WScript.Shell")\n'
            f'Set oMyShortcut = WshShell.CreateShortcut("{shortcut_lnk}")\n'
            f'oMyShortcut.TargetPath = "{target_path}"\n'
        )
        if arguments:
            vbs_script += f'oMyShortcut.Arguments = {arguments}\n'
        vbs_script += (
            f'oMyShortcut.WorkingDirectory = "{self.addon_dir}"\n'
            f'oMyShortcut.IconLocation = "{self.icon_path_ico},0"\n'
            f'oMyShortcut.Save\n'
        )
        
        try:
            vbs_tmp = self.addon_dir / "create_shortcut_temp.vbs"
            with open(vbs_tmp, "w", encoding="utf-8") as f:
                f.write(vbs_script)
            
            subprocess.run(["cscript", "/nologo", str(vbs_tmp)], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)
            if vbs_tmp.exists():
                os.remove(vbs_tmp)
            self.log_message("Desktop shortcut created successfully.")
        except Exception as e:
            self.log_message(f"Could not create desktop shortcut: {e}")

    def check_for_updates(self):
        def worker():
            import urllib.request
            import urllib.error
            import json
            try:
                url = "https://api.github.com/repos/Rynedelewis/RLM-Desktop-Companion/releases/latest"
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    tag_name = data.get("tag_name", "").strip().lstrip("v")
                    if tag_name:
                        # parse version lists
                        local_parts = [int(x) for x in VERSION.split(".")]
                        remote_parts = [int(x) for x in tag_name.split(".")]
                        # Pad lists with zeros if they differ in length
                        max_len = max(len(local_parts), len(remote_parts))
                        local_parts += [0] * (max_len - len(local_parts))
                        remote_parts += [0] * (max_len - len(remote_parts))
                        if remote_parts > local_parts:
                            self.root.after(0, lambda: self.show_update_available(data.get("tag_name", ""), data.get("html_url", "")))
            except Exception as e:
                # Silently fail, don't interrupt the user
                pass
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def show_update_available(self, remote_version, release_url):
        update_frame = ttk.Frame(self.header_frame)
        update_frame.pack(side="right", padx=5, pady=4)
        
        lbl_update = ttk.Label(update_frame, text=self.L("lbl_update_available").format(remote_version=remote_version), foreground="#ffcc00", font=("Segoe UI", 10, "bold"))
        lbl_update.pack(side="left", padx=5)
        
        btn_update = ttk.Button(update_frame, text=self.L("btn_update_now"), width=12, command=lambda: self.start_auto_update(remote_version))
        btn_update.pack(side="left", padx=5)

    def start_auto_update(self, tag_name):
        # Open a loading/status pop-up
        self.update_win = tk.Toplevel(self.root)
        self.update_win.title(self.L("title_app_update"))
        self.update_win.geometry("400x150")
        self.update_win.configure(bg=BG_DARK)
        self.update_win.transient(self.root)
        self.update_win.grab_set()

        lbl = ttk.Label(self.update_win, text=self.L("lbl_updating_status").format(tag_name=tag_name), style="Panel.TLabel", font=("Segoe UI", 11))
        lbl.pack(pady=20)
        
        self.update_progress = ttk.Progressbar(self.update_win, mode="indeterminate", length=300)
        self.update_progress.pack(pady=10)
        self.update_progress.start(10)

        threading.Thread(target=self.run_auto_update_thread, args=(tag_name,), daemon=True).start()

    def run_auto_update_thread(self, tag_name):
        import urllib.request
        import zipfile
        import shutil

        try:
            is_frozen = getattr(sys, 'frozen', False)
            
            if is_frozen:
                # 1. Standalone executable mode
                exe_url = f"https://github.com/Rynedelewis/RLM-Desktop-Companion/releases/download/{tag_name}/RLM_Companion.exe"
                new_exe = self.addon_dir / "RLM_Companion_new.exe"
                
                req = urllib.request.Request(exe_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    with open(new_exe, "wb") as f:
                        f.write(response.read())
                
                # Create bat updater
                bat_path = self.addon_dir / "apply_update.bat"
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(
                        "@echo off\n"
                        "timeout /t 2 /nobreak > nul\n"
                        f"del \"{self.addon_dir / 'RLM_Companion.exe'}\"\n"
                        f"rename \"{new_exe}\" \"RLM_Companion.exe\"\n"
                        f"start \"\" explorer.exe \"{self.addon_dir / 'RLM_Companion.exe'}\"\n"
                        "del \"%~f0\"\n"
                    )
                
                # Clean environment to prevent PyInstaller PATH pollution DLL load errors
                clean_env = os.environ.copy()
                if sys.platform == "win32":
                    path_parts = clean_env.get("PATH", "").split(os.pathsep)
                    clean_path_parts = [p for p in path_parts if "_MEI" not in p]
                    clean_env["PATH"] = os.pathsep.join(clean_path_parts)
                for var in ["_MEIPASS", "MEIPASS2"]:
                    clean_env.pop(var, None)

                # Detached run
                subprocess.Popen([str(bat_path)], env=clean_env, creationflags=0x08000000)
                self.root.after(0, self.root.quit)
            else:
                # 2. Python script mode
                zip_url = f"https://github.com/Rynedelewis/RLM-Desktop-Companion/archive/refs/tags/{tag_name}.zip"
                temp_zip = self.addon_dir / "temp_update.zip"
                
                req = urllib.request.Request(zip_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    with open(temp_zip, "wb") as f:
                        f.write(response.read())
                
                # Unzip
                extract_dir = self.addon_dir / "temp_extract"
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Copy files over
                extracted_folders = list(extract_dir.glob("*"))
                if extracted_folders:
                    source_dir = extracted_folders[0]
                    for item in source_dir.iterdir():
                        if item.name in [".git", "rlm_importer_config.json", "rlm_bot_db.json", ".env"]:
                            continue
                        dest = self.addon_dir / item.name
                        if item.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                
                # Cleanup
                if temp_zip.exists():
                    os.remove(temp_zip)
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                
                self.root.after(0, self.show_update_success_restart)
        except Exception as e:
            self.root.after(0, lambda: self.show_update_failed_error(e))

    def show_update_success_restart(self):
        self.update_win.destroy()
        messagebox.showinfo(self.L("update_complete_title"), self.L("update_complete_msg"))

    def show_update_failed_error(self, err):
        self.update_win.destroy()
        messagebox.showerror(self.L("update_failed_title"), self.L("update_failed_msg").format(err=err))

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

def watch_wow_process():
    import time
    import subprocess
    
    executable = sys.executable
    script_dir = os.path.dirname(os.path.abspath(executable))
    
    # Resolve log path
    log_file = os.path.join(script_dir, "raidlootmatrix_mplus_auto.log")
    
    def log_msg(msg):
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watcher] {msg}\n")
        except Exception:
            pass

    log_msg("WoW Close Watcher process started.")
    
    # Determine the execution arguments (python vs compiled exe)
    if getattr(sys, 'frozen', False):
        executable_args = [sys.executable]
    else:
        executable_args = [sys.executable, sys.argv[0]]

    def is_wow_running():
        try:
            # CREATE_NO_WINDOW = 0x08000000
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq Wow.exe"', shell=True, creationflags=0x08000000).decode('utf-8', errors='ignore')
            return "Wow.exe" in output
        except Exception:
            return False

    was_running = False
    while True:
        try:
            running = is_wow_running()
            if running:
                if not was_running:
                    log_msg("Wow.exe detected running.")
                    was_running = True
            else:
                if was_running:
                    log_msg("Wow.exe closed! Starting synchronization...")
                    
                    # Run Mythic+ runs parser and Discord Sync, outputting to the log file
                    with open(log_file, "a", encoding="utf-8") as lf:
                        lf.write("\n--- Running M+ Import ---\n")
                        lf.flush()
                        subprocess.run(executable_args + ["--run-mplus", "--week", "both"], stdout=lf, stderr=lf, cwd=script_dir, creationflags=0x08000000)
                        
                        lf.write("\n--- Running Discord Sync ---\n")
                        lf.flush()
                        subprocess.run(executable_args + ["--run-sync", "--non-interactive"], stdout=lf, stderr=lf, cwd=script_dir, creationflags=0x08000000)

                        lf.write("\n--- Running WoW Audit Sync ---\n")
                        lf.flush()
                        subprocess.run(executable_args + ["--run-wowaudit"], stdout=lf, stderr=lf, cwd=script_dir, creationflags=0x08000000)
                    
                    log_msg("Synchronization completed.")
                    was_running = False
        except Exception as e:
            log_msg(f"Error in watcher loop: {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    # Check for command line argument routing
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        if arg1 == "--run-mplus":
            # Shift sys.argv to remove --run-mplus so raidlootmatrix_mplus parses its options normally
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            try:
                raidlootmatrix_mplus.main()
            except Exception as e:
                print(f"[ERROR] Mythic+ importer failed: {e}")
                sys.exit(1)
            sys.exit(0)
        elif arg1 == "--run-sync":
            # Shift sys.argv to remove --run-sync so rlm_discord_sync parses its options normally
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            try:
                rlm_discord_sync.main()
            except Exception as e:
                print(f"[ERROR] Discord sync failed: {e}")
                sys.exit(1)
            sys.exit(0)
        elif arg1 == "--run-wowaudit":
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            try:
                import rlm_wowaudit_sync
                rlm_wowaudit_sync.main()
            except Exception as e:
                print(f"[ERROR] WoW Audit sync failed: {e}")
                sys.exit(1)
            sys.exit(0)
        elif arg1 == "--watch-wow":
            try:
                watch_wow_process()
            except Exception as e:
                print(f"[ERROR] WoW watcher failed: {e}")
                sys.exit(1)
            sys.exit(0)

    root = tk.Tk()
    app = RLMImporterApp(root)
    
    # Enforce single instance of UI, wake up existing window if duplicate launched
    app_lock = check_single_instance(lambda: root.after(0, app.show_window))
    
    root.mainloop()
