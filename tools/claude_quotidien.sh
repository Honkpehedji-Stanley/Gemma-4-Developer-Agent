#!/bin/bash
# Lance Claude chaque matin sur la routine point-du-jour (veille, résultats, évaluations, soumission prouvée sinon base).
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
C=$(ls -d "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1)
[ -x "$C" ] || { echo "$(date -u +%FT%T) claude introuvable" >> logs/claude_quotidien.log; exit 1; }
echo "=== $(date -u +%FT%T)" >> logs/claude_quotidien.log
timeout 3h "$C" -p "/point-du-jour" --permission-mode auto >> logs/claude_quotidien.log 2>&1
