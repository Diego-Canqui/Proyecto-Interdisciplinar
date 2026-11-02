import { apiClient } from "../../lib/apiClient.js";

export const buscarRecursos = (filtro = "") =>
  apiClient.get(`/recursos?filtro=${encodeURIComponent(filtro)}`);

export const consultarDisponibilidad = (idRecurso) =>
  apiClient.get(`/recursos/${encodeURIComponent(idRecurso)}/disponibilidad`);

export const obtenerFichaTecnica = (idRecurso) =>
  apiClient.get(`/recursos/${encodeURIComponent(idRecurso)}/ficha-tecnica`);

export const crearRecurso = (datosRecurso) =>
  apiClient.post("/recursos", datosRecurso);

export const actualizarRecurso = (idRecurso, datosRecurso) =>
  apiClient.put(`/recursos/${encodeURIComponent(idRecurso)}`, datosRecurso);

export const actualizarEstadoRecurso = (idRecurso, nuevoEstado) =>
  apiClient.patch(`/recursos/${encodeURIComponent(idRecurso)}/estado`, { estado: nuevoEstado });
