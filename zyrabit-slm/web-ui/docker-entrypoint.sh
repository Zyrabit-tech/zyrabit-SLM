#!/bin/sh
set -eu

# The service credential stays on the API. The browser file is an empty
# bootstrap so older pages that request it do not receive a Bearer token.
cp /usr/share/nginx/html/runtime-config.js.template /usr/share/nginx/html/runtime-config.js
