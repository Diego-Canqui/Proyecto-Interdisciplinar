import { apiClient } from "../../lib/apiClient.js";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Extrae el nombre de archivo de la cabecera Content-Disposition o devuelve el fallback.
 * @param {string|null} contentDisposition - Valor de la cabecera Content-Disposition
 * @param {string} fallback - Nombre por defecto si no viene en la cabecera
 * @returns {string} Nombre de archivo limpio
 */
function extraerNombreArchivo(contentDisposition, fallback) {
  if (!contentDisposition) {
    return fallback;
  }
  const matchUtf8 = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (matchUtf8?.[1]) {
    try {
      const decodificado = decodeURIComponent(matchUtf8[1].trim().replace(/^["']|["']$/g, ""));
      if (decodificado) {
        return decodificado;
      }
    } catch {
      // Si falla el decodificado, intentar con filename estándar
    }
  }
  const matchSimple = contentDisposition.match(/filename\s*=\s*"?([^";]+)"?/i);
  if (matchSimple?.[1]) {
    const limpio = matchSimple[1].trim();
    if (limpio) {
      return limpio;
    }
  }
  return fallback;
}

/**
 * Descarga un archivo CSV autenticado desde el backend usando Blob y enlace temporal.
 * @param {string} path - Ruta del endpoint
 * @param {string} nombreFallback - Nombre de archivo por defecto
 * @returns {Promise<string>} Nombre del archivo descargado
 */
async function descargarCsv(path, nombreFallback) {
  const token = localStorage.getItem("token");
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    let detalleBackend;
    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
      detalleBackend = errorData.detail ?? undefined;
    } catch {
      // Ignorar errores de parseo JSON y usar el mensaje basado en el estado HTTP
    }
    const error = new Error(typeof detail === "string" ? detail : "Error de validación");
    error.status = response.status;
    error.detail = detalleBackend;
    throw error;
  }

  const nombreArchivo = extraerNombreArchivo(
    response.headers.get("Content-Disposition"),
    nombreFallback
  );
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  try {
    enlace.click();
  } finally {
    enlace.remove();
    URL.revokeObjectURL(url);
  }
  return nombreArchivo;
}

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

/**
 * Obtiene la bitácora cronológica de movimientos de reputación de un usuario (solo roles de gestión).
 * @param {string} usuarioId - UUID del usuario consultado
 * @returns {Promise<Array<object>>} Lista de MovimientoReputacionDTO
 */
export async function obtenerMovimientosUsuario(usuarioId) {
  const response = await apiClient.get(
    `/reputacion/usuarios/${encodeURIComponent(usuarioId)}/movimientos`
  );
  return response;
}

/**
 * Descarga en CSV el historial de movimientos de reputación de un usuario (solo roles de gestión).
 * @param {string} usuarioId - UUID del usuario consultado
 * @returns {Promise<string>} Nombre del archivo CSV descargado
 */
export async function descargarCsvMovimientosUsuario(usuarioId) {
  const idCodificado = encodeURIComponent(usuarioId);
  return descargarCsv(
    `/reputacion/usuarios/${idCodificado}/movimientos/csv`,
    `historial-reputacion-${usuarioId}.csv`
  );
}

/**
 * Descarga en CSV el historial global de movimientos de reputación (solo roles de gestión).
 * @returns {Promise<string>} Nombre del archivo CSV descargado
 */
export async function descargarCsvMovimientosGlobal() {
  return descargarCsv("/reputacion/movimientos/csv", "historial-reputacion.csv");
}

/**
 * Cambia el rol de un usuario (solo ADMINISTRADOR_SISTEMA, RF-10).
 * @param {string} idUsuario - UUID del usuario
 * @param {string} rol - Nuevo rol asignado
 * @returns {Promise<object>} UsuarioDTO actualizado
 */
export async function cambiarRolUsuario(idUsuario, rol) {
  const response = await apiClient.patch(`/usuarios/${encodeURIComponent(idUsuario)}/rol`, { rol });
  return response;
}

/**
 * Cambia el estado de activación de un usuario (solo ADMINISTRADOR_SISTEMA, RF-11).
 * @param {string} idUsuario - UUID del usuario
 * @param {boolean} estado - true para activo, false para inactivo
 * @returns {Promise<object>} UsuarioDTO actualizado
 */
export async function cambiarEstadoUsuario(idUsuario, estado) {
  const response = await apiClient.patch(`/usuarios/${encodeURIComponent(idUsuario)}/estado`, { estado });
  return response;
}

/**
 * Elimina un usuario sin operaciones activas (solo ADMINISTRADOR_SISTEMA, RF-12).
 * @param {string} idUsuario - UUID del usuario
 * @returns {Promise<object>} Detalle de confirmación
 */
export async function eliminarUsuario(idUsuario) {
  const response = await apiClient.delete(`/usuarios/${encodeURIComponent(idUsuario)}`);
  return response;
}
