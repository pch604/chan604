#!/bin/bash
set -e
S=/tmp/claude-0/-home-user-chan604/9056538b-9072-58a7-8356-020fd7f22202/scratchpad
cd $S/build
NODE_PATH=$S/build/node_modules node build.js $S/build/deck_raw.pptx
python3 postprocess.py deck_raw.pptx ../orig.pptx deck.pptx
python3 /root/.claude/skills/synced/c1f289dd-5267-4395-801d-374d068c8226_9a20d148-3bc3-41b3-9cdd-9a064927fe7b/pptx/scripts/office/validate.py deck.pptx | tail -3
./render.sh deck.pptx "$1" > /dev/null
