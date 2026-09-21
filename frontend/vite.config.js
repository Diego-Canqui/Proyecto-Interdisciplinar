import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  envDir: "..", // lee el .env de la raíz del repositorio
  server: { port: 5173 },
});
