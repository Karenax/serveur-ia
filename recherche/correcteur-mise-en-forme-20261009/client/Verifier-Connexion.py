"""Read-only API connectivity check using a personalized EXE's WireGuard profile."""
import argparse
import json
from pathlib import Path
import struct
from client import Remote

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('exe',type=Path)
    parser.add_argument('--local-test',action='store_true')
    args=parser.parse_args()
    with args.exe.open('rb') as source:
        source.seek(-16,2);footer=source.read(16)
        assert footer[4:]==b'QWENPROFILE1'
        size=struct.unpack('<I',footer[:4])[0]
        assert 1<=size<=65536
        source.seek(-16-size,2);profile=json.loads(source.read(size))
    if args.local_test:
        port=profile['wireguard']['endpoint'].rsplit(':',1)[1]
        profile['wireguard']['endpoint']='127.0.0.1:'+port
    remote=Remote(profile)
    try:print(json.dumps(remote.check(),ensure_ascii=False))
    finally:remote.close()

if __name__=='__main__':main()
