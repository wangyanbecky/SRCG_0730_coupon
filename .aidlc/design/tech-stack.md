# 技术栈决策

- 后端：现有 Flask 与 Flask-SQLAlchemy。
- 模板：现有 Jinja2。
- 前端：现有 HTML/CSS，不增加 JavaScript 依赖。
- 数据库：沿用当前 SQLAlchemy 数据库配置。
- 验证：使用项目现有 `unittest` 测试发现命令，并执行 Python 语法编译检查。

选择理由：本需求可通过服务端查询和现有表单能力完成，新增框架或依赖会扩大旧项目风险。

## 需求 3 补充
- 日志：Python `logging`、`RotatingFileHandler`、JSON Lines。
- 健康检查：SQLAlchemy `text("SELECT 1")`、`os.access`、`time.perf_counter`、`importlib.metadata`。
- 不引入日志平台、APM、任务队列或报警依赖；这些属于二期集成范围。
