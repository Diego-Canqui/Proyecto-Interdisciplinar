import { apiClient } from "../../lib/apiClient.js";

export const solicitarReserva = (datosReserva) => apiClient.post("/reservas", datosReserva);

export const listarReservasUsuario = (idUsuario) =>
  apiClient.get(`/reservas/usuario/${encodeURIComponent(idUsuario)}`);

export const listarTodasReservas = () => apiClient.get("/reservas");

export const confirmarReserva = (idReserva) =>
  apiClient.patch(`/reservas/${encodeURIComponent(idReserva)}/confirmar`);

export const cancelarReserva = (idReserva) =>
  apiClient.patch(`/reservas/${encodeURIComponent(idReserva)}/cancelar`);

export const convertirReservaAPrestamo = (idReserva) =>
  apiClient.post(`/reservas/${encodeURIComponent(idReserva)}/prestamo`);
