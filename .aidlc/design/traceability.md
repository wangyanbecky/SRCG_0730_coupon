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
