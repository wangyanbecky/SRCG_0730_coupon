# 数据设计

## 既有活动数据
- `Campaign.name` 作为活动 title 和搜索所称优惠券名称。
- 搜索使用 SQLAlchemy `ilike`；排序使用 `Campaign.name.asc()/desc()`，并以 `Campaign.id.asc()` 稳定同名顺序。
- `Campaign.is_scheduled`、`scheduled_time` 和 `start_date` 用于推导待发布状态，不新增冗余展示状态字段。

## 新增 CampaignReservation
- 表名：`campaign_reservations`。
- 字段：`id` 主键、`user_id` 外键、`campaign_id` 外键、`created_at`。
- 约束：`UNIQUE(user_id, campaign_id)`，保证每个用户每个活动最多一条预约。
- 关系：User 与 Campaign 均可读取预约集合；删除用户或活动时级联清理预约。
- 初始化：模型加入统一导出，使应用启动时 `db.create_all()` 为旧数据库补建新表。

## 状态规则
- 待发布：活动 `status=active` 且 `is_scheduled=true`，有效发布时间晚于服务端当前时间且不晚于活动结束时间。
- 有效发布时间取 `scheduled_time` 与 `start_date` 中较晚者，避免二者不一致时提前开放。
- 预约记录不创建 Coupon，不改变 Campaign.stock，不改变 User.points。

## 需求 3 运行日志数据
- 存储：`api/data/logs/app.log` JSON Lines；轮转文件不进入版本控制。
- 字段：`timestamp`、`level`、`logger`、`event`、`request_id`、`method`、`endpoint`、`status`、`duration_ms`、`user_id`、`role`、`message`。
- 禁止字段：请求体、Cookie、Authorization、原始查询字符串、环境变量、数据库 URI、token/secret。
- 一期不新增数据库表；健康状态在请求时计算，不持久化伪历史。
