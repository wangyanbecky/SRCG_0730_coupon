# 需求设计追踪

| 需求 | 设计落点 | 实现文件 | 验证 |
|---|---|---|---|
| FR-001 | API sort 白名单、name 排序、排序下拉框 | `api/app/routes/operator.py`, `ui/templates/operator/dashboard.html` | 升序/降序页面顺序 |
| FR-002 | q 参数、ilike、搜索栏、空状态 | 路由、模板、CSS | 部分匹配、清除、无结果 |
| FR-003 | 单一 GET 表单同时提交 q/sort | 路由、模板 | 组合条件互相保留 |
| NFR-001 | 不新增依赖/schema/API | 三个既有文件 | Git diff 与现有测试 |
| NFR-002 | ORM 过滤和排序枚举回退 | 路由 | 非法 sort 回退 |
| NFR-003 | 工具栏位置、标签、响应式样式 | 模板、CSS | 页面结构与移动端样式检查 |
| NFR-004 | 查询在路由，渲染在模板，视觉在 CSS | 三个既有文件 | 代码审查 |
| FR-004 | Campaign 待发布判定、operator 统计和显示状态 | Campaign 模型、operator 路由/模板 | 时间前待发布、时间后进行中、取消状态不覆盖 |
| FR-005 | 用户可见集合、待发布标签和开始时间 | Campaign repository、CouponService、user 路由/模板 | 未来预约活动可见且当前活动不回归 |
| FR-006 | 提前领取服务端门禁与预约确认弹窗 | CouponService、user 模板 JS | 无 Coupon/库存/积分变化，取消无写入 |
| FR-007 | CampaignReservation、预约端点、收藏星标 | 新模型/repository、service、user 路由/模板 | 唯一、幂等、用户隔离、跨刷新 |
| NFR-005 | 数据库唯一约束与 create_all 补表 | CampaignReservation 模型 | 重复预约记录数为 1 |
| NFR-006 | 统一服务端状态和身份校验 | Campaign 方法、service、受保护路由 | 边界时间和非用户访问验证 |
| FR-008 | JSONL 请求日志、脱敏有界读取、admin 筛选页 | observability、admin route、logs template | 真日志、过滤、空/损坏行、敏感信息 |
| FR-009 | DB/日志/AI配置/应用检查与 overall | observability、admin route、health template | 成功/失败隔离、耗时、无泄密 |
| FR-010 | 稳定 URL 和二期只读规划页 | admin route、alerts template、导航 | 无伪告警、无副作用控件 |
| NFR-007 | 白名单采集、二次脱敏、admin 门禁 | observability、admin before_request | 非 admin 拒绝、secret 不显示 |
| NFR-008 | 轮转、limit/scan 上限、失败隔离 | config、observability | 容量边界与损坏行验证 |
| NFR-009 | AI 配置状态标注和报警未启用文案 | health/alerts templates | 页面语义审查 |
| FR-011 | 10 秒滑动窗口、当前请求计数、达到 5 次即 block | `api/config.py`, `ai/config.py`, `api/app/services/ai_gateway.py` | 默认配置 10/5、第 4 次放行、第 5 次 `risk_blocked` |