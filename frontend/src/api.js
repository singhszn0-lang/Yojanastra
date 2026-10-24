
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function apiRequest(endpoint, options = {}) {
  const token = sessionStorage.getItem("yojanastra_token");

  const headers = {
    ...(options.body instanceof FormData
      ? {}
      : { "Content-Type": "application/json" }),
    ...options.headers,
    ...(token
      ? { Authorization: `Bearer ${token}` }
      : {}),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      message || `API error: ${response.status}`
    );
  }

  if (response.status === 204) return null;

  return response.json();
}

export const getApplications = () =>
  apiRequest("/applications");

export const getSchemes = () =>
  apiRequest("/schemes");

export const getDashboardStats = () =>
  apiRequest("/dashboard/stats");

export const getDuplicateFlags = () =>
  apiRequest("/duplicate-flags?review_status=");

export const getAuditLogs = () =>
  apiRequest("/audit-logs");

export const getOfficerReviews = () =>
  apiRequest("/officer-reviews");
