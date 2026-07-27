"""Publish a holdout to decomp.me automatically.

Builds the target asm from an .inc (or takes a prepared .s), posts a scratch
via the API, and prints the scratch URL + the claim URL (so you can attach it
to your decomp.me account in one click).

Usage:
  python3 tools/scratch_up.py --inc asm/enemy/foo.inc --fn Foo_Update \
      --source notes/decompme/foo_source.c --context notes/decompme/foo_context.h \
      [--desc-file notes/decompme/foo_ask.md] [--name "Foo_Update"]

  # NOTE anonymous scratches EXPIRE if never claimed (JxrgW lesson) -- claim right away
  # or with an already-prepared target .s (must contain `glabel <fn>`):
  python3 tools/scratch_up.py --target notes/decompme/beetank_target.s --fn Beetank_Update ...

Notes:
- Use www.decomp.me (the bare domain is Cloudflare-walled for scripts) and a
  browser User-Agent.
- Scratches are created anonymous; the printed claim URL binds one to your
  account while logged in.
- The description PATCH is rejected (403) for anonymous scratches: claim the
  scratch first, then paste the ask into the About tab (or re-run the PATCH
  with your session cookie).
- Anything posted here is PUBLIC. Do not include private or unshared material.
"""
import argparse, io, json, os, re, sys, urllib.request

BASE = 'https://www.decomp.me'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
FLAGS = '-mthumb-interwork -Wimplicit -Wparentheses -O2 -fshort-enums'


def target_from_inc(inc_path, fn):
    """Extract one function from a project .inc and format it for decomp.me."""
    lines = io.open(inc_path, encoding='utf-8', errors='replace').read().split('\n')
    start = None
    for i, ln in enumerate(lines):
        m = re.match(r'\s*thumb_func_start (\S+)', ln)
        if m:
            if m.group(1) == fn:
                start = i
            elif start is not None:
                lines = lines[start:i]
                break
    else:
        if start is None:
            raise SystemExit('function %s not found in %s' % (fn, inc_path))
        lines = lines[start:]
    body = '\n'.join(lines)
    body = re.sub(r'\s*thumb_func_start (\S+)', r'glabel \1', body)
    return '.syntax unified\n.thumb\n' + body + '\n'


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                 'User-Agent': UA}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inc')
    ap.add_argument('--target')
    ap.add_argument('--fn', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--context', default=None)
    ap.add_argument('--desc-file', default=None)
    ap.add_argument('--name', default=None)
    ap.add_argument('--flags', default=FLAGS)
    a = ap.parse_args()

    if a.target:
        tgt = io.open(a.target, encoding='utf-8').read()
    elif a.inc:
        tgt = target_from_inc(a.inc, a.fn)
    else:
        raise SystemExit('need --inc or --target')

    payload = {
        'compiler': 'agbcc',
        'platform': 'gba',
        'compiler_flags': a.flags,
        'name': a.name or a.fn,
        'target_asm': tgt,
        'source_code': io.open(a.source, encoding='utf-8').read(),
        'context': io.open(a.context, encoding='utf-8').read() if a.context else '',
        'diff_label': a.fn,
    }
    d = post('/api/scratch', payload)
    # NOTE: success=False is a FAILURE — never hand out a claim link for a
    # scratch that does not compile server-side (2026-07-25 lesson).
    slug = d['slug']

    if a.desc_file:
        desc = io.open(a.desc_file, encoding='utf-8').read()
        req = urllib.request.Request(
            '%s/api/scratch/%s' % (BASE, slug),
            data=json.dumps({'description': desc}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                     'User-Agent': UA}, method='PATCH')
        try:
            urllib.request.urlopen(req, timeout=60)
            print('description set')
        except Exception as e:
            print('description PATCH failed (%s) — paste it in the About tab' % e)

    # compile once so the scratch shows a score immediately
    try:
        c = post('/api/scratch/%s/compile' % slug, {})
        print('compiled: success=%s' % c.get('success'))
        if not c.get('success'):
            print('*** SCRATCH DOES NOT COMPILE — fix the context and re-post')
            print('*** before sharing the claim link (see notes/decompme/fixes/).')
            for ln in (c.get('compiler_output') or '').splitlines()[:6]:
                print('   |', ln)
    except Exception as e:
        print('compile probe skipped (%s)' % e)

    print('scratch: %s/scratch/%s' % (BASE, slug))
    tok = d.get('claim_token')
    if tok:
        print('claim  : %s/scratch/%s/claim?token=%s' % (BASE, slug, tok))
        print('(open the claim link while logged in to attach it to your account)')


main()
