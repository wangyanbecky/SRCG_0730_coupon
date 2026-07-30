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
