#!/usr/bin/env bash
# ITC 531 — environment check.
#
# Run this in Module 1 and post the output in the Module 1 discussion. Run it again
# any time something stops working. It turns "it doesn't work" into a specific
# line of output.
#
#     bash scripts/doctor.sh
#
# It needs nothing but bash, so it works before anything else is set up.
#
# Exit codes:  0 = ready   1 = something needs fixing

set -uo pipefail

# Runs from anywhere: resolve everything relative to this script, not to your
# current directory. From module_N/scripts/doctor.sh that lands on
# module_N/ — this module's root — whichever directory you invoked it from.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1


PASS=0; WARN=0; FAIL=0
ok()   { printf '  \033[32m ok \033[0m %s\n' "$1"; PASS=$((PASS+1)); }
warn() { printf '  \033[33mwarn\033[0m %s\n' "$1"; WARN=$((WARN+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

COURSE="${COURSE:-531}"

echo "ITC ${COURSE} environment check — $(date -u '+%Y-%m-%d %H:%M UTC')"

# --------------------------------------------------------------- platform ---
head_ "Platform"
UNAME="$(uname -s)"
ARCH="$(uname -m)"
ok "os=${UNAME} arch=${ARCH}"
case "${ARCH}" in
  arm64|aarch64) ok "arm64 detected — every image this course pins publishes an arm64 variant" ;;
esac
if [[ "${UNAME}" == MINGW* || "${UNAME}" == CYGWIN* || "${UNAME}" == MSYS* ]]; then
  bad "you are in Git Bash or similar, not WSL2. Open a WSL2 (Ubuntu) terminal and re-run."
elif [[ "${UNAME}" == Linux* ]] && grep -qi microsoft /proc/version 2>/dev/null; then
  ok "running inside WSL2"
fi

# --------------------------------------------------------------- tooling ---
head_ "Course tooling"
# The course deliberately has no build tool and no task runner. Every command in
# the tutorials is one you would type at a real terminal, so the only things that
# need to be present are the real tools.
for tool in git unzip curl; do
  if command -v "${tool}" >/dev/null 2>&1; then
    ok "${tool}"
  else
    case "${tool}" in
      git)   warn "no 'git'. Needed from Module 2 onward for your project repository: sudo apt install -y git" ;;
      unzip) warn "no 'unzip'. Needed to extract the module folder: sudo apt install -y unzip" ;;
      curl)  warn "no 'curl'. Most tutorials test endpoints with it: sudo apt install -y curl" ;;
    esac
  fi
done

# ------------------------------------------------------------ container -----
head_ "Container engine"
if ! command -v docker >/dev/null 2>&1; then
  bad "no 'docker' command. Install Rancher Desktop and set Container Engine = dockerd (moby)."
else
  if ! docker info >/dev/null 2>&1; then
    bad "'docker' exists but the engine is not responding. Is Rancher Desktop running?"
  else
    ok "engine responding"
    SERVER="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo unknown)"
    ok "server version ${SERVER}"

    # Rancher Desktop can run containerd instead of moby. The course needs moby,
    # because containerd mode gives you nerdctl rather than a working `docker`.
    # docker info's output is captured first, not piped straight into grep -q:
    # grep -q exits the instant it matches and can SIGPIPE `docker info` before
    # it finishes writing, which under `pipefail` above made this warn falsely
    # on a container engine that was actually fine.
    DOCKER_INFO="$(docker info 2>/dev/null)"
    if grep -qi 'Server Version' <<< "${DOCKER_INFO}"; then
      ok "dockerd (moby) container engine"
    else
      warn "could not confirm the container engine is dockerd (moby)"
    fi

    if docker compose version >/dev/null 2>&1; then
      ok "compose v2: $(docker compose version --short 2>/dev/null)"
    else
      bad "'docker compose' (v2, with a space) not available. The course uses v2 exclusively."
    fi
    if command -v docker-compose >/dev/null 2>&1; then
      warn "the old 'docker-compose' v1 binary is also installed. Ignore it; every command in this course uses 'docker compose'."
    fi
  fi
fi

# --------------------------------------------------- this module ------------
# Each module is its own download, so this script only ever sees one of them.
# It checks that the folder it is sitting in is a complete one.
head_ "This module"
MISSING=""
for f in compose.yml Dockerfile requirements.txt app/main.py adapters/local.env; do
  [[ -e "${f}" ]] || MISSING+="${f} "
done
# The tutorial is named m<N>_tutorial.md (m1_tutorial.md, m2_tutorial.md, ...),
# matching every other file in the folder -- never the literal "TUTORIAL.md".
shopt -s nullglob
TUTORIALS=(m*_tutorial.md)
shopt -u nullglob
(( ${#TUTORIALS[@]} > 0 )) || MISSING+="m<N>_tutorial.md "
MODULE="$(grep -m1 -oE '^name: itc531m[0-9]+' compose.yml 2>/dev/null | grep -oE '[0-9]+$')"
if [[ -n "${MISSING}" ]]; then
  bad "this folder is incomplete — missing: ${MISSING}"
  bad "re-download this module's zip from Blackboard and unzip it again"
elif [[ -z "${MODULE}" ]]; then
  bad "compose.yml has no 'name: itc531m<N>' line — this is not an ITC ${COURSE} module folder"
else
  ok "module ${MODULE} is complete — 'docker compose up -d --wait' from here"
fi

# Other modules you have unzipped are none of this module's business, but a stack
# left running from one of them is the usual cause of a port collision.
RUNNING="$(docker ps --filter 'label=com.docker.compose.project' \
           --format '{{.Label "com.docker.compose.project"}}' 2>/dev/null \
           | grep -E '^itc531m[0-9]+$' | sort -u | grep -v "^itc531m${MODULE}$" || true)"
if [[ -n "${RUNNING}" ]]; then
  warn "another module is running: $(printf '%s ' ${RUNNING})— 'bash scripts/stop-all.sh' if a port is taken"
fi

# --------------------------------------------------- kubernetes toggle ------
head_ "Kubernetes toggle"
if command -v kubectl >/dev/null 2>&1 && kubectl cluster-info >/dev/null 2>&1; then
  if [[ "${COURSE}" == "531" ]]; then
    warn "Kubernetes is RUNNING. ITC 531 does not use it and it costs you about 1-1.5 GB of RAM.
        Rancher Desktop → Preferences → Kubernetes → untick 'Enable Kubernetes'.
        Leave it on if you are also taking ITC 532 this term."
  else
    ok "Kubernetes running (expected for ITC 532)"
  fi
else
  if [[ "${COURSE}" == "532" ]]; then
    bad "ITC 532 needs Kubernetes. Rancher Desktop → Preferences → Kubernetes → enable."
  else
    ok "Kubernetes off — correct for ITC 531"
  fi
fi

# --------------------------------------------------------------- memory -----
head_ "Memory"
MEM_MB=""
case "${UNAME}" in
  Linux)  MEM_MB=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo) / 1024 )) ;;
  Darwin) MEM_MB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 )) ;;
esac
if [[ -n "${MEM_MB}" ]]; then
  if   (( MEM_MB >= 15000 )); then ok "${MEM_MB} MB visible — comfortable"
  elif (( MEM_MB >=  7000 )); then warn "${MEM_MB} MB visible. Workable, but run one module's stack at a time — 'docker compose down --volumes' before starting the next."
  else bad "${MEM_MB} MB visible. The department baseline is 16 GB. Contact the instructor in Module 1, not Module 5."
  fi
fi

# ---------------------------------------------------------------- ports -----
head_ "Ports the course uses"
for spec in "8000:the app" "5432:postgres" "5672:amqp" "15672:broker UI" "9000:s3 endpoint" "9001:s3 console" "9090:prometheus" "3000:grafana"; do
  PORT="${spec%%:*}"; WHAT="${spec#*:}"
  if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    warn "port ${PORT} (${WHAT}) is already in use — stop whatever owns it, or override the mapping"
  elif command -v lsof >/dev/null 2>&1 && lsof -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    warn "port ${PORT} (${WHAT}) is already in use — stop whatever owns it, or override the mapping"
  fi
done
(( WARN == 0 )) && ok "no conflicts detected"

# ------------------------------------------------------------- filesystem ---
head_ "Working directory"
CWD="$(pwd)"
if [[ "${CWD}" == /mnt/[a-z]/* ]]; then
  bad "you are on a Windows drive mounted into WSL2 (${CWD}).
        File permissions and bind-mount performance both break here.
        Move this module to your Linux home:  cp -r . ~/itc531/ && cd ~/itc531/$(basename "${CWD}")
        Then reopen it in VS Code with 'code .' so the editor follows it."
else
  ok "${CWD}"
fi

# CRLF line endings are what you get when a file is edited from the Windows side
# rather than through the WSL extension. The failure is 'bash: \r: command not
# found', which names neither the file nor the cause.
CRLF=""
for f in scripts/*.sh compose.yml adapters/local.env; do
  [[ -f "$f" ]] || continue
  grep -qU $'\r' "$f" 2>/dev/null && CRLF+="$f "
done
if [[ -n "${CRLF}" ]]; then
  bad "these files have Windows line endings: ${CRLF}
        Something edited them from the Windows side. In VS Code, check the
        bottom-left corner says 'WSL: Ubuntu'; if it does not, close the window,
        then 'cd' here in a WSL terminal and run 'code .' to reopen it correctly.
        Re-download this module's zip to get clean copies."
else
  ok "line endings are LF"
fi

# ------------------------------------------------------------- editor -------
head_ "Editor"
if command -v code >/dev/null 2>&1; then
  ok "the 'code' command is on your PATH — 'code .' opens this folder"
elif [[ -n "${WSL_DISTRO_NAME:-}" ]] || [[ -r /proc/version && "$(cat /proc/version)" == *icrosoft* ]]; then
  warn "no 'code' command. Install VS Code and its WSL extension, then run 'code .' from here.
        Editing these files from the Windows side instead is the most common way to lose a day
        in this course — see 'Get Ready: Set Up Your Machine'."
elif [[ "${UNAME}" == "Darwin" ]]; then
  warn "no 'code' command. If you use VS Code: Command Palette (Shift-Cmd-P) ->
        \"Shell Command: Install 'code' command in PATH\". Any other editor is fine too."
else
  warn "no 'code' command on your PATH. Any editor works; the tutorials show VS Code."
fi

# ------------------------------------------------------------- adapters -----
head_ "Adapters"
shopt -s nullglob
for env_file in adapters/*.env; do
  [[ "$(basename "${env_file}")" == "TEMPLATE.env" ]] && continue
  NAME="$(basename "${env_file}" .env)"
  ENVKIND="$(grep -E '^ENVIRONMENT=' "${env_file}" | cut -d= -f2- | tr -d '"' || echo "")"
  if [[ "${ENVKIND}" != "local" ]] && grep -q 'local-development-secret' "${env_file}"; then
    bad "adapters/${NAME}.env is a cloud adapter but still carries the local development JWT secret. Generate a real one: openssl rand -base64 48"
  fi
  if [[ "${ENVKIND}" != "local" ]] && grep -qE 'IMAGE_REF=.*:latest' "${env_file}"; then
    bad "adapters/${NAME}.env pins an image tag of ':latest'. Use the git SHA."
  fi
  if [[ "${NAME}" != "local" && ! -f "adapters/${NAME}.sh" ]]; then
    warn "adapters/${NAME}.env exists but adapters/${NAME}.sh does not — write the adapter (module 6)"
  fi
  ok "adapter '${NAME}' present (${ENVKIND:-unset})"
done
if ! git check-ignore -q adapters/*.env 2>/dev/null; then
  [[ -d .git ]] && bad "adapters/*.env is NOT gitignored. Fix .gitignore before your next commit." \
                || warn "not a git repository yet — remember that adapters/*.env must never be committed"
fi

# ----------------------------------------------------- your check here ------
head_ "Student extension"
if [[ -x scripts/doctor.local.sh ]]; then
  # Module 1 assignment: add one check of your own. Anything that has bitten you.
  bash scripts/doctor.local.sh && ok "scripts/doctor.local.sh passed" || bad "scripts/doctor.local.sh failed"
else
  warn "scripts/doctor.local.sh not present — the Module 1 assignment asks you to write one"
fi

# --------------------------------------------------------------- summary ----
printf '\n\033[1mSummary\033[0m  %d ok, %d warn, %d fail\n' "${PASS}" "${WARN}" "${FAIL}"
if (( FAIL > 0 )); then
  echo "Not ready. Fix the FAIL lines above, then re-run. Post this output in the Module 1 discussion if you are stuck."
  exit 1
fi
echo "Ready. Paste this output into the Module 1 discussion."
exit 0
