const CLASE_ESTADO_PRESTAMO = {
  POR_ENTREGAR: "insignia--aviso",
  ENTREGADO: "insignia--info",
  DEVUELTO: "insignia--exito",
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

function formatearFechaHora(valor) {
  if (!valor) return "—";
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return "—";
  return fecha.toLocaleString(undefined, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Muestra el historial de préstamos de un recurso dentro del panel de detalle.
 * Usa tarjetas compactas para evitar scroll horizontal en el layout Master-Detail.
 */
export function HistorialRecursoPanel({
  prestamos,
  usuariosPorId,
  cargando,
  error,
}) {
  if (cargando) {
    return (
      <p className="cargando" role="status">
        Cargando historial de préstamos...
      </p>
    );
  }

  if (error) {
    return (
      <div className="alerta alerta--error" role="alert">
        {error}
      </div>
    );
  }

  if (!prestamos || prestamos.length === 0) {
    return (
      <div className="estado-vacio" style={{ padding: "1.5rem 1rem" }}>
        <p className="estado-vacio__titulo">Sin préstamos registrados</p>
        <p style={{ margin: 0 }}>Este recurso aún no ha sido prestado.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <p style={{ margin: 0, fontSize: "var(--texto-sm)", color: "var(--texto-suave)" }}>
        {prestamos.length === 1
          ? "1 préstamo registrado"
          : `${prestamos.length} préstamos registrados`}
      </p>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          maxHeight: "480px",
          overflowY: "auto",
          paddingRight: "0.25rem",
        }}
      >
        {prestamos.map((prestamo) => {
          const usuario = usuariosPorId[prestamo.usuario_id];
          const claseEstado =
            CLASE_ESTADO_PRESTAMO[prestamo.estado] || "insignia--neutra";
          const etiquetaEstado =
            ETIQUETA_ESTADO_PRESTAMO[prestamo.estado] || prestamo.estado;

          return (
            <article
              key={prestamo.id}
              style={{
                border: "1px solid var(--borde)",
                borderRadius: "var(--radio-md)",
                padding: "0.75rem",
                backgroundColor: "var(--fondo)",
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "0.5rem",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <p
                    style={{
                      margin: 0,
                      fontWeight: "var(--peso-fuerte)",
                      fontSize: "var(--texto-sm)",
                      color: "var(--texto)",
                    }}
                  >
                    {usuario ? usuario.nombre : prestamo.usuario_id}
                  </p>
                  {usuario?.correo && (
                    <p
                      style={{
                        margin: 0,
                        fontSize: "var(--texto-xs)",
                        color: "var(--texto-suave)",
                        wordBreak: "break-word",
                      }}
                    >
                      {usuario.correo}
                    </p>
                  )}
                </div>
                <span className={`insignia ${claseEstado}`}>{etiquetaEstado}</span>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.4rem 0.75rem",
                  fontSize: "var(--texto-xs)",
                  color: "var(--texto-suave)",
                  paddingTop: "0.4rem",
                  borderTop: "1px solid var(--borde)",
                }}
              >
                <div>
                  <strong style={{ color: "var(--texto)" }}>Inicio:</strong>{" "}
                  {formatearFechaHora(prestamo.fecha_inicio)}
                </div>
                <div>
                  <strong style={{ color: "var(--texto)" }}>Fin:</strong>{" "}
                  {formatearFechaHora(prestamo.fecha_fin)}
                </div>
                <div>
                  <strong style={{ color: "var(--texto)" }}>Entrega real:</strong>{" "}
                  {formatearFechaHora(prestamo.fecha_entrega_real)}
                </div>
                <div>
                  <strong style={{ color: "var(--texto)" }}>Devolución real:</strong>{" "}
                  {formatearFechaHora(prestamo.fecha_devolucion_real)}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
