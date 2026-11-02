import { apiClient } from "../../lib/apiClient.js";

export const registrarDevolucion = (idPrestamo) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/devolucion`);

export const consultarHistorial = (idUsuario) =>
  apiClient.get(`/prestamos/usuarios/${encodeURIComponent(idUsuario)}/historial`);

export const listarTodosPrestamos = () => apiClient.get("/prestamos");

