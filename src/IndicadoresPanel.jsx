export const MESES_LABELS = {
  1: "Enero",
  2: "Febrero",
  3: "Marzo",
  4: "Abril",
  5: "Mayo",
  6: "Junio",
  7: "Julio",
  8: "Agosto",
  9: "Septiembre",
  10: "Octubre",
  11: "Noviembre",
  12: "Diciembre",
};

export default function IndicadoresPanel({
  anio,
  mes,
  onAnioChange,
  onMesChange,
  indicadores,
  loading,
  message,
  onCalcular,
  esAdmin,
}) {
  return (
    <div className="space-y-4">
      {message && (
        <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {message}
        </p>
      )}

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
        <h2 className="text-base font-semibold text-white">Indicadores mensuales</h2>
        <p className="mt-1 text-sm text-zinc-500">
          {esAdmin
            ? "Vista institucional y por sección: riesgo de deserción, intervenciones y derivaciones."
            : "Resumen de tus secciones: quién está en riesgo y qué acciones se tomaron este mes."}
        </p>
        {!esAdmin && (
          <p className="mt-2 text-xs text-zinc-500">
            El total de toda la institución solo lo ve el administrador. El % de asistencia del alumno
            se registra al analizar en Resumen.
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Año</span>
            <input
              type="number"
              min="2020"
              max="2100"
              value={anio}
              onChange={(e) => onAnioChange(Number(e.target.value))}
              className="w-28 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Mes</span>
            <select
              value={mes}
              onChange={(e) => onMesChange(Number(e.target.value))}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              {Object.entries(MESES_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={onCalcular}
            disabled={loading}
            className="rounded-lg border border-blue-600/40 bg-blue-600/10 px-4 py-2 text-sm text-blue-100 disabled:opacity-60"
          >
            {loading ? "Calculando..." : "Calcular mes"}
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {!indicadores.length ? (
            <p className="text-sm text-zinc-500">
              Aún no hay indicadores para este período. Pulsa &quot;Calcular mes&quot;.
            </p>
          ) : (
            indicadores.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-zinc-100">{item.seccion_etiqueta}</p>
                  <p className="text-xs text-zinc-500">{item.total_estudiantes} alumnos</p>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <div>
                    <p className="text-xs text-zinc-500">Riesgo alto</p>
                    <div className="mt-1 h-2 rounded-full bg-zinc-800">
                      <div
                        className="h-2 rounded-full bg-red-500"
                        style={{ width: `${item.porcentaje_riesgo_alto || 0}%` }}
                      />
                    </div>
                    <p className="mt-1 text-sm text-red-200">{item.porcentaje_riesgo_alto}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Riesgo medio</p>
                    <div className="mt-1 h-2 rounded-full bg-zinc-800">
                      <div
                        className="h-2 rounded-full bg-amber-500"
                        style={{ width: `${item.porcentaje_riesgo_medio || 0}%` }}
                      />
                    </div>
                    <p className="mt-1 text-sm text-amber-200">{item.porcentaje_riesgo_medio}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Sin riesgo / bajo</p>
                    <div className="mt-1 h-2 rounded-full bg-zinc-800">
                      <div
                        className="h-2 rounded-full bg-emerald-500"
                        style={{ width: `${item.porcentaje_riesgo_bajo || 0}%` }}
                      />
                    </div>
                    <p className="mt-1 text-sm text-emerald-200">{item.porcentaje_riesgo_bajo}%</p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-zinc-500">
                  Asistencia prom.: {item.promedio_asistencia ?? "—"}% · Intervenciones:{" "}
                  {item.total_intervenciones} · Derivaciones: {item.total_derivaciones}
                </p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
