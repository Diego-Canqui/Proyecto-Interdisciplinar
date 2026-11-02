import { apiClient } from "../../lib/apiClient.js";

export const registrarDevolucion = (idPrestamo) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/devolucion`);

export const consultarHistorial = (idUsuario) =>
  apiClient.get(`/prestamos/usuarios/${encodeURIComponent(idUsuario)}/historial`);

export const listarTodosPrestamos = () => apiClient.get("/prestamos");

export const renovarPrestamo = (idPrestamo) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/renovar`);

export const iniciarEntrega = (idPrestamo, datosEntrega) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/entrega/iniciar`, datosEntrega);

export const agregarItemChecklist = (idPrestamo, datosItem) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/entrega/checklist/items`, datosItem);

export const confirmarEntrega = (idPrestamo) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/entrega/confirmar`);

export const finalizarEntrega = (idPrestamo) =>
  apiClient.post(`/prestamos/${encodeURIComponent(idPrestamo)}/entrega/finalizar`);
