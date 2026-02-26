#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CORE_JAR="${SCIONA_JAVAPARSER_JAR:-$ROOT/validations/reducers/jar/javaparser-core-3.25.9.jar}"
OUT_JAR="${SCIONA_JAVAPARSER_RUNNER_JAR:-$ROOT/validations/reducers/jar/java-parser-runner.jar}"
SRC="$ROOT/validations/reducers/validation/independent/scripts/JavaParserRunner.java"

if [[ ! -f "$CORE_JAR" ]]; then
  echo "Missing core jar: $CORE_JAR" >&2
  exit 1
fi
if [[ ! -f "$SRC" ]]; then
  echo "Missing source: $SRC" >&2
  exit 1
fi

TMPDIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

mkdir -p "$(dirname "$OUT_JAR")"
javac -cp "$CORE_JAR" -d "$TMPDIR" "$SRC"
jar --create --file "$OUT_JAR" -C "$TMPDIR" .
echo "Wrote: $OUT_JAR"
