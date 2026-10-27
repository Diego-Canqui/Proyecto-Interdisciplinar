const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("token");
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    // D11: se expone el `detail` del backend tal cual (string o lista de validación del 422)
    let detalleBackend;
    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
      detalleBackend = errorData.detail ?? undefined;
    } catch {
      // Ignore JSON parse errors, use status-based message
    }
    // Si el `detail` es una lista (422 de pydantic) no se pinta `[object Object]` (RF-09)
    const error = new Error(typeof detail === "string" ? detail : "Error de validación");
    error.status = response.status;
    error.detail = detalleBackend; // string | lista de errores de validación | undefined
    throw error;
  }
  return response.json();
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body) =>
    request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};
