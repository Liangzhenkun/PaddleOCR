#define MyAppName "PaddleOCR Desktop Tool"
#define MyAppExeName "PaddleOCRDesktopTool.exe"
#define MyAppPublisher "Liangzhenkun"
#define MyAppVersion "0.3.1"

[Setup]
AppId={{A252862A-0766-4338-9E6B-74D483267145}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=PaddleOCRDesktopTool-Setup-{#MyAppVersion}
SetupIconFile=..\assets\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "simplifiedchinese"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "..\dist\PaddleOCRDesktopTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\{#MyAppExeName}"
Type: filesandordirs; Name: "{app}\_internal"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsDir: string;
  SettingsPath: string;
  AppLangCode: string;
  Content: string;
begin
  if CurStep = ssPostInstall then
  begin
    if ActiveLanguage = 'simplifiedchinese' then
      AppLangCode := 'zh_CN'
    else
      AppLangCode := 'en_US';

    SettingsDir := ExpandConstant('{localappdata}\PaddleOCRDesktopTool');
    if not DirExists(SettingsDir) then
      ForceDirectories(SettingsDir);

    SettingsPath := SettingsDir + '\settings.json';
    Content :=
      '{'#13#10 +
      '  "ui_language": "' + AppLangCode + '"'#13#10 +
      '}'#13#10;
    SaveStringToFile(SettingsPath, Content, False);
  end;
end;
