"""Build a plugin from an explicit list of public sources."""
import hashlib
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parent
PUBLIC_FILES = ('plugin.toml', 'plugin.py', 'service.py', 'evidence.py',
                'bdsp_connect.py', 'README.md', 'NOTICE.md', 'LICENSE')

def main():
    version = tomllib.loads((ROOT/'plugin.toml').read_text(encoding='utf-8'))['version']
    output = ROOT/'dist'/f'BDSP-Diglett-Experimental-{version}.pokeplugin'
    for name in PUBLIC_FILES:
        if not (ROOT/name).is_file(): raise FileNotFoundError(name)
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in PUBLIC_FILES: archive.write(ROOT/name, name)
    output.with_suffix('.pokeplugin.sha256').write_text(
        hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n', encoding='ascii')
    print(output)
    return output

if __name__ == '__main__': main()
