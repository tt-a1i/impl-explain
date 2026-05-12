# Round-4 收敛评估 · impl-explain

基于 r4 `fullpage.png`（1400×5800）+ r3 基准对照 + 实际 render.py / SKILL.md / install.sh / demo JSON 核对。

---

## A. Round-3 P0/P1 是否真解决（逐条一句话）

1. **Before/After 高度差**——CSS 加 `max-height: 320px` 后 BEFORE 不再压倒 AFTER，但 AFTER 等比缩到失读（详 B2）。
2. **Top risk highlight 与 risks 首行 100% 重复**——已改用 `note`，文本不再 byte-identical，解决。
3. **demo 红警视觉**——新增 `Scheduler 单进程跑` high+none 风险，Top risk 卡渲染红色"未缓解"态，**关键**。
4. **TL;DR 到 Risks 两屏无风险信号**——TL;DR 尾 inline `5 RISKS · 2 HIGH (1 UNMIT) · 1 MEDIUM · 看详情→` 已加，**完美补位**。
5. **Hero commits 5 行未折叠**——已折叠到 3 行 + "展开全部 5 COMMITS" 按钮，解决。
6. **TOC 初始 active 错位**——r4 首屏高亮 `TL;DR`，解决。
7. **关键词算法 boilerplate 污染**——SKILL.md 步骤 1 已剥模板 token + 限定特征段落 + 阈值 2→3 + top1<5 安全网，方向对；未复测（详 B6）。
8. **mitigation 同义词漏 "长期/后期"**——L141 实测含 `后期 / 长期 / down the road / not yet`，**基本解决**。
9. **路径 fallback dev clone 卡死**——新增 manifest（P1 + install.sh 写入），**走完 install.sh 后**解决；首次未跑仍卡（详 B5）。
10. **question 字段冗余**——render 不渲染 + schema 仍接受 + L138 写"已废弃"，但 L156 有矛盾残留（详 B3）。

10 条里 6 条干净解决，2 条部分（#1/#10），1 条需复测（#7），1 条依赖前置（#9）。

---

## B. Round-4 新引入 / 显露的问题

### B1. Top risk highlight 用 `note` 反而更技术 — **P1**

highlight body 是 "多副本场景下两个调度器会争抢同一 SourceSyncDefinition, 触发 INSERT 主键冲突；需要 leader election 才能上 K8s rollingUpdate, 暂未做"——含 `INSERT 主键冲突 / leader election / K8s rollingUpdate` 三个底层名词，**实施 dev 自言自语**。而对应 risk-row 的 `description` "Scheduler 单进程跑, 多副本部署会同时跑造成 DB 写冲突" 反而**更适合 30 秒读者**——业务陈述、不假设技术栈。round-3 swap 方向选错。**建议**：highlight 用 description；risk-row 里**那条 highlight 匹配的行（Scheduler 单进程跑那行）**省略 description、只显示 note；分工反过来。

### B2. AFTER cell 等比缩小到失读 — **P0（视觉）**

肉眼可见：AFTER 的横向 5 节点链被压缩到一条 ~140px 宽的窄带，节点文字几乎读不出来；BEFORE 的垂直树占满 cell 正常。怀疑（未在浏览器实测 DOM）是 `.flow-cell .mermaid svg { max-height: 320px; width: auto !important }` + flex centering + cell 宽限制叠加导致——具体机制需打开 HTML inspect 确认。**建议**（任一）：(a) demo 把 AFTER 改 `flowchart TB` 让两侧都竖排；(b) `.flow-cell.after .mermaid svg { min-width: 100% }`；(c) 取消 `width: auto !important` 让 SVG 占满 cell 宽。

### B3. SKILL.md `question` 字段叙述自相矛盾 — **P2**

L138 写"已废弃, 不要再填", L156 又写"原问题留给可选的 question 字段做副标题"，**互相打架**。删掉 L156 这半句。

### B4. mitigation 同义词正则化未做 — **P2**

剩下 r3 提的"需要+任意动词"需要 regex 升级，纯字面匹配覆盖不到。可推到后续。

### B5. Manifest 链路完整但首次失败提示不够 — **P1**

链路：install.sh → 写 manifest → P1 读直跑。完整。但 SKILL.md L202 失败 message 写"请先 git clone …… ./install.sh"——如果 agent 是被一个**已 clone 但忘 install** 的用户触发（最常见），agent 不知道 source 在哪、无法 cd 进去跑。**建议**：message 加一行 "如果你已经 clone 了 repo, 进入它跑 `./install.sh` 即可。"

### B6. 关键词算法剥 boilerplate 未手工复跑 — **P0（验证空白）**

r3 LLM eval 实跑 184 plans, 报真 plan 排第 38。r4 修复方向对，但**没拿数据证明**新规则下真 plan 升到 top1 或差距 < 5 触发问询。算法是 prose 不是脚本，只能**手工 simulate**：在 global-hotspot-globe 仓库，按新规则取特征段落（文件名 + h1 + `## TL;DR` + `## Decisions` 子标题）切 token + 过停用词 + 算 overlap，确认 `unified-source-sync-manager` plan 排进 top1 或触发问询。**纯验证, 半小时**。

### B7. Commits 折叠 JS 静态分析通过, 浏览器交互未测 — **note**

render.py L1001–1013 JS 逻辑读 code 通过：handler 挂载、toggle 文案、aria-expanded 都对。**浏览器实际点击未测**。

---

## C. 之前未识别 / 现在显露的问题

1. **风险预告行 "看详情 →"** 中文 + 英文箭头，与全行其它纯英文 mono token 风格不和谐。可换 `JUMP →` / `DETAILS →`。
2. **risk-list 第一行 note 与 Top risk highlight body 100% 同文**——B1 swap 反向后这条会自然解决。
3. **Architecture mermaid 在 r4 未受 320px 影响**（CSS scope 只作用于 `.flow-cell`），正确。

---

## D. 是否收敛

**不收敛, 但 round-5 窄到 3 处, 不需要 round-6**：

1. **B2（AFTER 失读, P0）** — 改 demo 或 CSS, 任选一。视觉硬伤, 不能 ship。
2. **B1（Top risk swap 反了, P1）** — 1 处 render.py 改动 + demo 风险条目复用 description/note 分工。
3. **B6（算法手工复跑, P0 验证空白）** — 半小时 simulate, 不动代码。

剩下 B3/B4/B5/B7/C1-C3 都是 P2, 顺带做或推到后续。

**不直接 ship v1 的原因**：r4 解掉 r3 五条 P1 中的四条，但 B2 是新引入的视觉退化——首次读者一眼会怀疑"图坏了"，比 r3 的"BEFORE 太高"更伤信任。B1 swap 方向也选错。两者都属"半步走错, 再走半步就到"。

---

## 结论

Round 4 在风险信号、commits 折叠、TOC active、红警 demo 上有质提升，叙事密度达可用线。剩下 **1 个 CSS/demo 修复 + 1 个 swap 反向 + 1 次手工算法验证**，<1 小时工作量。**Round-5 收尾后即可 ship**, 不需 round-6。
