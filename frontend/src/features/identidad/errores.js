// Mensajes de error de la feature `identidad` (RF-09, D11).
// Sin JSX ni dependencias: es una hoja del grafo que usan el panel de gestión y `UsuariosPage`.

const MENSAJE_RED = "No se pudo conectar con el servidor. Inténtalo de nuevo.";
const MENSAJE_INESPERADO = "Error inesperado";

/**
 * Convierte el `detail` del backend en texto legible.
 * El 422 de validación llega como lista de errores, no como string (D11).
 * @param {unknown} detail - `detail` del backend tal cual lo expone `apiClient`
 * @returns {string} Texto listo para pintar; cadena vacía si no hay detalle usable
 */
export function textoDeDetalle(detail) {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((elemento) => (elemento && (elemento.msg || elemento.mensaje)) || "")
      .filter((texto) => texto !== "")
      .join(" · ");
  }
  return "";
}

/**
 * Devuelve el mensaje que debe ver el usuario para un error de la API (RF-09).
 * Orden: texto propio del código (`porCodigo`), detalle del backend, error de red y,
 * por último, el mensaje del propio error.
 * @param {{ message?: string, status?: number, detail?: unknown }} error
 * @param {Record<number, string>} porCodigo - Textos propios por código HTTP (p. ej. `{ 409: "..." }`)
 * @returns {string}
 */
export function mensajeDeError(error, porCodigo = {}) {
  if (porCodigo[error?.status]) {
    return porCodigo[error.status];
  }
  const detalle = textoDeDetalle(error?.detail);
  if (detalle) {
    return detalle;
  }
  if (error && error.status === undefined) {
    // Sin respuesta del backend (fetch rechazado): el `message` del navegador viene en inglés
    return MENSAJE_RED;
  }
  return error?.message || MENSAJE_INESPERADO;
}
