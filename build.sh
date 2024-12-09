#!/bin/bash

export LC_ALL="C"
set -euo pipefail

RUNTIME="$(command -v podman || command -v docker || true)"
[ -n "$RUNTIME" ] || { echo "${0##*/}: neither podman nor docker is found"; exit 1; }

cd "$(realpath "$(dirname "$0")")"
printf '\n!!! REMINDER: did you run ext/update-backends.sh? !!!\n\n' >&2
sleep 2

"$RUNTIME" build -t localhost/cge-bap . | tee build.log
