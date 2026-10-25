from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
for name in ('client-qwen/updater.py','lanceur/operations.py','client-qwen/package.json','client-qwen/package-lock.json'):
    path=ROOT/name;text=path.read_text(encoding='utf-8');assert '3.5.43' in text;path.write_text(text.replace('3.5.43','3.5.44'),encoding='utf-8')
path=ROOT/'client-android/app/build.gradle';text=path.read_text(encoding='utf-8');assert "versionName '1.0.17'" in text;path.write_text(text.replace("versionName '1.0.17'","versionName '1.0.18'").replace('versionCode 18','versionCode 19'),encoding='utf-8')
path=ROOT/'client-android/README.md';text=path.read_text(encoding='utf-8');path.write_text(text.replace('**1.0.17** (`versionCode=18`)','**1.0.18** (`versionCode=19`)'),encoding='utf-8')
prior=ROOT/'maintenance/2026-10-24-refresh-stability'
text=(prior/'publish_windows.py').read_text(encoding='utf-8').replace('3.5.43','3.5.44')
(OUT/'publish_windows.py').write_text(text,encoding='utf-8')
priorAndroid=ROOT/'maintenance/2026-10-24-android-1.0.17'
text=(priorAndroid/'publish.py').read_text(encoding='utf-8').replace('1.0.17','1.0.18').replace("version_code']==18","version_code']==19").replace("versionCode='18'","versionCode='19'")
text=text.replace("assert 'androidSharedError' in html", "assert 'classicLowSpeak' in html and 'classicLowRefresh' in html\n        assert 'androidSharedError' in html")
(OUT/'publish_android.py').write_text(text,encoding='utf-8')
shutil.copy2(priorAndroid/'signature.txt',OUT/'previous-signature.txt')
shutil.copy2(priorAndroid/'key-fingerprints.json',OUT/'key-fingerprints.json')
print('Prepared Windows 3.5.44 and Android 1.0.18; existing keys retained.')
