#!/usr/bin/env sh
set -eu
: "${DATABASE_URL:?Set DATABASE_URL}"
for file in tests/*.sql; do
  echo "Running $file"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
done
