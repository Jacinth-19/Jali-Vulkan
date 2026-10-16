; Personal-only build. Do not publish the installer or bundled models/executable.
#ifndef BundleDir
  #error BundleDir must point to your personal JaliStudio application directory
#endif
#ifndef OutputDir
  #error OutputDir must be explicit
#endif
[Setup]
AppId={{B68C270D-620D-45B5-8DCD-B503902BD52E}
AppName=Jali Studio Personal
AppVersion=0.2.0
AppPublisher=Personal local build
DefaultDirName={localappdata}\Programs\JaliStudio
DefaultGroupName=Jali Studio Personal
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=JaliStudio-Personal-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\JaliStudio.exe
SetupLogging=yes
DisableProgramGroupPage=yes
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Jali Studio"; Filename: "{app}\JaliStudio.exe"
Name: "{group}\Uninstall Jali Studio"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\JaliStudio.exe"; Description: "Open Jali Studio launcher"; Flags: nowait postinstall skipifsilent
[Code]
function InitializeSetup(): Boolean;
begin
  if WizardSilent then
    Result := ExpandConstant('{param:PERSONALUSE|}') = 'yes'
  else
    Result := MsgBox('This unsigned installer is for YOUR personal use only. Do not redistribute it. GPL/eSpeak corresponding-source and combined-work obligations remain unresolved. Signing is optional and does not establish license compliance. Continue?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;
// User data (including conversations and pairing keys) is deliberately preserved.
// No network update service, driver, machine-wide PATH or security setting changes.
