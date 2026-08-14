; =====================================================================
; RaidLootMatrix Desktop Companion — Inno Setup Script
; Generates a professional single-file Windows Setup installer (.exe)
; =====================================================================

#define MyAppName "RaidLootMatrix Desktop Companion"
#define MyAppVersion "1.5.4"
#define MyAppPublisher "RaidLootMatrix Team"
#define MyAppURL "https://github.com/rynecheow/AAAddon"
#define MyAppExeName "RLM_Companion.exe"

[Setup]
AppId={{D37E848A-9A22-4E5F-81A1-8C54B7A09231}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\RaidLootMatrix Companion
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_setup
OutputBaseFilename=RaidLootMatrix_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Automatically launch RaidLootMatrix Companion when Windows starts"; GroupDescription: "Automation Options:"

[Files]
Source: "..\dist\RLM_Companion.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RaidLootMatrixCompanion"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
