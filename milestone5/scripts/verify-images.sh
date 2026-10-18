#!/usr/bin/env bash
# Confirm every pinned image still resolves, and publishes an arm64 variant.
# Run at the start of each term.
#
#   bash scripts/verify-images.sh
#
# The tags are read straight out of the compose file, so this checks what is
# actually used rather than a separate list that could drift from it.
#
# Works in two places, because there are two:
#   * inside an unzipped module_N/ — one compose.yml, this module's images
#   * across the eight module folders
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

FAIL=0
SOURCES=()
[[ -f compose.yml ]] && SOURCES+=(compose.yml)
for f in module*/compose.yml; do [[ -f "$f" ]] && SOURCES+=("$f"); done

if (( ${#SOURCES[@]} == 0 )); then
  echo "  FAIL no compose.yml here. Run this from an unzipped module folder," >&2
  echo "       or from the module folder." >&2
  exit 1
fi

mapfile -t REFS < <(grep -hoE '^\s+image:\s*\S+' "${SOURCES[@]}" | awk '{print $2}' | sort -u)
printf 'reading pins from: %s\n' "${SOURCES[*]}"

# A module whose only service is built from the Dockerfile — Module 1 is one —
# has no `image:` line at all. That is not an error: its base image is still
# pinned, and the Dockerfile check below is the one that matters for it.
if (( ${#REFS[@]} == 0 )); then
  echo "  --   no image: lines here; every service is built from the Dockerfile"
fi

for ref in "${REFS[@]}"; do
  if [[ "${ref}" == *:latest ]]; then
    printf '  FAIL %-46s moving tag\n' "${ref}"; FAIL=1; continue
  fi
  if [[ "${ref}" != *:* ]]; then
    printf '  FAIL %-46s no tag at all\n' "${ref}"; FAIL=1; continue
  fi
  if docker manifest inspect "${ref}" >/dev/null 2>&1; then
    ARCHES=$(docker manifest inspect "${ref}" 2>/dev/null \
      | grep -o '"architecture": *"[a-z0-9]*"' | sed 's/.*"\([a-z0-9]*\)"$/\1/' | sort -u | tr '\n' ' ')
    printf '  ok   %-46s [%s]\n' "${ref}" "${ARCHES}"
    grep -q arm64 <<<"${ARCHES}" || printf '  WARN %-46s no arm64 variant — Apple Silicon students will struggle\n' "${ref}"
  else
    printf '  FAIL %-46s does not resolve\n' "${ref}"; FAIL=1
  fi
done

# The Dockerfile's base image is pinned separately.
BASE=$(grep -oE '^ARG PYTHON_TAG=\S+' Dockerfile 2>/dev/null | cut -d= -f2)
if [[ -z "${BASE}" ]] && (( ${#REFS[@]} == 0 )); then
  echo "  FAIL nothing to check — no image: lines and no ARG PYTHON_TAG in the Dockerfile"
  FAIL=1
fi
if [[ -n "${BASE}" ]]; then
  if docker manifest inspect "python:${BASE}" >/dev/null 2>&1; then
    printf '  ok   %-46s [Dockerfile base]\n' "python:${BASE}"
  else
    printf '  FAIL %-46s does not resolve\n' "python:${BASE}"; FAIL=1
  fi
fi

exit "${FAIL}"
