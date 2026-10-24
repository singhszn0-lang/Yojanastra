export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8004";

export async function apiRequest(endpoint, options = {}) {
  const token = sessionStorage.getItem("yojanastra_token");
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Start the FastAPI server and check VITE_API_URL.`
    );
  }

  if (response.status === 204) return null;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Backend request failed (${response.status})`
    );
  }

  return body;
}

export const getApplications = () => apiRequest("/applications");
export const getSchemes = () => apiRequest("/schemes");
export const getDashboardStats = () => apiRequest("/dashboard/stats");
export const getDuplicateFlags = () =>
  apiRequest("/duplicate-flags?review_status=");
export const getAuditLogs = () => apiRequest("/audit-logs");
export const getOfficerReviews = () => apiRequest("/officer-reviews");
