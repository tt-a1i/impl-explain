#!/usr/bin/env bash
# impl-explain 跨 agent skill 安装脚本
#
# 把 SKILL.md + examples/sample.html 安装到三家 agent 都能读到的位置：
#   - Claude Code:  ~/.claude/skills/impl-explain/
#   - Codex CLI:    ~/.codex/.agents/skills/impl-explain/
#   - opencode:     ~/.config/opencode/skills/impl-explain/
#
# 同时（可选）安装 slash 触发壳子：
#   - Codex:    ~/.codex/prompts/impl-explain.md
#   - opencode: ~/.config/opencode/commands/impl-explain.md
#
# Claude Code 不需要壳子，自动暴露 /impl-explain。
#
# 用法：
#   ./install.sh                # 安装（默认 copy 模式）
#   ./install.sh --link         # symlink 模式（dev 边改边生效）
#   ./install.sh --force        # 覆盖已存在的安装
#   ./install.sh --no-wrappers  # 只装 skill, 不装 Codex/opencode 壳子
#   ./install.sh --uninstall    # 移除所有安装位置
#   ./install.sh --help

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="impl-explain"

# 安装目标（覆盖 Codex / opencode / Claude Code 三家发现位置）
TARGETS=(
  "$HOME/.agents/skills/$SKILL_NAME:primary (~/.agents/skills/$SKILL_NAME)"
  "$HOME/.claude/skills/$SKILL_NAME:Claude Code (~/.claude/skills/$SKILL_NAME)"
  "$HOME/.config/opencode/skills/$SKILL_NAME:opencode (~/.config/opencode/skills/$SKILL_NAME)"
  "$HOME/.codex/.agents/skills/$SKILL_NAME:Codex (~/.codex/.agents/skills/$SKILL_NAME)"
)

CODEX_PROMPT="$HOME/.codex/prompts/$SKILL_NAME.md"
OPENCODE_COMMAND="$HOME/.config/opencode/commands/$SKILL_NAME.md"

# 选项
FORCE=0
INSTALL_WRAPPERS=1
USE_LINK=0
UNINSTALL=0

for arg in "$@"; do
  case $arg in
    --force) FORCE=1 ;;
    --no-wrappers) INSTALL_WRAPPERS=0 ;;
    --link) USE_LINK=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help)
      sed -n '2,/^set/p' "${BASH_SOURCE[0]}" | sed -e 's/^# \?//' -e '/^set/d'
      exit 0
      ;;
    *) echo "未知参数: $arg" >&2; echo "用 --help 查看用法" >&2; exit 2 ;;
  esac
done

log_step() { printf "\033[1;36m▸\033[0m %s\n" "$1"; }
log_ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
log_skip() { printf "  \033[33m○\033[0m %s\n" "$1"; }

install_one() {
  local target="$1" name="$2"
  log_step "$name"

  if [[ -e "$target" ]]; then
    if [[ $FORCE -eq 0 ]]; then
      log_skip "已存在, 跳过 (用 --force 覆盖)"
      return
    fi
    rm -rf "$target"
  fi

  mkdir -p "$(dirname "$target")"

  if [[ $USE_LINK -eq 1 ]]; then
    ln -s "$SOURCE_DIR" "$target"
    log_ok "symlink → $target"
  else
    mkdir -p "$target/examples"
    cp "$SOURCE_DIR/SKILL.md" "$target/SKILL.md"
    cp "$SOURCE_DIR/examples/sample.html" "$target/examples/sample.html"
    log_ok "copy → $target"
  fi
}

install_wrapper() {
  local src="$1" target="$2" name="$3"
  log_step "$name"
  if [[ -e "$target" && $FORCE -eq 0 ]]; then
    log_skip "已存在, 跳过 (用 --force 覆盖)"
    return
  fi
  mkdir -p "$(dirname "$target")"
  if [[ $USE_LINK -eq 1 ]]; then
    rm -f "$target"
    ln -s "$src" "$target"
    log_ok "symlink → $target"
  else
    cp "$src" "$target"
    log_ok "copy → $target"
  fi
}

remove_one() {
  local target="$1" name="$2"
  if [[ -e "$target" || -L "$target" ]]; then
    rm -rf "$target"
    log_ok "removed $name"
  else
    log_skip "$name 不存在"
  fi
}

# 卸载
if [[ $UNINSTALL -eq 1 ]]; then
  log_step "卸载 impl-explain"
  for entry in "${TARGETS[@]}"; do
    target="${entry%%:*}"; name="${entry##*:}"
    remove_one "$target" "$name"
  done
  remove_one "$CODEX_PROMPT" "Codex prompt wrapper"
  remove_one "$OPENCODE_COMMAND" "opencode command wrapper"
  echo
  echo "✓ 卸载完成"
  exit 0
fi

# 安装
echo
echo "impl-explain installer"
echo "源目录: $SOURCE_DIR"
[[ $USE_LINK -eq 1 ]] && echo "模式: symlink (dev)" || echo "模式: copy (production)"
[[ $FORCE -eq 1 ]] && echo "强制覆盖: 是"
echo

for entry in "${TARGETS[@]}"; do
  target="${entry%%:*}"; name="${entry##*:}"
  install_one "$target" "$name"
done

if [[ $INSTALL_WRAPPERS -eq 1 ]]; then
  if [[ -f "$SOURCE_DIR/slash-wrappers/codex-prompt.md" ]]; then
    install_wrapper "$SOURCE_DIR/slash-wrappers/codex-prompt.md" "$CODEX_PROMPT" \
      "Codex slash 壳子 (~/.codex/prompts/$SKILL_NAME.md, Codex prompts 已 deprecated, 为 fallback)"
  fi
  if [[ -f "$SOURCE_DIR/slash-wrappers/opencode-command.md" ]]; then
    install_wrapper "$SOURCE_DIR/slash-wrappers/opencode-command.md" "$OPENCODE_COMMAND" \
      "opencode command 壳子 (~/.config/opencode/commands/$SKILL_NAME.md)"
  fi
fi

echo
echo "✓ 安装完成"
echo
echo "触发方式："
echo "  Claude Code:  /$SKILL_NAME"
echo "  Codex CLI:    /$SKILL_NAME (prompts 壳子, fallback)  或 /skills 菜单"
echo "  opencode:     /$SKILL_NAME (commands 壳子)"
echo
echo "卸载: ./install.sh --uninstall"
