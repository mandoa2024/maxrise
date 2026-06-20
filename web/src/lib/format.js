export function formatTimestamp(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatKb(value) {
  if (value === null || value === undefined) return "N/A";
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} GB`;
  if (value >= 1024) return `${(value / 1024).toFixed(2)} MB`;
  return `${value} KB`;
}

export function toDateTimeInputValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}
