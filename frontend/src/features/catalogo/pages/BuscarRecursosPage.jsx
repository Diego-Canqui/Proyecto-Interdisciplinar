import { useState, useEffect } from "react";
import { buscarRecursos, consultarDisponibilidad, obtenerFichaTecnica } from "../api.js";

export default function BuscarRecursosPage() {
  const [filtro, setFiltro] = useState("");
  const [recursos, setRecursos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recursoSeleccionado, setRecursoSeleccionado] = useState(null);
  const [disponibilidad, setDisponibilidad] = useState(null);
  const [fichaTecnica, setFichaTecnica] = useState(null);

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
  }, []);

  const handleBuscar = (e) => {
    e.preventDefault();
    cargarRecursos(filtro);
  };

  const handleSeleccionarRecurso = async (recurso) => {
    setRecursoSeleccionado(recurso);
    setDisponibilidad(null);
    setFichaTecnica(null);
    try {
      const dispData = await consultarDisponibilidad(recurso.id);
      setDisponibilidad(dispData.disponible);

      const fichaData = await obtenerFichaTecnica(recurso.id);
      setFichaTecnica(fichaData);
    } catch (err) {
      console.error("Error al obtener detalles del recurso", err);
    }
  };

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: "1000px", margin: "0 auto", padding: "20px" }}>
      <h1>Catálogo de Recursos</h1>
      
      <form onSubmit={handleBuscar} style={{ marginBottom: "20px", display: "flex", gap: "10px" }}>
        <input
          type="text"
          placeholder="Buscar por nombre, descripción o categoría..."
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          style={{ flex: 1, padding: "8px", fontSize: "16px" }}
        />
        <button type="submit" style={{ padding: "8px 16px", fontSize: "16px", cursor: "pointer" }}>
          Buscar
        </button>
      </form>

      {loading && <p>Cargando recursos...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        <div>
          <h2>Lista de Recursos</h2>
          {recursos.length === 0 && !loading && <p>No se encontraron recursos.</p>}
          <ul style={{ listStyle: "none", padding: 0 }}>
            {recursos.map((r) => (
              <li
                key={r.id}
                onClick={() => handleSeleccionarRecurso(r)}
                style={{
                  border: "1px solid #ccc",
                  padding: "12px",
                  marginBottom: "10px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  backgroundColor: recursoSeleccionado?.id === r.id ? "#f0f8ff" : "#fff",
                }}
              >
                <strong>{r.nombre}</strong> ({r.categoria})<br />
                <span style={{ fontSize: "14px", color: "#666" }}>{r.descripcion}</span><br />
                <span style={{ fontSize: "12px", fontWeight: "bold", color: r.estado === "DISPONIBLE" ? "green" : "orange" }}>
                  Estado: {r.estado}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h2>Detalle y Ficha Técnica</h2>
          {recursoSeleccionado ? (
            <div style={{ border: "1px solid #ddd", padding: "16px", borderRadius: "6px", backgroundColor: "#fafafa" }}>
              <h3>{recursoSeleccionado.nombre}</h3>
              <p><strong>Descripción:</strong> {recursoSeleccionado.descripcion}</p>
              <p><strong>Categoría:</strong> {recursoSeleccionado.categoria}</p>
              <p><strong>Disponibilidad actual:</strong> {disponibilidad !== null ? (disponibilidad ? "🟢 Disponible" : "🔴 No disponible") : "Verificando..."}</p>
              
              {fichaTecnica && (
                <div style={{ marginTop: "16px", borderTop: "1px solid #ccc", paddingTop: "12px" }}>
                  <h4>Ficha Técnica</h4>
                  <p><strong>Marca:</strong> {fichaTecnica.marca}</p>
                  <p><strong>Modelo:</strong> {fichaTecnica.modelo}</p>
                  <p><strong>Nº de Serie:</strong> {fichaTecnica.numero_serie}</p>
                  <p><strong>Color:</strong> {fichaTecnica.color}</p>
                  <p><strong>Estado Físico:</strong> {fichaTecnica.estado_fisico}</p>
                  {fichaTecnica.foto_url && (
                    <div>
                      <strong>Foto:</strong><br />
                      <img src={fichaTecnica.foto_url} alt={fichaTecnica.nombre} style={{ maxWidth: "100%", maxHeight: "150px", marginTop: "8px", borderRadius: "4px" }} />
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: "#777" }}>Selecciona un recurso de la lista para ver su ficha técnica.</p>
          )}
        </div>
      </div>
    </div>
  );
}
