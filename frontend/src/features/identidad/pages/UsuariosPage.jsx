import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  cambiarEstadoUsuario,
  cambiarRolUsuario,
  crearUsuario,
  eliminarUsuario,
  listarUsuarios,
  obtenerPerfil,
} from "../api.js";
import { mensajeDeError, textoDeDetalle } from "../errores.js";

// Textos propios por código para la creación de usuarios (RF-09, RF-10)
const MENSAJES_ERROR = {
  403: "No tienes permisos de gestión para crear usuarios o asignar este rol.",
  409: "Ya existe un usuario con ese correo.",
  422: "Datos inválidos: revisa la contraseña (mínimo 8 caracteres, una mayúscula, una minúscula y un dígito) y el teléfono.",
};

// Textos propios por código para la carga de usuarios
const MENSAJES_CARGA = {
  403: "No tienes permisos de gestión para consultar usuarios.",
};

// Opciones de roles según jerarquía (RF-09, RF-10)
const ROLES_SOLICITANTES = [
  "ESTUDIANTE",
  "DOCENTE",
  "PERSONAL_ADMINISTRATIVO",
];

const ROLES_GESTION = [
  "GESTOR_ALMACEN",
  "ADMINISTRADOR_SISTEMA",
];

const TODOS_LOS_ROLES = [...ROLES_SOLICITANTES, ...ROLES_GESTION];

/**
 * Lee el identificador y roles del usuario desde el JWT en localStorage (D5).
 * @returns {{ id: string, roles: string[] } | null}
 */
function leerUsuarioToken() {
  try {
    const token = localStorage.getItem("token");
    if (!token) return null;
    const payload = token.split(".")[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const relleno = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const datos = JSON.parse(atob(relleno));
    return {
      id: datos.sub || "",
      roles: Array.isArray(datos.roles) ? datos.roles : [],
    };
  } catch {
    return null;
  }
}

/**
 * Página de administración y gestión de usuarios (RF-09, RF-10, RF-11, RF-12).
 * La ruta se anida bajo el layout, de modo que la página no aporta contenedor principal propio.
 * @returns {JSX.Element} Formulario de alta y tabla de usuarios registrados
 */
export default function UsuariosPage() {
  const navigate = useNavigate();
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState(null);

  // Perfil del usuario en sesión (RF-09, RF-10, RF-11, RF-12)
  const [usuarioActual, setUsuarioActual] = useState(leerUsuarioToken);

  // Campos del formulario de alta de usuario
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [telefono, setTelefono] = useState("");
  const [password, setPassword] = useState("");
  const [rol, setRol] = useState("ESTUDIANTE");

  // Estado de envío y mensajes de resultado del formulario
  const [enCurso, setEnCurso] = useState(false);
  const [errorCrear, setErrorCrear] = useState("");
  const [exitoCrear, setExitoCrear] = useState("");

  // Estado de acciones de administración sobre la tabla (RF-10, RF-11, RF-12)
  const [accionEnCurso, setAccionEnCurso] = useState(null);
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState(null);
  const [exitoAccion, setExitoAccion] = useState("");
  const [errorAccion, setErrorAccion] = useState("");

  // Permisos según el rol del usuario en sesión
  const esAdmin = Boolean(usuarioActual?.roles?.includes("ADMINISTRADOR_SISTEMA"));
  const esGestor = Boolean(usuarioActual?.roles?.includes("GESTOR_ALMACEN"));
  const opcionesRolFormulario = esAdmin ? TODOS_LOS_ROLES : ROLES_SOLICITANTES;

  const cargar = useCallback(async () => {
    setCargando(true);
    setErrorCarga(null);
    try {
      const [datosUsuarios, perfil] = await Promise.all([
        listarUsuarios(),
        obtenerPerfil().catch(() => null),
      ]);
      setUsuarios(Array.isArray(datosUsuarios) ? datosUsuarios : []);
      if (perfil) {
        setUsuarioActual(perfil);
      }
    } catch (err) {
      // 401: la sesión ya no vale → descartar token y redirigir al login (RF-09, RF-10)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos, sin tabla ni formulario (RF-10)
      if (err.status === 403) {
        setErrorCarga({
          texto: mensajeDeError(err, MENSAJES_CARGA),
          permisos: true,
        });
        return;
      }
      // Red o 5xx: alerta con acción para reintentar la carga (RF-10)
      setErrorCarga({
        texto: mensajeDeError(err),
        reintentable: true,
      });
    } finally {
      setCargando(false);
    }
  }, [navigate]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (enCurso) {
      return;
    }
    setEnCurso(true);
    setErrorCrear("");
    setExitoCrear("");
    try {
      await crearUsuario({
        nombre,
        correo,
        telefono,
        password,
        roles: [rol],
      });
      setExitoCrear("Usuario creado correctamente.");
      setNombre("");
      setCorreo("");
      setTelefono("");
      setPassword("");
      setRol("ESTUDIANTE");
      await cargar();
    } catch (err) {
      // 401: descartar token y redirigir al login (RF-09)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      const detalle = textoDeDetalle(err?.detail);
      setErrorCrear(detalle || mensajeDeError(err, MENSAJES_ERROR));
    } finally {
      setEnCurso(false);
    }
  };

  const handleCambiarRol = async (idUsuario, nuevoRol) => {
    setAccionEnCurso(idUsuario);
    setExitoAccion("");
    setErrorAccion("");
    try {
      await cambiarRolUsuario(idUsuario, nuevoRol);
      setExitoAccion(`Rol actualizado correctamente a ${nuevoRol}.`);
      await cargar();
    } catch (err) {
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      setErrorAccion(mensajeDeError(err));
    } finally {
      setAccionEnCurso(null);
    }
  };

  const handleCambiarEstado = async (idUsuario, nuevoEstado) => {
    setAccionEnCurso(idUsuario);
    setExitoAccion("");
    setErrorAccion("");
    try {
      await cambiarEstadoUsuario(idUsuario, nuevoEstado);
      setExitoAccion(
        nuevoEstado
          ? "Cuenta activada correctamente."
          : "Cuenta desactivada correctamente."
      );
      await cargar();
    } catch (err) {
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      setErrorAccion(mensajeDeError(err));
    } finally {
      setAccionEnCurso(null);
    }
  };

  const handleEliminar = async (idUsuario) => {
    setAccionEnCurso(idUsuario);
    setExitoAccion("");
    setErrorAccion("");
    try {
      await eliminarUsuario(idUsuario);
      setExitoAccion("Usuario eliminado correctamente.");
      setConfirmandoEliminarId(null);
      await cargar();
    } catch (err) {
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      setErrorAccion(mensajeDeError(err));
    } finally {
      setAccionEnCurso(null);
    }
  };

  return (
    <div>
      <header className="pagina__cabecera">
        <h1 className="pagina__titulo">Usuarios</h1>
        <p className="pagina__subtitulo">
          Crea nuevos usuarios y consulta las cuentas registradas en el sistema.
        </p>
      </header>

      {errorCarga?.permisos ? (
        <div className="alerta alerta--error" role="alert">
          {errorCarga.texto}
        </div>
      ) : (
        <div className="formulario">
          <section className="tarjeta">
            <div className="tarjeta__cabecera">Crear usuario</div>
            <div className="tarjeta__cuerpo">
              <form className="formulario" onSubmit={handleSubmit}>
                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="usuario-nombre">
                    Nombre
                  </label>
                  <input
                    className="campo__control"
                    id="usuario-nombre"
                    type="text"
                    placeholder="Nombre completo"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    required
                  />
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="usuario-correo">
                    Correo
                  </label>
                  <input
                    className="campo__control"
                    id="usuario-correo"
                    type="email"
                    placeholder="correo@ejemplo.com"
                    value={correo}
                    onChange={(e) => setCorreo(e.target.value)}
                    required
                  />
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="usuario-telefono">
                    Teléfono
                  </label>
                  <input
                    className="campo__control"
                    id="usuario-telefono"
                    type="tel"
                    placeholder="Número de teléfono"
                    value={telefono}
                    onChange={(e) => setTelefono(e.target.value)}
                    required
                  />
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="usuario-password">
                    Contraseña
                  </label>
                  <input
                    className="campo__control"
                    id="usuario-password"
                    type="password"
                    placeholder="Contraseña segura"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="usuario-rol">
                    Rol inicial
                  </label>
                  <select
                    className="campo__control"
                    id="usuario-rol"
                    value={rol}
                    onChange={(e) => setRol(e.target.value)}
                  >
                    {opcionesRolFormulario.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>

                {exitoCrear && (
                  <div className="alerta alerta--exito" role="status">
                    {exitoCrear}
                  </div>
                )}

                {errorCrear && (
                  <div className="alerta alerta--error" role="alert">
                    {errorCrear}
                  </div>
                )}

                <div className="formulario__acciones">
                  <button
                    type="submit"
                    className="boton boton--primario"
                    disabled={enCurso}
                  >
                    {enCurso ? "Creando usuario..." : "Crear usuario"}
                  </button>
                </div>
              </form>
            </div>
          </section>

          <section className="tarjeta">
            <div className="tarjeta__cabecera">Usuarios registrados</div>
            <div className="tarjeta__cuerpo">
              {exitoAccion && (
                <div className="alerta alerta--exito" role="status">
                  {exitoAccion}
                </div>
              )}

              {errorAccion && (
                <div className="alerta alerta--error" role="alert">
                  {errorAccion}
                </div>
              )}

              {cargando ? (
                <p className="cargando" role="status">
                  Cargando usuarios...
                </p>
              ) : errorCarga ? (
                <div className="alerta alerta--error" role="alert">
                  <span>{errorCarga.texto}</span>{" "}
                  {errorCarga.reintentable && (
                    <button
                      type="button"
                      className="boton boton--secundario boton--sm"
                      onClick={cargar}
                    >
                      Reintentar
                    </button>
                  )}
                </div>
              ) : usuarios.length === 0 ? (
                <div className="estado-vacio">
                  <p className="estado-vacio__titulo">No hay usuarios registrados</p>
                  <p>Todavía no hay cuentas registradas en el sistema.</p>
                </div>
              ) : (
                <div className="tabla__contenedor">
                  <table className="tabla tabla--apilada">
                    <thead>
                      <tr>
                        <th scope="col">Nombre</th>
                        <th scope="col">Correo</th>
                        <th scope="col">Roles</th>
                        <th scope="col">Estado</th>
                        {esAdmin && <th scope="col">Acciones</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {usuarios.map((u) => {
                        const esPropiaCuenta = u.id === usuarioActual?.id;
                        const rolActualFila =
                          u.roles?.find((r) => TODOS_LOS_ROLES.includes(r)) ||
                          u.roles?.[0] ||
                          "ESTUDIANTE";

                        return (
                          <tr key={u.id}>
                            <td data-etiqueta="Nombre">{u.nombre}</td>
                            <td data-etiqueta="Correo">{u.correo}</td>
                            <td data-etiqueta="Roles">
                              {esAdmin && !esPropiaCuenta ? (
                                <select
                                  className="campo__control"
                                  value={rolActualFila}
                                  onChange={(e) => handleCambiarRol(u.id, e.target.value)}
                                  disabled={accionEnCurso === u.id}
                                  aria-label={`Cambiar rol de ${u.nombre}`}
                                >
                                  {TODOS_LOS_ROLES.map((r) => (
                                    <option key={r} value={r}>
                                      {r}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                (u.roles || []).join(", ")
                              )}
                            </td>
                            <td data-etiqueta="Estado">
                              <span
                                className={`insignia ${u.estado ? "insignia--exito" : "insignia--neutra"}`}
                              >
                                {u.estado ? "Activo" : "Inactivo"}
                              </span>
                            </td>
                            {esAdmin && (
                              <td data-etiqueta="Acciones">
                                {esPropiaCuenta ? (
                                  <>
                                    <span className="insignia insignia--info">
                                      Tu cuenta (protegida)
                                    </span>{" "}
                                    <button
                                      type="button"
                                      className="boton boton--secundario boton--sm"
                                      disabled
                                    >
                                      Desactivar
                                    </button>{" "}
                                    <button
                                      type="button"
                                      className="boton boton--peligro boton--sm"
                                      disabled
                                    >
                                      Eliminar
                                    </button>
                                  </>
                                ) : (
                                  <>
                                    <button
                                      type="button"
                                      className="boton boton--secundario boton--sm"
                                      onClick={() => handleCambiarEstado(u.id, !u.estado)}
                                      disabled={accionEnCurso === u.id}
                                    >
                                      {u.estado ? "Desactivar" : "Activar"}
                                    </button>{" "}
                                    {confirmandoEliminarId !== u.id ? (
                                      <button
                                        type="button"
                                        className="boton boton--peligro boton--sm"
                                        onClick={() => {
                                          setConfirmandoEliminarId(u.id);
                                          setErrorAccion("");
                                          setExitoAccion("");
                                        }}
                                        disabled={accionEnCurso === u.id}
                                      >
                                        Eliminar
                                      </button>
                                    ) : (
                                      <>
                                        <button
                                          type="button"
                                          className="boton boton--peligro boton--sm"
                                          onClick={() => handleEliminar(u.id)}
                                          disabled={accionEnCurso === u.id}
                                        >
                                          {accionEnCurso === u.id
                                            ? "Eliminando..."
                                            : "Confirmar eliminación"}
                                        </button>{" "}
                                        <button
                                          type="button"
                                          className="boton boton--secundario boton--sm"
                                          onClick={() => setConfirmandoEliminarId(null)}
                                          disabled={accionEnCurso === u.id}
                                        >
                                          Cancelar
                                        </button>
                                      </>
                                    )}
                                  </>
                                )}
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
