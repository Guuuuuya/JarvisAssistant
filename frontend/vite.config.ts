import { defineConfig } from "vite";
import fs from "fs";

export default defineConfig({
  server: {
    port: 5173,
    host: true,
    https: {
      key: fs.readFileSync("../key.pem"),
      cert: fs.readFileSync("../cert.pem"),
    },
    proxy: {
      "/ws": { target: "https://localhost:8000", ws: true, secure: false },
    },
  },
});
