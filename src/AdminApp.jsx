import { useCallback, useEffect, useRef, useState } from "react";
import {
  API_BASE,
  authFetch,
  authFetchJson,
} from "./apiClient";
import {
  IconChart,
  IconFile,
  IconLogout,
  IconSchool,
  IconUpload,
  IconUsers,
} from "./icons";

function AdminTab({ label, icon: Icon, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition ${
        active
          ? "border-amber-500/50 bg-amber-500/10 text-amber-100"
          : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
      }`}
    >
      <Icon />
      {label}
    </button>
  );
}

function StatCard({ title, value, subtitle, tone = "zinc" }) {
  const tones = {
    red: "text-red-400",
    orange: "text-orange-400",
    green: "text-emerald-400",
    blue: "text-blue-400",
    zinc: "text-zinc-100",
  };
  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
      <p className="text-sm text-zinc-400">{title}</p>
      <p className={`mt-2 text-4xl font-semibold ${tones[tone]}`}>{value}</p>
      <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>
    </article>
  );
}

const CARGO_LABELS = {
  docente: "Docente",
  tutor: "Tutor",
  director: "Director",
  psicologo: "Psicologo",
  admin: "Administracion",
};

function formatSeccion(item) {
  const nivel = item.nivel_educativo === "primaria" ? "Primaria" : "Secundaria";
  return `${item.grado}° ${item.seccion} · ${nivel}`;
}

function formatTurno(turno) {
  if (turno === "tarde") return "Tarde";
  return "Manana";
}

export default function AdminApp({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState("panel");
  const [cargas, setCargas] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [docentes, setDocentes] = useState([]);
  const [secciones, setSecciones] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [systemReady, setSystemReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [siagie, users, docentesData, seccionesData, resumenDash, status] =
        await Promise.all([
          authFetchJson(`${API_BASE}/api/admin/cargas-siagie`),
          authFetchJson(`${API_BASE}/api/admin/usuarios`),
          authFetchJson(`${API_BASE}/api/admin/docentes`),
          authFetchJson(`${API_BASE}/api/admin/secciones`),
          authFetchJson(`${API_BASE}/api/resumen`),
          authFetchJson(`${API_BASE}/api/status`),
        ]);
      setCargas(siagie.cargas || []);
      setUsuarios(users.usuarios || []);
      setDocentes(docentesData.docentes || []);
      setSecciones(seccionesData.secciones || []);
      setResumen(resumenDash);
      setSystemReady(status.database?.ready ?? false);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAdminData();
  }, [loadAdminData]);

  const handleUploadButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      const formDataUpload = new FormData();
      formDataUpload.append("file", file);
      const response = await authFetch(`${API_BASE}/api/upload_siagie`, {
        method: "POST",
        body: formDataUpload,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "No se pudo procesar el archivo SIAGIE.");
      }
      setMessage(
        `Carga SIAGIE registrada · ${data.storage?.filas_guardadas ?? 0} estudiantes importados.`
      );
      await loadAdminData();
      setActiveTab("siagie");
    } catch (uploadError) {
      setError(uploadError.message || "Error al subir el archivo.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const docentesActivos = docentes.filter((item) => item.activo).length;

  return (
    <main className="min-h-screen bg-zinc-950 px-5 py-8 text-zinc-100">
      <section className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-amber-900/40 bg-gradient-to-br from-zinc-900 to-zinc-950 p-6 shadow-xl shadow-black/30 md:flex-row md:items-start">
          <div>
            <p className="text-sm text-amber-200/80">Modo administracion</p>
            <h1 className="mt-1 text-4xl font-semibold text-white">PredictEdu Admin</h1>
            <p className="mt-2 text-sm text-zinc-400">
              Gestion institucional: personal docente, secciones, usuarios y cargas SIAGIE.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-100">
                {user.nombre_completo || user.username} · administrador
              </span>
              <span
                className={`rounded-full border px-3 py-1 text-xs ${
                  systemReady
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                    : "border-red-500/40 bg-red-500/10 text-red-200"
                }`}
              >
                {systemReady ? "Sistema operativo" : "Servicio no disponible"}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 hover:bg-zinc-700"
          >
            <IconLogout />
            Cerrar sesion
          </button>
        </header>

        {(message || error) && (
          <div className="mb-4 space-y-2">
            {message && (
              <p className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                {message}
              </p>
            )}
            {error && (
              <p className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </p>
            )}
          </div>
        )}

        <nav className="mb-6 flex flex-wrap gap-2">
          <AdminTab
            label="Panel"
            icon={IconChart}
            active={activeTab === "panel"}
            onClick={() => setActiveTab("panel")}
          />
          <AdminTab
            label="Docentes"
            icon={IconUsers}
            active={activeTab === "docentes"}
            onClick={() => setActiveTab("docentes")}
          />
          <AdminTab
            label="Secciones"
            icon={IconSchool}
            active={activeTab === "secciones"}
            onClick={() => setActiveTab("secciones")}
          />
          <AdminTab
            label="Usuarios"
            icon={IconUsers}
            active={activeTab === "usuarios"}
            onClick={() => setActiveTab("usuarios")}
          />
          <AdminTab
            label="Cargas SIAGIE"
            icon={IconFile}
            active={activeTab === "siagie"}
            onClick={() => setActiveTab("siagie")}
          />
        </nav>

        {loading ? (
          <p className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-400">
            Cargando panel de administracion...
          </p>
        ) : (
          <>
            {activeTab === "panel" && (
              <div className="space-y-6">
                <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <StatCard
                    title="Estudiantes"
                    value={resumen?.total_estudiantes ?? 0}
                    subtitle="matriculados activos"
                    tone="blue"
                  />
                  <StatCard
                    title="Analisis"
                    value={resumen?.total_predicciones ?? 0}
                    subtitle="registrados en el ano"
                    tone="zinc"
                  />
                  <StatCard
                    title="Riesgo alto"
                    value={resumen?.summary?.alto ?? 0}
                    subtitle="ultimo analisis por alumno"
                    tone="red"
                  />
                  <StatCard
                    title="Docentes"
                    value={docentesActivos}
                    subtitle={`de ${docentes.length} en plantel`}
                    tone="green"
                  />
                </section>
                <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                  <h2 className="text-lg font-semibold text-white">Ultimas cargas SIAGIE</h2>
                  {cargas.length === 0 ? (
                    <p className="mt-3 text-sm text-zinc-400">Sin cargas registradas.</p>
                  ) : (
                    <div className="mt-4 space-y-2">
                      {cargas.slice(0, 5).map((carga) => (
                        <div
                          key={carga.id}
                          className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3 text-sm"
                        >
                          <p className="font-medium text-zinc-100">{carga.nombre_archivo}</p>
                          <p className="mt-1 text-zinc-400">
                            {carga.filas_procesadas}/{carga.total_filas} estudiantes ·{" "}
                            {carga.subido_por || "sin usuario"}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            )}

            {activeTab === "docentes" && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <h2 className="text-lg font-semibold text-white">Personal docente</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Docentes y tutores registrados en la institucion educativa.
                </p>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="border-b border-zinc-800 text-zinc-400">
                      <tr>
                        <th className="px-3 py-2">Nombre</th>
                        <th className="px-3 py-2">DNI</th>
                        <th className="px-3 py-2">Especialidad</th>
                        <th className="px-3 py-2">Cargo</th>
                        <th className="px-3 py-2">Telefono</th>
                        <th className="px-3 py-2">Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {docentes.map((item) => (
                        <tr key={item.id} className="border-b border-zinc-800/80">
                          <td className="px-3 py-3 text-zinc-100">{item.nombre_completo}</td>
                          <td className="px-3 py-3 text-zinc-300">{item.dni || "—"}</td>
                          <td className="px-3 py-3 text-zinc-300">
                            {item.especialidad || "—"}
                          </td>
                          <td className="px-3 py-3 text-zinc-300">
                            {CARGO_LABELS[item.cargo] || item.cargo}
                          </td>
                          <td className="px-3 py-3 text-zinc-300">{item.telefono || "—"}</td>
                          <td className="px-3 py-3">
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs ${
                                item.activo
                                  ? "bg-emerald-500/10 text-emerald-200"
                                  : "bg-zinc-800 text-zinc-400"
                              }`}
                            >
                              {item.activo ? "Activo" : "Inactivo"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {activeTab === "secciones" && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <h2 className="text-lg font-semibold text-white">Secciones del ano escolar</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Aulas, tutores asignados y alumnos matriculados por seccion.
                </p>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="border-b border-zinc-800 text-zinc-400">
                      <tr>
                        <th className="px-3 py-2">Seccion</th>
                        <th className="px-3 py-2">Ano escolar</th>
                        <th className="px-3 py-2">Turno</th>
                        <th className="px-3 py-2">Tutor</th>
                        <th className="px-3 py-2">Alumnos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {secciones.map((item) => (
                        <tr key={item.id} className="border-b border-zinc-800/80">
                          <td className="px-3 py-3 font-medium text-zinc-100">
                            {formatSeccion(item)}
                          </td>
                          <td className="px-3 py-3 text-zinc-300">{item.anio_escolar}</td>
                          <td className="px-3 py-3 text-zinc-300">{formatTurno(item.turno)}</td>
                          <td className="px-3 py-3 text-zinc-300">
                            {item.tutor_nombre || "Sin tutor asignado"}
                          </td>
                          <td className="px-3 py-3 text-zinc-300">
                            {item.alumnos_matriculados}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {activeTab === "usuarios" && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <h2 className="text-lg font-semibold text-white">Usuarios del sistema</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Cuentas con acceso a PredictEdu (docentes y administradores).
                </p>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="border-b border-zinc-800 text-zinc-400">
                      <tr>
                        <th className="px-3 py-2">Usuario</th>
                        <th className="px-3 py-2">Rol</th>
                        <th className="px-3 py-2">Docente</th>
                        <th className="px-3 py-2">Ultimo acceso</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usuarios.map((item) => (
                        <tr key={item.id} className="border-b border-zinc-800/80">
                          <td className="px-3 py-3 text-zinc-100">{item.username}</td>
                          <td className="px-3 py-3 text-zinc-300">{item.rol}</td>
                          <td className="px-3 py-3 text-zinc-300">
                            {item.nombre_completo || "—"}
                          </td>
                          <td className="px-3 py-3 text-zinc-400">
                            {item.ultimo_acceso
                              ? new Date(item.ultimo_acceso).toLocaleString()
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {activeTab === "siagie" && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-white">Cargas SIAGIE</h2>
                    <p className="mt-1 text-sm text-zinc-400">
                      Historial de importaciones masivas y nueva carga desde aqui.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleUploadButtonClick}
                    disabled={uploading}
                    className="inline-flex items-center gap-2 rounded-xl border border-blue-600/40 bg-blue-600/10 px-4 py-2 text-sm text-blue-100 hover:bg-blue-600/20 disabled:opacity-50"
                  >
                    <IconUpload />
                    {uploading ? "Procesando..." : "Nueva carga SIAGIE"}
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </div>
                <div className="mt-4 space-y-2">
                  {cargas.length === 0 ? (
                    <p className="text-sm text-zinc-400">Aun no hay cargas registradas.</p>
                  ) : (
                    cargas.map((carga) => (
                      <div
                        key={carga.id}
                        className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3 text-sm"
                      >
                        <p className="font-medium text-zinc-100">{carga.nombre_archivo}</p>
                        <p className="mt-1 text-zinc-400">
                          {carga.filas_procesadas}/{carga.total_filas} estudiantes · errores{" "}
                          {carga.filas_error} · por {carga.subido_por || "—"}
                        </p>
                        <p className="text-xs text-zinc-500">
                          {new Date(carga.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </section>
            )}
          </>
        )}
      </section>
    </main>
  );
}
