# 项目 Bug 记录与修复方案

## Bug #1: `per_user_limit > 1` 的优惠券无法多次领取

**发现日期：** 2026-07-29

**严重程度：** 高

**影响范围：** 所有 `per_user_limit > 1` 的优惠券活动

**问题描述：**
`claim_coupon()` 中存在一个残留的有效性检查（约第137-146行）。该检查在 per-user-limit 校验通过后，额外判断 `Coupon.query.filter_by(campaign_id, user_id).first()` 是否存在。只要用户在该活动中已领取过任意一张券，就直接返回"您已领取过该优惠券"，完全无视 `per_user_limit` 的设定值。

例如：`夏日清凉节` 设置 `per_user_limit=2`，用户领取第1张成功，但领取第2张时被此检查拦截，无法达到限额。

**根因：**
早期版本只支持每用户限领1张。后来新增了 `per_user_limit` 字段和对应的限额检查（Step 4），但忘记删除旧的唯一性检查（Step 5）。两个检查形成了冗余：当 `per_user_limit=1` 时两者等价，当 `per_user_limit>1` 时旧检查错误拦截。

**修复方案：**
删除残留的 `if existing` 检查块，仅保留 `if user_claimed >= campaign.per_user_limit` 的限额检查。

**修改文件：** `app/user_bp.py` — `claim_coupon()` 方法

**修复前：**
```python
if user_claimed >= campaign.per_user_limit:
    return jsonify({'success': False, 'message': '您已达到该活动的领取上限。'}), 400

# 残留检查 — BUG 所在
existing = Coupon.query.filter_by(
    campaign_id=campaign_id, user_id=current_user.id
).first()
if existing:
    return jsonify({'success': False, 'message': '您已领取过该优惠券。'}), 400
```

**修复后：**
```python
if user_claimed >= campaign.per_user_limit:
    return jsonify({
        'success': False,
        'message': '您已达到该活动的领取上限。',
        'error_type': 'limit_exceeded',
    }), 400
```

---

## Bug #2: 优惠券网格布局每行只显示1张卡片

**发现日期：** 2026-07-29

**严重程度：** 中

**影响范围：** 用户"发现优惠"页面

**问题描述：**
CSS 中 `.user-coupon-grid` 设置了 `grid-template-columns: repeat(4, 1fr) !important`，但缺少 `display: grid` 声明。由于 grid 容器没有触发 grid 布局，`grid-template-columns` 被忽略，卡片按默认 block 布局排列，每行只显示1张，大量空白。

**根因：**
CSS 属性遗漏。`grid-template-columns` 只有在父元素为 `display: grid` 时才生效。

**修复方案：**
为 `.user-coupon-grid` 添加 `display: grid; gap: 15px`。

**修改文件：** `static/css/style.css`

**修复前：**
```css
.user-coupon-grid{grid-template-columns:repeat(4,1fr)!important}
```

**修复后：**
```css
.user-coupon-grid{display:grid;gap:15px;grid-template-columns:repeat(4,1fr)!important}
```

---

## Bug #3: "我的优惠券"页面每行只显示1张券

**发现日期：** 2026-07-29

**严重程度：** 中

**影响范围：** 用户"我的优惠券"页面

**问题描述：**
`.owned-grid` 设置了 `display: grid` 但未指定列数，默认单列布局。券卡（ticket-card）较宽，但也可以并排显示2列以利用空间。

**修复方案：**
为 `.owned-grid` 添加 `grid-template-columns: repeat(2, 1fr)`。小屏（≤800px）降级为单列。

**修改文件：** `static/css/style.css`

---

## Bug #4: `.env` 文件不生效

**发现日期：** 2026-07-29

**严重程度：** 高

**影响范围：** AI 功能无法启用

**问题描述：**
`requirements.txt` 中已包含 `python-dotenv==1.0.0`，但 `config.py` 中从未调用 `load_dotenv()`。用户按文档编辑了 `.env` 文件（含 `AWS_BEARER_TOKEN_BEDROCK`），但环境变量从未被加载，AI 服务始终处于 Mock 降级模式。

**根因：**
缺少 `load_dotenv()` 调用。

**修复方案：**
在 `config.py` 顶部添加：
```python
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))
```

**修改文件：** `config.py`

---

## Bug #5: 售罄和领满的优惠券不显示

**发现日期：** 2026-07-29

**严重程度：** 中

**影响范围：** 用户"发现优惠"页面

**问题描述：**
`dashboard()` 中有两个过滤条件导致部分有效券被隐藏：
1. `Campaign.stock > 0` — 售罄券被过滤
2. `user_claimed < per_user_limit` — 用户领满的券被过滤

用户无法看到已售罄或已领满的优惠券，不清楚哪些活动已结束或已达上限。

**修复方案：**
- 移除 `stock > 0` 和 `user_claimed < per_user_limit` 过滤
- 所有有效期内的券都显示，通过卡片灰化（`offer-exhausted`）+ 标签区分状态
- 用户可点击已领满/已售罄券，弹出 modal 提示原因

**修改文件：** `app/user_bp.py`、`templates/user/dashboard.html`、`static/css/style.css`

---

## Bug #6: 风控拦截和库存不足缺少错误类型标识

**发现日期：** 2026-07-29

**严重程度：** 低

**影响范围：** 前端错误提示体验

**问题描述：**
`claim_coupon()` 中以下错误响应缺少 `error_type` 字段：
- 风控拦截（403）：只有 `risk_blocked: True`，无 `error_type`
- 库存不足（400）：只有 message，无 `error_type`

前端 JS 无法区分错误类型，只能统一用 toast 提示，无法弹出针对性的 modal 弹窗。

**修复方案：**
- 风控拦截：添加 `error_type: 'risk_blocked'`
- 库存不足：添加 `error_type: 'out_of_stock'`

**修改文件：** `app/user_bp.py` — `claim_coupon()` 方法

---

## 修复汇总

| Bug # | 文件 | 问题 | 修复方式 |
|---|---|---|---|
| 1 | `app/user_bp.py` | `per_user_limit > 1` 无法多次领取 | 删除残留唯一性检查 |
| 2 | `static/css/style.css` | 4列网格不生效 | 添加 `display: grid` |
| 3 | `static/css/style.css` | 我的券页面单列 | 添加 `grid-template-columns` |
| 4 | `config.py` | `.env` 不被加载 | 添加 `load_dotenv()` |
| 5 | `user_bp.py` + 模板 + CSS | 售罄/领满券被隐藏 | 移除过滤，改为灰化+弹窗 |
| 6 | `app/user_bp.py` | 错误响应缺少类型标识 | 添加 `error_type` 字段 |
