#!/bin/bash
# Push a scratch branch that carries the CI workflow, so a PR branch can be
# build-verified without the workflow appearing in the PR itself.
#
# A branch only gets a CI run if .github/workflows/build.yml exists ON that
# branch. upstream/dev does not have it yet (that is PR #77), so every branch
# cut from dev is invisible to CI. Cherry-picking the workflow onto the PR
# branch would work but would put an unrelated file in the diff the maintainer
# reviews. So: ci/<name> = <branch> + the workflow commit, pushed separately.
#
#   ci_verify.sh <local-branch> [<local-branch> ...]
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
TOK=$(powershell.exe -NoProfile -Command \
      "[Environment]::GetEnvironmentVariable('GITHUB_TOKEN','User')" | tr -d '\r\n')
AUTH="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$TOK" | base64 -w0)"

for b in "$@"; do
  # Include the source prefix. `ci/$(basename)` collides: port/tretista and
  # reb/tretista both became ci/tretista, so a cluster test silently
  # overwrote a PR branch's verification and the PR then read as failing.
  name="ci/$(echo "$b" | tr "/" "-")"
  git diff --quiet || { echo "  ABORT: dirty tree"; exit 1; }
  git checkout -q -B "$name" "$b" 2>/dev/null
  if [ "$(git rev-parse --abbrev-ref HEAD)" != "$name" ]; then
    echo "  ABORT $b"; git checkout -q "$b"; continue
  fi

  # COPY the workflow files rather than cherry-picking the commit. build-fixes
  # has more than one commit touching build.yml now, so cherry-picking just the
  # tip conflicts against a branch that has no build.yml at all. Taking the
  # files at their current state is what we actually want and cannot conflict.
  git checkout contrib/build-fixes -- .github/workflows/build.yml tools/preproc/io.cpp 2>/dev/null
  git add -A .github tools/preproc 2>/dev/null
  git -c user.name="SensanaMMZ" \
      -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
      commit -q -m "CI harness for verification (not part of the PR)" 2>/dev/null

  git -c http.extraheader="$AUTH" push -q -f prfork "$name" && echo "  pushed $name"

  # ALWAYS return to the branch we came from, on every path. Leaving HEAD on the
  # scratch ci/ branch means the next round of fixes gets committed THERE
  # instead of on the PR branch -- two commits went astray that way before
  # anyone noticed, and the PR branch silently kept shipping the broken tree.
  git checkout -q "$b"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "$b" ] || echo "  WARNING: could not return to $b"
done
