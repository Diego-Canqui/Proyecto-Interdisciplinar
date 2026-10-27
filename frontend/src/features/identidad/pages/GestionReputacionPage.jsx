import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  anularExcepcion,
  aplicarSancion,
  ejecutarAmnistia,
  listarUsuarios,
  obtenerPerfilGestion,
  registrarExcepcion,
} from "../api.js";
import { mensajeDeError, textoDeDetalle } from "../errores.js";

// Aviso propio del 403; el resto de códigos muestran el detalle del backend (RF-09)
const MENSAJES_CARGA = {
  403: "No tienes permisos de gestión para consultar la reputación de otros usuarios.",
};

// Mapeo de la guía §9: el color acompaña al texto, nunca es la única señal
const CLASES_NIVEL = {
  BAJO: "insignia--error",
  NORMAL: "insignia--neutra",
  BUENO: "insignia--info",
  EXCELENTE: "insignia--exito",
};

// Estados de excepción derivados en el backend; aquí solo se elige la insignia
const CLASES_ESTADO_EXCEPCION = {
  VIGENTE: "insignia--exito",
  PROGRAMADA: "insignia--info",
  VENCIDA: "insignia--aviso",
  ANULADA: "insignia--neutra",
};

/**
 * Formatea una fecha del backend en la zona local del navegador.
 * @param {string|null|undefined} valor - Fecha ISO 8601
 * @returns {string} Fecha y hora legibles en español, o «—» si no hay valor
 */
function formatearFecha(valor) {
  if (!valor) {
    return "—";
  }
  return new Date(valor).toLocaleString();
}

/**
 * Normaliza un texto para el filtro local: sin mayúsculas ni acentos (RF-03).
 * @param {string} texto - Texto a normalizar
 * @returns {string} Texto en minúsculas y sin diacríticos
 */
function normalizar(texto) {
  return String(texto ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/**
 * Panel de gestión de reputación (RF-01, RF-02, RF-03).
 * La ruta se anida bajo el layout, así que la página no monta su propio contenedor
 * principal ni navbar.
 * @returns {JSX.Element} Listado de usuarios con filtro y selección del usuario a gestionar
 */
export default function GestionReputacionPage() {
  const navigate = useNavigate();
  const [usuarios, setUsuarios] = useState([]);
  const [cargandoUsuarios, setCargandoUsuarios] = useState(true);
  const [errorUsuarios, setErrorUsuarios] = useState(null);
  const [filtro, setFiltro] = useState("");
  const [seleccionado, setSeleccionado] = useState(null);
  const [ficha, setFicha] = useState(null);
  const [cargandoFicha, setCargandoFicha] = useState(false);
  const [errorFicha, setErrorFicha] = useState(null);
  // Último usuario pedido: descarta respuestas de selecciones anteriores (RF-04)
  const idPedidoFicha = useRef(null);

  // --- Estado del formulario de sanción (T7, RF-05, RF-09) ---
  // Tipo de sanción: los cuatro valores posibles del dominio
  const [tipoSancion, setTipoSancion] = useState("TARDANZA");
  const [motivoSancion, setMotivoSancion] = useState("");
  // diasRetardo solo se envía cuando tipo === TARDANZA
  const [diasRetardo, setDiasRetardo] = useState("");
  // montoSancion solo se envía cuando tipo === DANO_TOTAL
  const [montoSancion, setMontoSancion] = useState("");
  const [exitoSancion, setExitoSancion] = useState(null);
  const [errorSancion, setErrorSancion] = useState(null);

  // --- Estado del formulario de excepción (T7, RF-06, RF-09) ---
  const [motivoExcepcion, setMotivoExcepcion] = useState("");
  const [inicioExcepcion, setInicioExcepcion] = useState("");
  const [finExcepcion, setFinExcepcion] = useState("");
  // finInvalido: true cuando fin < inicio (validación local)
  const [finInvalido, setFinInvalido] = useState(false);
  const [exitoExcepcion, setExitoExcepcion] = useState(null);
  const [errorExcepcion, setErrorExcepcion] = useState(null);

  // --- Estado de anulación de excepción (T8, RF-07, RF-09) ---
  // anulacionPendiente: id de la excepción con confirmación abierta en la misma celda
  const [anulacionPendiente, setAnulacionPendiente] = useState(null);
  const [exitoAnulacion, setExitoAnulacion] = useState(null);
  const [errorAnulacion, setErrorAnulacion] = useState(null);

  // --- Estado de amnistía mensual (T8, RF-08, RF-09) ---
  // amnistiaPendiente: true cuando el primer clic pide confirmación en la misma sección
  const [amnistiaPendiente, setAmnistiaPendiente] = useState(false);
  const [resultadoAmnistia, setResultadoAmnistia] = useState(null);
  const [errorAmnistia, setErrorAmnistia] = useState(null);

  // enCurso: "sancion" | "excepcion" | "anular" | "amnistia" | null — impide dobles envíos (RF-09)
  const [enCurso, setEnCurso] = useState(null);

  const cargarUsuarios = useCallback(async () => {
    setCargandoUsuarios(true);
    setErrorUsuarios(null);
    try {
      const datos = await listarUsuarios();
      setUsuarios(Array.isArray(datos) ? datos : []);
    } catch (err) {
      // 401: la sesión ya no vale → descartar el token y volver al login (RF-09)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos, sin tabla ni selección (RF-01, RF-09)
      if (err.status === 403) {
        setErrorUsuarios({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      // Red o 5xx: alerta con acción para reintentar (RF-09)
      setErrorUsuarios({ texto: mensajeDeError(err), reintentable: true });
    } finally {
      setCargandoUsuarios(false);
    }
  }, [navigate]);

  useEffect(() => {
    cargarUsuarios();
  }, [cargarUsuarios]);

  /**
   * Consulta la ficha de reputación de un usuario (RF-04).
   * Es también el punto de recarga que usarán las acciones de T7 y T8.
   * @param {string} usuarioId - UUID del usuario consultado
   */
  const cargarFicha = useCallback(
    async (usuarioId) => {
      idPedidoFicha.current = usuarioId;
      setErrorFicha(null);
      // Al cambiar de usuario se oculta la ficha anterior; al recargar el mismo se conserva
      setFicha((actual) => (actual?.usuario_id === usuarioId ? actual : null));
      setCargandoFicha(true);
      try {
        const datos = await obtenerPerfilGestion(usuarioId);
        // Ignorar la respuesta si ya se seleccionó otro usuario
        if (idPedidoFicha.current !== usuarioId) {
          return;
        }
        setFicha(datos);
      } catch (err) {
        if (idPedidoFicha.current !== usuarioId) {
          return;
        }
        // 401: la sesión ya no vale → descartar el token y volver al login (RF-09)
        if (err.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }
        // 403: aviso de permisos (RF-01, RF-09)
        if (err.status === 403) {
          setErrorFicha({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
          return;
        }
        // 404: el usuario ya no existe → mensaje del backend y recarga de la lista
        if (err.status === 404) {
          setFicha(null);
          setErrorFicha({ texto: mensajeDeError(err), noEncontrado: true });
          return;
        }
        // Red o 5xx: alerta reintentable (RF-09)
        setFicha(null);
        setErrorFicha({ texto: mensajeDeError(err), reintentable: true });
      } finally {
        if (idPedidoFicha.current === usuarioId) {
          setCargandoFicha(false);
        }
      }
    },
    [navigate]
  );

  // Cargar la ficha al seleccionar un usuario y al cambiar de selección (RF-03, RF-04)
  useEffect(() => {
    if (!seleccionado) {
      idPedidoFicha.current = null;
      setFicha(null);
      setErrorFicha(null);
      setCargandoFicha(false);
      return;
    }
    cargarFicha(seleccionado.id);
  }, [seleccionado, cargarFicha]);

  // Filtro local: sin peticiones por tecla y sin distinguir mayúsculas ni acentos (RF-03)
  const textoFiltro = normalizar(filtro);
  const usuariosFiltrados = usuarios.filter(
    (usuario) =>
      normalizar(usuario.nombre).includes(textoFiltro) ||
      normalizar(usuario.correo).includes(textoFiltro)
  );

  const seleccionar = (usuario) => {
    setSeleccionado(usuario);
    // Cambiar de selección limpia mensajes y vuelve a cargar la ficha (RF-03, RF-04)
    setErrorFicha(null);
    setExitoSancion(null);
    setErrorSancion(null);
    setExitoExcepcion(null);
    setErrorExcepcion(null);
    setAnulacionPendiente(null);
    setExitoAnulacion(null);
    setErrorAnulacion(null);
  };

  const sanciones = ficha?.sanciones ?? [];
  const excepciones = ficha?.excepciones ?? [];
  // La deuda solo se muestra cuando alguna sanción la tiene (RF-04)
  const hayMonto = sanciones.some((sancion) => Number(sancion.monto_descuento) > 0);
  // Aviso informativo: una excepción con inicio futuro aún no cubre nada (RF-06)
  const excepcionesProgramadas = excepciones.filter(
    (excepcion) => excepcion.estado === "PROGRAMADA"
  );

  // Recarga la lista y descarta la selección cuando el usuario consultado ya no existe
  const recargarUsuariosYLimpiar = () => {
    setSeleccionado(null);
    cargarUsuarios();
  };

  /**
   * Manejador de errores compartido para los formularios de sanción y excepción (RF-09).
   * Devuelve el objeto de error que el formulario debe guardar en su estado.
   * @param {Error} err - Error lanzado por el apiClient
   * @param {"sancion"|"excepcion"} tipo - Formulario que originó el error
   * @returns {{ texto: string, permisos?: boolean, noEncontrado?: boolean, reintentable?: boolean }}
   */
  function procesarErrorFormulario(err, tipo) {
    // 401: sesión expirada → descartar token y redirigir al login (RF-09)
    if (err.status === 401) {
      localStorage.removeItem("token");
      navigate("/login");
      return null;
    }
    // 422: detalle de validación del backend (lista normalizada por textoDeDetalle)
    if (err.status === 422) {
      return { texto: textoDeDetalle(err.detail) || mensajeDeError(err) };
    }
    // 403: aviso de permisos
    if (err.status === 403) {
      return { texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true };
    }
    // 404: mensaje del backend + recarga del listado de usuarios
    if (err.status === 404) {
      return { texto: mensajeDeError(err), noEncontrado: true };
    }
    // Red o 5xx: reintentable
    return { texto: mensajeDeError(err), reintentable: true };
    void tipo; // suprimir aviso de parámetro no usado
  }

  /**
   * Envía el formulario de sanción al backend (RF-05, RF-09).
   * Los campos condicionales que no aplican al tipo seleccionado no viajan en la petición.
   * @param {React.FormEvent} e - Evento de envío del formulario
   */
  const enviarSancion = async (e) => {
    e.preventDefault();
    if (enCurso || !seleccionado) {
      return;
    }
    setEnCurso("sancion");
    setExitoSancion(null);
    setErrorSancion(null);
    try {
      // Solo se envía el campo que corresponde al tipo seleccionado (RF-05)
      const diasNum = tipoSancion === "TARDANZA" && diasRetardo !== "" ? Number(diasRetardo) : null;
      const montoNum =
        tipoSancion === "DANO_TOTAL" && montoSancion !== "" ? Number(montoSancion) : null;
      const resultado = await aplicarSancion(
        seleccionado.id,
        tipoSancion,
        motivoSancion,
        montoNum,
        diasNum
      );
      // Éxito: mostrar tipo, puntos descontados y fecha de fin devueltos por el backend
      setExitoSancion(
        `Sanción «${resultado.tipo}» aplicada: ${resultado.puntos_descuento} punto(s) descontado(s). ` +
          `Vigente hasta ${formatearFecha(resultado.fecha_fin)}.`
      );
      // Limpiar motivo e importes (el tipo se conserva para mayor comodidad)
      setMotivoSancion("");
      setDiasRetardo("");
      setMontoSancion("");
      // Recargar la ficha para reflejar el nuevo puntaje (RF-05)
      await cargarFicha(seleccionado.id);
    } catch (err) {
      const error = procesarErrorFormulario(err, "sancion");
      if (error !== null) {
        setErrorSancion(error);
        // 404: el usuario desapareció → recargar lista
        if (error.noEncontrado) {
          recargarUsuariosYLimpiar();
        }
      }
    } finally {
      setEnCurso(null);
    }
  };

  /**
   * Envía el formulario de excepción académica al backend (RF-06, RF-09).
   * Convierte las fechas locales a UTC antes de enviar y valida que fin >= inicio.
   * @param {React.FormEvent} e - Evento de envío del formulario
   */
  const enviarExcepcion = async (e) => {
    e.preventDefault();
    if (enCurso || !seleccionado) {
      return;
    }
    // Validación local: fin no puede ser anterior a inicio (fin == inicio sí se acepta)
    const inicioMs = new Date(inicioExcepcion).getTime();
    const finMs = new Date(finExcepcion).getTime();
    if (finMs < inicioMs) {
      setFinInvalido(true);
      return;
    }
    setFinInvalido(false);
    setEnCurso("excepcion");
    setExitoExcepcion(null);
    setErrorExcepcion(null);
    try {
      // Convertir a UTC antes de enviar (RF-06)
      const inicioUtc = new Date(inicioExcepcion).toISOString();
      const finUtc = new Date(finExcepcion).toISOString();
      const resultado = await registrarExcepcion(
        seleccionado.id,
        motivoExcepcion,
        inicioUtc,
        finUtc
      );
      // Éxito: informar el rango registrado
      let mensajeExito =
        `Excepción registrada: del ${formatearFecha(resultado.fecha_inicio)} ` +
        `al ${formatearFecha(resultado.fecha_fin)}.`;
      // Aviso adicional si la excepción empieza en el futuro (todavía no cubre nada)
      if (new Date(resultado.fecha_inicio) > new Date()) {
        mensajeExito +=
          ` Programada: cubrirá desde ${formatearFecha(resultado.fecha_inicio)}.`;
      }
      setExitoExcepcion(mensajeExito);
      // Limpiar el formulario
      setMotivoExcepcion("");
      setInicioExcepcion("");
      setFinExcepcion("");
      // Recargar la ficha para reflejar la nueva excepción (RF-06)
      await cargarFicha(seleccionado.id);
    } catch (err) {
      const error = procesarErrorFormulario(err, "excepcion");
      if (error !== null) {
        setErrorExcepcion(error);
        if (error.noEncontrado) {
          recargarUsuariosYLimpiar();
        }
      }
    } finally {
      setEnCurso(null);
    }
  };

  /**
   * Abre la confirmación inline para anular una excepción en la misma celda (RF-07).
   * @param {string} id - UUID de la excepción académica
   */
  const pedirAnulacion = (id) => {
    setAnulacionPendiente(id);
    setExitoAnulacion(null);
    setErrorAnulacion(null);
  };

  /**
   * Cancela la anulación inline sin llamar al backend (RF-07).
   */
  const cancelarAnulacion = () => {
    setAnulacionPendiente(null);
  };

  /**
   * Confirma y ejecuta la anulación de la excepción académica (RF-07, RF-09).
   * Deshabilita mientras enCurso === "anular". Recarga la ficha para mostrar estado ANULADA.
   * @param {string} excepcionId - UUID de la excepción a anular
   */
  const confirmarAnulacion = async (excepcionId) => {
    if (enCurso || !seleccionado) {
      return;
    }
    setEnCurso("anular");
    setExitoAnulacion(null);
    setErrorAnulacion(null);
    try {
      await anularExcepcion(excepcionId);
      setAnulacionPendiente(null);
      setExitoAnulacion("Excepción académica anulada correctamente.");
      // Recargar la ficha para mostrar la excepción en estado ANULADA devuelta por el backend (RF-07)
      await cargarFicha(seleccionado.id);
    } catch (err) {
      setAnulacionPendiente(null);
      // 401: sesión expirada → descartar token y navegar al login (RF-09)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos
      if (err.status === 403) {
        setErrorAnulacion({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      // 404: no encontrada → mensaje + recarga de la ficha (RF-07, RF-09)
      if (err.status === 404) {
        setErrorAnulacion({ texto: mensajeDeError(err), noEncontrado: true });
        if (seleccionado) {
          await cargarFicha(seleccionado.id);
        }
        return;
      }
      // Red o 5xx: error reintentable
      setErrorAnulacion({ texto: mensajeDeError(err), reintentable: true });
    } finally {
      setEnCurso(null);
    }
  };

  /**
   * Abre la confirmación en dos pasos para la amnistía global (RF-08).
   */
  const pedirAmnistia = () => {
    setAmnistiaPendiente(true);
    setResultadoAmnistia(null);
    setErrorAmnistia(null);
  };

  /**
   * Cancela la ejecución de la amnistía sin llamar al backend (RF-08).
   */
  const cancelarAmnistia = () => {
    setAmnistiaPendiente(false);
  };

  /**
   * Confirma y ejecuta la amnistía mensual global (RF-08, RF-09).
   * Deshabilita mientras enCurso === "amnistia". Trata N = 0 como resultado informativo válido.
   */
  const confirmarAmnistia = async () => {
    if (enCurso) {
      return;
    }
    setEnCurso("amnistia");
    setResultadoAmnistia(null);
    setErrorAmnistia(null);
    try {
      const res = await ejecutarAmnistia();
      setAmnistiaPendiente(false);
      const n = Number(res?.perfiles_premiados ?? 0);
      if (n > 0) {
        setResultadoAmnistia({
          tipo: "exito",
          texto: n === 1 ? "1 perfil premiado" : `${n} perfiles premiados`,
        });
      } else {
        // N = 0 es un resultado informativo válido, no un error (RF-08)
        setResultadoAmnistia({
          tipo: "info",
          texto: "Ningún perfil resultó elegible",
        });
      }
      // Si hay un usuario seleccionado, recargar su ficha para reflejar posibles cambios (RF-08)
      if (seleccionado) {
        await cargarFicha(seleccionado.id);
      }
    } catch (err) {
      setAmnistiaPendiente(false);
      // 401: sesión expirada → login
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos
      if (err.status === 403) {
        setErrorAmnistia({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      // Red o 5xx: error reintentable
      setErrorAmnistia({ texto: mensajeDeError(err), reintentable: true });
    } finally {
      setEnCurso(null);
    }
  };

  return (
    <div>
      <header className="pagina__cabecera">
        <h1 className="pagina__titulo">Gestión de reputación</h1>
        <p className="pagina__subtitulo">
          Elige un usuario para consultar su reputación y gestionar sus sanciones y excepciones.
        </p>
      </header>

      {errorUsuarios?.permisos ? (
        <div className="alerta alerta--error" role="alert">
          {errorUsuarios.texto}
        </div>
      ) : (
        <div className="formulario">
          <section className="tarjeta">
            <div className="tarjeta__cabecera">Usuarios</div>
            <div className="tarjeta__cuerpo">
              {cargandoUsuarios ? (
                <p className="cargando" role="status">
                  Cargando usuarios...
                </p>
              ) : errorUsuarios ? (
                <div className="alerta alerta--error" role="alert">
                  <span>{errorUsuarios.texto}</span>
                  {errorUsuarios.reintentable && (
                    <button
                      type="button"
                      className="boton boton--secundario boton--sm"
                      onClick={cargarUsuarios}
                    >
                      Reintentar
                    </button>
                  )}
                </div>
              ) : usuarios.length === 0 ? (
                <div className="estado-vacio">
                  <p className="estado-vacio__titulo">No hay usuarios registrados</p>
                  <p>Todavía no hay cuentas que gestionar.</p>
                </div>
              ) : (
                <div className="formulario">
                  <div className="campo">
                    <label className="campo__etiqueta" htmlFor="filtro-usuarios">
                      Filtrar por nombre o correo
                    </label>
                    <input
                      className="campo__control"
                      id="filtro-usuarios"
                      type="search"
                      value={filtro}
                      onChange={(e) => setFiltro(e.target.value)}
                      placeholder="Escribe un nombre o un correo"
                    />
                  </div>

                  {usuariosFiltrados.length === 0 ? (
                    <div className="estado-vacio">
                      <p className="estado-vacio__titulo">Ningún usuario coincide</p>
                      <p>Prueba con otro nombre o correo.</p>
                    </div>
                  ) : (
                    <div className="tabla__contenedor">
                      <table className="tabla tabla--apilada">
                        <thead>
                          <tr>
                            <th scope="col">Nombre</th>
                            <th scope="col">Correo</th>
                            <th scope="col">Roles</th>
                            <th scope="col">Acción</th>
                          </tr>
                        </thead>
                        <tbody>
                          {usuariosFiltrados.map((usuario) => {
                            const esSeleccionado = seleccionado?.id === usuario.id;
                            return (
                              <tr key={usuario.id}>
                                <td data-etiqueta="Nombre">{usuario.nombre}</td>
                                <td data-etiqueta="Correo">{usuario.correo}</td>
                                <td data-etiqueta="Roles">
                                  {(usuario.roles || []).join(", ")}
                                </td>
                                <td data-etiqueta="Acción">
                                  <button
                                    type="button"
                                    className="boton boton--secundario boton--sm"
                                    onClick={() => seleccionar(usuario)}
                                    aria-pressed={esSeleccionado}
                                  >
                                    Seleccionar
                                  </button>{" "}
                                  {esSeleccionado && (
                                    <span className="insignia insignia--info">
                                      Seleccionado
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          <section className="tarjeta">
            <div className="tarjeta__cabecera">Ficha del usuario</div>
            <div className="tarjeta__cuerpo">
              {/* Sin usuario seleccionado */}
              {!seleccionado && (
                <div className="estado-vacio">
                  <p className="estado-vacio__titulo">Sin usuario seleccionado</p>
                  <p>Selecciona un usuario en la lista para ver su ficha.</p>
                </div>
              )}

              {/* Usuario seleccionado: estados de carga, error y contenido */}
              {seleccionado && (
                <>
                  <p>
                    Usuario seleccionado: <strong>{seleccionado.nombre}</strong> (
                    {seleccionado.correo}).
                  </p>

                  {/* Cargando la ficha */}
                  {cargandoFicha && (
                    <p className="cargando" role="status">
                      Cargando ficha de reputación...
                    </p>
                  )}

                  {/* Error 403: aviso de permisos (RF-09) */}
                  {!cargandoFicha && errorFicha?.permisos && (
                    <div className="alerta alerta--error" role="alert">
                      {errorFicha.texto}
                    </div>
                  )}

                  {/* Error 404: usuario no encontrado → mensaje + botón para recargar (RF-09) */}
                  {!cargandoFicha && errorFicha?.noEncontrado && (
                    <div className="alerta alerta--error" role="alert">
                      <span>{errorFicha.texto}</span>{" "}
                      <button
                        type="button"
                        className="boton boton--secundario boton--sm"
                        onClick={recargarUsuariosYLimpiar}
                      >
                        Recargar usuarios
                      </button>
                    </div>
                  )}

                  {/* Error de red / 5xx: alerta reintentable (RF-09) */}
                  {!cargandoFicha && errorFicha?.reintentable && (
                    <div className="alerta alerta--error" role="alert">
                      <span>{errorFicha.texto}</span>{" "}
                      <button
                        type="button"
                        className="boton boton--secundario boton--sm"
                        onClick={() => cargarFicha(seleccionado.id)}
                      >
                        Reintentar
                      </button>
                    </div>
                  )}

                  {/* Ficha de reputación: puntaje, nivel y fecha de actualización (RF-04, §9) */}
                  {!cargandoFicha && !errorFicha && ficha && (
                    <>
                      <div className="tarjeta__contenido">
                        <p>
                          <strong>Puntaje:</strong> {ficha.puntaje} / 1000
                        </p>
                        <p>
                          <strong>Nivel:</strong>{" "}
                          <span
                            className={`insignia ${CLASES_NIVEL[ficha.nivel] ?? "insignia--neutra"}`}
                          >
                            {ficha.nivel}
                          </span>
                        </p>
                        <p>
                          <strong>Última actualización:</strong>{" "}
                          {ficha.fecha_actualizacion
                            ? formatearFecha(ficha.fecha_actualizacion)
                            : "Sin perfil todavía"}
                        </p>
                      </div>

                      {/* Tabla de sanciones (RF-04): tipo, motivo, puntos, monto si >0, fechas y estado */}
                      <h3 className="tarjeta__titulo">Sanciones</h3>
                      {sanciones.length === 0 ? (
                        <p className="estado-vacio">Sin sanciones registradas.</p>
                      ) : (
                        <div className="tabla__contenedor">
                          <table className="tabla tabla--apilada">
                            <thead>
                              <tr>
                                <th scope="col">Tipo</th>
                                <th scope="col">Motivo</th>
                                <th scope="col">Puntos</th>
                                {hayMonto && <th scope="col">Monto (€)</th>}
                                <th scope="col">Fecha aplicación</th>
                                <th scope="col">Fecha fin</th>
                                <th scope="col">Estado</th>
                              </tr>
                            </thead>
                            <tbody>
                              {sanciones.map((sancion) => (
                                <tr key={sancion.id}>
                                  <td data-etiqueta="Tipo">{sancion.tipo}</td>
                                  <td data-etiqueta="Motivo">{sancion.motivo}</td>
                                  <td data-etiqueta="Puntos">{sancion.puntos_descuento}</td>
                                  {hayMonto && (
                                    <td data-etiqueta="Monto (€)">
                                      {Number(sancion.monto_descuento) > 0
                                        ? sancion.monto_descuento
                                        : "—"}
                                    </td>
                                  )}
                                  <td data-etiqueta="Fecha aplicación">
                                    {formatearFecha(sancion.fecha_aplicacion)}
                                  </td>
                                  <td data-etiqueta="Fecha fin">
                                    {formatearFecha(sancion.fecha_fin)}
                                  </td>
                                  <td data-etiqueta="Estado">
                                    {sancion.vigente ? (
                                      <span className="insignia insignia--error">Vigente</span>
                                    ) : (
                                      <span className="insignia insignia--neutra">Expirada</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Tabla de excepciones (RF-04): motivo, inicio, fin, estado (texto + insignia), acciones (RF-07) */}
                      <h3 className="tarjeta__titulo">Excepciones académicas</h3>
                      {/* Aviso informativo: las excepciones programadas aún no cubren nada (RF-06) */}
                      {excepcionesProgramadas.length > 0 && (
                        <div className="alerta alerta--aviso" role="status">
                          {excepcionesProgramadas.length === 1
                            ? "Hay 1 excepción programada que todavía no está en vigor."
                            : `Hay ${excepcionesProgramadas.length} excepciones programadas que todavía no están en vigor.`}
                        </div>
                      )}
                      {/* Mensaje de éxito tras anular una excepción (RF-07, RF-09) */}
                      {exitoAnulacion && (
                        <div className="alerta alerta--exito" role="status">
                          {exitoAnulacion}
                        </div>
                      )}
                      {/* Mensaje de error al anular (RF-07, RF-09) */}
                      {errorAnulacion && (
                        <div className="alerta alerta--error" role="alert">
                          <span>{errorAnulacion.texto}</span>
                        </div>
                      )}
                      {excepciones.length === 0 ? (
                        <p className="estado-vacio">Sin excepciones registradas.</p>
                      ) : (
                        <div className="tabla__contenedor">
                          <table className="tabla tabla--apilada">
                            <thead>
                              <tr>
                                <th scope="col">Motivo</th>
                                <th scope="col">Inicio</th>
                                <th scope="col">Fin</th>
                                <th scope="col">Estado</th>
                                <th scope="col">Acciones</th>
                              </tr>
                            </thead>
                            <tbody>
                              {excepciones.map((excepcion) => (
                                <tr key={excepcion.id}>
                                  <td data-etiqueta="Motivo">{excepcion.motivo}</td>
                                  <td data-etiqueta="Inicio">
                                    {formatearFecha(excepcion.fecha_inicio)}
                                  </td>
                                  <td data-etiqueta="Fin">
                                    {formatearFecha(excepcion.fecha_fin)}
                                  </td>
                                  <td data-etiqueta="Estado">
                                    <span
                                      className={`insignia ${CLASES_ESTADO_EXCEPCION[excepcion.estado] ?? "insignia--neutra"}`}
                                    >
                                      {excepcion.estado}
                                    </span>
                                  </td>
                                  <td data-etiqueta="Acciones">
                                    {/* Solo mostrar botón en VIGENTE o PROGRAMADA. En VENCIDA y ANULADA no existe botón (RF-07) */}
                                    {excepcion.estado === "VIGENTE" ||
                                    excepcion.estado === "PROGRAMADA" ? (
                                      anulacionPendiente === excepcion.id ? (
                                        <>
                                          <button
                                            type="button"
                                            className="boton boton--peligro boton--sm"
                                            onClick={() => confirmarAnulacion(excepcion.id)}
                                            disabled={enCurso === "anular"}
                                          >
                                            {enCurso === "anular"
                                              ? "Anulando..."
                                              : "Confirmar anulación"}
                                          </button>{" "}
                                          <button
                                            type="button"
                                            className="boton boton--secundario boton--sm"
                                            onClick={cancelarAnulacion}
                                            disabled={enCurso === "anular"}
                                          >
                                            Cancelar
                                          </button>
                                        </>
                                      ) : (
                                        <button
                                          type="button"
                                          className="boton boton--peligro boton--sm"
                                          onClick={() => pedirAnulacion(excepcion.id)}
                                          disabled={enCurso === "anular"}
                                        >
                                          Anular
                                        </button>
                                      )
                                    ) : (
                                      "—"
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </div>
          </section>

          {/* Formularios de sanción y excepción: solo cuando hay usuario seleccionado (T7, RF-05, RF-06) */}
          {seleccionado && (
            <>
              {/* Formulario de sanción (RF-05, RF-09) */}
              <section className="tarjeta">
                <div className="tarjeta__cabecera">Aplicar sanción</div>
                <div className="tarjeta__cuerpo">
                  <form className="formulario" onSubmit={enviarSancion} noValidate>
                    {/* Tipo de sanción: los cuatro valores del dominio */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="sancion-tipo">
                        Tipo de sanción
                      </label>
                      <select
                        className="campo__control"
                        id="sancion-tipo"
                        value={tipoSancion}
                        onChange={(e) => {
                          setTipoSancion(e.target.value);
                          // Al cambiar el tipo se descarta el valor del campo que deja de aplicar
                          setDiasRetardo("");
                          setMontoSancion("");
                          setExitoSancion(null);
                          setErrorSancion(null);
                        }}
                        required
                      >
                        <option value="TARDANZA">TARDANZA</option>
                        <option value="PERDIDA">PERDIDA</option>
                        <option value="DANO_PARCIAL">DANO_PARCIAL</option>
                        <option value="DANO_TOTAL">DANO_TOTAL</option>
                      </select>
                    </div>

                    {/* Motivo: siempre obligatorio, máx. 500 caracteres */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="sancion-motivo">
                        Motivo
                      </label>
                      <textarea
                        className="campo__control"
                        id="sancion-motivo"
                        value={motivoSancion}
                        onChange={(e) => setMotivoSancion(e.target.value)}
                        maxLength={500}
                        required
                        rows={3}
                      />
                    </div>

                    {/* Campo condicional: días de retardo (solo TARDANZA) */}
                    {tipoSancion === "TARDANZA" && (
                      <div className="campo">
                        <label className="campo__label" htmlFor="sancion-dias">
                          Días de retardo
                        </label>
                        <input
                          className="campo__control"
                          id="sancion-dias"
                          type="number"
                          min="1"
                          step="1"
                          value={diasRetardo}
                          onChange={(e) => setDiasRetardo(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    {/* Campo condicional: monto (solo DANO_TOTAL) */}
                    {tipoSancion === "DANO_TOTAL" && (
                      <div className="campo">
                        <label className="campo__label" htmlFor="sancion-monto">
                          Monto del daño (€)
                        </label>
                        <input
                          className="campo__control"
                          id="sancion-monto"
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={montoSancion}
                          onChange={(e) => setMontoSancion(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    {/* Mensaje de éxito: tipo, puntos y fecha de fin del backend (RF-05) */}
                    {exitoSancion && (
                      <div className="alerta alerta--exito" role="status">
                        {exitoSancion}
                      </div>
                    )}

                    {/* Mensajes de error según código HTTP (RF-09) */}
                    {errorSancion && (
                      <div className="alerta alerta--error" role="alert">
                        <span>{errorSancion.texto}</span>{" "}
                        {errorSancion.reintentable && (
                          <button
                            type="submit"
                            className="boton boton--secundario boton--sm"
                          >
                            Reintentar
                          </button>
                        )}
                      </div>
                    )}

                    <div className="formulario__acciones">
                      {/* Botón primario; disabled mientras la petición está en vuelo (RF-09) */}
                      <button
                        type="submit"
                        className="boton boton--primario"
                        disabled={enCurso === "sancion"}
                      >
                        {enCurso === "sancion" ? "Aplicando..." : "Aplicar sanción"}
                      </button>
                    </div>
                  </form>
                </div>
              </section>

              {/* Formulario de excepción académica (RF-06, RF-09) */}
              <section className="tarjeta">
                <div className="tarjeta__cabecera">Registrar excepción académica</div>
                <div className="tarjeta__cuerpo">
                  <form className="formulario" onSubmit={enviarExcepcion} noValidate>
                    {/* Motivo de la excepción: máx. 500 caracteres */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="excepcion-motivo">
                        Motivo
                      </label>
                      <textarea
                        className="campo__control"
                        id="excepcion-motivo"
                        value={motivoExcepcion}
                        onChange={(e) => setMotivoExcepcion(e.target.value)}
                        maxLength={500}
                        required
                        rows={3}
                      />
                    </div>

                    {/* Fecha de inicio: datetime-local obligatorio */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="excepcion-inicio">
                        Fecha y hora de inicio
                      </label>
                      <input
                        className="campo__control"
                        id="excepcion-inicio"
                        type="datetime-local"
                        value={inicioExcepcion}
                        onChange={(e) => {
                          setInicioExcepcion(e.target.value);
                          // Al cambiar el inicio se resetea la marca de fin inválido
                          setFinInvalido(false);
                        }}
                        required
                      />
                    </div>

                    {/* Fecha de fin: datetime-local obligatorio; se marca aria-invalid si fin < inicio */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="excepcion-fin">
                        Fecha y hora de fin
                      </label>
                      <input
                        className="campo__control"
                        id="excepcion-fin"
                        type="datetime-local"
                        value={finExcepcion}
                        onChange={(e) => {
                          setFinExcepcion(e.target.value);
                          setFinInvalido(false);
                        }}
                        required
                        aria-invalid={finInvalido ? "true" : undefined}
                        aria-describedby={finInvalido ? "excepcion-fin-error" : undefined}
                      />
                      {/* Error de validación local: fin anterior a inicio */}
                      {finInvalido && (
                        <span className="campo__error" id="excepcion-fin-error" role="alert">
                          La fecha de fin no puede ser anterior a la fecha de inicio.
                        </span>
                      )}
                    </div>

                    {/* Mensaje de éxito: rango registrado y aviso si es futura (RF-06) */}
                    {exitoExcepcion && (
                      <div className="alerta alerta--exito" role="status">
                        {exitoExcepcion}
                      </div>
                    )}

                    {/* Mensajes de error según código HTTP (RF-09) */}
                    {errorExcepcion && (
                      <div className="alerta alerta--error" role="alert">
                        <span>{errorExcepcion.texto}</span>{" "}
                        {errorExcepcion.reintentable && (
                          <button
                            type="submit"
                            className="boton boton--secundario boton--sm"
                          >
                            Reintentar
                          </button>
                        )}
                      </div>
                    )}

                    <div className="formulario__acciones">
                      {/* Botón primario; disabled mientras la petición está en vuelo (RF-09) */}
                      <button
                        type="submit"
                        className="boton boton--primario"
                        disabled={enCurso === "excepcion"}
                      >
                        {enCurso === "excepcion" ? "Registrando..." : "Registrar excepción"}
                      </button>
                    </div>
                  </form>
                </div>
              </section>
            </>
          )}

          {/* Amnistía mensual: acción global con confirmación en dos pasos (T8, RF-08, RF-09) */}
          <section className="tarjeta">
            <div className="tarjeta__cabecera">Amnistía mensual</div>
            <div className="tarjeta__cuerpo">
              <div className="formulario">
                <div className="alerta alerta--aviso">
                  La amnistía mensual es una acción global que afecta a todos los perfiles elegibles
                  del sistema, no solo al usuario seleccionado. Suma puntos a perfiles en nivel BAJO
                  que no registren sanciones recientes.
                </div>

                {/* Resultado de la amnistía: N > 0 es alerta--exito, N = 0 es alerta--info (RF-08) */}
                {resultadoAmnistia && (
                  <div
                    className={`alerta ${
                      resultadoAmnistia.tipo === "exito" ? "alerta--exito" : "alerta--info"
                    }`}
                    role="status"
                  >
                    {resultadoAmnistia.texto}
                  </div>
                )}

                {/* Error de amnistía según RF-09 */}
                {errorAmnistia && (
                  <div className="alerta alerta--error" role="alert">
                    <span>{errorAmnistia.texto}</span>
                  </div>
                )}

                <div className="formulario__acciones">
                  {amnistiaPendiente ? (
                    <>
                      <button
                        type="button"
                        className="boton boton--peligro"
                        onClick={confirmarAmnistia}
                        disabled={enCurso === "amnistia"}
                      >
                        {enCurso === "amnistia" ? "Ejecutando..." : "Confirmar ejecución"}
                      </button>{" "}
                      <button
                        type="button"
                        className="boton boton--secundario"
                        onClick={cancelarAmnistia}
                        disabled={enCurso === "amnistia"}
                      >
                        Cancelar
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="boton boton--peligro"
                      onClick={pedirAmnistia}
                      disabled={enCurso === "amnistia"}
                    >
                      Ejecutar amnistía
                    </button>
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
