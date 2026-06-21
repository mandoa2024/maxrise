# Mini-Drop

Mini-Drop 是一个可运行的 Linux 性能分析平台，包含 Web、Server、Agent、
Analyzer 和 PostgreSQL。

支持：

- `perf` CPU 火焰图与内存快照
- bpftrace/eBPF 内核探针
- `py-spy` Python 调用树
- Continuous Profiling 时间窗口回溯
- 基于可验证证据的 LLM 智能归因
- 任务状态、Agent 心跳与离线审计

## 运行要求

| 类别 | 要求 |
|---|---|
| 硬件 | x86_64，2 CPU，4GB 内存，建议 10GB 可用磁盘 |
| 系统 | Ubuntu 22.04+ 或同类 Linux 发行版 |
| 内核 | Linux 5.15+，启用 perf events、BPF 和 tracing filesystem |
| 软件 | Docker Engine 24+、Docker Compose v2 |
| 网络 | 可访问 Docker Hub 和 PyPI |
| 权限 | 当前用户可执行 Docker；Agent 使用 `pid: host` 和 `privileged` |

`perf`、bpftrace 和 py-spy 需要观察宿主机进程。若宿主策略阻止 perf，可执行：

```bash
sudo sysctl kernel.perf_event_paranoid=1
```

eBPF 还要求 `/sys/kernel/tracing` 或 `/sys/kernel/debug/tracing` 可用。具体 kprobe
能否挂载取决于内核符号和宿主机安全策略。上述高权限配置仅用于考题复现。

## 快速启动

```bash
git clone https://github.com/mandoa2024/mini-drop.git minidrop
cd minidrop
./scripts/ubuntu-preflight.sh
docker compose up -d --build
```

访问：

- Web：`http://localhost:3000`
- API 文档：`http://localhost:8080/docs`

## 自动演示

执行真实 perf 采集，并验证任务从创建到分析完成：

```bash
make demo
```

成功输出包含：

```text
status=DONE reason=analysis completed
top functions: ... parse_payload ...
```

## 手工采集

获取内置 workload 的宿主 PID：

```bash
# C workload：perf / eBPF
docker compose exec workload cat /runtime/workload.pid

# Python workload：py-spy
docker compose exec python-workload cat /runtime/python-workload.pid
```

在 Web 中选择 `demo-agent`，填写 PID、采集器、时长和采样率即可创建任务。

eBPF 支持：

- `kprobe:vfs_read`
- `kprobe:vfs_write`
- `kprobe:tcp_sendmsg`
- `profile:hz`

## 智能归因

未配置 LLM 时，系统生成确定性差分报告。启用 DeepSeek：

```bash
cp .env.example .env
```

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-key
```

```bash
docker compose up -d --build server web
```

LLM 只能调用白名单只读工具，报告引用的 `evidence_id` 由 Server 验证。详见
[智能归因评测报告](docs/智能归因评测报告.md)。

## 测试

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q --cov=agent --cov=analyzer --cov=server
```

当前结果：47 项测试通过，Python 代码覆盖率 53%。

## 常用命令

```bash
make up       # 构建并启动
make demo     # 运行真实 perf 演示
make logs     # 查看日志
make down     # 停止服务
```

## 权限与边界

- Agent 使用 `pid: host` 和 `privileged`，仅用于考题复现。
- 原始 profile 当前存储在 PostgreSQL；Web 使用轮询而非 SSE。
- 智能归因具备证据验证和安全降级，但尚不代表生产级根因定位准确率。

架构与取舍见 [设计文档](DESIGN.md)。
