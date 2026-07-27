#!/usr/bin/env python3
"""Put back regex escapes that a shell heredoc turned into control characters.

Patching these scripts through `python3 - <<'PY'` blocks is fine until the
payload contains a regex escape: `\\b` reached the file as a literal backspace
(0x08), so `[\\w \\*]*\\b(\\w+)` became `[\\w \\*]*<BS>(\\w+)` and matched
nothing at all -- silently, because the caller redirected stderr. Same hazard as
the earlier `\\n` that became a real newline inside a string literal.
"""
import glob
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BAD = {'\b': r'\b', '\f': r'\f', '\v': r'\v', '\a': r'\a'}

fixed = 0
for path in glob.glob(os.path.join(HERE, '*.py')):
    if os.path.basename(path) == 'repair_escapes.py':
        continue
    with io.open(path, encoding='utf-8') as fh:
        text = fh.read()
    hits = [c for c in BAD if c in text]
    if not hits:
        continue
    for c in hits:
        text = text.replace(c, BAD[c])
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    print('  repaired %s (%d escape type(s))'
          % (os.path.basename(path), len(hits)))
    fixed += 1

print('files repaired: %d' % fixed)
