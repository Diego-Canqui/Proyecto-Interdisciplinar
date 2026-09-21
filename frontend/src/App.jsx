import { BrowserRouter, Route, Routes } from "react-router-dom";
import { LoginPage } from "./features/identidad";
import { BuscarRecursosPage } from "./features/catalogo";
import { MisReservasPage } from "./features/reservas";
import { HistorialPage } from "./features/prestamos";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/recursos" element={<BuscarRecursosPage />} />
        <Route path="/reservas" element={<MisReservasPage />} />
        <Route path="/historial" element={<HistorialPage />} />
      </Routes>
    </BrowserRouter>
  );
}
