const API_BASE =
  window.location.port === "3000"
    ? `${window.location.protocol}//${window.location.hostname}:8080`
    : "";

export async function api(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
}
