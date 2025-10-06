; Inno Setup Script for HeatSim
#define AppName "HeatSim"
#define AppPublisher "HeatSim"
#define AppURL "https://github.com/gevorkyan424/HeatSim"
#define AppExeName "HeatSim.exe"
; Passed via command line: /DAppVersion=1.9 /DProjectRoot=C:\path\to\repo
#ifndef AppVersion
  #define AppVersion "1.9"
#endif
#ifndef ProjectRoot
  #error "ProjectRoot is not defined. Pass /DProjectRoot=... to ISCC."
#endif

[Setup]
AppId={{4E0E9F3C-4E7B-4E3F-9F0A-6B6B8C1F1F18}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
; Per-user by default; user can choose any folder
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=no
DisableProgramGroupPage=yes
LicenseFile={#ProjectRoot}\Лицензионное_соглашение.txt
OutputDir={#ProjectRoot}\dist
OutputBaseFilename={#AppName}-Setup-v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#ProjectRoot}\\dist\\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\\Лицензионное_соглашение.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

[Run]
Filename: "{app}\\{#AppExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
