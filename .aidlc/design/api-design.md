# 接口设计

## GET /operator/dashboard

查询参数：
- `q`：可选字符串；去除首尾空格后对 `Campaign.name` 做包含搜索。
- `sort`：可选枚举；`title_asc` 或 `title_desc`，缺失或非法值回退到 `title_asc`。

响应仍为现有 HTML 页面。URL 参数使搜索和排序状态可刷新、可复制，不改变现有路由和权限机制。

## POST /user/reserve/<campaign_id>

- 认证：仅已登录普通用户。
- 请求体：无。
- 成功：`200`，返回 `success=true`、提示消息、`reserved=true`；重复预约同样返回成功并标识幂等结果。
- 失败：活动不存在返回 404；活动非未来待发布状态返回 400 和稳定 `error_type`。
- 副作用：仅新增当前用户与活动的预约关系，不创建 Coupon、不扣库存、不加积分。

## POST /user/claim/<campaign_id> 时间门禁

未来待发布活动继续返回 `campaign_not_started`，前端据此也可触发预约提示；所有时间判断使用服务端时间。

## GET /admin/system/logs
- 认证：仅 admin。
- 查询参数：`level` 为 `DEBUG|INFO|WARNING|ERROR|CRITICAL` 白名单；`q` 为最多 100 字符普通关键字；`limit` 默认 50、最大 100。
- 响应：服务端 HTML；损坏日志行跳过，日志不可用时显示安全错误和空列表。

## GET /admin/system/health
- 认证：仅 admin。
- 行为：同步执行本地轻量检查，不进行外部 AI 网络调用。
- 响应：overall、检查项、checked_at、运行元数据的 HTML 页面。

## GET /admin/system/alerts
- 认证：仅 admin。
- 响应：二期规划占位 HTML，无数据写入、轮询或操作端点。
