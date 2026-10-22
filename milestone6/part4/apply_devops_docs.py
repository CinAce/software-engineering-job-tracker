#!/usr/bin/env python3
"""Idempotently add DevOps-owned Part 6 documentation to root README.md.
Preserves existing content, including the teammate's CI/OIDC section.
"""
from pathlib import Path
root = Path('README.md')
section = Path('milestone6/part4/README_DEVOPS_SECTION.md').read_text().strip()
start = '<!-- BEGIN M6 DEVOPS OWNER SECTION -->'
end = '<!-- END M6 DEVOPS OWNER SECTION -->'
if not root.exists():
    raise SystemExit('Run from the project repository root (README.md missing)')
s = root.read_text()
block = f'{start}\n\n{section}\n\n{end}'
if start in s or end in s:
    if s.count(start) != 1 or s.count(end) != 1:
        raise SystemExit('README markers are malformed; do not overwrite teammate edits')
    a = s.index(start)
    b = s.index(end, a) + len(end)
    s = s[:a] + block + s[b:]
else:
    s = s.rstrip() + '\n\n' + block + '\n'
root.write_text(s)
print('Appended or refreshed only the Milestone 6 DevOps section in README.md.')
print('Existing teammate CI/OIDC documentation left untouched.')
