export const COLLECTORS = [
  { value: "perf", label: "perf / cpu-clock" },
  { value: "ebpf", label: "eBPF / bpftrace" },
  { value: "py-spy", label: "py-spy / Python" },
];

export const EBPF_PROBES = [
  {
    value: "vfs_read",
    label: "文件读取",
    technicalName: "kprobe:vfs_read",
    description: "观察目标进程进入内核文件读取路径的次数和调用栈。",
  },
  {
    value: "vfs_write",
    label: "文件写入",
    technicalName: "kprobe:vfs_write",
    description: "观察目标进程进入内核文件写入路径的次数和调用栈。",
  },
  {
    value: "tcp_sendmsg",
    label: "网络发送",
    technicalName: "kprobe:tcp_sendmsg",
    description: "观察目标进程通过 TCP 发送数据时的内核调用栈。",
  },
];
