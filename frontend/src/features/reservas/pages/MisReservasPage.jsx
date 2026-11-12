import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listarUsuarios, obtenerPerfil } from "../../identidad/api.js";
import { buscarRecursos } from "../../catalogo/api.js";
import {
  cancelarReserva,
  confirmarReserva,
  convertirReservaAPrestamo,
  listarReservasUsuario,
  listarTodasReservas,
  solicitarReserva,
} from "../api.js";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];
const ESTADOS_ACTIVOS = new Set(["PENDIENTE", "CONFIRMADA"]);

const CLASE_ESTADO = {
  PENDIENTE: "insignia--aviso",
  CONFIRMADA: "insignia--exito",
  CANCELADA: "insignia--neutra",
  VENCIDA: "insignia--error",
  CONVERTIDA: "insignia--info",
};

function fechaLocalMinima() {
  const ahora = new Date();
  ahora.setMinutes(ahora.getMinutes() - ahora.getTimezoneOffset());
  return ahora.toISOString().slice(0, 16);
}

function formatearFechaNominalUTC(fechaLocalStr) {
  if (!fechaLocalStr) return "";
  if (fechaLocalStr.endsWith("Z")) return fechaLocalStr;
  if (fechaLocalStr.length === 16) {
    return `${fechaLocalStr}:00Z`;
  }
  return `${fechaLocalStr}Z`;
}

function esHorarioAtencionValido(fechaIsoNominal) {
  const d = new Date(fechaIsoNominal);
  if (Number.isNaN(d.getTime())) return false;
  const diaSemana = d.getUTCDay(); // 0 = Domingo, 1 = Lunes, ..., 5 = Viernes, 6 = Sábado
  if (diaSemana < 1 || diaSemana > 5) return false;
  const horas = d.getUTCHours();
  const minutos = d.getUTCMinutes();
  const segundos = d.getUTCSeconds();
  const segundosTotales = horas * 3600 + minutos * 60 + segundos;
  if (segundosTotales < 8 * 3600 || segundosTotales > 20 * 3600) return false;
  return true;
}

function calcularFechaMaxima(fechaInicioStr) {
  if (!fechaInicioStr) return undefined;
  const fecha = new Date(fechaInicioStr);
  if (Number.isNaN(fecha.getTime())) return undefined;
  const fechaMax = new Date(fecha.getTime() + 7 * 24 * 60 * 60 * 1000);
  const fechaAjustada = new Date(fechaMax.getTime() - fechaMax.getTimezoneOffset() * 60000);
  return fechaAjustada.toISOString().slice(0, 16);
}

function mostrarFecha(fecha) {
  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(fecha));
}

function mensajeError(error) {
  if (error?.status === 401) return "Tu sesión venció. Inicia sesión para continuar.";
  if (error?.status === 403) return "No tienes permiso para realizar esta acción.";
  return error?.message || "Ocurrió un error. Inténtalo de nuevo.";
}

export default function MisReservasPage() {
  const [usuario, setUsuario] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [recursos, setRecursos] = useState([]);
  const [reservas, setReservas] = useState([]);
  const [searchParams] = useSearchParams();
  const recursoParam = searchParams.get("recursoId") || "";
  const [recursoId, setRecursoId] = useState(recursoParam);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [accionId, setAccionId] = useState("");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");

  const esGestion = Boolean(
    usuario?.roles?.some((rol) => ROLES_GESTION.includes(rol))
  );

  const recursosPorId = useMemo(
    () => new Map(recursos.map((recurso) => [recurso.id, recurso])),
    [recursos]
  );

  const usuariosPorId = useMemo(
    () => new Map(usuarios.map((u) => [u.id, u])),
    [usuarios]
  );

  const reservasActivas = reservas.filter((reserva) =>
    ESTADOS_ACTIVOS.has(reserva.estado)
  );

  const accionEnCurso = Boolean(accionId);

  const cargarReservas = async (perfilActual = usuario) => {
    if (!perfilActual) return;
    const tieneGestion = Boolean(
      perfilActual?.roles?.some((rol) => ROLES_GESTION.includes(rol))
    );
    if (tieneGestion) {
      const datos = await listarTodasReservas();
      setReservas(datos);
    } else {
      const datos = await listarReservasUsuario(perfilActual.id);
      setReservas(datos);
    }
  };

  useEffect(() => {
    let vigente = true;

    async function cargarPagina() {
      if (!localStorage.getItem("token")) {
        setError("Inicia sesión para consultar y solicitar reservas.");
        setCargando(false);
        return;
      }

      try {
        const perfil = await obtenerPerfil();
        const tieneGestion = Boolean(
          perfil?.roles?.some((rol) => ROLES_GESTION.includes(rol))
        );

        if (tieneGestion) {
          const [listaRecursos, listaReservas, listaUsuarios] = await Promise.all([
            buscarRecursos(),
            listarTodasReservas(),
            listarUsuarios().catch(() => []),
          ]);
          if (vigente) {
            setUsuario(perfil);
            setRecursos(listaRecursos);
            setReservas(listaReservas);
            setUsuarios(listaUsuarios || []);
          }
        } else {
          const [listaRecursos, listaReservas] = await Promise.all([
            buscarRecursos(),
            listarReservasUsuario(perfil.id),
          ]);
          if (vigente) {
            setUsuario(perfil);
            setRecursos(listaRecursos);
            setReservas(listaReservas);
            setUsuarios([]);
          }
        }
      } catch (errorCarga) {
        if (vigente) setError(mensajeError(errorCarga));
      } finally {
        if (vigente) setCargando(false);
      }
    }

    cargarPagina();
    return () => {
      vigente = false;
    };
  }, []);

  const enviarSolicitud = async (evento) => {
    evento.preventDefault();
    setError("");
    setExito("");

    if (!usuario || !recursoId || !fechaInicio || !fechaFin) {
      setError("Completa el recurso y las fechas para solicitar la reserva.");
      return;
    }

    const inicioIso = formatearFechaNominalUTC(fechaInicio);
    const finIso = formatearFechaNominalUTC(fechaFin);
    const inicio = new Date(inicioIso);
    const fin = new Date(finIso);

    if (fin <= inicio) {
      setError("La fecha de fin debe ser posterior a la fecha de inicio.");
      return;
    }

    if (fin - inicio < 60 * 60 * 1000) {
      setError("La duración mínima de una reserva es de 1 hora.");
      return;
    }

    if (fin - inicio > 7 * 24 * 60 * 60 * 1000) {
      setError("La duración máxima de una reserva es de 7 días.");
      return;
    }

    if (!esHorarioAtencionValido(inicioIso) || !esHorarioAtencionValido(finIso)) {
      setError(
        "El horario de atención para entregas y devoluciones es de lunes a viernes de 08:00 a 20:00."
      );
      return;
    }

    setEnviando(true);
    try {
      const reservaCreada = await solicitarReserva({
        usuario_id: usuario.id,
        recurso_id: recursoId,
        fecha_inicio: inicioIso,
        fecha_fin: finIso,
      });
      if (reservaCreada?.id) {
        setReservas((prev) => [
          ...prev.filter((r) => r.id !== reservaCreada.id),
          reservaCreada,
        ]);
      }
      if (reservaCreada?.estado === "PENDIENTE") {
        setExito(
          "El horario ya tiene una reserva confirmada. Tu solicitud quedó en lista de espera (PENDIENTE) y se priorizará según tu reputación."
        );
      } else {
        setExito("Reserva registrada y confirmada.");
      }
      await cargarReservas(usuario);
      setRecursoId("");
      setFechaInicio("");
      setFechaFin("");
    } catch (errorSolicitud) {
      setError(mensajeError(errorSolicitud));
    } finally {
      setEnviando(false);
    }
  };

  const manejarConfirmar = async (idReserva) => {
    setError("");
    setExito("");
    setAccionId(idReserva);
    try {
      const confirmada = await confirmarReserva(idReserva);
      if (confirmada?.id) {
        setReservas((prev) =>
          prev.map((r) => (r.id === confirmada.id ? confirmada : r))
        );
      }
      await cargarReservas(usuario);
      setExito("Reserva confirmada.");
    } catch (errorAccion) {
      setError(mensajeError(errorAccion));
    } finally {
      setAccionId("");
    }
  };

  const manejarIniciarPrestamo = async (idReserva) => {
    setError("");
    setExito("");
    setAccionId(idReserva);
    try {
      await convertirReservaAPrestamo(idReserva);
      setReservas((prev) => prev.filter((r) => r.id !== idReserva));
      const [, listaRecursos] = await Promise.all([
        cargarReservas(usuario),
        buscarRecursos(),
      ]);
      setRecursos(listaRecursos);
      setExito("Préstamo iniciado. Puedes consultarlo y registrar su devolución en Historial.");
    } catch (errorAccion) {
      setError(mensajeError(errorAccion));
    } finally {
      setAccionId("");
    }
  };

  const manejarCancelar = async (idReserva) => {
    setError("");
    setExito("");
    setAccionId(idReserva);
    try {
      await cancelarReserva(idReserva);
      setReservas((prev) => prev.filter((r) => r.id !== idReserva));
      await cargarReservas(usuario);
      setExito("Reserva cancelada.");
    } catch (errorAccion) {
      setError(mensajeError(errorAccion));
    } finally {
      setAccionId("");
    }
  };

  if (cargando) {
    return <p className="cargando" role="status">Cargando tus reservas...</p>;
  }

  if (!usuario) {
    return (
      <section aria-labelledby="titulo-reservas">
        <header className="pagina__cabecera">
          <h1 id="titulo-reservas" className="pagina__titulo">Mis reservas</h1>
          <p className="pagina__subtitulo">Consulta tus solicitudes y reserva un recurso.</p>
        </header>
        <div className="alerta alerta--aviso" role="alert">
          <span>{error}</span>
          <Link to="/login">Iniciar sesión</Link>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-reservas">
      <header className="pagina__cabecera">
        <h1 id="titulo-reservas" className="pagina__titulo">
          {esGestion ? "Gestión de reservas" : "Mis reservas"}
        </h1>
        <p className="pagina__subtitulo">
          {esGestion
            ? "Supervisa, confirma, inicia el préstamo o cancela las solicitudes de reserva de los usuarios."
            : "Solicita un recurso y revisa el estado de tus reservas activas."}
        </p>
      </header>

      {error && <p className="alerta alerta--error" role="alert">{error}</p>}
      {exito && <p className="alerta alerta--exito" role="status">{exito}</p>}

      {!esGestion && (
        <section className="tarjeta" aria-labelledby="titulo-nueva-reserva">
          <div className="tarjeta__cabecera" id="titulo-nueva-reserva">Solicitar una reserva</div>
          <div className="tarjeta__cuerpo">
            {recursos.length === 0 ? (
              <div className="estado-vacio">
                <p className="estado-vacio__titulo">No hay recursos para seleccionar</p>
                <p>Vuelve a intentarlo cuando el catálogo tenga recursos disponibles.</p>
              </div>
            ) : (
              <form className="formulario" onSubmit={enviarSolicitud}>
                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="recurso-reserva">Recurso</label>
                  <select
                    className="campo__control"
                    id="recurso-reserva"
                    value={recursoId}
                    onChange={(evento) => setRecursoId(evento.target.value)}
                    required
                  >
                    <option value="">Selecciona un recurso</option>
                    {recursos.map((recurso) => {
                      const noDisponible =
                        recurso.estado === "MANTENIMIENTO" ||
                        recurso.estado === "FUERA_DE_SERVICIO";
                      return (
                        <option
                          key={recurso.id}
                          value={recurso.id}
                          disabled={noDisponible}
                        >
                          {recurso.nombre} — {recurso.categoria} ({recurso.estado})
                          {noDisponible ? " — (No disponible para reservas)" : ""}
                        </option>
                      );
                    })}
                  </select>
                  <span className="campo__ayuda">
                    Horario de atención: lunes a viernes de 08:00 a 20:00. Duración: de 1 hora a 7 días. Anticipación máxima: 30 días. Si el horario se cruza con otra reserva, entrará en lista de espera priorizada por reputación.
                  </span>
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="fecha-inicio">Fecha y hora de inicio</label>
                  <input
                    className="campo__control"
                    id="fecha-inicio"
                    type="datetime-local"
                    min={fechaLocalMinima()}
                    value={fechaInicio}
                    onChange={(evento) => setFechaInicio(evento.target.value)}
                    required
                  />
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="fecha-fin">Fecha y hora de fin</label>
                  <input
                    className="campo__control"
                    id="fecha-fin"
                    type="datetime-local"
                    min={fechaInicio || fechaLocalMinima()}
                    max={fechaInicio ? calcularFechaMaxima(fechaInicio) : undefined}
                    value={fechaFin}
                    onChange={(evento) => setFechaFin(evento.target.value)}
                    required
                  />
                  <span className="campo__ayuda">
                    Horario de atención: lunes a viernes de 08:00 a 20:00. Duración: de 1 hora a 7 días.
                  </span>
                </div>

                <div className="formulario__acciones">
                  <button className="boton boton--primario" type="submit" disabled={enviando}>
                    {enviando ? "Enviando solicitud..." : "Solicitar reserva"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </section>
      )}

      <section aria-labelledby="titulo-reservas-activas">
        <header className="pagina__cabecera">
          <h2 id="titulo-reservas-activas" className="pagina__titulo">Reservas activas</h2>
        </header>

        {reservasActivas.length === 0 ? (
          <div className="estado-vacio">
            <p className="estado-vacio__titulo">
              {esGestion
                ? "No hay reservas activas en el sistema"
                : "Todavía no tienes reservas activas"}
            </p>
            <p>
              {esGestion
                ? "Cuando los usuarios soliciten reservas, aparecerán listadas aquí."
                : "Completa el formulario para solicitar un recurso."}
            </p>
            <Link className="boton boton--secundario" to="/recursos">Ver catálogo</Link>
          </div>
        ) : (
          <div className="tabla__contenedor">
            <table className="tabla tabla--apilada">
              <thead>
                <tr>
                  <th>Recurso</th>
                  {esGestion && <th>Usuario</th>}
                  <th>Inicio</th>
                  <th>Fin</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {reservasActivas.map((reserva) => {
                  const titular = usuariosPorId.get(reserva.usuario_id);
                  const textoUsuario = titular
                    ? `${titular.nombre} (${titular.correo})`
                    : reserva.usuario_id || "Usuario desconocido";

                  return (
                    <tr key={reserva.id}>
                      <td data-etiqueta="Recurso">
                        {recursosPorId.get(reserva.recurso_id)?.nombre || "Recurso del catálogo"}
                      </td>
                      {esGestion && (
                        <td data-etiqueta="Usuario">{textoUsuario}</td>
                      )}
                      <td data-etiqueta="Inicio">{mostrarFecha(reserva.fecha_inicio)}</td>
                      <td data-etiqueta="Fin">{mostrarFecha(reserva.fecha_fin)}</td>
                      <td data-etiqueta="Estado">
                        <span className={`insignia ${CLASE_ESTADO[reserva.estado] || "insignia--neutra"}`}>
                          {reserva.estado}
                        </span>
                      </td>
                      <td data-etiqueta="Acciones">
                        {reserva.estado === "PENDIENTE" && (
                          <>
                            {esGestion && (
                              <button
                                type="button"
                                className="boton boton--secundario boton--sm"
                                onClick={() => manejarConfirmar(reserva.id)}
                                disabled={accionEnCurso}
                              >
                                {accionId === reserva.id ? "Confirmando..." : "Confirmar"}
                              </button>
                            )}
                            {esGestion && " "}
                            <button
                              type="button"
                              className="boton boton--peligro boton--sm"
                              onClick={() => manejarCancelar(reserva.id)}
                              disabled={accionEnCurso}
                            >
                              Cancelar
                            </button>
                          </>
                        )}
                        {reserva.estado === "CONFIRMADA" && (
                          <>
                            {esGestion && (
                              <button
                                type="button"
                                className="boton boton--secundario boton--sm"
                                onClick={() => manejarIniciarPrestamo(reserva.id)}
                                disabled={accionEnCurso}
                              >
                                {accionId === reserva.id ? "Iniciando..." : "Iniciar préstamo"}
                              </button>
                            )}
                            {esGestion && " "}
                            <button
                              type="button"
                              className="boton boton--peligro boton--sm"
                              onClick={() => manejarCancelar(reserva.id)}
                              disabled={accionEnCurso}
                            >
                              Cancelar
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
