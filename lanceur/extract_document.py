"""Bounded document extraction subprocess, input is raw bytes on stdin."""
import json
import sys
from workspace import extract,MAX_FILE

if __name__=='__main__':
    try:result={'pages':extract(sys.argv[1],sys.stdin.buffer.read(MAX_FILE+1))}
    except Exception as error:result={'error':str(error)[:500]}
    sys.stdout.buffer.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))
