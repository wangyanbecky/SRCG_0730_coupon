# 架构设计

## 需求 1：operator 搜索与排序
1. 浏览器以 GET 请求访问 `/operator/dashboard?q=<关键字>&sort=<方向>`。
2. `operator.dashboard` 读取并规范化参数。
3. SQLAlchemy 查询按 `Campaign.name` 可选过滤并按白名单方向排序。
4. 路由向 Jinja 模板传递活动结果、搜索值和排序值。
5. 模板渲染搜索/排序表单、活动表格及无结果状态。

## 需求 2：预约发布与用户收藏
1. `Campaign.is_pending_release_at(now)` 统一推导未来预约活动状态。
2. operator 路由按推导状态计算“进行中”和“草稿 / 预约”，模板显示待发布。
3. `CampaignRepository.list_user_visible(now)` 返回当前可领活动与未来预约发布活动。
4. 用户 dashboard 将 `is_pending`、`is_reserved` 和开始时间传给卡片模板。
5. 用户提前点击领取时前端显示预约确认弹窗；服务端领券校验仍阻止提前领取。
6. `POST /user/reserve/<campaign_id>` 调用预约服务，写入 `CampaignReservation`。
7. 页面重新加载预约 ID 集合，已预约卡片右上角显示收藏星标。

继续使用 Flask 服务端渲染、原生 JavaScript 和 SQLAlchemy；不新增外部依赖。新增预约表由现有 `db.create_all()` 初始化。

## 需求 3：Admin 系统监控
1. `configure_observability(app)` 在应用工厂中初始化独立 JSONL 轮转 logger、启动时间和请求生命周期 hooks。
2. 请求完成后只记录白名单元数据：request_id、method、endpoint、status、duration、用户 ID/角色；异常信号记录脱敏摘要。
3. `read_system_logs()` 有界读取当前日志尾部，解析、脱敏并按 level/query 过滤。
4. `collect_system_health()` 独立执行应用、数据库、日志、AI 配置检查并汇总 overall 状态，单项失败隔离。
5. admin 蓝图提供 `/system/logs`、`/system/health`、`/system/alerts` 三个只读页面，统一复用 admin 权限门禁。
6. 报警页面只渲染二期规划，不连接后台任务或告警数据源。

不增加第三方依赖；日志和健康能力使用 Python 标准库、Flask hooks 与 SQLAlchemy `SELECT 1`。
