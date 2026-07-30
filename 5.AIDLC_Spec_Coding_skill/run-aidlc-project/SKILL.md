---
name: run-aidlc-project
description: "Run and resume a five-stage AI Development Life Cycle (AIDLC) for software projects: requirements analysis, design documentation, implementation planning, task implementation, and real-environment testing and bug fixing. Use when Codex needs to initialize or continue an `.aidlc`-managed project, turn vague requirements into traceable documents, create architecture and API designs, produce ordered implementation tasks, implement from `.aidlc/tasks.md`, or validate and repair an application against its requirements. 适用于用户要求使用 AIDLC 五步法、继续现有 `.aidlc` 项目、生成需求/设计/任务文档、按任务开发，或执行真实测试与缺陷修复。"
---

# Run AIDLC Project

把 `.aidlc` 作为项目事实来源和中断恢复日志，按“需求 -> 设计 -> 计划 -> 实现 -> 测试”推进软件交付。保持产物可追踪、阶段可恢复、实现可验收。

## 基本约定

- 使用用户输入所采用的区域语言回复并编写 AIDLC 文档；代码标识符遵循项目惯例。
- 在目标项目根目录工作。新项目可运行 `scripts/init_aidlc.sh <项目根目录>`；该脚本只补齐目录，不覆盖文件。
- 开始前检查已有 `.aidlc`、`src`、版本控制状态和项目说明。保留用户已有改动，不重建已完成产物。
- 把每次计划调整、关键决定、问题、回答、执行结果和阻塞原因写入对应计划文件，使新会话只读文件即可恢复。
- 优先核心价值和直接方案。不要扩展用户未要求的业务范围，不要引入无必要的服务、依赖或抽象。
- 用户明确指定阶段时执行该阶段，但先验证其前置产物。未指定时按下方规则定位当前阶段。
- 仅在满足阶段完成门禁后进入下一阶段。不得用“文档已创建”代替内容完整或验证通过。

## 定位当前阶段

按顺序检查，选择第一个未满足完成条件的阶段：

1. **需求分析**：`.aidlc/requirements/` 缺少完整需求清单，或 `req-plan.md` 有未完成项/未回答问题。
2. **设计文档**：需求已完成，但 `.aidlc/design/` 未覆盖架构、数据、接口、前端和技术栈，或 `design-plan.md` 未完成。
3. **实现计划**：设计已完成，但 `.aidlc/tasks.md` 不存在、内容不完整或尚未获得用户认可。
4. **任务实现**：任务已认可，但仍有未勾选任务。
5. **测试修复**：实现任务均完成，但测试计划缺失、仍有未完成测试，或修复后尚未回归。

如果存在计划文件，先完整读取该文件及对应阶段已生成产物，再从最后一个未完成项继续。不要重复已记录的问题或覆盖已有回答。

## 阶段路由

### 1. 需求分析

先阅读 [requirements-stage.md](references/requirements-stage.md)，再创建或恢复 `.aidlc/plan/req-plan.md`。分析初始需求，集中提出少量会改变范围、验收或约束的关键问题，并用 `[Question]`/`[Answer]` 记录。

存在空白 `[Answer]` 时停止该阶段，清楚告知用户需要回答的问题；不要自行补答。答案齐备后生成需求文档和带唯一编号的完整需求清单，并更新计划复选框。

### 2. 设计文档

先完整读取需求产物，再阅读 [design-stage.md](references/design-stage.md)，创建或恢复 `.aidlc/plan/design-plan.md`。按高内聚、低耦合划分领域，描述架构、数据、接口、前端和技术栈，不编写具体实现代码。

只对高影响且无法从项目上下文确定的技术决策使用 `[Question]`/`[Answer]`。存在空白答案时等待技术顾问回复；答案齐备后完成设计并建立需求到设计的追踪关系。

### 3. 实现计划

完整读取需求和设计文件，再阅读 [implementation-planning-stage.md](references/implementation-planning-stage.md)。生成或修订 `.aidlc/tasks.md`，按依赖顺序组织可独立验收、粒度适中的任务。

生成后交由用户审阅。将审阅状态记入文件；用户未明确认可前，不进入批量实现。用户要求直接继续实现可视为认可，但仍需记录。

### 4. 任务实现

阅读 [implementation-stage.md](references/implementation-stage.md)，完整检查现有 `src/` 和项目配置，然后从 `.aidlc/tasks.md` 第一个未完成任务开始。每个任务开始前亲自读取其需求、设计和外部 API 引用。

实现、测试并满足该任务验收标准后才勾选复选框。持续执行后续任务，除非遇到真实阻塞、用户暂停或必须由用户决定的破坏性/外部操作。

### 5. 测试与修复

完整读取需求文件，再阅读 [testing-stage.md](references/testing-stage.md)。创建或恢复 `.aidlc/plan/test-plan.md`，在真实运行环境中执行以用户场景为中心的功能、集成和必要非功能测试。

失败时记录现象和证据，定位根因，修复后重跑失败用例。只要发生过代码修复，就追加并完成一轮受影响范围的回归测试。

## 阶段门禁

进入下一阶段前确认：

- 当前计划文件无未完成计划项和空白 `[Answer]`。
- 必需产物存在，内容相互一致，并能追踪到上游编号。
- 本阶段验证证据已记录；测试阶段必须来自实际命令、日志、响应或 UI 操作，不接受纯理论判断。
- 未解决风险、范围外事项和外部依赖已明确记录，而不是被静默忽略。

## 项目管理案例

当用户要构建本技能来源中的“智能项目任务管理平台”，或需求涉及任务管理、钉钉、AI PM、自动跟进 Agent 时，读取 [project-management-baseline.md](references/project-management-baseline.md)。把它作为初始需求输入，不把未确认的建议当成最终决定。

## 资源

- `scripts/init_aidlc.sh`：幂等创建 AIDLC 项目目录。
- `references/requirements-stage.md`：需求计划、文档结构和完整性门禁。
- `references/design-stage.md`：技术设计产物、决策记录和追踪规则。
- `references/implementation-planning-stage.md`：任务格式、依赖排序和验收规则。
- `references/implementation-stage.md`：逐任务实现与完成判定。
- `references/testing-stage.md`：真实测试、缺陷记录和回归规则。
- `references/project-management-baseline.md`：智能项目任务管理平台的初始需求基线。
