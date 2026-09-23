; Inno Setup script for the renasync-gui windows build.
; Compile with: iscc /DMyAppVersion=0.0.1 renasync.iss

#ifndef MyAppVersion
	#define MyAppVersion "0.0.1"
#endif

#define MyAppName "Renasync"
#define MyAppExeName "renasync-gui.exe"
#define MyAppPublisher "renasync-gui"

[Setup]
AppId={{5272DF8A-8E7C-4A63-9F2B-6C1D8E9A7B3F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Renasync
DefaultGroupName=Renasync
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Renasync-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\renasync-gui.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Renasync"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Renasync"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Renasync"; Flags: nowait postinstall skipifsilent