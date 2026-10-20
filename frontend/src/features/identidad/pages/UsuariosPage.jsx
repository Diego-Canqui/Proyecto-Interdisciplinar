import { useEffect, useState } from "react";
import { crearUsuario, listarUsuarios } from "../api.js";

const MENSAJES_ERROR = {
  403: "No tienes permisos de gestión para crear usuarios.",
  409: "Ya existe un usuario con ese correo.",
  422: "Datos inválidos: revisa la contraseña (mínimo 8 caracteres, una mayúscula, una minúscula y un dígito) y el teléfono.",
};

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [telefono, setTelefono] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const cargar = () => listarUsuarios().then(setUsuarios);

  useEffect(() => {
    cargar();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      // Sin `roles`: el default [ESTUDIANTE] lo aplica el backend (RF-16)
      await crearUsuario({ nombre, correo, telefono, password });
    } catch (err) {
      setError(MENSAJES_ERROR[err.status] || err.message || "Error al crear el usuario");
      return;
    }
    setNombre("");
    setCorreo("");
    setTelefono("");
    setPassword("");
    cargar();
  };

  return (
    <main>
      <h1>Usuarios</h1>
      <form onSubmit={handleSubmit}>
        <input placeholder="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <input placeholder="Correo" value={correo} onChange={(e) => setCorreo(e.target.value)} required />
        <input placeholder="Teléfono" value={telefono} onChange={(e) => setTelefono(e.target.value)} required />
        <input
          placeholder="Contraseña"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">Crear</button>
      </form>
      {error && (
        <p role="alert" style={{ color: "red" }}>
          {error}
        </p>
      )}
      <ul>
        {usuarios.map((u) => (
          <li key={u.id}>
            {u.nombre} — {u.correo}
          </li>
        ))}
      </ul>
    </main>
  );
}
