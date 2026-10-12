"""Build a universal APK using Android SDK 35 and an ECJ Java compiler.
Set LUODI_TOOLCHAIN to an extracted toolchain containing android-35,
android-15 (SDK build-tools 35.0.0), and ecj.jar. No Gradle network is required.
"""
from pathlib import Path
import os, subprocess, zipfile, json, hashlib
from verify_apk import verify_resource_table
ROOT=Path(__file__).resolve().parent
T=Path(os.environ.get('LUODI_TOOLCHAIN',ROOT.parent/'toolchain')).resolve()
BT=T/'android-15'; JAR=T/'android-35/android.jar'; BUILD=ROOT/'build'; MAIN=ROOT/'app/src/main'
BUILD.mkdir(exist_ok=True);(BUILD/'classes').mkdir(exist_ok=True);(BUILD/'dex').mkdir(exist_ok=True)
def run(args):subprocess.run([str(x) for x in args],check=True,cwd=ROOT)
run([BT/'aapt','package','-f','-M',MAIN/'AndroidManifest.xml','-S',MAIN/'res','-A',MAIN/'assets','-I',JAR,'-F',BUILD/'resources.apk'])
run(['java','-jar',T/'ecj.jar','-8','-proc:none','-bootclasspath',JAR,'-d',BUILD/'classes',*sorted((MAIN/'java').rglob('*.java'))])
run([BT/'d8','--min-api','23','--lib',JAR,'--output',BUILD/'dex',*sorted((BUILD/'classes').rglob('*.class'))])
with zipfile.ZipFile(BUILD/'resources.apk') as src,zipfile.ZipFile(BUILD/'unsigned.apk','w',zipfile.ZIP_DEFLATED) as dst:
 # Keep aapt's entry compression settings. Android 11+ cannot install a
 # target-30+ APK with a compressed or unaligned resources.arsc table.
 for info in src.infolist():
  if info.filename=='resources.arsc':info.compress_type=zipfile.ZIP_STORED
  dst.writestr(info,src.read(info.filename))
 dst.write(BUILD/'dex/classes.dex','classes.dex')
run([BT/'zipalign','-f','-p','4',BUILD/'unsigned.apk',BUILD/'aligned.apk'])
KEY=ROOT/'signing/luodi-release.jks'
config_file=ROOT/'signing/credentials.json'
config=json.loads(config_file.read_text()) if config_file.exists() else {}
store_password=os.environ.get('LUODI_STORE_PASSWORD',config.get('store_password'))
key_password=os.environ.get('LUODI_KEY_PASSWORD',config.get('key_password',store_password))
key_alias=os.environ.get('LUODI_KEY_ALIAS',config.get('key_alias','luodi'))
if not KEY.exists() or not store_password or not key_password:
 raise SystemExit('Restore the original private signing/luodi-release.jks and credentials.json, or configure LUODI_STORE_PASSWORD and LUODI_KEY_PASSWORD. No replacement key is generated.')
# Pass passwords through the child environment, not process arguments or logs.
os.environ['LUODI_SIGN_STORE_PASSWORD']=store_password
os.environ['LUODI_SIGN_KEY_PASSWORD']=key_password
APK=ROOT/'Luodi-1.0.5.apk'
run([BT/'apksigner','sign','--ks',KEY,'--ks-key-alias',key_alias,'--ks-pass','env:LUODI_SIGN_STORE_PASSWORD','--key-pass','env:LUODI_SIGN_KEY_PASSWORD','--out',APK,BUILD/'aligned.apk'])
resource_check=verify_resource_table(APK)
run([BT/'zipalign','-c','4',APK])
run([BT/'apksigner','verify','--verbose',APK]);run([BT/'apksigner','verify','--min-sdk-version','33','--max-sdk-version','33',APK]);run([BT/'aapt','dump','badging',APK])
report={'apk':APK.name,'sha256':hashlib.sha256(APK.read_bytes()).hexdigest(),'bytes':APK.stat().st_size,'minAndroid':'6.0 (API 23)','targetSdk':34,'abi':'universal; no native libraries','resourceTable':resource_check,'android13SignatureVerification':'passed (API 33)','signing':'v1/v2/v3 signatures verified by Android SDK apksigner'}
(ROOT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
