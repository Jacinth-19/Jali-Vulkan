"""Explicit x64 analyzer profiles; no download or execution on import."""
import platform
import sys
from pathlib import Path

from runtime_paths import ASSET_ROOT as ROOT
PROFILES = {
    'linux': {'platform':'linux-x64','cache':'rhubarb','executable':'rhubarb','format':'tar',
        'marker':'package/.tools/rhubarb-Lip-Sync-1.13.0-Linux/',
        'url':'https://registry.npmjs.org/rhubarb-lip-sync/-/rhubarb-lip-sync-0.0.1-alfa-3.tgz',
        'archive_sha256':'d797623611a61b7e0c7f2c2e6f4c5c79eec2325f4447c6aaebb037083c082239',
        'binary_sha256':'03e82c9c76c4e691a058f38a9cf7e75331e2f3c31a9c1fab90c00944b3ef7dc2'},
    'win32': {'platform':'windows-x64','cache':'rhubarb-windows','executable':'rhubarb.exe','format':'zip',
        'marker':'Rhubarb-Lip-Sync-1.13.0-Windows/',
        'url':'https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/Rhubarb-Lip-Sync-1.13.0-Windows.zip',
        'archive_sha256':'189ac55dae253dba3994d4075b8375b615f255759c105c7ed21bd88ad7728386',
        'binary_sha256':'d31a3030bcb11c39c175cdba45f8152456d7d2a288a8198b820f3b8c4f37ab2b'},
}


def analyzer_profile(system=None, machine=None):
    system = sys.platform if system is None else system
    machine = platform.machine() if machine is None else machine
    if system not in PROFILES or machine.lower() not in ('amd64','x86_64'):
        raise ValueError('Local analyzer supports x64 Windows/Linux only; no platform fallback')
    return dict(PROFILES[system])


def analyzer_path():
    spec = analyzer_profile()
    return ROOT / '.cache/lipsync' / spec['cache'] / spec['executable']


def archive_relative(name, spec):
    """Return an allowlisted, portable path or refuse traversal before filtering."""
    from pathlib import PurePosixPath
    if '\\' in name or ':' in name or name.startswith('/') or '..' in PurePosixPath(name).parts:
        raise ValueError('Unsafe analyzer archive path')
    if not name.startswith(spec['marker']):
        return None
    relative = name[len(spec['marker']):]
    if relative == spec['executable'] or relative.startswith('res/') or relative in ('LICENSE.md','README.adoc','CHANGELOG.md'):
        return relative or None
    return None
