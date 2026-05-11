# Round 2 端到端 LLM 走查报告

**视角**：从零进场的 LLM agent，在 `/Users/admin/work/de/global-hotspot-globe/` 仓库被 `/impl-explain` 触发，要为 "GDELT GKG ingester" 这次实施生成 HTML。**实际我并不知道用户指代哪个 plan，必须靠 SKILL.md 步骤 1 推断**。

---

## 步骤 1：定位 plan 文件 — 卡在交叉验证规则的具体阈值

**心理日志**：

1. 先去 `docs/superpowers/plans/` —— 直接撞墙：**183 个 plan 文件**。"日期最新"完全失效，因为今天就有 3 个：
   - `2026-05-11-gdelt-gkg-ingester.md`
   - `2026-05-11-gdelt-subdomain-and-batch20-run.md`
   - `2026-05-11-unified-source-sync-manager.md`

2. SKILL.md 说"超过 1 个 plan 文件" → 必须做交叉验证。OK，跑 `git log origin/main..HEAD`：拿到 20+ 条 commit。subject 关键词：`Add GDELT GKG ingester with audit locks` / `Improve source sync coverage and GDELT taxonomy` / `Add unified source sync manager` / `Add RSS conditional fetch support` / `Add open-source and policy Pulse sources` 等。

3. **第一处卡点 — 关键词重合度怎么算？**SKILL.md 说"top1 与 top2 差距 < 2 个关键词就问用户"。但什么算"一个关键词"？我可以把 `gdelt-gkg-ingester` 拆成 `gdelt` / `gkg` / `ingester` 三个，也可以当成一个 multi-token 命中。按前一种算法，gdelt-gkg-ingester plan 命中 `gdelt`（2 次）+ `gkg`（1 次）+ `ingester`（1 次）= 4；unified-source-sync-manager plan 命中 `source-sync`（2 次）+ `unified`（1 次）+ `gdelt-taxonomy`（1 次）= 4。**差距 0，必须问用户**。这个结果其实是对的（commits 横跨两次实施），但**算法本身没规定，不同 LLM 会算出不同分**。建议加一条："关键词以 commit subject 的去 stop-word 后的 token 集合（lowercase + 拆 hyphen）为准"。

4. **第二处卡点 — "本次实施" 范围怎么定？**`git log origin/main..HEAD` 实际包含 *至少两次完整实施* 的 commit（unified source sync + GDELT GKG）。SKILL.md 假设 commits 区间天然对应一个 plan，但分支拖 20+ commits 时一个分支可能扛了 2-3 个 plan。**这种情况下交叉验证必然会触发"问用户"，但 prompt 里没说怎么问得有信息量**。我会问："本次实施分支包含 unified source sync / GDELT GKG / RSS batch 三组 commits，本次报告对应哪一组？" 这种判断需要在 SKILL.md 里显式写出。

5. **第三处卡点 — `docs/superpowers/plans/` 路径不在四条默认查找路径里？**等一下，再读 SKILL.md —— 在的，第 2 条是它。OK，但 `docs/plans/` 和 `docs/superpowers/plans/` 两条共存时优先级清晰，good。

**结论**：步骤 1 在 183-plan 仓库 + 多实施分支组合下会**正确触发"问用户"**，但问题本身怎么问，没规定。

---

## 步骤 2：收集 git 上下文 — symbolic-ref 在本仓库 OK，但有可移植性隐患

**心理日志**：

1. `git symbolic-ref refs/remotes/origin/HEAD --short` → 在本仓库返回 `origin/main`，good。**但这个命令在不少仓库会失败**：
   - 仓库没设 remote HEAD（很常见，需要手动 `git remote set-head origin -a`）
   - 仓库没有 remote（本地实验仓库）
   - fork 仓库 origin 指向自己，HEAD 不一定是 main
   SKILL.md 写了 fallback 到 `main` → `master`，OK。但**没说哪个情况会冒静默错误**：如果 origin/HEAD 错指向一个过时分支（开发者从未更新），`git log origin/HEAD..HEAD` 会包含远超本次实施的 commit。建议加："如果 `git log <base>..HEAD` 输出 > 50 条，提示用户：'base 分支可能过时（或本分支落后于上游），返回了 N 条 commit，请确认 base'"。

2. commits 列表 OK。我会拿到 20+ 条，超过 30 阈值的压缩规则 SKILL.md 写得清楚。

3. **fallback 路径（空 commit list）**：我看完之后觉得清楚，但实际跑 `git log <base>..HEAD` **几乎不会**返回空——除非分支恰好 fast-forward 合并完。fast-forward 后 `git log` 又能拿 N 条（main 历史）。这条 fallback 描述的场景，多数实际情况下并不会触发，反而真实失败模式是 commits **过多** 而不是过少。

**结论**：步骤 2 大多数仓库能跑通，但 symbolic-ref 失败 / commits 数过多两类隐患没处理。

---

## 步骤 3：综合输入 JSON — title vs question / mitigation 三态判定不够鲁棒

**心理日志**（假设用户回答"GDELT GKG ingester"，我读 `2026-05-11-gdelt-gkg-ingester.md`）：

1. **title vs question 的认知负担**：我对 `decision[0]` 第一反应是把"GKG 不进 pulse_feed_definitions"这一条搬进来。原 plan 写的是叙述句："不进 `pulse_feed_definitions.py` —— 那是 on-demand HTTP adapter 模式，GKG 是 push 流"。我现在要把这段拆成：
   - title: "GKG 走独立 pipeline stage"
   - question: "GKG 接入点放哪？"
   
   **拆是能拆，但 plan 里本就没有 question 字段**。每条决策我都要"反编译"出原问题，这步推断质量不稳。建议 SKILL.md 加："如果 plan 原文是叙述式而非 Q&A 式，**question 字段可省略**——title 自给自足时不强求副标题"。否则 LLM 容易瞎编一个生硬的"原问题"。

2. **mitigation 三态判定**：plan 里 risks 段写：
   - "rate limit 触发" — 已设 retry → 我标 `full`
   - "GDELT 上游断流" — Note 写 "短期缓存，长期需补 backfill 路径" → "长期需"是不是 partial？SKILL.md 的 rule of thumb 提了 "future / 后续 / 暂未接入"，但**没提"长期需"、"需补"、"待扩展"**。中文同义词覆盖不足，LLM 容易判错。建议把 rule of thumb 改成正则式说明："note 包含 future / TODO / 后续 / 长期 / 暂未 / 需补 / 待 + 任意动词 等延期意图词 → partial"。

3. **metrics 自动派生 vs 自填的边界**：SKILL.md 说"没填会自动派生（决策数 + 风险数）"。但**如果我填了一条特色 metric（比如"目标日入库 5K-30K"），剩下两个是不是要自己也填？还是 render.py 会补齐？** 读 `render_header`：`metrics = meta.get("metrics") or _auto_metrics(data)`——是 **or 整体替换**，不是 merge。这意味着**只要 meta.metrics 非空，自动派生完全跳过**。LLM 容易踩坑：填一条特色指标 → 决策/风险计数没了。建议 SKILL.md 明写："metrics 是 all-or-nothing。要写一条就要把决策/风险计数也手动写上"，或改 render.py 做 merge。

4. **architecture_diagram 没 5 个节点的硬约束**：SKILL.md 说"至少 5 个节点"是软约束，validator 不卡。LLM 容易省略——比如 GDELT GKG 这次实施只有 3 个组件（Adapter / Runner / Lifespan），我会写一个 3 节点 flowchart，跑过 validator，但图看起来空旷。建议软约束也加 warning（不阻塞）。

5. **Risks 段的提取陷阱**：plan 用 `- desc — severity: high — mitigation: full` 格式。我提取时容易把整行 `description` 写成 `desc — severity: high — mitigation: full`（即把 metadata 也吃进描述）。SKILL.md 第 103 行有警告，good，但**警告太隐蔽**——藏在 JSON schema 的内联注释里。建议拎出来做一条独立 bullet，和"mitigation rule of thumb"并列。

---

## 步骤 4：写临时 JSON — `/tmp` 在 macOS sandbox 有时不可写

无大卡点。SKILL.md 已经写了 `.impl-explain.input.json` fallback + 提示加 .gitignore，足够。

---

## 步骤 5：路径查找 — **致命：4 条路径都不命中**

**心理日志**：

1. 我跑 `git rev-parse --show-toplevel` → `/Users/admin/work/de/global-hotspot-globe`，OK。

2. 找 SKILL_DIR，按 SKILL.md 4 条优先级：
   - `~/.agents/skills/impl-explain/scripts/render.py` → 不存在
   - `~/.claude/skills/impl-explain/scripts/render.py` → 不存在
   - `~/.codex/.agents/skills/impl-explain/scripts/render.py` → 不存在
   - `~/.config/opencode/skills/impl-explain/scripts/render.py` → 不存在

   **实际 render.py 在 `/Users/admin/code/impl-explain/scripts/render.py`**（项目源码目录），4 条默认路径全部 miss。SKILL.md 明确禁止 `find ~` 兜底，所以我**只能告诉用户"未安装，请运行 install.sh"然后停止**。

3. 问题是：**这个 skill 在很多用户机器上就只装在源仓库里**（开发期 / 不想全局装 / 用 plugin manager 把 skill 仓库放别处）。4 条显式路径排除了所有"在仓库里跑自带 render.py" 的场景。建议加第 5 条 fallback："如果 4 条都 miss，检查 `$SKILL_REPO_ROOT/scripts/render.py`（基于 SKILL.md 自身路径反推），或环境变量 `IMPL_EXPLAIN_HOME`"。

4. 另一个隐患：Claude Code plugin marketplace 装的 skill 通常落在 `~/.claude/plugins/<plugin-name>/skills/<skill-name>/`，**不在 4 条路径里**。Codex 实际 skill 路径是 `~/.codex/agents/skills/`（无前导点）还是 `~/.codex/.agents/skills/`（有前导点）也存在分歧。建议核实 Codex 官方路径并补一条 `~/.codex/agents/skills/` 候选。

---

## 步骤 6：报告路径 — OK

如果跑到这步意味着前面都过了，纯字符串拼装无卡点。

---

## validate() 心理跑一遍

假设我漏了 `meta.title`：错误信息 `\`meta.title\` 缺失` —— 清晰，LLM 知道补。**好**。

假设我把 architecture_diagram.diagram 写成 ASCII：错误 "看起来不是 mermaid 语法... 如果只是 ASCII 图，请省略该字段让对应 section 不出现"。**好，明确给两条出路**（翻译 / 省略）。

假设我 status 写 `rejected`：错误信息提示"rejected 已废弃 → 多半应该放进 out_of_scope"。**好**。

假设 mermaid diagram 首行是 `%%{init: {...}}%%` 然后才 `flowchart LR`：`_MERMAID_RE` 用 `^\s*` 不跨行，**会误报为非 mermaid**。Plan 里如果作者写了 mermaid init directive，validator 会拒绝。建议放宽正则：跳过 `%%{...}%%` 注释/指令行后再匹配。

---

## SKILL.md vs plan-template.md 对齐情况

通读两份，**整体对齐**。一个小不一致：plan-template.md "Decisions" 段说 "至少 3 条，至多 8 条"；SKILL.md 第 122 行说 `decisions ≥ 1`（validator 阈值）+ "推荐 3-8 条"（软）。两者描述方向一致但数字不严格相同 —— 不算冲突。

plan-template.md `## Tasks` 末注明 "本段不会被 impl-explain 渲染"——**和 SKILL.md 互补**，good。

---

## 三种失败模式兜底评估

**(a) plan 没 `## Decisions` 段**：SKILL.md 第 190 行有 fallback 流程（先 grep commit body，不够 3 条问用户）。**OK**。但 grep 关键词只列了 "why / because / 因为 / 考虑过"，漏了 "选择 / 决定 / decided / chose / preferred / 权衡 / trade-off"。中文项目里我会漏掉一半 commit。

**(b) 仓库不在 git**：步骤 2 全部依赖 git 命令。SKILL.md 没说如果 `git rev-parse --is-inside-work-tree` 返回非 0 怎么办。LLM 进场后只能直接卡死，或硬塞 `meta.commits = []` 跑下去。建议加最前面一条：步骤 2 起手 `git rev-parse --is-inside-work-tree`，失败 → "本仓库不在 git，请手动提供 commit 列表 / 或退出"。

**(c) plan 全是叙述没结构化字段**：本质上是 (a) 的强化版。SKILL.md 给了"先 grep commit body" 路径，但没给"plan 的叙述段如何抽决策"的启发。建议加一条："如果 plan 用叙述段（非列表），按段落题目（### / ####）做粗切，每段提取第一句作为 chosen，从段内找 because/因为 子句作为 rationale。质量不稳时立刻问用户。"

---

## 如果只能再改 3 处 SKILL.md / schema

1. **路径查找加 fallback** —— 把 4 条显式路径扩成 6 条（补 Claude plugin marketplace 路径 + 基于 SKILL.md 自身位置反推 `$SKILL_REPO_ROOT/scripts/render.py`），或加一个环境变量 `IMPL_EXPLAIN_HOME` 兜底。当前 4 条对开发期 / plugin manager / 源码跑场景全 miss，是端到端最大杀手。

2. **多 plan 仓库交叉验证算法显式化** —— 写清"关键词 = commit subject 去 stop-word 后小写 + hyphen 拆 token 的集合"、"top1/top2 差距用集合 IoU 还是命中数"、"分支包含多次实施时怎么分组并问用户"。否则不同 LLM 在 183-plan 仓库行为发散。

3. **mitigation rule of thumb 中文同义词扩充 + commits 过多预警** —— `partial` 触发词增加 "长期 / 需补 / 待 + 动词 / TODO"；`git log <base>..HEAD` 超过 50 条时主动提示 "base 可能过时或分支扛多次实施，请确认"。前者直接降低 risk 字段错判率，后者捕获"分支拖太多 commit"这个高频真实失败模式。
