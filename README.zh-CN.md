# semantic-decision-lab

[English](README.md) | [日本語](README.ja.md) | **简体中文** | [한국어](README.ko.md) | [Français](README.fr.md)

[![PDDR validation](https://github.com/serevy/semantic-decision-lab/actions/workflows/pddr.yml/badge.svg?branch=main&event=push)](https://github.com/serevy/semantic-decision-lab/actions/workflows/pddr.yml)
[![GitHub Pages](https://github.com/serevy/semantic-decision-lab/actions/workflows/pages.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/pages.yml)
[![PDDR Kit v0.3.0](https://img.shields.io/badge/PDDR%20Kit-v0.3.0-0969da)](https://github.com/serevy/pddr-kit/releases/tag/v0.3.0)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/serevy/semantic-decision-lab?utm_source=oss&utm_medium=github&utm_campaign=serevy%2Fsemantic-decision-lab&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)](https://coderabbit.ai)

> **关于语义决策层的提供方中立实验：**将模糊状态转化为确定性系统可以使用的类型化概率决策。

核心问题不是“LLM 能做所有事情吗？”而是：

> **能否将语义判断隔离为一个小型、可测试的软件原语，同时由确定性代码继续控制执行、策略和安全？**

该代码库围绕编排、上下文选择、类型化交接、状态解读、领域门控、实时系统以及可互换的语义决策提供方，探讨了这一问题。

## 核心理念

语义层应回答**当前状态意味着什么**。确定性系统仍负责**接下来会发生什么**。

![语义决策核心架构](docs/assets/semantic-decision-core.svg)

这种分离使我们能够独立测试语义判断与执行逻辑。它还将不确定性、弃答、升级处理和提供商替换明确呈现出来，而不是将它们隐藏在单体代理中。

## 研究边界

2026 年的一次现有技术调研发现，在模型路由与级联、上下文和提示词压缩、结构化代理交接、对话及行动状态跟踪、语用学评估、轨迹与过程监督、高层具身规划以及中间表示等领域，已有大量相关工作。

因此，本实验室将这些技术视为**构建模块和基线**，而不将它们本身作为新颖性主张。共同研究边界更为聚焦：

> **能否将模糊的语义判断表示为具备不确定性感知能力的类型化状态及其转换，在保留下游行为的同时尽可能保持提供商可移植性，并始终让确定性执行、授权、策略及硬安全机制掌握控制权？**

在可行的情况下，实验应复用成熟方法，将定制工程投入到语义保真度、校准、弃答、状态转换、下游影响和权限边界。

有关证据及范围决定，请参见 [PDDR-0007](docs/records/PDDR-0007-focus-typed-semantic-state.md) 和 [#70 外部参考雷达](https://github.com/serevy/semantic-decision-lab/issues/70)。

## 研究地图

| 领域 | 研究问题 | 主要线索 |
|---|---|---|
| 编排 | 语义路由能否综合改善端到端任务成功率、成本、延迟以及升级处理和返工？ | [#1 AI Work Routing](https://github.com/serevy/semantic-decision-lab/issues/1) |
| 上下文与记忆 | 在保持下游决策行为的同时，可以压缩多少决策历史上下文？ | [#2 PDDR Context Selection](https://github.com/serevy/semantic-decision-lab/issues/2), [#74 下游任务成功评估](https://github.com/serevy/semantic-decision-lab/issues/74) |
| 交接 | 在保留约束、不确定性、证据来源以及所需下一步行动的前提下，最小的类型化交接是什么？ | [#3 Typed Handoff](https://github.com/serevy/semantic-decision-lab/issues/3) |
| 状态解释 | 能否在不虚构缺乏依据的确定性或授权的情况下，表示决策状态、语用状态和语义转换？ | [#4](https://github.com/serevy/semantic-decision-lab/issues/4), [#5](https://github.com/serevy/semantic-decision-lab/issues/5), [#9](https://github.com/serevy/semantic-decision-lab/issues/9) |
| 领域门控与发现 | 在有边界的领域工作流中，语义分类、评分、检索和排序可以在哪些环节发挥作用？ | [#6 Trading Strategy Gate](https://github.com/serevy/semantic-decision-lab/issues/6), [#7 VTuber Discovery](https://github.com/serevy/semantic-decision-lab/issues/7), [#8 Taste Discovery](https://github.com/serevy/semantic-decision-lab/issues/8) |
| 实时 / 具身 | 在延迟、漂移或模型策略变化时，能否让确定性硬安全保持独立，同时借助低延迟语义状态改善交互？ | [#10 Real-time / Embodied Decision Layer](https://github.com/serevy/semantic-decision-lab/issues/10) |
| 提供商可移植性 | 类型化决策契约能否跨托管和本地提供商保留语义、校准及可观察能力，而不只是 API 形式？ | [#81 System One provider portability](https://github.com/serevy/semantic-decision-lab/issues/81) |

本仓库把分类、评分、路由、检索、压缩、结构化交接、验证、轨迹分析及类型化中间表示视为成熟的构建模块。研究重点在于，当这些原语被组合为可靠的软件架构时，类型化语义状态及其转换能在多大程度上保持下游行为。

## 设计上与提供商无关

Jev 是这项工作中的重要提供方和参考点，但它**并不是研究的定义**。在可行的情况下，实验旨在将应用逻辑置于一个通用的类型化决策边界之后。

![与提供商无关的语义决策架构](docs/assets/provider-neutral-architecture.svg)

提供商比较会将不同维度分别对待：

- **契约兼容性**——是否可以使用相同的请求/响应结构？
- **语义质量**——决策是否正确地满足任务要求？
- **校准** — 概率是否代表下游自动化所假定的含义？
- **稳健性**——选项顺序、上下文长度、打包、弃答和故障行为
- **系统成本** — 延迟、内存、硬件、吞吐量和外部 API 成本

**API 兼容性并不等同于语义等价性。** 某个提供商可能很容易替换，但其行为差异可能大到需要采用不同的阈值或部署约束。

## 实验如何运作

该实验室以证据为先。实验设计和原始证据与持久的项目决策分开。

![实验依据和 PDDR 工作流](docs/assets/experiment-evidence-pddr.svg)

通用规则：

- 在评分提供商输出之前冻结评估条件；
- 保留首次运行的证据，而不是在发现失败后重写它；
- 明确记录版本协议、打包、数据集或提示词的变更；
- 在相关情况下与确定性基线和/或传统基线进行比较；
- 区分提供商拒绝或截断输入时的覆盖范围与正确性；
- 在复现之前，将上游基准测试的声明视为相关工作证据；
- 在发布特定于提供商的基准测试结果之前，请尊重提供商条款。

## 结果和可视化

README 有意**不是**实时排行榜。

稳定且冻结的发现日后可在此处以小型图表或摘要图的形式展示。详细的结果拆解、来源信息、诊断信息和交互式视图应放在实验产物、`docs/`或未来的 GitHub Pages 网站中。

这能让着陆页保持易读，同时避免一种常见的失败模式：那些颇具吸引力的图表悄然长存，甚至超过了生成它们的实验版本。

## 仓库布局

| 路径 | 用途 |
|---|---|
| `experiments/` | 可复现实验代码、数据集、评估器和面向证据的资源 |
| `docs/records/` | 已接受的 PDDR 决策记录 |
| `.pddr/` | PDDR Kit 工具、架构、验证和检查点支持 |
| `docs/` | 不属于落地页的支持性文档和研究笔记 |
| GitHub Issues | 假设、协议、中间观察结果、原始结果、失败情况和后续跟进 |

对于可能影响未来实验的外部实现和论文，请参见[#70 外部参考雷达](https://github.com/serevy/semantic-decision-lab/issues/70)。

## 研究记录

工作实验的详细信息保留在 GitHub Issues 中。只有当证据促成了一个值得在实验本身之外长期保留的项目、产品或流程决策时，才会创建 PDDR。

| 工件 | 角色 |
|---|---|
| GitHub Issue | 假设、协议、观察结果、原始证据、失败情况和后续跟进 |
| PDDR | 有证据支持的采用、拒绝、推迟、范围、后果和重新审议条件 |

本仓库在受管理的核心部分使用 [PDDR Kit](https://github.com/serevy/pddr-kit/releases/tag/v0.3.0) `v0.3.0`（于 [PR #145](https://github.com/serevy/semantic-decision-lab/pull/145) 更新）；此次核心迁移并未更新实验用 Evidence、决策记录或可选 Skills。[`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md) 界定了实验工作与持久决策记录之间的边界。
