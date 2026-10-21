#!/usr/bin/env bash
# Linux offline execution: no host devices, network, home, sysfs, or service sockets.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
exec bwrap --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --ro-bind /etc/alternatives /etc/alternatives \
  --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
  --proc /proc --dev /dev --tmpfs /tmp --ro-bind "$ROOT" /research \
  --chdir /research --clearenv --setenv PATH /usr/bin:/bin \
  --setenv HOME /tmp --setenv PYTHONDONTWRITEBYTECODE 1 "$@"
