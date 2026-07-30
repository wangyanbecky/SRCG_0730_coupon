# 测试与修复计划

## 范围
验证 FR-001、FR-002、FR-003 及相关非功能需求；不修改或清理用户已有数据库和 Git 工作区变更。

## 测试计划
- [x] Python 路由语法检查
- [x] 现有集成测试回归
- [x] operator 登录与页面模板渲染
- [x] 标题升序与降序
- [x] 名称包含搜索与搜索/排序组合
- [x] 无结果状态
- [x] 非法排序值安全回退
- [x] 检查实现 diff 与需求追踪一致性

## 执行证据

### TV-001 Python 语法检查
- 命令：`python -m py_compile "api/app/routes/operator.py"`
- 结果：通过，退出码 0。

### TV-002 现有测试回归
- 命令：`python -m unittest discover -s test -p "test_*.py"`
- 结果：通过；`Ran 4 tests in 12.413s`，`OK`。
- 备注：运行中出现外部 HTTP 403 的 `ResourceWarning`，未导致用例失败，且与本页面改动无关。

### TV-003 operator 页面专项烟雾验证
- 环境：Flask test client + 内存 SQLite；使用种子 operator 登录，不触碰项目数据库。
- 结果：通过，输出 `operator dashboard smoke: OK`。
- 覆盖：`title_asc`、`title_desc`、名称包含搜索、搜索与降序组合、无结果、非法 sort 回退、模板成功渲染。
- 临时脚本在验证后已删除，未作为新增测试保留。

## 缺陷与修复
- 未发现产品代码缺陷。
- 两次长 `python -c` 验证命令分别因 PowerShell 引号和验证脚本范围问题失败；改用临时脚本并将断言限定到活动行后通过，不属于应用缺陷。

## 未覆盖项
- 未启动长期运行的开发服务器，因此未执行人工浏览器视觉检查；响应式 CSS 已按现有断点实现，模板与页面请求已通过服务端烟雾验证。

## 回归结论
FR-001、FR-002、FR-003 的自动化烟雾验收通过，现有 4 项集成测试无回归，可以完成本次 AIDLC 改进任务。

## 增量需求 2 测试记录（2026-07-30）

### 范围
验证 FR-004 至 FR-007、NFR-005 至 NFR-006，使用内存 SQLite 和 Flask test client，不触碰项目数据库。

### 执行项
- [x] 所有变更 Python 文件语法编译
- [x] 现有集成测试完整回归
- [x] operator 未来预约活动显示待发布
- [x] operator 进行中与草稿/预约统计
- [x] 用户页显示未来活动与领取开始时间
- [x] AI 遗漏活动时仍保证完整可见集合
- [x] 提前领取返回 campaign_not_started
- [x] 提前领取不改变库存、积分、Coupon 或风控流程
- [x] 首次预约、重复预约幂等和数据库唯一记录
- [x] 不同用户预约状态隔离
- [x] 隐藏草稿与结束早于发布时间的活动不可预约
- [x] 预约后刷新显示收藏星标
- [x] 到达开始时间后 operator 显示进行中、拒绝新预约
- [x] 已预约用户开始后保留星标并恢复领取能力

### TV-004 Python 语法检查
- 命令：`python -m py_compile` 覆盖新增/修改的 model、repository、service 和 route 文件。
- 结果：通过，退出码 0；行为审查修复后再次检查通过。

### TV-005 现有集成测试回归
- 命令：`python -m unittest discover -s test -p "test_*.py"`
- 首轮结果：4 项通过，`Ran 4 tests in 11.930s`，`OK`。
- 审查修复后结果：4 项通过，`Ran 4 tests in 13.424s`，`OK`。
- 备注：仍出现外部 HTTP 403 的 ResourceWarning，不导致失败，与本需求无关。

### TV-006 预约发布专项烟雾
- 环境：Flask test client + 内存 SQLite + 种子用户/活动。
- 结果：通过，输出 `scheduled reservation smoke: OK`。
- 覆盖：状态与统计、用户可见性、开始时间、AI 遗漏补全、提前领取、无副作用、预约幂等、用户隔离、非法活动拒绝、收藏持久化、开始后恢复领取。
- 临时脚本验证后已删除，未新增永久测试文件。

### 行为审查与缺陷修复
1. 已修复：预约记录原本会在发布时间后继续禁用领取；现仅 `is_pending && is_reserved` 显示禁用“已预约”，开始后保留星标并恢复领取。
2. 已修复：草稿或无效时间活动可通过构造 ID 预约；现待发布谓词要求 active 且有效发布时间不晚于结束时间。
3. 已修复：AI 返回子集时活动可能消失；现推荐结果只影响排序/说明，遗漏活动补入完整可见集合。

### 未覆盖与风险
- 未启动长期开发服务器进行人工浏览器视觉检查；Jinja 页面请求和脚本/样式输出已通过服务端烟雾。
- 项目现有 Cookie 写接口整体未启用应用级 CSRF token；本次预约端点沿用相同安全基线并受登录用户角色校验保护。建议后续作为全项目安全改进统一引入 CSRF，而不是只修补单一路由。

### 回归结论
FR-004 至 FR-007 的服务端和页面输出验收通过，预约不会提前创建 Coupon 或改变库存/积分，开始后领取链路可继续使用。本增量达到 AIDLC 测试门禁。

## 增量需求 3 测试记录（2026-07-30）

### 范围
验证 FR-008 至 FR-010、NFR-007 至 NFR-009。专项验证使用临时 SQLite、临时日志目录和 Flask test client，不触碰项目数据库；不伪造历史日志、健康状态或已启用的报警能力。

### 执行项
- [x] 可观测性、配置、应用工厂及 admin 路由语法编译
- [x] 现有集成测试完整回归
- [x] anonymous 跳转登录、普通用户 403、admin 三页面 200
- [x] 请求 ID 响应头和 JSONL 请求日志写入
- [x] password/token/Bearer/手机号脱敏，原始 query 不采集
- [x] 损坏 JSON 和非标量字段不会阻断读取或页面渲染
- [x] 日志读取条数受配置上限约束，页面选项跟随上限
- [x] 非法整数环境变量不阻止配置导入
- [x] 越界日志路径安全回退并显示 degraded
- [x] DB 检查失败隔离且不泄露底层异常文本
- [x] AI 状态兼容 dict 和属性对象，且不主动联网探测
- [x] 日志 handler 随应用回收关闭，Windows 临时目录可删除
- [x] 报警页明确“二期未启用”，无表单、按钮和虚假数据

### TV-007 Python 语法检查
- 命令：`python -m py_compile "api/config.py" "api/app/observability.py" "api/app/__init__.py" "api/app/routes/admin.py"`
- 结果：通过，退出码 0。

### TV-008 现有集成测试回归
- 命令：`python -m unittest discover -s test -p "test_*.py"`
- 结果：通过；`Ran 4 tests in 12.847s`，`OK`。
- 备注：仍出现外部 HTTP 403 的 `ResourceWarning`，未导致失败，与本需求无关。

### TV-009 admin monitoring 专项烟雾
- 环境：Flask test client + 临时 SQLite + 临时轮转日志目录；AI 仅替换本地状态对象，不发起网络请求。
- 结果：通过，输出 `admin monitoring smoke: OK`。
- 覆盖：权限、三页面、请求 ID、脱敏、过滤上限、损坏日志、DB 失败隔离、AI 状态兼容、非法配置、路径回退及 handler 释放。
- 首轮因测试中的备用路径未做规范化比较而断言失败；规范化测试路径后原实现通过，不属于产品缺陷。
- 临时脚本验证后已删除，未新增永久测试文件。

### TV-010 工作区静态检查
- 命令：`git diff --check`
- 结果：通过，无空白错误；仅提示部分工作区文件后续可能由 LF 转换为 CRLF。

### 安全审查与修复
1. 已从 `.env.example` 移除完整凭证形态值并改为占位符；若原值是真实凭证，必须在 AWS 侧立即撤销/轮换并检查 Git 历史，工作区代码修改不能替代轮换。
2. 日志只记录 request ID、method、endpoint、status、duration、user ID/role 等白名单元数据，不记录请求体、Cookie、Authorization、原始 query、IP 或 User-Agent。
3. 未处理异常只记录异常类型；DB、日志及 AI 状态检查不展示连接串、密钥或完整底层异常消息。
4. 日志路径限制在 `APP_LOG_ROOT`，配置非法时回退到应用 instance 日志目录并真实标记 degraded。

### 未覆盖与限制
- 未启动长期开发服务器，未进行人工浏览器视觉检查；三页面已通过服务端模板渲染和权限烟雾。
- 当前轮转 handler 适用于项目现有单进程 Flask 运行模型，不保证多个 worker 同时写同一文件的跨进程安全；生产多 worker 应改用集中日志或外部日志 handler。
- 健康页的 AI 项表示本地配置/降级状态，不代表实时远端可用性；一期按设计不主动进行 AI 网络探测。
- 异常报警仅为二期只读占位，未实现规则引擎、通知渠道、后台任务或告警闭环。

### 回归结论
FR-008 至 FR-010 的权限、真实日志、轻量健康状态和二期报警占位均通过自动化烟雾验收，现有 4 项集成测试无回归。本增量达到 AIDLC 测试门禁。

## 增量需求 4 测试记录（2026-07-30）

### 范围
验证 FR-011：默认领取风控阈值调整为 10 秒 5 次，并明确达到阈值即拦截。

### TV-011 配置与语法检查
- 命令：`python -m py_compile "api/config.py" "ai/config.py" "api/app/services/ai_gateway.py" "api/app/services/coupon_service.py"`
- 结果：通过，退出码 0；应用 Config、独立 AIConfig 及环境示例均为 10/5。

### TV-012 风控边界专项烟雾
- 环境：Flask test client、临时 SQLite、本地固定 allow 风险服务；不调用外部 AI。
- 结果：通过，输出 `risk threshold smoke: OK (4th allowed, 5th blocked)`。
- 覆盖：前 4 次请求不因频率阈值拦截；第 5 次返回 403 `risk_blocked`；风险日志决策依次为 4 个 allow 和 1 个 block。
- 临时脚本验证后已删除，未新增永久测试文件。

### TV-013 完整回归与 diff 检查
- 命令：`python -m unittest discover -s test -p "test_*.py"`
- 结果：通过；`Ran 4 tests in 13.732s`，`OK`。
- 备注：既有外部 HTTP 403 `ResourceWarning` 仍不导致失败，与本次阈值修改无关。
- `git diff --check` 通过，仅有 Windows LF/CRLF 转换提示。

### 结论
默认阈值已从 10 秒 50 次调整为 10 秒 5 次，当前请求计入窗口，第 5 次直接拦截。FR-011 达到 AIDLC 测试门禁。