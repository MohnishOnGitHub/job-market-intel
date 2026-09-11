const API_BASE = "";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function errorMessage(data, fallback) {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return fallback;
  return fallback;
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(errorMessage(data, "Request failed."));
    error.status = response.status;
    throw error;
  }
  return data;
}

async function apiUpload(path, formData) {
  const response = await fetch(`${API_BASE}${path}`, { method: "POST", body: formData });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(errorMessage(data, "Upload failed."));
    error.status = response.status;
    throw error;
  }
  return data;
}

function queryString(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      search.set(key, String(value).trim());
    }
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  return Number(value).toLocaleString();
}

function formatShare(value) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(Number(value) * 1000) / 10}%`;
}

function formatWhen(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString();
}

function setStatus(node, kind, message) {
  node.className = `status ${kind}`;
  node.hidden = false;
  node.textContent = message;
}

function clearStatus(node) {
  node.hidden = true;
  node.textContent = "";
}
