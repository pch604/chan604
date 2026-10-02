#!/bin/bash
# usage: render.sh deck.pptx outdir
set -e
P=/root/.claude/skills/synced/c1f289dd-5267-4395-801d-374d068c8226_9a20d148-3bc3-41b3-9cdd-9a064927fe7b/pptx
mkdir -p "$2"; rm -f "$2"/*.jpg "$2"/*.pdf
cp "$1" /tmp/lo/r.pptx
python3 $P/scripts/office/soffice.py --headless --convert-to pdf --outdir /tmp/lo /tmp/lo/r.pptx >/dev/null 2>&1
cp /tmp/lo/r.pdf "$2/deck.pdf"
pdftoppm -jpeg -r 110 "$2/deck.pdf" "$2/s"
ls "$2"
