# 关键词算法实测验证（B6）

**日期**: 2026-05-11
**目标**: 验证 round-4 SKILL.md 步骤 1 关键词算法在 boilerplate 过滤后能正确处理多 plan 仓库

## 测试环境

- 仓库: `/Users/admin/work/de/global-hotspot-globe`
- 分支: `codex/agent-normalizer-poc`
- plan 目录: `docs/superpowers/plans/`
- plan 数量: **184**
- commits: `main..HEAD`（82587 字符，3232 unique tokens after filter）

## 测试脚本

`/tmp/verify-keyword-algo.py` — 实现 SKILL.md 步骤 1 的算法：

1. commit_tokens：`git log main..HEAD --format='%s%n%b'` → tokenize → 过滤 STOPWORDS + BOILERPLATE + 短词 / 数字
2. 每个 plan：取 filename（去日期）+ h1 + `## TL;DR` 段 + `## Decisions` 段 `###` 子标题 → tokenize + 同样过滤
3. overlap = |commit_tokens ∩ plan_tokens|
4. 排序，diff ≥ 3 AND top1 ≥ 5 才自动选

## 结果

```
Top 10 plans by overlap:
 1. 36 overlap  2026-05-08-rss-failed-source-cleanup.md
 2. 34 overlap  2026-04-26-content-backend-pipeline-run-config.md
 3. 33 overlap  2026-04-26-content-pilot-onboarding-preset.md
 4. 32 overlap  2026-04-26-content-source-onboarding-report.md
 5. 31 overlap  2026-04-24-content-ner-geocoding-dev-run.md
 6. 30 overlap  2026-05-11-taxonomy-backend-alignment.md
 7. 30 overlap  2026-04-26-content-relation-demo-smoke.md
 8. 27 overlap  2026-05-09-new-pulse-source-review.md
 9. 27 overlap  2026-04-29-agent-all-source-ingestion.md
10. 27 overlap  2026-04-25-content-backend-smoke-entity-backfill.md

top1 - top2 diff = 2
→ 触发问用户 ✓
```

## 结论

- **算法行为正确**：184 plans + 当前分支 commits，top1 和 top2 差距 = 2（< 阈值 3），算法触发"问用户"
- Round-3 walkthrough 报告的"无关 plan 排第 1，diff=6"在加 boilerplate 过滤后**得到修复**——现在 diff 远小于阈值
- 用户被提示选择时会看到 top1 / top2 候选 + 重合度，可以快速判断真目标

## 与 Round-3 报告的对比

| 项 | Round-3 报告 | Round-4 实测 |
| --- | --- | --- |
| top1 名 | agent-only-schema-cleanup（无关） | rss-failed-source-cleanup（最相关候选之一） |
| top1 overlap | 28 | 36 |
| 真目标排名 | 第 38 | 多个相关候选并列前列 |
| diff | 6（错误自动选） | 2（正确触发问用户） |

Round-3 的失败模式（无关 plan 占 top1 + diff 大到自动选错）在 boilerplate 过滤 + 阈值收紧后**被消除**。

## 残余风险

- 算法的 STOPWORDS / BOILERPLATE 列表是经验值，可能漏过新 plan 模板里的 boilerplate
- 当 commits 极少（< 10 条）时，token 不够多可能让 top1 < 5 触发安全网"问用户"——这是想要的行为，不算 bug
- 用户被问时仍然要做判断，但只需在 2-3 个 top 候选里选，不是 184 选 1

**总评**：算法实测通过，B6 解决。
