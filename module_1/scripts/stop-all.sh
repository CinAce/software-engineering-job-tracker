#!/usr/bin/env bash
# Stop every ITC 531 module that is running, wherever you unzipped it, and remove
# its volumes.
#
#   bash scripts/stop-all.sh
#
# Useful when a module will not start with "port is already allocated", which
# almost always means another module is still running from a folder you are not
# standing in.
#
# It works by project name rather than by folder, because each module is its own
# download and you may have unzipped them anywhere. Every module's compose.yml
# begins `name: itc531m<N>`, so that prefix is the handle:
#
#   docker compose -p itc531m3 down --volumes --remove-orphans
#
# `-p` targets a project by name with no compose file involved, which is the only
# way to reach a stack whose folder you cannot see from here.
set -uo pipefail

command -v docker >/dev/null || { echo "docker not found — is Rancher Desktop running?" >&2; exit 1; }

# `docker compose ls` lists running projects. Fall back to reading the label off
# the containers themselves if this version of Compose does not have it.
PROJECTS="$(docker compose ls --all --format json 2>/dev/null \
            | grep -oE '"Name":"itc531m[0-9]+"' | grep -oE 'itc531m[0-9]+' | sort -u)"
if [[ -z "${PROJECTS}" ]]; then
  PROJECTS="$(docker ps -a --filter 'label=com.docker.compose.project' \
              --format '{{.Label "com.docker.compose.project"}}' 2>/dev/null \
              | grep -E '^itc531m[0-9]+$' | sort -u)"
fi

if [[ -z "${PROJECTS}" ]]; then
  echo "Nothing to stop — no ITC 531 module is running."
else
  for p in ${PROJECTS}; do
    printf 'stopping %s ... ' "${p}"
    if docker compose -p "${p}" down --volumes --remove-orphans >/dev/null 2>&1; then
      echo "done"
    else
      echo "failed — try it yourself: docker compose -p ${p} down --volumes"
    fi
  done
fi

# Volumes can outlive their project if a stack was removed with plain `down`.
ORPHANS="$(docker volume ls -q 2>/dev/null | grep -E '^itc531m[0-9]+_' || true)"
if [[ -n "${ORPHANS}" ]]; then
  echo
  echo "These volumes have no running stack and still hold data:"
  printf '%s\n' "${ORPHANS}" | sed 's/^/    /'
  echo
  echo "Remove them when you are sure you do not want what is in them:"
  echo "    docker volume rm ${ORPHANS//$'\n'/ }"
fi

echo
echo "Confirm with:"
echo "    docker ps"
echo "    docker volume ls | grep itc531"
