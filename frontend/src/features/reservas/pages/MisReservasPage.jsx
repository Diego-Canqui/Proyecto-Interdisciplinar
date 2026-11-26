import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { buscarRecursos } from "../../catalogo/api.js";
import { obtenerPerfil } from "../../identidad/api.js";
import {
  cancelarReserva,
  listarReservasUsuario,
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

function convertirLocalAUTC(fechaLocalStr) {
  if (!fechaLocalStr) return "";
  const fecha = new Date(fechaLocalStr);
  if (Number.isNaN(fecha.getTime())) return "";
  return fecha.toISOString();
}

function esHorarioAtencionValido(fechaLocalStr) {
  const d = new Date(fechaLocalStr);
  if (Number.isNaN(d.getTime())) return false;
  const diaSemana = d.getDay(); // 0 = Domingo, 1 = Lunes, ..., 5 = Viernes, 6 = Sábado
  if (diaSemana < 1 || diaSemana > 5) return false;
  const horas = d.getHours();
  const minutos = d.getMinutes();
  const segundos = d.getSeconds();
  const segundosTotales = horas * 3600 + minutos * 60 + segundos;
  if (segundosTotales < 8 * 3600 || segundosTotales > 20 * 3600) return false;
  return true;
}

function esHoraInicioValida(fechaLocalStr) {
  const d = new Date(fechaLocalStr);
  if (Number.isNaN(d.getTime())) return false;
  const segundosTotales = d.getHours() * 3600 + d.getMinutes() * 60 + d.getSeconds();
  return segundosTotales <= 19 * 3600 + 30 * 60;
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

function mostrarHora(fecha) {
  return new Intl.DateTimeFormat("es-PE", {
    timeStyle: "short",
  }).format(fecha);
}

function mostrarSoloFecha(fecha) {
  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
  }).format(fecha);
}

function formatearVentanaRecogida(fechaInicio, fechaFin) {
  const inicio = new Date(fechaInicio);
  const fin = new Date(fechaFin);
  if (Number.isNaN(inicio.getTime()) || Number.isNaN(fin.getTime())) return "";
  const desde = new Date(inicio.getTime() - 60 * 60 * 1000);
  const limite30m = new Date(inicio.getTime() + 30 * 60 * 1000);
  const hasta = limite30m < fin ? limite30m : fin;
  const mismoDia =
    desde.getFullYear() === hasta.getFullYear() &&
    desde.getMonth() === hasta.getMonth() &&
    desde.getDate() === hasta.getDate();
  if (mismoDia) {
    return `desde las ${mostrarHora(desde)} hasta las ${mostrarHora(hasta)} (${mostrarSoloFecha(desde)})`;
  }
  return `desde el ${mostrarFecha(desde)} hasta el ${mostrarFecha(hasta)}`;
}

function formatearAvisoEnUso(disponibleDesde) {
  const advertenciaRiesgo =
    "Tu reserva quedará pendiente hasta que sea devuelto en buen estado; si hay retraso o daño, podría cancelarse.";
  if (!disponibleDesde) {
    return `El recurso está siendo usado. ${advertenciaRiesgo}`;
  }
  const fecha = new Date(disponibleDesde);
  if (Number.isNaN(fecha.getTime())) {
    return `El recurso está siendo usado. ${advertenciaRiesgo}`;
  }
  if (fecha <= new Date()) {
    return "El recurso está siendo usado y tiene una devolución pendiente.";
  }
  return `El recurso está siendo usado (disponible aprox. desde el ${mostrarFecha(fecha)}). ${advertenciaRiesgo}`;
}

function mensajeError(error) {
  if (error?.status === 401) return "Tu sesión venció. Inicia sesión para continuar.";
  if (error?.status === 403) return "No tienes permiso para realizar esta acción.";
  return error?.message || "Ocurrió un error. Inténtalo de nuevo.";
}

export default function MisReservasPage() {
  const [usuario, setUsuario] = useState(null);
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

  const esGestion = Boolean(usuario?.roles?.some((rol) => ROLES_GESTION.includes(rol)));

  const recursosPorId = useMemo(
    () => new Map(recursos.map((recurso) => [recurso.id, recurso])),
    [recursos]
  );

  const recursoSeleccionado = recursoId ? recursosPorId.get(recursoId) : null;

  const reservasActivas = reservas.filter((reserva) =>
    ESTADOS_ACTIVOS.has(reserva.estado)
  );

  const reservasCanceladasNoDisponibles = reservas.filter((reserva) => {
    if (reserva.estado !== "CANCELADA") return false;
    if (new Date(reserva.fecha_fin) <= new Date()) return false;
    const recurso = recursosPorId.get(reserva.recurso_id);
    return (
      recurso?.estado === "MANTENIMIENTO" ||
      recurso?.estado === "FUERA_DE_SERVICIO"
    );
  });

  const cargarReservas = async (perfilActual = usuario) => {
    if (!perfilActual) return;
    const datos = await listarReservasUsuario(perfilActual.id);
    setReservas(datos);
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
        const [listaRecursos, listaReservas] = await Promise.all([
          buscarRecursos(),
          listarReservasUsuario(perfil.id),
        ]);
        if (vigente) {
          setUsuario(perfil);
          setRecursos(listaRecursos);
          setReservas(listaReservas);
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

    const inicioIso = convertirLocalAUTC(fechaInicio);
    const finIso = convertirLocalAUTC(fechaFin);
    if (!inicioIso || !finIso) {
      setError("Las fechas ingresadas no son válidas.");
      return;
    }
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

    if (!esHorarioAtencionValido(fechaInicio) || !esHorarioAtencionValido(fechaFin)) {
      setError(
        "El horario de atención para entregas y devoluciones es de lunes a viernes de 08:00 a 20:00."
      );
      return;
    }

    if (!esHoraInicioValida(fechaInicio)) {
      setError(
        "La hora máxima de inicio de una reserva es a las 19:30 (para garantizar los 30 minutos de recogida antes del cierre a las 20:00)."
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
      const ventanaRecogida = formatearVentanaRecogida(
        reservaCreada?.fecha_inicio || inicioIso,
        reservaCreada?.fecha_fin || finIso
      );
      if (reservaCreada?.estado === "PENDIENTE") {
        setExito(
          "Reserva registrada como pendiente. El recurso está siendo usado actualmente; se confirmará automáticamente cuando sea devuelto en buen estado (si ocurre un retraso o daño, se cancelará y lo verás aquí)."
        );
      } else {
        setExito(
          ventanaRecogida
            ? `Reserva registrada y confirmada. Puedes recoger el recurso ${ventanaRecogida}.`
            : "Reserva registrada y confirmada."
        );
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
    return (
      <p className="cargando" role="status">
        Cargando tus reservas...
      </p>
    );
  }

  if (!usuario) {
    return (
      <section aria-labelledby="titulo-reservas">
        <header className="pagina__cabecera">
          <h1 id="titulo-reservas" className="pagina__titulo">
            Mis reservas
          </h1>
          <p className="pagina__subtitulo">
            Consulta tus solicitudes y reserva un recurso.
          </p>
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
          Mis reservas
        </h1>
        <p className="pagina__subtitulo">
          Solicita un recurso y revisa el estado de tus reservas activas.
        </p>
      </header>

      {esGestion && (
        <div className="alerta alerta--info" role="status" style={{ marginBottom: "1rem" }}>
          <span>
            La atención operativa de reservas de usuarios se realiza desde{" "}
            <Link to="/ventanilla">Ventanilla</Link>.
          </span>
        </div>
      )}

      {error && (
        <p className="alerta alerta--error" role="alert">
          {error}
        </p>
      )}
      {exito && (
        <p className="alerta alerta--exito" role="status">
          {exito}
        </p>
      )}

      <section className="tarjeta" aria-labelledby="titulo-nueva-reserva">
        <div className="tarjeta__cabecera" id="titulo-nueva-reserva">
          Solicitar una reserva
        </div>
        <div className="tarjeta__cuerpo">
          {recursos.length === 0 ? (
            <div className="estado-vacio">
              <p className="estado-vacio__titulo">No hay recursos para seleccionar</p>
              <p>Vuelve a intentarlo cuando el catálogo tenga recursos disponibles.</p>
            </div>
          ) : (
            <form className="formulario" onSubmit={enviarSolicitud}>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="recurso-reserva">
                  Recurso
                </label>
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
                  Horario de atención: lunes a viernes de 08:00 a 20:00 (inicio hasta las 19:30).
                  Duración: de 1 hora a 7 días. Anticipación máxima: 30 días. Si el horario se
                  cruza con un préstamo en curso o una reserva confirmada, deberás elegir un
                  horario libre.
                </span>
                {recursoSeleccionado?.estado === "EN_USO" && (
                  <div
                    className="alerta alerta--info"
                    role="status"
                    style={{ marginTop: "0.5rem", marginBottom: 0 }}
                  >
                    ℹ️ {formatearAvisoEnUso(recursoSeleccionado.disponible_desde)}
                  </div>
                )}
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="fecha-inicio">
                  Fecha y hora de inicio
                </label>
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
                <label className="campo__etiqueta" htmlFor="fecha-fin">
                  Fecha y hora de fin
                </label>
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
                  Horario de atención: lunes a viernes de 08:00 a 20:00 (inicio hasta las 19:30).
                  Duración: de 1 hora a 7 días.
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

      <section aria-labelledby="titulo-lista-reservas" style={{ marginTop: "2rem" }}>
        <h2 id="titulo-lista-reservas">Mis reservas activas</h2>

        {reservasCanceladasNoDisponibles.length > 0 && (
          <div
            className="alerta alerta--aviso"
            role="status"
            style={{ marginBottom: "1rem" }}
          >
            <div>
              {reservasCanceladasNoDisponibles.map((reserva) => {
                const nombre =
                  recursosPorId.get(reserva.recurso_id)?.nombre ||
                  "el recurso seleccionado";
                return (
                  <p key={reserva.id} style={{ margin: "0.25rem 0" }}>
                    Tu reserva para <strong>{nombre}</strong> (
                    {mostrarFecha(reserva.fecha_inicio)}) fue cancelada porque el
                    recurso pasó a mantenimiento o fuera de servicio.
                  </p>
                );
              })}
            </div>
          </div>
        )}

        {reservasActivas.length === 0 ? (
          <div className="estado-vacio">
            <p className="estado-vacio__titulo">No tienes reservas activas</p>
            <p>
              Cuando solicites un recurso aparecerá aquí hasta que se complete o se cancele.
            </p>
            <Link className="boton boton--secundario" to="/recursos">
              Ver catálogo
            </Link>
          </div>
        ) : (
          <div className="tabla__contenedor">
            <table className="tabla tabla--apilada">
              <thead>
                <tr>
                  <th>Recurso</th>
                  <th>Inicio</th>
                  <th>Fin</th>
                  <th>Recogida</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {reservasActivas.map((reserva) => (
                  <tr key={reserva.id}>
                    <td data-etiqueta="Recurso">
                      {recursosPorId.get(reserva.recurso_id)?.nombre ||
                        "Recurso del catálogo"}
                    </td>
                    <td data-etiqueta="Inicio">{mostrarFecha(reserva.fecha_inicio)}</td>
                    <td data-etiqueta="Fin">{mostrarFecha(reserva.fecha_fin)}</td>
                    <td data-etiqueta="Recogida">
                      {reserva.estado === "CONFIRMADA"
                        ? `Puedes recoger ${formatearVentanaRecogida(
                            reserva.fecha_inicio,
                            reserva.fecha_fin
                          )}`
                        : reserva.estado === "PENDIENTE"
                          ? "Pendiente de devolución del recurso"
                          : "—"}
                    </td>
                    <td data-etiqueta="Estado">
                      <span
                        className={`insignia ${
                          CLASE_ESTADO[reserva.estado] || "insignia--neutra"
                        }`}
                      >
                        {reserva.estado}
                      </span>
                    </td>
                    <td data-etiqueta="Acciones">
                      <button
                        type="button"
                        className="boton boton--peligro boton--sm"
                        onClick={() => manejarCancelar(reserva.id)}
                        disabled={Boolean(accionId)}
                      >
                        {accionId === reserva.id ? "Cancelando..." : "Cancelar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
