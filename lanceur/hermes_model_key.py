"""Fixed native key_cmd helper: profile authentication, selected active model only."""
import json
import os
import re
import sys
import urllib.request
from urllib.parse import urlsplit


def main():
    try:
        model=sys.argv[1]
        # Standalone helper executes in the private Hermes environment.
        # Keep both negotiated request generations without importing Kiara.
        if len(sys.argv)!=3 or not re.fullmatch(r'fred-model-[a-f0-9]{24}',model) or not re.fullmatch(r'(?:v2_)?[a-f0-9]{32}',sys.argv[2]):raise ValueError()
        url=os.environ['FRED_PROVIDER_URL']; parsed=urlsplit(url)
        if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','::1'} or not parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path!='/v1/provider/credential':raise ValueError()
        request=urllib.request.Request(url,json.dumps({'model_id':model,'request_id':sys.argv[2]}).encode(),
            {'Authorization':'Bearer '+os.environ['FRED_INFERENCE_KEY'],'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=13) as response:value=json.loads(response.read(65536))
        if not isinstance(value.get('access_token'),str) or not value['access_token']:raise ValueError()
        print(json.dumps({'access_token':value['access_token'],'expires_in':1},separators=(',',':')))
    except Exception:raise SystemExit(1) from None


if __name__=='__main__':main()
