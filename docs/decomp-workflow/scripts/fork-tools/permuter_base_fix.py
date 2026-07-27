#!/usr/bin/env python3
# Make a decomp-permuter base.c parseable by pycparser AND compilable by agbcc,
# for this codebase's style. Run with NO --preserve-macros (so data macros like
# MOTION/LAYER expand and stay constant for the compiler); this script then:
#   - GNU colon designated-initializers  `field : value`  ->  `.field = value`
#     including several on one line (LAYER expands to `atkType: .., element : ..`)
#   - varargs function-pointer typedefs   `(...)`          ->  `(void)`
#   - deletes `extern char assertion[...]` lines (STATIC_ASSERT; compile-time
#     only, irrelevant to the permuted function's codegen)
# Skips anonymous/typed bitfields (`u8 x : 4;`), labels, `case`, and ternaries
# by only converting a `name :` that directly follows `{`, `,`, or line-start
# indentation, isn't a type/keyword, and is followed by a real value.
#
# Usage: python tools/permuter_base_fix.py nonmatchings/<Func>/base.c
import re, sys

SKIP = {
    "u8","u16","u32","u64","s8","s16","s32","s64","int","char","short","long",
    "unsigned","signed","void","float","double","bool","bool8","bool16","bool32",
    "vu8","vu16","vu32","vs8","vs16","vs32","size_t","case","default","struct",
    "union","enum","const","static","volatile","return","goto",
}

# delimiter ({ , or start-of-line indent), field name, colon, then a value
PAT = re.compile(r'([{,]\s*|^\s*)([A-Za-z_]\w*)\s*:[ \t]+(?=[^\s:])', re.MULTILINE)

def repl(m):
    if m.group(2) in SKIP:
        return m.group(0)
    return f"{m.group(1)}.{m.group(2)} = "

def fix(path):
    out = []
    for line in open(path, encoding="utf-8").read().split("\n"):
        if re.match(r'\s*extern char assertion\[', line):
            continue
        line = line.replace(")(...)", ")(void)")
        # apply repeatedly so multiple inits on one line all convert
        prev = None
        while prev != line:
            prev = line
            line = PAT.sub(repl, line, count=1)
        out.append(line)
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out))

if __name__ == "__main__":
    fix(sys.argv[1])
    print("fixed", sys.argv[1])
