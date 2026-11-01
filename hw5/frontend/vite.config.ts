import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `npm run dev` serves the desk on http://localhost:5173 and opens it in the browser.
// The page calls the FastAPI backend directly (VITE_API_URL, default http://127.0.0.1:8000);
// backend/main.py allows this origin through CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    open: true,
  },
})
