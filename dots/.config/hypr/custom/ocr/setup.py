#!/usr/bin/env python3
"""One-time isolated CPU environment and verified model downloads. No system Python writes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

HERE=Path(__file__).resolve().parent
DEFAULT=Path.home()/'.local/share/rdp-screen-ocr'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=Path,default=DEFAULT);args=parser.parse_args()
    directory=args.data_dir;directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    python=directory/'venv/bin/python'
    if not python.exists():subprocess.run(['uv','venv','--python','3.12',str(directory/'venv')],check=True)
    subprocess.run(['uv','pip','install','--python',str(python),'-r',str(HERE/('requirements.lock' if (HERE/'requirements.lock').exists() else 'requirements.txt'))],check=True)
    models=directory/'models';models.mkdir(exist_ok=True)
    for entry in json.loads((HERE/'models.json').read_text()).values():
        target=models/entry['file']
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==entry['sha256']:
            print('Verified',target.name);continue
        with tempfile.NamedTemporaryFile(dir=models,delete=False) as stream:
            temp=Path(stream.name)
            try:
                with urllib.request.urlopen(entry['url'],timeout=60) as response:shutil.copyfileobj(response,stream)
                stream.flush()
                if hashlib.sha256(temp.read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Model checksum mismatch: '+entry['file'])
                temp.replace(target)
            finally:temp.unlink(missing_ok=True)
        print('Downloaded and verified',target.name,target.stat().st_size,'bytes')
    subprocess.run(['uv','pip','freeze','--python',str(python)],check=True,stdout=(directory/'installed-requirements.txt').open('w'))
    print('Ready:',directory)

if __name__=='__main__':main()
