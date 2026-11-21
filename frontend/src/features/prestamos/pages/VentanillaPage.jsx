import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { buscarRecursos } from "../../catalogo/api.js";
import { listarUsuarios, obtenerPerfil } from "../../identidad/api.js";
import {
  cancelarReserva,
  confirmarReserva,
  convertirReservaAPrestamo,
  listarTodasReservas,
} from "../../reservas/api.js";
import {
  cancelarPrestamo,
  completarEntrega,
  consultarInspeccion,
  devolverPrestamo,
  listarTodosPrestamos,
  obtenerPlantillaChecklist,
} from "../api.js";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];
const ESTADOS_RESERVA_ATENDER = new Set(["PENDIENTE", "CONFIRMADA"]);
const ESTADOS_ACCION_DEVOLUCION = new Set(["ENTREGADO", "VENCIDO"]);

const CLASE_ESTADO_RESERVA = {
  PENDIENTE: "insignia--aviso",
  CONFIRMADA: "insignia--exito",
};

const CLASE_ESTADO_PRESTAMO = {
  POR_ENTREGAR: "insignia--info",
  ENTREGADO: "insignia--exito",
  DEVUELTO: "insignia--neutra",
  VENCIDO: "insignia--error",
  CANCELADO: "insignia--neutra",
};

const ETIQUETA_ESTADO_PRESTAMO = {
  POR_ENTREGAR: "Por entregar",
  ENTREGADO: "Entregado",
  DEVUELTO: "Devuelto",
  VENCIDO: "Vencido",
  CANCELADO: "Cancelado",
};

function mostrarFecha(fecha, textoVacio = "—") {
  if (!fecha) return textoVacio;
  try {
    return new Intl.DateTimeFormat("es-PE", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(fecha));
  } catch {
    return String(fecha);
  }
}

function mensajeError(error) {
  if (error?.status === 401) return "Tu sesión venció. Inicia sesión para continuar.";
  if (error?.status === 403) return "No tienes permiso para realizar esta acción.";
  if (error?.status === 404) return "El registro solicitado no fue encontrado.";
  if (error?.status === 409) {
    return error.message || "La operación no se puede realizar en el estado actual.";
  }
  return error?.message || "Ocurrió un error. Inténtalo de nuevo.";
}

export default function VentanillaPage() {
  const [usuario, setUsuario] = useState(null);
  const [reservas, setReservas] = useState([]);
  const [prestamos, setPrestamos] = useState([]);
  const [recursos, setRecursos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [accionId, setAccionId] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("TODOS");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");

  const contenedorPanelesRef = useRef(null);

  // Modal Entrega / Checklist Salida
  const [prestamoParaEntrega, setPrestamoParaEntrega] = useState(null);
  const [enviandoEntrega, setEnviandoEntrega] = useState(false);
  const [cargandoPlantilla, setCargandoPlantilla] = useState(false);
  const [plantillaChecklist, setPlantillaChecklist] = useState([]);
  const [elementosChecklist, setElementosChecklist] = useState({});
  const [datosEntrega, setDatosEntrega] = useState({
    tipo_garantia: "CARNET_UNIVERSITARIO",
    compromiso_testigo: "",
    compromiso_contenido:
      "El usuario asume la total responsabilidad por la integridad y cuidado del bien entregado hasta su devolución formal.",
    compromiso_firma_url: "FIRMA_CONFORME_VENTANILLA",
    observaciones_checklist: "Equipo entregado en óptimas condiciones físicas y operativas.",
    foto_url: "",
  });

  // Modal Devolución / Checklist Retorno
  const [prestamoParaDevolucion, setPrestamoParaDevolucion] = useState(null);
  const [enviandoDevolucion, setEnviandoDevolucion] = useState(false);
  const [datosDevolucion, setDatosDevolucion] = useState({
    observaciones: "Devuelto completo y conforme tras verificación técnica.",
    tipo_dano: "NINGUNO",
    monto_dano: "",
    foto_url: "",
  });

  // Panel Ver Inspecciones
  const [inspeccionVisualizada, setInspeccionVisualizada] = useState(null);
  const [cargandoInspeccion, setCargandoInspeccion] = useState(false);

  const esGestion = Boolean(usuario?.roles?.some((rol) => ROLES_GESTION.includes(rol)));

  const recursosPorId = useMemo(
    () => new Map(recursos.map((recurso) => [recurso.id, recurso])),
    [recursos]
  );

  const usuariosPorId = useMemo(
    () => new Map(usuarios.map((u) => [u.id, u])),
    [usuarios]
  );

  const reservasPorAtender = useMemo(
    () => reservas.filter((r) => ESTADOS_RESERVA_ATENDER.has(r.estado)),
    [reservas]
  );

  const prestamosFiltrados = useMemo(() => {
    if (filtroEstado === "TODOS") return prestamos;
    if (filtroEstado === "EN_CURSO") {
      return prestamos.filter(
        (p) => p.estado === "POR_ENTREGAR" || p.estado === "ENTREGADO" || p.estado === "VENCIDO"
      );
    }
    return prestamos.filter((p) => p.estado === filtroEstado);
  }, [prestamos, filtroEstado]);

  const recargarOperacion = async () => {
    const [listaReservas, listaPrestamos, listaRecursos] = await Promise.all([
      listarTodasReservas(),
      listarTodosPrestamos(),
      buscarRecursos(),
    ]);
    setReservas(listaReservas);
    setPrestamos(listaPrestamos);
    setRecursos(listaRecursos);
  };

  useEffect(() => {
    let vigente = true;

    async function cargarVentanilla() {
      if (!localStorage.getItem("token")) {
        setError("Inicia sesión con una cuenta de gestión para acceder a Ventanilla.");
        setCargando(false);
        return;
      }

      try {
        const perfil = await obtenerPerfil();
        if (!vigente) return;
        setUsuario(perfil);

        const tieneGestion = Boolean(
          perfil?.roles?.some((rol) => ROLES_GESTION.includes(rol))
        );
        if (!tieneGestion) {
          setCargando(false);
          return;
        }

        const [listaReservas, listaPrestamos, listaRecursos, listaUsuarios] = await Promise.all([
          listarTodasReservas(),
          listarTodosPrestamos(),
          buscarRecursos(),
          listarUsuarios().catch(() => []),
        ]);
        if (!vigente) return;
        setReservas(listaReservas);
        setPrestamos(listaPrestamos);
        setRecursos(listaRecursos);
        setUsuarios(listaUsuarios);
      } catch (err) {
        if (vigente) setError(mensajeError(err));
      } finally {
        if (vigente) setCargando(false);
      }
    }

    cargarVentanilla();
    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    if (prestamoParaEntrega || prestamoParaDevolucion || inspeccionVisualizada) {
      contenedorPanelesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [prestamoParaEntrega, prestamoParaDevolucion, inspeccionVisualizada]);

  const manejarConfirmarReserva = async (idReserva) => {
    setError("");
    setExito("");
    setAccionId(idReserva);
    try {
      await confirmarReserva(idReserva);
      await recargarOperacion();
      setExito("Reserva confirmada.");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setAccionId("");
    }
  };

  const manejarConvertirAPrestamo = async (idReserva) => {
    setError("");
    setExito("");
    setAccionId(idReserva);
    try {
      await convertirReservaAPrestamo(idReserva);
      await recargarOperacion();
      setExito("Préstamo iniciado en ventanilla. Ya puedes realizar la entrega física.");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setAccionId("");
    }
  };

  const manejarCancelarReserva = async (idReserva) => {
    setError("");
    setExito("");
    setAccionId(idReserva);
    try {
      await cancelarReserva(idReserva);
      await recargarOperacion();
      setExito("Reserva cancelada.");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setAccionId("");
    }
  };

  const abrirModalEntrega = async (prestamo) => {
    setError("");
    setExito("");
    setInspeccionVisualizada(null);
    setPrestamoParaDevolucion(null);
    setDatosEntrega((prev) => ({
      ...prev,
      compromiso_testigo: usuario?.nombre || "Operador de Almacén",
      foto_url: "",
    }));
    setPlantillaChecklist([]);
    setElementosChecklist({});
    setPrestamoParaEntrega(prestamo);
    setCargandoPlantilla(true);
    try {
      const plantilla = await obtenerPlantillaChecklist(prestamo.id);
      const items = Array.isArray(plantilla?.items) ? plantilla.items : [];
      setPlantillaChecklist(items);
      const estadoInicial = {};
      for (const item of items) {
        estadoInicial[item.id] = true;
      }
      setElementosChecklist(estadoInicial);
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargandoPlantilla(false);
    }
  };

  const manejarCompletarEntrega = async (e) => {
    e.preventDefault();
    if (!prestamoParaEntrega) return;
    setError("");
    setExito("");
    setEnviandoEntrega(true);

    const elementosVerificados = plantillaChecklist.map((item) =>
      elementosChecklist[item.id] !== false
        ? item.descripcion_ok || item.etiqueta
        : item.descripcion_fallo || `${item.etiqueta} (con observaciones)`
    );

    const notas = datosEntrega.observaciones_checklist.trim();
    const obsFinal = elementosVerificados.length
      ? `${elementosVerificados.join(" | ")}${notas ? `. Notas: ${notas}` : ""}`
      : notas || "Entrega verificada en ventanilla.";
    const fotos = datosEntrega.foto_url.trim() ? [datosEntrega.foto_url.trim()] : [];

    try {
      await completarEntrega(prestamoParaEntrega.id, {
        tipo_garantia: datosEntrega.tipo_garantia,
        compromiso_contenido: datosEntrega.compromiso_contenido,
        compromiso_firma_url: datosEntrega.compromiso_firma_url,
        compromiso_testigo: datosEntrega.compromiso_testigo,
        elementos_verificados: elementosVerificados,
        observaciones_checklist: obsFinal,
        fotos_urls: fotos,
      });
      setExito(
        "Entrega física completada exitosamente: garantía registrada y checklist inicial guardado."
      );
      setPrestamoParaEntrega(null);
      await recargarOperacion();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviandoEntrega(false);
    }
  };

  const abrirModalDevolucion = (prestamo) => {
    setError("");
    setExito("");
    setInspeccionVisualizada(null);
    setPrestamoParaEntrega(null);
    setDatosDevolucion({
      observaciones: "Devuelto completo y conforme tras verificación técnica.",
      tipo_dano: "NINGUNO",
      monto_dano: "",
      foto_url: "",
    });
    setPrestamoParaDevolucion(prestamo);
  };

  const manejarRegistrarDevolucion = async (e) => {
    e.preventDefault();
    if (!prestamoParaDevolucion) return;
    setError("");
    setExito("");

    const esDanoTotal = datosDevolucion.tipo_dano === "DANO_TOTAL";
    const montoNumerico = Number(datosDevolucion.monto_dano);
    if (esDanoTotal && (!datosDevolucion.monto_dano || Number.isNaN(montoNumerico) || montoNumerico <= 0)) {
      setError("Debes ingresar un monto de daño mayor a cero para daño total.");
      return;
    }

    setEnviandoDevolucion(true);

    const fotos = datosDevolucion.foto_url.trim() ? [datosDevolucion.foto_url.trim()] : [];

    try {
      const res = await devolverPrestamo(prestamoParaDevolucion.id, {
        observaciones: datosDevolucion.observaciones,
        tipo_dano: datosDevolucion.tipo_dano,
        danos_detectados: datosDevolucion.tipo_dano !== "NINGUNO",
        monto_dano: esDanoTotal ? montoNumerico : null,
        fotos_urls: fotos,
      });
      const diasRetraso = typeof res?.dias_retraso === "number" ? res.dias_retraso : 0;
      let mensaje = "Devolución registrada exitosamente. ";
      if (res?.puntual) {
        mensaje += `Entrega puntual (0 días de retraso, +10 pts en reputación). `;
      } else if (diasRetraso > 0) {
        mensaje += `No puntual: hubo ${diasRetraso} día(s) de retraso (sin bono +10 pts, se aplicó sanción por tardanza). `;
      } else {
        mensaje +=
          "No puntual: devuelto fuera de hora el mismo día (0 días de retraso, sin bono +10 pts). ";
      }
      if (datosDevolucion.tipo_dano === "DANO_PARCIAL") {
        mensaje +=
          "Se registró daño parcial: la garantía quedó retenida, el recurso pasó a mantenimiento y se penalizó la reputación.";
      } else if (datosDevolucion.tipo_dano === "DANO_TOTAL") {
        mensaje += `Se registró daño total (monto a cobrar: S/ ${montoNumerico.toFixed(
          2
        )}): la garantía quedó retenida, el recurso pasó a fuera de servicio y se penalizó la reputación.`;
      }
      setExito(mensaje);
      setPrestamoParaDevolucion(null);
      await recargarOperacion();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviandoDevolucion(false);
    }
  };

  const manejarCancelarPrestamo = async (idPrestamo) => {
    setError("");
    setExito("");
    setAccionId(idPrestamo);
    try {
      await cancelarPrestamo(idPrestamo);
      await recargarOperacion();
      setExito("Préstamo cancelado exitosamente. El recurso volvió a estar disponible.");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setAccionId("");
    }
  };

  const verInspeccion = async (idPrestamo) => {
    setCargandoInspeccion(true);
    setInspeccionVisualizada(null);
    try {
      const data = await consultarInspeccion(idPrestamo);
      setInspeccionVisualizada(data);
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargandoInspeccion(false);
    }
  };

  if (cargando) {
    return (
      <p className="cargando" role="status">
        Cargando panel de ventanilla...
      </p>
    );
  }

  if (!usuario) {
    return (
      <section aria-labelledby="titulo-ventanilla">
        <header className="pagina__cabecera">
          <h1 id="titulo-ventanilla" className="pagina__titulo">
            Ventanilla de almacén
          </h1>
          <p className="pagina__subtitulo">
            Atención presencial de reservas, entregas físicas y devoluciones.
          </p>
        </header>
        <div className="alerta alerta--aviso" role="alert">
          <span>{error || "Inicia sesión para acceder a Ventanilla."}</span>
          <Link to="/login">Iniciar sesión</Link>
        </div>
      </section>
    );
  }

  if (!esGestion) {
    return (
      <section aria-labelledby="titulo-ventanilla">
        <header className="pagina__cabecera">
          <h1 id="titulo-ventanilla" className="pagina__titulo">
            Ventanilla de almacén
          </h1>
          <p className="pagina__subtitulo">
            Esta sección es exclusiva para el personal de gestión de almacén.
          </p>
        </header>
        <div className="alerta alerta--error" role="alert">
          <span>
            No tienes permisos para acceder a la ventanilla operativa. Consulta tus operaciones en{" "}
            <Link to="/reservas">Mis Reservas</Link> o <Link to="/historial">Mis Préstamos</Link>.
          </span>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-ventanilla">
      <header className="pagina__cabecera">
        <h1 id="titulo-ventanilla" className="pagina__titulo">
          Ventanilla de almacén
        </h1>
        <p className="pagina__subtitulo">
          Atiende reservas pendientes y confirmadas, realiza entregas físicas con garantía y
          checklist, y registra devoluciones.
        </p>
      </header>

      {error && (
        <div className="alerta alerta--error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      {exito && (
        <div className="alerta alerta--exito" role="status" style={{ marginBottom: "1rem" }}>
          {exito}
        </div>
      )}

      {/* Paneles dinámicos de Entrega, Devolución e Inspección */}
      <div ref={contenedorPanelesRef}>
        {prestamoParaEntrega && (
          <div
            className="tarjeta"
            style={{ marginBottom: "2rem", border: "2px solid var(--primario)" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
              }}
            >
              <h2 className="tarjeta__titulo" style={{ margin: 0 }}>
                Inspección de salida y registro de garantía
              </h2>
              <button
                type="button"
                className="boton boton--fantasma boton--sm"
                onClick={() => setPrestamoParaEntrega(null)}
              >
                Cerrar
              </button>
            </div>
            <p className="campo__ayuda" style={{ marginBottom: "1rem" }}>
              Recurso:{" "}
              <strong>
                {recursosPorId.get(prestamoParaEntrega.recurso_id)?.nombre || "Recurso"}
              </strong>{" "}
              | Solicitante:{" "}
              <strong>
                {usuariosPorId.get(prestamoParaEntrega.usuario_id)?.nombre ||
                  prestamoParaEntrega.usuario_id}
              </strong>
            </p>

            <form onSubmit={manejarCompletarEntrega} className="formulario">
              <fieldset
                style={{
                  border: "1px solid var(--borde)",
                  borderRadius: "8px",
                  padding: "1rem",
                }}
              >
                <legend style={{ fontWeight: "600", padding: "0 0.5rem" }}>
                  1. Garantía y compromiso de responsabilidad
                </legend>
                <div className="grilla">
                  <div className="campo">
                    <label className="campo__etiqueta" htmlFor="ventanilla_tipo_garantia">
                      Tipo de garantía *
                    </label>
                    <select
                      id="ventanilla_tipo_garantia"
                      className="campo__control"
                      value={datosEntrega.tipo_garantia}
                      onChange={(e) =>
                        setDatosEntrega({ ...datosEntrega, tipo_garantia: e.target.value })
                      }
                    >
                      <option value="CARNET_UNIVERSITARIO">Carné Universitario</option>
                      <option value="DOCUMENTO_IDENTIDAD">DNI / Documento de Identidad</option>
                      <option value="DEPOSITO_ECONOMICO">Depósito Económico de Resguardo</option>
                      <option value="OTRO">Otro documento institucional</option>
                    </select>
                  </div>

                  <div className="campo">
                    <label className="campo__etiqueta" htmlFor="ventanilla_testigo">
                      Operador / Testigo *
                    </label>
                    <input
                      id="ventanilla_testigo"
                      type="text"
                      className="campo__control"
                      required
                      value={datosEntrega.compromiso_testigo}
                      onChange={(e) =>
                        setDatosEntrega({ ...datosEntrega, compromiso_testigo: e.target.value })
                      }
                    />
                  </div>

                  <div className="campo">
                    <label className="campo__etiqueta" htmlFor="ventanilla_firma">
                      Código de conformidad / Firma *
                    </label>
                    <input
                      id="ventanilla_firma"
                      type="text"
                      className="campo__control"
                      required
                      value={datosEntrega.compromiso_firma_url}
                      onChange={(e) =>
                        setDatosEntrega({ ...datosEntrega, compromiso_firma_url: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="campo" style={{ marginTop: "0.75rem" }}>
                  <label className="campo__etiqueta" htmlFor="ventanilla_compromiso">
                    Términos del compromiso
                  </label>
                  <textarea
                    id="ventanilla_compromiso"
                    className="campo__control"
                    rows={2}
                    required
                    value={datosEntrega.compromiso_contenido}
                    onChange={(e) =>
                      setDatosEntrega({ ...datosEntrega, compromiso_contenido: e.target.value })
                    }
                  />
                </div>
              </fieldset>

              <fieldset
                style={{
                  border: "1px solid var(--borde)",
                  borderRadius: "8px",
                  padding: "1rem",
                }}
              >
                <legend style={{ fontWeight: "600", padding: "0 0.5rem" }}>
                  2. Checklist de inspección física (Salida)
                </legend>
                {cargandoPlantilla ? (
                  <p className="campo__ayuda" role="status" style={{ marginBottom: "0.75rem" }}>
                    Cargando ítems de inspección según categoría del recurso...
                  </p>
                ) : plantillaChecklist.length === 0 ? (
                  <p className="campo__ayuda" style={{ marginBottom: "0.75rem" }}>
                    No se encontraron ítems sugeridos; registra las observaciones de entrega.
                  </p>
                ) : (
                  <div className="grilla" style={{ marginBottom: "0.75rem" }}>
                    {plantillaChecklist.map((item) => (
                      <label
                        key={item.id}
                        style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
                      >
                        <input
                          type="checkbox"
                          checked={elementosChecklist[item.id] !== false}
                          onChange={(e) =>
                            setElementosChecklist((prev) => ({
                              ...prev,
                              [item.id]: e.target.checked,
                            }))
                          }
                        />
                        <span>{item.etiqueta}</span>
                      </label>
                    ))}
                  </div>
                )}

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="ventanilla_obs_entrega">
                    Observaciones de entrega *
                  </label>
                  <textarea
                    id="ventanilla_obs_entrega"
                    className="campo__control"
                    rows={2}
                    required
                    value={datosEntrega.observaciones_checklist}
                    onChange={(e) =>
                      setDatosEntrega({
                        ...datosEntrega,
                        observaciones_checklist: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="campo" style={{ marginTop: "0.75rem" }}>
                  <label className="campo__etiqueta" htmlFor="ventanilla_foto_entrega">
                    URL de evidencia fotográfica (opcional)
                  </label>
                  <input
                    id="ventanilla_foto_entrega"
                    type="url"
                    className="campo__control"
                    value={datosEntrega.foto_url}
                    onChange={(e) =>
                      setDatosEntrega({ ...datosEntrega, foto_url: e.target.value })
                    }
                    placeholder="https://..."
                  />
                </div>
              </fieldset>

              <div className="formulario__acciones">
                <button
                  type="submit"
                  className="boton boton--primario"
                  disabled={enviandoEntrega}
                >
                  {enviandoEntrega ? "Registrando entrega..." : "Confirmar entrega física"}
                </button>
                <button
                  type="button"
                  className="boton boton--fantasma"
                  disabled={enviandoEntrega}
                  onClick={() => setPrestamoParaEntrega(null)}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {prestamoParaDevolucion && (
          <div
            className="tarjeta"
            style={{ marginBottom: "2rem", border: "2px solid var(--primario)" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
              }}
            >
              <h2 className="tarjeta__titulo" style={{ margin: 0 }}>
                Recepción física e inspección de retorno
              </h2>
              <button
                type="button"
                className="boton boton--fantasma boton--sm"
                onClick={() => setPrestamoParaDevolucion(null)}
              >
                Cerrar
              </button>
            </div>
            <p className="campo__ayuda" style={{ marginBottom: "1rem" }}>
              Recurso:{" "}
              <strong>
                {recursosPorId.get(prestamoParaDevolucion.recurso_id)?.nombre || "Recurso"}
              </strong>{" "}
              | Fecha pactada:{" "}
              <strong>{mostrarFecha(prestamoParaDevolucion.fecha_fin)}</strong>
            </p>

            <form onSubmit={manejarRegistrarDevolucion} className="formulario">
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="ventanilla_obs_devolucion">
                  Observaciones de recepción *
                </label>
                <textarea
                  id="ventanilla_obs_devolucion"
                  className="campo__control"
                  rows={2}
                  required
                  value={datosDevolucion.observaciones}
                  onChange={(e) =>
                    setDatosDevolucion({ ...datosDevolucion, observaciones: e.target.value })
                  }
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="ventanilla_foto_devolucion">
                  URL de evidencia fotográfica de retorno (opcional)
                </label>
                <input
                  id="ventanilla_foto_devolucion"
                  type="url"
                  className="campo__control"
                  value={datosDevolucion.foto_url}
                  onChange={(e) =>
                    setDatosDevolucion({ ...datosDevolucion, foto_url: e.target.value })
                  }
                  placeholder="https://..."
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="ventanilla_tipo_dano">
                  Evaluación de daños en retorno *
                </label>
                <select
                  id="ventanilla_tipo_dano"
                  className="campo__control"
                  value={datosDevolucion.tipo_dano}
                  onChange={(e) =>
                    setDatosDevolucion({
                      ...datosDevolucion,
                      tipo_dano: e.target.value,
                      monto_dano: e.target.value === "DANO_TOTAL" ? datosDevolucion.monto_dano : "",
                    })
                  }
                >
                  <option value="NINGUNO">Sin daños (recurso disponible)</option>
                  <option value="DANO_PARCIAL">
                    Daño parcial (reparable — pasa a mantenimiento y retiene garantía)
                  </option>
                  <option value="DANO_TOTAL">
                    Daño total / pérdida (fuera de servicio — requiere monto a cobrar)
                  </option>
                </select>
              </div>

              {datosDevolucion.tipo_dano === "DANO_TOTAL" && (
                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="ventanilla_monto_dano">
                    Monto del daño a cobrar (S/) *
                  </label>
                  <input
                    id="ventanilla_monto_dano"
                    type="number"
                    min="0.01"
                    step="0.01"
                    className="campo__control"
                    required
                    value={datosDevolucion.monto_dano}
                    onChange={(e) =>
                      setDatosDevolucion({
                        ...datosDevolucion,
                        monto_dano: e.target.value,
                      })
                    }
                    placeholder="Ej. 350.00"
                  />
                </div>
              )}

              <div className="formulario__acciones">
                <button
                  type="submit"
                  className="boton boton--primario"
                  disabled={enviandoDevolucion}
                >
                  {enviandoDevolucion ? "Registrando devolución..." : "Confirmar devolución"}
                </button>
                <button
                  type="button"
                  className="boton boton--fantasma"
                  disabled={enviandoDevolucion}
                  onClick={() => setPrestamoParaDevolucion(null)}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {inspeccionVisualizada && (
          <div className="tarjeta" style={{ marginBottom: "2rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
              }}
            >
              <h2 className="tarjeta__titulo" style={{ margin: 0 }}>
                Detalle de inspección y garantía
              </h2>
              <button
                type="button"
                className="boton boton--fantasma boton--sm"
                onClick={() => setInspeccionVisualizada(null)}
              >
                Cerrar
              </button>
            </div>
            <div className="grilla">
              <div>
                <h3>Garantía</h3>
                {inspeccionVisualizada.garantia ? (
                  <p className="campo__ayuda">
                    Tipo: <strong>{inspeccionVisualizada.garantia.tipo}</strong>
                    <br />
                    Estado: <strong>{inspeccionVisualizada.garantia.estado}</strong>
                    <br />
                    Testigo: {inspeccionVisualizada.garantia.testigo}
                    <br />
                    Registro: {mostrarFecha(inspeccionVisualizada.garantia.fecha_registro)}
                    {inspeccionVisualizada.garantia.fecha_liberacion && (
                      <>
                        <br />
                        Liberación:{" "}
                        {mostrarFecha(inspeccionVisualizada.garantia.fecha_liberacion)}
                      </>
                    )}
                  </p>
                ) : (
                  <p className="campo__ayuda">Sin garantía registrada.</p>
                )}
              </div>

              <div>
                <h3>Checklist inicial</h3>
                {inspeccionVisualizada.checklist_inicial ? (
                  <p className="campo__ayuda">
                    Fecha:{" "}
                    {mostrarFecha(inspeccionVisualizada.checklist_inicial.fecha_inspeccion)}
                    <br />
                    {inspeccionVisualizada.checklist_inicial.observaciones}
                  </p>
                ) : (
                  <p className="campo__ayuda">Pendiente de entrega física.</p>
                )}
              </div>

              <div>
                <h3>Checklist de devolución</h3>
                {inspeccionVisualizada.checklist_devolucion ? (
                  <p className="campo__ayuda">
                    Fecha:{" "}
                    {mostrarFecha(inspeccionVisualizada.checklist_devolucion.fecha_inspeccion)}
                    <br />
                    {inspeccionVisualizada.checklist_devolucion.observaciones}
                  </p>
                ) : (
                  <p className="campo__ayuda">Pendiente de devolución.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Sección 1: Reservas por atender */}
      <section aria-labelledby="subtitulo-reservas-ventanilla" style={{ marginBottom: "2.5rem" }}>
        <h2 id="subtitulo-reservas-ventanilla" style={{ marginBottom: "0.75rem" }}>
          Reservas por atender ({reservasPorAtender.length})
        </h2>

        {reservasPorAtender.length === 0 ? (
          <div className="estado-vacio">
            No hay reservas pendientes o confirmadas por atender en este momento.
          </div>
        ) : (
          <div className="tabla__contenedor">
            <table className="tabla tabla--apilada">
              <thead>
                <tr>
                  <th>Recurso</th>
                  <th>Solicitante</th>
                  <th>Periodo pactado</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {reservasPorAtender.map((reserva) => {
                  const recurso = recursosPorId.get(reserva.recurso_id);
                  const solicitante = usuariosPorId.get(reserva.usuario_id);
                  return (
                    <tr key={reserva.id}>
                      <td data-etiqueta="Recurso">
                        <strong>{recurso?.nombre || "Recurso del catálogo"}</strong>
                      </td>
                      <td data-etiqueta="Solicitante">
                        {solicitante
                          ? `${solicitante.nombre} (${solicitante.correo})`
                          : reserva.usuario_id}
                      </td>
                      <td data-etiqueta="Periodo pactado">
                        <div>Desde: {mostrarFecha(reserva.fecha_inicio)}</div>
                        <div>Hasta: {mostrarFecha(reserva.fecha_fin)}</div>
                      </td>
                      <td data-etiqueta="Estado">
                        <span
                          className={`insignia ${
                            CLASE_ESTADO_RESERVA[reserva.estado] || "insignia--neutra"
                          }`}
                        >
                          {reserva.estado}
                        </span>
                      </td>
                      <td data-etiqueta="Acciones">
                        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                          {reserva.estado === "PENDIENTE" && (
                            <button
                              type="button"
                              className="boton boton--secundario boton--sm"
                              disabled={Boolean(accionId)}
                              onClick={() => manejarConfirmarReserva(reserva.id)}
                            >
                              {accionId === reserva.id ? "Procesando..." : "Confirmar"}
                            </button>
                          )}
                          {reserva.estado === "CONFIRMADA" && (
                            <button
                              type="button"
                              className="boton boton--primario boton--sm"
                              disabled={Boolean(accionId)}
                              onClick={() => manejarConvertirAPrestamo(reserva.id)}
                            >
                              {accionId === reserva.id ? "Procesando..." : "Iniciar préstamo"}
                            </button>
                          )}
                          <button
                            type="button"
                            className="boton boton--peligro boton--sm"
                            disabled={Boolean(accionId)}
                            onClick={() => manejarCancelarReserva(reserva.id)}
                          >
                            Cancelar
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Sección 2: Préstamos en almacén */}
      <section aria-labelledby="subtitulo-prestamos-ventanilla">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "1rem",
            marginBottom: "0.75rem",
          }}
        >
          <h2 id="subtitulo-prestamos-ventanilla" style={{ margin: 0 }}>
            Préstamos en almacén ({prestamosFiltrados.length})
          </h2>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {[
              { valor: "TODOS", texto: "Todos" },
              { valor: "EN_CURSO", texto: "En curso" },
              { valor: "POR_ENTREGAR", texto: "Por entregar" },
              { valor: "ENTREGADO", texto: "Entregados" },
              { valor: "VENCIDO", texto: "Vencidos" },
              { valor: "DEVUELTO", texto: "Devueltos" },
              { valor: "CANCELADO", texto: "Cancelados" },
            ].map((f) => (
              <button
                key={f.valor}
                type="button"
                className={`boton boton--sm ${
                  filtroEstado === f.valor ? "boton--primario" : "boton--fantasma"
                }`}
                onClick={() => setFiltroEstado(f.valor)}
              >
                {f.texto}
              </button>
            ))}
          </div>
        </div>

        {prestamosFiltrados.length === 0 ? (
          <div className="estado-vacio">
            No hay préstamos registrados para el filtro seleccionado.
          </div>
        ) : (
          <div className="tabla__contenedor">
            <table className="tabla tabla--apilada">
              <thead>
                <tr>
                  <th>Recurso</th>
                  <th>Solicitante</th>
                  <th>Periodo pactado</th>
                  <th>Tiempos reales</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {prestamosFiltrados.map((prestamo) => {
                  const recurso = recursosPorId.get(prestamo.recurso_id);
                  const solicitante = usuariosPorId.get(prestamo.usuario_id);
                  const puedeDevolver = ESTADOS_ACCION_DEVOLUCION.has(prestamo.estado);

                  return (
                    <tr key={prestamo.id}>
                      <td data-etiqueta="Recurso">
                        <strong>{recurso?.nombre || "Recurso del catálogo"}</strong>
                        {recurso?.categoria && (
                          <div className="campo__ayuda">{recurso.categoria}</div>
                        )}
                      </td>
                      <td data-etiqueta="Solicitante">
                        {solicitante
                          ? `${solicitante.nombre} (${solicitante.correo})`
                          : prestamo.usuario_id}
                      </td>
                      <td data-etiqueta="Periodo pactado">
                        <div>Desde: {mostrarFecha(prestamo.fecha_inicio)}</div>
                        <div>Hasta: {mostrarFecha(prestamo.fecha_fin)}</div>
                      </td>
                      <td data-etiqueta="Tiempos reales">
                        <div>
                          Entrega: {mostrarFecha(prestamo.fecha_entrega_real, "Pendiente")}
                        </div>
                        <div>
                          Devolución: {mostrarFecha(prestamo.fecha_devolucion_real, "Pendiente")}
                        </div>
                      </td>
                      <td data-etiqueta="Estado">
                        <span
                          className={`insignia ${
                            CLASE_ESTADO_PRESTAMO[prestamo.estado] || "insignia--neutra"
                          }`}
                        >
                          {ETIQUETA_ESTADO_PRESTAMO[prestamo.estado] || prestamo.estado}
                        </span>
                      </td>
                      <td data-etiqueta="Acciones">
                        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                          {prestamo.estado === "POR_ENTREGAR" && (
                            <>
                              <button
                                type="button"
                                className="boton boton--primario boton--sm"
                                disabled={Boolean(accionId)}
                                onClick={() => abrirModalEntrega(prestamo)}
                              >
                                Realizar Entrega
                              </button>
                              <button
                                type="button"
                                className="boton boton--peligro boton--sm"
                                disabled={Boolean(accionId)}
                                onClick={() => manejarCancelarPrestamo(prestamo.id)}
                              >
                                {accionId === prestamo.id ? "Cancelando..." : "Cancelar Préstamo"}
                              </button>
                            </>
                          )}
                          {puedeDevolver && (
                            <button
                              type="button"
                              className="boton boton--secundario boton--sm"
                              disabled={Boolean(accionId)}
                              onClick={() => abrirModalDevolucion(prestamo)}
                            >
                              Registrar Devolución
                            </button>
                          )}
                          <button
                            type="button"
                            className="boton boton--fantasma boton--sm"
                            disabled={cargandoInspeccion || Boolean(accionId)}
                            onClick={() => verInspeccion(prestamo.id)}
                          >
                            Checklist
                          </button>
                        </div>
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
