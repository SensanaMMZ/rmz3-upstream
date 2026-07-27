#!/bin/bash
# Print why a ci/<branch> run failed -- the lines just before the error marker.
# Downloading and unzipping the log by hand every time was costing a round trip
# per failure, and the interesting part is always the same five lines.
set -u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SW=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)
export GITHUB_TOKEN=$(powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('GITHUB_TOKEN','User')" | tr -d '\r')

for b in "$@"; do
  echo "=== $b"
  id=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
    "https://api.github.com/repos/SensanaMMZ/rmz3-upstream/actions/runs?branch=ci/$b&per_page=1" \
    | python3 -c "import sys,json; w=json.load(sys.stdin)['workflow_runs']; print(w[0]['id'] if w else '')")
  [ -n "$id" ] || { echo "  no run"; continue; }
  curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
    "https://api.github.com/repos/SensanaMMZ/rmz3-upstream/actions/runs/$id/logs" -o "$S/ci_log.zip"
  python3 -c "
import zipfile
z = zipfile.ZipFile(r'$SW\ci_log.zip')
n = [x for x in z.namelist() if x.startswith('0_')]
t = z.read(n[0]).decode('utf-8', 'replace')
L = [l[29:] for l in t.splitlines()]
i = [k for k, l in enumerate(L) if l.startswith('##[error]')]
print('\n'.join('  ' + x[:150] for x in L[max(0, i[0]-4):i[0]]) if i else '  no error marker')
"
done
