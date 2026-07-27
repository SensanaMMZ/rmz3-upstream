#!/bin/bash
# Download a branch's CI-built ROM and locate every byte that differs from
# retail. A failed `make compare` says only "did not match"; this says where.
#   rom_diff.sh <ci-branch>
set -u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BR="$1"
ID=$(python3 - "$BR" <<'PY'
import json,os,sys,urllib.request,urllib.parse
tok=os.environ['GITHUB_TOKEN']
def req(u): return urllib.request.urlopen(urllib.request.Request(u,headers={'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','User-Agent':'x'}))
r=json.load(req('https://api.github.com/repos/SensanaMMZ/rmz3-upstream/actions/runs?branch=%s&per_page=1'
                % urllib.parse.quote(sys.argv[1],safe='')))['workflow_runs'][0]
a=json.load(req(r['artifacts_url']))['artifacts']
print(a[0]['id'] if a else '')
PY
)
[ -z "$ID" ] && { echo "  no artifact"; exit 1; }
# curl, not urllib: the artifact URL 302s to blob storage which 401s on a
# forwarded Authorization header.
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/SensanaMMZ/rmz3-upstream/actions/artifacts/$ID/zip" -o "$S/rd.zip"
rm -rf "$S/rd"; mkdir -p "$S/rd"; (cd "$S/rd" && unzip -o -q ../rd.zip)
N=$(cmp -l ${RMZ3_FORK}/baseimg.gba "$S/rd/rmz3.gba" 2>/dev/null | wc -l)
echo "  differing bytes: $N"
cmp -l ${RMZ3_FORK}/baseimg.gba "$S/rd/rmz3.gba" 2>/dev/null \
  | head -6 | while read pos a b; do
      printf "    0x%X  retail 0x%02X  built 0x%02X\n" $((pos-1)) $((8#$a)) $((8#$b))
    done
