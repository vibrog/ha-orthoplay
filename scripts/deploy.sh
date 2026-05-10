#!/usr/bin/env bash
# Deploys the integration to a HA instance via SSH.
# Usage: ./scripts/deploy.sh [user@host] [path]
# Requires the SSH add-on or SSH access to the HA instance.

HOST=${1:-root@homeassistant.local}
HA_CONFIG=${2:-/config}
COMPONENT="orthoplay"
SOURCE="$(cd "$(dirname "$0")/.." && pwd)/custom_components/$COMPONENT"
TARGET="$HA_CONFIG/custom_components/$COMPONENT"

ssh "$HOST" "[ -d $TARGET ] && mkdir -p $TARGET"
scp -rp "$SOURCE/." "$HOST:$TARGET/"
ssh "$HOST" "ha core restart"
