#!/usr/bin/env bash
# impl-explain 跨 agent skill 安装脚本
#
# 把 SKILL.md + scripts/ 安装到三家 agent 都能读到的位置：
#   - Claude Code:  ~/.claude/skills/impl-explain/
#   - Codex CLI:    ~/.codex/.agents/skills/impl-explain/  (Codex 同时也扫 ~/.agents/skills)
#   - opencode:     ~/.config/opencode/skills/impl-explain/ (opencode 同时也扫 ~/.claude/skills 和 ~/.agents/skills)
#
# 同时（可选）安装 slash 触发壳子：
#   - Codex:    ~/.codex/prompts/impl-explain.md   (注意：Codex custom prompts 已被官方标 deprecated)
#   - opencode: ~/.config/opencode/commands/impl-explain.md
#
# Claude Code 不需要壳子，自动暴露 /impl-explain。
#
# 用法：
#   ./install.sh                # 安装 skill + 壳子（默认）
#   ./install.sh --force        # 覆盖已存在的安装
#   ./install.sh --no-wrappers  # 只装 skill 不装 Codex/opencode 壳子
#   ./install.sh --link         # 用 symlink 而非 copy（便于本地 dev 迭代）
#   ./install.sh --status       # 检查 4 份副本是否与源同步（不修改任何文件）
#   ./install.sh --uninstall    # 移除所有安装位置
#   ./install.sh --help

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="impl-explain"

# 安装目标
PRIMARY_DIR="$HOME/.agents/skills/$SKILL_NAME"
CLAUDE_DIR="$HOME/.claude/skills/$SKILL_NAME"
OPENCODE_DIR="$HOME/.config/opencode/skills/$SKILL_NAME"
CODEX_DIR="$HOME/.codex/.agents/skills/$SKILL_NAME"

CODEX_PROMPT="$HOME/.codex/prompts/$SKILL_NAME.md"
OPENCODE_COMMAND="$HOME/.config/opencode/commands/$SKILL_NAME.md"

# Manifest 文件：SKILL.md 步骤 5 优先读这里拿到 skill 源目录，跨仓库可达
MANIFEST_DIR="$HOME/.config/$SKILL_NAME"
MANIFEST_FILE="$MANIFEST_DIR/manifest.json"

INSTALL_TARGETS=("$PRIMARY_DIR" "$CLAUDE_DIR" "$OPENCODE_DIR" "$CODEX_DIR")
INSTALL_TARGET_NAMES=("primary (~/.agents/skills/$SKILL_NAME)" "Claude Code (~/.claude/skills/$SKILL_NAME)" \
  "opencode (~/.config/opencode/skills/$SKILL_NAME)" "Codex (~/.codex/.agents/skills/$SKILL_NAME)")

# 选项
FORCE=0
INSTALL_WRAPPERS=1
USE_LINK=0
UNINSTALL=0
STATUS_ONLY=0

for arg in "$@"; do
  case $arg in
    --force) FORCE=1 ;;
    --no-wrappers) INSTALL_WRAPPERS=0 ;;
    --link) USE_LINK=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --status) STATUS_ONLY=1 ;;
    -h|--help)
      sed -n '2,/^set/p' "${BASH_SOURCE[0]}" | sed -e 's/^# \?//' -e '/^set/d'
      exit 0
      ;;
    *)
      echo "未知参数: $arg" >&2
      echo "用 --help 查看用法" >&2
      exit 2
      ;;
  esac
done

# ============ 工具函数 ============

log_step() { printf "\033[1;36m▸\033[0m %s\n" "$1"; }
log_ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
log_skip() { printf "  \033[33m○\033[0m %s\n" "$1"; }
log_warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
log_err()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }

# 平台兼容的 hash
file_hash() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" 2>/dev/null | awk '{print $1}'
  else
    md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | awk '{print $1}'
  fi
}

install_skill_dir() {
  local target="$1"
  local target_name="$2"
  log_step "安装 skill 到 $target_name"

  if [[ -e "$target" ]]; then
    if [[ $FORCE -eq 0 ]]; then
      log_skip "已存在 ($target), 跳过. 用 --force 覆盖."
      return
    fi
    rm -rf "$target"
  fi

  mkdir -p "$(dirname "$target")"

  if [[ $USE_LINK -eq 1 ]]; then
    ln -s "$SOURCE_DIR" "$target"
    log_ok "symlink → $target"
  else
    mkdir -p "$target/scripts"
    cp "$SOURCE_DIR/SKILL.md" "$target/SKILL.md"
    cp "$SOURCE_DIR/scripts/render.py" "$target/scripts/render.py"
    chmod +x "$target/scripts/render.py"
    log_ok "copy → $target"
  fi
}

install_file() {
  local source_file="$1"
  local target="$2"
  local target_name="$3"
  log_step "安装 $target_name"

  if [[ -e "$target" && $FORCE -eq 0 ]]; then
    log_skip "已存在 ($target), 跳过. 用 --force 覆盖."
    return
  fi

  mkdir -p "$(dirname "$target")"

  if [[ $USE_LINK -eq 1 ]]; then
    rm -f "$target"
    ln -s "$source_file" "$target"
    log_ok "symlink → $target"
  else
    cp "$source_file" "$target"
    log_ok "copy → $target"
  fi
}

remove_path() {
  local target="$1"
  local name="$2"
  if [[ -e "$target" || -L "$target" ]]; then
    rm -rf "$target"
    log_ok "removed $name ($target)"
  else
    log_skip "$name 不存在 ($target)"
  fi
}

# ============ Status 检查 ============

check_status() {
  echo "impl-explain status check"
  echo "源目录: $SOURCE_DIR"
  echo

  local src_skill_hash src_render_hash
  src_skill_hash=$(file_hash "$SOURCE_DIR/SKILL.md")
  src_render_hash=$(file_hash "$SOURCE_DIR/scripts/render.py")

  local drift=0

  for i in "${!INSTALL_TARGETS[@]}"; do
    local target="${INSTALL_TARGETS[$i]}"
    local name="${INSTALL_TARGET_NAMES[$i]}"
    log_step "$name"

    if [[ ! -e "$target" ]]; then
      log_skip "未安装"
      continue
    fi

    if [[ -L "$target" ]]; then
      local link_target
      link_target=$(readlink "$target")
      if [[ "$link_target" == "$SOURCE_DIR" ]]; then
        log_ok "symlink → 源同步"
      else
        log_warn "symlink → $link_target  (与当前源 $SOURCE_DIR 不一致)"
        drift=1
      fi
      continue
    fi

    local installed_skill installed_render
    installed_skill=$(file_hash "$target/SKILL.md" 2>/dev/null || echo "missing")
    installed_render=$(file_hash "$target/scripts/render.py" 2>/dev/null || echo "missing")

    local status_ok=1
    if [[ "$installed_skill" != "$src_skill_hash" ]]; then
      log_err "SKILL.md 与源不一致（已漂移，重新跑 ./install.sh --force 同步）"
      status_ok=0
      drift=1
    fi
    if [[ "$installed_render" != "$src_render_hash" ]]; then
      log_err "scripts/render.py 与源不一致（已漂移）"
      status_ok=0
      drift=1
    fi
    if [[ $status_ok -eq 1 ]]; then
      log_ok "与源同步"
    fi
  done

  # Wrapper files
  echo
  for pair in "$CODEX_PROMPT:slash-wrappers/codex-prompt.md:Codex prompt" \
              "$OPENCODE_COMMAND:slash-wrappers/opencode-command.md:opencode command"; do
    local target="${pair%%:*}"
    local rest="${pair#*:}"
    local source_rel="${rest%%:*}"
    local name="${rest##*:}"
    log_step "$name 壳子"
    if [[ ! -e "$target" ]]; then
      log_skip "未安装"
      continue
    fi
    if [[ -L "$target" ]]; then
      log_ok "symlink"
      continue
    fi
    local src="$SOURCE_DIR/$source_rel"
    if [[ "$(file_hash "$target")" == "$(file_hash "$src")" ]]; then
      log_ok "与源同步"
    else
      log_err "与源不一致（已漂移）"
      drift=1
    fi
  done

  echo
  if [[ $drift -eq 0 ]]; then
    echo "✓ 全部同步"
    exit 0
  else
    echo "! 检测到漂移，运行 ./install.sh --force 重新同步"
    exit 1
  fi
}

# ============ 前置检查 ============

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: 找不到 python3, impl-explain 需要 Python 3.x (stdlib only, 无 pip 依赖)" >&2
  exit 1
fi

if [[ ! -f "$SOURCE_DIR/SKILL.md" || ! -f "$SOURCE_DIR/scripts/render.py" ]]; then
  echo "error: 源目录缺少 SKILL.md 或 scripts/render.py: $SOURCE_DIR" >&2
  exit 1
fi

# ============ Status / Uninstall 分支 ============

if [[ $STATUS_ONLY -eq 1 ]]; then
  check_status
fi

if [[ $UNINSTALL -eq 1 ]]; then
  log_step "卸载 impl-explain"
  for i in "${!INSTALL_TARGETS[@]}"; do
    remove_path "${INSTALL_TARGETS[$i]}" "${INSTALL_TARGET_NAMES[$i]}"
  done
  remove_path "$CODEX_PROMPT" "Codex prompt wrapper"
  remove_path "$OPENCODE_COMMAND" "opencode command wrapper"
  remove_path "$MANIFEST_FILE" "manifest 文件"
  echo
  echo "✓ 卸载完成"
  exit 0
fi

# ============ 安装 ============

echo
echo "impl-explain installer"
echo "源目录: $SOURCE_DIR"
echo "Python: $(python3 --version)"
if [[ $USE_LINK -eq 1 ]]; then
  echo "模式: symlink (dev)"
else
  echo "模式: copy (production) — 修改源后需 ./install.sh --force 同步; 或用 ./install.sh --status 检查漂移"
fi
[[ $FORCE -eq 1 ]] && echo "强制覆盖: 是"
echo

# 1) Primary location — Codex + opencode 都扫
install_skill_dir "$PRIMARY_DIR" "primary location (~/.agents/skills/$SKILL_NAME)"

# 2) Claude Code location
install_skill_dir "$CLAUDE_DIR" "Claude Code (~/.claude/skills/$SKILL_NAME)"

# 3) opencode location
install_skill_dir "$OPENCODE_DIR" "opencode (~/.config/opencode/skills/$SKILL_NAME)"

# 4) Codex 独立目录
install_skill_dir "$CODEX_DIR" "Codex (~/.codex/.agents/skills/$SKILL_NAME)"

# 4.5) Manifest 文件（让 skill 在用户没装到任何标准位置 / 在 dev clone 仓库下跑也能找到 render.py）
log_step "写入 manifest ($MANIFEST_FILE)"
mkdir -p "$MANIFEST_DIR"
# 用 Python json.dumps 安全转义路径里的引号 / 反斜杠 / 换行——直接 heredoc 拼字符串
# 会被路径里的特殊字符破坏 manifest 文件。
MODE=$([[ $USE_LINK -eq 1 ]] && echo symlink || echo copy)
INSTALLED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 -c "
import json, sys
manifest = {
    'skill_dir': sys.argv[1],
    'primary_dir': sys.argv[2],
    'installed_at': sys.argv[3],
    'mode': sys.argv[4],
}
with open(sys.argv[5], 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write('\n')
" "$SOURCE_DIR" "$PRIMARY_DIR" "$INSTALLED_AT" "$MODE" "$MANIFEST_FILE"
log_ok "manifest 写入 $MANIFEST_FILE"

# 5) Slash wrappers
if [[ $INSTALL_WRAPPERS -eq 1 ]]; then
  if [[ -f "$SOURCE_DIR/slash-wrappers/codex-prompt.md" ]]; then
    install_file "$SOURCE_DIR/slash-wrappers/codex-prompt.md" "$CODEX_PROMPT" \
      "Codex slash 壳子 (~/.codex/prompts/$SKILL_NAME.md)"
    log_warn "Codex custom prompts 已被官方标 deprecated；本壳子是 fallback，未来 Codex 下线该机制后需迁移到 /skills 菜单触发"
  fi
  if [[ -f "$SOURCE_DIR/slash-wrappers/opencode-command.md" ]]; then
    install_file "$SOURCE_DIR/slash-wrappers/opencode-command.md" "$OPENCODE_COMMAND" \
      "opencode command 壳子 (~/.config/opencode/commands/$SKILL_NAME.md)"
  fi
fi

# ============ 验证 ============

echo
log_step "验证 render.py 可执行"
if python3 "$PRIMARY_DIR/scripts/render.py" --help >/dev/null 2>&1; then
  log_ok "render.py --help 正常"
else
  log_warn "render.py 调用失败, 检查 Python 版本"
fi

echo
echo "✓ 安装完成"
echo
echo "触发方式："
echo "  Claude Code:  在会话里输 /$SKILL_NAME"
echo "  Codex CLI:    在会话里输 /$SKILL_NAME (走 prompts 壳子, deprecated), 或 /skills 菜单选 $SKILL_NAME"
echo "  opencode:     在会话里输 /$SKILL_NAME (走 commands 壳子, 优先调原生 skill 工具)"
echo
echo "检查漂移：./install.sh --status"
echo "卸载：./install.sh --uninstall"
