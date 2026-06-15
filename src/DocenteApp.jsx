import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  API_BASE,
  authFetch,
  authFetchJson,
} from "./apiClient";
import { IconLogout, IconUpload } from "./icons";

const initialForm = {
  dni: "",
  nombre: "",
  bimestre: "1",
  asistencias: "",
  nota_matematica: "A",
  nota_lenguaje: "A",
  participacion: "",
};

const initialStats = { alto: 0, medio: 0, bajo: 0 };

function apiErrorMessage(error) {
  if (error?.message === "Failed to fetch") {
    return "No se conecto con el motor Flask en 127.0.0.1:5000. Ejecuta: venv\\Scripts\\python.exe backend-sidecar\\app.py";
  }
  return error?.message || "Ocurrio un error inesperado.";
}

async function fetchJson(url, options) {
  return authFetchJson(url, options);
}

function buildInitials(nombre) {
  return (nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("") || "SN";
}

function mapLastPredictionToResult(last) {
  if (!last) return null;
  return {
    sourceLabel: "Historial del estudiante",
    prediction: last.prediction || last.etiqueta,
    confidence: last.confianza,
    nivel_riesgo: last.nivel_riesgo,
    storage: {
      persisted: true,
      estudiante_id: last.estudiante_id,
      prediccion_id: last.prediccion_id,
      auto_nombre: String(last.nombre || "").startsWith("Simulacion "),
    },
  };
}

function riskLabel(level) {
  if (level === "alto") return "Riesgo alto";
  if (level === "medio") return "Riesgo medio";
  return "Sin riesgo";
}

function riskTone(level) {
  if (level === "alto") return "red";
  if (level === "medio") return "orange";
  return "green";
}

export default function DocenteApp({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState("resumen");
  const [formData, setFormData] = useState(initialForm);
  const [stats, setStats] = useState(initialStats);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [alertsData, setAlertsData] = useState([]);
  const [studentsList, setStudentsList] = useState([]);
  const [interventionsList, setInterventionsList] = useState([]);
  const [activeStudent, setActiveStudent] = useState("");
  const [error, setError] = useState("");
  const [dbInfo, setDbInfo] = useState(null);
  const [searchMessage, setSearchMessage] = useState("");
  const [studentFilters, setStudentFilters] = useState({ busqueda: "", riesgo: "" });
  const [studentsTotal, setStudentsTotal] = useState(0);
  const [exporting, setExporting] = useState(false);
  const fileInputRef = useRef(null);
  const submitInFlightRef = useRef(false);

  const loadStudents = useCallback(async (filters = studentFilters) => {
    const params = new URLSearchParams();
    if (filters.busqueda.trim()) params.set("busqueda", filters.busqueda.trim());
    if (filters.riesgo) params.set("riesgo", filters.riesgo);

    const query = params.toString();
    const url = `${API_BASE}/api/estudiantes${query ? `?${query}` : ""}`;
    const estudiantesRes = await authFetch(url);
    if (estudiantesRes.ok) {
      const estudiantesData = await estudiantesRes.json();
      setStudentsList(estudiantesData.estudiantes || []);
      setStudentsTotal(estudiantesData.total ?? 0);
    }
  }, [studentFilters]);

  const refreshDashboard = useCallback(async () => {
    try {
      const [statusRes, resumenRes, intervencionesRes] = await Promise.all([
        authFetch(`${API_BASE}/api/status`),
        authFetch(`${API_BASE}/api/resumen`),
        authFetch(`${API_BASE}/api/intervenciones`),
      ]);

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setDbInfo((prev) => ({
          ...prev,
          ready: statusData.database?.ready ?? false,
          schemaVersion: statusData.database?.schema_version ?? 0,
          modelLoaded: statusData.model_loaded ?? false,
        }));
      }

      if (resumenRes.ok) {
        const resumenData = await resumenRes.json();
        setStats({
          alto: resumenData.summary?.alto ?? 0,
          medio: resumenData.summary?.medio ?? 0,
          bajo: resumenData.summary?.bajo ?? 0,
        });
        setDbInfo((prev) => ({
          ...prev,
          totalEstudiantes: resumenData.total_estudiantes ?? 0,
          totalPredicciones: resumenData.total_predicciones ?? 0,
          alertasActivas: resumenData.alertas_activas ?? 0,
        }));

        if (resumenData.alertas_prioritarias?.length) {
          setAlertsData(resumenData.alertas_prioritarias);
        } else {
          setAlertsData([]);
        }

        if (resumenData.ultima_prediccion) {
          setResult(mapLastPredictionToResult(resumenData.ultima_prediccion));
        }
      }

      if (intervencionesRes.ok) {
        const intervencionesData = await intervencionesRes.json();
        setInterventionsList(intervencionesData.intervenciones || []);
      }

      await loadStudents(studentFilters);
    } catch {
      setDbInfo((prev) => ({ ...prev, ready: false }));
    }
  }, [loadStudents, studentFilters]);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  useEffect(() => {
    if (activeTab === "estudiantes") {
      loadStudents(studentFilters);
    }
  }, [activeTab, studentFilters, loadStudents]);

  const handleStudentFilterChange = (event) => {
    const { name, value } = event.target;
    setStudentFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleExportReport = async (formato = "xlsx") => {
    setExporting(true);
    setError("");
    try {
      const params = new URLSearchParams({ formato });
      if (studentFilters.busqueda.trim()) {
        params.set("busqueda", studentFilters.busqueda.trim());
      }
      if (studentFilters.riesgo) {
        params.set("riesgo", studentFilters.riesgo);
      }

      const response = await authFetch(`${API_BASE}/api/reportes/exportar?${params}`);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "No se pudo exportar el reporte.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download =
        formato === "csv"
          ? "reporte_estudiantes_predictedu.csv"
          : "reporte_estudiantes_predictedu.xlsx";
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(apiErrorMessage(exportError));
    } finally {
      setExporting(false);
    }
  };

  const totalStudents = stats.alto + stats.medio + stats.bajo;
  const riskIsHigh = String(result?.prediction || "")
    .toLowerCase()
    .includes("alto");

  const motivationalMessage = riskIsHigh
    ? "Prioriza contacto con la familia y seguimiento semanal para reducir el riesgo de desercion."
    : "Buen pronostico: mantenga actividades participativas para consolidar este avance.";

  const barData = useMemo(
    () => [
      { label: "Riesgo alto", value: stats.alto, colorClass: "bg-red-500" },
      { label: "Riesgo medio", value: stats.medio, colorClass: "bg-orange-400" },
      { label: "Sin riesgo", value: stats.bajo, colorClass: "bg-emerald-500" },
    ],
    [stats]
  );

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const requestPrediction = async (payload, sourceLabel = "Formulario") => {
    if (submitInFlightRef.current) {
      return null;
    }
    submitInFlightRef.current = true;

    try {
      const data = await fetchJson(`${API_BASE}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!data.storage?.persisted && data.storage?.error) {
        throw new Error(data.storage.error);
      }

      setResult({ ...data, sourceLabel });
      await refreshDashboard();
      return data;
    } finally {
      submitInFlightRef.current = false;
    }
  };

  const handleClearForm = () => {
    setFormData(initialForm);
    setResult(null);
    setSearchMessage("");
    setError("");
  };

  const handleRegisterStudent = async () => {
    const dni = formData.dni.trim();
    const nombre = formData.nombre.trim();

    if (!dni || !nombre) {
      setError("Para registrar: DNI y nombre completo son obligatorios.");
      return;
    }

    setLoading(true);
    setError("");
    setSearchMessage("");

    try {
      const data = await fetchJson(`${API_BASE}/api/estudiantes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dni, nombre }),
      });
      setSearchMessage(`Alumno registrado: ${data.estudiante.nombre} (DNI ${data.estudiante.dni})`);
      await refreshDashboard();
    } catch (registerError) {
      setError(apiErrorMessage(registerError));
    } finally {
      setLoading(false);
    }
  };

  const handleSearchByDni = async () => {
    const dni = formData.dni.trim();
    if (!dni) {
      setSearchMessage("Ingresa un DNI para buscar.");
      return;
    }

    setSearchMessage("");
    setError("");

    try {
      const response = await authFetch(
        `${API_BASE}/api/estudiantes/buscar?dni=${encodeURIComponent(dni)}`
      );
      const data = await response.json();

      if (response.status === 404) {
        setSearchMessage(`DNI ${dni} no registrado. Puedes crear un analisis nuevo.`);
        return;
      }

      if (!response.ok) {
        throw new Error(data.error || "No se pudo buscar el estudiante.");
      }

      const student = data.estudiante;
      setFormData((prev) => ({
        ...prev,
        dni: student.dni || dni,
        nombre: student.nombre || prev.nombre,
        bimestre: String(student.bimestre || prev.bimestre || "1"),
        asistencias: student.asistencias ?? prev.asistencias,
        nota_matematica: student.nota_matematica || prev.nota_matematica,
        nota_lenguaje: student.nota_lenguaje || prev.nota_lenguaje,
        participacion: student.participacion ?? prev.participacion,
      }));
      setSearchMessage(`Alumno encontrado: ${student.nombre}`);
    } catch (searchError) {
      setError(apiErrorMessage(searchError));
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitInFlightRef.current || loading) {
      return;
    }

    const dni = formData.dni.trim();
    const nombre = formData.nombre.trim();

    if (!dni) {
      setError("Ingresa el DNI del alumno. Si es nuevo, registrlo primero.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const payload = {
        dni,
        nombre: nombre || undefined,
        bimestre: Number(formData.bimestre) || 1,
        asistencias: Number(formData.asistencias),
        nota_matematica: formData.nota_matematica,
        nota_lenguaje: formData.nota_lenguaje,
        participacion: Number(formData.participacion),
      };
      await requestPrediction(payload, "Formulario manual");
    } catch (submitError) {
      setError(apiErrorMessage(submitError));
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterIntervention = async (student) => {
    if (!student.estudiante_id && !student.id) {
      setError("Este alumno aun no esta registrado en el sistema.");
      return;
    }

    setLoading(true);
    setError("");
    setActiveStudent(student.nombre);

    try {
      await fetchJson(`${API_BASE}/api/intervenciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          estudiante_id: student.estudiante_id || student.id,
          prediccion_id: student.prediccion_id,
          titulo: `Seguimiento — ${student.nombre}`,
          tipo: "contacto_familia",
          descripcion: "Accion registrada desde el panel de alertas prioritarias.",
        }),
      });

      await refreshDashboard();
      setActiveTab("intervenciones");
    } catch (interventionError) {
      setError(apiErrorMessage(interventionError));
    } finally {
      setLoading(false);
      setActiveStudent("");
    }
  };

  const handleUploadButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");

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

      setResult({
        sourceLabel: "Carga SIAGIE",
        prediction: data.summary?.alto > data.summary?.bajo ? "Alto Riesgo" : "Bajo Riesgo",
        confidence: data.total_students ? data.summary?.alto / data.total_students : 0,
        storage: data.storage,
      });

      await refreshDashboard();
    } catch (uploadError) {
      setError(uploadError.message || "Error al subir el archivo.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 px-5 py-8 text-zinc-100">
      <section className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 shadow-xl shadow-black/30 md:flex-row md:items-start">
          <div>
            <p className="text-sm text-zinc-400">Modo docente · I.E.I. N° 32857 — Huacalle</p>
            <h1 className="mt-1 text-4xl font-semibold text-white">PredictEdu</h1>
            <p className="mt-2 text-xs text-zinc-500">
              Analisis de riesgo, alertas e intervenciones de tu aula
            </p>
            {dbInfo && (
              <div className="mt-3 flex flex-wrap gap-2">
                <StatusPill
                  label={`${user.nombre_completo || user.username} · docente`}
                  tone="blue"
                />
                <StatusPill
                  label={dbInfo.ready ? "Sistema en linea" : "Sin conexion"}
                  tone={dbInfo.ready ? "green" : "red"}
                />
                <StatusPill label={`${dbInfo.totalEstudiantes ?? 0} estudiantes`} tone="blue" />
                <StatusPill label={`${dbInfo.totalPredicciones ?? 0} predicciones`} tone="blue" />
                {dbInfo.alertasActivas > 0 && (
                  <StatusPill
                    label={`${dbInfo.alertasActivas} alertas activas`}
                    tone="orange"
                  />
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 hover:bg-zinc-700"
            >
              <IconLogout />
              Cerrar sesion
            </button>
            <button
              type="button"
              onClick={handleUploadButtonClick}
              disabled={uploading}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <IconUpload />
              {uploading ? "Procesando SIAGIE..." : "Cargar SIAGIE"}
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileUpload}
            className="hidden"
          />
        </header>

        <nav className="mb-6 flex gap-3">
          <Tab
            label="Resumen"
            active={activeTab === "resumen"}
            onClick={() => setActiveTab("resumen")}
          />
          <Tab
            label="Estudiantes"
            active={activeTab === "estudiantes"}
            onClick={() => setActiveTab("estudiantes")}
          />
          <Tab
            label="Intervenciones"
            active={activeTab === "intervenciones"}
            onClick={() => setActiveTab("intervenciones")}
          />
        </nav>

        {activeTab === "resumen" && (
          <>
            <section className="mb-6 grid gap-4 md:grid-cols-3">
              <SummaryCard title="Riesgo alto" value={stats.alto} subtitle="estudiantes" tone="red" />
              <SummaryCard title="Riesgo medio" value={stats.medio} subtitle="estudiantes" tone="orange" />
              <SummaryCard title="Sin riesgo" value={stats.bajo} subtitle="estudiantes" tone="green" />
            </section>

            <section className="grid gap-6 lg:grid-cols-3">
              <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5 lg:col-span-2">
                <h2 className="text-lg font-semibold text-white">
                  Distribucion de riesgo — {totalStudents} estudiantes total
                </h2>
                <div className="mt-5 space-y-4">
                  {barData.map((item) => {
                    const percent = totalStudents ? (item.value / totalStudents) * 100 : 0;
                    return (
                      <div key={item.label}>
                        <div className="mb-1 flex items-center justify-between text-sm text-zinc-300">
                          <span>{item.label}</span>
                          <span>{item.value}</span>
                        </div>
                        <div className="h-3 w-full overflow-hidden rounded-full bg-zinc-800">
                          <div
                            className={`h-full rounded-full ${item.colorClass}`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </article>

              <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
                <h2 className="text-lg font-semibold text-white">Simular analisis</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  1) Registra o busca por DNI · 2) Completa notas · 3) Analiza una sola vez
                </p>
                <form onSubmit={handleSubmit} className="mt-4 space-y-3">
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <InputField
                        label="DNI del estudiante"
                        name="dni"
                        value={formData.dni}
                        onChange={handleInputChange}
                        type="text"
                        placeholder="Ej: 72345678"
                        required
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleSearchByDni}
                      disabled={loading}
                      className="mt-5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-60"
                    >
                      Buscar
                    </button>
                  </div>
                  {searchMessage && (
                    <p className="text-xs text-blue-200">{searchMessage}</p>
                  )}
                  <InputField
                    label="Nombre completo"
                    name="nombre"
                    value={formData.nombre}
                    onChange={handleInputChange}
                    type="text"
                    placeholder="Ej: Juanito Perez Garcia"
                  />
                  <button
                    type="button"
                    onClick={handleRegisterStudent}
                    disabled={loading}
                    className="w-full rounded-lg border border-emerald-600/40 bg-emerald-600/10 px-4 py-2 text-sm font-medium text-emerald-200 hover:bg-emerald-600/20 disabled:opacity-60"
                  >
                    Registrar alumno (solo DNI + nombre)
                  </button>
                  <InputField
                    label="Bimestre (1-4)"
                    name="bimestre"
                    value={formData.bimestre}
                    onChange={handleInputChange}
                    min="1"
                    max="4"
                  />
                  <InputField
                    label="Asistencia (%)"
                    name="asistencias"
                    value={formData.asistencias}
                    onChange={handleInputChange}
                    min="0"
                    max="100"
                  />
                  <InputField
                    label="Nota Matematica"
                    name="nota_matematica"
                    value={formData.nota_matematica}
                    onChange={handleInputChange}
                    type="select"
                  />
                  <InputField
                    label="Nota Lenguaje"
                    name="nota_lenguaje"
                    value={formData.nota_lenguaje}
                    onChange={handleInputChange}
                    type="select"
                  />
                  <InputField
                    label="Participacion"
                    name="participacion"
                    value={formData.participacion}
                    onChange={handleInputChange}
                    min="0"
                    max="10"
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={loading || submitInFlightRef.current}
                      className="flex-1 rounded-xl bg-blue-500 px-4 py-2.5 font-medium text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-blue-800"
                    >
                      {loading ? "Analizando..." : "Analizar y guardar"}
                    </button>
                    {result?.sourceLabel === "Formulario manual" && (
                      <button
                        type="button"
                        onClick={handleClearForm}
                        disabled={loading}
                        className="rounded-xl border border-zinc-600 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-zinc-700 disabled:opacity-60"
                      >
                        Limpiar
                      </button>
                    )}
                  </div>
                </form>
                <p className="mt-3 text-xs text-zinc-500">
                  Carga masiva: usa docs/siagie_demo_5toA.xlsx o el prompt en docs/PROMPT_SIAGIE.md
                </p>
              </article>
            </section>

            <section className="mt-6 grid gap-6 lg:grid-cols-3">
              <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5 lg:col-span-2">
                <h2 className="text-lg font-semibold text-white">
                  Alertas prioritarias — accion inmediata
                </h2>
                <div className="mt-4 space-y-3">
                  {alertsData.length === 0 ? (
                    <p className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-400">
                      No hay alertas activas. Las predicciones de riesgo alto o medio generan
                      alertas automaticamente.
                    </p>
                  ) : (
                    alertsData.map((student) => (
                      <div
                        key={`${student.alerta_id || student.nombre}-${student.estudiante_id}`}
                        className="flex flex-col gap-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 md:flex-row md:items-center md:justify-between"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-200">
                            {student.iniciales || buildInitials(student.nombre)}
                          </div>
                          <div>
                            <p className="font-medium text-zinc-100">{student.nombre}</p>
                            <p className="text-sm text-zinc-400">
                              Asistencia {student.asistencias}% · Mat {student.nota_matematica} ·
                              Leng {student.nota_lenguaje}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="rounded-full border border-red-500/40 bg-red-500/20 px-3 py-1 text-xs font-medium text-red-200">
                            {riskLabel(student.risk_level || student.ultimo_nivel_riesgo)}
                          </span>
                          <button
                            onClick={() => handleRegisterIntervention(student)}
                            disabled={loading}
                            className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {loading && activeStudent === student.nombre
                              ? "Guardando..."
                              : "Registrar accion"}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </article>

              <ResultPanel
                result={result}
                error={error}
                riskIsHigh={riskIsHigh}
                motivationalMessage={motivationalMessage}
                onClear={result?.sourceLabel === "Formulario manual" ? handleClearForm : null}
              />
            </section>
          </>
        )}

        {activeTab === "estudiantes" && (
          <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">
                  Estudiantes registrados — {studentsTotal}
                </h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Filtra por nombre/DNI o nivel de riesgo. Exporta para reportes UGEL o dirección.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleExportReport("xlsx")}
                  disabled={exporting || studentsTotal === 0}
                  className="rounded-lg border border-blue-600/40 bg-blue-600/10 px-3 py-2 text-sm text-blue-100 hover:bg-blue-600/20 disabled:opacity-50"
                >
                  {exporting ? "Exportando..." : "Exportar reporte"}
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <label className="block md:col-span-2">
                <span className="mb-1 block text-xs text-zinc-400">Buscar por DNI o nombre</span>
                <input
                  type="text"
                  name="busqueda"
                  value={studentFilters.busqueda}
                  onChange={handleStudentFilterChange}
                  placeholder="Ej: Mendoza o 72345601"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-400"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-zinc-400">Filtrar por riesgo</span>
                <select
                  name="riesgo"
                  value={studentFilters.riesgo}
                  onChange={handleStudentFilterChange}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-400"
                >
                  <option value="">Todos</option>
                  <option value="alto">Riesgo alto</option>
                  <option value="medio">Riesgo medio</option>
                  <option value="bajo">Sin riesgo / bajo</option>
                </select>
              </label>
            </div>

            {studentsList.length === 0 ? (
              <p className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-400">
                {studentsTotal === 0
                  ? "Aun no hay estudiantes. Registra uno o carga un archivo SIAGIE."
                  : "Ningun estudiante coincide con los filtros aplicados."}
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-zinc-800 text-zinc-400">
                    <tr>
                      <th className="px-3 py-2">DNI</th>
                      <th className="px-3 py-2">Estudiante</th>
                      <th className="px-3 py-2">Asistencia</th>
                      <th className="px-3 py-2">Notas</th>
                      <th className="px-3 py-2">Riesgo</th>
                      <th className="px-3 py-2">Ultima prediccion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {studentsList.map((student) => (
                      <tr key={student.id} className="border-b border-zinc-800/80">
                        <td className="px-3 py-3 text-zinc-400">{student.dni || "—"}</td>
                        <td className="px-3 py-3 font-medium text-zinc-100">{student.nombre}</td>
                        <td className="px-3 py-3 text-zinc-300">{student.asistencias ?? "—"}%</td>
                        <td className="px-3 py-3 text-zinc-300">
                          Mat {student.nota_matematica ?? "—"} · Leng{" "}
                          {student.nota_lenguaje ?? "—"}
                        </td>
                        <td className="px-3 py-3">
                          <RiskBadge level={student.ultimo_nivel_riesgo} />
                        </td>
                        <td className="px-3 py-3 text-zinc-400">
                          {student.ultima_prediccion
                            ? new Date(student.ultima_prediccion).toLocaleString()
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {activeTab === "intervenciones" && (
          <section className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
            <h2 className="text-lg font-semibold text-white">
              Intervenciones registradas — {interventionsList.length}
            </h2>
            <p className="mt-1 text-sm text-zinc-400">
              Acciones docentes guardadas desde el panel de alertas.
            </p>
            {interventionsList.length === 0 ? (
              <p className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-400">
                No hay intervenciones aun. Usa &quot;Registrar accion&quot; en una alerta prioritaria.
              </p>
            ) : (
              <div className="mt-4 space-y-3">
                {interventionsList.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-zinc-100">{item.titulo}</p>
                      <span className="rounded-full border border-zinc-700 px-3 py-1 text-xs text-zinc-300">
                        {item.estado}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-zinc-400">{item.nombre_estudiante}</p>
                    <p className="mt-2 text-xs text-zinc-500">
                      {new Date(item.created_at).toLocaleString()} · {item.tipo}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </section>
    </main>
  );
}

function ResultPanel({ result, error, riskIsHigh, motivationalMessage, onClear }) {
  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Resultado del motor</h2>
          <p className="mt-1 text-sm text-zinc-400">Se restaura al recargar si hay historial en BD.</p>
        </div>
        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="shrink-0 rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 hover:bg-zinc-700"
          >
            Limpiar
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {result ? (
        <div
          className={`mt-4 rounded-xl border p-4 ${
            riskIsHigh
              ? "border-red-500/40 bg-red-500/10"
              : "border-emerald-500/40 bg-emerald-500/10"
          }`}
        >
          <p className="text-xs uppercase tracking-wide text-zinc-400">{result.sourceLabel}</p>
          <p
            className={`mt-2 text-2xl font-semibold ${
              riskIsHigh ? "text-red-300" : "text-emerald-300"
            }`}
          >
            {riskIsHigh ? "Riesgo Alto" : "Riesgo Bajo"}
          </p>
          <p className="mt-2 text-sm text-zinc-200">
            Confianza:{" "}
            {typeof result.confidence === "number"
              ? `${(result.confidence * 100).toFixed(1)}%`
              : "No disponible"}
          </p>
          <p className="mt-3 text-sm text-zinc-100">{motivationalMessage}</p>
          {result.storage?.persisted ? (
            <p className="mt-3 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs text-blue-100">
              Analisis guardado en el historial del estudiante.
              {result.storage.alerta_id ? " Se genero una alerta de seguimiento." : ""}
            </p>
          ) : result.storage?.error ? (
            <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
              {result.storage.error}
            </p>
          ) : null}
          {result.storage?.carga_siagie_id ? (
            <p className="mt-3 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs text-blue-100">
              Carga SIAGIE registrada · {result.storage.filas_guardadas} estudiantes importados
              correctamente.
            </p>
          ) : null}
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 text-sm text-zinc-400">
          Aun no hay predicciones guardadas. Ejecuta un analisis para crear el historial.
        </div>
      )}
    </article>
  );
}

function RiskBadge({ level }) {
  const styles = {
    alto: "border-red-500/40 bg-red-500/20 text-red-200",
    medio: "border-orange-500/40 bg-orange-500/20 text-orange-200",
    bajo: "border-emerald-500/40 bg-emerald-500/20 text-emerald-200",
  };
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-medium ${
        styles[level] || "border-zinc-700 text-zinc-300"
      }`}
    >
      {riskLabel(level || "bajo")}
    </span>
  );
}

function SummaryCard({ title, value, subtitle, tone }) {
  const toneStyles = {
    red: "text-red-400",
    orange: "text-orange-400",
    green: "text-emerald-400",
  };

  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
      <p className="text-sm text-zinc-400">{title}</p>
      <p className={`mt-2 text-5xl font-semibold ${toneStyles[tone]}`}>{value}</p>
      <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>
    </article>
  );
}

function StatusPill({ label, tone }) {
  const toneStyles = {
    green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
    red: "border-red-500/40 bg-red-500/10 text-red-200",
    blue: "border-blue-500/40 bg-blue-500/10 text-blue-100",
    orange: "border-orange-500/40 bg-orange-500/10 text-orange-100",
  };

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-medium ${toneStyles[tone]}`}
    >
      {label}
    </span>
  );
}

function Tab({ label, active = false, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm transition ${
        active
          ? "border-zinc-500 bg-zinc-800 text-zinc-100"
          : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
      }`}
    >
      {label}
    </button>
  );
}

function InputField({
  label,
  name,
  value,
  onChange,
  min,
  max,
  type = "number",
  placeholder,
  required = false,
}) {
  if (type === "text") {
    return (
      <label className="block">
        <span className="mb-1 block text-xs text-zinc-400">{label}</span>
        <input
          type="text"
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-zinc-100 outline-none transition focus:border-blue-400"
        />
      </label>
    );
  }

  if (type === "select") {
    return (
      <label className="block">
        <span className="mb-1 block text-xs text-zinc-400">{label}</span>
        <select
          name={name}
          value={value}
          onChange={onChange}
          required
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-zinc-100 outline-none transition focus:border-blue-400"
        >
          <option value="AD">AD</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>
      </label>
    );
  }

  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-400">{label}</span>
      <input
        type="number"
        name={name}
        value={value}
        onChange={onChange}
        min={min}
        max={max}
        step="any"
        required
        className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-zinc-100 outline-none transition focus:border-blue-400"
      />
    </label>
  );
}

