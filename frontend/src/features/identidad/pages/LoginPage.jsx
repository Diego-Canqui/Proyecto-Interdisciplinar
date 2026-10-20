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
      navigate("/recursos");
    } catch (err) {
      setError(err.message || "Correo o contraseña incorrectos");
    }
  };

  const handleInputChange = () => {
    if (error) setError("");
  };

  return (
    <main className="contenedor contenedor--estrecho pagina">
      <div className="tarjeta">
        <div className="tarjeta__cuerpo">
          <h1 className="pagina__titulo">Iniciar sesión</h1>
          <form className="formulario" onSubmit={handleSubmit}>
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="correo">
                Correo electrónico
              </label>
              <input
                className="campo__control"
                id="correo"
                type="email"
                value={correo}
                onChange={(e) => {
                  setCorreo(e.target.value);
                  handleInputChange();
                }}
                required
              />
            </div>

            <div className="campo">
              <label className="campo__etiqueta" htmlFor="password">
                Contraseña
              </label>
              <input
                className="campo__control"
                id="password"
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  handleInputChange();
                }}
                required
              />
            </div>

            {error && (
              <div className="alerta alerta--error" role="alert">
                {error}
              </div>
            )}

            <div className="formulario__acciones">
              <button type="submit" className="boton boton--primario boton--bloque">
                Iniciar sesión
              </button>
            </div>
          </form>

          <p className="texto-suave texto-centrado">
            ¿No tienes cuenta? <Link to="/registro">Regístrate</Link>
          </p>
        </div>
      </div>
    </main>
  );
}
