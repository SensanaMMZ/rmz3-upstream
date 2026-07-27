#!/usr/bin/env python3
"""Rewrite `OBJECT_HDR;` -> `COLLISION_OBJECT_HDR;` in one file.

A separate script (not a bash heredoc) because heredocs have twice silently
mangled regex escapes into control characters in this session.
"""
import io
import re
import sys

p = sys.argv[1]
s = io.open(p, encoding='utf-8', errors='replace').read()
new, n = re.subn(r'^(\s*)OBJECT_HDR;', r'\1COLLISION_OBJECT_HDR;', s, flags=re.M)
if n:
    io.open(p, 'w', encoding='utf-8', newline='').write(new)
