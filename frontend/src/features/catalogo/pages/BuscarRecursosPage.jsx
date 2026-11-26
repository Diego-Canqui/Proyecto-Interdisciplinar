import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  buscarRecursos,
  obtenerFichaTecnica,
  crearRecurso,
  actualizarRecurso,
  actualizarEstadoRecurso,
} from "../api.js";
import { obtenerPerfil, listarUsuarios } from "../../identidad/api.js";
import { consultarHistorialRecurso } from "../../prestamos/api.js";
import { HistorialRecursoPanel } from "../components/HistorialRecursoPanel.jsx";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];

const CLASE_ESTADO = {
  DISPONIBLE: "insignia--exito",
  EN_USO: "insignia--info",
  MANTENIMIENTO: "insignia--aviso",
  FUERA_DE_SERVICIO: "insignia--error",
};

const CATEGORIAS_SUGERIDAS = ["Cómputo", "Multimedia", "Libro", "Laboratorio"];

const ESPECIFICACIONES_SUGERIDAS = {
  libro: ["Autor", "Editorial", "ISBN", "Edición", "Año"],
  computo: ["Procesador", "RAM", "Almacenamiento"],
  multimedia: ["Resolución / Lente", "Accesorios incluidos"],
  laboratorio: ["Rango / Capacidad", "Calibración", "Accesorios"],
};

const normalizarCategoria = (categoria = "") =>
  categoria
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

const esCategoriaLibro = (categoria = "") => {
  const norm = normalizarCategoria(categoria);
  return norm === "libro" || norm === "libros";
};

const obtenerClavesSugeridas = (categoria = "") => {
  const norm = normalizarCategoria(categoria);
  if (norm === "libro" || norm === "libros" || norm === "bibliografia") {
    return ESPECIFICACIONES_SUGERIDAS.libro;
  }
  if (norm === "computo" || norm === "electronica" || norm === "laptops") {
    return ESPECIFICACIONES_SUGERIDAS.computo;
  }
  if (norm === "multimedia" || norm === "audio y video" || norm === "fotografia") {
    return ESPECIFICACIONES_SUGERIDAS.multimedia;
  }
  if (norm === "laboratorio") {
    return ESPECIFICACIONES_SUGERIDAS.laboratorio;
  }
  return [];
};

const crearEstadoFormularioInicial = () => ({
  nombre: "",
  descripcion: "",
  categoria: "",
  marca: "",
  modelo: "",
  numero_serie: "",
  color: "",
  estado_fisico: "OPERATIVO",
  foto_url: "",
  especificaciones: [],
});

const convertirEspecificacionesALista = (especificacionesObj) =>
  Object.entries(especificacionesObj || {}).map(([clave, valor]) => ({
    clave,
    valor: valor == null ? "" : String(valor),
  }));

const normalizarTextoOpcional = (valor) => {
  const limpio = (valor || "").trim();
  return limpio ? limpio : null;
};

function formatearAvisoEnUso(disponibleDesde) {
  if (!disponibleDesde) {
    return "El recurso está siendo usado. Puedes reservarlo para un horario posterior (quedará pendiente hasta su devolución).";
  }
  const fecha = new Date(disponibleDesde);
  if (Number.isNaN(fecha.getTime())) {
    return "El recurso está siendo usado. Puedes reservarlo para un horario posterior (quedará pendiente hasta su devolución).";
  }
  if (fecha <= new Date()) {
    return "El recurso está siendo usado y tiene una devolución pendiente.";
  }
  const textoFecha = new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(fecha);
  return `El recurso está siendo usado. Disponible aprox. desde el ${textoFecha}.`;
}

const construirPayloadRecurso = (formulario) => {
  const ocultarCamposHardware = esCategoriaLibro(formulario.categoria);
  const especificaciones = {};
  for (const item of formulario.especificaciones || []) {
    const clave = (item.clave || "").trim();
    const valor = (item.valor || "").trim();
    if (clave && valor) {
      especificaciones[clave] = valor;
    }
  }

  return {
    nombre: (formulario.nombre || "").trim(),
    descripcion: (formulario.descripcion || "").trim(),
    categoria: (formulario.categoria || "").trim(),
    marca: ocultarCamposHardware ? null : normalizarTextoOpcional(formulario.marca),
    modelo: ocultarCamposHardware ? null : normalizarTextoOpcional(formulario.modelo),
    numero_serie: ocultarCamposHardware ? null : normalizarTextoOpcional(formulario.numero_serie),
    color: ocultarCamposHardware ? null : normalizarTextoOpcional(formulario.color),
    estado_fisico: (formulario.estado_fisico || "").trim(),
    foto_url: (formulario.foto_url || "").trim(),
    especificaciones,
  };
};

function FormularioRecurso({
  idPrefix,
  titulo,
  valores,
  onChange,
  onSubmit,
  onCancelar,
  guardando,
  textoGuardar,
}) {
  const esLibro = esCategoriaLibro(valores.categoria);
  const clavesSugeridas = obtenerClavesSugeridas(valores.categoria);
  const especificaciones = valores.especificaciones || [];

  const handleCategoriaChange = (nuevaCategoria) => {
    if (esCategoriaLibro(nuevaCategoria)) {
      onChange({
        ...valores,
        categoria: nuevaCategoria,
        marca: "",
        modelo: "",
        numero_serie: "",
        color: "",
      });
    } else {
      onChange({ ...valores, categoria: nuevaCategoria });
    }
  };

  const handleEspecificacionSugeridaChange = (clave, nuevoValor) => {
    const indiceExistente = especificaciones.findIndex((item) => item.clave === clave);
    const siguiente = [...especificaciones];
    if (indiceExistente >= 0) {
      siguiente[indiceExistente] = { clave, valor: nuevoValor };
    } else {
      siguiente.push({ clave, valor: nuevoValor });
    }
    onChange({ ...valores, especificaciones: siguiente });
  };

  const handleAgregarEspecificacion = () => {
    onChange({
      ...valores,
      especificaciones: [...especificaciones, { clave: "", valor: "" }],
    });
  };

  const handleActualizarEspecificacion = (indice, campo, nuevoValor) => {
    const siguiente = especificaciones.map((item, idx) =>
      idx === indice ? { ...item, [campo]: nuevoValor } : item
    );
    onChange({ ...valores, especificaciones: siguiente });
  };

  const handleEliminarEspecificacion = (indice) => {
    onChange({
      ...valores,
      especificaciones: especificaciones.filter((_, idx) => idx !== indice),
    });
  };

  const especificacionesPersonalizadas = especificaciones
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => !clavesSugeridas.includes(item.clave));

  return (
    <div className="tarjeta" style={{ marginBottom: "2rem" }}>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>{titulo}</h2>
      <form onSubmit={onSubmit} className="formulario">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1rem",
          }}
        >
          <div className="campo">
            <label className="campo__etiqueta" htmlFor={`${idPrefix}-nombre`}>
              Nombre del Recurso *
            </label>
            <input
              id={`${idPrefix}-nombre`}
              type="text"
              className="campo__control"
              required
              value={valores.nombre}
              onChange={(e) => onChange({ ...valores, nombre: e.target.value })}
              placeholder="Ej. Laptop Dell Latitude 5420"
            />
          </div>

          <div className="campo">
            <label className="campo__etiqueta" htmlFor={`${idPrefix}-categoria`}>
              Categoría *
            </label>
            <input
              id={`${idPrefix}-categoria`}
              type="text"
              list={`${idPrefix}-categorias-sugeridas`}
              className="campo__control"
              required
              value={valores.categoria}
              onChange={(e) => handleCategoriaChange(e.target.value)}
              placeholder="Ej. Cómputo, Multimedia, Libro, Laboratorio"
            />
            <datalist id={`${idPrefix}-categorias-sugeridas`}>
              {CATEGORIAS_SUGERIDAS.map((cat) => (
                <option key={cat} value={cat} />
              ))}
            </datalist>
          </div>

          {!esLibro && (
            <>
              <div className="campo">
                <label className="campo__etiqueta" htmlFor={`${idPrefix}-marca`}>
                  Marca
                </label>
                <input
                  id={`${idPrefix}-marca`}
                  type="text"
                  className="campo__control"
                  value={valores.marca}
                  onChange={(e) => onChange({ ...valores, marca: e.target.value })}
                  placeholder="Ej. Dell, Epson, Sony"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor={`${idPrefix}-modelo`}>
                  Modelo
                </label>
                <input
                  id={`${idPrefix}-modelo`}
                  type="text"
                  className="campo__control"
                  value={valores.modelo}
                  onChange={(e) => onChange({ ...valores, modelo: e.target.value })}
                  placeholder="Ej. Latitude 5420"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor={`${idPrefix}-numero_serie`}>
                  Número de Serie
                </label>
                <input
                  id={`${idPrefix}-numero_serie`}
                  type="text"
                  className="campo__control"
                  value={valores.numero_serie}
                  onChange={(e) => onChange({ ...valores, numero_serie: e.target.value })}
                  placeholder="Ej. SN-DELL-883921"
                />
              </div>

              <div className="campo">
                <label className="campo__etiqueta" htmlFor={`${idPrefix}-color`}>
                  Color
                </label>
                <input
                  id={`${idPrefix}-color`}
                  type="text"
                  className="campo__control"
                  value={valores.color}
                  onChange={(e) => onChange({ ...valores, color: e.target.value })}
                  placeholder="Ej. Gris espacial, Negro"
                />
              </div>
            </>
          )}

          <div className="campo">
            <label className="campo__etiqueta" htmlFor={`${idPrefix}-estado_fisico`}>
              Estado Físico *
            </label>
            <input
              id={`${idPrefix}-estado_fisico`}
              type="text"
              className="campo__control"
              required
              value={valores.estado_fisico}
              onChange={(e) => onChange({ ...valores, estado_fisico: e.target.value })}
              placeholder="Ej. OPERATIVO, EXCELENTE, NUEVO"
            />
          </div>

          <div className="campo">
            <label className="campo__etiqueta" htmlFor={`${idPrefix}-foto_url`}>
              URL de Fotografía
            </label>
            <input
              id={`${idPrefix}-foto_url`}
              type="url"
              className="campo__control"
              value={valores.foto_url}
              onChange={(e) => onChange({ ...valores, foto_url: e.target.value })}
              placeholder="https://ejemplo.com/foto.jpg"
            />
          </div>
        </div>

        <div className="campo" style={{ marginTop: "1rem" }}>
          <label className="campo__etiqueta" htmlFor={`${idPrefix}-descripcion`}>
            Descripción detallada *
          </label>
          <textarea
            id={`${idPrefix}-descripcion`}
            className="campo__control"
            required
            rows={2}
            value={valores.descripcion}
            onChange={(e) => onChange({ ...valores, descripcion: e.target.value })}
            placeholder="Especificaciones o notas relevantes sobre el recurso..."
          />
        </div>

        {/* Especificaciones sugeridas por categoría y pares clave-valor personalizados */}
        <div
          style={{
            marginTop: "1.25rem",
            paddingTop: "1rem",
            borderTop: "1px solid var(--borde)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "0.5rem",
              marginBottom: "0.75rem",
            }}
          >
            <strong style={{ fontSize: "0.95rem" }}>
              Especificaciones adicionales{valores.categoria ? ` (${valores.categoria})` : ""}
            </strong>
            <button
              type="button"
              className="boton boton--secundario"
              onClick={handleAgregarEspecificacion}
            >
              ＋ Agregar especificación
            </button>
          </div>

          {clavesSugeridas.length > 0 && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "0.75rem",
                marginBottom: especificacionesPersonalizadas.length > 0 ? "1rem" : "0",
              }}
            >
              {clavesSugeridas.map((clave) => {
                const actual = especificaciones.find((item) => item.clave === clave)?.valor || "";
                return (
                  <div className="campo" key={clave}>
                    <label
                      className="campo__etiqueta"
                      htmlFor={`${idPrefix}-esp-${normalizarCategoria(clave)}`}
                    >
                      {clave}
                    </label>
                    <input
                      id={`${idPrefix}-esp-${normalizarCategoria(clave)}`}
                      type="text"
                      className="campo__control"
                      value={actual}
                      onChange={(e) => handleEspecificacionSugeridaChange(clave, e.target.value)}
                      placeholder={`Ingresa ${clave.toLowerCase()}`}
                    />
                  </div>
                );
              })}
            </div>
          )}

          {especificacionesPersonalizadas.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {especificacionesPersonalizadas.map(({ item, index }) => (
                <div
                  key={`${idPrefix}-custom-${index}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr auto",
                    gap: "0.5rem",
                    alignItems: "center",
                  }}
                >
                  <input
                    type="text"
                    className="campo__control"
                    aria-label="Nombre de especificación"
                    placeholder="Campo (ej. Idioma, Peso)"
                    value={item.clave}
                    onChange={(e) =>
                      handleActualizarEspecificacion(index, "clave", e.target.value)
                    }
                  />
                  <input
                    type="text"
                    className="campo__control"
                    aria-label="Valor de especificación"
                    placeholder="Valor"
                    value={item.valor}
                    onChange={(e) =>
                      handleActualizarEspecificacion(index, "valor", e.target.value)
                    }
                  />
                  <button
                    type="button"
                    className="boton boton--secundario"
                    onClick={() => handleEliminarEspecificacion(index)}
                    aria-label="Eliminar especificación"
                    title="Eliminar especificación"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {clavesSugeridas.length === 0 && especificacionesPersonalizadas.length === 0 && (
            <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--texto-secundario, #64748b)" }}>
              No hay especificaciones registradas. Usa &ldquo;＋ Agregar especificación&rdquo; para añadir detalles personalizados.
            </p>
          )}
        </div>

        <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem" }}>
          <button type="submit" className="boton boton--primario" disabled={guardando}>
            {guardando ? "Guardando..." : textoGuardar}
          </button>
          <button type="button" className="boton boton--secundario" onClick={onCancelar}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}

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
  const [editandoRecurso, setEditandoRecurso] = useState(null);
  const [guardandoEdicion, setGuardandoEdicion] = useState(false);

  // Formulario nuevo recurso
  const [nuevoRecurso, setNuevoRecurso] = useState(crearEstadoFormularioInicial);
  const [creando, setCreando] = useState(false);

  // Estado para actualización rápida de estado por gestor
  const [nuevoEstadoSeleccionado, setNuevoEstadoSeleccionado] = useState("");
  const [actualizandoEstado, setActualizandoEstado] = useState(false);

  // Pestaña activa y historial de préstamos del recurso (solo gestión)
  const [pestanaDetalle, setPestanaDetalle] = useState("ficha");
  const [historialRecurso, setHistorialRecurso] = useState([]);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState(null);
  const [usuariosPorId, setUsuariosPorId] = useState({});
  const idPedidoHistorial = useRef(null);
  const formularioEdicionRef = useRef(null);

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
    if (esGestion && pestanaDetalle === "historial") {
      cargarHistorialRecurso(recurso.id);
    }
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
      await crearRecurso(construirPayloadRecurso(nuevoRecurso));
      setExito("Recurso registrado exitosamente en el catálogo.");
      setMostrarModalCrear(false);
      setNuevoRecurso(crearEstadoFormularioInicial());
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

  const abrirModalEdicion = () => {
    const origen = fichaTecnica || recursoSeleccionado;
    if (!origen) return;
    setMostrarModalCrear(false);
    setEditandoRecurso({
      nombre: origen.nombre || "",
      descripcion: origen.descripcion || "",
      categoria: origen.categoria || "",
      marca: origen.marca || "",
      modelo: origen.modelo || "",
      numero_serie: origen.numero_serie || "",
      color: origen.color || "",
      estado_fisico: origen.estado_fisico || "OPERATIVO",
      foto_url: origen.foto_url || "",
      especificaciones: convertirEspecificacionesALista(origen.especificaciones),
    });
    requestAnimationFrame(() => {
      formularioEdicionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const cargarHistorialRecurso = async (idRecurso) => {
    if (!idRecurso || !esGestion) return;
    idPedidoHistorial.current = idRecurso;
    setCargandoHistorial(true);
    setErrorHistorial(null);
    try {
      const yaHayUsuarios = Object.keys(usuariosPorId).length > 0;
      const [prestamos, usuarios] = await Promise.all([
        consultarHistorialRecurso(idRecurso),
        yaHayUsuarios ? Promise.resolve(null) : listarUsuarios().catch(() => []),
      ]);
      if (idPedidoHistorial.current !== idRecurso) return;
      if (Array.isArray(usuarios)) {
        const mapaUsuarios = {};
        usuarios.forEach((u) => {
          mapaUsuarios[u.id] = u;
        });
        setUsuariosPorId(mapaUsuarios);
      }
      setHistorialRecurso(Array.isArray(prestamos) ? prestamos : []);
    } catch (err) {
      if (idPedidoHistorial.current !== idRecurso) return;
      setErrorHistorial(err?.message || "No se pudo cargar el historial de préstamos del recurso.");
      setHistorialRecurso([]);
    } finally {
      if (idPedidoHistorial.current === idRecurso) {
        setCargandoHistorial(false);
      }
    }
  };

  const cambiarPestanaDetalle = (pestana) => {
    setPestanaDetalle(pestana);
    if (pestana === "historial" && recursoSeleccionado && esGestion) {
      cargarHistorialRecurso(recursoSeleccionado.id);
    }
  };

  const handleEditarRecurso = async (e) => {
    e.preventDefault();
    if (!recursoSeleccionado || !editandoRecurso) return;
    setError(null);
    setExito(null);
    setGuardandoEdicion(true);
    try {
      const actualizado = await actualizarRecurso(
        recursoSeleccionado.id,
        construirPayloadRecurso(editandoRecurso)
      );
      setExito("Recurso actualizado correctamente.");
      setEditandoRecurso(null);
      setRecursoSeleccionado(actualizado);
      setFichaTecnica(actualizado);
      await cargarRecursos(filtro);
    } catch (err) {
      setError(err?.message || "Error al actualizar el recurso.");
    } finally {
      setGuardandoEdicion(false);
    }
  };

  const camposFichaInformados = fichaTecnica
    ? [
        { etiqueta: "Marca", valor: fichaTecnica.marca },
        { etiqueta: "Modelo", valor: fichaTecnica.modelo },
        { etiqueta: "Nº Serie", valor: fichaTecnica.numero_serie, esCodigo: true },
        { etiqueta: "Color", valor: fichaTecnica.color },
        { etiqueta: "Estado físico", valor: fichaTecnica.estado_fisico },
        { etiqueta: "Categoría", valor: fichaTecnica.categoria },
      ].filter((campo) => campo.valor != null && String(campo.valor).trim() !== "")
    : [];

  const especificacionesInformadas = fichaTecnica
    ? Object.entries(fichaTecnica.especificaciones || {}).filter(
        ([clave, valor]) =>
          clave.trim() !== "" &&
          valor !== null &&
          valor !== undefined &&
          String(valor).trim() !== ""
      )
    : [];

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
              onClick={() => {
                setEditandoRecurso(null);
                setMostrarModalCrear(!mostrarModalCrear);
              }}
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
        <FormularioRecurso
          idPrefix="crear"
          titulo="Registrar Nuevo Recurso"
          valores={nuevoRecurso}
          onChange={setNuevoRecurso}
          onSubmit={handleCrearRecurso}
          onCancelar={() => setMostrarModalCrear(false)}
          guardando={creando}
          textoGuardar="Guardar en Catálogo"
        />
      )}

      {/* Formulario de edición para Gestor/Administrador */}
      {editandoRecurso && esGestion && recursoSeleccionado && (
        <div ref={formularioEdicionRef}>
          <FormularioRecurso
            idPrefix="editar"
            titulo={`Editar Recurso: ${recursoSeleccionado.nombre}`}
            valores={editandoRecurso}
            onChange={setEditandoRecurso}
            onSubmit={handleEditarRecurso}
            onCancelar={() => setEditandoRecurso(null)}
            guardando={guardandoEdicion}
            textoGuardar="Guardar cambios"
          />
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
                  {r.estado === "EN_USO" && (
                    <p
                      style={{
                        margin: "0.5rem 0 0",
                        fontSize: "0.85rem",
                        color: "var(--primario, #1d4ed8)",
                        fontWeight: 500,
                      }}
                    >
                      ℹ️ {formatearAvisoEnUso(r.disponible_desde)}
                    </p>
                  )}
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.2rem" }}>{recursoSeleccionado.nombre}</h3>
                <span className={`insignia ${CLASE_ESTADO[recursoSeleccionado.estado] || "insignia--neutra"}`}>
                  {recursoSeleccionado.estado}
                </span>
              </div>

              {esGestion && (
                <div
                  className="pestanas"
                  role="tablist"
                  aria-label="Secciones del detalle del recurso"
                  style={{ marginBottom: "1rem" }}
                >
                  <button
                    type="button"
                    role="tab"
                    aria-selected={pestanaDetalle === "ficha"}
                    className={`pestanas__boton ${
                      pestanaDetalle === "ficha" ? "pestanas__boton--activa" : ""
                    }`}
                    onClick={() => cambiarPestanaDetalle("ficha")}
                  >
                    Ficha técnica
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={pestanaDetalle === "historial"}
                    className={`pestanas__boton ${
                      pestanaDetalle === "historial" ? "pestanas__boton--activa" : ""
                    }`}
                    onClick={() => cambiarPestanaDetalle("historial")}
                  >
                    Historial de préstamos
                  </button>
                </div>
              )}

              {esGestion && pestanaDetalle === "historial" ? (
                <HistorialRecursoPanel
                  prestamos={historialRecurso}
                  usuariosPorId={usuariosPorId}
                  cargando={cargandoHistorial}
                  error={errorHistorial}
                />
              ) : cargandoFicha ? (
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
                  {camposFichaInformados.length > 0 && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.9rem" }}>
                      {camposFichaInformados.map((campo) => (
                        <div key={campo.etiqueta}>
                          <strong>{campo.etiqueta}:</strong>{" "}
                          {campo.esCodigo ? <code>{campo.valor}</code> : campo.valor}
                        </div>
                      ))}
                    </div>
                  )}
                  {especificacionesInformadas.length > 0 && (
                    <div>
                      <strong>Especificaciones:</strong>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: "0.5rem",
                          fontSize: "0.9rem",
                          marginTop: "0.35rem",
                        }}
                      >
                        {especificacionesInformadas.map(([clave, valor]) => (
                          <div key={clave}>
                            <strong>{clave}:</strong> {String(valor)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

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
                              ℹ️ {formatearAvisoEnUso(fichaTecnica?.disponible_desde ?? recursoSeleccionado.disponible_desde)}
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

                  {/* Acciones de gestión de almacén: cambiar estado y editar */}
                  {esGestion && (
                    <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--borde)" }}>
                      <label className="campo__etiqueta" style={{ marginBottom: "0.5rem" }}>
                        Estado operativo (Gestión):
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
                      <button
                        type="button"
                        className="boton boton--secundario boton--bloque"
                        style={{ marginTop: "0.75rem" }}
                        onClick={abrirModalEdicion}
                      >
                        Editar datos del recurso
                      </button>
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
