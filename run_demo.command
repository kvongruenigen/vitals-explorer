#!/bin/sh
# macOS: double-click; Linux/macOS terminal: ./run_demo.command
cd "$(dirname "$0")" || exit 1
for interpreter in python3.12 python3.11 python3; do
    if command -v "$interpreter" >/dev/null 2>&1; then
        "$interpreter" run_demo.py "$@"
        result=$?
        if [ "$result" -ne 0 ] && [ -t 0 ]; then
            printf '\nPress Enter to close… '
            read -r answer
        fi
        exit "$result"
    fi
done
printf 'Install Python 3.12 or 3.11, then launch again.\n' >&2
exit 1
