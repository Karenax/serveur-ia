from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
for name in ('client-qwen/updater.py','lanceur/operations.py','client-qwen/package.json','client-qwen/package-lock.json'):
    path=ROOT/name;s=path.read_text(encoding='utf-8');assert '3.5.42' in s;path.write_text(s.replace('3.5.42','3.5.43'),encoding='utf-8')
path=ROOT/'client-android/app/build.gradle';s=path.read_text(encoding='utf-8');assert "versionName '1.0.15'" in s;path.write_text(s.replace("versionName '1.0.15'","versionName '1.0.16'").replace('versionCode 16','versionCode 17'),encoding='utf-8')
path=ROOT/'client-android/README.md';s=path.read_text(encoding='utf-8');path.write_text(s.replace('**1.0.15** (`versionCode=16`)','**1.0.16** (`versionCode=17`)'),encoding='utf-8')
windows=(ROOT/'maintenance/2026-10-24-client-3.5.42/publish.py').read_text(encoding='utf-8').replace('3.5.42','3.5.43')
(OUT/'publish_windows.py').write_text(windows,encoding='utf-8')
android=(ROOT/'maintenance/2026-10-24-android-1.0.15/publish.py').read_text(encoding='utf-8').replace('1.0.15','1.0.16').replace("version_code']==16","version_code']==17").replace("versionCode='16'","versionCode='17'")
android=android.replace("'publication.json'","'android-publication.json'")
(OUT/'publish_android.py').write_text(android,encoding='utf-8')
previous=ROOT/'maintenance/2026-10-24-android-1.0.15'
shutil.copy2(previous/'signature.txt',OUT/'previous-signature.txt')
shutil.copy2(previous/'key-fingerprints.json',OUT/'key-fingerprints.json')
print('Prepared Windows 3.5.43 and Android 1.0.16, preserving signing identities.')
