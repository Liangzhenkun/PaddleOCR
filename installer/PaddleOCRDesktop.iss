#define MyAppName "PaddleOCR Desktop Tool"
#define MyAppExeName "PaddleOCRDesktopTool.exe"
#define MyAppPublisher "Liangzhenkun"
#define MyAppVersion "0.3.0"

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

[CustomMessages]
english.AppLangPageTitle=Application language
english.AppLangPageDescription=Choose the default interface language used by the desktop app.
english.AppLangChinese=Simplified Chinese
english.AppLangEnglish=English
simplifiedchinese.AppLangPageTitle=软件界面语言
simplifiedchinese.AppLangPageDescription=请选择软件默认使用的界面语言。
simplifiedchinese.AppLangChinese=简体中文
simplifiedchinese.AppLangEnglish=English

[Code]
var
  AppLangPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  AppLangPage := CreateInputOptionPage(
    wpSelectDir,
    ExpandConstant('{cm:AppLangPageTitle}'),
    ExpandConstant('{cm:AppLangPageDescription}'),
    '',
    True,
    False
  );
  AppLangPage.Add(ExpandConstant('{cm:AppLangChinese}'));
  AppLangPage.Add(ExpandConstant('{cm:AppLangEnglish}'));

  if ActiveLanguage = 'simplifiedchinese' then
    AppLangPage.SelectedValueIndex := 0
  else
    AppLangPage.SelectedValueIndex := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsDir: string;
  SettingsPath: string;
  AppLangCode: string;
  Content: string;
begin
  if CurStep = ssPostInstall then
  begin
    if AppLangPage.SelectedValueIndex = 0 then
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
