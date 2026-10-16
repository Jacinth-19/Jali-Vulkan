#!/usr/bin/env python3
"""Build an opt-in portable Windows CPU/WebGL app from explicitly prepared assets.

Does not include recordings, credentials, caches other than the pinned analyzer,
or a native Vulkan executable. The latter remains a separate developer build.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--personal-build',action='store_true',required=True,help='Acknowledge local personal use only; redistribution/source compliance is not established');parser.add_argument('--no-archive',action='store_true',help='CI: test directory without creating a distributable ZIP');args=parser.parse_args()
    if sys.platform!='win32' or platform.machine().lower() not in ('amd64','x86_64'):raise RuntimeError('Build on Windows x64')
    from local_neural_speech import verify_assets
    from analyze_neural_clips import verify_engine
    from neural_platform import analyzer_path
    verify_assets(ROOT/'models/kokoro');verify_engine(analyzer_path())
    if importlib.metadata.version('pyinstaller')!='6.16.0':raise RuntimeError('Install pyinstaller==6.16.0 explicitly')
    dest=ROOT/'artifacts/windows-portable';dest.mkdir(parents=True,exist_ok=True)
    # Positive allowlist: never collect a whole checkout, home directory or cache.
    assets=[]
    for source,relative in [(ROOT/'models/kokoro','models/kokoro'),(ROOT/'artifacts/neural-studio','artifacts/neural-studio'),(analyzer_path().parent,'.cache/lipsync/rhubarb-windows')]:
        for f in source.rglob('*'):
            if f.is_file() and 'proof' not in f.relative_to(source).parts:
                assets.append((str(f),str(Path(relative)/f.relative_to(source).parent)))
    spec=dest/'JaliStudio.spec'
    spec.write_text('''from PyInstaller.utils.hooks import collect_all, copy_metadata
import importlib.metadata
datas='''+repr(assets)+'''
binaries=[];hiddenimports=[]
for package in ('kokoro_onnx','onnxruntime','phonemizer','espeakng_loader','segments','language_tags'):
    d,b,h=collect_all(package);datas+=d;binaries+=b;hiddenimports+=h
for distribution in importlib.metadata.distributions():
    name=distribution.metadata.get('Name')
    if name:datas+=copy_metadata(name)
a=Analysis(['''+repr(str(ROOT/'tools/portable_entry.py'))+'''],pathex=['''+repr(str(ROOT/'tools'))+'''],binaries=binaries,datas=datas,hiddenimports=hiddenimports,excludes=['tkinter','pytest'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='JaliStudio',console=True)
coll=COLLECT(exe,a.binaries,a.datas,name='JaliStudio')
''',encoding='utf-8')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--distpath',str(dest/'app'),'--workpath',str(dest/'work'),str(spec)],cwd=ROOT,check=True,timeout=600)
    app=dest/'app/JaliStudio'
    (app/'PERSONAL-BUILD-ONLY.txt').write_text('Personal local build only. Do not publish this bundle.\nphonemizer-fork is GPL-3.0 and espeakng-loader embeds eSpeak.\nComplete corresponding source, notices and combined-work redistribution\nobligations have NOT been established. Metadata alone is not compliance.\nThis does not change the repository license.\n',encoding='utf-8')
    (app/'START-HERE.txt').write_text('Jali portable CPU neural face studio\n\nExtract the ENTIRE ZIP to a writable folder, then double-click JaliStudio.exe.\nIt opens your default browser at localhost. No Python, Node, GitHub account,\nadmin installation, speech API, or runtime model download is required.\nKeep the console open; Ctrl+C stops the server. Windows SmartScreen may warn\nbecause this personal build is unsigned. Do not disable system security.\n\nVoice: stock Kokoro af_heart, not a clone. Human rig: CC0 MPFB/MakeHuman.\nWhole utterance or bounded sentence-batched playback; not incremental Kokoro.\nThis package uses WEBGL, not the separate native Vulkan developer renderer.\nSessions live under %LOCALAPPDATA%\\JaliVulkan\\sessions and old UUID folders\nare cleared on startup. Save desired WAVs before closing/restarting.\nNo public authentication; service is restricted to 127.0.0.1.\n\nLicense notices are in _internal/models/kokoro/licenses,\n_internal/artifacts/neural-studio/licenses, _internal/.cache/lipsync/rhubarb-windows,\nand the bundled Python package metadata/third-party notices.\nSource: https://github.com/Jacinth-19/Jali-Vulkan\n',encoding='utf-8')
    receipt={'schema':'jali-windows-portable-v1','personal_build_only':True,'redistribution_compliance_reviewed':False,'voice':'stock af_heart','renderer':'WebGL','runtime_downloads':False,'signed':False,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'build_packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata.get('Name')},
        'limits':'Portable personal build, not a signed consumer installer or target-laptop/hardware/perceptual acceptance.'}
    (app/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (dest/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if args.no_archive:print(app);return
    archive=shutil.make_archive(str(dest/'JaliStudio-Windows-x64'),'zip',root_dir=dest/'app',base_dir='JaliStudio')
    print(archive)


if __name__=='__main__':main()
