#!/usr/bin/env python3
"""Open a PR against mmzret/rmz3 from a SensanaMMZ fork branch.

`gh` is not installed in this environment, so talk to the REST API directly.
PRs on this project target the upstream `dev` branch, not `main` -- basing on
main produces a 560-file diff because the fork has diverged.

usage: open_pr.py <head-branch> <title> <body-file>
"""
import json
import os
import sys
import urllib.error
import urllib.request

REPO = 'mmzret/rmz3'
OWNER = 'SensanaMMZ'
BASE = 'dev'


def api(path, payload=None, method=None):
    tok = os.environ['GITHUB_TOKEN']
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        'https://api.github.com' + path, data=data, method=method,
        headers={'Authorization': 'Bearer ' + tok,
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json',
                 'User-Agent': 'rmz3-contrib'})
    return json.load(urllib.request.urlopen(req))


def main():
    head, title, body_file = sys.argv[1], sys.argv[2], sys.argv[3]
    body = open(body_file, encoding='utf-8').read()

    existing = api('/repos/%s/pulls?state=open&head=%s:%s' % (REPO, OWNER, head))
    if existing:
        print('PR already open for %s: #%d' % (head, existing[0]['number']))
        return 0

    try:
        pr = api('/repos/%s/pulls' % REPO, {
            'title': title, 'body': body,
            'head': '%s:%s' % (OWNER, head), 'base': BASE,
        })
    except urllib.error.HTTPError as e:
        print('FAILED (%d): %s' % (e.code, e.read().decode()[:400]))
        return 1
    print('opened #%d  %s' % (pr['number'], pr['html_url']))
    print('   %d file(s), +%d -%d' % (pr['changed_files'], pr['additions'],
                                      pr['deletions']))
    return 0


sys.exit(main())
