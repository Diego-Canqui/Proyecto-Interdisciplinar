import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { buscarRecursos } from "../../catalogo/api.js";
import { listarUsuarios, obtenerPerfil } from "../../identidad/api.js";
import {
  completarEntrega,
  consultarHistorial,
  consultarInspeccion,
  listarTodosPrestamos,
  registrarDevolucion,
  renovarPrestamo,
} from "../api.js";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];

const ESTADOS_ACCION_DEVOLUCION = new Set(["ACTIVO", "ENTREGADO", "VENCIDO"]);

const CLASE_ESTADO_PRESTAMO = {
  ACTIVO: "insignia--info",
  ENTREGADO: "insignia--exito",
  DEVUELTO: "insignia--neutra",
  VENCIDO: "insignia--error",
  CANCELADO: "insignia--neutra",
};

function mostrarFecha(fecha) {
  if (!fecha) return "—";
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
  if (error?.status === 404) return "El préstamo no fue encontrado.";
  if (error?.status === 409) {
    return error.message || "El préstamo no se puede operar en su estado actual.";
  }
  return error?.message || "Ocurrió un error. Inténtalo de nuevo.";
}

export default function HistorialPage() {
  const [usuario, setUsuario] = useState(null);
  const [prestamos, setPrestamos] = useState([]);
  const [recursos, setRecursos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [renovandoId, setRenovandoId] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("TODOS");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");

  // Modal Entrega / Checklist Salida
  const [prestamoParaEntrega, setPrestamoParaEntrega] = useState(null);
  const [enviandoEntrega, setEnviandoEntrega] = useState(false);
  const [datosEntrega, setDatosEntrega] = useState({
    tipo_garantia: "CARNET_UNIVERSITARIO",
    compromiso_testigo: "",
    compromiso_contenido: "El usuario asume la total responsabilidad por la integridad y cuidado del bien entregado hasta su devolución formal.",
    compromiso_firma_url: "FIRMA_CONFORME_VENTANILLA",
    check_carcasa: true,
    check_pantalla: true,
    check_cables: true,
    check_serie: true,
    observaciones_checklist: "Equipo entregado en óptimas condiciones físicas y operativas.",
    foto_url: "",
  });

  // Modal Devolución / Checklist Retorno
  const [prestamoParaDevolucion, setPrestamoParaDevolucion] = useState(null);
  const [enviandoDevolucion, setEnviandoDevolucion] = useState(false);
  const [datosDevolucion, setDatosDevolucion] = useState({
    observaciones: "Devuelto completo y conforme tras verificación técnica.",
    danos_detectados: false,
    foto_url: "",
  });

  // Modal Ver Inspecciones
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

  const prestamosFiltrados = useMemo(() => {
    if (filtroEstado === "TODOS") return prestamos;
    if (filtroEstado === "ACTIVOS") {
      return prestamos.filter((p) => p.estado === "ACTIVO" || p.estado === "ENTREGADO");
    }
    return prestamos.filter((p) => p.estado === filtroEstado);
  }, [prestamos, filtroEstado]);

  const cargarListaPrestamos = async (perfilActual) => {
    const esRolGestion = Boolean(
      perfilActual?.roles?.some((rol) => ROLES_GESTION.includes(rol))
    );
    const datos = await (esRolGestion
      ? listarTodosPrestamos()
      : consultarHistorial(perfilActual.id));
    setPrestamos(datos);
  };

  useEffect(() => {
    let vigente = true;

    async function cargarPagina() {
      if (!localStorage.getItem("token")) {
        setError("Inicia sesión para consultar el historial de préstamos.");
        setCargando(false);
        return;
      }

      try {
        const perfil = await obtenerPerfil();
        if (!vigente) return;
        setUsuario(perfil);

        const esRolGestion = Boolean(
          perfil?.roles?.some((rol) => ROLES_GESTION.includes(rol))
        );

        const [listaRecursos, listaPrestamos, listaUsuarios] = await Promise.all([
          buscarRecursos().catch(() => []),
          esRolGestion ? listarTodosPrestamos() : consultarHistorial(perfil.id),
          esRolGestion ? listarUsuarios().catch(() => []) : Promise.resolve([]),
        ]);

        if (vigente) {
          setRecursos(listaRecursos);
          setPrestamos(listaPrestamos);
          setUsuarios(listaUsuarios);
          setDatosEntrega((prev) => ({
            ...prev,
            compromiso_testigo: perfil.nombre || "Encargado de Almacén",
          }));
        }
      } catch (errorCarga) {
        if (vigente) {
          setError(mensajeError(errorCarga));
        }
      } finally {
        if (vigente) {
          setCargando(false);
        }
      }
    }

    cargarPagina();
    return () => {
      vigente = false;
    };
  }, []);

  const abrirModalEntrega = (prestamo) => {
    setError("");
    setExito("");
    setPrestamoParaEntrega(prestamo);
    setDatosEntrega((prev) => ({
      ...prev,
      compromiso_testigo: usuario?.nombre || "Encargado de Almacén",
      observaciones_checklist: "Equipo entregado en óptimas condiciones físicas y operativas.",
      check_carcasa: true,
      check_pantalla: true,
      check_cables: true,
      check_serie: true,
      foto_url: "",
    }));
  };

  const handleConfirmarEntrega = async (e) => {
    e.preventDefault();
    if (!prestamoParaEntrega) return;
    setError("");
    setExito("");
    setEnviandoEntrega(true);

    const checklistDetalle = [
      datosEntrega.check_carcasa ? "✓ Carcasa en buen estado" : "✗ Carcasa con observaciones",
      datosEntrega.check_pantalla ? "✓ Pantalla/Display operativo" : "✗ Pantalla con detalles",
      datosEntrega.check_cables ? "✓ Cables y cargador completo" : "✗ Sin cargador original",
      datosEntrega.check_serie ? "✓ Nº de serie verificado" : "✗ Nº de serie pendiente",
      datosEntrega.observaciones_checklist.trim(),
    ].filter(Boolean).join(" | ");

    const payload = {
      tipo_garantia: datosEntrega.tipo_garantia,
      compromiso_contenido: datosEntrega.compromiso_contenido,
      compromiso_firma_url: datosEntrega.compromiso_firma_url,
      compromiso_testigo: datosEntrega.compromiso_testigo,
      observaciones_checklist: checklistDetalle,
      fotos_urls: datosEntrega.foto_url ? [datosEntrega.foto_url] : [],
    };

    try {
      await completarEntrega(prestamoParaEntrega.id, payload);
      setExito("Entrega física y checklist inicial registrados con éxito. El recurso está en custodia del usuario.");
      setPrestamoParaEntrega(null);
      await cargarListaPrestamos(usuario);
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviandoEntrega(false);
    }
  };

  const abrirModalDevolucion = (prestamo) => {
    setError("");
    setExito("");
    setPrestamoParaDevolucion(prestamo);
    setDatosDevolucion({
      observaciones: "Devuelto completo y conforme tras verificación técnica.",
      danos_detectados: false,
      foto_url: "",
    });
  };

  const handleConfirmarDevolucion = async (e) => {
    e.preventDefault();
    if (!prestamoParaDevolucion) return;
    setError("");
    setExito("");
    setEnviandoDevolucion(true);

    const payload = {
      observaciones: datosDevolucion.observaciones.trim() || "Devuelto conforme",
      danos_detectados: datosDevolucion.danos_detectados,
      fotos_urls: datosDevolucion.foto_url ? [datosDevolucion.foto_url] : [],
    };

    try {
      const res = await registrarDevolucion(prestamoParaDevolucion.id, payload);
      let mensaje = "Devolución registrada exitosamente. ";
      if (typeof res?.dias_retraso === "number" && res.dias_retraso > 0) {
        mensaje += `Hubo ${res.dias_retraso} día(s) de retraso (se aplicó sanción por tardanza). `;
      } else {
        mensaje += "Entrega puntual (se premió la reputación del usuario). ";
      }
      if (datosDevolucion.danos_detectados) {
        mensaje += "Se registraron daños físicos: el recurso pasó a Mantenimiento y se penalizó la reputación.";
      }
      setExito(mensaje);
      setPrestamoParaDevolucion(null);
      await cargarListaPrestamos(usuario);
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviandoDevolucion(false);
    }
  };

  const verInspeccion = async (idPrestamo) => {
    setCargandoInspeccion(true);
    setInspeccionVisualizada(null);
    try {
      const data = await consultarInspeccion(idPrestamo);
      setInspeccionVisualizada(data);
    } catch (err) {
      setError("No se pudo obtener la información de inspección.");
    } finally {
      setCargandoInspeccion(false);
    }
  };

  const manejarRenovacion = async (idPrestamo) => {
    setError("");
    setExito("");
    setRenovandoId(idPrestamo);
    try {
      const res = await renovarPrestamo(idPrestamo);
      setExito(res?.detalle || "Préstamo renovado exitosamente por 7 días adicionales.");
      await cargarListaPrestamos(usuario);
    } catch (errorRenovacion) {
      setError(mensajeError(errorRenovacion));
    } finally {
      setRenovandoId("");
    }
  };

  if (cargando) {
    return (
      <p className="cargando" role="status">
        Cargando historial de préstamos...
      </p>
    );
  }

  if (!usuario) {
    return (
      <section aria-labelledby="titulo-historial">
        <header className="pagina__cabecera">
          <h1 id="titulo-historial" className="pagina__titulo">
            Historial de préstamos
          </h1>
          <p className="pagina__subtitulo">
            Consulta los préstamos registrados y su estado de entrega/devolución.
          </p>
        </header>
        <div className="alerta alerta--aviso" role="alert">
          <span>{error || "Inicia sesión para consultar el historial de préstamos."}</span>
          <Link to="/login">Iniciar sesión</Link>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-historial">
      <header className="pagina__cabecera">
        <h1 id="titulo-historial" className="pagina__titulo">
          Préstamos, Devoluciones y Checklists
        </h1>
        <p className="pagina__subtitulo">
          {esGestion
            ? "Ventanilla de almacén: inspección de salida (garantía + checklist), control de entrega y recepción física con detección de daños."
            : "Revisa los préstamos asociados a tus reservas, consulta el checklist de tus equipos y solicita renovaciones."}
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

      {/* MODAL / FORMULARIO FLOTANTE DE ENTREGA Y CHECKLIST INICIAL */}
      {prestamoParaEntrega && (
        <div className="tarjeta" style={{ marginBottom: "2rem", border: "2px solid var(--primario)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 style={{ fontSize: "1.25rem", margin: 0 }}>
              📋 Inspección de Salida y Formalización de Entrega
            </h2>
            <button
              type="button"
              className="boton boton--fantasma boton--sm"
              onClick={() => setPrestamoParaEntrega(null)}
            >
              ✕ Cerrar
            </button>
          </div>

          <p style={{ fontSize: "0.95rem", color: "var(--texto-secundario, #64748b)" }}>
            Recurso: <strong>{recursosPorId.get(prestamoParaEntrega.recurso_id)?.nombre || "Recurso"}</strong> | 
            Usuario: <strong>{usuariosPorId.get(prestamoParaEntrega.usuario_id)?.nombre || prestamoParaEntrega.usuario_id}</strong>
          </p>

          <form onSubmit={handleConfirmarEntrega} className="formulario" style={{ marginTop: "1rem" }}>
            {/* SECCIÓN 1: GARANTÍA */}
            <fieldset style={{ border: "1px solid var(--borde)", borderRadius: "6px", padding: "1rem", marginBottom: "1.25rem" }}>
              <legend style={{ fontWeight: "bold", padding: "0 0.5rem" }}>1. Garantía Institucional y Responsabilidad</legend>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="tipo_garantia">Tipo de Garantía *</label>
                  <select
                    id="tipo_garantia"
                    className="campo__control"
                    value={datosEntrega.tipo_garantia}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, tipo_garantia: e.target.value })}
                  >
                    <option value="CARNET_UNIVERSITARIO">Carné Universitario</option>
                    <option value="DOCUMENTO_IDENTIDAD">DNI / Documento de Identidad</option>
                    <option value="DEPOSITO_ECONOMICO">Depósito Económico de Resguardo</option>
                    <option value="OTRO">Otro documento institucional</option>
                  </select>
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="compromiso_testigo">Operador / Testigo de Entrega *</label>
                  <input
                    id="compromiso_testigo"
                    type="text"
                    className="campo__control"
                    required
                    value={datosEntrega.compromiso_testigo}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, compromiso_testigo: e.target.value })}
                    placeholder="Nombre del encargado en ventanilla"
                  />
                </div>

                <div className="campo">
                  <label className="campo__etiqueta" htmlFor="compromiso_firma_url">Código de Conformidad / Firma *</label>
                  <input
                    id="compromiso_firma_url"
                    type="text"
                    className="campo__control"
                    required
                    value={datosEntrega.compromiso_firma_url}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, compromiso_firma_url: e.target.value })}
                    placeholder="Firma digital o código de conformidad"
                  />
                </div>
              </div>

              <div className="campo" style={{ marginTop: "0.75rem" }}>
                <label className="campo__etiqueta" htmlFor="compromiso_contenido">Términos del Compromiso de Responsabilidad</label>
                <textarea
                  id="compromiso_contenido"
                  className="campo__control"
                  rows={2}
                  required
                  value={datosEntrega.compromiso_contenido}
                  onChange={(e) => setDatosEntrega({ ...datosEntrega, compromiso_contenido: e.target.value })}
                />
              </div>
            </fieldset>

            {/* SECCIÓN 2: CHECKLIST TÉCNICO */}
            <fieldset style={{ border: "1px solid var(--borde)", borderRadius: "6px", padding: "1rem", marginBottom: "1.25rem" }}>
              <legend style={{ fontWeight: "bold", padding: "0 0.5rem" }}>2. Checklist de Inspección Física (Salida)</legend>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={datosEntrega.check_carcasa}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, check_carcasa: e.target.checked })}
                  />
                  <span>Carcasa / Chasis íntegro</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={datosEntrega.check_pantalla}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, check_pantalla: e.target.checked })}
                  />
                  <span>Pantalla / Lente operativo</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={datosEntrega.check_cables}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, check_cables: e.target.checked })}
                  />
                  <span>Cables y cargador completo</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={datosEntrega.check_serie}
                    onChange={(e) => setDatosEntrega({ ...datosEntrega, check_serie: e.target.checked })}
                  />
                  <span>Nº Serie físico coincide</span>
                </label>
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="obs_checklist">Observaciones de Entrega *</label>
                <input
                  id="obs_checklist"
                  type="text"
                  className="campo__control"
                  required
                  value={datosEntrega.observaciones_checklist}
                  onChange={(e) => setDatosEntrega({ ...datosEntrega, observaciones_checklist: e.target.value })}
                  placeholder="Detalles sobre accesorios, estado cosmético, etc."
                />
              </div>

              <div className="campo" style={{ marginTop: "0.75rem" }}>
                <label className="campo__etiqueta" htmlFor="foto_entrega">URL de Fotografía de Inspección (opcional)</label>
                <input
                  id="foto_entrega"
                  type="url"
                  className="campo__control"
                  value={datosEntrega.foto_url}
                  onChange={(e) => setDatosEntrega({ ...datosEntrega, foto_url: e.target.value })}
                  placeholder="https://ejemplo.com/inspeccion-salida.jpg"
                />
              </div>
            </fieldset>

            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <button type="submit" className="boton boton--primario" disabled={enviandoEntrega}>
                {enviandoEntrega ? "Registrando Entrega..." : "✅ Confirmar Checklist y Entregar Equipo"}
              </button>
              <button
                type="button"
                className="boton boton--secundario"
                onClick={() => setPrestamoParaEntrega(null)}
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL / FORMULARIO FLOTANTE DE DEVOLUCIÓN CON INSPECCIÓN DE RETORNO */}
      {prestamoParaDevolucion && (
        <div className="tarjeta" style={{ marginBottom: "2rem", border: "2px solid var(--aviso, #f59e0b)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 style={{ fontSize: "1.25rem", margin: 0 }}>
              📥 Inspección de Retorno y Devolución del Bien
            </h2>
            <button
              type="button"
              className="boton boton--fantasma boton--sm"
              onClick={() => setPrestamoParaDevolucion(null)}
            >
              ✕ Cerrar
            </button>
          </div>

          <p style={{ fontSize: "0.95rem", color: "var(--texto-secundario, #64748b)" }}>
            Equipo: <strong>{recursosPorId.get(prestamoParaDevolucion.recurso_id)?.nombre || "Recurso"}</strong> | 
            Fecha pactada: <strong>{mostrarFecha(prestamoParaDevolucion.fecha_fin)}</strong>
          </p>

          <form onSubmit={handleConfirmarDevolucion} className="formulario" style={{ marginTop: "1rem" }}>
            <div className="campo">
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontWeight: "bold" }}>
                <input
                  type="checkbox"
                  checked={datosDevolucion.danos_detectados}
                  onChange={(e) => setDatosDevolucion({ ...datosDevolucion, danos_detectados: e.target.checked })}
                />
                <span style={{ color: datosDevolucion.danos_detectados ? "var(--error)" : "inherit" }}>
                  ⚠️ ¿Se detectaron anomalías, roturas o daños físicos al recibir el equipo?
                </span>
              </label>
              {datosDevolucion.danos_detectados && (
                <p style={{ fontSize: "0.85rem", color: "var(--error)", margin: "0.25rem 0 0" }}>
                  Al marcar esta casilla, el equipo pasará a Mantenimiento y se registrará automáticamente una sanción por daños en la reputación del usuario.
                </p>
              )}
            </div>

            <div className="campo" style={{ marginTop: "1rem" }}>
              <label className="campo__etiqueta" htmlFor="obs_devolucion">Observaciones de Recepción / Retorno *</label>
              <textarea
                id="obs_devolucion"
                className="campo__control"
                rows={2}
                required
                value={datosDevolucion.observaciones}
                onChange={(e) => setDatosDevolucion({ ...datosDevolucion, observaciones: e.target.value })}
                placeholder="Especifica el estado en el que se devuelve el equipo..."
              />
            </div>

            <div className="campo" style={{ marginTop: "0.75rem" }}>
              <label className="campo__etiqueta" htmlFor="foto_devolucion">URL Evidencia Fotográfica de Retorno (opcional)</label>
              <input
                id="foto_devolucion"
                type="url"
                className="campo__control"
                value={datosDevolucion.foto_url}
                onChange={(e) => setDatosDevolucion({ ...datosDevolucion, foto_url: e.target.value })}
                placeholder="https://ejemplo.com/inspeccion-retorno.jpg"
              />
            </div>

            <div style={{ marginTop: "1.25rem", display: "flex", gap: "1rem" }}>
              <button type="submit" className="boton boton--primario" disabled={enviandoDevolucion}>
                {enviandoDevolucion ? "Procesando Devolución..." : "📥 Confirmar Devolución e Inspección"}
              </button>
              <button
                type="button"
                className="boton boton--secundario"
                onClick={() => setPrestamoParaDevolucion(null)}
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL DETALLES DE INSPECCIÓN / CHECKLIST REGISTRADO */}
      {inspeccionVisualizada && (
        <div className="tarjeta" style={{ marginBottom: "2rem", backgroundColor: "var(--superficie-resaltada, #f8fafc)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 style={{ fontSize: "1.2rem", margin: 0 }}>🔍 Registro de Inspecciones y Garantía</h2>
            <button
              type="button"
              className="boton boton--fantasma boton--sm"
              onClick={() => setInspeccionVisualizada(null)}
            >
              ✕ Cerrar detalle
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            {/* Garantía */}
            <div style={{ border: "1px solid var(--borde)", padding: "0.75rem", borderRadius: "6px" }}>
              <h3 style={{ fontSize: "1rem", marginTop: 0 }}>Garantía Registrada</h3>
              {inspeccionVisualizada.garantia ? (
                <div style={{ fontSize: "0.9rem" }}>
                  <p><strong>Tipo:</strong> {inspeccionVisualizada.garantia.tipo}</p>
                  <p><strong>Estado:</strong> {inspeccionVisualizada.garantia.estado}</p>
                  <p><strong>Testigo:</strong> {inspeccionVisualizada.garantia.testigo}</p>
                  <p><strong>Fecha:</strong> {mostrarFecha(inspeccionVisualizada.garantia.fecha_registro)}</p>
                </div>
              ) : (
                <p style={{ fontSize: "0.85rem", color: "var(--texto-secundario)" }}>Sin garantía registrada aún.</p>
              )}
            </div>

            {/* Checklist Inicial */}
            <div style={{ border: "1px solid var(--borde)", padding: "0.75rem", borderRadius: "6px" }}>
              <h3 style={{ fontSize: "1rem", marginTop: 0 }}>Checklist de Salida (Entrega)</h3>
              {inspeccionVisualizada.checklist_inicial ? (
                <div style={{ fontSize: "0.9rem" }}>
                  <p><strong>Observaciones:</strong> {inspeccionVisualizada.checklist_inicial.observaciones}</p>
                  <p><strong>Confirmado:</strong> {inspeccionVisualizada.checklist_inicial.completo ? "Sí ✓" : "Pendiente"}</p>
                  <p><strong>Fecha inspección:</strong> {mostrarFecha(inspeccionVisualizada.checklist_inicial.fecha_inspeccion)}</p>
                  {inspeccionVisualizada.checklist_inicial.fotos_urls?.length > 0 && (
                    <p><strong>Fotos:</strong> {inspeccionVisualizada.checklist_inicial.fotos_urls.join(", ")}</p>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: "0.85rem", color: "var(--texto-secundario)" }}>Sin checklist de salida registrado.</p>
              )}
            </div>

            {/* Checklist Retorno */}
            <div style={{ border: "1px solid var(--borde)", padding: "0.75rem", borderRadius: "6px" }}>
              <h3 style={{ fontSize: "1rem", marginTop: 0 }}>Checklist de Retorno (Devolución)</h3>
              {inspeccionVisualizada.checklist_devolucion ? (
                <div style={{ fontSize: "0.9rem" }}>
                  <p><strong>Observaciones:</strong> {inspeccionVisualizada.checklist_devolucion.observaciones}</p>
                  <p><strong>Fecha retorno:</strong> {mostrarFecha(inspeccionVisualizada.checklist_devolucion.fecha_inspeccion)}</p>
                  {inspeccionVisualizada.checklist_devolucion.fotos_urls?.length > 0 && (
                    <p><strong>Fotos:</strong> {inspeccionVisualizada.checklist_devolucion.fotos_urls.join(", ")}</p>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: "0.85rem", color: "var(--texto-secundario)" }}>Equipo aún no devuelto o sin inspección de retorno.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Barra de filtros */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <label htmlFor="filtro-estado" style={{ fontSize: "0.9rem", fontWeight: "bold" }}>
            Filtrar préstamos:
          </label>
          <select
            id="filtro-estado"
            className="campo__control"
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            style={{ padding: "0.25rem 0.5rem" }}
          >
            <option value="TODOS">Todos ({prestamos.length})</option>
            <option value="ACTIVO">Activos (Pendientes de Entrega / En Uso)</option>
            <option value="ENTREGADO">Entregados en Ventanilla</option>
            <option value="DEVUELTO">Devueltos</option>
            <option value="VENCIDO">Vencidos en Mora</option>
          </select>
        </div>
        <span style={{ fontSize: "0.85rem", color: "var(--texto-secundario, #64748b)" }}>
          Total: {prestamosFiltrados.length} préstamo(s)
        </span>
      </div>

      {prestamosFiltrados.length === 0 ? (
        <div className="estado-vacio">
          <p className="estado-vacio__titulo">No hay préstamos con este criterio</p>
          <p>No se encontraron préstamos registrados para el filtro seleccionado.</p>
          <Link className="boton boton--secundario" to="/reservas">
            Ir a reservas
          </Link>
        </div>
      ) : (
        <div className="tabla__contenedor">
          <table className="tabla">
            <thead>
              <tr>
                <th>Recurso</th>
                {esGestion && <th>Usuario Solicitante</th>}
                <th>Periodo</th>
                <th>Estado</th>
                <th>Acciones de Almacén</th>
              </tr>
            </thead>
            <tbody>
              {prestamosFiltrados.map((prestamo) => {
                const recurso = recursosPorId.get(prestamo.recurso_id);
                const nombreRecurso = recurso?.nombre || "Recurso del catálogo";
                const usuarioObj = usuariosPorId.get(prestamo.usuario_id);
                const nombreUsuario = usuarioObj
                  ? `${usuarioObj.nombre} (${usuarioObj.correo})`
                  : prestamo.usuario_id;
                const puedeDevolver = esGestion && ESTADOS_ACCION_DEVOLUCION.has(prestamo.estado);
                const puedeRenovar = prestamo.estado === "ACTIVO" || prestamo.estado === "ENTREGADO";
                const estaRenovando = renovandoId === prestamo.id;

                return (
                  <tr key={prestamo.id}>
                    <td data-etiqueta="Recurso">
                      <strong>{nombreRecurso}</strong>
                      {recurso?.categoria && (
                        <div style={{ fontSize: "0.8rem", color: "var(--texto-secundario, #64748b)" }}>
                          {recurso.categoria}
                        </div>
                      )}
                    </td>
                    {esGestion && <td data-etiqueta="Usuario">{nombreUsuario}</td>}
                    <td data-etiqueta="Periodo">
                      <div style={{ fontSize: "0.85rem" }}>
                        <div><strong>Desde:</strong> {mostrarFecha(prestamo.fecha_inicio)}</div>
                        <div><strong>Hasta:</strong> {mostrarFecha(prestamo.fecha_fin)}</div>
                      </div>
                    </td>
                    <td data-etiqueta="Estado">
                      <span
                        className={`insignia ${
                          CLASE_ESTADO_PRESTAMO[prestamo.estado] || "insignia--neutra"
                        }`}
                      >
                        {prestamo.estado}
                      </span>
                    </td>
                    <td data-etiqueta="Acciones">
                      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                        {/* Botón de Entrega Física con Checklist (Gestores, cuando el préstamo está ACTIVO pero no formalizado) */}
                        {esGestion && prestamo.estado === "ACTIVO" && (
                          <button
                            type="button"
                            className="boton boton--primario boton--sm"
                            onClick={() => abrirModalEntrega(prestamo)}
                            title="Completar garantía y checklist de entrega"
                          >
                            📋 Realizar Entrega
                          </button>
                        )}

                        {/* Botón de Devolución con Checklist de Retorno */}
                        {puedeDevolver && (
                          <button
                            type="button"
                            className="boton boton--secundario boton--sm"
                            onClick={() => abrirModalDevolucion(prestamo)}
                            title="Recepción física y verificación de estado"
                          >
                            📥 Registrar Devolución
                          </button>
                        )}

                        {/* Botón de Renovación */}
                        {puedeRenovar && (
                          <button
                            type="button"
                            className="boton boton--fantasma boton--sm"
                            disabled={renovandoId !== ""}
                            onClick={() => manejarRenovacion(prestamo.id)}
                            title="Extender fecha límite 7 días"
                          >
                            {estaRenovando ? "..." : "🔄 +7 días"}
                          </button>
                        )}

                        {/* Botón de Consulta de Checklist/Inspección */}
                        <button
                          type="button"
                          className="boton boton--fantasma boton--sm"
                          disabled={cargandoInspeccion}
                          onClick={() => verInspeccion(prestamo.id)}
                          title="Consultar checklist y garantía"
                        >
                          🔍 Checklist
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
  );
}
