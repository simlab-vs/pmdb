#!/bin/sh
# Regenerate the scenario's data: the night's orders (work/input), the private levels snapshot,
# the hidden nights and their reference allocations. The catalog is regenerated only with --catalog.
set -eu
cd "$(dirname "$0")/.."
G=gen/gen_data.py
[ "${1:-}" = --catalog ] && python3 $G --catalog-out work/catalog
python3 $G --seed 20260929 --stock-scale 1800 --p-low 0.08 \
  --orders-out work/input/orders-2026-09-29.jsonl --levels-out private/levels-2026-09-29T0200.json
mkdir -p hidden/h1-original hidden/h2-low-stock hidden/h3-marketplace-kits hidden/h4-ample-stock
cp work/input/orders-2026-09-29.jsonl hidden/h1-original/orders.jsonl
cp private/levels-2026-09-29T0200.json hidden/h1-original/levels.json
python3 $G --seed 7201 --stock-scale 1000 --p-low 0.2 --orders 3000 \
  --orders-out hidden/h2-low-stock/orders.jsonl --levels-out hidden/h2-low-stock/levels.json
python3 $G --seed 7202 --stock-scale 1500 --p-low 0.12 --w-web 0.35 --w-mp 0.5 --w-b2b 0.15 --p-kit 0.1 --p-express 0.4 \
  --orders-out hidden/h3-marketplace-kits/orders.jsonl --levels-out hidden/h3-marketplace-kits/levels.json
python3 $G --seed 7203 --stock-scale 60000 --p-low 0 --p-oversold 0 --status-scale 0 \
  --orders-out hidden/h4-ample-stock/orders.jsonl --levels-out hidden/h4-ample-stock/levels.json
for d in hidden/*/; do
  python3 gen/reference.py "$d/orders.jsonl" "$d/levels.json" work/config/settings.toml work/catalog > "$d/truth.json"
done
