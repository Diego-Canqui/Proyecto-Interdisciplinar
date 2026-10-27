import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { buscarRecursos } from "../../catalogo/api.js";
import { listarUsuarios, obtenerPerfil } from "../../identidad/api.js";
import {
  consultarHistorial,
  listarTodosPrestamos,
  registrarDevolucion,
} from "../api.js";

const ROLES_GESTION = ["GESTOR_ALMACEN", "ADMINISTRADOR_SISTEMA"];

const ESTADOS_ACCION_DEVOLUCION = new Set(["ACTIVO", "ENTREGADO", "VENCIDO"]);

const CLASE_ESTADO_PRESTAMO = {
  ACTIVO: "insignia--info",
  ENTREGADO: "insignia--info",
  DEVUELTO: "insignia--exito",
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
    return error.message || "El préstamo no se puede devolver en su estado actual.";
  }
  return error?.message || "Ocurrió un error. Inténtalo de nuevo.";
}

export default function HistorialPage() {
  const [usuario, setUsuario] = useState(null);
  const [prestamos, setPrestamos] = useState([]);
  const [recursos, setRecursos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [devolviendoId, setDevolviendoId] = useState("");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");

  const esGestion = Boolean(usuario?.roles?.some((rol) => ROLES_GESTION.includes(rol)));

  const recursosPorId = useMemo(
    () => new Map(recursos.map((recurso) => [recurso.id, recurso])),
    [recursos]
  );

  const usuariosPorId = useMemo(
    () => new Map(usuarios.map((u) => [u.id, u])),
    [usuarios]
  );

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

  const manejarDevolucion = async (idPrestamo) => {
    setError("");
    setExito("");
    setDevolviendoId(idPrestamo);
    try {
      const res = await registrarDevolucion(idPrestamo);
      if (typeof res?.dias_retraso === "number" && res.dias_retraso > 0) {
        setExito(`Devolución registrada con ${res.dias_retraso} día(s) de retraso.`);
      } else {
        setExito("Devolución registrada a tiempo. El recurso ya está disponible.");
      }
      await cargarListaPrestamos(usuario);
    } catch (errorDevolucion) {
      setError(mensajeError(errorDevolucion));
    } finally {
      setDevolviendoId("");
    }
  };

  if (cargando) {
    return (
      <p className="cargando" role="status">
        Cargando préstamos...
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
            Consulta los préstamos registrados y su estado de devolución.
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
          Historial de préstamos
        </h1>
        <p className="pagina__subtitulo">
          {esGestion
            ? "Gestión global de todos los préstamos registrados en el sistema."
            : "Revisa los préstamos asociados a tus reservas y registra sus devoluciones."}
        </p>
      </header>

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

      {prestamos.length === 0 ? (
        <div className="estado-vacio">
          <p className="estado-vacio__titulo">Todavía no hay préstamos registrados</p>
          <p>No se encontraron préstamos activos ni devueltos en el historial.</p>
          <Link className="boton boton--secundario" to="/reservas">
            Ir a reservas
          </Link>
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
              {prestamos.map((prestamo) => {
                const recurso = recursosPorId.get(prestamo.recurso_id);
                const nombreRecurso = recurso?.nombre || "Recurso del catálogo";
                const usuarioObj = usuariosPorId.get(prestamo.usuario_id);
                const nombreUsuario = usuarioObj
                  ? `${usuarioObj.nombre} (${usuarioObj.correo})`
                  : prestamo.usuario_id;
                const puedeDevolver = ESTADOS_ACCION_DEVOLUCION.has(prestamo.estado);
                const estaDevolviendo = devolviendoId === prestamo.id;

                return (
                  <tr key={prestamo.id}>
                    <td data-etiqueta="Recurso">{nombreRecurso}</td>
                    {esGestion && <td data-etiqueta="Usuario">{nombreUsuario}</td>}
                    <td data-etiqueta="Inicio">{mostrarFecha(prestamo.fecha_inicio)}</td>
                    <td data-etiqueta="Fin">{mostrarFecha(prestamo.fecha_fin)}</td>
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
                      {puedeDevolver ? (
                        <button
                          type="button"
                          className="boton boton--secundario boton--sm"
                          disabled={devolviendoId !== ""}
                          onClick={() => manejarDevolucion(prestamo.id)}
                        >
                          {estaDevolviendo ? "Devolviendo..." : "Devolver"}
                        </button>
                      ) : (
                        <span>Sin acciones</span>
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
  );
}

