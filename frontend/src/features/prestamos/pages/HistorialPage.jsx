import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { buscarRecursos } from "../../catalogo/api.js";
import { obtenerPerfil } from "../../identidad/api.js";
import {
  consultarHistorial,
  consultarInspeccion,
  renovarPrestamo,
} from "../api.js";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];
const ESTADOS_RENOVABLES = new Set(["ACTIVO", "ENTREGADO"]);

const CLASE_ESTADO_PRESTAMO = {
  ACTIVO: "insignia--info",
  ENTREGADO: "insignia--exito",
  DEVUELTO: "insignia--neutra",
  VENCIDO: "insignia--error",
  CANCELADO: "insignia--neutra",
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
  const [cargando, setCargando] = useState(true);
  const [renovandoId, setRenovandoId] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("TODOS");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");

  const [inspeccionVisualizada, setInspeccionVisualizada] = useState(null);
  const [cargandoInspeccion, setCargandoInspeccion] = useState(false);
  const contenedorPanelRef = useRef(null);

  const esGestion = Boolean(usuario?.roles?.some((rol) => ROLES_GESTION.includes(rol)));

  const recursosPorId = useMemo(
    () => new Map(recursos.map((recurso) => [recurso.id, recurso])),
    [recursos]
  );

  const prestamosFiltrados = useMemo(() => {
    if (filtroEstado === "TODOS") return prestamos;
    if (filtroEstado === "ACTIVOS") {
      return prestamos.filter((p) => p.estado === "ACTIVO" || p.estado === "ENTREGADO");
    }
    return prestamos.filter((p) => p.estado === filtroEstado);
  }, [prestamos, filtroEstado]);

  const cargarHistorial = async (perfilActual) => {
    const datos = await consultarHistorial(perfilActual.id);
    setPrestamos(datos);
  };

  useEffect(() => {
    let vigente = true;

    async function cargarPagina() {
      if (!localStorage.getItem("token")) {
        setError("Inicia sesión para consultar tu historial de préstamos.");
        setCargando(false);
        return;
      }

      try {
        const perfil = await obtenerPerfil();
        if (!vigente) return;
        setUsuario(perfil);

        const [listaRecursos, listaPrestamos] = await Promise.all([
          buscarRecursos(),
          consultarHistorial(perfil.id),
        ]);
        if (!vigente) return;
        setRecursos(listaRecursos);
        setPrestamos(listaPrestamos);
      } catch (err) {
        if (vigente) setError(mensajeError(err));
      } finally {
        if (vigente) setCargando(false);
      }
    }

    cargarPagina();
    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    if (inspeccionVisualizada) {
      contenedorPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [inspeccionVisualizada]);

  const verInspeccion = async (idPrestamo) => {
    setError("");
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

  const manejarRenovacion = async (idPrestamo) => {
    setError("");
    setExito("");
    setRenovandoId(idPrestamo);
    try {
      await renovarPrestamo(idPrestamo);
      await cargarHistorial(usuario);
      setExito("Préstamo renovado exitosamente por 7 días.");
    } catch (err) {
      setError(mensajeError(err));
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
            Mis préstamos
          </h1>
          <p className="pagina__subtitulo">
            Consulta tus préstamos registrados, tiempos reales y checklists de inspección.
          </p>
        </header>
        <div className="alerta alerta--aviso" role="alert">
          <span>{error || "Inicia sesión para consultar tus préstamos."}</span>
          <Link to="/login">Iniciar sesión</Link>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-historial">
      <header className="pagina__cabecera">
        <h1 id="titulo-historial" className="pagina__titulo">
          Mis préstamos
        </h1>
        <p className="pagina__subtitulo">
          Revisa el periodo pactado, las fechas reales de entrega y devolución, y el detalle de
          inspección de tus equipos.
        </p>
      </header>

      {esGestion && (
        <div className="alerta alerta--info" role="status" style={{ marginBottom: "1rem" }}>
          <span>
            Las entregas físicas, devoluciones y cancelaciones de almacén se gestionan desde{" "}
            <Link to="/ventanilla">Ventanilla</Link>.
          </span>
        </div>
      )}

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

      <div ref={contenedorPanelRef}>
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
                  <p className="campo__ayuda">Sin garantía registrada aún.</p>
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

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        {[
          { valor: "TODOS", texto: "Todos" },
          { valor: "ACTIVOS", texto: "En curso" },
          { valor: "DEVUELTO", texto: "Devueltos" },
          { valor: "VENCIDO", texto: "Vencidos" },
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

      {prestamosFiltrados.length === 0 ? (
        <div className="estado-vacio">
          <p className="estado-vacio__titulo">No tienes préstamos en esta categoría</p>
          <p>Cuando retires un recurso reservado aparecerá aquí con su detalle.</p>
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
                <th>Periodo pactado</th>
                <th>Tiempos reales</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {prestamosFiltrados.map((prestamo) => {
                const recurso = recursosPorId.get(prestamo.recurso_id);
                const puedeRenovar = ESTADOS_RENOVABLES.has(prestamo.estado);

                return (
                  <tr key={prestamo.id}>
                    <td data-etiqueta="Recurso">
                      <strong>{recurso?.nombre || "Recurso del catálogo"}</strong>
                      {recurso?.categoria && (
                        <div className="campo__ayuda">{recurso.categoria}</div>
                      )}
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
                        {prestamo.estado}
                      </span>
                    </td>
                    <td data-etiqueta="Acciones">
                      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        <button
                          type="button"
                          className="boton boton--fantasma boton--sm"
                          disabled={cargandoInspeccion || Boolean(renovandoId)}
                          onClick={() => verInspeccion(prestamo.id)}
                        >
                          Checklist
                        </button>
                        {puedeRenovar && (
                          <button
                            type="button"
                            className="boton boton--secundario boton--sm"
                            disabled={Boolean(renovandoId)}
                            onClick={() => manejarRenovacion(prestamo.id)}
                          >
                            {renovandoId === prestamo.id ? "Renovando..." : "Renovar"}
                          </button>
                        )}
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
