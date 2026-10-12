"""Download the pinned official SDK tools and ECJ compiler, then build Luodi.
Prerequisites: Python 3 and a Java 17 runtime with keytool.
"""
from pathlib import Path
import json,hashlib,urllib.request,zipfile,subprocess,os
ROOT=Path(__file__).resolve().parent
T=Path(os.environ.get('LUODI_TOOLCHAIN',ROOT.parent/'toolchain')).resolve()
T.mkdir(exist_ok=True,parents=True)
for entry in json.loads((ROOT/'toolchain-lock.json').read_text()):
 p=T/entry['file']
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:
  print('Downloading',entry['file']);urllib.request.urlretrieve(entry['url'],p)
 if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Checksum mismatch: '+p.name)
 if p.suffix=='.zip':
  with zipfile.ZipFile(p) as z:z.extractall(T)
for name in ['aapt','aapt2','d8','zipalign','apksigner']:(T/'android-15'/name).chmod(0o755)
env=dict(os.environ,LUODI_TOOLCHAIN=str(T))
subprocess.run(['python3',str(ROOT/'build.py')],env=env,check=True)
