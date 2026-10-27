import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { crearUsuario, listarUsuarios } from "../api.js";
import { mensajeDeError } from "../errores.js";

// Textos propios por código para la creación de usuarios (RF-09, RF-10)
const MENSAJES_ERROR = {
  403: "No tienes permisos de gestión para crear usuarios.",
  409: "Ya existe un usuario con ese correo.",
  422: "Datos inválidos: revisa la contraseña (mínimo 8 caracteres, una mayúscula, una minúscula y un dígito) y el teléfono.",
};

// Textos propios por código para la carga de usuarios
const MENSAJES_CARGA = {
  403: "No tienes permisos de gestión para consultar usuarios.",
};

/**
 * Página de administración y gestión de usuarios (RF-10).
 * La ruta se anida bajo el layout, de modo que la página no aporta contenedor principal propio.
 * @returns {JSX.Element} Formulario de alta y tabla de usuarios registrados
 */
export default function UsuariosPage() {
  const navigate = useNavigate();
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState(null);

  // Campos del formulario de alta de usuario
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [telefono, setTelefono] = useState("");
  const [password, setPassword] = useState("");

  // Estado de envío y mensajes de resultado del formulario
  const [enCurso, setEnCurso] = useState(false);
  const [errorCrear, setErrorCrear] = useState("");
  const [exitoCrear, setExitoCrear] = useState("");

  const cargar = useCallback(async () => {
    setCargando(true);
    setErrorCarga(null);
    try {
      const datos = await listarUsuarios();
      setUsuarios(Array.isArray(datos) ? datos : []);
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
      // Sin `roles`: el default [ESTUDIANTE] lo aplica el backend (RF-16)
      await crearUsuario({ nombre, correo, telefono, password });
      setExitoCrear("Usuario creado correctamente.");
      setNombre("");
      setCorreo("");
      setTelefono("");
      setPassword("");
      await cargar();
    } catch (err) {
      // 401: descartar token y redirigir al login (RF-09)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      setErrorCrear(mensajeDeError(err, MENSAJES_ERROR));
    } finally {
      setEnCurso(false);
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
                      </tr>
                    </thead>
                    <tbody>
                      {usuarios.map((u) => (
                        <tr key={u.id}>
                          <td data-etiqueta="Nombre">{u.nombre}</td>
                          <td data-etiqueta="Correo">{u.correo}</td>
                          <td data-etiqueta="Roles">{(u.roles || []).join(", ")}</td>
                          <td data-etiqueta="Estado">
                            <span
                              className={`insignia ${u.estado ? "insignia--exito" : "insignia--neutra"}`}
                            >
                              {u.estado ? "Activo" : "Inactivo"}
                            </span>
                          </td>
                        </tr>
                      ))}
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
