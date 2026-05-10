#!/usr/bin/env bash
cd "$(dirname "$0")/.."
src="custom_components/orthoplay"
ls -1A -- "$src" | while IFS= read -r name; do
  ln -sn "$src/$name" "$name"
done
