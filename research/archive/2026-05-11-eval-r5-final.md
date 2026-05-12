# Round-5 最终验证 · impl-explain

基于 r5 `fullpage.png`（1400×5800）+ r4 基准对照 + render.py / SKILL.md / demo JSON / 算法实测报告核对。

---

## A. 三处修复是否真落地

### A1. B1 — Top risk swap（P1）→ **解决**

r5 截图（Risks 区域）的 Top risk 卡片现在主行是 "Scheduler 单进程跑，多副本部署会同时跑造成 DB 写冲突 — 待缓解"——纯业务陈述，不再假设技术栈。下面 italic Fraunces 13px secondary 行写 "多副本场景下两个调度器会争抢同一 SourceSyncDefinition, 触发 INSERT 主键冲突；需要 leader election 才能上 K8s rollingUpdate, 暂未做"，技术细节降级到二级，r4 评估的 swap 方向反过来了。render.py L1202-1212 / CSS L514-522 实现一致。30 秒读者能在主行读完业务结论, 想深挖再看 italic 行——分工正确。

### A2. B2 — AFTER cell 失读（P0 视觉）→ **未解决**

逐像素对比 r5 vs r4 的 BEFORE/AFTER 截图（crop y=2000–3100）：**两版几乎完全一致**, AFTER cell 仍然是一条横向窄带, 5 节点链字号约 6-7px, 完全失读。时间戳确认 r5 PNG (16:20) 晚于 render.py (16:18), 截图就是 CSS 改动后的真实输出, 不是 stale 缓存。CSS 改动（`align-items: stretch` + `flex: 1` + 删 `max-height` / `width: auto !important`, 见 render.py L643-666）方向对, **但根因不是 CSS 容器**——是 `flowchart LR` 五节点链的天然 SVG aspect ratio 在 cell 宽度受限时被 `max-width:100%; height:auto` 等比缩成扁条。容器变高了, SVG 不会变高。R5 这个改动属于"看着像 fix, 但视觉退化没消"。

**剩余可行方案**（任一, 半小时）：
- 改 demo JSON 把 `data_flow.after` 从 `flowchart LR` 改 `flowchart TB`（和 BEFORE 一致竖排）；
- 或在 `.flow-cell .mermaid svg` 加 `min-width: 100%` 强制占满 cell 宽（SVG 等比放大文字也会跟着大）；
- 或 cell 加 `min-height: 460px` + svg `height: 100%` + `width: auto`, 让 SVG 由高度反推宽度。

### A3. B6 — 算法实测（P0 验证空白）→ **解决**

`research/2026-05-11-algo-empirical-verification.md` 实测 184 plans, 当前分支 commits 跑下来 top1=`rss-failed-source-cleanup` (36), top2=`content-backend-pipeline-run-config` (34), diff=2 < 阈值 3, **触发问用户**——正是想要的行为。Round-3 失败模式（无关 plan 占 top1 + diff=6 自动选错）经 boilerplate 过滤 + 阈值 2→3 + top1<5 安全网后被消除。证据级别够: 真仓库 + 真 commits + 真 plan 量级, 不是 toy case, 可以收下。

---

## B. Round-5 改动新引入问题

- **flow-grid stretch 后 cell 高度对齐**: BEFORE / AFTER cell 外框等高, 无空白拉伸异常。但 AFTER 内 SVG 被 mermaid 自己渲染成扁带, cell 内部出现大面积留白——视觉上更显得"是空的", 比 r4 还略糟。
- **risk-highlight `.hl-note` 与主行视觉关系**: italic Fraunces 13px secondary 与上方 15px sans-serif 主行层次清晰, 留白合理, 主从分工成立, 无视觉冲突。

---

## C. 最终 ship 判断

**结论: 仍需 round-6（窄到 1 条, 不凑数）**

不能直接 ship 的原因: **B2 P0 视觉硬伤没消除**——AFTER 节点 6-7px 失读, 首次读者一眼会怀疑"AFTER 是不是渲染坏了 / 是不是空的", 比 r3 的"BEFORE 太高"更伤信任。Round-5 改了 CSS 但根因（mermaid LR 链 + svg height:auto 的等比缩放）没动, **看起来动了, 实际没动**。

Round-6 唯一动作:
- **B2 收尾**: demo JSON `data_flow.after` 改 `flowchart TB`（最稳, 0 行 CSS）, 或者按 A2 给的 CSS 方案选一。10 分钟内可验。

B1/B6 都干净落地; B3 (SKILL.md L156 措辞矛盾) / B4 (mitigation 同义词 regex) / B5 (manifest 首次失败文案) / B7 (commits 折叠浏览器交互) 全 P2, 不阻塞 ship, 可推后续。

**理由一句话**: 三处修复里 B1 / B6 真到位, 但 B2 的视觉退化没消除, ship 出去用户会怀疑图坏了——再走 10 分钟就到位。
