#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec docker compose --env-file /opt/sigfq/private/vps.env -f "$project_dir/compose.vps.yaml" "$@"
