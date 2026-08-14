; =====================================================================
; RaidLootMatrix Desktop Companion — Inno Setup Script
; Generates a professional single-file Windows Setup installer (.exe)
; =====================================================================

#define MyAppName "RaidLootMatrix Desktop Companion"
#define MyAppVersion "1.7.7"
#define MyAppPublisher "RaidLootMatrix Team"
#define MyAppURL "https://github.com/Rynedelewis/RLM-Desktop-Companion"
#define MyAppExeName "RLM_Companion.exe"

[Setup]
AppId={{D37E848A-9A22-4E5F-81A1-8C54B7A09231}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\RaidLootMatrix Companion
PrivilegesRequired=lowest
CloseApplications=yes
CloseApplicationsFilter=*RLM_Companion*
RestartApplications=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=RLM_Companion_Setup_v{#MyAppVersion}
SetupIconFile=..\rlm_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Automatically launch RaidLootMatrix Companion when Windows starts"; GroupDescription: "Automation Options:"

[Files]
Source: "..\dist\RLM_Companion_Folder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RaidLootMatrixCompanion"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
