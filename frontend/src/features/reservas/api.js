import { apiClient } from "../../lib/apiClient.js";

export const solicitarReserva = (datosReserva) => apiClient.post("/reservas", datosReserva);

export const listarReservasUsuario = (idUsuario) =>
  apiClient.get(`/reservas/usuario/${encodeURIComponent(idUsuario)}`);
