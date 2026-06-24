const GRADE_OPTIONS = [
  { value: "AD", label: "AD", desc: "Logro destacado" },
  { value: "A", label: "A", desc: "Logro esperado" },
  { value: "B", label: "B", desc: "En proceso" },
  { value: "C", label: "C", desc: "En inicio" },
];

function attendanceTone(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return { bar: "bg-zinc-600", text: "text-zinc-400", label: "Sin dato" };
  if (n >= 85) return { bar: "bg-emerald-500", text: "text-emerald-300", label: "Buena asistencia" };
  if (n >= 70) return { bar: "bg-amber-500", text: "text-amber-300", label: "Asistencia regular" };
  return { bar: "bg-red-500", text: "text-red-300", label: "Asistencia baja" };
}

function participationLabel(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "Sin dato";
  if (n >= 8) return "Participación alta";
  if (n >= 5) return "Participación regular";
  return "Participación baja";
}

export function FormHint({ children }) {
  return <p className="text-xs leading-relaxed text-zinc-500">{children}</p>;
}

export function FormSection({ step, title, children, disabled = false }) {
  return (
    <fieldset
      disabled={disabled}
      className={`space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/40 p-4 ${
        disabled ? "opacity-50" : ""
      }`}
    >
      <legend className="flex items-center gap-2 px-1 text-sm font-medium text-zinc-200">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/20 text-xs text-blue-200">
          {step}
        </span>
        {title}
      </legend>
      {children}
    </fieldset>
  );
}

export function StudentFoundCard({ nombre, dni, seccion }) {
  const initials = (nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || "")
    .join("");

  return (
    <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-3 py-3">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-semibold text-emerald-100">
        {initials || "?"}
      </div>
      <div className="min-w-0">
        <p className="truncate font-medium text-zinc-100">{nombre}</p>
        <p className="text-xs text-zinc-400">
          DNI {dni}
          {seccion ? ` · ${seccion}` : ""}
        </p>
      </div>
      <span className="ml-auto shrink-0 rounded-full border border-emerald-500/40 px-2 py-0.5 text-xs text-emerald-200">
        Listo
      </span>
    </div>
  );
}

export function BimestrePills({ value, onChange }) {
  const selected = value ? String(value) : "";
  return (
    <div>
      <span className="mb-2 block text-xs text-zinc-400">Bimestre del año escolar</span>
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3, 4].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(String(n))}
            className={`rounded-lg border px-4 py-2 text-sm transition ${
              selected === String(n)
                ? "border-blue-500/50 bg-blue-500/15 text-blue-100"
                : "border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
            }`}
          >
            {n}° bimestre
          </button>
        ))}
      </div>
      {!selected && (
        <p className="mt-2 text-xs text-zinc-500">Sin bimestre — busca un alumno por DNI primero.</p>
      )}
    </div>
  );
}

export function AsistenciaSlider({ value, onChange }) {
  const isEmpty = value === "" || value === undefined || value === null;
  const numeric = isEmpty ? NaN : Number(value);
  const safe = Number.isNaN(numeric) ? 0 : Math.min(100, Math.max(0, numeric));
  const tone = attendanceTone(isEmpty ? NaN : safe);

  const setValue = (next) => {
    onChange({ target: { name: "asistencias", value: String(next) } });
  };

  if (isEmpty) {
    return (
      <div>
        <div className="mb-1 flex items-end justify-between gap-2">
          <span className="text-xs text-zinc-400">Asistencia a clases</span>
          <span className="text-lg font-semibold tabular-nums text-zinc-500">—</span>
        </div>
        <FormHint>
          Indica qué porcentaje de días asistió al colegio en este bimestre (de 0 a 100).
        </FormHint>
        <div className="mt-3 h-2 rounded-full bg-zinc-800/80" />
        <p className="mt-2 text-xs text-zinc-500">Sin dato — busca un alumno por DNI primero.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-1 flex items-end justify-between gap-2">
        <span className="text-xs text-zinc-400">Asistencia a clases</span>
        <span className={`text-lg font-semibold tabular-nums ${tone.text}`}>{safe}%</span>
      </div>
      <FormHint>
        Indica qué porcentaje de días asistió al colegio en este bimestre (de 0 a 100).
      </FormHint>
      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={safe}
        onChange={(e) => setValue(e.target.value)}
        className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full bg-zinc-800 accent-blue-500"
      />
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full rounded-full transition-all ${tone.bar}`} style={{ width: `${safe}%` }} />
      </div>
      <p className={`mt-2 text-xs ${tone.text}`}>{tone.label}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {[
          { v: 95, l: "Casi siempre" },
          { v: 85, l: "Habitual" },
          { v: 75, l: "Regular" },
          { v: 60, l: "Baja" },
        ].map((preset) => (
          <button
            key={preset.v}
            type="button"
            onClick={() => setValue(preset.v)}
            className={`rounded-lg border px-2.5 py-1 text-xs transition ${
              safe === preset.v
                ? "border-blue-500/50 bg-blue-500/10 text-blue-100"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-600"
            }`}
          >
            {preset.l} ({preset.v}%)
          </button>
        ))}
      </div>
    </div>
  );
}

export function ParticipacionSlider({ value, onChange }) {
  const isEmpty = value === "" || value === undefined || value === null;
  const numeric = isEmpty ? NaN : Number(value);
  const safe = Number.isNaN(numeric) ? 0 : Math.min(10, Math.max(0, numeric));

  const setValue = (next) => {
    onChange({ target: { name: "participacion", value: String(next) } });
  };

  if (isEmpty) {
    return (
      <div>
        <div className="mb-1 flex items-end justify-between gap-2">
          <span className="text-xs text-zinc-400">Participación en clase</span>
          <span className="text-lg font-semibold tabular-nums text-zinc-500">—</span>
        </div>
        <FormHint>
          Qué tan activo es el alumno: responde, participa y se involucra en las actividades.
        </FormHint>
        <div className="mt-3 h-2 rounded-full bg-zinc-800/80" />
        <p className="mt-2 text-xs text-zinc-500">Sin dato — busca un alumno por DNI primero.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-1 flex items-end justify-between gap-2">
        <span className="text-xs text-zinc-400">Participación en clase</span>
        <span className="text-lg font-semibold tabular-nums text-blue-200">{safe}/10</span>
      </div>
      <FormHint>Qué tan activo es el alumno: responde, participa y se involucra en las actividades.</FormHint>
      <input
        type="range"
        min={0}
        max={10}
        step={1}
        value={safe}
        onChange={(e) => setValue(e.target.value)}
        className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full bg-zinc-800 accent-blue-500"
      />
      <p className="mt-2 text-xs text-zinc-400">{participationLabel(safe)}</p>
      <div className="mt-2 flex justify-between text-[10px] text-zinc-600">
        <span>0 · Nada</span>
        <span>5 · A veces</span>
        <span>10 · Mucho</span>
      </div>
    </div>
  );
}

export function GradeChips({ label, name, value, onChange }) {
  const selected = value || "";
  return (
    <div>
      <span className="mb-2 block text-xs text-zinc-400">{label}</span>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {GRADE_OPTIONS.map((grade) => (
          <button
            key={grade.value}
            type="button"
            onClick={() => onChange({ target: { name, value: grade.value } })}
            className={`rounded-xl border px-2 py-2.5 text-left transition ${
              selected === grade.value
                ? "border-blue-500/50 bg-blue-500/15 ring-1 ring-blue-500/30"
                : "border-zinc-700 bg-zinc-900 hover:border-zinc-600"
            }`}
          >
            <span className="block text-sm font-semibold text-zinc-100">{grade.label}</span>
            <span className="block text-[10px] leading-tight text-zinc-500">{grade.desc}</span>
          </button>
        ))}
      </div>
      {!selected && (
        <p className="mt-2 text-xs text-zinc-500">Sin nota — busca un alumno por DNI primero.</p>
      )}
    </div>
  );
}

export function TextField({
  label,
  name,
  value,
  onChange,
  placeholder,
  hint,
  required,
  inputMode,
  maxLength,
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-400">{label}</span>
      {hint && <FormHint>{hint}</FormHint>}
      <input
        type="text"
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        inputMode={inputMode}
        maxLength={maxLength}
        className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-500/30"
      />
      {name === "dni" && value && (
        <p className="mt-1 text-[10px] text-zinc-500">{String(value).length}/8 dígitos</p>
      )}
    </label>
  );
}
