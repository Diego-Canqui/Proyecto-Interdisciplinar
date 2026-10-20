import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { obtenerElegibilidad, obtenerPerfilReputacion } from "../api.js";

export default function ReputacionPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [elegibilidad, setElegibilidad] = useState(null);
  const [cargandoElegibilidad, setCargandoElegibilidad] = useState(false);
  const [errorElegibilidad, setErrorElegibilidad] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const cargarPerfil = async () => {
      try {
        const data = await obtenerPerfilReputacion();
        setPerfil(data);
      } catch (err) {
        if (err.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
        } else {
          setError(err.message || "Error al cargar el perfil de reputación");
        }
      } finally {
        setCargando(false);
      }
    };

    cargarPerfil();
  }, [navigate]);

  if (cargando) {
    return (
      <main style={{ maxWidth: "600px", margin: "2rem auto", padding: "1rem" }}>
        <p>Cargando perfil de reputación...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ maxWidth: "600px", margin: "2rem auto", padding: "1rem" }}>
        <div style={{ color: "red" }} role="alert">
          {error}
        </div>
        <button
          onClick={() => navigate("/recursos")}
          style={{
            marginTop: "1rem",
            padding: "0.5rem 1rem",
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Volver al inicio
        </button>
      </main>
    );
  }

  if (!perfil) {
    return (
      <main style={{ maxWidth: "600px", margin: "2rem auto", padding: "1rem" }}>
        <p>No se pudo cargar el perfil.</p>
      </main>
    );
  }

  const sanciones = perfil.sanciones || [];

  const getNivelColor = (nivel) => {
    switch (nivel) {
      case "EXCELENTE":
        return "#28a745";
      case "BUENO":
        return "#17a2b8";
      case "NORMAL":
        return "#ffc107";
      case "BAJO":
        return "#dc3545";
      default:
        return "#6c757d";
    }
  };

  // RF-21: la elegibilidad la calcula el backend; la interfaz solo la muestra
  const consultarElegibilidad = async () => {
    setCargandoElegibilidad(true);
    setErrorElegibilidad("");
    try {
      const data = await obtenerElegibilidad();
      setElegibilidad(data);
    } catch (err) {
      setElegibilidad(null);
      setErrorElegibilidad(err.message || "No se pudo consultar la elegibilidad");
    } finally {
      setCargandoElegibilidad(false);
    }
  };

  return (
    <main style={{ maxWidth: "700px", margin: "2rem auto", padding: "1rem" }}>
      <h1>Mi Perfil de Reputación</h1>

      <div
        style={{
          border: "1px solid #dee2e6",
          borderRadius: "8px",
          padding: "1.5rem",
          marginBottom: "1.5rem",
          backgroundColor: "#f8f9fa",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 style={{ margin: "0 0 0.5rem 0" }}>Puntaje: {perfil.puntaje} / 1000</h2>
            <span
              style={{
                display: "inline-block",
                padding: "0.25rem 0.75rem",
                backgroundColor: getNivelColor(perfil.nivel),
                color: "white",
                borderRadius: "4px",
                fontWeight: "bold",
                textTransform: "uppercase",
                fontSize: "0.875rem",
              }}
            >
              {perfil.nivel}
            </span>
          </div>
          <div style={{ textAlign: "right", color: "#6c757d", fontSize: "0.875rem" }}>
            <div>Actualizado: {new Date(perfil.fecha_actualizacion).toLocaleString()}</div>
          </div>
        </div>
      </div>

      <section style={{ marginBottom: "1.5rem" }}>
        <h2>Historial de sanciones</h2>
        {sanciones.length === 0 ? (
          <p style={{ color: "#28a745" }}>No tienes sanciones registradas. ✓</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0 }}>
            {sanciones.map((sancion) => (
              <li
                key={sancion.id}
                style={{
                  border: "1px solid #dee2e6",
                  borderRadius: "4px",
                  padding: "1rem",
                  marginBottom: "0.75rem",
                  backgroundColor: "#fff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <strong style={{ textTransform: "capitalize" }}>{sancion.tipo.toLowerCase()}</strong>
                    <span
                      style={{
                        padding: "0.15rem 0.5rem",
                        borderRadius: "4px",
                        color: "white",
                        backgroundColor: sancion.vigente ? "#dc3545" : "#6c757d",
                        fontSize: "0.75rem",
                        fontWeight: "bold",
                        textTransform: "uppercase",
                      }}
                    >
                      {sancion.vigente ? "Vigente" : "Expirada"}
                    </span>
                  </span>
                  <span style={{ color: "#dc3545", fontWeight: "bold" }}>
                    {sancion.puntos_descuento > 0 ? `-${sancion.puntos_descuento} pts` : `${sancion.puntos_descuento} pts`}
                  </span>
                </div>
                <div style={{ color: "#6c757d", fontSize: "0.875rem", marginBottom: "0.25rem" }}>
                  {sancion.motivo}
                </div>
                <div style={{ color: "#6c757d", fontSize: "0.75rem" }}>
                  Aplicada: {new Date(sancion.fecha_aplicacion).toLocaleString()}
                </div>
                <div style={{ color: "#6c757d", fontSize: "0.75rem" }}>
                  Fin: {new Date(sancion.fecha_fin).toLocaleString()}
                </div>
                {Number(sancion.monto_descuento) > 0 && (
                  <div style={{ color: "#dc3545", fontSize: "0.875rem", marginTop: "0.25rem" }}>
                    Monto a pagar: ${Number(sancion.monto_descuento).toFixed(2)}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Elegibilidad para préstamo</h2>
        <button
          onClick={consultarElegibilidad}
          disabled={cargandoElegibilidad}
          style={{
            padding: "0.75rem 1.5rem",
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "1rem",
          }}
        >
          {cargandoElegibilidad ? "Consultando..." : "Ver elegibilidad"}
        </button>
        {elegibilidad && (
          <p
            role="status"
            style={{
              marginTop: "1rem",
              color: elegibilidad.elegible ? "#28a745" : "#dc3545",
              fontWeight: "bold",
            }}
          >
            {elegibilidad.elegible
              ? "✅ Eres elegible para realizar préstamos."
              : `❌ No eres elegible para préstamos.${elegibilidad.razon ? ` ${elegibilidad.razon}` : ""}`}
          </p>
        )}
        {errorElegibilidad && (
          <p role="alert" style={{ marginTop: "1rem", color: "red" }}>
            {errorElegibilidad}
          </p>
        )}
      </section>
    </main>
  );
}