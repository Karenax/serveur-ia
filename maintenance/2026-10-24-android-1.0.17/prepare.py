from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
path=ROOT/'client-android/app/build.gradle';text=path.read_text(encoding='utf-8');assert "versionName '1.0.16'" in text
path.write_text(text.replace("versionName '1.0.16'","versionName '1.0.17'").replace('versionCode 17','versionCode 18'),encoding='utf-8')
path=ROOT/'client-android/README.md';text=path.read_text(encoding='utf-8');path.write_text(text.replace('**1.0.16** (`versionCode=17`)','**1.0.17** (`versionCode=18`)'),encoding='utf-8')
previous=ROOT/'maintenance/2026-10-24-refresh-stability'
shutil.copy2(previous/'signature.txt',OUT/'previous-signature.txt')
shutil.copy2(previous/'key-fingerprints.json',OUT/'key-fingerprints.json')
text=(previous/'publish_android.py').read_text(encoding='utf-8').replace('1.0.16','1.0.17').replace("version_code']==17","version_code']==18").replace("versionCode='17'","versionCode='18'")
text=text.replace("assert 'conversationStatus' in html", "assert 'androidSharedError' in html\n        assert 'conversationStatus' in html")
(OUT/'publish.py').write_text(text,encoding='utf-8')
print('Android 1.0.17/code 18 prepared; existing signing identity required.')
