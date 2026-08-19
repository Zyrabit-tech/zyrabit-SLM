#!/bin/sh
set -eu

# The browser needs a token to call the local API. Keep its value out of the
# source tree and inject it only into the local container at startup.
envsubst '${ZYRABIT_API_KEY_WEB}' \
  < /usr/share/nginx/html/runtime-config.js.template \
  > /usr/share/nginx/html/runtime-config.js
