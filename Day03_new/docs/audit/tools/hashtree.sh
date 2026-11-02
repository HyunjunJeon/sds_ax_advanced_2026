#!/bin/bash
# usage: hashtree.sh -> per-directory sha256 over Day03_new/{mas_lab,tests,rag_lab}, the seven notebooks Day03_new/0*.ipynb and Day02_new/rag_lab (no __pycache__, no .pyc), plus informational counts.
# Run it before and after a run and compare the two outputs. The last all-files line leaves out data/gold.jsonl (the answer key is never read by these tools), so it is not comparable with older outputs.
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)  # tools -> audit -> docs -> Day03_new -> repository
cd "$ROOT/Day03_new" || exit 1
for d in mas_lab tests rag_lab; do
  h=$(find "$d" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | LC_ALL=C sort | while read -r f; do shasum -a 256 "$f"; done | shasum -a 256 | cut -c1-64)
  n=$(find "$d" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | wc -l | tr -d ' ')
  echo "Day03_new/$d  files=$n  sha256=$h"
done
nbh=$(ls 0*.ipynb | LC_ALL=C sort | while read -r f; do shasum -a 256 "$f"; done | shasum -a 256 | cut -c1-64)
echo "Day03_new/0*.ipynb  files=$(ls 0*.ipynb | wc -l | tr -d ' ')  sha256=$nbh"
d=Day02_new/rag_lab
cd "$ROOT"
h=$(find "$d" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | LC_ALL=C sort | while read -r f; do shasum -a 256 "$f"; done | shasum -a 256 | cut -c1-64)
n=$(find "$d" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | wc -l | tr -d ' ')
echo "$d  files=$n  sha256=$h"
h=$(cd Day03_new && find . -type f ! -path './outputs/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -path '*/.ipynb_checkpoints/*' ! -path '*/.ruff_cache/*' ! -name .env ! -path ./data/gold.jsonl | LC_ALL=C sort | while read -r f; do shasum -a 256 "$f"; done | shasum -a 256 | cut -c1-64)
echo "Day03_new (all non-excluded files, informational)  sha256=$h"
echo "Day03_new/outputs/runs files=$(ls Day03_new/outputs/runs | wc -l | tr -d ' ')"
