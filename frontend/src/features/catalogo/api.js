import { apiClient } from "../../lib/apiClient.js";

export const buscarRecursos = (filtro = "") =>
  apiClient.get(`/recursos?filtro=${encodeURIComponent(filtro)}`);
export const consultarDisponibilidad = (idRecurso) =>
  apiClient.get(`/recursos/${idRecurso}/disponibilidad`);
export const obtenerFichaTecnica = (idRecurso) =>
  apiClient.get(`/recursos/${idRecurso}/ficha-tecnica`);
