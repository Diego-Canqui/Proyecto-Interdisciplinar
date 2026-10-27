import { apiClient } from "../../lib/apiClient.js";

/**
 * Inicia sesión de un usuario.
 * @param {{ correo: string, password: string }} credenciales
 * @returns {Promise<{ token: string, usuario: object }>} TokenDTO con JWT y datos del usuario
 */
export async function login(credenciales) {
  const response = await apiClient.post("/auth/login", credenciales);
  return response;
}

/**
 * Registra un nuevo usuario.
 * @param {{ nombre: string, correo: string, telefono?: string, password: string, roles?: string[] }} datos
 * @returns {Promise<{ token: string, usuario: object }>} TokenDTO con JWT y datos del usuario
 */
export async function registro(datos) {
  const response = await apiClient.post("/auth/registro", datos);
  return response;
}

/**
 * Cierra la sesión del usuario (stateless, solo descarta token en cliente).
 * @returns {Promise<void>}
 */
export async function logout() {
  await apiClient.post("/auth/logout");
}

/**
 * Obtiene el perfil del usuario autenticado.
 * @returns {Promise<object>} UsuarioDTO con datos del usuario
 */
export async function obtenerPerfil() {
  const response = await apiClient.get("/auth/perfil");
  return response;
}

/**
 * Crea un nuevo usuario (admin/management).
 * @param {object} datos
 * @returns {Promise<object>}
 */
export async function crearUsuario(datos) {
  const response = await apiClient.post("/usuarios", datos);
  return response;
}

/**
 * Lista todos los usuarios (admin/management).
 * @returns {Promise<Array>}
 */
export async function listarUsuarios() {
  const response = await apiClient.get("/usuarios");
  return response;
}

/**
 * Obtiene el perfil de reputación del usuario autenticado.
 * @returns {Promise<object>} PerfilReputacionDTO con puntaje, nivel, sanciones y fechaActualizacion
 */
export async function obtenerPerfilReputacion() {
  const response = await apiClient.get("/reputacion/perfil");
  return response;
}

/**
 * Aplica una sanción a un usuario (requiere rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).
 * @param {string} usuario_id - UUID del usuario a sancionar
 * @param {string} tipo - Tipo de sanción: TARDANZA, DANO_PARCIAL, DANO_TOTAL, INASISTENCIA_RESERVA
 * @param {string} motivo - Motivo de la sanción
 * @param {number|null} monto_opcional - Solo DANO_TOTAL: valor del recurso (RF-06)
 * @param {number|null} dias_retardo - Solo TARDANZA: días de retraso >= 1 (RF-07)
 * @returns {Promise<object>} SancionDTO creada, con fecha_fin y vigente
 */
export async function aplicarSancion(
  usuario_id,
  tipo,
  motivo,
  monto_opcional = null,
  dias_retardo = null
) {
  const datos = { usuario_id, tipo, motivo };
  // Cada tipo solo admite sus parámetros propios: se omiten los que no aplican
  if (monto_opcional !== null) {
    datos.monto_opcional = monto_opcional;
  }
  if (dias_retardo !== null) {
    datos.dias_retardo = dias_retardo;
  }
  const response = await apiClient.post("/reputacion/sanciones", datos);
  return response;
}

/**
 * Registra una excepción académica para un usuario (requiere rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).
 * @param {string} usuario_id - UUID del usuario
 * @param {string} motivo - Motivo de la excepción
 * @param {string} fecha_inicio - Fecha inicio ISO 8601
 * @param {string} fecha_fin - Fecha fin ISO 8601
 * @returns {Promise<object>} ExcepcionAcademicaDTO creada
 */
export async function registrarExcepcion(usuario_id, motivo, fecha_inicio, fecha_fin) {
  const response = await apiClient.post("/reputacion/excepciones", {
    usuario_id,
    motivo,
    fecha_inicio,
    fecha_fin,
  });
  return response;
}

/**
 * Consulta la elegibilidad del usuario autenticado (RF-21).
 * @returns {Promise<{ elegible: boolean, razon: string|null }>} ElegibilidadDTO evaluada en el backend
 */
export async function obtenerElegibilidad() {
  const response = await apiClient.get("/reputacion/elegibilidad");
  return response;
}

/**
 * Ejecuta la amnistía mensual (requiere rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).
 * @returns {Promise<{ perfiles_premiados: number }>} ResultadoAmnistiaDTO con el conteo
 */
export async function ejecutarAmnistia() {
  const response = await apiClient.post("/reputacion/amnistia");
  return response;
}

/**
 * Anula una excepción académica (idempotente; requiere rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).
 * @param {string} excepcionId - UUID de la excepción a anular
 * @returns {Promise<object>} ExcepcionAcademicaDTO anulada
 */
export async function anularExcepcion(excepcionId) {
  const response = await apiClient.post(`/reputacion/excepciones/${excepcionId}/anular`);
  return response;
}

/**
 * Obtiene la ficha de reputación de un tercero (solo roles de gestión, RF-04).
 * @param {string} usuarioId - UUID del usuario consultado
 * @returns {Promise<object>} PerfilGestionDTO con puntaje, nivel, sanciones y excepciones
 */
export async function obtenerPerfilGestion(usuarioId) {
  const response = await apiClient.get(`/reputacion/usuarios/${usuarioId}/perfil`);
  return response;
}
