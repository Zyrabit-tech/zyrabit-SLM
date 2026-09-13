#!/usr/bin/env bash
# [DEPRECATED] Compatibility shim — zyra-up.sh will be retired in v3.0.
# Please use ./zyra.sh directly.
if [ -t 1 ]; then
  printf "\033[33m⚠️  Notice: ./zyra-up.sh is deprecated. Use ./zyra.sh instead.\033[0m\n" >&2
fi
exec "$(dirname "$0")/zyra.sh" "$@"
