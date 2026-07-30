# 优惠券系统代码架构重构计划

## 1. 重构背景

当前项目的后端路由、数据库模型、AI 服务、Jinja2 页面模板和静态资源集中在 `coupon_system/` 目录。虽然现有结构可以支持本地演示，但前端、后端、AI 和测试团队在同一目录中并行开发时，容易出现职责边界不清、代码相互依赖、修改冲突和验证困难等问题。

本次重构计划将生产代码和测试代码按照团队职责拆分到以下目录：

- `api/`：后端接口、业务逻辑、数据库和认证。
- `ui/`：页面模板、样式和浏览器端交互。
- `ai/`：Bedrock 接入、智能推荐、风险检测和规则降级。
- `test/`：单元测试、集成测试、并发测试和端到端测试。

建议采用“先建立基线、再物理拆分、随后接口解耦、最后删除旧目录”的渐进式方案，避免一次性重写导致现有登录、领券和核销流程失效。

## 2. 重构目标

重构完成后应满足以下目标：

1. 前端、后端、AI 和测试代码分别进入明确的目录。
2. UI 不直接访问数据库或 AI 的内部实现。
3. AI 模块不直接依赖 Flask 路由或 SQLAlchemy ORM 对象。
4. 后端通过稳定接口调用 AI 推荐和风险检测服务。
5. 前后端通过明确且可版本化的 API 契约通信。
6. 测试代码不进入生产模块，生产代码不反向依赖测试代码。
7. 保留现有用户、活动、优惠券和风险日志数据。
8. 保持登录、活动管理、领券、核销、广播和统计流程可运行。
9. 支持不同职责的团队成员在各自目录内独立开发和评审。

## 3. 目标目录结构

目录名建议统一使用小写，因此 AI 部分使用 `ai/`：

```text
SRCG_0730_coupon/
├── README.md
├── project_description.md
├── project_refact.md
├── .env.example
│
├── api/
│   ├── README_API.md
│   ├── requirements.txt
│   ├── run.py
│   ├── config.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── extensions.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── campaign.py
│   │   │   ├── coupon.py
│   │   │   ├── risk_log.py
│   │   │   └── notification.py
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── operator.py
│   │   │   ├── user.py
│   │   │   ├── verifier.py
│   │   │   └── admin.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── campaign_service.py
│   │   │   ├── coupon_service.py
│   │   │   ├── verification_service.py
│   │   │   ├── notification_service.py
│   │   │   └── statistics_service.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── campaign_repository.py
│   │   │   ├── coupon_repository.py
│   │   │   └── user_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── campaign.py
│   │   │   ├── coupon.py
│   │   │   └── user.py
│   │   │
│   │   └── security/
│   │       └── decorators.py
│   │
│   ├── openapi/
│   │   └── openapi.yaml
│   └── data/
│       └── coupon.db
│
├── ui/
│   ├── README_UI.md
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── operator/
│   │   ├── user/
│   │   ├── verifier/
│   │   └── admin/
│   └── static/
│       ├── css/
│       ├── js/
│       │   ├── api-client.js
│       │   ├── auth.js
│       │   ├── operator.js
│       │   ├── user.js
│       │   ├── verifier.js
│       │   └── admin.js
│       └── images/
│
├── ai/
│   ├── README_AI.md
│   ├── requirements.txt
│   ├── config.py
│   ├── contracts.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── bedrock.py
│   ├── services/
│   │   ├── recommendation.py
│   │   └── risk_assessment.py
│   ├── fallback/
│   │   ├── recommendation_rules.py
│   │   └── risk_rules.py
│   └── prompts/
│       ├── recommendation.py
│       └── risk_assessment.py
│
├── test/
│   ├── README_TEST.md
│   ├── conftest.py
│   ├── fixtures/
│   ├── unit/
│   │   ├── api/
│   │   ├── ai/
│   │   └── ui/
│   ├── integration/
│   ├── concurrency/
│   └── e2e/
│
└── coupon_system/
    └── 迁移完成并通过验证后删除
```

## 4. 模块职责和依赖边界

### 4.1 API 模块

`api/` 负责：

- Flask 应用创建和配置。
- 用户认证、Session 和角色权限。
- SQLAlchemy 模型和数据库事务。
- 活动管理。
- 原子领券。
- 优惠券核销。
- 广播通知。
- 积分处理。
- 管理员统计。
- 调用 AI 模块。
- 向 UI 暴露 `/api/v1/*` 接口。

后端建议采用分层结构：

```text
HTTP Route
    ↓
Service（业务规则和事务）
    ↓
Repository（数据库访问）
    ↓
SQLAlchemy / SQLite
```

路由层只负责身份校验、请求参数解析和响应构造。限领、库存扣减、积分、过期和核销等规则放入 Service 层，数据库查询和更新逐步封装到 Repository 层。

### 4.2 UI 模块

`ui/` 负责：

- Jinja2 页面模板。
- CSS 样式。
- 浏览器端 JavaScript。
- 表单和页面交互。
- 调用后端 API。
- 展示推荐、库存、错误和核销结果。

UI 迁移建议分两步：

1. **物理拆分阶段**：将模板和静态资源移到 `ui/`，由 Flask 配置外部模板和静态资源路径，尽量保持现有页面行为。
2. **接口解耦阶段**：逐步将领券、活动管理、核销和统计数据改为调用 `/api/v1/*` JSON API，减少模板与后端内部实现的耦合。

第一阶段可以使用类似配置：

```python
Flask(
    __name__,
    template_folder="../../ui/templates",
    static_folder="../../ui/static",
)
```

### 4.3 AI 模块

`ai/` 负责：

- Bedrock Bearer Token HTTP 调用。
- boto3 SDK 调用。
- Converse 请求和响应解析。
- 推荐 Prompt。
- 风控 Prompt。
- 推荐规则降级。
- 风控规则降级。
- AI 服务状态信息。

AI 模块不能直接接收 SQLAlchemy 的 `User` 或 `Campaign` 对象，应使用普通字典或 DTO。例如：

```python
user_profile = {
    "age": 25,
    "gender": "female",
    "hobbies": ["运动", "美食"],
    "occupation": "engineer",
    "points": 100,
}

campaigns = [
    {
        "id": 1,
        "name": "运动用品券",
        "amount": 50,
        "stock": 10,
        "days_left": 3,
        "description": "运动用品专用",
    }
]
```

建议通过 `contracts.py` 定义两个稳定接口：

```python
recommend_coupons(user_profile, campaigns)
assess_risk(user_context, action_history)
```

后端只依赖接口和返回结构，不关心底层使用 Bedrock 还是规则引擎。

### 4.4 Test 模块

`test/` 负责全部验证代码：

- `unit/api/`：后端 Service、权限和参数校验测试。
- `unit/ai/`：推荐规则、风控规则和 Bedrock 响应解析测试。
- `unit/ui/`：JavaScript 工具和页面组件测试。
- `integration/`：API、数据库和 AI Mock 联调测试。
- `concurrency/`：库存并发扣减和幂等测试。
- `e2e/`：登录、领券、核销和统计完整流程测试。
- `fixtures/`：用户、活动、优惠券和数据库样本。

测试应使用独立临时数据库，不能修改开发数据库。普通测试中的 Bedrock 调用必须使用 Mock，避免产生真实网络依赖和调用费用。

## 5. 依赖方向

重构后建议严格遵守以下依赖关系：

```text
UI ──HTTP/API──> API ──Interface/DTO──> AI
                       │
                       └──> Database

Test ──> UI / API / AI
```

禁止以下依赖：

- AI 导入 API 的 ORM 模型。
- UI 访问数据库文件。
- UI 调用 Bedrock。
- API 导入测试模块。
- AI 或 UI 依赖具体的测试 Fixture。

## 6. 现有文件迁移关系

| 当前文件 | 目标位置 |
|---|---|
| `coupon_system/run.py` | `api/run.py` |
| `coupon_system/config.py` | 拆分到 `api/config.py` 和 `ai/config.py` |
| `coupon_system/app/__init__.py` | `api/app/__init__.py` |
| `coupon_system/app/models.py` | 拆分到 `api/app/models/` |
| `coupon_system/app/auth.py` | `api/app/routes/auth.py` |
| `coupon_system/app/decorators.py` | `api/app/security/decorators.py` |
| `coupon_system/app/operator.py` | `api/app/routes/operator.py` 和对应 Services |
| `coupon_system/app/user_bp.py` | `api/app/routes/user.py` 和对应 Services |
| `coupon_system/app/verifier.py` | `api/app/routes/verifier.py` 和对应 Services |
| `coupon_system/app/admin_bp.py` | `api/app/routes/admin.py` 和对应 Services |
| `coupon_system/app/ai_service.py` | 拆分到 `ai/providers/`、`ai/services/` 和 `ai/fallback/` |
| `coupon_system/templates/*` | `ui/templates/*` |
| `coupon_system/static/*` | `ui/static/*` |
| `coupon_system/coupon.db` | `api/data/coupon.db` |
| `coupon_system/requirements.txt` | 拆分到 `api/requirements.txt` 和 `ai/requirements.txt` |
| `coupon_system/bedrock.service.txt` | 移到 `ai/` 作为参考资料或删除 |
| `api/README_API.md` | 保留并补充正式接口说明 |
| `ui/README_UI.md` | 保留并补充页面开发说明 |
| `test/README_TEST.md` | 保留并补充测试执行说明 |

迁移时必须同步更新 Python import、模板路径、静态资源 URL、数据库 URI、启动脚本和环境变量加载路径。

## 7. 分阶段实施计划

### 阶段 0：建立重构基线

目标：确保重构前后行为可比较、数据可恢复。

任务：

1. 记录当前安装和启动方式。
2. 备份 `coupon.db`。
3. 固化四类演示账号和基础活动数据。
4. 记录登录、活动创建、领券、核销、广播和统计的手工验证步骤。
5. 确认 `.env` 已被 Git 忽略。
6. 创建独立重构分支。
7. 记录现有 API 路由和关键响应格式。

验收标准：

- 原系统可以正常启动。
- 核心竞赛演示流程可以完成。
- 数据库已备份并可以恢复。
- 重构基线和验证步骤已记录。

### 阶段 1：创建新目录骨架

任务：

1. 建立 `api/`、`ui/`、`ai/` 和 `test/` 的目标目录。
2. 添加必要的 `__init__.py`。
3. 为每个目录补充职责和开发说明。
4. 建立新的依赖文件和启动入口骨架。
5. 暂时保留 `coupon_system/`，不删除现有实现。

验收标准：

- 新 Python 包可以被正确导入。
- 新目录职责清晰。
- 旧系统仍可正常运行。

### 阶段 2：提取 AI 模块

AI 与页面和数据库之间相对独立，适合优先迁移。

任务：

1. 从 `ai_service.py` 提取 Bedrock Provider。
2. 分离推荐 Service 和风控 Service。
3. 分离推荐与风控规则降级。
4. 将 Prompt 移到独立模块。
5. 定义 AI 输入输出 DTO 和异常类型。
6. 移除 AI 对 SQLAlchemy 模型的直接依赖。
7. 后端通过统一接口调用 AI。
8. 为 Bedrock 超时、认证失败、无效 JSON 和规则降级添加测试。

验收标准：

- Bearer Token 模式仍可调用。
- boto3 SDK 模式仍可调用。
- AI 不可用时推荐和风控自动降级。
- `ai/` 不导入 `api/app/models`。
- AI 单元测试不依赖真实 Bedrock。

### 阶段 3：拆分后端

任务：

1. 迁移 Flask 应用工厂和扩展初始化。
2. 将 `models.py` 按领域模型拆分。
3. 迁移认证和角色装饰器。
4. 迁移各角色 Blueprint。
5. 将复杂业务逻辑下沉到 Service 层。
6. 将数据库查询逐步封装到 Repository 层。
7. 统一异常和 JSON 响应格式。
8. 保持现有数据库表结构兼容。
9. 将接口统一到 `/api/v1` 前缀。
10. 修复 SQLite 下库存扣减的原子性问题。

推荐统一响应格式：

```json
{
  "success": true,
  "data": {},
  "message": "领取成功",
  "error": null
}
```

验收标准：

- 四类角色权限与原系统一致。
- 原有数据库可以继续使用。
- 登录、活动、领券、核销、通知和统计接口全部正常。
- 路由中不再包含大段数据库和业务逻辑。
- 并发领取不会导致库存为负或超发。

### 阶段 4：迁移 UI

任务：

1. 将模板迁移到 `ui/templates/`。
2. 将 CSS 和 JavaScript 迁移到 `ui/static/`。
3. 修改 Flask 模板和静态资源加载路径。
4. 提取统一的 `api-client.js`。
5. 清理模板中的内联 JavaScript。
6. 按角色拆分页面 JavaScript。
7. 逐页将数据操作切换到 `/api/v1`。
8. 统一成功、失败、未登录和无权限提示。
9. 保持页面 URL 和用户操作习惯尽量不变。

验收标准：

- 页面样式没有明显回归。
- 登录、活动管理、领券、核销和统计均可操作。
- UI 不导入后端 Python 代码。
- UI 不直接访问数据库或 AI 服务。

### 阶段 5：建立测试体系

优先补充以下高风险场景：

1. 库存为 N 时，N+1 个并发领取只允许 N 个成功。
2. 同一用户达到限领数量后不能继续领取。
3. 过期优惠券不能核销。
4. 重复核销返回幂等结果且不重复增加积分。
5. 风控在配置阈值处准确触发。
6. 定向广播只有目标用户可见。
7. 四种角色不能访问其他角色的受限接口。
8. Bedrock 异常时正确使用规则降级。
9. 独立有效期与活动有效期计算正确。
10. 管理员统计数据准确。
11. 预约活动到达发布时间后展示和领券状态一致。

验收标准：

- 测试可以通过一条命令运行。
- 测试使用独立临时数据库。
- 普通测试不发起真实 Bedrock 请求。
- 关键验收流程具备自动化覆盖。

### 阶段 6：联调、切换和清理

任务：

1. 对比新旧系统的核心业务结果。
2. 执行完整回归测试。
3. 更新根目录 README。
4. 更新安装、配置和启动命令。
5. 更新 `.gitignore` 和 `.env.example`。
6. 清理旧 import 和临时兼容代码。
7. 确认没有代码继续引用 `coupon_system/`。
8. 完成数据备份后删除或归档旧目录。

验收标准：

- 新目录成为唯一运行入口。
- 删除旧 `coupon_system/` 后系统仍能启动。
- 原有数据可以使用。
- 文档与实际启动方式一致。
- 各团队可以在自己的目录中独立工作。

## 8. 建议优先定义的 API 契约

在大规模迁移之前，建议先确定以下接口：

```text
POST   /api/v1/auth/login
POST   /api/v1/auth/register
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

GET    /api/v1/campaigns
POST   /api/v1/campaigns
GET    /api/v1/campaigns/{id}
PUT    /api/v1/campaigns/{id}
GET    /api/v1/campaigns/{id}/insights

POST   /api/v1/campaigns/{id}/claim
GET    /api/v1/users/me/coupons
GET    /api/v1/users/me/recommendations
GET    /api/v1/users/me/notifications
GET    /api/v1/users/me/profile
PUT    /api/v1/users/me/profile

POST   /api/v1/verifications/search
POST   /api/v1/verifications/{couponId}
POST   /api/v1/verifications/by-code
GET    /api/v1/verifications/history

GET    /api/v1/risk-logs
POST   /api/v1/risk-logs/{id}/resolve
POST   /api/v1/notifications

GET    /api/v1/admin/statistics
GET    /api/v1/admin/anomalies
```

正式契约保存在：

```text
api/openapi/openapi.yaml
```

接口或 DTO 变更应先更新 OpenAPI，再由前端、后端、AI 和测试团队共同确认。

## 9. 配置和依赖管理

### 9.1 环境变量

建议保留一个统一的根目录 `.env` 或由启动环境注入变量，不要在多个模块中复制真实密钥。可以创建不包含秘密值的 `.env.example`，列出：

- Flask Secret Key。
- 数据库地址。
- Bedrock Region。
- Bedrock Model ID。
- Bedrock Bearer Token 占位符。
- AI Mock 模式。
- 风控时间窗口和次数阈值。
- 积分参数。

### 9.2 Python 依赖

初期可保留一个统一依赖文件以降低迁移风险，待边界稳定后再拆分：

- `api/requirements.txt`：Flask、SQLAlchemy、Flask-Login 等。
- `ai/requirements.txt`：boto3、requests 等。
- 测试依赖可放在独立测试依赖文件中。

如果 API 和 AI 仍运行在同一 Python 进程中，应避免安装出不兼容的重复版本。

### 9.3 数据库

目录重构阶段不同时修改数据库结构。优先移动数据库路径并验证兼容性，之后再单独引入数据库迁移工具或调整表结构。

## 10. 团队职责建议

| 团队 | 负责目录 | 主要责任 |
|---|---|---|
| 后端团队 | `api/` | Flask、业务逻辑、数据库、认证、接口 |
| 前端团队 | `ui/` | 页面、样式、交互、API Client |
| AI 团队 | `ai/` | Bedrock、Prompt、推荐、风控、规则降级 |
| 测试团队 | `test/` | 单元、接口、并发、E2E 和测试数据 |
| 全团队共同维护 | 根目录和 API 契约 | README、环境变量模板、OpenAPI 和发布约定 |

建议建立以下协作规则：

1. API 和 DTO 修改必须经过前端、后端、AI 和测试负责人评审。
2. 每个目录维护自己的 README、启动方式和验证命令。
3. 跨目录修改应拆成小提交，避免一次提交同时包含大量移动和功能变更。
4. 文件移动提交与业务逻辑修改提交尽量分开。
5. 各模块负责人对本目录测试和文档负责。

## 11. 主要风险和控制措施

### 11.1 一次性迁移风险

不要直接剪切全部文件后统一修复。应按 AI、API、UI、Test 的阶段逐步迁移，每个阶段保持系统可启动。

### 11.2 数据库风险

不要在目录迁移时同时重构数据库结构。移动数据库前先备份，并通过配置控制数据库路径。

### 11.3 隐性耦合风险

AI 当前直接使用 ORM 对象，页面路由也包含业务逻辑。必须通过 DTO、Service 和 API 契约消除这些隐性依赖，否则只移动文件无法实现真正解耦。

### 11.4 配置和秘密泄漏风险

不要将 `.env` 复制到多个模块。真实 Bedrock Token、Secret Key 和 AWS 凭证不能进入文档、测试数据或版本库。

### 11.5 测试调用真实 AI 的风险

自动化测试默认使用 Mock Provider。真实 Bedrock 测试应单独标记，并且只在明确配置时运行。

### 11.6 现有业务回归风险

每完成一个阶段，都要验证登录、活动管理、领券、限领、库存、核销、幂等、积分、广播、推荐和风控。

### 11.7 并发库存风险

现有 SQLite 环境中的 `with_for_update()` 不能可靠提供行级锁。API 拆分阶段应优先改成数据库条件原子更新，并通过并发测试验证。

## 12. 推荐执行顺序

```text
建立重构基线
    ↓
创建目录骨架
    ↓
提取 AI 模块
    ↓
拆分 API 和业务 Service
    ↓
迁移 UI
    ↓
建立测试体系
    ↓
新旧系统联调与回归
    ↓
删除或归档 coupon_system
```

不建议同时并行迁移所有模块。AI 接口和 API 契约应先稳定，前端和测试团队再基于契约开展并行工作。

## 13. 完成定义

本次重构只有同时满足以下条件才能视为完成：

- `api/`、`ui/`、`ai/` 和 `test/` 职责明确。
- 新目录是唯一有效代码入口。
- `coupon_system/` 已删除或只作为只读归档存在。
- AI 不依赖 ORM 模型。
- UI 通过 API 获取和修改业务数据。
- 核心 API 有明确的 OpenAPI 契约。
- 核心业务具备自动化测试。
- 并发领取不会超发。
- 重复核销保持幂等。
- Bedrock 不可用时可以正常降级。
- 旧数据库数据仍可使用。
- 启动、配置、测试和团队协作说明已经更新。

## 14. 总结

该重构分为两个核心层次：

1. **物理拆分**：先将后端、前端、AI 和测试代码移动到团队对应目录，快速降低文件冲突并明确所有权。
2. **架构解耦**：通过 Service、Repository、DTO、AI Contract 和 `/api/v1` 契约消除跨模块隐式依赖。

采用渐进迁移可以在保持现有竞赛演示流程可运行的同时，让前端、后端、AI 和测试团队尽快分头开发。重构过程中应优先保证数据库兼容、领券库存一致性、核销幂等和 AI 降级能力，再逐步完善接口契约、测试体系与生产安全配置。
