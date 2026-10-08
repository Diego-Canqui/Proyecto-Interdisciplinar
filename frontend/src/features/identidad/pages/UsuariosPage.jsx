import { useEffect, useState } from "react";
import { crearUsuario, listarUsuarios } from "../api.js";

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [telefono, setTelefono] = useState("");

  const cargar = () => listarUsuarios().then(setUsuarios);

  useEffect(() => {
    cargar();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    await crearUsuario({ nombre, correo, telefono, roles: [] });
    setNombre("");
    setCorreo("");
    setTelefono("");
    cargar();
  };

  return (
    <main>
      <h1>Usuarios</h1>
      <form onSubmit={handleSubmit}>
        <input placeholder="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <input placeholder="Correo" value={correo} onChange={(e) => setCorreo(e.target.value)} required />
        <input placeholder="Teléfono" value={telefono} onChange={(e) => setTelefono(e.target.value)} required />
        <button type="submit">Crear</button>
      </form>
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
