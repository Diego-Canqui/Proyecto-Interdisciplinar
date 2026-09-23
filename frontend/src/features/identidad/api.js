import { apiClient } from "../../lib/apiClient.js";

export const login = (credenciales) => apiClient.post("/auth/login", credenciales);
export const logout = (token) =>
  apiClient.post(`/auth/logout?token=${encodeURIComponent(token)}`);
export const obtenerPerfil = () => apiClient.get("/auth/perfil");

export const crearUsuario = (datos) => apiClient.post("/usuarios", datos);
export const listarUsuarios = () => apiClient.get("/usuarios");
