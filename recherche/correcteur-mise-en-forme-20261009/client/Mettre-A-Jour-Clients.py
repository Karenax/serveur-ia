"""Repackage existing personal clients, preserving their access and pinned keys."""
from pathlib import Path
import json
import struct
import sys
import shutil

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'lanceur'))
from core import read_json
from wireguard_access import network_routes
from wg_bridge import validate_profile

def read_exe_profile(path):
    with path.open('rb') as source:
        source.seek(-16,2);footer=source.read(16)
        if footer[4:]!=b'QWENPROFILE1':raise ValueError('Profil personnel absent.')
        size=struct.unpack('<I',footer[:4])[0]
        if not 1<=size<=65536:raise ValueError('Profil personnel invalide.')
        source.seek(-16-size,2);profile=json.loads(source.read(size))
    return validate_profile(profile)

def main():
    from releases import repackage
    print(repackage(root/'lanceur')['message'])

if __name__=='__main__':main()
