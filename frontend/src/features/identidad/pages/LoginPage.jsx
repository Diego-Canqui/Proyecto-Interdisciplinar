import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../api.js";

export default function LoginPage() {
  const navigate = useNavigate();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const response = await login({ correo, password });
      localStorage.setItem("token", response.token);
      navigate("/");
    } catch (err) {
      setError(err.message || "Correo o contraseña incorrectos");
    }
  };

  const handleInputChange = () => {
    if (error) setError("");
  };

  return (
    <main style={{ maxWidth: "400px", margin: "2rem auto", padding: "1rem" }}>
      <h1>Iniciar sesión</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label htmlFor="correo" style={{ display: "block", marginBottom: "0.25rem" }}>
            Correo electrónico
          </label>
          <input
            id="correo"
            type="email"
            value={correo}
            onChange={(e) => {
              setCorreo(e.target.value);
              handleInputChange();
            }}
            required
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
            }}
          />
        </div>

        <div>
          <label htmlFor="password" style={{ display: "block", marginBottom: "0.25rem" }}>
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              handleInputChange();
            }}
            required
            style={{
              width: "100%",
              padding: "0.5rem",
              boxSizing: "border-box",
            }}
          />
        </div>

        {error && (
          <div style={{ color: "red", fontSize: "0.875rem" }} role="alert">
            {error}
          </div>
        )}

        <button
          type="submit"
          style={{
            padding: "0.75rem",
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "1rem",
          }}
        >
          Iniciar sesión
        </button>
      </form>

      <p style={{ marginTop: "1rem", textAlign: "center" }}>
        ¿No tienes cuenta? <Link to="/registro">Regístrate</Link>
      </p>
    </main>
  );
}