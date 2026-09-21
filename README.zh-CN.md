# semantic-decision-lab

[English](README.md) | [日本語](README.ja.md) | **简体中文** | [한국어](README.ko.md) | [Français](README.fr.md)

面向 AI 编排、上下文选择、路由、交接和实时系统的语义决策层实验。

## 工作模型

本仓库将实验工作与需要长期保留的项目决策分开。

| 产物 | 用途 | 典型内容 |
|---|---|---|
| GitHub Issue | 实验待办与工作讨论串 | 假设、设置、任务、中间观察、原始结果、后续跟进 |
| PDDR | 重要决策的长期记录 | 基于证据的采纳、拒绝、暂缓、范围、后果和重新审议条件 |

运行或完成实验本身不会自动创建 PDDR。仅当证据促成一项重要的 Project、Product 或 Process 决策，且其理由需要跨越 Issue 生命周期长期保留时，才创建或更新 PDDR。

做出决策后，应将 Issue 与 PDDR 相互链接，并把原始实验细节保留在 Issue 中。

## PDDR

本仓库使用 [PDDR Kit](https://github.com/serevy/pddr-kit) `v0.1.0-rc.1`。

以 `.pddr/template.md` 为模板创建记录，将其保存到 `docs/records/` 目录下，并在审核前进行验证：

```bash
cp .pddr/template.md docs/records/PDDR-0002-short-title.md
python .pddr/pddr.py validate
```

第一条记录 [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md) 定义了 Issue 与决策记录之间的边界。
