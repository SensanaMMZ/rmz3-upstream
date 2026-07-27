import os
"""Split the declared holdouts into the two populations that need different work.

A function marked NON_MATCH/NAKED is either:
  * reconstructed -- it has a `#if MODERN` C body, so it is an objdiff/permuter
    target and the ranking's match% means something; or
  * a pure INCCODE stub -- no C at all, so it needs source reconstruction first
    (this is what the Ghidra harness in tools/ghidra/ is for).

Writes notes/holdouts-withc.md and notes/holdouts-pure.md.
Usage: python3 tools/classify_holdouts.py
"""
import collections, io, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECL = re.compile(r'^(NON_MATCH|NAKED)\b')


def body_of(path, lineno, maxlines=600):
    """Text of the function starting at lineno, by brace balance."""
    lines = io.open(path, encoding='utf-8', errors='replace').read().split('\n')
    depth, out, started = 0, [], False
    for l in lines[lineno - 1:lineno - 1 + maxlines]:
        out.append(l)
        depth += l.count('{') - l.count('}')
        if '{' in l:
            started = True
        if started and depth <= 0:
            break
    return out


def main():
    os.chdir(REPO)
    raw = subprocess.run(['git', 'grep', '-n', '-E', r'^(NON_MATCH|NAKED)\b',
                          '--', 'src/*.c', 'src/**/*.c'],
                         capture_output=True).stdout.decode('utf-8', 'replace')
    rows = [r for r in raw.split('\n') if r.strip()]
    withc, pure = [], []
    for r in rows:
        f, ln, _ = r.split(':', 2)
        body = body_of(f, int(ln))
        sig = body[0].strip().rstrip('{').strip()
        (withc if re.search(r'#if\s+MODERN', '\n'.join(body)) else pure).append(
            (f, int(ln), sig, len(body)))

    for path, rowset, title, blurb in (
        ('notes/holdouts-withc.md', withc,
         'Holdouts with a reconstructed C body',
         'These have a `#if MODERN` body, so `tools/objdiff_rank.sh` gives a\n'
         'meaningful match%% for them and the permuter has something to chew on.'),
        ('notes/holdouts-pure.md', pure,
         'Holdouts that are pure INCCODE stubs',
         'No C body at all -- these need source reconstruction before any\n'
         'matching work can start. This is what the Ghidra harness is for; see\n'
         '`tools/ghidra/symbolize_rom.md`.'),
    ):
        by_file = collections.Counter(f for f, _, _, _ in rowset)
        with io.open(os.path.join(REPO, path), 'w', encoding='utf-8',
                     newline='\n') as w:
            w.write(u'# %s (%d)\n\n%s\n\n' % (title, len(rowset), blurb))
            w.write(u'Regenerate with `python3 tools/classify_holdouts.py`.\n\n')
            w.write(u'## By file\n\n| file | count |\n|---|---|\n')
            for f, n in by_file.most_common():
                w.write(u'| %s | %d |\n' % (f, n))
            w.write(u'\n## All\n\n| location | signature |\n|---|---|\n')
            for f, ln, sig, _ in sorted(rowset):
                w.write(u'| %s:%d | `%s` |\n' % (f, ln, sig.replace('|', '\\|')))
        print('%-28s %4d -> %s' % (title.split()[0], len(rowset), path))

    print('\n%d declared holdouts: %d reconstructed, %d pure stubs'
          % (len(rows), len(withc), len(pure)))


main()
