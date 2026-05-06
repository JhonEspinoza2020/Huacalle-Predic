import { useMemo, useRef, useState } from "react";

const initialForm = {
  asistencias: "",
  nota_matematica: "A",
  nota_lenguaje: "A",
  participacion: "",
};

const initialStats = { alto: 4, medio: 7, bajo: 21 };

const alertStudents = [
  {
    nombre: "Luis Mendoza",
    iniciales: "LM",
    asistencias: 42,
    nota_matematica: "C",
    nota_lenguaje: "B",
    participacion: 3,
  },
  {
    nombre: "Camila Rojas",
    iniciales: "CR",
    asistencias: 58,
    nota_matematica: "B",
    nota_lenguaje: "B",
    participacion: 4,
  },
  {
    nombre: "Diego Huaman",
    iniciales: "DH",
    asistencias: 63,
    nota_matematica: "B",
    nota_lenguaje: "C",
    participacion: 5,
  },
];

function App() {
  const [formData, setFormData] = useState(initialForm);
  const [stats, setStats] = useState(initialStats);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [alertsData, setAlertsData] = useState(alertStudents);
  const [activeStudent, setActiveStudent] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const totalStudents = stats.alto + stats.medio + stats.bajo;
  const riskIsHigh = String(result?.prediction || "")
    .toLowerCase()
    .includes("alto");

  const motivationalMessage = riskIsHigh
    ? "Prioriza contacto con la familia y seguimiento semanal para reducir el riesgo de desercion."
    : "Buen pronostico: mantenga actividades participativas para consolidar este avance.";

  const barData = useMemo(
    () => [
      {
        label: "Riesgo alto",
        value: stats.alto,
        colorClass: "bg-red-500",
      },
      {
        label: "Riesgo medio",
        value: stats.medio,
        colorClass: "bg-orange-400",
      },
      {
        label: "Sin riesgo",
        value: stats.bajo,
        colorClass: "bg-emerald-500",
      },
    ],
    [stats]
  );

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const classifyRisk = (prediction, confidence) => {
    const predictedHigh = String(prediction || "")
      .toLowerCase()
      .includes("alto");
    if (predictedHigh) return "alto";
    if (typeof confidence === "number" && confidence >= 0.5 && confidence < 0.75) {
      return "medio";
    }
    return "bajo";
  };

  const requestPrediction = async (payload, sourceLabel = "Formulario") => {
    const response = await fetch("http://127.0.0.1:5000/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("No se pudo obtener una prediccion del servidor Flask.");
    }

    const data = await response.json();
    const bucket = classifyRisk(data.prediction, data.confidence);

    setStats((prev) => ({
      ...prev,
      [bucket]: prev[bucket] + 1,
    }));
    setResult({ ...data, sourceLabel });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload = {
        asistencias: Number(formData.asistencias),
        nota_matematica: formData.nota_matematica,
        nota_lenguaje: formData.nota_lenguaje,
        participacion: Number(formData.participacion),
      };
      await requestPrediction(payload, "Formulario manual");
      setFormData(initialForm);
    } catch (submitError) {
      setError(submitError.message || "Ocurrio un error inesperado.");
    } finally {
      setLoading(false);
    }
  };

  const handleStudentAction = async (student) => {
    setLoading(true);
    setError("");
    setActiveStudent(student.nombre);
    try {
      await requestPrediction(
        {
          asistencias: student.asistencias,
          nota_matematica: student.nota_matematica,
          nota_lenguaje: student.nota_lenguaje,
          participacion: student.participacion,
        },
        `Alerta: ${student.nombre}`
      );
    } catch (studentError) {
      setError(studentError.message || "No se pudo analizar el alumno.");
    } finally {
      setLoading(false);
      setActiveStudent("");
    }
  };

  const handleUploadButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");

    try {
      const formDataUpload = new FormData();
      formDataUpload.append("file", file);

      const response = await fetch("http://127.0.0.1:5000/api/upload_siagie", {
        method: "POST",
        body: formDataUpload,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "No se pudo procesar el archivo SIAGIE.");
      }

      setStats({
        alto: data.summary?.alto ?? 0,
        medio: data.summary?.medio ?? 0,
        bajo: data.summary?.bajo ?? 0,
      });

      const mappedAlerts = (data.top_5_high_risk || []).map((student) => {
        const safeName = student.nombre || "Sin nombre";
        const initials = safeName
          .split(" ")
          .filter(Boolean)
          .slice(0, 2)
          .map((part) => part[0]?.toUpperCase() || "")
          .join("");

        return {
          ...student,
          nombre: safeName,
          iniciales: initials || "SN",
        };
      });

      if (mappedAlerts.length) {
        setAlertsData(mappedAlerts);
      }

      setResult({
        sourceLabel: "Carga SIAGIE",
        prediction: data.summary?.alto > data.summary?.bajo ? "Alto Riesgo" : "Bajo Riesgo",
        confidence: data.total_students ? data.summary?.alto / data.total_students : 0,
      });
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
            <p className="text-sm text-zinc-400">I.E.I. N° 32857 — Huacalle</p>
            <h1 className="mt-1 text-4xl font-semibold text-white">PredictEdu</h1>
            <p className="mt-2 text-xs text-zinc-500">
              Ultima actualizacion: 26/04/2026 13:06
            </p>
          </div>

          <button
            onClick={handleUploadButtonClick}
            disabled={uploading}
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <span className="text-base">↗</span>
            {uploading ? "Procesando SIAGIE..." : "+ Cargar SIAGIE"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileUpload}
            className="hidden"
          />
        </header>

        <nav className="mb-6 flex gap-3">
          <Tab label="Resumen" active />
          <Tab label="Estudiantes" />
          <Tab label="Intervenciones" />
        </nav>

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
              Completa los campos y presiona analizar.
            </p>
            <form onSubmit={handleSubmit} className="mt-4 space-y-3">
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
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-blue-500 px-4 py-2.5 font-medium text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-blue-800"
              >
                {loading ? "Analizando..." : "Analizar"}
              </button>
            </form>
          </article>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5 lg:col-span-2">
            <h2 className="text-lg font-semibold text-white">
              Alertas prioritarias — accion inmediata
            </h2>
            <div className="mt-4 space-y-3">
              {alertsData.map((student) => (
                <div
                  key={student.nombre}
                  className="flex flex-col gap-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-200">
                      {student.iniciales}
                    </div>
                    <div>
                      <p className="font-medium text-zinc-100">{student.nombre}</p>
                      <p className="text-sm text-zinc-400">
                        Asistencia {student.asistencias}% · Mat {student.nota_matematica} · Leng{" "}
                        {student.nota_lenguaje}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-red-500/40 bg-red-500/20 px-3 py-1 text-xs font-medium text-red-200">
                      {student.risk_level === "medio" ? "Riesgo medio" : "Riesgo alto"}
                    </span>
                    <button
                      onClick={() => handleStudentAction(student)}
                      disabled={loading}
                      className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {loading && activeStudent === student.nombre
                        ? "Analizando..."
                        : "Registrar accion"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-5">
            <h2 className="text-lg font-semibold text-white">Resultado del motor</h2>
            <p className="mt-1 text-sm text-zinc-400">
              Prediccion en vivo desde Flask.
            </p>

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
                <p className="text-xs uppercase tracking-wide text-zinc-400">
                  {result.sourceLabel}
                </p>
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
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 text-sm text-zinc-400">
                Aun no hay predicciones. Ejecuta un analisis para actualizar este panel.
              </div>
            )}
          </article>
        </section>
      </section>
    </main>
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

function Tab({ label, active = false }) {
  return (
    <button
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

function InputField({ label, name, value, onChange, min, max, type = "number" }) {
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

export default App;
