# 优惠券发放与核销系统项目说明

## 1. 项目概述

本项目是一个本地单机部署的优惠券发放与核销系统。系统围绕优惠券活动创建、用户领券、优惠券核销、运营风控和数据统计构建，并接入 Amazon Bedrock 提供个性化推荐和异常行为检测能力。当 AI 服务不可用时，系统自动降级到本地规则引擎，以保证核心业务仍然可用。

项目的主要业务目标包括：

- 运营人员创建和管理优惠券活动。
- 普通用户浏览、领取和管理优惠券。
- 核销人员通过手机号或券码核销优惠券。
- 管理员查看活动统计和异常情况。
- 保证限领、库存扣减、过期校验和重复核销等核心规则。
- 使用 AI 提升优惠券推荐效果和领券风控能力。

主要需求和项目背景文档包括：

- `coupon_system/project_requirement.md`
- `coupon_system/3.SRCG_workshop_Requirement_V1.md`
- `coupon_system/4.SRCG_workshop_competation_intro.md`
- `coupon_system/project_bug.md`

竞赛演示的主要业务流程是：创建库存为 1 的活动，用户 A 领取成功，用户 B 因库存不足领取失败，用户 A 核销成功，再次核销返回已核销的幂等结果，用户 C 高频领券时触发风控拦截。

## 2. 技术栈

| 层面 | 技术 |
|---|---|
| Web 框架 | Flask 3、Jinja2 |
| 数据访问 | Flask-SQLAlchemy |
| 数据库 | SQLite |
| 身份认证 | Flask-Login、Session |
| 密码处理 | Werkzeug 密码哈希 |
| AI 服务 | Amazon Bedrock Converse API |
| AI 调用方式 | `requests` Bearer Token 或 `boto3` SDK |
| 前端 | 原生 HTML、CSS Grid、JavaScript |
| 配置 | python-dotenv、环境变量 |
| 部署方式 | 本地运行 `python run.py` |

## 3. 项目目录与模块职责

```text
SRCG_0730_coupon/
├── README.md
├── project_description.md
├── api/
│   └── README_API.md
├── test/
│   └── README_TEST.md
├── ui/
│   └── README_UI.md
└── coupon_system/
    ├── run.py
    ├── config.py
    ├── requirements.txt
    ├── coupon.db
    ├── project_requirement.md
    ├── project_bug.md
    ├── 3.SRCG_workshop_Requirement_V1.md
    ├── 4.SRCG_workshop_competation_intro.md
    ├── bedrock.service.txt
    ├── app/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── auth.py
    │   ├── decorators.py
    │   ├── operator.py
    │   ├── user_bp.py
    │   ├── verifier.py
    │   ├── admin_bp.py
    │   └── ai_service.py
    ├── templates/
    │   ├── base.html
    │   ├── login.html
    │   ├── register.html
    │   ├── operator/
    │   ├── user/
    │   ├── verifier/
    │   └── admin/
    └── static/
        ├── css/style.css
        └── js/app.js
```

各模块职责如下：

- `run.py`：应用启动入口，启动 Flask 开发服务器。
- `config.py`：数据库、Session、积分、AI、Bedrock 和风控参数配置。
- `app/__init__.py`：应用工厂，初始化数据库和登录管理器，注册各业务蓝图，创建表和演示数据。
- `app/models.py`：定义用户、活动、优惠券、风控日志和通知模型。
- `app/auth.py`：负责登录、注册、退出和登录后的角色跳转。
- `app/decorators.py`：实现 operator、user、verifier、admin 的角色权限检查。
- `app/operator.py`：实现活动创建、编辑、活动洞察、广播通知和风控日志管理。
- `app/user_bp.py`：实现用户首页、AI 推荐、领券、我的优惠券和个人资料。
- `app/verifier.py`：实现手机号查询、券码核销、按 ID 核销和核销历史。
- `app/admin_bp.py`：实现管理员统计面板。
- `app/ai_service.py`：实现 Bedrock Converse 调用、推荐、风险评估和规则降级。
- `bedrock.service.txt`：Bedrock 服务的 TypeScript 参考实现，不属于当前 Python 运行链路。
- `templates/`：各角色的 Jinja2 页面模板。
- `static/`：全局样式和浏览器端交互逻辑。
- `api/README_API.md`、`test/README_TEST.md`、`ui/README_UI.md`：当前主要是工作分工或说明文件，并非完整 API 契约、测试套件或 UI 规范。

## 4. 总体架构

```text
浏览器
  │
  ├── Jinja2 页面模板
  ├── static/css/style.css
  └── static/js/app.js
          │
          ▼
Flask Application Factory
app/__init__.py
  │
  ├── auth.py          登录、注册、退出
  ├── operator.py      活动、广播、风控管理
  ├── user_bp.py       推荐、领券、用户资料
  ├── verifier.py      查询和核销
  ├── admin_bp.py      统计面板
  ├── decorators.py    角色权限控制
  ├── ai_service.py    Bedrock 与规则降级
  └── models.py        SQLAlchemy 数据模型
          │
          ▼
        SQLite
      coupon.db
```

系统采用 Flask Blueprint 按角色划分业务模块。身份认证由 Flask-Login 管理，登录后通过角色装饰器限制访问范围。页面主要使用服务端 Jinja2 渲染，领券、查询和核销等局部交互使用原生 JavaScript 请求 JSON 接口。

## 5. 数据模型

### 5.1 User

`User` 表示系统用户，主要字段包括：

- `username`：唯一用户名。
- `password_hash`：密码哈希，不保存明文密码。
- `role`：`operator`、`user`、`verifier` 或 `admin`。
- `phone`：手机号。
- `age`、`gender`、`hobbies`、`occupation`：用户画像。
- `points`：用户积分。
- `last_login`、`created_at`：登录和创建时间。

一个用户可以领取多张优惠券、创建多个活动、发送通知、产生风险日志或作为核销人员执行核销。

### 5.2 Campaign

`Campaign` 表示优惠券活动，主要字段包括：

- 活动名称、面额和用途描述。
- 当前库存 `stock` 和初始库存 `initial_stock`。
- 开始时间和结束时间。
- 每用户限领数量。
- `draft`、`active`、`expired`、`cancelled` 状态。
- 是否预约发布及预约时间。
- 用户领券后的独立有效天数。
- 创建人员和创建时间。

模型提供领取率、核销率和当前是否可领取等计算属性。

### 5.3 Coupon

`Coupon` 表示用户实际领取到的优惠券，主要字段包括：

- 所属活动和持有用户。
- 唯一券码。
- `claimed`、`verified` 或 `expired` 状态。
- 领取时间、独立过期时间和核销时间。
- 执行核销的用户。

优惠券的实际有效期优先使用 `expires_at`；如果没有独立有效期，则使用所属活动的 `end_date`。

### 5.4 RiskLog

`RiskLog` 保存领券风险评估记录，包含：

- 用户和操作类型。
- 0 到 1 的风险评分。
- `allow`、`block` 或 `review` 决策。
- 决策原因和创建时间。

### 5.5 Notification

`Notification` 表示运营广播，包含：

- 消息内容。
- 全员或指定用户的目标类型。
- 指定用户 ID 列表。
- 可选的关联活动。
- 创建人员和创建时间。

### 5.6 主要关联关系

```text
User 1 ── N Campaign      用户创建活动
User 1 ── N Coupon        用户持有优惠券
Campaign 1 ── N Coupon    活动产生优惠券
User 1 ── N RiskLog       用户产生风控记录
User 1 ── N Notification  运营人员发送通知
User 1 ── N Coupon        核销人员执行核销
```

## 6. 用户角色和业务流程

### 6.1 运营人员

运营人员通过 `/operator/*` 路由完成以下工作：

1. 创建优惠券活动。
2. 设置名称、面额、库存、活动时间、限领数量、用途描述和领券后有效期。
3. 编辑已有活动。
4. 查看活动领取占比、领取记录和活动洞察。
5. 设置预约发布信息。
6. 发送全员或指定用户广播。
7. 查看风险日志并将异常记录标记为已处理。

主要页面包括：

- `templates/operator/dashboard.html`
- `templates/operator/campaign_form.html`
- `templates/operator/insights.html`
- `templates/operator/notifications.html`
- `templates/operator/risk_logs.html`

### 6.2 普通用户

普通用户通过 `/user/*` 完成以下流程：

1. 查看当前活动、系统广播和临期提醒。
2. 根据用户画像获得 AI 或规则引擎推荐排序。
3. 发起领券请求。
4. 系统检查活动状态、开始结束时间和风险决策。
5. 系统检查每用户限领数量和剩余库存。
6. 成功时扣减库存并生成唯一券码。
7. 用户获得领券积分。
8. 用户在“我的优惠券”中查看券码和状态。
9. 用户可以维护年龄、性别、爱好和职业等画像。

主要页面包括：

- `templates/user/dashboard.html`
- `templates/user/my_coupons.html`
- `templates/user/profile.html`

### 6.3 核销人员

核销人员通过 `/verifier/*` 完成以下流程：

1. 使用手机号查询用户当前可核销的优惠券。
2. 选择优惠券按 ID 核销，或直接输入券码核销。
3. 系统检查券是否存在、是否已核销以及是否过期。
4. 已核销的券重复提交时返回相同业务结果，不重复增加积分。
5. 未核销且有效的券被更新为 `verified`。
6. 系统记录核销人员和核销时间。
7. 优惠券持有用户和核销人员获得相应积分。
8. 核销人员可以查看自己的核销历史。

主要页面包括：

- `templates/verifier/dashboard.html`
- `templates/verifier/history.html`

页面预留了二维码扫描控件入口，但当前没有真实摄像头、二维码识别或扫码枪集成。

### 6.4 管理员

管理员通过 `/admin/dashboard` 查看系统统计信息，包括：

- 用户、活动和优惠券数量。
- 活动领取率。
- 优惠券核销率。
- 剩余库存。
- 风险和异常概览。

管理员模板包括：

- `templates/admin/dashboard.html`
- `templates/admin/anomalies.html`
- `templates/admin/statistics.html`

其中后两个模板当前缺少完整的后端路由接入。

## 7. 主要路由

### 7.1 认证

- `/`
- `/login`
- `/logout`
- `/register`

### 7.2 运营人员

- `/operator/dashboard`
- `/operator/campaigns/create`
- `/operator/campaigns/<id>/edit`
- `/operator/campaigns/<id>/insights`
- `/operator/risk-logs`
- `/operator/risk-logs/<id>/resolve`
- `/operator/notifications`

### 7.3 普通用户

- `/user/dashboard`
- `/user/claim/<campaign_id>`
- `/user/my-coupons`
- `/user/profile`

### 7.4 核销人员

- `/verifier/dashboard`
- `/verifier/search`
- `/verifier/verify/<coupon_id>`
- `/verifier/verify-by-code`
- `/verifier/history`

### 7.5 管理员

- `/admin/dashboard`

## 8. AI 服务架构

`app/ai_service.py` 支持三种运行方式。

### 8.1 Bearer Token 模式

当配置 `AWS_BEARER_TOKEN_BEDROCK` 时，系统通过 HTTP POST 调用 Bedrock Converse API，并使用 Bearer Token 认证。该模式优先于 SDK 模式。

### 8.2 boto3 SDK 模式

没有 Bearer Token 且未启用 Mock 模式时，系统尝试创建 `bedrock-runtime` 客户端，并通过 `converse()` 调用模型。

### 8.3 规则引擎降级

当 Bedrock 不可用、调用超时、返回格式错误或显式启用 Mock 模式时，推荐和风控自动切换到本地规则引擎。页面状态指示器会显示 Bedrock API、Bedrock SDK 或规则引擎降级模式。

### 8.4 个性化推荐

AI 推荐输入包括：

- 用户年龄、性别、爱好和职业。
- 用户当前积分。
- 活动名称、面额、库存、剩余天数和描述。

AI 返回活动排序、0 到 1 的评分及中文推荐理由。

规则引擎按以下因素计算推荐分数：

1. 即将到期程度。
2. 优惠券面额。
3. 库存稀缺程度。
4. 用户爱好与活动描述的匹配程度。

### 8.5 风险评估

领券前系统调用风险评估，输出：

```json
{
  "risk_score": 0.0,
  "decision": "allow",
  "reason": "风险判断原因"
}
```

AI 不可用时，规则引擎统计配置时间窗口内的历史领券行为，并根据操作次数返回 `allow`、`review` 或 `block`。

## 9. 核心需求实现情况

当前已经实现的主要需求包括：

- 四类角色登录和权限隔离。
- 运营人员创建、编辑和查看活动洞察。
- 用户注册、登录和个人画像维护。
- 每用户限领校验。
- 库存检查和扣减。
- 唯一优惠券码生成。
- 手机号查询候选优惠券。
- 按优惠券 ID 或券码核销。
- 重复核销业务幂等。
- 过期券拒绝核销。
- 领券、核销和过期相关的基础积分逻辑。
- AI 个性化推荐和本地规则降级。
- AI 风险评估和频率规则降级。
- 风控日志查询和处理。
- 广播通知。
- 管理员统计面板。
- 预约活动相关字段和部分展示逻辑。

`project_bug.md` 中记录的多领限制、售罄展示、CSS Grid、dotenv 加载和错误类型等问题，在当前实现中大部分已有对应修复。

## 10. 已识别的缺口与风险

### 10.1 SQLite 并发库存风险

领券逻辑使用 `Campaign.query.with_for_update()` 获取活动，但 SQLite 通常不会提供真正的行级 `SELECT FOR UPDATE` 锁。因此，在多个请求并发读取相同库存时，仍可能出现竞争条件。“库存为 N 时，N+1 个并发领取只有 N 个成功”这一验收项需要并发测试验证，或改为数据库条件更新，例如仅在 `stock > 0` 时原子执行 `stock = stock - 1` 并检查受影响行数。

### 10.2 风控触发次数可能偏一

规则风控在保存本次风险日志前统计历史操作次数。如果配置最大次数为 50，当前逻辑可能在第 51 次请求时才执行拦截，而需求演示预期第 50 次触发。应明确阈值是“达到最大值”还是“超过最大值”，并将本次操作计入判断。

### 10.3 定向广播未按用户过滤

用户 Dashboard 当前读取最近通知时没有根据 `target_type` 和 `target_users` 过滤。运营人员发送给指定用户的广播可能被其他用户看到。

### 10.4 预约活动展示与领券状态不一致

用户 Dashboard 为兼容旧数据，会展示已到预约时间的部分 `draft` 活动；但领券接口明确只允许 `active` 状态。因此可能出现用户可以看到活动，但点击领取后提示活动未开放的情况。系统需要统一预约到期后的状态转换策略。

### 10.5 临期提醒逻辑不完整

临期提醒查询首先根据 `Campaign.end_date` 过滤，随后才进行时间判断。该实现没有完全基于 `Coupon.effective_expiry`，可能遗漏使用独立 `expires_at` 的优惠券，也可能无法完整覆盖需求中的未来三天范围。

### 10.6 积分定时规则未完整实现

当前“过期未核销扣分”主要在核销时检测到过期后执行，没有后台任务自动扫描过期优惠券。“7 天未登录扣分”也没有调度器或定时任务实现。

### 10.7 管理员页面和权限路由不完整

`admin/anomalies.html` 和 `admin/statistics.html` 已存在，但没有对应的管理员路由。管理员 Dashboard 中查看全部风险记录的链接指向运营人员路由，可能因为角色装饰器返回 403。

### 10.8 二维码扫描仅为预留接口

核销页面存在二维码扫描相关 UI 入口，但没有摄像头权限、二维码解析或硬件扫码枪对接代码。

### 10.9 缺少自动化测试

项目没有可执行的单元测试、并发库存测试、API 契约测试或端到端测试。`test/README_TEST.md` 当前只是说明文件，无法验证关键验收项。

建议优先补充：

- N+1 并发领券测试。
- 同一用户限领测试。
- 高频领券风控边界测试。
- 过期核销测试。
- 重复核销幂等测试。
- 定向广播权限测试。
- 四角色路由权限测试。

### 10.10 缺少正式 API 契约

`api/README_API.md` 不是 OpenAPI 或其他机器可读的接口规范。当前接口行为主要由 Flask 路由和页面 JavaScript 隐式定义。

### 10.11 生产安全风险

当前配置适合本地演示，不适合直接部署到生产环境，主要风险包括：

- 可能使用默认 Secret Key。
- 包含演示账号和口令。
- `debug=True`。
- 开发服务器监听 `0.0.0.0`。
- 表单和 JSON 写操作缺少 CSRF 防护。
- 没有生产级 WSGI 服务器和反向代理配置。
- 没有请求限流、审计留存和数据库备份策略。

## 11. 启动和配置

在 Windows PowerShell 中进入项目目录：

```powershell
Set-Location "d:\0730\SRCG_0730_coupon\coupon_system"
python -m pip install -r requirements.txt
python run.py
```

默认访问地址：

```text
http://localhost:5000
```

主要 AI 环境变量包括：

- `AWS_BEARER_TOKEN_BEDROCK`
- `BEDROCK_MODEL_ID`
- `AWS_REGION`
- AWS SDK 凭证相关变量
- AI Mock 模式和 Bedrock 超时相关配置

敏感配置保存在 `.env` 中，不应提交到公开仓库或写入项目说明文档。

## 12. 建议的后续开发优先级

建议按以下顺序继续完善项目：

1. 修复库存扣减的数据库原子性并增加并发测试。
2. 修正风控阈值边界并添加频率测试。
3. 修复定向广播过滤和预约活动状态转换。
4. 统一优惠券实际有效期和临期提醒逻辑。
5. 增加定时任务，处理过期券和长期未登录积分。
6. 补齐管理员统计、异常页面和角色权限。
7. 建立单元测试、接口测试和端到端测试。
8. 编写 OpenAPI 接口契约。
9. 增加 CSRF、请求限流、生产配置和部署方案。

## 13. 总结

当前项目已经形成可演示的优惠券业务闭环，覆盖活动管理、AI 推荐、用户领券、风险检测、券码核销、积分和管理统计。代码结构按角色和职责划分，便于继续扩展。

项目当前最重要的技术风险不是页面功能，而是 SQLite 环境下的并发库存一致性、风控边界、通知权限过滤、预约状态转换和后台定时任务缺失。这些问题解决后，再补充自动化测试、API 契约和生产安全配置，系统即可从竞赛演示原型逐步演进为更稳定的完整应用。
