"""Offline package damage checks. NOT a signature or trusted update mechanism.

An attacker replacing both the manifest and payload defeats this check. Builds
remain unsigned/personal; never download replacement DLLs from random sites.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath

NAME='installation-manifest.json'
SCHEMA='jali-installation-integrity-v1'
REPAIR='Extract the entire original personal-build ZIP into a new empty folder, or rebuild from your trusted source checkout. Do not mix versions or download individual replacement DLLs.'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def safe_name(name):
    if not isinstance(name,str) or not name or len(name)>1024:return False
    p=PurePosixPath(name)
    return not p.is_absolute() and p.as_posix()==name and all(c not in name for c in '\\:\x00<>"|?*') and all(part not in ('.','..') and part.rstrip(' .')==part for part in p.parts)


def link(path):
    return path.is_symlink() or bool(getattr(path.lstat(),'st_file_attributes',0)&0x400)


def inventory(root):
    result={};seen=set()
    for path in sorted(root.rglob('*')):
        name=path.relative_to(root).as_posix()
        if link(path):raise ValueError(f'Links/reparse points are not supported: {name}')
        if path.is_dir():continue
        if name==NAME:continue
        if not path.is_file() or not safe_name(name):raise ValueError(f'Unsupported installation path: {name}')
        if name.casefold() in seen:raise ValueError(f'Case-colliding installation path: {name}')
        seen.add(name.casefold());result[name]={'size':path.stat().st_size,'sha256':digest(path)}
    return result


def create_manifest(root):
    root=Path(root).resolve();files=inventory(root)
    if not files or len(files)>20000:raise ValueError('Installation must contain 1-20000 regular files')
    manifest={'schema':SCHEMA,'authenticity_verified':False,'files':files}
    (root/NAME).write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return manifest


def verify_installation(root):
    root=Path(root).resolve();issues=[];checked=0;total=0
    try:
        mf=root/NAME
        if link(mf) or mf.stat().st_size>8*1024*1024:raise ValueError('Invalid installation manifest file')
        manifest=json.loads(mf.read_text(encoding='utf-8'))
        if manifest.get('schema')!=SCHEMA:raise ValueError('Unsupported installation manifest schema')
        expected=manifest.get('files')
        if not isinstance(expected,dict) or not 1<=len(expected)<=20000:raise ValueError('Invalid installation file inventory')
        folded=set()
        # Validate ALL entries before touching a payload path, including on POSIX.
        for name,entry in expected.items():
            if not safe_name(name) or name==NAME or name.casefold() in folded:raise ValueError('Unsafe or duplicate manifest path')
            folded.add(name.casefold())
            if not isinstance(entry,dict) or type(entry.get('size')) is not int or entry['size']<0 or not isinstance(entry.get('sha256'),str) or len(entry['sha256'])!=64 or any(c not in '0123456789abcdef' for c in entry['sha256']):raise ValueError('Invalid manifest file digest/size')
        # Inspect parents as well as leaves; never hash through a junction/link.
        actual=set()
        for path in root.rglob('*'):
            name=path.relative_to(root).as_posix()
            if link(path):raise ValueError(f'Linked/reparse-point installation path: {name}')
            if path.is_file() and name!=NAME:actual.add(name)
        for name in sorted(actual-set(expected)):issues.append({'kind':'unexpected','file':name})
        for name,entry in expected.items():
            file=root/name
            if name not in actual:issues.append({'kind':'missing','file':name});continue
            checked+=1;size=file.stat().st_size;total+=size
            if size!=entry['size'] or digest(file)!=entry['sha256']:issues.append({'kind':'modified','file':name})
    except (OSError,ValueError,TypeError,AttributeError) as e:issues.append({'kind':'manifest-or-access','detail':str(e)})
    return {'schema':'jali-installation-check-v1','verified':not issues,'authenticity_verified':False,'checked_files':checked,'checked_bytes':total,'issue_count':len(issues),'issues':issues[:20],'repair':REPAIR if issues else None,'limits':'Offline integrity check only; not code signing, malware scanning, redistribution clearance or a physical laptop benchmark.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);a=p.parse_args();report=verify_installation(a.root);print(json.dumps(report,indent=2));return 0 if report['verified'] else 2


if __name__=='__main__':raise SystemExit(main())
