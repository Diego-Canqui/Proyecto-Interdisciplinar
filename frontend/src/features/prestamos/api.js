import { apiClient } from "../../lib/apiClient.js";

export const registrarDevolucion = (idPrestamo) =>
  apiClient.post(`/prestamos/${idPrestamo}/devolucion`);
export const consultarHistorial = (idUsuario) =>
  apiClient.get(`/prestamos/usuarios/${idUsuario}/historial`);
