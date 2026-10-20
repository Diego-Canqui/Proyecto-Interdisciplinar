import { NavLink, Link, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../features/identidad/api.js";

// Mapa rol → enlace = tabla de la guía §6 (D1). «Usuarios» solo para administración.
const ENLACES = [
  { a: "/recursos", texto: "Recursos" },
  { a: "/reservas", texto: "Reservas" },
  { a: "/historial", texto: "Historial" },
  { a: "/reputacion", texto: "Reputación" },
  { a: "/usuarios", texto: "Usuarios", soloAdministrador: true },
];

/**
 * Lee los roles del JWT guardado en localStorage, sin dependencias externas (D5).
 * Es una noción de presentación: no valida la firma ni la expiración.
 * @returns {string[]} Roles del payload, o [] si no hay token o no se puede decodificar
 */
function leerRoles() {
  try {
    const token = localStorage.getItem("token");
    if (!token) return [];
    const payload = token.split(".")[1];
    if (!payload) return [];
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const relleno = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const datos = JSON.parse(atob(relleno));
    return Array.isArray(datos.roles) ? datos.roles : [];
  } catch {
    return []; // token ilegible o payload raro → visitante (caso límite 2)
  }
}

/**
 * Esqueleto común de la interfaz: barra superior con la navegación y área de contenido
 * donde se renderiza la página activa. El estado de la barra se deriva del token.
 * @returns {JSX.Element} Layout con la navbar y el área de contenido
 */
export default function Layout() {
  const navigate = useNavigate();
  const roles = leerRoles(); // única lectura del token (P2)
  const haySesion = roles.length > 0; // RF-03
  const esAdministrador = roles.includes("ADMINISTRADOR_SISTEMA");
  const enlaces = ENLACES.filter((e) => !e.soloAdministrador || esAdministrador); // RF-02

  const cerrarSesion = async () => {
    try {
      await logout();
    } catch {
      // Un fallo de red o un 4xx/5xx no impide el cierre en el cliente (RF-05)
    } finally {
      localStorage.removeItem("token");
      navigate("/login");
    }
  };

  return (
    <>
      <header className="navbar">
        <div className="navbar__contenido contenedor">
          <span className="navbar__marca">Préstamos de Recursos</span>
          <nav className="navbar__enlaces" aria-label="Navegación principal">
            {haySesion ? (
              <>
                {enlaces.map(({ a, texto }) => (
                  <NavLink
                    key={a}
                    to={a}
                    className={({ isActive }) =>
                      isActive ? "navbar__enlace navbar__enlace--activo" : "navbar__enlace"
                    }
                  >
                    {texto}
                  </NavLink>
                ))}
                <button type="button" className="boton boton--fantasma" onClick={cerrarSesion}>
                  Cerrar sesión
                </button>
              </>
            ) : (
              <>
                <Link className="navbar__enlace" to="/login">
                  Iniciar sesión
                </Link>
                <Link className="navbar__enlace" to="/registro">
                  Registrarse
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="contenedor pagina">
        <Outlet />
      </main>
    </>
  );
}
