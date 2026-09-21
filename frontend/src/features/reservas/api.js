import { apiClient } from "../../lib/apiClient.js";

export const solicitarReserva = (idUsuario, idRecurso) =>
  apiClient.post(`/reservas?id_usuario=${idUsuario}&id_recurso=${idRecurso}`);
