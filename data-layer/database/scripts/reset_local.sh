#!/usr/bin/env sh
set -eu
printf 'This deletes the local Arbor Vista PostgreSQL volume. Continue? [y/N] '
read answer
case "$answer" in
  y|Y|yes|YES) docker compose down -v && docker compose up -d --build ;;
  *) echo 'Cancelled.' ;;
esac
