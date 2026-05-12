#!/usr/bin/env bash
# 重新渲染 examples/ 下的 demo HTML（render.py 改后同步）+ 跑测试 + 截图。
#
# 用法：
#   ./bin/regen-demo.sh           # 渲染 demo HTML + 跑测试
#   ./bin/regen-demo.sh --screenshot  # 额外用 headless Chrome 截图到 docs/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

# 1) 跑测试 (stdlib unittest, 无 pip dep)
echo "▸ running unittest"
python3 -m unittest tests.test_render -v 2>&1 | tail -5

# 2) 重新渲染所有 examples
echo
echo "▸ regenerating examples"
for INPUT in examples/*.input.json; do
  OUTPUT="${INPUT%.input.json}.html"
  python3 scripts/render.py --input "$INPUT" --output "$OUTPUT"
done

# 3) 可选截图（需要 Chrome）
if [[ "${1:-}" == "--screenshot" ]]; then
  echo
  echo "▸ taking screenshots (headless Chrome)"
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  if [[ ! -x "$CHROME" ]]; then
    echo "  ✗ Chrome 未找到 ($CHROME), 跳过截图"
    exit 0
  fi

  mkdir -p docs
  URL="file://$ROOT/examples/unified-source-sync-manager.html"

  "$CHROME" --headless --no-sandbox \
    --screenshot="$ROOT/docs/hero.png" \
    --window-size=1400,1000 \
    --hide-scrollbars \
    --virtual-time-budget=4500 \
    "$URL" 2>/dev/null
  echo "  ✓ docs/hero.png"

  "$CHROME" --headless --no-sandbox \
    --screenshot="$ROOT/docs/preview.png" \
    --window-size=1400,5800 \
    --hide-scrollbars \
    --virtual-time-budget=4500 \
    "$URL" 2>/dev/null
  echo "  ✓ docs/preview.png"
fi

echo
echo "✓ demo 重新生成完毕"
