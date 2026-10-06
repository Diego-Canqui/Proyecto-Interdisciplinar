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
