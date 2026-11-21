import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { buscarRecursos } from "../../catalogo/api.js";
import { consultarHistorial, consultarInspeccion } from "../../prestamos/api.js";
import {
  anularExcepcion,
  aplicarSancion,
  descargarCsvMovimientosGlobal,
  descargarCsvMovimientosUsuario,
  ejecutarAmnistia,
  listarUsuarios,
  obtenerMovimientosUsuario,
  obtenerPerfilGestion,
  registrarExcepcion,
} from "../api.js";
import { mensajeDeError, textoDeDetalle } from "../errores.js";

// Roles que pueden solicitar préstamos (se excluyen GESTOR_ALMACEN y ADMINISTRADOR_SISTEMA)
const ROLES_SOLICITANTES = ["ESTUDIANTE", "DOCENTE", "PERSONAL_ADMINISTRATIVO"];

const ETIQUETAS_ROL = {
  ESTUDIANTE: "Estudiante",
  DOCENTE: "Docente",
  PERSONAL_ADMINISTRATIVO: "Personal admin.",
};

// Aviso propio del 403; el resto de códigos muestran el detalle del backend (RF-09)
const MENSAJES_CARGA = {
  403: "No tienes permisos de gestión para consultar la reputación de otros usuarios.",
};

// Mapeo de la guía §9: el color acompaña al texto, nunca es la única señal
const CLASES_NIVEL = {
  BAJO: "insignia--error",
  NORMAL: "insignia--neutra",
  BUENO: "insignia--info",
  EXCELENTE: "insignia--exito",
};

// Estados de excepción derivados en el backend; aquí solo se elige la insignia
const CLASES_ESTADO_EXCEPCION = {
  VIGENTE: "insignia--exito",
  PROGRAMADA: "insignia--info",
  VENCIDA: "insignia--aviso",
  ANULADA: "insignia--neutra",
};

const CLASES_ESTADO_PRESTAMO = {
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

const ETIQUETAS_TIPO_MOVIMIENTO = {
  BONIFICACION_ENTREGA_PUNTUAL: "Entrega puntual",
  BONIFICACION_DEVOLUCION_PUNTUAL: "Devolución puntual",
  SANCION: "Sanción",
  AMNISTIA_MENSUAL: "Amnistía mensual",
  SALDO_INICIAL_HEREDADO: "Saldo previo",
};

/**
 * Formatea una fecha del backend en la zona local del navegador.
 * @param {string|null|undefined} valor - Fecha ISO 8601
 * @returns {string} Fecha y hora legibles en español, o «—» si no hay valor
 */
function formatearFecha(valor) {
  if (!valor) {
    return "—";
  }
  return new Date(valor).toLocaleString();
}

/**
 * Normaliza un texto para el filtro local: sin mayúsculas ni acentos (RF-03).
 * @param {string} texto - Texto a normalizar
 * @returns {string} Texto en minúsculas y sin diacríticos
 */
function normalizar(texto) {
  return String(texto ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/**
 * Panel de gestión de reputación (RF-01, RF-02, RF-03).
 * La ruta se anida bajo el layout, así que la página no monta su propio contenedor
 * principal ni navbar.
 * @returns {JSX.Element} Listado de usuarios con filtro y selección del usuario a gestionar
 */
export default function GestionReputacionPage() {
  const navigate = useNavigate();
  const [usuarios, setUsuarios] = useState([]);
  const [cargandoUsuarios, setCargandoUsuarios] = useState(true);
  const [errorUsuarios, setErrorUsuarios] = useState(null);
  const [filtro, setFiltro] = useState("");
  const [seleccionado, setSeleccionado] = useState(null);
  const [ficha, setFicha] = useState(null);
  const [cargandoFicha, setCargandoFicha] = useState(false);
  const [errorFicha, setErrorFicha] = useState(null);
  // Último usuario pedido: descarta respuestas de selecciones anteriores (RF-04)
  const idPedidoFicha = useRef(null);
  const idPedidoMovimientos = useRef(null);
  const fichaRef = useRef(null);

  // --- Estado de pestañas y del historial de préstamos del alumno (Spec 008, RF-07) ---
  const [pestanaActiva, setPestanaActiva] = useState("reputacion");
  const [prestamosAlumno, setPrestamosAlumno] = useState([]);
  const [recursosCatalogo, setRecursosCatalogo] = useState([]);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState(null);
  const [inspeccionVisualizada, setInspeccionVisualizada] = useState(null);
  const [cargandoInspeccion, setCargandoInspeccion] = useState(false);
  const [errorInspeccion, setErrorInspeccion] = useState(null);

  // --- Estado de la bitácora de movimientos y descarga CSV (Spec 011, RF-06) ---
  const [movimientosAlumno, setMovimientosAlumno] = useState([]);
  const [cargandoMovimientos, setCargandoMovimientos] = useState(false);
  const [errorMovimientos, setErrorMovimientos] = useState(null);
  const [descargandoCsvGlobal, setDescargandoCsvGlobal] = useState(false);
  const [errorCsvGlobal, setErrorCsvGlobal] = useState(null);
  const [descargandoCsvAlumno, setDescargandoCsvAlumno] = useState(false);
  const [errorCsvAlumno, setErrorCsvAlumno] = useState(null);

  const descargarPrestamosCsv = () => {
    if (!seleccionado) {
      return;
    }
    const sanearCsv = (valor) => {
      const texto = valor == null ? "" : String(valor);
      const protegido = /^[=+\-@\t\r]/.test(texto.trimStart()) ? `'${texto}` : texto;
      return `"${protegido.replaceAll('"', '""')}"`;
    };
    const encabezados = [
      "Usuario",
      "Correo",
      "Recurso",
      "Estado",
      "Inicio pactado",
      "Fin pactado",
      "Recogida real",
      "Devolución real",
    ];
    const filas = prestamosAlumno.map((prestamo) => {
      const recurso = recursosPorId.get(prestamo.recurso_id);
      return [
        seleccionado.nombre,
        seleccionado.correo,
        recurso?.nombre || "Recurso del catálogo",
        ETIQUETA_ESTADO_PRESTAMO[prestamo.estado] || prestamo.estado,
        formatearFecha(prestamo.fecha_inicio),
        formatearFecha(prestamo.fecha_fin),
        prestamo.fecha_entrega_real ? formatearFecha(prestamo.fecha_entrega_real) : "Pendiente",
        prestamo.fecha_devolucion_real
          ? formatearFecha(prestamo.fecha_devolucion_real)
          : "Pendiente",
      ]
        .map(sanearCsv)
        .join(",");
    });
    const contenido = `\ufeff${[encabezados.map(sanearCsv).join(","), ...filas].join("\n")}`;
    const blob = new Blob([contenido], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `prestamos_${seleccionado.id}.csv`;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  };

  // --- Estado del formulario de sanción (T7, RF-05, RF-09) ---
  // Tipo de sanción: los cuatro valores posibles del dominio
  const [tipoSancion, setTipoSancion] = useState("TARDANZA");
  const [motivoSancion, setMotivoSancion] = useState("");
  // diasRetardo solo se envía cuando tipo === TARDANZA
  const [diasRetardo, setDiasRetardo] = useState("");
  // montoSancion solo se envía cuando tipo === DANO_TOTAL
  const [montoSancion, setMontoSancion] = useState("");
  const [exitoSancion, setExitoSancion] = useState(null);
  const [errorSancion, setErrorSancion] = useState(null);

  // --- Estado del formulario de excepción (T7, RF-06, RF-09) ---
  const [motivoExcepcion, setMotivoExcepcion] = useState("");
  const [inicioExcepcion, setInicioExcepcion] = useState("");
  const [finExcepcion, setFinExcepcion] = useState("");
  // finInvalido: true cuando fin < inicio (validación local)
  const [finInvalido, setFinInvalido] = useState(false);
  const [exitoExcepcion, setExitoExcepcion] = useState(null);
  const [errorExcepcion, setErrorExcepcion] = useState(null);

  // --- Estado de anulación de excepción (T8, RF-07, RF-09) ---
  // anulacionPendiente: id de la excepción con confirmación abierta en la misma celda
  const [anulacionPendiente, setAnulacionPendiente] = useState(null);
  const [exitoAnulacion, setExitoAnulacion] = useState(null);
  const [errorAnulacion, setErrorAnulacion] = useState(null);

  // --- Estado de amnistía mensual (T8, RF-08, RF-09) ---
  // amnistiaPendiente: true cuando el primer clic pide confirmación en la misma sección
  const [amnistiaPendiente, setAmnistiaPendiente] = useState(false);
  const [resultadoAmnistia, setResultadoAmnistia] = useState(null);
  const [errorAmnistia, setErrorAmnistia] = useState(null);

  // enCurso: "sancion" | "excepcion" | "anular" | "amnistia" | null — impide dobles envíos (RF-09)
  const [enCurso, setEnCurso] = useState(null);

  const cargarUsuarios = useCallback(async () => {
    setCargandoUsuarios(true);
    setErrorUsuarios(null);
    try {
      const datos = await listarUsuarios();
      setUsuarios(Array.isArray(datos) ? datos : []);
    } catch (err) {
      // 401: la sesión ya no vale → descartar el token y volver al login (RF-09)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos, sin tabla ni selección (RF-01, RF-09)
      if (err.status === 403) {
        setErrorUsuarios({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      // Red o 5xx: alerta con acción para reintentar (RF-09)
      setErrorUsuarios({ texto: mensajeDeError(err), reintentable: true });
    } finally {
      setCargandoUsuarios(false);
    }
  }, [navigate]);

  useEffect(() => {
    cargarUsuarios();
  }, [cargarUsuarios]);

  /**
   * Consulta la ficha de reputación de un usuario (RF-04).
   * Es también el punto de recarga que usarán las acciones de T7 y T8.
   * @param {string} usuarioId - UUID del usuario consultado
   */
  const cargarFicha = useCallback(
    async (usuarioId) => {
      idPedidoFicha.current = usuarioId;
      setErrorFicha(null);
      // Al cambiar de usuario se oculta la ficha anterior; al recargar el mismo se conserva
      setFicha((actual) => (actual?.usuario_id === usuarioId ? actual : null));
      setCargandoFicha(true);
      try {
        const datos = await obtenerPerfilGestion(usuarioId);
        // Ignorar la respuesta si ya se seleccionó otro usuario
        if (idPedidoFicha.current !== usuarioId) {
          return;
        }
        setFicha(datos);
      } catch (err) {
        if (idPedidoFicha.current !== usuarioId) {
          return;
        }
        // 401: la sesión ya no vale → descartar el token y volver al login (RF-09)
        if (err.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }
        // 403: aviso de permisos (RF-01, RF-09)
        if (err.status === 403) {
          setErrorFicha({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
          return;
        }
        // 404: el usuario ya no existe → mensaje del backend y recarga de la lista
        if (err.status === 404) {
          setFicha(null);
          setErrorFicha({ texto: mensajeDeError(err), noEncontrado: true });
          return;
        }
        // Red o 5xx: alerta reintentable (RF-09)
        setFicha(null);
        setErrorFicha({ texto: mensajeDeError(err), reintentable: true });
      } finally {
        if (idPedidoFicha.current === usuarioId) {
          setCargandoFicha(false);
        }
      }
    },
    [navigate]
  );

  const cargarHistorialAlumno = useCallback(
    async (usuarioId) => {
      setCargandoHistorial(true);
      setErrorHistorial(null);
      setInspeccionVisualizada(null);
      setErrorInspeccion(null);
      try {
        const [listaPrestamos, listaRecursos] = await Promise.all([
          consultarHistorial(usuarioId),
          recursosCatalogo.length > 0 ? Promise.resolve(recursosCatalogo) : buscarRecursos(),
        ]);
        if (idPedidoFicha.current !== usuarioId) {
          return;
        }
        setPrestamosAlumno(Array.isArray(listaPrestamos) ? listaPrestamos : []);
        if (recursosCatalogo.length === 0 && Array.isArray(listaRecursos)) {
          setRecursosCatalogo(listaRecursos);
        }
      } catch (err) {
        if (idPedidoFicha.current !== usuarioId) {
          return;
        }
        if (err.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }
        setPrestamosAlumno([]);
        setErrorHistorial(mensajeDeError(err));
      } finally {
        if (idPedidoFicha.current === usuarioId) {
          setCargandoHistorial(false);
        }
      }
    },
    [navigate, recursosCatalogo]
  );

  const procesarErrorBitacora = useCallback(
    (err, setErrorEstado) => {
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      if (err.status === 403) {
        setErrorEstado({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      if (err.status === 404) {
        setErrorEstado({ texto: mensajeDeError(err), noEncontrado: true });
        return;
      }
      setErrorEstado({
        texto: mensajeDeError(err),
        reintentable: err.status === undefined || err.status >= 500,
      });
    },
    [navigate]
  );

  const cargarMovimientosAlumno = useCallback(
    async (usuarioId) => {
      idPedidoMovimientos.current = usuarioId;
      setCargandoMovimientos(true);
      setErrorMovimientos(null);
      try {
        const datos = await obtenerMovimientosUsuario(usuarioId);
        if (idPedidoMovimientos.current !== usuarioId) {
          return;
        }
        setMovimientosAlumno(Array.isArray(datos) ? datos : []);
      } catch (err) {
        if (idPedidoMovimientos.current !== usuarioId) {
          return;
        }
        setMovimientosAlumno([]);
        procesarErrorBitacora(err, setErrorMovimientos);
      } finally {
        if (idPedidoMovimientos.current === usuarioId) {
          setCargandoMovimientos(false);
        }
      }
    },
    [procesarErrorBitacora]
  );

  // Cargar la ficha al seleccionar un usuario y al cambiar de selección (RF-03, RF-04)
  useEffect(() => {
    if (!seleccionado) {
      idPedidoFicha.current = null;
      setFicha(null);
      setErrorFicha(null);
      setCargandoFicha(false);
      setPrestamosAlumno([]);
      setErrorHistorial(null);
      setInspeccionVisualizada(null);
      setErrorInspeccion(null);
      return;
    }
    cargarFicha(seleccionado.id);
    cargarHistorialAlumno(seleccionado.id);
  }, [seleccionado, cargarFicha, cargarHistorialAlumno]);

  // Cargar bitácora de movimientos por separado para no romper la ficha si falla (Spec 011)
  useEffect(() => {
    if (!seleccionado) {
      idPedidoMovimientos.current = null;
      setMovimientosAlumno([]);
      setErrorMovimientos(null);
      setCargandoMovimientos(false);
      setErrorCsvAlumno(null);
      return;
    }
    cargarMovimientosAlumno(seleccionado.id);
  }, [seleccionado, cargarMovimientosAlumno]);

  const recursosPorId = useMemo(
    () => new Map(recursosCatalogo.map((r) => [r.id, r])),
    [recursosCatalogo]
  );

  const verInspeccionAlumno = async (idPrestamo) => {
    setCargandoInspeccion(true);
    setErrorInspeccion(null);
    setInspeccionVisualizada(null);
    try {
      const data = await consultarInspeccion(idPrestamo);
      setInspeccionVisualizada(data);
    } catch (err) {
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      setErrorInspeccion(mensajeDeError(err));
    } finally {
      setCargandoInspeccion(false);
    }
  };

  // Filtro local: solo solicitantes (ESTUDIANTE, DOCENTE, PERSONAL_ADMINISTRATIVO)
  const usuariosSolicitantes = usuarios.filter((usuario) =>
    (usuario.roles || []).some((rol) => ROLES_SOLICITANTES.includes(rol))
  );
  const textoFiltro = normalizar(filtro);
  const usuariosFiltrados = usuariosSolicitantes.filter(
    (usuario) =>
      normalizar(usuario.nombre).includes(textoFiltro) ||
      normalizar(usuario.correo).includes(textoFiltro)
  );

  const seleccionar = (usuario) => {
    setSeleccionado(usuario);
    // Cambiar de selección limpia mensajes y vuelve a cargar la ficha (RF-03, RF-04)
    setErrorFicha(null);
    setErrorMovimientos(null);
    setErrorCsvAlumno(null);
    setExitoSancion(null);
    setErrorSancion(null);
    setExitoExcepcion(null);
    setErrorExcepcion(null);
    setAnulacionPendiente(null);
    setExitoAnulacion(null);
    setErrorAnulacion(null);
    if (window.innerWidth < 900) {
      fichaRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const descargarCsvGlobal = async () => {
    if (descargandoCsvGlobal) {
      return;
    }
    setDescargandoCsvGlobal(true);
    setErrorCsvGlobal(null);
    try {
      await descargarCsvMovimientosGlobal();
    } catch (err) {
      procesarErrorBitacora(err, setErrorCsvGlobal);
    } finally {
      setDescargandoCsvGlobal(false);
    }
  };

  const descargarCsvAlumno = async (usuarioId) => {
    if (descargandoCsvAlumno || !usuarioId) {
      return;
    }
    setDescargandoCsvAlumno(true);
    setErrorCsvAlumno(null);
    try {
      await descargarCsvMovimientosUsuario(usuarioId);
    } catch (err) {
      procesarErrorBitacora(err, setErrorCsvAlumno);
    } finally {
      setDescargandoCsvAlumno(false);
    }
  };

  const sanciones = ficha?.sanciones ?? [];
  const excepciones = ficha?.excepciones ?? [];
  // La deuda solo se muestra cuando alguna sanción la tiene (RF-04)
  const hayMonto = sanciones.some((sancion) => Number(sancion.monto_descuento) > 0);
  // Aviso informativo: una excepción con inicio futuro aún no cubre nada (RF-06)
  const excepcionesProgramadas = excepciones.filter(
    (excepcion) => excepcion.estado === "PROGRAMADA"
  );

  // Recarga la lista y descarta la selección cuando el usuario consultado ya no existe
  const recargarUsuariosYLimpiar = () => {
    setSeleccionado(null);
    cargarUsuarios();
  };

  /**
   * Manejador de errores compartido para los formularios de sanción y excepción (RF-09).
   * Devuelve el objeto de error que el formulario debe guardar en su estado.
   * @param {Error} err - Error lanzado por el apiClient
   * @param {"sancion"|"excepcion"} tipo - Formulario que originó el error
   * @returns {{ texto: string, permisos?: boolean, noEncontrado?: boolean, reintentable?: boolean }}
   */
  function procesarErrorFormulario(err, tipo) {
    // 401: sesión expirada → descartar token y redirigir al login (RF-09)
    if (err.status === 401) {
      localStorage.removeItem("token");
      navigate("/login");
      return null;
    }
    // 422: detalle de validación del backend (lista normalizada por textoDeDetalle)
    if (err.status === 422) {
      return { texto: textoDeDetalle(err.detail) || mensajeDeError(err) };
    }
    // 403: aviso de permisos
    if (err.status === 403) {
      return { texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true };
    }
    // 404: mensaje del backend + recarga del listado de usuarios
    if (err.status === 404) {
      return { texto: mensajeDeError(err), noEncontrado: true };
    }
    // Red o 5xx: reintentable
    return { texto: mensajeDeError(err), reintentable: true };
    void tipo; // suprimir aviso de parámetro no usado
  }

  /**
   * Envía el formulario de sanción al backend (RF-05, RF-09).
   * Los campos condicionales que no aplican al tipo seleccionado no viajan en la petición.
   * @param {React.FormEvent} e - Evento de envío del formulario
   */
  const enviarSancion = async (e) => {
    e.preventDefault();
    if (enCurso || !seleccionado) {
      return;
    }
    setEnCurso("sancion");
    setExitoSancion(null);
    setErrorSancion(null);
    try {
      // Solo se envía el campo que corresponde al tipo seleccionado (RF-05)
      const diasNum = tipoSancion === "TARDANZA" && diasRetardo !== "" ? Number(diasRetardo) : null;
      const montoNum =
        tipoSancion === "DANO_TOTAL" && montoSancion !== "" ? Number(montoSancion) : null;
      const resultado = await aplicarSancion(
        seleccionado.id,
        tipoSancion,
        motivoSancion,
        montoNum,
        diasNum
      );
      // Éxito: mostrar tipo, puntos descontados y fecha de fin devueltos por el backend
      setExitoSancion(
        `Sanción «${resultado.tipo}» aplicada: ${resultado.puntos_descuento} punto(s) descontado(s). ` +
          `Vigente hasta ${formatearFecha(resultado.fecha_fin)}.`
      );
      // Limpiar motivo e importes (el tipo se conserva para mayor comodidad)
      setMotivoSancion("");
      setDiasRetardo("");
      setMontoSancion("");
      // Recargar la ficha y la bitácora para reflejar el nuevo puntaje (RF-05, Spec 011)
      await Promise.all([
        cargarFicha(seleccionado.id),
        cargarMovimientosAlumno(seleccionado.id),
      ]);
    } catch (err) {
      const error = procesarErrorFormulario(err, "sancion");
      if (error !== null) {
        setErrorSancion(error);
        // 404: el usuario desapareció → recargar lista
        if (error.noEncontrado) {
          recargarUsuariosYLimpiar();
        }
      }
    } finally {
      setEnCurso(null);
    }
  };

  /**
   * Envía el formulario de excepción académica al backend (RF-06, RF-09).
   * Convierte las fechas locales a UTC antes de enviar y valida que fin >= inicio.
   * @param {React.FormEvent} e - Evento de envío del formulario
   */
  const enviarExcepcion = async (e) => {
    e.preventDefault();
    if (enCurso || !seleccionado) {
      return;
    }
    // Validación local: fechas obligatorias válidas y fin >= inicio
    if (!inicioExcepcion || !finExcepcion) {
      setErrorExcepcion({
        texto: "Completa las fechas de inicio y fin para registrar la excepción.",
        reintentable: false,
      });
      return;
    }
    const inicioMs = new Date(inicioExcepcion).getTime();
    const finMs = new Date(finExcepcion).getTime();
    if (Number.isNaN(inicioMs) || Number.isNaN(finMs)) {
      setErrorExcepcion({
        texto: "Las fechas ingresadas no son válidas.",
        reintentable: false,
      });
      return;
    }
    if (finMs < inicioMs) {
      setFinInvalido(true);
      return;
    }
    setFinInvalido(false);
    setEnCurso("excepcion");
    setExitoExcepcion(null);
    setErrorExcepcion(null);
    try {
      // Convertir a UTC antes de enviar (RF-06)
      const inicioUtc = new Date(inicioExcepcion).toISOString();
      const finUtc = new Date(finExcepcion).toISOString();
      const resultado = await registrarExcepcion(
        seleccionado.id,
        motivoExcepcion,
        inicioUtc,
        finUtc
      );
      // Éxito: informar el rango registrado
      let mensajeExito =
        `Excepción registrada: del ${formatearFecha(resultado.fecha_inicio)} ` +
        `al ${formatearFecha(resultado.fecha_fin)}.`;
      // Aviso adicional si la excepción empieza en el futuro (todavía no cubre nada)
      if (new Date(resultado.fecha_inicio) > new Date()) {
        mensajeExito +=
          ` Programada: cubrirá desde ${formatearFecha(resultado.fecha_inicio)}.`;
      }
      setExitoExcepcion(mensajeExito);
      // Limpiar el formulario
      setMotivoExcepcion("");
      setInicioExcepcion("");
      setFinExcepcion("");
      // Recargar la ficha para reflejar la nueva excepción (RF-06)
      await cargarFicha(seleccionado.id);
    } catch (err) {
      const error = procesarErrorFormulario(err, "excepcion");
      if (error !== null) {
        setErrorExcepcion(error);
        if (error.noEncontrado) {
          recargarUsuariosYLimpiar();
        }
      }
    } finally {
      setEnCurso(null);
    }
  };

  /**
   * Abre la confirmación inline para anular una excepción en la misma celda (RF-07).
   * @param {string} id - UUID de la excepción académica
   */
  const pedirAnulacion = (id) => {
    setAnulacionPendiente(id);
    setExitoAnulacion(null);
    setErrorAnulacion(null);
  };

  /**
   * Cancela la anulación inline sin llamar al backend (RF-07).
   */
  const cancelarAnulacion = () => {
    setAnulacionPendiente(null);
  };

  /**
   * Confirma y ejecuta la anulación de la excepción académica (RF-07, RF-09).
   * Deshabilita mientras enCurso === "anular". Recarga la ficha para mostrar estado ANULADA.
   * @param {string} excepcionId - UUID de la excepción a anular
   */
  const confirmarAnulacion = async (excepcionId) => {
    if (enCurso || !seleccionado) {
      return;
    }
    setEnCurso("anular");
    setExitoAnulacion(null);
    setErrorAnulacion(null);
    try {
      await anularExcepcion(excepcionId);
      setAnulacionPendiente(null);
      setExitoAnulacion("Excepción académica anulada correctamente.");
      // Recargar la ficha para mostrar la excepción en estado ANULADA devuelta por el backend (RF-07)
      await cargarFicha(seleccionado.id);
    } catch (err) {
      setAnulacionPendiente(null);
      // 401: sesión expirada → descartar token y navegar al login (RF-09)
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos
      if (err.status === 403) {
        setErrorAnulacion({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      // 404: no encontrada → mensaje + recarga de la ficha (RF-07, RF-09)
      if (err.status === 404) {
        setErrorAnulacion({ texto: mensajeDeError(err), noEncontrado: true });
        if (seleccionado) {
          await cargarFicha(seleccionado.id);
        }
        return;
      }
      // Red o 5xx: error reintentable
      setErrorAnulacion({ texto: mensajeDeError(err), reintentable: true });
    } finally {
      setEnCurso(null);
    }
  };

  /**
   * Abre la confirmación en dos pasos para la amnistía global (RF-08).
   */
  const pedirAmnistia = () => {
    setAmnistiaPendiente(true);
    setResultadoAmnistia(null);
    setErrorAmnistia(null);
  };

  /**
   * Cancela la ejecución de la amnistía sin llamar al backend (RF-08).
   */
  const cancelarAmnistia = () => {
    setAmnistiaPendiente(false);
  };

  /**
   * Confirma y ejecuta la amnistía mensual global (RF-08, RF-09).
   * Deshabilita mientras enCurso === "amnistia". Trata N = 0 como resultado informativo válido.
   */
  const confirmarAmnistia = async () => {
    if (enCurso) {
      return;
    }
    setEnCurso("amnistia");
    setResultadoAmnistia(null);
    setErrorAmnistia(null);
    try {
      const res = await ejecutarAmnistia();
      setAmnistiaPendiente(false);
      const n = Number(res?.perfiles_premiados ?? 0);
      if (n > 0) {
        setResultadoAmnistia({
          tipo: "exito",
          texto: n === 1 ? "1 perfil premiado" : `${n} perfiles premiados`,
        });
      } else {
        // N = 0 es un resultado informativo válido, no un error (RF-08)
        setResultadoAmnistia({
          tipo: "info",
          texto: "Ningún perfil resultó elegible",
        });
      }
      // Si hay un usuario seleccionado, recargar su ficha y bitácora para reflejar posibles cambios (RF-08, Spec 011)
      if (seleccionado) {
        await Promise.all([
          cargarFicha(seleccionado.id),
          cargarMovimientosAlumno(seleccionado.id),
        ]);
      }
    } catch (err) {
      setAmnistiaPendiente(false);
      // 401: sesión expirada → login
      if (err.status === 401) {
        localStorage.removeItem("token");
        navigate("/login");
        return;
      }
      // 403: aviso de permisos
      if (err.status === 403) {
        setErrorAmnistia({ texto: mensajeDeError(err, MENSAJES_CARGA), permisos: true });
        return;
      }
      // Red o 5xx: error reintentable
      setErrorAmnistia({ texto: mensajeDeError(err), reintentable: true });
    } finally {
      setEnCurso(null);
    }
  };

  return (
    <div>
      <header className="pagina__cabecera">
        <div className="formulario">
          <div>
            <h1 className="pagina__titulo">Alumnos y gestión de reputación</h1>
            <p className="pagina__subtitulo">
              Elige un alumno para consultar su reputación, gestionar sanciones y excepciones, y
              revisar su historial de préstamos.
            </p>
          </div>
          {!errorUsuarios?.permisos && (
            <div className="formulario__acciones">
              <button
                type="button"
                className="boton boton--secundario"
                onClick={descargarCsvGlobal}
                disabled={descargandoCsvGlobal}
              >
                {descargandoCsvGlobal
                  ? "Descargando historial..."
                  : "Descargar historial general (CSV)"}
              </button>
            </div>
          )}
          {errorCsvGlobal && (
            <div className="alerta alerta--error" role="alert">
              <span>{errorCsvGlobal.texto}</span>
              {errorCsvGlobal.reintentable && (
                <button
                  type="button"
                  className="boton boton--secundario boton--sm"
                  onClick={descargarCsvGlobal}
                >
                  Reintentar
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {errorUsuarios?.permisos ? (
        <div className="alerta alerta--error" role="alert">
          {errorUsuarios.texto}
        </div>
      ) : (
        <div className="formulario">
          <div className="maestro-detalle">
            <section className="tarjeta maestro-detalle__lista">
              <div className="tarjeta__cabecera">
                Solicitantes ({usuariosSolicitantes.length})
              </div>
              <div className="tarjeta__cuerpo">
                {cargandoUsuarios ? (
                  <p className="cargando" role="status">
                    Cargando usuarios...
                  </p>
                ) : errorUsuarios ? (
                  <div className="alerta alerta--error" role="alert">
                    <span>{errorUsuarios.texto}</span>
                    {errorUsuarios.reintentable && (
                      <button
                        type="button"
                        className="boton boton--secundario boton--sm"
                        onClick={cargarUsuarios}
                      >
                        Reintentar
                      </button>
                    )}
                  </div>
                ) : usuariosSolicitantes.length === 0 ? (
                  <div className="estado-vacio">
                    <p className="estado-vacio__titulo">No hay solicitantes registrados</p>
                    <p>Todavía no hay estudiantes, docentes o personal administrativo.</p>
                  </div>
                ) : (
                  <div className="formulario">
                    <div className="campo">
                      <label className="campo__etiqueta" htmlFor="filtro-usuarios">
                        Filtrar por nombre o correo
                      </label>
                      <input
                        className="campo__control"
                        id="filtro-usuarios"
                        type="search"
                        value={filtro}
                        onChange={(e) => setFiltro(e.target.value)}
                        placeholder="Escribe un nombre o un correo"
                      />
                    </div>

                    {usuariosFiltrados.length === 0 ? (
                      <div className="estado-vacio">
                        <p className="estado-vacio__titulo">Ningún solicitante coincide</p>
                        <p>Prueba con otro nombre o correo.</p>
                      </div>
                    ) : (
                      <div className="maestro-detalle__scroll">
                        <div className="lista-seleccion" role="list" aria-label="Lista de solicitantes">
                          {usuariosFiltrados.map((usuario) => {
                            const esSeleccionado = seleccionado?.id === usuario.id;
                            const rolVisible = (usuario.roles || [])
                              .filter((rol) => ROLES_SOLICITANTES.includes(rol))
                              .map((rol) => ETIQUETAS_ROL[rol] || rol)
                              .join(", ");
                            return (
                              <button
                                key={usuario.id}
                                type="button"
                                role="listitem"
                                className={`lista-seleccion__item ${
                                  esSeleccionado ? "lista-seleccion__item--activo" : ""
                                }`}
                                onClick={() => seleccionar(usuario)}
                                aria-pressed={esSeleccionado}
                              >
                                <span className="lista-seleccion__meta">
                                  <span className="lista-seleccion__nombre">{usuario.nombre}</span>
                                  <span className="lista-seleccion__sub">{usuario.correo}</span>
                                </span>
                                <span
                                  className={`insignia ${
                                    esSeleccionado ? "insignia--info" : "insignia--neutra"
                                  }`}
                                >
                                  {esSeleccionado ? "Seleccionado" : rolVisible}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>

            <div className="maestro-detalle__contenido" ref={fichaRef}>
              <section className="tarjeta">
                <div className="tarjeta__cabecera">Ficha del usuario</div>
            <div className="tarjeta__cuerpo">
              {/* Sin usuario seleccionado */}
              {!seleccionado && (
                <div className="estado-vacio">
                  <p className="estado-vacio__titulo">Sin usuario seleccionado</p>
                  <p>Selecciona un usuario en la lista para ver su ficha.</p>
                </div>
              )}

              {/* Usuario seleccionado: pestañas de Reputación e Historial de Préstamos */}
              {seleccionado && (
                <>
                  <p>
                    Alumno seleccionado: <strong>{seleccionado.nombre}</strong> (
                    {seleccionado.correo}).
                  </p>

                  <div
                    className="pestanas"
                    role="tablist"
                    aria-label="Secciones de la ficha del alumno"
                  >
                    <button
                      type="button"
                      role="tab"
                      aria-selected={pestanaActiva === "reputacion"}
                      className={`pestanas__boton ${
                        pestanaActiva === "reputacion" ? "pestanas__boton--activa" : ""
                      }`}
                      onClick={() => setPestanaActiva("reputacion")}
                    >
                      Reputación y Sanciones
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={pestanaActiva === "historial"}
                      className={`pestanas__boton ${
                        pestanaActiva === "historial" ? "pestanas__boton--activa" : ""
                      }`}
                      onClick={() => setPestanaActiva("historial")}
                    >
                      <span>Historial de Préstamos</span>
                      <span className="pestanas__contador">{prestamosAlumno.length}</span>
                    </button>
                  </div>

                  {pestanaActiva === "reputacion" && (
                    <>
                      {/* Cargando la ficha */}
                      {cargandoFicha && (
                    <p className="cargando" role="status">
                      Cargando ficha de reputación...
                    </p>
                  )}

                  {/* Error 403: aviso de permisos (RF-09) */}
                  {!cargandoFicha && errorFicha?.permisos && (
                    <div className="alerta alerta--error" role="alert">
                      {errorFicha.texto}
                    </div>
                  )}

                  {/* Error 404: usuario no encontrado → mensaje + botón para recargar (RF-09) */}
                  {!cargandoFicha && errorFicha?.noEncontrado && (
                    <div className="alerta alerta--error" role="alert">
                      <span>{errorFicha.texto}</span>{" "}
                      <button
                        type="button"
                        className="boton boton--secundario boton--sm"
                        onClick={recargarUsuariosYLimpiar}
                      >
                        Recargar usuarios
                      </button>
                    </div>
                  )}

                  {/* Error de red / 5xx: alerta reintentable (RF-09) */}
                  {!cargandoFicha && errorFicha?.reintentable && (
                    <div className="alerta alerta--error" role="alert">
                      <span>{errorFicha.texto}</span>{" "}
                      <button
                        type="button"
                        className="boton boton--secundario boton--sm"
                        onClick={() => cargarFicha(seleccionado.id)}
                      >
                        Reintentar
                      </button>
                    </div>
                  )}

                  {/* Ficha de reputación: puntaje, nivel y fecha de actualización (RF-04, §9) */}
                  {!cargandoFicha && !errorFicha && ficha && (
                    <>
                      <div className="tarjeta__contenido">
                        <p>
                          <strong>Puntaje:</strong> {ficha.puntaje} / 1000
                        </p>
                        <p>
                          <strong>Nivel:</strong>{" "}
                          <span
                            className={`insignia ${CLASES_NIVEL[ficha.nivel] ?? "insignia--neutra"}`}
                          >
                            {ficha.nivel}
                          </span>
                        </p>
                        <p>
                          <strong>Última actualización:</strong>{" "}
                          {ficha.fecha_actualizacion
                            ? formatearFecha(ficha.fecha_actualizacion)
                            : "Sin perfil todavía"}
                        </p>
                      </div>

                      {/* Tabla de sanciones (RF-04): tipo, motivo, puntos, monto si >0, fechas y estado */}
                      <h3 className="tarjeta__titulo">Sanciones</h3>
                      {sanciones.length === 0 ? (
                        <p className="estado-vacio">Sin sanciones registradas.</p>
                      ) : (
                        <div className="tabla__contenedor">
                          <table className="tabla tabla--apilada">
                            <thead>
                              <tr>
                                <th scope="col">Tipo</th>
                                <th scope="col">Motivo</th>
                                <th scope="col">Puntos</th>
                                {hayMonto && <th scope="col">Monto ($)</th>}
                                <th scope="col">Fecha aplicación</th>
                                <th scope="col">Fecha fin</th>
                                <th scope="col">Estado</th>
                              </tr>
                            </thead>
                            <tbody>
                              {sanciones.map((sancion) => (
                                <tr key={sancion.id}>
                                  <td data-etiqueta="Tipo">{sancion.tipo}</td>
                                  <td data-etiqueta="Motivo">{sancion.motivo}</td>
                                  <td data-etiqueta="Puntos">{sancion.puntos_descuento}</td>
                                  {hayMonto && (
                                    <td data-etiqueta="Monto ($)">
                                      {Number(sancion.monto_descuento) > 0
                                        ? sancion.monto_descuento
                                        : "—"}
                                    </td>
                                  )}
                                  <td data-etiqueta="Fecha aplicación">
                                    {formatearFecha(sancion.fecha_aplicacion)}
                                  </td>
                                  <td data-etiqueta="Fecha fin">
                                    {formatearFecha(sancion.fecha_fin)}
                                  </td>
                                  <td data-etiqueta="Estado">
                                    {sancion.vigente ? (
                                      <span className="insignia insignia--error">Vigente</span>
                                    ) : (
                                      <span className="insignia insignia--neutra">Expirada</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Tabla de excepciones (RF-04): motivo, inicio, fin, estado (texto + insignia), acciones (RF-07) */}
                      <h3 className="tarjeta__titulo">Excepciones académicas</h3>
                      {/* Aviso informativo: las excepciones programadas aún no cubren nada (RF-06) */}
                      {excepcionesProgramadas.length > 0 && (
                        <div className="alerta alerta--aviso" role="status">
                          {excepcionesProgramadas.length === 1
                            ? "Hay 1 excepción programada que todavía no está en vigor."
                            : `Hay ${excepcionesProgramadas.length} excepciones programadas que todavía no están en vigor.`}
                        </div>
                      )}
                      {/* Mensaje de éxito tras anular una excepción (RF-07, RF-09) */}
                      {exitoAnulacion && (
                        <div className="alerta alerta--exito" role="status">
                          {exitoAnulacion}
                        </div>
                      )}
                      {/* Mensaje de error al anular (RF-07, RF-09) */}
                      {errorAnulacion && (
                        <div className="alerta alerta--error" role="alert">
                          <span>{errorAnulacion.texto}</span>
                        </div>
                      )}
                      {excepciones.length === 0 ? (
                        <p className="estado-vacio">Sin excepciones registradas.</p>
                      ) : (
                        <div className="tabla__contenedor">
                          <table className="tabla tabla--apilada">
                            <thead>
                              <tr>
                                <th scope="col">Motivo</th>
                                <th scope="col">Inicio</th>
                                <th scope="col">Fin</th>
                                <th scope="col">Estado</th>
                                <th scope="col">Acciones</th>
                              </tr>
                            </thead>
                            <tbody>
                              {excepciones.map((excepcion) => (
                                <tr key={excepcion.id}>
                                  <td data-etiqueta="Motivo">{excepcion.motivo}</td>
                                  <td data-etiqueta="Inicio">
                                    {formatearFecha(excepcion.fecha_inicio)}
                                  </td>
                                  <td data-etiqueta="Fin">
                                    {formatearFecha(excepcion.fecha_fin)}
                                  </td>
                                  <td data-etiqueta="Estado">
                                    <span
                                      className={`insignia ${CLASES_ESTADO_EXCEPCION[excepcion.estado] ?? "insignia--neutra"}`}
                                    >
                                      {excepcion.estado}
                                    </span>
                                  </td>
                                  <td data-etiqueta="Acciones">
                                    {/* Solo mostrar botón en VIGENTE o PROGRAMADA. En VENCIDA y ANULADA no existe botón (RF-07) */}
                                    {excepcion.estado === "VIGENTE" ||
                                    excepcion.estado === "PROGRAMADA" ? (
                                      anulacionPendiente === excepcion.id ? (
                                        <>
                                          <button
                                            type="button"
                                            className="boton boton--peligro boton--sm"
                                            onClick={() => confirmarAnulacion(excepcion.id)}
                                            disabled={enCurso === "anular"}
                                          >
                                            {enCurso === "anular"
                                              ? "Anulando..."
                                              : "Confirmar anulación"}
                                          </button>{" "}
                                          <button
                                            type="button"
                                            className="boton boton--secundario boton--sm"
                                            onClick={cancelarAnulacion}
                                            disabled={enCurso === "anular"}
                                          >
                                            Cancelar
                                          </button>
                                        </>
                                      ) : (
                                        <button
                                          type="button"
                                          className="boton boton--peligro boton--sm"
                                          onClick={() => pedirAnulacion(excepcion.id)}
                                          disabled={enCurso === "anular"}
                                        >
                                          Anular
                                        </button>
                                      )
                                    ) : (
                                      "—"
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </>
                  )}

                  {/* Bitácora cronológica de movimientos de reputación (Spec 011, RF-06) */}
                  {!cargandoFicha && !errorFicha?.permisos && !errorFicha?.noEncontrado && (
                    <section
                      className="formulario"
                      aria-labelledby="titulo-movimientos-reputacion"
                    >
                      <div>
                        <h3 className="tarjeta__titulo" id="titulo-movimientos-reputacion">
                          Historial de movimientos en el tiempo
                        </h3>
                        <div className="formulario__acciones">
                          <button
                            type="button"
                            className="boton boton--secundario boton--sm"
                            onClick={() => descargarCsvAlumno(seleccionado.id)}
                            disabled={descargandoCsvAlumno}
                          >
                            {descargandoCsvAlumno
                              ? "Descargando CSV..."
                              : "Descargar CSV del alumno"}
                          </button>
                        </div>
                      </div>

                      {errorCsvAlumno && (
                        <div className="alerta alerta--error" role="alert">
                          <span>{errorCsvAlumno.texto}</span>
                          {errorCsvAlumno.reintentable && (
                            <button
                              type="button"
                              className="boton boton--secundario boton--sm"
                              onClick={() => descargarCsvAlumno(seleccionado.id)}
                            >
                              Reintentar
                            </button>
                          )}
                        </div>
                      )}

                      {cargandoMovimientos ? (
                        <p className="cargando" role="status">
                          Cargando historial de movimientos...
                        </p>
                      ) : errorMovimientos ? (
                        <div className="alerta alerta--error" role="alert">
                          <span>{errorMovimientos.texto}</span>
                          {errorMovimientos.reintentable && (
                            <button
                              type="button"
                              className="boton boton--secundario boton--sm"
                              onClick={() => cargarMovimientosAlumno(seleccionado.id)}
                            >
                              Reintentar
                            </button>
                          )}
                        </div>
                      ) : movimientosAlumno.length === 0 ? (
                        <p className="estado-vacio">Sin movimientos de reputación registrados.</p>
                      ) : (
                        <div className="tabla__contenedor">
                          <table className="tabla tabla--apilada">
                            <thead>
                              <tr>
                                <th scope="col">Fecha</th>
                                <th scope="col">Evento</th>
                                <th scope="col">Recurso</th>
                                <th scope="col">Motivo</th>
                                <th scope="col">Variación</th>
                                <th scope="col">Saldo</th>
                              </tr>
                            </thead>
                            <tbody>
                              {movimientosAlumno.map((mov) => {
                                const variacion = Number(mov.variacion_puntos ?? 0);
                                const claseVariacion =
                                  variacion > 0
                                    ? "insignia--exito"
                                    : variacion < 0
                                      ? "insignia--error"
                                      : "insignia--neutra";
                                const textoVariacion =
                                  variacion > 0 ? `+${variacion}` : String(variacion);
                                return (
                                  <tr
                                    key={
                                      mov.id ??
                                      `${mov.fecha_movimiento}-${mov.numero_secuencia ?? ""}`
                                    }
                                  >
                                    <td data-etiqueta="Fecha">
                                      {formatearFecha(mov.fecha_movimiento)}
                                    </td>
                                    <td data-etiqueta="Evento">
                                      {ETIQUETAS_TIPO_MOVIMIENTO[mov.tipo] || mov.tipo}
                                    </td>
                                    <td data-etiqueta="Recurso">
                                      {mov.recurso_nombre || "—"}
                                    </td>
                                    <td data-etiqueta="Motivo">{mov.motivo || "—"}</td>
                                    <td data-etiqueta="Variación">
                                      <span className={`insignia ${claseVariacion}`}>
                                        {textoVariacion}
                                      </span>
                                    </td>
                                    <td data-etiqueta="Saldo">{mov.puntaje_resultante}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </section>
                  )}
                    </>
                  )}

                  {pestanaActiva === "historial" && (
                    <div className="formulario">
                      {cargandoHistorial ? (
                        <p className="cargando" role="status">
                          Cargando historial de préstamos del alumno...
                        </p>
                      ) : errorHistorial ? (
                        <div className="alerta alerta--error" role="alert">
                          <span>{errorHistorial}</span>{" "}
                          <button
                            type="button"
                            className="boton boton--secundario boton--sm"
                            onClick={() => cargarHistorialAlumno(seleccionado.id)}
                          >
                            Reintentar
                          </button>
                        </div>
                      ) : prestamosAlumno.length === 0 ? (
                        <div className="estado-vacio">
                          <p className="estado-vacio__titulo">Sin préstamos registrados</p>
                          <p>Este alumno aún no tiene préstamos asociados.</p>
                        </div>
                      ) : (
                        <>
                          <div className="formulario__acciones">
                            <button
                              type="button"
                              className="boton boton--secundario boton--sm"
                              onClick={descargarPrestamosCsv}
                            >
                              Descargar préstamos (CSV)
                            </button>
                          </div>

                          {errorInspeccion && (
                            <div className="alerta alerta--error" role="alert">
                              {errorInspeccion}
                            </div>
                          )}

                          {inspeccionVisualizada && (
                            <div
                              className="tarjeta"
                              style={{ border: "1px solid var(--primario)", marginBottom: "1rem" }}
                            >
                              <div className="tarjeta__cuerpo">
                                <div
                                  style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    marginBottom: "0.75rem",
                                  }}
                                >
                                  <strong>Detalle de inspección y garantía</strong>
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
                                    <strong>Garantía:</strong>{" "}
                                    {inspeccionVisualizada.garantia ? (
                                      <div className="campo__ayuda">
                                        Tipo: {inspeccionVisualizada.garantia.tipo} · Estado:{" "}
                                        {inspeccionVisualizada.garantia.estado} · Testigo:{" "}
                                        {inspeccionVisualizada.garantia.testigo}
                                        {inspeccionVisualizada.garantia.fecha_liberacion && (
                                          <>
                                            {" "}
                                            · Liberación:{" "}
                                            {formatearFecha(
                                              inspeccionVisualizada.garantia.fecha_liberacion
                                            )}
                                          </>
                                        )}
                                      </div>
                                    ) : (
                                      <div className="campo__ayuda">Sin garantía registrada.</div>
                                    )}
                                  </div>
                                  <div>
                                    <strong>Checklist inicial:</strong>
                                    <div className="campo__ayuda">
                                      {inspeccionVisualizada.checklist_inicial
                                        ? `${formatearFecha(
                                            inspeccionVisualizada.checklist_inicial.fecha_inspeccion
                                          )} — ${
                                            inspeccionVisualizada.checklist_inicial.observaciones
                                          }`
                                        : "Pendiente de entrega física."}
                                    </div>
                                  </div>
                                  <div>
                                    <strong>Checklist de devolución:</strong>
                                    <div className="campo__ayuda">
                                      {inspeccionVisualizada.checklist_devolucion
                                        ? `${formatearFecha(
                                            inspeccionVisualizada.checklist_devolucion
                                              .fecha_inspeccion
                                          )} — ${
                                            inspeccionVisualizada.checklist_devolucion.observaciones
                                          }`
                                        : "Pendiente de devolución."}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}

                          <div className="tabla__contenedor">
                            <table className="tabla tabla--apilada">
                              <thead>
                                <tr>
                                  <th scope="col">Recurso</th>
                                  <th scope="col">Estado</th>
                                  <th scope="col">Periodo pactado</th>
                                  <th scope="col">Tiempos reales</th>
                                  <th scope="col">Inspección</th>
                                </tr>
                              </thead>
                              <tbody>
                                {prestamosAlumno.map((prestamo) => {
                                  const recurso = recursosPorId.get(prestamo.recurso_id);
                                  return (
                                    <tr key={prestamo.id}>
                                      <td data-etiqueta="Recurso">
                                        <strong>
                                          {recurso?.nombre || "Recurso del catálogo"}
                                        </strong>
                                      </td>
                                      <td data-etiqueta="Estado">
                                        <span
                                          className={`insignia ${
                                            CLASES_ESTADO_PRESTAMO[prestamo.estado] ||
                                            "insignia--neutra"
                                          }`}
                                        >
                                          {ETIQUETA_ESTADO_PRESTAMO[prestamo.estado] ||
                                            prestamo.estado}
                                        </span>
                                      </td>
                                      <td data-etiqueta="Periodo pactado">
                                        <div>Inicio: {formatearFecha(prestamo.fecha_inicio)}</div>
                                        <div>Fin: {formatearFecha(prestamo.fecha_fin)}</div>
                                      </td>
                                      <td data-etiqueta="Tiempos reales">
                                        <div>
                                          Recogida:{" "}
                                          {prestamo.fecha_entrega_real
                                            ? formatearFecha(prestamo.fecha_entrega_real)
                                            : "Pendiente"}
                                        </div>
                                        <div>
                                          Devolución:{" "}
                                          {prestamo.fecha_devolucion_real
                                            ? formatearFecha(prestamo.fecha_devolucion_real)
                                            : "Pendiente"}
                                        </div>
                                      </td>
                                      <td data-etiqueta="Inspección">
                                        <button
                                          type="button"
                                          className="boton boton--fantasma boton--sm"
                                          disabled={cargandoInspeccion}
                                          onClick={() => verInspeccionAlumno(prestamo.id)}
                                        >
                                          Checklist
                                        </button>
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </section>

          {/* Formularios de sanción y excepción: solo en pestaña de reputación */}
          {seleccionado && pestanaActiva === "reputacion" && (
            <>
              {/* Formulario de sanción (RF-05, RF-09) */}
              <section className="tarjeta">
                <div className="tarjeta__cabecera">Aplicar sanción</div>
                <div className="tarjeta__cuerpo">
                  <form className="formulario" onSubmit={enviarSancion} noValidate>
                    {/* Tipo de sanción: los cuatro valores del dominio */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="sancion-tipo">
                        Tipo de sanción
                      </label>
                      <select
                        className="campo__control"
                        id="sancion-tipo"
                        value={tipoSancion}
                        onChange={(e) => {
                          setTipoSancion(e.target.value);
                          // Al cambiar el tipo se descarta el valor del campo que deja de aplicar
                          setDiasRetardo("");
                          setMontoSancion("");
                          setExitoSancion(null);
                          setErrorSancion(null);
                        }}
                        required
                      >
                        <option value="TARDANZA">TARDANZA</option>
                        <option value="INASISTENCIA_RESERVA">INASISTENCIA_RESERVA</option>
                        <option value="DANO_PARCIAL">DANO_PARCIAL</option>
                        <option value="DANO_TOTAL">DANO_TOTAL</option>
                      </select>
                    </div>

                    {/* Motivo: siempre obligatorio, máx. 500 caracteres */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="sancion-motivo">
                        Motivo
                      </label>
                      <textarea
                        className="campo__control"
                        id="sancion-motivo"
                        value={motivoSancion}
                        onChange={(e) => setMotivoSancion(e.target.value)}
                        maxLength={500}
                        required
                        rows={3}
                      />
                    </div>

                    {/* Campo condicional: días de retardo (solo TARDANZA) */}
                    {tipoSancion === "TARDANZA" && (
                      <div className="campo">
                        <label className="campo__label" htmlFor="sancion-dias">
                          Días de retardo
                        </label>
                        <input
                          className="campo__control"
                          id="sancion-dias"
                          type="number"
                          min="1"
                          step="1"
                          value={diasRetardo}
                          onChange={(e) => setDiasRetardo(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    {/* Campo condicional: monto (solo DANO_TOTAL) */}
                    {tipoSancion === "DANO_TOTAL" && (
                      <div className="campo">
                        <label className="campo__label" htmlFor="sancion-monto">
                          Monto del daño ($)
                        </label>
                        <input
                          className="campo__control"
                          id="sancion-monto"
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={montoSancion}
                          onChange={(e) => setMontoSancion(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    {/* Mensaje de éxito: tipo, puntos y fecha de fin del backend (RF-05) */}
                    {exitoSancion && (
                      <div className="alerta alerta--exito" role="status">
                        {exitoSancion}
                      </div>
                    )}

                    {/* Mensajes de error según código HTTP (RF-09) */}
                    {errorSancion && (
                      <div className="alerta alerta--error" role="alert">
                        <span>{errorSancion.texto}</span>{" "}
                        {errorSancion.reintentable && (
                          <button
                            type="submit"
                            className="boton boton--secundario boton--sm"
                          >
                            Reintentar
                          </button>
                        )}
                      </div>
                    )}

                    <div className="formulario__acciones">
                      {/* Botón primario; disabled mientras la petición está en vuelo (RF-09) */}
                      <button
                        type="submit"
                        className="boton boton--primario"
                        disabled={enCurso === "sancion"}
                      >
                        {enCurso === "sancion" ? "Aplicando..." : "Aplicar sanción"}
                      </button>
                    </div>
                  </form>
                </div>
              </section>

              {/* Formulario de excepción académica (RF-06, RF-09) */}
              <section className="tarjeta">
                <div className="tarjeta__cabecera">Registrar excepción académica</div>
                <div className="tarjeta__cuerpo">
                  <form className="formulario" onSubmit={enviarExcepcion} noValidate>
                    {/* Motivo de la excepción: máx. 500 caracteres */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="excepcion-motivo">
                        Motivo
                      </label>
                      <textarea
                        className="campo__control"
                        id="excepcion-motivo"
                        value={motivoExcepcion}
                        onChange={(e) => setMotivoExcepcion(e.target.value)}
                        maxLength={500}
                        required
                        rows={3}
                      />
                    </div>

                    {/* Fecha de inicio: datetime-local obligatorio */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="excepcion-inicio">
                        Fecha y hora de inicio
                      </label>
                      <input
                        className="campo__control"
                        id="excepcion-inicio"
                        type="datetime-local"
                        value={inicioExcepcion}
                        onChange={(e) => {
                          setInicioExcepcion(e.target.value);
                          // Al cambiar el inicio se resetea la marca de fin inválido
                          setFinInvalido(false);
                        }}
                        required
                      />
                    </div>

                    {/* Fecha de fin: datetime-local obligatorio; se marca aria-invalid si fin < inicio */}
                    <div className="campo">
                      <label className="campo__label" htmlFor="excepcion-fin">
                        Fecha y hora de fin
                      </label>
                      <input
                        className="campo__control"
                        id="excepcion-fin"
                        type="datetime-local"
                        value={finExcepcion}
                        onChange={(e) => {
                          setFinExcepcion(e.target.value);
                          setFinInvalido(false);
                        }}
                        required
                        aria-invalid={finInvalido ? "true" : undefined}
                        aria-describedby={finInvalido ? "excepcion-fin-error" : undefined}
                      />
                      {/* Error de validación local: fin anterior a inicio */}
                      {finInvalido && (
                        <span className="campo__error" id="excepcion-fin-error" role="alert">
                          La fecha de fin no puede ser anterior a la fecha de inicio.
                        </span>
                      )}
                    </div>

                    {/* Mensaje de éxito: rango registrado y aviso si es futura (RF-06) */}
                    {exitoExcepcion && (
                      <div className="alerta alerta--exito" role="status">
                        {exitoExcepcion}
                      </div>
                    )}

                    {/* Mensajes de error según código HTTP (RF-09) */}
                    {errorExcepcion && (
                      <div className="alerta alerta--error" role="alert">
                        <span>{errorExcepcion.texto}</span>{" "}
                        {errorExcepcion.reintentable && (
                          <button
                            type="submit"
                            className="boton boton--secundario boton--sm"
                          >
                            Reintentar
                          </button>
                        )}
                      </div>
                    )}

                    <div className="formulario__acciones">
                      {/* Botón primario; disabled mientras la petición está en vuelo (RF-09) */}
                      <button
                        type="submit"
                        className="boton boton--primario"
                        disabled={enCurso === "excepcion"}
                      >
                        {enCurso === "excepcion" ? "Registrando..." : "Registrar excepción"}
                      </button>
                    </div>
                  </form>
                </div>
              </section>
            </>
          )}
            </div>
          </div>

          {/* Amnistía mensual: acción global con confirmación en dos pasos (T8, RF-08, RF-09) */}
          <section className="tarjeta">
            <div className="tarjeta__cabecera">Amnistía mensual</div>
            <div className="tarjeta__cuerpo">
              <div className="formulario">
                <div className="alerta alerta--aviso">
                  La amnistía mensual es una acción global que afecta a todos los perfiles elegibles
                  del sistema, no solo al usuario seleccionado. Suma puntos a perfiles en nivel BAJO
                  que no registren sanciones recientes.
                </div>

                {/* Resultado de la amnistía: N > 0 es alerta--exito, N = 0 es alerta--info (RF-08) */}
                {resultadoAmnistia && (
                  <div
                    className={`alerta ${
                      resultadoAmnistia.tipo === "exito" ? "alerta--exito" : "alerta--info"
                    }`}
                    role="status"
                  >
                    {resultadoAmnistia.texto}
                  </div>
                )}

                {/* Error de amnistía según RF-09 */}
                {errorAmnistia && (
                  <div className="alerta alerta--error" role="alert">
                    <span>{errorAmnistia.texto}</span>
                  </div>
                )}

                <div className="formulario__acciones">
                  {amnistiaPendiente ? (
                    <>
                      <button
                        type="button"
                        className="boton boton--peligro"
                        onClick={confirmarAmnistia}
                        disabled={enCurso === "amnistia"}
                      >
                        {enCurso === "amnistia" ? "Ejecutando..." : "Confirmar ejecución"}
                      </button>{" "}
                      <button
                        type="button"
                        className="boton boton--secundario"
                        onClick={cancelarAmnistia}
                        disabled={enCurso === "amnistia"}
                      >
                        Cancelar
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="boton boton--peligro"
                      onClick={pedirAmnistia}
                      disabled={enCurso === "amnistia"}
                    >
                      Ejecutar amnistía
                    </button>
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
