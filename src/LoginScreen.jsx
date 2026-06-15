import { useState } from "react";
import { API_BASE, saveSession } from "./apiClient";
import { IconEye, IconEyeOff } from "./icons";
import RecoverPassword from "./RecoverPassword";

export default function LoginScreen({ onLoggedIn }) {
  const [view, setView] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "No se pudo iniciar sesion.");
      }
      saveSession(data.token, data.user);
      onLoggedIn(data.user);
    } catch (loginError) {
      setError(loginError.message || "Error de autenticacion.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-5 py-8 text-zinc-100">
      {view === "recover" ? (
        <RecoverPassword onBack={() => setView("login")} />
      ) : (
        <section className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900/90 p-8 shadow-xl shadow-black/40">
          <p className="text-sm text-zinc-400">I.E.I. N° 32857 — Huacalle</p>
          <h1 className="mt-1 text-3xl font-semibold text-white">PredictEdu</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Acceso para docentes y administracion del colegio.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-1 block text-xs text-zinc-400">Usuario</span>
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin o mquispe"
                autoComplete="username"
                required
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-blue-400"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-zinc-400">Contrasena</span>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 py-2 pl-3 pr-10 text-sm outline-none focus:border-blue-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-zinc-400 hover:text-zinc-200"
                  aria-label={showPassword ? "Ocultar contrasena" : "Mostrar contrasena"}
                >
                  {showPassword ? <IconEyeOff /> : <IconEye />}
                </button>
              </div>
            </label>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setView("recover")}
                className="text-xs text-blue-300 hover:text-blue-200"
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>
            {error && (
              <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-blue-500 py-2.5 font-medium text-white hover:bg-blue-400 disabled:opacity-60"
            >
              {loading ? "Ingresando..." : "Iniciar sesion"}
            </button>
          </form>

          <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-500">
            <p className="font-medium text-zinc-400">Cuentas de demostracion</p>
            <p className="mt-1">Admin: admin / admin2026</p>
            <p>Docente: mquispe / tutor2026</p>
          </div>
        </section>
      )}
    </main>
  );
}
