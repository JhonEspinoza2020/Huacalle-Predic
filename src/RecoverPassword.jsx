import { useState } from "react";
import { API_BASE } from "./apiClient";
import {
  sanitizeTelefonoInput,
  validateTelefono,
  validateUsername,
} from "./validators";

export default function RecoverPassword({ onBack }) {
  const [username, setUsername] = useState("");
  const [telefono, setTelefono] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const userError = validateUsername(username);
    const telefonoError = validateTelefono(telefono);

    if (telefonoError || userError) {
      setError(telefonoError || userError);
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/recover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          telefono: telefono.trim(),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "No se pudo enviar la solicitud.");
      }
      setMessage(
        data.message ||
          "Próximamente recibirás un código en el teléfono registrado del docente."
      );
    } catch (recoverError) {
      setError(recoverError.message || "Error al solicitar recuperación.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900/90 p-8 shadow-xl shadow-black/40">
      <button
        type="button"
        onClick={onBack}
        className="text-sm text-blue-300 hover:text-blue-200"
      >
        Volver al inicio de sesión
      </button>
      <h2 className="mt-4 text-2xl font-semibold text-white">Recuperar acceso</h2>
      <p className="mt-2 text-sm text-zinc-400">
        Ingresa el teléfono registrado en tu ficha. Enviaremos un código por SMS para restablecer el acceso.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <label className="block">
          <span className="mb-1 block text-xs text-zinc-400">Usuario</span>
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-blue-400"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-zinc-400">Teléfono registrado</span>
          <input
            type="tel"
            value={telefono}
            onChange={(event) => setTelefono(sanitizeTelefonoInput(event.target.value))}
            placeholder="987654321"
            inputMode="numeric"
            required
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-blue-400"
          />
          {telefono && (
            <p className="mt-1 text-[10px] text-zinc-500">{telefono.length}/9 dígitos</p>
          )}
        </label>
        {message && (
          <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
            {message}
          </p>
        )}
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
          {loading ? "Enviando solicitud..." : "Solicitar código"}
        </button>
      </form>
    </section>
  );
}
