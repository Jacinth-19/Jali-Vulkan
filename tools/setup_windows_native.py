#!/usr/bin/env python3
"""Explicit source build of Windows native Vulkan (no paid SDK/driver download).

CI may OPT IN to the SwiftShader already installed with Chrome; never substitute
it silently for a user's hardware driver or redistribute that Chrome binary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 ('Vulkan-Headers','1.3.290','f38a653bf93cab7a2a229a53d2d53b1cba9a2819e4c0a7de13c54085bde9bcf5'),
 ('Vulkan-Loader','1.3.290','a1f0d80c4ee448d4fa37d1d4a4c4cf1d6d0f5873d3ca6dffe2a9498e6e654142'),
 ('tinygltf','2.9.3','c34443de2e9afaaf005713f69f5b061101a24ab2e9ee4021d882ac1d7983dbc0'),
]


def run(*args):subprocess.run([str(a) for a in args],cwd=ROOT,check=True,timeout=600)


def source(name,version,expected):
    owner='syoyo' if name=='tinygltf' else 'KhronosGroup'
    cache=ROOT/'.cache/deps';cache.mkdir(parents=True,exist_ok=True);archive=cache/f'{name}-{version}.tar.gz'
    if not archive.is_file():
        with urlopen(f'https://codeload.github.com/{owner}/{name}/tar.gz/refs/tags/v{version}',timeout=60) as src,archive.open('wb') as dst:shutil.copyfileobj(src,dst)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError(f'Checksum mismatch: {archive}; remove and prepare again')
    target=cache/f'{name}-{version}'
    if not target.is_dir():
        with tarfile.open(archive) as tar:
            for m in tar.getmembers():
                if not (cache/m.name).resolve().is_relative_to(cache.resolve()) or not (m.isfile() or m.isdir()):raise ValueError('Unsafe source archive')
            tar.extractall(cache)
    return target



def ci_driver_registration(remove=False):
    """Hosted elevated Windows ignores driver environment overrides (by design).

    Register ONLY this run's explicit test ICD on the disposable hosted machine;
    never alter a user's/self-hosted machine or disable secure loader behavior.
    """
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':
        if remove:return
        raise RuntimeError('Test-driver registration is restricted to disposable GitHub-hosted CI')
    import winreg
    icd=ROOT/'.cache/runtime/windows-swiftshader.json';state=ROOT/'artifacts/windows-native/ci-driver-registration.json'
    keyname=r'SOFTWARE\Khronos\Vulkan\Drivers'
    if remove:
        if not state.is_file() or not json.loads(state.read_text()).get('created_by_this_run'):return
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,keyname,0,winreg.KEY_SET_VALUE|winreg.KEY_WOW64_64KEY) as key:
            try:winreg.DeleteValue(key,str(icd))
            except FileNotFoundError:pass
        state.write_text(json.dumps({'created_by_this_run':True,'removed':True})+'\n');return
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,keyname,0,winreg.KEY_SET_VALUE|winreg.KEY_QUERY_VALUE|winreg.KEY_WOW64_64KEY) as key:
        try:winreg.QueryValueEx(key,str(icd))
        except FileNotFoundError:pass
        else:raise RuntimeError('Refusing to overwrite an existing driver registry value')
        winreg.SetValueEx(key,str(icd),0,winreg.REG_DWORD,0)
    state.parent.mkdir(parents=True,exist_ok=True);state.write_text(json.dumps({'created_by_this_run':True,'removed':False})+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--unregister-ci-driver',action='store_true',help='Cleanup only this run’s hosted-test registry value');p.add_argument('--ci-software',action='store_true',help='Explicitly use installed Chrome SwiftShader instead of hardware');a=p.parse_args()
    if sys.platform!='win32':raise ValueError('Run this source build on Windows x64 with Visual Studio C++ build tools')
    if a.unregister_ci_driver:ci_driver_registration(remove=True);return
    sources={name:source(name,v,sha) for name,v,sha in SOURCES};prefix=ROOT/'.cache/windows-vulkan'
    for name in ('Vulkan-Headers','Vulkan-Loader'):
        build=ROOT/f'build-windows-{name.lower()}'
        run('cmake','-S',sources[name],'-B',build,'-A','x64',f'-DCMAKE_INSTALL_PREFIX={prefix}',f'-DCMAKE_PREFIX_PATH={prefix}','-DBUILD_TESTS=OFF','-DUPDATE_DEPS=OFF')
        run('cmake','--build',build,'--config','Release','--parallel','2');run('cmake','--install',build,'--config','Release')
    library=prefix/'lib/vulkan-1.lib';loader=prefix/'bin/vulkan-1.dll'
    if not library.is_file() or not loader.is_file():raise RuntimeError('Vulkan loader build did not produce the expected x64 DLL/import library')
    run('cmake','-S',ROOT,'-B','build-live','-A','x64','-DJALI_ENABLE_VULKAN=ON','-DJALI_ENABLE_ESPEAK=OFF',f'-DPython3_EXECUTABLE={sys.executable}',f'-DVulkan_INCLUDE_DIR={prefix / "include"}',f'-DVulkan_LIBRARY={library}',f'-DTINYGLTF_INCLUDE_DIR={sources["tinygltf"]}',f'-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE={ROOT / "build-live"}')
    run('cmake','--build','build-live','--config','Release','--parallel','2');shutil.copy2(loader,ROOT/'build-live/vulkan-1.dll')
    receipt={'schema':'jali-windows-native-build-v1','sources':[{ 'project':n,'version':v,'archive_sha256':s} for n,v,s in SOURCES],'loader_sha256':hashlib.sha256(loader.read_bytes()).hexdigest(),'software_driver_opted_in':a.ci_software,'physical_hardware_acceptance':False}
    if a.ci_software:
        chrome=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Google/Chrome/Application'
        candidates=list(chrome.glob('**/vk_swiftshader.dll'))
        if not candidates:raise RuntimeError('Installed Chrome SwiftShader not found; no driver download or hardware fallback performed')
        driver=max(candidates,key=lambda f:f.stat().st_mtime);icd=ROOT/'.cache/runtime/windows-swiftshader.json';icd.parent.mkdir(parents=True,exist_ok=True)
        icd.write_text(json.dumps({'file_format_version':'1.0.0','ICD':{'library_path':str(driver),'api_version':'1.0.0'}},indent=2))
        if os.environ.get('GITHUB_ACTIONS')=='true':ci_driver_registration()
        receipt.update(driver_path=str(driver),driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),icd=str(icd))
        if os.environ.get('GITHUB_ENV'):
            with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as f:f.write(f'VK_ICD_FILENAMES={icd}\n')
        print(f'Explicit software ICD: {icd}; set VK_ICD_FILENAMES to this path for a local software test')
    dest=ROOT/'artifacts/windows-native';dest.mkdir(parents=True,exist_ok=True);(dest/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Native source build complete. Normal user runs retain their system hardware driver selection.')


if __name__=='__main__':main()
