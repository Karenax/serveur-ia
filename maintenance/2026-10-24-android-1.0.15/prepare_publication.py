from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
previous=root/'maintenance/2026-10-24-android-1.0.14'
for name,source in [('previous-signature.txt','signature.txt'),('key-fingerprints.json','key-fingerprints.json')]:
    shutil.copy2(previous/source,out/name)
script=(previous/'publish.py').read_text(encoding='utf-8')
script=script.replace('1.0.14','1.0.15').replace("version_code']==15","version_code']==16").replace("versionCode='15'","versionCode='16'")
script=script.replace("names=archive.namelist()", "names=archive.namelist()\n        html=archive.read('assets/android-chat.html').decode('utf-8')\n        assert 'conversationStatus' in html and 'voice-title' in html and 'Low · écoute sur cet appareil' in html\n        assert 'conversation.js' in archive.read('assets/ui-package.json').decode('utf-8')")
(out/'publish.py').write_text(script,encoding='utf-8')
print('Publication prepared; existing Android signing identity is required.')
