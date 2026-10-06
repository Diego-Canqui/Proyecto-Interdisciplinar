import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { registro } from "../api.js";

/**
 * Valida la complejidad de la contraseña.
 * @param {string} password
 * @returns {string[]|true} Array de mensajes de error o true si es válida
 */
function validarPassword(password) {
  const errores = [];
  if (password.length < 8) {
    errores.push("Mínimo 8 caracteres");
  }
  if (!/[A-Z]/.test(password)) {
    errores.push("Al menos 1 mayúscula");
  }
  if (!/[a-z]/.test(password)) {
    errores.push("Al menos 1 minúscula");
  }
  if (!/[0-9]/.test(password)) {
    errores.push("Al menos 1 dígito");
  }
  return errores.length > 0 ? errores : true;
}

/**
 * Valida el formato del teléfono (opcional).
 * @param {string} telefono
 * @returns {boolean}
 */
function validarTelefono(telefono) {
  if (!telefono || telefono.trim() === "") return true;
  const regex = /^\+?[0-9\s-]{7,20}$/;
  return regex.test(telefono.trim());
}

/**
 * Valida el formato del email.
 * @param {string} email
 * @returns {boolean}
 */
function validarEmail(email) {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
}

export default function RegistroPage() {
  const navigate = useNavigate();
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [telefono, setTelefono] = useState("");
  const [password, setPassword] = useState("");
  const [confirmarPassword, setConfirmarPassword] = useState("");
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState("");

  const limpiarError = (campo) => {
    if (errores[campo]) {
      setErrores((prev) => {
        const nuevos = { ...prev };
        delete nuevos[campo];
        return nuevos;
      });
    }
    if (errorGeneral) setErrorGeneral("");
  };

  const validarFormulario = () => {
    const nuevosErrores = {};

    if (!nombre.trim()) {
      nuevosErrores.nombre = "El nombre es obligatorio";
    }

    if (!correo.trim()) {
      nuevosErrores.correo = "El correo es obligatorio";
    } else if (!validarEmail(correo)) {
      nuevosErrores.correo = "Formato de correo inválido";
    }

    if (!password) {
      nuevosErrores.password = "La contraseña es obligatoria";
    } else {
      const validacionPassword = validarPassword(password);
      if (validacionPassword !== true) {
        nuevosErrores.password = validacionPassword.join(", ");
      }
    }

    if (!confirmarPassword) {
      nuevosErrores.confirmarPassword = "Confirma tu contraseña";
    } else if (password !== confirmarPassword) {
      nuevosErrores.confirmarPassword = "Las contraseñas no coinciden";
    }

    if (telefono && telefono.trim() !== "" && !validarTelefono(telefono)) {
      nuevosErrores.telefono = "Formato de teléfono inválido (ej: +34 912 345 678)";
    }

    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorGeneral("");

    if (!validarFormulario()) {
      return;
    }

    try {
      const response = await registro({
        nombre: nombre.trim(),
        correo: correo.trim(),
        telefono: telefono.trim() || undefined,
        password,
        roles: ["ESTUDIANTE"],
      });
      localStorage.setItem("token", response.token);
      navigate("/");
    } catch (err) {
      setErrorGeneral(err.message || "Error al registrar usuario");
    }
  };

  return (
    <main style={{ maxWidth: "400px", margin: "2rem auto", padding: "1rem" }}>
      <h1>Registro</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label htmlFor="nombre" style={{ display: "block", marginBottom: "0.25rem" }}>
            Nombre *
          </label>
          <input
            id="nombre"
            type="text"
            value={nombre}
            onChange={(e) => {
              setNombre(e.target.value);
              limpiarError("nombre");
            }}
            required
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
              borderColor: errores.nombre ? "red" : undefined,
            }}
          />
          {errores.nombre && (
            <span style={{ color: "red", fontSize: "0.75rem" }}>{errores.nombre}</span>
          )}
        </div>

        <div>
          <label htmlFor="correo" style={{ display: "block", marginBottom: "0.25rem" }}>
            Correo electrónico *
          </label>
          <input
            id="correo"
            type="email"
            value={correo}
            onChange={(e) => {
              setCorreo(e.target.value);
              limpiarError("correo");
            }}
            required
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
              borderColor: errores.correo ? "red" : undefined,
            }}
          />
          {errores.correo && (
            <span style={{ color: "red", fontSize: "0.75rem" }}>{errores.correo}</span>
          )}
        </div>

        <div>
          <label htmlFor="telefono" style={{ display: "block", marginBottom: "0.25rem" }}>
            Teléfono (opcional)
          </label>
          <input
            id="telefono"
            type="tel"
            value={telefono}
            onChange={(e) => {
              setTelefono(e.target.value);
              limpiarError("telefono");
            }}
            placeholder="+34 912 345 678"
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
              borderColor: errores.telefono ? "red" : undefined,
            }}
          />
          {errores.telefono && (
            <span style={{ color: "red", fontSize: "0.75rem" }}>{errores.telefono}</span>
          )}
        </div>

        <div>
          <label htmlFor="password" style={{ display: "block", marginBottom: "0.25rem" }}>
            Contraseña *
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              limpiarError("password");
            }}
            required
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
              borderColor: errores.password ? "red" : undefined,
            }}
          />
          {errores.password && (
            <span style={{ color: "red", fontSize: "0.75rem" }}>{errores.password}</span>
          )}
          <div style={{ fontSize: "0.75rem", color: "#666", marginTop: "0.25rem" }}>
            Mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula y 1 dígito
          </div>
        </div>

        <div>
          <label htmlFor="confirmarPassword" style={{ display: "block", marginBottom: "0.25rem" }}>
            Confirmar contraseña *
          </label>
          <input
            id="confirmarPassword"
            type="password"
            value={confirmarPassword}
            onChange={(e) => {
              setConfirmarPassword(e.target.value);
              limpiarError("confirmarPassword");
            }}
            required
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
              borderColor: errores.confirmarPassword ? "red" : undefined,
            }}
          />
          {errores.confirmarPassword && (
            <span style={{ color: "red", fontSize: "0.75rem" }}>{errores.confirmarPassword}</span>
          )}
        </div>

        {errorGeneral && (
          <div style={{ color: "red", fontSize: "0.875rem" }} role="alert">
            {errorGeneral}
          </div>
        )}

        <button
          type="submit"
          style={{
            padding: "0.75rem",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "1rem",
          }}
        >
          Registrarse
        </button>
      </form>

      <p style={{ marginTop: "1rem", textAlign: "center" }}>
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </main>
  );
}