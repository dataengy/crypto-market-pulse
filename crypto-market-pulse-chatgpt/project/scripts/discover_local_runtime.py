#!/usr/bin/env python3
"""Read-only survey of host tools in PATH/~/.apps/~/.app and Docker/Colima.

No installs, no container start/stop, no environment or secret-value dump.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

TOOL_ALIASES = {
    "clickhouse": ("clickhouse", "clickhouse-client", "clickhouse-server"),
    "redpanda_kafka": ("redpanda", "rpk", "kcat", "kafka-topics", "kafka-console-producer"),
    "spark": ("spark-submit", "spark-shell", "pyspark"),
    "postgres": ("postgres", "pg_ctl", "psql"),
    "minilake": ("minilake",),
    "airbyte": ("airbyte", "abctl"),
    "gcp_beam": ("gcloud", "bq", "terraform"),
    "runtime": ("docker", "colima", "java", "python3", "just", "duckdb"),
}
# No arbitrary execution of discovered binaries (only known read-only CLI commands below).
SEARCH_LEVELS = 5
MAX_VISITS = 12000


def possible_binaries(home: Path, wanted: set[str]) -> dict[str, list[str]]:
    """Limit filesystem walk; don't follow symlinks or inspect file contents."""
    found = {name: [] for name in wanted}
    visited = 0
    for root in (home / '.apps', home / '.app'):
        if not root.is_dir():
            continue
        root_depth = len(root.parts)
        for parent, dirs, files in os.walk(root, topdown=True, followlinks=False):
            visited += 1
            if visited > MAX_VISITS:
                break
            depth = len(Path(parent).parts) - root_depth
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '.git', 'venv', '.venv', 'site-packages', '__pycache__'}]
            if depth >= SEARCH_LEVELS:
                dirs[:] = []
            for name in files:
                if name not in wanted:
                    continue
                path = Path(parent) / name
                if path.is_file() and os.access(path, os.X_OK):
                    found[name].append(str(path))
        if visited > MAX_VISITS:
            break
    return {key: sorted(set(value)) for key, value in sorted(found.items()) if value}


def discover_app_bundles(home: Path) -> list[str]:
    """List named macOS .app bundles without reading package contents."""
    roots = [home / '.apps', home / '.app', home / 'Applications', Path('/Applications')]
    keywords = ('clickhouse', 'redpanda', 'spark', 'postgres', 'minilake', 'airbyte',
                'docker', 'colima', 'gcloud', 'cloud sdk', 'python', 'databricks')
    found: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        base = len(root.parts)
        for parent, dirs, _files in os.walk(root, topdown=True, followlinks=False):
            depth = len(Path(parent).parts) - base
            matching = [d for d in dirs if d.endswith('.app') and any(k in d.lower() for k in keywords)]
            found.update(str(Path(parent)/d) for d in matching)
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.endswith('.app')]
            if depth >= 3:
                dirs[:] = []
    return sorted(found)


def run_readonly(args: list[str], timeout: int = 6) -> dict[str, Any]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {'returncode': p.returncode, 'output': (p.stdout or '')[:40000], 'error': (p.stderr or '')[:800]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'returncode': None, 'output': '', 'error': type(exc).__name__}


def json_lines(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                result.append(obj)
        except json.JSONDecodeError:
            pass
    return result


def get_inventory(home: Path | None = None) -> dict[str, Any]:
    home = home or Path.home()
    wanted = {name for group in TOOL_ALIASES.values() for name in group}
    path_tools = {name: path for name in sorted(wanted) if (path := shutil.which(name))}
    inventory: dict[str, Any] = {
        'priority_order': ['installed OS/PATH/.apps/.app', 'existing Docker/Colima containers', 'new installation only if needed'],
        'searched_directories': [str(home / '.apps'), str(home / '.app')],
        'path_tools': path_tools,
        'additional_host_binaries': possible_binaries(home, wanted),
        'host_app_bundles': discover_app_bundles(home),
        'docker': {'available': bool(shutil.which('docker'))},
        'colima': {'available': bool(shutil.which('colima'))},
        'recommendation': 'Inspect compatibility and ownership before any start/stop/install; no changes performed.'
    }
    if shutil.which('docker'):
        d = inventory['docker']
        d['active_context'] = run_readonly(['docker', 'context', 'show'])
        d['contexts'] = run_readonly(['docker', 'context', 'ls', '--format', '{{json .}}'])
        ps = run_readonly(['docker', 'ps', '-a', '--no-trunc', '--format', '{{json .}}'])
        d['containers'] = json_lines(ps['output'])
        d['containers_error'] = ps['error'] or (f'exit={ps["returncode"]}' if ps['returncode'] else '')
        compose = run_readonly(['docker', 'compose', 'ls', '--all', '--format', 'json'])
        try:
            d['compose_projects'] = json.loads(compose['output']) if compose['returncode'] == 0 else []
        except json.JSONDecodeError:
            d['compose_projects'] = []
        d['compose_error'] = compose['error'] or (f'exit={compose["returncode"]}' if compose['returncode'] else '')
        images = run_readonly(['docker', 'images', '--format', '{{json .}}'])
        d['images'] = [x for x in json_lines(images['output']) if any(k in str(x).lower() for k in ('clickhouse','redpanda','kafka','spark','postgres','minilake','airbyte','pubsub'))]
        d['images_error'] = images['error'] or (f'exit={images["returncode"]}' if images['returncode'] else '')
    if shutil.which('colima'):
        inventory['colima']['profiles'] = run_readonly(['colima', 'list'])
    return inventory


def print_markdown(inv: dict[str, Any]) -> None:
    print('# Local runtime inventory (read-only)')
    print('Priority: OS app/PATH/~/.apps/~/.app → existing Docker/Colima → new deployment last.')
    for group, aliases in TOOL_ALIASES.items():
        entries=[]
        for alias in aliases:
            if alias in inv['path_tools']:
                entries.append(f'`{alias}`: `{inv["path_tools"][alias]}`')
            for extra in inv['additional_host_binaries'].get(alias,[]):
                entries.append(f'`{alias}`: `{extra}`')
        print(f'\n## {group}\n' + ('; '.join(entries) if entries else 'Not discovered (not proof of absence).'))
    print('\n## macOS application bundles')
    for p in inv.get('host_app_bundles',[]):
        print('- ' + p)
    if not inv.get('host_app_bundles'): print('No matched application bundle discovered.')
    docker=inv['docker']
    print('\n## Docker/Colima')
    if docker['available']:
        print('Docker context: ' + docker.get('active_context', {}).get('output', 'unknown').strip())
        for c in docker.get('containers', []):
            print(f'- container {c.get("Names","?")}: {c.get("Image","?")}, {c.get("Status","?")}, {c.get("Ports", "")}')
        if docker.get('containers_error'): print('Docker containers not fully available: '+docker['containers_error'])
        for i in docker.get('images', []):
            print(f'- cached image: {i.get("Repository","?")}:{i.get("Tag","?")}')
    else:
        print('Docker CLI not found.')
    if inv['colima']['available']:
        print('Colima profiles:\n'+inv['colima']['profiles']['output'].strip())
    else: print('Colima CLI not found.')
    print('\n**No install/start/stop/cleanup performed.** Validate endpoints, service owner, versions and compatibility manually.')


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    opts=parser.add_mutually_exclusive_group()
    opts.add_argument('--json',action='store_true',help='Emit machine-readable JSON (default).')
    opts.add_argument('--markdown',action='store_true',help='Show readable summary.')
    args=parser.parse_args()
    inv=get_inventory()
    if args.markdown:
        print_markdown(inv)
    else:
        print(json.dumps(inv, indent=2, ensure_ascii=False))

if __name__=='__main__':
    main()
