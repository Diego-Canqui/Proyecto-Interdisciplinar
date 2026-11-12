import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  buscarRecursos,
  consultarDisponibilidad,
  obtenerFichaTecnica,
  crearRecurso,
  actualizarEstadoRecurso,
} from "../api.js";
import { obtenerPerfil } from "../../identidad/api.js";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];

const CLASE_ESTADO = {
  DISPONIBLE: "insignia--exito",
  EN_USO: "insignia--info",
  MANTENIMIENTO: "insignia--aviso",
  FUERA_DE_SERVICIO: "insignia--error",
};

export default function BuscarRecursosPage() {
  const [filtro, setFiltro] = useState("");
  const [recursos, setRecursos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exito, setExito] = useState(null);
  const [recursoSeleccionado, setRecursoSeleccionado] = useState(null);
  const [fichaTecnica, setFichaTecnica] = useState(null);
  const [cargandoFicha, setCargandoFicha] = useState(false);
  const [usuario, setUsuario] = useState(null);
  const [mostrarModalCrear, setMostrarModalCrear] = useState(false);

  // Formulario nuevo recurso
  const [nuevoRecurso, setNuevoRecurso] = useState({
    nombre: "",
    descripcion: "",
    categoria: "",
    marca: "",
    modelo: "",
    numero_serie: "",
    color: "",
    estado_fisico: "OPERATIVO",
    foto_url: "",
  });
  const [creando, setCreando] = useState(false);

  // Estado para actualización rápida de estado por gestor
  const [nuevoEstadoSeleccionado, setNuevoEstadoSeleccionado] = useState("");
  const [actualizandoEstado, setActualizandoEstado] = useState(false);

  const esGestion = Boolean(
    usuario?.roles?.some((rol) => ROLES_GESTION.includes(rol))
  );

  const cargarRecursos = async (filtroTerm = "") => {
    setLoading(true);
    setError(null);
    try {
      const data = await buscarRecursos(filtroTerm);
      setRecursos(data);
    } catch (err) {
      setError("Error al cargar los recursos del catálogo.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarRecursos();
    obtenerPerfil()
      .then((perfil) => setUsuario(perfil))
      .catch(() => setUsuario(null));
  }, []);

  const handleBuscar = (e) => {
    e.preventDefault();
    cargarRecursos(filtro);
  };

  const handleSeleccionarRecurso = async (recurso) => {
    setRecursoSeleccionado(recurso);
    setNuevoEstadoSeleccionado(recurso.estado);
    setFichaTecnica(null);
    setCargandoFicha(true);
    try {
      const fichaData = await obtenerFichaTecnica(recurso.id);
      setFichaTecnica(fichaData);
    } catch (err) {
      console.error("Error al obtener ficha técnica del recurso", err);
    } finally {
      setCargandoFicha(false);
    }
  };

  const handleCrearRecurso = async (e) => {
    e.preventDefault();
    setError(null);
    setExito(null);
    setCreando(true);
    try {
      await crearRecurso(nuevoRecurso);
      setExito("Recurso registrado exitosamente en el catálogo.");
      setMostrarModalCrear(false);
      setNuevoRecurso({
        nombre: "",
        descripcion: "",
        categoria: "",
        marca: "",
        modelo: "",
        numero_serie: "",
        color: "",
        estado_fisico: "OPERATIVO",
        foto_url: "",
      });
      await cargarRecursos(filtro);
    } catch (err) {
      setError(err?.message || "Error al crear el recurso.");
    } finally {
      setCreando(false);
    }
  };

  const handleCambiarEstado = async () => {
    if (!recursoSeleccionado || !nuevoEstadoSeleccionado) return;
    setError(null);
    setExito(null);
    setActualizandoEstado(true);
    try {
      await actualizarEstadoRecurso(recursoSeleccionado.id, nuevoEstadoSeleccionado);
      setExito(`Estado del recurso actualizado a ${nuevoEstadoSeleccionado}.`);
      setRecursoSeleccionado((prev) => ({ ...prev, estado: nuevoEstadoSeleccionado }));
      await cargarRecursos(filtro);
    } catch (err) {
      setError(err?.message || "Error al actualizar el estado del recurso.");
    } finally {
      setActualizandoEstado(false);
    }
  };

  return (
    <section aria-labelledby="titulo-catalogo">
      <header className="pagina__cabecera">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1 id="titulo-catalogo" className="pagina__titulo">
              Catálogo de Recursos
            </h1>
            <p className="pagina__subtitulo">
              Explora y gestiona los equipos, laboratorios y herramientas disponibles en la institución.
            </p>
          </div>
          {esGestion && (
            <button
              type="button"
              className="boton boton--primario"
              onClick={() => setMostrarModalCrear(!mostrarModalCrear)}
            >
              {mostrarModalCrear ? "✕ Cancelar registro" : "＋ Registrar nuevo recurso"}
            </button>
          )}
        </div>
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

      {/* Formulario de creación para Gestor/Administrador */}
      {mostrarModalCrear && esGestion && (
        <div className="tarjeta" style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Registrar Nuevo Recurso</h2>
          <form onSubmit={handleCrearRecurso} className="formulario">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor="nombre">Nombre del Recurso *</label>
                <input
                  id="nombre"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.nombre}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, nombre: e.target.value })}
                  placeholder="Ej. Laptop Dell Latitude 5420"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="categoria">Categoría *</label>
                <input
                  id="categoria"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.categoria}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, categoria: e.target.value })}
                  placeholder="Ej. Cómputo, Multimedia, Laboratorio"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="marca">Marca *</label>
                <input
                  id="marca"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.marca}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, marca: e.target.value })}
                  placeholder="Ej. Dell, Epson, Sony"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="modelo">Modelo *</label>
                <input
                  id="modelo"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.modelo}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, modelo: e.target.value })}
                  placeholder="Ej. Latitude 5420"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="numero_serie">Número de Serie *</label>
                <input
                  id="numero_serie"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.numero_serie}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, numero_serie: e.target.value })}
                  placeholder="Ej. SN-DELL-883921"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="color">Color *</label>
                <input
                  id="color"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.color}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, color: e.target.value })}
                  placeholder="Ej. Gris espacial, Negro"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="estado_fisico">Estado Físico Inicial *</label>
                <input
                  id="estado_fisico"
                  type="text"
                  className="campo__control"
                  required
                  value={nuevoRecurso.estado_fisico}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, estado_fisico: e.target.value })}
                  placeholder="Ej. OPERATIVO, EXCELENTE, NUEVO"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor="foto_url">URL de Fotografía</label>
                <input
                  id="foto_url"
                  type="url"
                  className="campo__control"
                  value={nuevoRecurso.foto_url}
                  onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, foto_url: e.target.value })}
                  placeholder="https://ejemplo.com/foto.jpg"
                />
              </div>
            </div>

            <div className="campo" style={{ marginTop: "1rem" }}>
              <label className="campo__etiqueta" htmlFor="descripcion">Descripción detallada *</label>
              <textarea
                id="descripcion"
                className="campo__control"
                required
                rows={2}
                value={nuevoRecurso.descripcion}
                onChange={(e) => setNuevoRecurso({ ...nuevoRecurso, descripcion: e.target.value })}
                placeholder="Especificaciones o notas relevantes sobre el recurso..."
              />
            </div>

            <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem" }}>
              <button type="submit" className="boton boton--primario" disabled={creando}>
                {creando ? "Guardando..." : "Guardar en Catálogo"}
              </button>
              <button
                type="button"
                className="boton boton--secundario"
                onClick={() => setMostrarModalCrear(false)}
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Buscador */}
      <form onSubmit={handleBuscar} style={{ marginBottom: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="Buscar por nombre, categoría o especificaciones..."
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          className="campo__control"
          style={{ flex: "1 1 300px" }}
        />
        <button type="submit" className="boton boton--primario">
          Buscar
        </button>
        {filtro && (
          <button
            type="button"
            className="boton boton--secundario"
            onClick={() => {
              setFiltro("");
              cargarRecursos("");
            }}
          >
            Limpiar
          </button>
        )}
      </form>

      {loading && (
        <p className="cargando" role="status">
          Cargando catálogo...
        </p>
      )}

      {/* Layout de dos columnas: lista y detalle */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        {/* Columna Izquierda: Lista de Recursos */}
        <div>
          <h2 style={{ fontSize: "1.2rem", marginBottom: "0.75rem" }}>
            Recursos Disponibles ({recursos.length})
          </h2>
          {recursos.length === 0 && !loading && (
            <div className="estado-vacio">
              <p className="estado-vacio__titulo">No se encontraron recursos</p>
              <p>Intenta con otros términos de búsqueda o añade un nuevo recurso.</p>
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {recursos.map((r) => {
              const seleccionado = recursoSeleccionado?.id === r.id;
              return (
                <article
                  key={r.id}
                  onClick={() => handleSeleccionarRecurso(r)}
                  className="tarjeta"
                  style={{
                    cursor: "pointer",
                    border: seleccionado ? "2px solid var(--primario)" : "1px solid var(--borde)",
                    backgroundColor: seleccionado ? "var(--superficie-resaltada, #f8fafc)" : "var(--superficie)",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                    <div>
                      <h3 style={{ fontSize: "1.05rem", margin: "0 0 0.25rem 0" }}>{r.nombre}</h3>
                      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--texto-secundario, #64748b)" }}>
                        {r.categoria}
                      </p>
                    </div>
                    <span className={`insignia ${CLASE_ESTADO[r.estado] || "insignia--neutra"}`}>
                      {r.estado}
                    </span>
                  </div>
                  <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem" }}>{r.descripcion}</p>
                </article>
              );
            })}
          </div>
        </div>

        {/* Columna Derecha: Ficha Técnica y Acciones */}
        <div>
          <h2 style={{ fontSize: "1.2rem", marginBottom: "0.75rem" }}>Detalle y Ficha Técnica</h2>
          {recursoSeleccionado ? (
            <div className="tarjeta" style={{ position: "sticky", top: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.2rem" }}>{recursoSeleccionado.nombre}</h3>
                <span className={`insignia ${CLASE_ESTADO[recursoSeleccionado.estado] || "insignia--neutra"}`}>
                  {recursoSeleccionado.estado}
                </span>
              </div>

              {cargandoFicha ? (
                <p className="cargando">Cargando especificaciones...</p>
              ) : fichaTecnica ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {fichaTecnica.foto_url && (
                    <img
                      src={fichaTecnica.foto_url}
                      alt={fichaTecnica.nombre}
                      style={{ maxHeight: "180px", objectFit: "contain", borderRadius: "4px", backgroundColor: "#fff", padding: "4px" }}
                      onError={(e) => { e.currentTarget.style.display = "none"; }}
                    />
                  )}
                  <div>
                    <strong>Descripción:</strong>
                    <p style={{ margin: "0.25rem 0 0" }}>{fichaTecnica.descripcion}</p>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.9rem" }}>
                    <div><strong>Marca:</strong> {fichaTecnica.marca || "—"}</div>
                    <div><strong>Modelo:</strong> {fichaTecnica.modelo || "—"}</div>
                    <div><strong>Nº Serie:</strong> <code>{fichaTecnica.numero_serie || "—"}</code></div>
                    <div><strong>Color:</strong> {fichaTecnica.color || "—"}</div>
                    <div><strong>Estado físico:</strong> {fichaTecnica.estado_fisico || "—"}</div>
                    <div><strong>Categoría:</strong> {fichaTecnica.categoria || "—"}</div>
                  </div>

                  {/* Acción para usuarios solicitantes: Reservar */}
                  {!esGestion && (
                    <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--borde)" }}>
                      {recursoSeleccionado.estado === "DISPONIBLE" || recursoSeleccionado.estado === "EN_USO" ? (
                        <>
                          <Link
                            to={`/reservas?recursoId=${recursoSeleccionado.id}`}
                            className="boton boton--primario boton--bloque"
                            style={{ textAlign: "center", textDecoration: "none" }}
                          >
                            🗓️ Solicitar Reserva de este Recurso
                          </Link>
                          {recursoSeleccionado.estado === "EN_USO" && (
                            <p style={{ fontSize: "0.85rem", color: "var(--texto-secundario)", marginTop: "0.5rem", marginBottom: 0, textAlign: "center" }}>
                              ℹ️ Este recurso está actualmente en uso, pero se puede reservar para una fecha futura o entrar en lista de espera.
                            </p>
                          )}
                        </>
                      ) : (
                        <div className="alerta alerta--aviso" style={{ fontSize: "0.875rem", margin: 0 }}>
                          Este recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio (Estado: {recursoSeleccionado.estado}).
                        </div>
                      )}
                    </div>
                  )}

                  {/* Acciones de gestión de almacén: cambiar estado */}
                  {esGestion && (
                    <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--borde)" }}>
                      <label className="campo__etiqueta" style={{ marginBottom: "0.5rem" }}>
                        🛠️ Cambiar estado operativo (Gestión):
                      </label>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <select
                          className="campo__control"
                          value={nuevoEstadoSeleccionado}
                          onChange={(e) => setNuevoEstadoSeleccionado(e.target.value)}
                        >
                          <option value="DISPONIBLE">DISPONIBLE</option>
                          <option value="EN_USO">EN_USO</option>
                          <option value="MANTENIMIENTO">MANTENIMIENTO</option>
                          <option value="FUERA_DE_SERVICIO">FUERA_DE_SERVICIO</option>
                        </select>
                        <button
                          type="button"
                          className="boton boton--secundario"
                          disabled={actualizandoEstado || nuevoEstadoSeleccionado === recursoSeleccionado.estado}
                          onClick={handleCambiarEstado}
                        >
                          {actualizandoEstado ? "..." : "Actualizar"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p>No se pudo cargar la información detallada.</p>
              )}
            </div>
          ) : (
            <div className="tarjeta estado-vacio">
              <p className="estado-vacio__titulo">Selecciona un recurso</p>
              <p>Haz clic en cualquier recurso de la lista para ver sus especificaciones técnicas y reservarlo.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
