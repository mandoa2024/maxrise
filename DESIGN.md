# Mini-Drop 初步设计

## 架构

```text
Browser -> Web/nginx -> FastAPI Server -> PostgreSQL
                         |       ^
                         v       |
                      Analyzer  Agent -> perf
```

Server 是唯一的任务状态写入者。Agent 通过轮询领取任务，Analyzer 是无状态转换服务。首周版本把原始折叠栈和分析 JSON 暂存在 PostgreSQL，后续迁移到 MinIO 不改变组件接口。

## 状态机

```text
PENDING -> RUNNING -> UPLOADING -> DONE
    |          |           |
    +----------+-----------+-----> FAILED
```

`transition_task` 在数据库事务内锁定任务、校验迁移、更新任务并插入事件。初始 `PENDING` 也写一条事件。数据库对状态值和非空 reason 再做一层约束。

## 关键取舍

- 首周统一使用 Python，减少多语言构建成本；接口边界允许后续用 Go 重写 Agent 或 Server。
- 前端采用静态 JavaScript，避免 UI 工具链拖慢闭环；功能稳定后再迁移 React。
- Demo 默认产生确定性采样数据，保证非 Linux 开发机可复现；真实 Linux 验收必须关闭 Demo 模式。
- Agent 当前使用 HTTP 长轮询式拉取而非 gRPC，优先验证调度语义；多 Agent 扩展时可替换为 gRPC stream。

## 第 7 天验收目标

`docker compose up --build -d` 后 Agent 自动上线。运行 `python scripts/demo.py` 创建任务，任务最终为 `DONE`，Web 能显示状态迁移、火焰图和 TopN。
