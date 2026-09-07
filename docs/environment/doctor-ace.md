ITC 531 environment check — 2026-09-07 00:17 UTC

[1mPlatform[0m
  [32m ok [0m os=Darwin arch=arm64
  [32m ok [0m arm64 detected — every image this course pins publishes an arm64 variant

[1mCourse tooling[0m
  [32m ok [0m git
  [32m ok [0m unzip
  [32m ok [0m curl

[1mContainer engine[0m
  [32m ok [0m engine responding
  [32m ok [0m server version 29.7.2
  [32m ok [0m dockerd (moby) container engine
  [32m ok [0m compose v2: 5.5.0
  [33mwarn[0m the old 'docker-compose' v1 binary is also installed. Ignore it; every command in this course uses 'docker compose'.

[1mThis module[0m
  [32m ok [0m module 1 is complete — 'docker compose up -d --wait' from here

[1mKubernetes toggle[0m
  [32m ok [0m Kubernetes off — correct for ITC 531

[1mMemory[0m
  [32m ok [0m 24576 MB visible — comfortable

[1mPorts the course uses[0m
  [33mwarn[0m port 8000 (the app) is already in use — stop whatever owns it, or override the mapping

[1mWorking directory[0m
  [32m ok [0m /Users/ace/software-engineering-job-tracker
  [32m ok [0m line endings are LF

[1mEditor[0m
  [33mwarn[0m no 'code' command. If you use VS Code: Command Palette (Shift-Cmd-P) ->
        "Shell Command: Install 'code' command in PATH". Any other editor is fine too.

[1mAdapters[0m
  [32m ok [0m adapter 'local' present (local)
  [31mFAIL[0m adapters/*.env is NOT gitignored. Fix .gitignore before your next commit.

[1mStudent extension[0m
  [33mwarn[0m scripts/doctor.local.sh not present — the Module 1 assignment asks you to write one

[1mSummary[0m  15 ok, 4 warn, 1 fail
Not ready. Fix the FAIL lines above, then re-run. Post this output in the Module 1 discussion if you are stuck.
