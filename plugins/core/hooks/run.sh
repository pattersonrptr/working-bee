#!/usr/bin/env bash
# Run a working-bee hook with the first real Python 3.9+ on this machine.
#
# Why not just "python3 hook.py": on Windows, python3 is often the Microsoft
# Store stub. It exits 49 without running anything, Claude Code treats that as
# a non-blocking error, and the guard is silently off. On some Linux systems
# "python" is Python 2. So each candidate is probed before use, and the one
# that works is remembered in $CLAUDE_PLUGIN_DATA (probing costs ~250 ms, and
# this runs before every tool call).
#
# Usage (from hooks.json): bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" guard_files.py
set -u
here="$(cd "$(dirname "$0")" && pwd)"
script="$here/$1"
shift
cache="${CLAUDE_PLUGIN_DATA:+$CLAUDE_PLUGIN_DATA/python-cmd}"

run() {  # run <python executable> <flag or empty> -- -I: isolated from PYTHONPATH and user site
  if [ -n "$2" ]; then exec "$1" "$2" -I "$script" "${@:3}"; fi
  exec "$1" -I "$script" "${@:3}"
}

if [ -n "$cache" ] && [ -r "$cache" ]; then
  { read -r py; read -r flag; } <"$cache"
  if [ -n "${py:-}" ] && [ -x "$py" ]; then
    run "$py" "${flag:-}" "$@"
  fi
fi

probe='import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'
for name in python3 python py; do
  py="$(command -v "$name" 2>/dev/null)" || continue
  flag=""
  [ "$name" = py ] && flag="-3"
  if "$py" $flag -c "$probe" >/dev/null 2>&1; then
    if [ -n "$cache" ]; then
      mkdir -p "$CLAUDE_PLUGIN_DATA" 2>/dev/null && printf '%s\n%s\n' "$py" "$flag" >"$cache" 2>/dev/null
    fi
    run "$py" "$flag" "$@"
  fi
done

msg="working-bee: no Python 3.9+ found (tried python3, python, py -3); its guardrails are OFF."
case "$(basename "$script")" in
  session_brief.py) echo "$msg Tell the user." ;;  # stdout becomes session context
  *) echo "$msg" >&2 ;;
esac
exit 1
