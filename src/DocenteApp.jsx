import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  API_BASE,
  authFetch,
  authFetchJson,
} from "./apiClient";
import { IconLogout, IconUpload } from "./icons";
import IndicadoresPanel, { MESES_LABELS } from "./IndicadoresPanel";
import {
  sanitizeDniInput,
  validateAsistencias,
  validateDni,
  validateNombre,
  validateParticipacion,
  validateParentesco,
  validateDniOpcional,
  validateSeccionRequerida,
  sanitizeTelefonoInput,
} from "./validators";
import {
  AsistenciaSlider,
  BimestrePills,
  FormHint,
  FormSection,
  GradeChips,
  ParticipacionSlider,
  StudentFoundCard,
  TextField,
} from "./docenteForm";

const initialForm = {
  dni: "",
  nombre: "",
  bimestre: "1",
  asistencias: "",
  nota_matematica: "",
  nota_lenguaje: "",
  participacion: "",
  competencias: {
    personal_social: "",
    ciencia_tecnologia: "",
    arte_cultura: "",
    educacion_fisica: "",
  },
};

const COMPETENCIAS_OPCIONALES = [
  { key: "personal_social", label: "Personal social" },
  { key: "ciencia_tecnologia", label: "Ciencia y tecnología" },
  { key: "arte_cultura", label: "Arte y cultura" },
  { key: "educacion_fisica", label: "Educación física" },
];

const defaultStudentMetrics = {
  bimestre: "1",
  asistencias: "85",
  nota_matematica: "A",
  nota_lenguaje: "A",
  participacion: "7",
};

const initialRegisterForm = {
  dni: "",
  nombre: "",
};

const initialRegisterApoderado = {
  nombre: "",
  telefono: "",
  parentesco: "apoderado",
  dni: "",
};

const PARENTESCO_LABELS = {
  padre: "Padre",
  madre: "Madre",
  apoderado: "Apoderado",
  tutor: "Tutor",
  otro: "Otro",
};

const initialStats = { alto: 0, medio: 0, bajo: 0 };

const INTERVENCION_TIPO_LABELS = {
  contacto_familia: "Contacto con familia",
  tutoria: "Tutoría",
  reforzamiento: "Reforzamiento",
  derivacion_ugel: "Derivación UGEL",
  entrevista_psicologica: "Entrevista psicológica",
  otro: "Otra acción",
};

const INTERVENCION_ESTADO_LABELS = {
  pendiente: "Pendiente",
  en_curso: "En curso",
  cerrada: "Realizada",
  cancelada: "Cancelada",
};

const ALERTA_ESTADO_LABELS = {
  nueva: "Nueva",
  en_revision: "En revisión",
  atendida: "Atendida",
  cerrada: "Cerrada",
};

const SEGUIMIENTO_ACCION_LABELS = {
  en_revision: "Marcada en revisión",
  registro_intervencion: "Intervención registrada",
  atencion_registrada: "Atención registrada",
  cambio_estado_cerrada: "Alerta cerrada",
  cambio_estado_en_revision: "Paso a revisión",
  cambio_estado_atendida: "Marcada atendida",
  contacto_familia: "Contacto con familia",
};

const MOTIVO_INSCRIPCION_LABELS = {
  riesgo_alto: "Riesgo alto",
  riesgo_medio: "Riesgo medio",
  bajo_rendimiento: "Bajo rendimiento",
  baja_asistencia: "Baja asistencia",
  otro: "Otro motivo",
};

const RESULTADO_INSCRIPCION_LABELS = {
  mejoro: "Mejoró",
  sin_cambio: "Sin cambio",
  deserto: "Deserto",
  en_proceso: "En proceso",
};

const AREA_CURSO_LABELS = {
  matematica: "Matemática",
  comunicacion: "Comunicación",
  ciencias: "Ciencias",
  personal_social: "Personal social",
  integral: "Integral",
};

const ENTIDAD_DESTINO_LABELS = {
  ugel: "UGEL",
  demuna: "DEMUNA",
  salud: "Salud / ESSALUD",
  psicologia: "Psicología escolar",
  defensoria: "Defensoria del Pueblo",
  otro: "Otra entidad",
};

const ESTADO_DERIVACION_LABELS = {
  pendiente: "Pendiente",
  aceptada: "Aceptada",
  en_proceso: "En proceso",
  cerrada: "Cerrada",
  rechazada: "Rechazada",
};

const TIPO_INCIDENCIA_LABELS = {
  bullying: "Bullying",
  violencia: "Violencia",
  falta_disciplina: "Falta de disciplina",
  inasistencia_reiterada: "Inasistencia reiterada",
  afectacion_emocional: "Afectación emocional",
  otro: "Otro",
};

const SEVERIDAD_LABELS = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  critica: "Crítica",
};

const initialDerivacionForm = {
  estudiante_id: "",
  entidad_destino: "ugel",
  motivo: "",
  intervencion_id: "",
  observaciones: "",
};

const initialIncidenciaForm = {
  estudiante_id: "",
  tipo_incidencia: "bullying",
  severidad: "media",
  descripcion: "",
  acciones_tomadas: "",
  fecha_incidencia: "",
};

function apiErrorMessage(error) {
  if (error?.message === "Failed to fetch") {
    return "No se conectó con el motor Flask en 127.0.0.1:5000. Ejecuta: venv\\Scripts\\python.exe backend-sidecar\\app.py";
  }
  return error?.message || "Ocurrió un error inesperado.";
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

function resolveResultRiskLevel(result) {
  if (!result) return "bajo";
  if (result.nivel_riesgo) return result.nivel_riesgo;
  if (result.storage?.nivel_riesgo) return result.storage.nivel_riesgo;
  return String(result.prediction || "").toLowerCase().includes("alto") ? "alto" : "bajo";
}

function resultRiskStyles(level) {
  if (level === "alto") {
    return {
      box: "border-red-500/40 bg-red-500/10",
      text: "text-red-300",
    };
  }
  if (level === "medio") {
    return {
      box: "border-orange-500/40 bg-orange-500/10",
      text: "text-orange-300",
    };
  }
  return {
    box: "border-emerald-500/40 bg-emerald-500/10",
    text: "text-emerald-300",
  };
}

function motivationalText(level) {
  if (level === "alto") {
    return "Prioriza contacto con la familia y seguimiento semanal para reducir el riesgo de deserción.";
  }
  if (level === "medio") {
    return "Riesgo moderado: refuerza seguimiento en clase y manten contacto con la familia.";
  }
  return "Buen pronóstico: mantén actividades participativas para consolidar este avance.";
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

function formatDateInput(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultInterventionFilters() {
  const hasta = new Date();
  const desde = new Date(hasta.getFullYear(), hasta.getMonth(), 1);
  return { desde: formatDateInput(desde), hasta: formatDateInput(hasta) };
}

function interventionPresetRange(preset) {
  const hasta = new Date();
  if (preset === "mes") {
    return {
      desde: formatDateInput(new Date(hasta.getFullYear(), hasta.getMonth(), 1)),
      hasta: formatDateInput(hasta),
    };
  }
  if (preset === "30d") {
    const desde = new Date(hasta);
    desde.setDate(desde.getDate() - 29);
    return { desde: formatDateInput(desde), hasta: formatDateInput(hasta) };
  }
  if (preset === "90d") {
    const desde = new Date(hasta);
    desde.setDate(desde.getDate() - 89);
    return { desde: formatDateInput(desde), hasta: formatDateInput(hasta) };
  }
  return defaultInterventionFilters();
}

function formatInterventionPeriod(filters) {
  if (!filters.desde && !filters.hasta) return "todas las fechas";
  if (filters.desde && filters.hasta) {
    return `${filters.desde} al ${filters.hasta}`;
  }
  if (filters.desde) return `desde ${filters.desde}`;
  return `hasta ${filters.hasta}`;
}

function inferMotivoInscripcion(student) {
  const nivel = student.risk_level || student.ultimo_nivel_riesgo;
  if (nivel === "alto") return "riesgo_alto";
  if (nivel === "medio") return "riesgo_medio";
  const asist = Number(student.asistencias);
  if (!Number.isNaN(asist) && asist < 70) return "baja_asistencia";
  const mat = String(student.nota_matematica || "").toUpperCase();
  const leng = String(student.nota_lenguaje || "").toUpperCase();
  if (mat === "C" || leng === "C") return "bajo_rendimiento";
  return "otro";
}

function inferAreaCurso(student) {
  const mat = String(student.nota_matematica || "").toUpperCase();
  const leng = String(student.nota_lenguaje || "").toUpperCase();
  if (mat === "C" && leng !== "C") return "matematica";
  if (leng === "C" && mat !== "C") return "comunicacion";
  if (mat === "C") return "matematica";
  if (leng === "C") return "comunicacion";
  return "matematica";
}

function buildPendingEnroll(student, source = "reforzamiento") {
  return {
    estudiante_id: student.estudiante_id || student.id,
    nombre: student.nombre,
    prediccion_id: student.prediccion_id,
    motivo: inferMotivoInscripcion(student),
    area_sugerida: inferAreaCurso(student),
    riesgo: student.risk_level || student.ultimo_nivel_riesgo,
    source,
  };
}

function filterStudentsForEnroll(students, riskFilter, searchTerm, inscribedIds) {
  let list = students.filter((item) => !inscribedIds.has(item.id));

  if (riskFilter === "alto") {
    list = list.filter((item) => item.ultimo_nivel_riesgo === "alto");
  } else if (riskFilter === "medio") {
    list = list.filter((item) => item.ultimo_nivel_riesgo === "medio");
  } else if (riskFilter === "con_riesgo") {
    list = list.filter((item) => ["alto", "medio"].includes(item.ultimo_nivel_riesgo));
  } else if (riskFilter === "rendimiento") {
    list = list.filter((item) => {
      const mat = String(item.nota_matematica || "").toUpperCase();
      const leng = String(item.nota_lenguaje || "").toUpperCase();
      return mat === "C" || leng === "C";
    });
  }

  const term = String(searchTerm || "").trim().toLowerCase();
  if (term) {
    list = list.filter(
      (item) =>
        item.nombre?.toLowerCase().includes(term) || String(item.dni || "").includes(term)
    );
  }

  return list;
}

export default function DocenteApp({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState("resumen");
  const [formData, setFormData] = useState(initialForm);
  const [showCompetenciasOpcionales, setShowCompetenciasOpcionales] = useState(false);
  const [stats, setStats] = useState(initialStats);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [alertsData, setAlertsData] = useState([]);
  const [studentsList, setStudentsList] = useState([]);
  const [interventionsList, setInterventionsList] = useState([]);
  const [interventionsTotal, setInterventionsTotal] = useState(0);
  const [interventionFilters, setInterventionFilters] = useState(defaultInterventionFilters);
  const [activeStudent, setActiveStudent] = useState("");
  const [error, setError] = useState("");
  const [searchMessage, setSearchMessage] = useState("");
  const [registerData, setRegisterData] = useState(initialRegisterForm);
  const [registerApoderado, setRegisterApoderado] = useState(initialRegisterApoderado);
  const [registerMessage, setRegisterMessage] = useState("");
  const [registerLoading, setRegisterLoading] = useState(false);
  const [secciones, setSecciones] = useState(user?.secciones || []);
  const [todasSecciones, setTodasSecciones] = useState([]);
  const [registerSeccionId, setRegisterSeccionId] = useState("");
  const [studentFilters, setStudentFilters] = useState({ busqueda: "", riesgo: "", seccion_id: "" });
  const [studentsTotal, setStudentsTotal] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [interventionMessage, setInterventionMessage] = useState("");
  const [foundApoderado, setFoundApoderado] = useState(null);
  const [contactStudent, setContactStudent] = useState(null);
  const [contactForm, setContactForm] = useState(initialRegisterApoderado);
  const [contactSaving, setContactSaving] = useState(false);
  const [contactMessage, setContactMessage] = useState("");
  const [copyMessage, setCopyMessage] = useState("");
  const [cursosReforzamiento, setCursosReforzamiento] = useState([]);
  const [selectedCursoId, setSelectedCursoId] = useState("");
  const [cursoDetalle, setCursoDetalle] = useState(null);
  const [reforzamientoLoading, setReforzamientoLoading] = useState(false);
  const [reforzamientoMessage, setReforzamientoMessage] = useState("");
  const [pendingEnroll, setPendingEnroll] = useState(null);
  const [sessionForm, setSessionForm] = useState({
    fecha_sesion: "",
    tema: "",
    modalidad: "presencial",
    asistencia_registrada: "0",
  });
  const [materialLinkForm, setMaterialLinkForm] = useState({ titulo: "", url: "" });
  const [materialFileTitle, setMaterialFileTitle] = useState("");
  const materialFileRef = useRef(null);
  const [enrollPickerOpen, setEnrollPickerOpen] = useState(false);
  const [enrollRiskFilter, setEnrollRiskFilter] = useState("con_riesgo");
  const [enrollSearch, setEnrollSearch] = useState("");
  const [enrollPool, setEnrollPool] = useState([]);
  const [derivacionesList, setDerivacionesList] = useState([]);
  const [derivacionesTotal, setDerivacionesTotal] = useState(0);
  const [derivacionFilters, setDerivacionFilters] = useState({ estado: "" });
  const [incidenciasList, setIncidenciasList] = useState([]);
  const [incidenciasTotal, setIncidenciasTotal] = useState(0);
  const [incidenciaFilters, setIncidenciaFilters] = useState({ severidad: "" });
  const [convivenciaMessage, setConvivenciaMessage] = useState("");
  const [convivenciaLoading, setConvivenciaLoading] = useState(false);
  const [derivacionForm, setDerivacionForm] = useState(initialDerivacionForm);
  const [incidenciaForm, setIncidenciaForm] = useState(initialIncidenciaForm);
  const [pendingDerivacion, setPendingDerivacion] = useState(null);
  const [convivenciaStudents, setConvivenciaStudents] = useState([]);
  const [fichaStudent, setFichaStudent] = useState(null);
  const [fichaIncidencias, setFichaIncidencias] = useState([]);
  const [fichaDerivaciones, setFichaDerivaciones] = useState([]);
  const [fichaSeveridadFilter, setFichaSeveridadFilter] = useState("");
  const [fichaLoading, setFichaLoading] = useState(false);
  const [indicadorAnio, setIndicadorAnio] = useState(() => new Date().getFullYear());
  const [indicadorMes, setIndicadorMes] = useState(() => new Date().getMonth() + 1);
  const [indicadoresList, setIndicadoresList] = useState([]);
  const [indicadoresLoading, setIndicadoresLoading] = useState(false);
  const [indicadoresMessage, setIndicadoresMessage] = useState("");
  const fileInputRef = useRef(null);
  const submitInFlightRef = useRef(false);
  const analysisSectionRef = useRef(null);

  const misSecciones = useMemo(
    () => (secciones.length ? secciones : user?.secciones || []),
    [secciones, user?.secciones]
  );

  const seccionResumenLabel = useMemo(() => {
    if (misSecciones.length === 0) return null;
    if (misSecciones.length === 1) return misSecciones[0].etiqueta;
    return `${misSecciones.length} secciones a cargo`;
  }, [misSecciones]);

  const studentReady = Boolean(formData.nombre?.trim() && formData.dni?.trim());

  const canAnalyze = useMemo(() => {
    if (!studentReady) return false;
    const asist = formData.asistencias;
    const part = formData.participacion;
    return asist !== "" && part !== "" && !Number.isNaN(Number(asist)) && !Number.isNaN(Number(part));
  }, [studentReady, formData.asistencias, formData.participacion]);

  const buildStudentQuery = useCallback((filters) => {
    const params = new URLSearchParams();
    if (filters.busqueda?.trim()) params.set("busqueda", filters.busqueda.trim());
    if (filters.riesgo) params.set("riesgo", filters.riesgo);
    if (filters.seccion_id) params.set("seccion_id", filters.seccion_id);
    return params.toString();
  }, []);

  const loadStudents = useCallback(async (filters = studentFilters) => {
    const query = buildStudentQuery(filters);
    const url = `${API_BASE}/api/estudiantes${query ? `?${query}` : ""}`;
    const estudiantesRes = await authFetch(url);
    if (estudiantesRes.ok) {
      const estudiantesData = await estudiantesRes.json();
      setStudentsList(estudiantesData.estudiantes || []);
      setStudentsTotal(estudiantesData.total ?? 0);
    }
  }, [buildStudentQuery, studentFilters]);

  const loadSecciones = useCallback(async () => {
    try {
      const data = await authFetchJson(`${API_BASE}/api/secciones`);
      setTodasSecciones(data.secciones || []);
      setSecciones(data.mis_secciones || []);
      if (!registerSeccionId && data.mis_secciones?.length >= 1) {
        setRegisterSeccionId(String(data.mis_secciones[0].id));
      }
    } catch {
      setSecciones(user?.secciones || []);
    }
  }, [registerSeccionId, user?.secciones]);

  const buildInterventionQuery = useCallback((filters, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (filters.desde) params.set("desde", filters.desde);
    if (filters.hasta) params.set("hasta", filters.hasta);
    return params.toString();
  }, []);

  const loadInterventions = useCallback(async (filters = interventionFilters) => {
    const query = buildInterventionQuery(filters);
    const intervencionesRes = await authFetch(`${API_BASE}/api/intervenciones?${query}`);
    if (intervencionesRes.ok) {
      const intervencionesData = await intervencionesRes.json();
      setInterventionsList(intervencionesData.intervenciones || []);
      setInterventionsTotal(intervencionesData.total ?? 0);
    }
  }, [buildInterventionQuery, interventionFilters]);

  const loadDerivaciones = useCallback(async (filters = derivacionFilters) => {
    const params = new URLSearchParams({ limit: "50" });
    if (filters.estado) params.set("estado", filters.estado);
    const response = await authFetch(`${API_BASE}/api/derivaciones?${params}`);
    if (response.ok) {
      const data = await response.json();
      setDerivacionesList(data.derivaciones || []);
      setDerivacionesTotal(data.total ?? 0);
    }
  }, [derivacionFilters]);

  const loadIncidencias = useCallback(async (filters = incidenciaFilters) => {
    const params = new URLSearchParams({ limit: "50" });
    if (filters.severidad) params.set("severidad", filters.severidad);
    const response = await authFetch(`${API_BASE}/api/incidencias?${params}`);
    if (response.ok) {
      const data = await response.json();
      setIncidenciasList(data.incidencias || []);
      setIncidenciasTotal(data.total ?? 0);
    }
  }, [incidenciaFilters]);

  const loadConvivenciaStudents = useCallback(async () => {
    const data = await authFetchJson(`${API_BASE}/api/estudiantes?limit=200`);
    setConvivenciaStudents(data.estudiantes || []);
    return data.estudiantes || [];
  }, []);

  const loadFichaConvivencia = useCallback(async (student, severidad = fichaSeveridadFilter) => {
    if (!student?.id) return;
    setFichaLoading(true);
    setError("");
    try {
      const incParams = new URLSearchParams({ limit: "50" });
      if (severidad) incParams.set("severidad", severidad);
      const [incData, derData] = await Promise.all([
        authFetchJson(`${API_BASE}/api/estudiantes/${student.id}/incidencias?${incParams}`),
        authFetchJson(`${API_BASE}/api/derivaciones?estudiante_id=${student.id}&limit=50`),
      ]);
      setFichaStudent(student);
      setFichaIncidencias(incData.incidencias || []);
      setFichaDerivaciones(derData.derivaciones || []);
    } catch {
      setError("No se pudo cargar la ficha de convivencia del alumno.");
    } finally {
      setFichaLoading(false);
    }
  }, [fichaSeveridadFilter]);

  const loadIndicadores = useCallback(async (anio = indicadorAnio, mes = indicadorMes) => {
    const data = await authFetchJson(`${API_BASE}/api/indicadores?anio=${anio}&mes=${mes}`);
    setIndicadoresList(data.indicadores || []);
    return data.indicadores || [];
  }, [indicadorAnio, indicadorMes]);

  const refreshDashboard = useCallback(async () => {
    try {
      const resumenRes = await authFetch(`${API_BASE}/api/resumen`);

      if (resumenRes.ok) {
        const resumenData = await resumenRes.json();
        setStats({
          alto: resumenData.summary?.alto ?? 0,
          medio: resumenData.summary?.medio ?? 0,
          bajo: resumenData.summary?.bajo ?? 0,
        });

        if (resumenData.alertas_prioritarias?.length) {
          setAlertsData(resumenData.alertas_prioritarias);
        } else {
          setAlertsData([]);
        }
      }

      await loadInterventions(interventionFilters);
      await loadStudents(studentFilters);
    } catch {
      setError("No se pudo cargar el resumen. Verifica que el servidor esté en ejecución.");
    }
  }, [interventionFilters, loadInterventions, loadStudents, studentFilters]);

  useEffect(() => {
    loadSecciones();
  }, [loadSecciones]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchJson(`${API_BASE}/api/estudiantes/invalidos`, {
          method: "DELETE",
        });
        if (!cancelled && data.eliminados > 0) {
          await refreshDashboard();
        }
      } catch {
        // Sin permiso o servidor no disponible aun.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  useEffect(() => {
    if (activeTab === "estudiantes") {
      loadStudents(studentFilters);
    }
  }, [activeTab, studentFilters, loadStudents]);

  useEffect(() => {
    if (activeTab === "intervenciones") {
      loadInterventions(interventionFilters);
    }
  }, [activeTab, interventionFilters, loadInterventions]);

  const loadCursosReforzamiento = useCallback(async () => {
    const data = await authFetchJson(`${API_BASE}/api/cursos-reforzamiento`);
    const cursos = data.cursos || [];
    setCursosReforzamiento(cursos);
    return cursos;
  }, []);

  const loadCursoDetalle = useCallback(async (cursoId) => {
    if (!cursoId) {
      setCursoDetalle(null);
      return;
    }
    const data = await authFetchJson(`${API_BASE}/api/cursos-reforzamiento/${cursoId}`);
    setCursoDetalle(data);
  }, []);

  useEffect(() => {
    if (activeTab !== "reforzamiento") return;
    let cancelled = false;
    (async () => {
      setReforzamientoLoading(true);
      setError("");
      try {
        const cursos = await loadCursosReforzamiento();
        if (cancelled) return;
        if (pendingEnroll?.area_sugerida) {
          const match = cursos.find((item) => item.area === pendingEnroll.area_sugerida);
          if (match) setSelectedCursoId(String(match.id));
        } else if (!selectedCursoId && cursos.length > 0) {
          setSelectedCursoId(String(cursos[0].id));
        }
      } catch {
        if (!cancelled) {
          setError("No se pudieron cargar los talleres de reforzamiento.");
        }
      } finally {
        if (!cancelled) setReforzamientoLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeTab, loadCursosReforzamiento, pendingEnroll?.area_sugerida]);

  useEffect(() => {
    if (activeTab !== "reforzamiento" || !selectedCursoId) return;
    loadCursoDetalle(selectedCursoId).catch(() => {
      setError("No se pudo cargar el detalle del taller.");
    });
  }, [activeTab, selectedCursoId, loadCursoDetalle]);

  useEffect(() => {
    if (activeTab !== "convivencia") return;
    loadDerivaciones();
    loadIncidencias();
    loadConvivenciaStudents().catch(() => {
      setError("No se pudo cargar alumnos para convivencia.");
    });
  }, [activeTab, derivacionFilters, incidenciaFilters, loadDerivaciones, loadIncidencias, loadConvivenciaStudents]);

  useEffect(() => {
    if (!pendingDerivacion) return;
    setDerivacionForm({
      estudiante_id: String(pendingDerivacion.estudiante_id || ""),
      entidad_destino: "ugel",
      motivo: pendingDerivacion.motivo || "",
      intervencion_id: pendingDerivacion.intervencion_id
        ? String(pendingDerivacion.intervencion_id)
        : "",
      observaciones: pendingDerivacion.observaciones || "",
    });
  }, [pendingDerivacion]);

  useEffect(() => {
    if (activeTab !== "indicadores") return;
    loadIndicadores().catch(() => {
      setError("No se pudieron cargar los indicadores.");
    });
  }, [activeTab, indicadorAnio, indicadorMes, loadIndicadores]);

  const loadEnrollPool = useCallback(async () => {
    const data = await authFetchJson(`${API_BASE}/api/estudiantes?limit=200`);
    setEnrollPool(data.estudiantes || []);
    return data.estudiantes || [];
  }, []);

  const inscribedStudentIds = useMemo(() => {
    return new Set((cursoDetalle?.inscripciones || []).map((item) => item.estudiante_id));
  }, [cursoDetalle?.inscripciones]);

  const enrollCandidates = useMemo(
    () => filterStudentsForEnroll(enrollPool, enrollRiskFilter, enrollSearch, inscribedStudentIds),
    [enrollPool, enrollRiskFilter, enrollSearch, inscribedStudentIds]
  );

  const applyPendingEnroll = useCallback(
    (pending, cursos = cursosReforzamiento) => {
      setPendingEnroll(pending);
      setReforzamientoMessage("");
      const match = cursos.find((item) => item.area === pending.area_sugerida);
      if (match) {
        setSelectedCursoId(String(match.id));
      }
    },
    [cursosReforzamiento]
  );

  const handleStudentFilterChange = (event) => {
    const { name, value } = event.target;
    setStudentFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleInterventionFilterChange = (event) => {
    const { name, value } = event.target;
    setInterventionFilters((prev) => ({ ...prev, [name]: value }));
  };

  const applyInterventionPreset = (preset) => {
    setInterventionFilters(interventionPresetRange(preset));
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
      if (studentFilters.seccion_id) {
        params.set("seccion_id", studentFilters.seccion_id);
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

  const displayedResult = useMemo(() => {
    if (!result) return null;
    const resultDni = sanitizeDniInput(result.dni || result.received?.dni || "");
    const currentDni = sanitizeDniInput(formData.dni);
    if (!resultDni || !currentDni || resultDni !== currentDni) {
      return null;
    }
    return result;
  }, [result, formData.dni]);

  const resultRiskLevel = resolveResultRiskLevel(displayedResult);
  const resultStyles = resultRiskStyles(resultRiskLevel);
  const motivationalMessage = motivationalText(resultRiskLevel);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    if (name === "dni") {
      setFormData({
        dni: sanitizeDniInput(value),
        nombre: "",
        bimestre: "1",
        asistencias: "",
        nota_matematica: "",
        nota_lenguaje: "",
        participacion: "",
        competencias: { ...initialForm.competencias },
      });
      setFoundApoderado(null);
      setSearchMessage("");
      setResult(null);
      setShowCompetenciasOpcionales(false);
      return;
    }
    setFormData((prev) => ({ ...prev, [name]: value }));
    setResult(null);
  };

  const handleRegisterInputChange = (event) => {
    const { name, value } = event.target;
    if (name === "dni") {
      setRegisterData((prev) => ({ ...prev, dni: sanitizeDniInput(value) }));
      return;
    }
    setRegisterData((prev) => ({ ...prev, [name]: value }));
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

      const dni = sanitizeDniInput(payload.dni || data.received?.dni || "");
      setResult({
        ...data,
        sourceLabel,
        nivel_riesgo: data.nivel_riesgo,
        dni,
        factores: data.factores || [],
      });
      await refreshDashboard();
      return data;
    } finally {
      submitInFlightRef.current = false;
    }
  };

  const handleClearForm = () => {
    setFormData(initialForm);
    setShowCompetenciasOpcionales(false);
    setFoundApoderado(null);
    setResult(null);
    setSearchMessage("");
    setError("");
  };

  const handleRegisterApoderadoChange = (event) => {
    const { name, value } = event.target;
    if (name === "telefono") {
      setRegisterApoderado((prev) => ({ ...prev, telefono: sanitizeTelefonoInput(value) }));
      return;
    }
    if (name === "dni") {
      setRegisterApoderado((prev) => ({ ...prev, dni: sanitizeDniInput(value) }));
      return;
    }
    setRegisterApoderado((prev) => ({ ...prev, [name]: value }));
  };

  const handleContactFormChange = (event) => {
    const { name, value } = event.target;
    if (name === "telefono") {
      setContactForm((prev) => ({ ...prev, telefono: sanitizeTelefonoInput(value) }));
      return;
    }
    if (name === "dni") {
      setContactForm((prev) => ({ ...prev, dni: sanitizeDniInput(value) }));
      return;
    }
    setContactForm((prev) => ({ ...prev, [name]: value }));
  };

  const openContactEditor = (student) => {
    setContactStudent(student);
    setContactForm({
      nombre: student.apoderado_nombre || "",
      telefono: student.apoderado_telefono || "",
      parentesco: student.apoderado_parentesco || "apoderado",
      dni: student.apoderado_dni || "",
    });
    setContactMessage("");
  };

  const handleSaveContact = async () => {
    if (!contactStudent?.id) return;

    const nombreError = validateNombre(contactForm.nombre);
    const telefonoError = validateTelefono(contactForm.telefono);
    const parentescoError = validateParentesco(contactForm.parentesco);
    const dniError = validateDniOpcional(contactForm.dni);

    if (nombreError || telefonoError || parentescoError || dniError) {
      setError(nombreError || telefonoError || parentescoError || dniError);
      return;
    }

    setContactSaving(true);
    setError("");
    setContactMessage("");

    try {
      await fetchJson(`${API_BASE}/api/estudiantes/${contactStudent.id}/apoderado`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: contactForm.nombre.trim(),
          telefono: contactForm.telefono.trim(),
          parentesco: contactForm.parentesco,
          dni: contactForm.dni.trim() || undefined,
        }),
      });
      setContactMessage(`Contacto familiar guardado para ${contactStudent.nombre}.`);
      setContactStudent(null);
      await loadStudents(studentFilters);
      await refreshDashboard();
    } catch (contactError) {
      setError(apiErrorMessage(contactError));
    } finally {
      setContactSaving(false);
    }
  };

  const handleCopyGuardianContact = async (student) => {
    if (!student.apoderado_telefono) return;
    const parentesco =
      PARENTESCO_LABELS[student.apoderado_parentesco] || student.apoderado_parentesco || "Apoderado";
    const text = `${student.apoderado_nombre || parentesco} · ${student.apoderado_telefono}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopyMessage(`Contacto copiado: ${student.apoderado_telefono}`);
      window.setTimeout(() => setCopyMessage(""), 2500);
    } catch {
      setCopyMessage("No se pudo copiar al portapapeles.");
    }
  };

  const handleRegisterStudent = async () => {
    const dni = registerData.dni.trim();
    const nombre = registerData.nombre.trim();

    const dniError = validateDni(dni);
    const nombreError = validateNombre(nombre);
    const seccionError = validateSeccionRequerida(registerSeccionId, misSecciones);
    const hasApoderadoData =
      registerApoderado.nombre.trim() ||
      registerApoderado.telefono.trim() ||
      registerApoderado.dni.trim();
    const apoderadoNombreError = hasApoderadoData
      ? validateNombre(registerApoderado.nombre)
      : null;
    const apoderadoTelefonoError = hasApoderadoData
      ? validateTelefono(registerApoderado.telefono)
      : null;
    const apoderadoParentescoError = hasApoderadoData
      ? validateParentesco(registerApoderado.parentesco)
      : null;
    const apoderadoDniError = validateDniOpcional(registerApoderado.dni);

    if (
      dniError ||
      nombreError ||
      seccionError ||
      apoderadoNombreError ||
      apoderadoTelefonoError ||
      apoderadoParentescoError ||
      apoderadoDniError
    ) {
      setError(
        dniError ||
          nombreError ||
          seccionError ||
          apoderadoNombreError ||
          apoderadoTelefonoError ||
          apoderadoParentescoError ||
          apoderadoDniError
      );
      return;
    }

    setRegisterLoading(true);
    setError("");
    setRegisterMessage("");

    try {
      const body = { dni, nombre };
      if (registerSeccionId) {
        body.seccion_id = Number(registerSeccionId);
      }
      if (hasApoderadoData) {
        body.apoderado = {
          nombre: registerApoderado.nombre.trim(),
          telefono: registerApoderado.telefono.trim(),
          parentesco: registerApoderado.parentesco,
          dni: registerApoderado.dni.trim() || undefined,
        };
      }
      const data = await fetchJson(`${API_BASE}/api/estudiantes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const seccionMsg = data.estudiante.seccion_etiqueta
        ? ` · ${data.estudiante.seccion_etiqueta}`
        : "";
      setRegisterMessage(
        `Alumno registrado: ${data.estudiante.nombre} (DNI ${data.estudiante.dni})${seccionMsg}${
          data.apoderado ? " · Apoderado registrado" : ""
        }`
      );
      setRegisterData(initialRegisterForm);
      setRegisterApoderado(initialRegisterApoderado);
      await refreshDashboard();
      if (activeTab === "estudiantes") {
        await loadStudents(studentFilters);
      }
    } catch (registerError) {
      setError(apiErrorMessage(registerError));
    } finally {
      setRegisterLoading(false);
    }
  };

  const handleSearchByDni = async () => {
    const dni = formData.dni.trim();
    const dniError = validateDni(dni);
    if (dniError) {
      setSearchMessage(dniError);
      return;
    }

    setSearchMessage("");
    setError("");
    setResult(null);

    try {
      const response = await authFetch(
        `${API_BASE}/api/estudiantes/buscar?dni=${encodeURIComponent(dni)}`
      );
      const data = await response.json();

      if (response.status === 404) {
        setFormData((prev) => ({
          ...prev,
          nombre: "",
          bimestre: "1",
          asistencias: "",
          nota_matematica: "",
          nota_lenguaje: "",
          participacion: "",
          competencias: { ...initialForm.competencias },
        }));
        setFoundApoderado(null);
        setResult(null);
        setSearchMessage(
          `DNI ${dni} no está registrado. Ve a la pestaña Estudiantes para registrarlo primero.`
        );
        return;
      }

      if (!response.ok) {
        throw new Error(data.error || "No se pudo buscar el estudiante.");
      }

      const student = data.estudiante;
      setFormData({
        dni: student.dni || dni,
        nombre: student.nombre || "",
        bimestre: String(student.bimestre || defaultStudentMetrics.bimestre),
        asistencias:
          student.asistencias != null && student.asistencias !== ""
            ? String(student.asistencias)
            : defaultStudentMetrics.asistencias,
        nota_matematica: student.nota_matematica || defaultStudentMetrics.nota_matematica,
        nota_lenguaje: student.nota_lenguaje || defaultStudentMetrics.nota_lenguaje,
        participacion:
          student.participacion != null && student.participacion !== ""
            ? String(student.participacion)
            : defaultStudentMetrics.participacion,
        competencias: { ...initialForm.competencias },
      });
      setFoundApoderado(
        student.apoderado_telefono
          ? {
              nombre: student.apoderado_nombre,
              telefono: student.apoderado_telefono,
              parentesco: student.apoderado_parentesco,
            }
          : null
      );
      setSearchMessage("");
    } catch (searchError) {
      setError(apiErrorMessage(searchError));
    }
  };

  const startAnalysisForStudent = async (student) => {
    setActiveTab("resumen");
    setError("");
    setSearchMessage("");
    setResult(null);

    const dni = sanitizeDniInput(student.dni || "");
    const nombre = String(student.nombre || "").trim();
    const asistencias =
      student.asistencias != null && student.asistencias !== ""
        ? String(student.asistencias)
        : "85";
    const participacion =
      student.participacion != null && student.participacion !== ""
        ? String(student.participacion)
        : "7";

    setFormData({
      dni,
      nombre,
      bimestre: String(student.bimestre || "1"),
      asistencias,
      nota_matematica: student.nota_matematica || "A",
      nota_lenguaje: student.nota_lenguaje || "A",
      participacion,
      competencias: { ...initialForm.competencias },
    });

    window.requestAnimationFrame(() => {
      analysisSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    if (!dni || dni.length !== 8) {
      setSearchMessage(
        "Este alumno no tiene DNI válido. Regístralo en Estudiantes con su DNI de 8 dígitos."
      );
      return;
    }

    if (!nombre) {
      setSearchMessage("Falta el nombre del alumno. Buscalo por DNI en el formulario.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        dni,
        nombre,
        bimestre: Number(student.bimestre) || 1,
        asistencias: Number(asistencias),
        nota_matematica: student.nota_matematica || "A",
        nota_lenguaje: student.nota_lenguaje || "A",
        participacion: Number(participacion),
      };
      await requestPrediction(payload, `Alerta — ${nombre}`);
    } catch (analysisError) {
      setError(apiErrorMessage(analysisError));
      setSearchMessage("Revisa los datos y pulsa Analizar y guardar.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitInFlightRef.current || loading) {
      return;
    }

    const dni = formData.dni.trim();
    const nombre = formData.nombre.trim();

    const dniError = validateDni(dni);
    if (dniError) {
      setError(dniError);
      return;
    }

    if (!nombre) {
      setError("Busca el DNI primero. El alumno debe estar registrado en Estudiantes.");
      return;
    }

    const asistError = validateAsistencias(formData.asistencias);
    const partError = validateParticipacion(formData.participacion);
    if (asistError || partError) {
      setError(asistError || partError);
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
      const competencias = Object.fromEntries(
        Object.entries(formData.competencias || {}).filter(([, nota]) => String(nota || "").trim())
      );
      if (Object.keys(competencias).length) {
        payload.competencias = competencias;
      }
      await requestPrediction(payload, "Formulario manual");
    } catch (submitError) {
      setError(apiErrorMessage(submitError));
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterIntervention = async (student) => {
    if (!student.estudiante_id && !student.id) {
      setError("Este alumno aún no está registrado en el sistema.");
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
          alerta_id: student.alerta_id,
          titulo: `Seguimiento — ${student.nombre}`,
          tipo: "contacto_familia",
          descripcion: "Acción registrada desde el panel de alertas prioritarias.",
        }),
      });

      await refreshDashboard();
      setInterventionMessage(
        `Acción registrada para ${student.nombre}. La alerta quedó en bitácora y se marcó como atendida.`
      );
      setActiveTab("intervenciones");
    } catch (interventionError) {
      setError(apiErrorMessage(interventionError));
    } finally {
      setLoading(false);
      setActiveStudent("");
    }
  };

  const handleEnrollWorkshop = (student) => {
    applyPendingEnroll(buildPendingEnroll(student, "alerta"));
    setEnrollPickerOpen(false);
    setActiveTab("reforzamiento");
  };

  const handleOpenEnrollPicker = async () => {
    setEnrollPickerOpen(true);
    setEnrollSearch("");
    setError("");
    try {
      await loadEnrollPool();
    } catch {
      setError("No se pudo cargar la lista de alumnos.");
    }
  };

  const handleSelectStudentForEnroll = (student) => {
    applyPendingEnroll(buildPendingEnroll(student, "reforzamiento"));
    setEnrollPickerOpen(false);
  };

  const handleConfirmEnroll = async () => {
    if (!pendingEnroll?.estudiante_id || !selectedCursoId) return;
    setReforzamientoLoading(true);
    setError("");
    const origen =
      pendingEnroll.source === "alerta"
        ? "alerta de riesgo"
        : "panel de reforzamiento";
    try {
      await fetchJson(`${API_BASE}/api/cursos-reforzamiento/${selectedCursoId}/inscripciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          estudiante_id: pendingEnroll.estudiante_id,
          prediccion_id: pendingEnroll.prediccion_id,
          motivo: pendingEnroll.motivo,
          observaciones: `Inscripcion desde ${origen} (${pendingEnroll.nombre}).`,
        }),
      });
      setReforzamientoMessage(`${pendingEnroll.nombre} inscrito en el taller.`);
      setPendingEnroll(null);
      await loadCursoDetalle(selectedCursoId);
      await loadCursosReforzamiento();
    } catch (enrollError) {
      setError(apiErrorMessage(enrollError));
    } finally {
      setReforzamientoLoading(false);
    }
  };

  const handleCreateSession = async () => {
    if (!selectedCursoId || !sessionForm.fecha_sesion.trim() || !sessionForm.tema.trim()) {
      setError("Completa fecha y tema de la sesión.");
      return;
    }
    setReforzamientoLoading(true);
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/cursos-reforzamiento/${selectedCursoId}/sesiones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fecha_sesion: sessionForm.fecha_sesion,
          tema: sessionForm.tema.trim(),
          modalidad: sessionForm.modalidad,
          asistencia_registrada: Number(sessionForm.asistencia_registrada) || 0,
        }),
      });
      setSessionForm({ fecha_sesion: "", tema: "", modalidad: "presencial", asistencia_registrada: "0" });
      setReforzamientoMessage("Sesión registrada.");
      await loadCursoDetalle(selectedCursoId);
    } catch (sessionError) {
      setError(apiErrorMessage(sessionError));
    } finally {
      setReforzamientoLoading(false);
    }
  };

  const handleAddMaterialLink = async () => {
    if (!selectedCursoId || !materialLinkForm.titulo.trim() || !materialLinkForm.url.trim()) {
      setError("Completa título y URL del material.");
      return;
    }
    setReforzamientoLoading(true);
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/cursos-reforzamiento/${selectedCursoId}/materiales`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          titulo: materialLinkForm.titulo.trim(),
          url: materialLinkForm.url.trim(),
        }),
      });
      setMaterialLinkForm({ titulo: "", url: "" });
      setReforzamientoMessage("Enlace agregado a la biblioteca.");
      await loadCursoDetalle(selectedCursoId);
    } catch (linkError) {
      setError(apiErrorMessage(linkError));
    } finally {
      setReforzamientoLoading(false);
    }
  };

  const handleUploadMaterialFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !selectedCursoId) return;
    setReforzamientoLoading(true);
    setError("");
    try {
      const formDataUpload = new FormData();
      formDataUpload.append("file", file);
      formDataUpload.append("titulo", materialFileTitle.trim() || file.name);
      const response = await authFetch(
        `${API_BASE}/api/cursos-reforzamiento/${selectedCursoId}/materiales`,
        { method: "POST", body: formDataUpload }
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "No se pudo subir el archivo.");
      }
      setMaterialFileTitle("");
      if (materialFileRef.current) materialFileRef.current.value = "";
      setReforzamientoMessage("Archivo subido a la biblioteca.");
      await loadCursoDetalle(selectedCursoId);
    } catch (uploadError) {
      setError(apiErrorMessage(uploadError));
    } finally {
      setReforzamientoLoading(false);
    }
  };

  const handleDownloadMaterial = async (material) => {
    try {
      const response = await authFetch(
        `${API_BASE}/api/materiales-reforzamiento/${material.id}/descargar`
      );
      if (!response.ok) throw new Error("No se pudo descargar el archivo.");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = material.nombre_archivo || material.titulo || "material.pdf";
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(apiErrorMessage(downloadError));
    }
  };

  const handleUpdateInscripcion = async (inscripcionId, resultado) => {
    setReforzamientoLoading(true);
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/inscripciones/${inscripcionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resultado }),
      });
      setReforzamientoMessage("Resultado de inscripción actualizado.");
      await loadCursoDetalle(selectedCursoId);
    } catch (updateError) {
      setError(apiErrorMessage(updateError));
    } finally {
      setReforzamientoLoading(false);
    }
  };

  const handleAlertStatusChange = async (alertaId, estado, accion, detalle) => {
    setLoading(true);
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/alertas/${alertaId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado, accion, detalle }),
      });
      await refreshDashboard();
    } catch (statusError) {
      setError(apiErrorMessage(statusError));
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteIntervention = async (intervencionId) => {
    setLoading(true);
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/intervenciones/${intervencionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado: "cerrada" }),
      });
      setInterventionMessage("Intervención marcada como realizada.");
      await refreshDashboard();
    } catch (completeError) {
      setError(apiErrorMessage(completeError));
    } finally {
      setLoading(false);
    }
  };

  const handleDeriveFromIntervention = (item) => {
    setPendingDerivacion({
      estudiante_id: item.estudiante_id,
      nombre: item.nombre_estudiante,
      intervencion_id: item.id,
      motivo: `Derivación vinculada a intervención: ${item.titulo}`,
      observaciones: item.descripcion || "",
    });
    setConvivenciaMessage("");
    setActiveTab("convivencia");
  };

  const handleCreateDerivacion = async () => {
    if (!derivacionForm.estudiante_id || !derivacionForm.motivo.trim()) return;
    setConvivenciaLoading(true);
    setConvivenciaMessage("");
    setError("");
    try {
      const estudianteId = Number(derivacionForm.estudiante_id);
      await fetchJson(`${API_BASE}/api/derivaciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          estudiante_id: estudianteId,
          entidad_destino: derivacionForm.entidad_destino,
          motivo: derivacionForm.motivo.trim(),
          intervencion_id: derivacionForm.intervencion_id
            ? Number(derivacionForm.intervencion_id)
            : null,
          observaciones: derivacionForm.observaciones.trim() || null,
        }),
      });
      setDerivacionForm(initialDerivacionForm);
      setPendingDerivacion(null);
      setConvivenciaMessage("Derivación registrada correctamente.");
      await loadDerivaciones();
      if (fichaStudent?.id === estudianteId) {
        await loadFichaConvivencia(fichaStudent);
      }
    } catch (createError) {
      setError(apiErrorMessage(createError));
    } finally {
      setConvivenciaLoading(false);
    }
  };

  const handleUpdateDerivacionEstado = async (derivacionId, estado) => {
    setConvivenciaLoading(true);
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/derivaciones/${derivacionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado }),
      });
      setConvivenciaMessage("Estado de derivación actualizado.");
      await loadDerivaciones();
      if (fichaStudent) await loadFichaConvivencia(fichaStudent);
    } catch (updateError) {
      setError(apiErrorMessage(updateError));
    } finally {
      setConvivenciaLoading(false);
    }
  };

  const handleCreateIncidencia = async () => {
    if (!incidenciaForm.estudiante_id || !incidenciaForm.descripcion.trim()) return;
    setConvivenciaLoading(true);
    setConvivenciaMessage("");
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/incidencias`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          estudiante_id: Number(incidenciaForm.estudiante_id),
          tipo_incidencia: incidenciaForm.tipo_incidencia,
          severidad: incidenciaForm.severidad,
          descripcion: incidenciaForm.descripcion.trim(),
          acciones_tomadas: incidenciaForm.acciones_tomadas.trim() || null,
          fecha_incidencia: incidenciaForm.fecha_incidencia || null,
        }),
      });
      const estudianteId = Number(incidenciaForm.estudiante_id);
      setIncidenciaForm(initialIncidenciaForm);
      setConvivenciaMessage("Incidencia registrada correctamente.");
      await loadIncidencias();
      if (fichaStudent?.id === estudianteId) {
        await loadFichaConvivencia(fichaStudent);
      }
    } catch (createError) {
      setError(apiErrorMessage(createError));
    } finally {
      setConvivenciaLoading(false);
    }
  };

  const openFichaConvivencia = async (student) => {
    await loadFichaConvivencia(student);
  };

  const handleCalcularIndicadores = async () => {
    setIndicadoresLoading(true);
    setIndicadoresMessage("");
    setError("");
    try {
      await fetchJson(`${API_BASE}/api/indicadores/calcular`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anio: indicadorAnio, mes: indicadorMes }),
      });
      await loadIndicadores(indicadorAnio, indicadorMes);
      setIndicadoresMessage(
        `Indicadores calculados para ${MESES_LABELS[indicadorMes] || indicadorMes} ${indicadorAnio}.`
      );
    } catch (calcError) {
      setError(apiErrorMessage(calcError));
    } finally {
      setIndicadoresLoading(false);
    }
  };

  const handleCompetenciaChange = (area, nota) => {
    setFormData((prev) => ({
      ...prev,
      competencias: { ...prev.competencias, [area]: nota },
    }));
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
    <main className="min-h-screen bg-zinc-950 px-4 py-4 text-zinc-100 sm:px-5">
      <section className="mx-auto max-w-7xl">
        <header className="mb-4 flex flex-col justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 shadow-lg shadow-black/20 sm:flex-row sm:items-center">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold text-white sm:text-3xl">PredictEdu</h1>
            <p className="mt-0.5 truncate text-sm text-zinc-400">
              {user.nombre_completo || user.username}
              {seccionResumenLabel ? ` · ${seccionResumenLabel}` : ""}
            </p>
          </div>

          <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-200 hover:bg-zinc-700"
            >
              <IconLogout />
              Cerrar sesión
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

        <nav className="mb-4 flex flex-wrap gap-2">
          <Tab
            label="Resumen"
            active={activeTab === "resumen"}
            onClick={() => setActiveTab("resumen")}
          />
          <Tab
            label="Alertas"
            active={activeTab === "alertas"}
            badge={alertsData.length > 0 ? alertsData.length : null}
            onClick={() => setActiveTab("alertas")}
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
          <Tab
            label="Reforzamiento"
            active={activeTab === "reforzamiento"}
            onClick={() => setActiveTab("reforzamiento")}
          />
          <Tab
            label="Convivencia"
            active={activeTab === "convivencia"}
            onClick={() => setActiveTab("convivencia")}
          />
          <Tab
            label="Indicadores"
            active={activeTab === "indicadores"}
            onClick={() => setActiveTab("indicadores")}
          />
        </nav>

        {error && (
          <p className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        )}

        {activeTab === "resumen" && (
          <>
            <section className="mb-4 grid gap-3 sm:grid-cols-3">
              <SummaryCard title="Riesgo alto" value={stats.alto} tone="red" />
              <SummaryCard title="Riesgo medio" value={stats.medio} tone="orange" />
              <SummaryCard title="Sin riesgo" value={stats.bajo} tone="green" />
            </section>

            <section ref={analysisSectionRef} className="grid items-start gap-4 lg:grid-cols-5">
              <article className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 lg:col-span-3">
                <h2 className="text-base font-semibold text-white">Analizar alumno</h2>
                <form onSubmit={handleSubmit} className="mt-3 space-y-3">
                  <FormSection step="1" title="Buscar alumno registrado">
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <TextField
                          label="DNI del estudiante"
                          name="dni"
                          value={formData.dni}
                          onChange={handleInputChange}
                          placeholder="12345678"
                          hint="8 dígitos, sin espacios ni guiones."
                          inputMode="numeric"
                          maxLength={8}
                          required
                        />
                      </div>
                      <button
                        type="button"
                        onClick={handleSearchByDni}
                        disabled={loading || !formData.dni.trim()}
                        className="mt-6 shrink-0 self-end rounded-xl border border-blue-600/40 bg-blue-600/10 px-4 py-2.5 text-sm font-medium text-blue-100 hover:bg-blue-600/20 disabled:opacity-40"
                      >
                        Buscar
                      </button>
                    </div>
                    {searchMessage && (
                      <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                        {searchMessage}
                      </p>
                    )}
                    {studentReady && (
                      <StudentFoundCard nombre={formData.nombre} dni={formData.dni} />
                    )}
                    {studentReady && foundApoderado?.telefono && (
                      <p className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-400">
                        Apoderado: {foundApoderado.nombre || "Sin nombre"} ·{" "}
                        {PARENTESCO_LABELS[foundApoderado.parentesco] || foundApoderado.parentesco} ·{" "}
                        <span className="text-emerald-300">{foundApoderado.telefono}</span>
                      </p>
                    )}
                  </FormSection>

                  <FormSection step="2" title="Período y asistencia" disabled={!studentReady}>
                    <BimestrePills
                      value={studentReady ? formData.bimestre : ""}
                      onChange={(bimestre) => {
                        setResult(null);
                        setFormData((prev) => ({ ...prev, bimestre }));
                      }}
                    />
                    <AsistenciaSlider
                      value={studentReady ? formData.asistencias : ""}
                      onChange={handleInputChange}
                    />
                  </FormSection>

                  <FormSection step="3" title="Rendimiento en clase" disabled={!studentReady}>
                    <GradeChips
                      label="Matemática"
                      name="nota_matematica"
                      value={studentReady ? formData.nota_matematica : ""}
                      onChange={handleInputChange}
                    />
                    <GradeChips
                      label="Comunicación / Lenguaje"
                      name="nota_lenguaje"
                      value={studentReady ? formData.nota_lenguaje : ""}
                      onChange={handleInputChange}
                    />
                    <ParticipacionSlider
                      value={studentReady ? formData.participacion : ""}
                      onChange={handleInputChange}
                    />
                  </FormSection>

                  {studentReady && (
                    <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/30">
                      <button
                        type="button"
                        onClick={() => setShowCompetenciasOpcionales((prev) => !prev)}
                        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-zinc-900/40"
                      >
                        <span>
                          <span className="text-sm font-medium text-zinc-200">
                            {showCompetenciasOpcionales
                              ? "Ocultar otras competencias"
                              : "Evaluar con otras competencias"}
                          </span>
                          <span className="mt-0.5 block text-xs text-zinc-500">
                            Opcional: personal social, ciencia, arte y educación física
                          </span>
                        </span>
                        <span className="shrink-0 text-xs text-zinc-500">
                          {showCompetenciasOpcionales ? "Ocultar" : "Mostrar"}
                        </span>
                      </button>
                      {showCompetenciasOpcionales && (
                        <div className="space-y-2 border-t border-zinc-800 px-4 pb-4 pt-3">
                          {COMPETENCIAS_OPCIONALES.map((item) => (
                            <GradeChips
                              key={item.key}
                              label={item.label}
                              name={item.key}
                              value={formData.competencias?.[item.key] || ""}
                              onChange={(event) =>
                                handleCompetenciaChange(item.key, event.target.value)
                              }
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {!studentReady && (
                    <FormHint>
                      Busca un alumno por DNI para habilitar asistencia, notas y el análisis.
                    </FormHint>
                  )}

                  <div className="flex gap-2 pt-1">
                    <button
                      type="submit"
                      disabled={loading || !canAnalyze || submitInFlightRef.current}
                      className="flex-1 rounded-xl bg-blue-500 px-4 py-3 font-medium text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-500"
                    >
                      {loading ? "Analizando..." : "Analizar y guardar"}
                    </button>
                    {displayedResult?.sourceLabel === "Formulario manual" && (
                      <button
                        type="button"
                        onClick={handleClearForm}
                        disabled={loading}
                        className="rounded-xl border border-zinc-600 bg-zinc-800 px-4 py-3 text-sm font-medium text-zinc-200 transition hover:bg-zinc-700 disabled:opacity-60"
                      >
                        Limpiar
                      </button>
                    )}
                  </div>
                </form>
              </article>

              <ResultPanel
                result={displayedResult}
                riskLevel={resultRiskLevel}
                riskStyles={resultStyles}
                motivationalMessage={motivationalMessage}
                onClear={displayedResult?.sourceLabel === "Formulario manual" ? handleClearForm : null}
              />
            </section>
          </>
        )}

        {activeTab === "alertas" && (
          <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h2 className="text-base font-semibold text-white">
              Alertas de riesgo
              {alertsData.length > 0 ? ` (${alertsData.length})` : ""}
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              Alumnos con riesgo alto o medio. Analizar vuelve a evaluar; Registrar acción crea un
              seguimiento en Intervenciones.
            </p>
            <PriorityAlertsList
              alerts={alertsData}
              loading={loading}
              activeStudent={activeStudent}
              onAnalyze={startAnalysisForStudent}
              onRegisterIntervention={handleRegisterIntervention}
              onCopyContact={handleCopyGuardianContact}
              onAlertStatusChange={handleAlertStatusChange}
              onEnrollWorkshop={handleEnrollWorkshop}
            />
            {copyMessage && (
              <p className="mt-3 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm text-blue-200">
                {copyMessage}
              </p>
            )}
          </section>
        )}

        {activeTab === "estudiantes" && (
          <div className="space-y-6">
            <section className="rounded-xl border border-emerald-900/30 bg-zinc-900/80 p-4">
              <h2 className="text-base font-semibold text-white">Registrar nuevo alumno</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <TextField
                  label="DNI"
                  name="dni"
                  value={registerData.dni}
                  onChange={handleRegisterInputChange}
                  placeholder="12345678"
                  hint="8 dígitos del documento de identidad."
                  inputMode="numeric"
                  maxLength={8}
                />
                <TextField
                  label="Nombre completo"
                  name="nombre"
                  value={registerData.nombre}
                  onChange={handleRegisterInputChange}
                  placeholder="Nombres y apellidos"
                />
                <label className="block md:col-span-2">
                  <span className="mb-1 block text-xs text-zinc-400">Sección</span>
                  <select
                    value={registerSeccionId}
                    onChange={(event) => setRegisterSeccionId(event.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-400"
                  >
                    <option value="">Selecciona una sección</option>
                    {(misSecciones.length ? misSecciones : todasSecciones).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.etiqueta}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                <h3 className="text-sm font-medium text-zinc-200">Apoderado o contacto familiar</h3>
                <p className="mt-1 text-xs text-zinc-500">
                  Opcional al registrar. Sirve para llamadas desde Alertas de riesgo.
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <TextField
                    label="Nombre del apoderado"
                    name="nombre"
                    value={registerApoderado.nombre}
                    onChange={handleRegisterApoderadoChange}
                    placeholder="Nombres y apellidos"
                  />
                  <TextField
                    label="Teléfono móvil"
                    name="telefono"
                    value={registerApoderado.telefono}
                    onChange={handleRegisterApoderadoChange}
                    placeholder="987654321"
                    hint="9 dígitos, empieza con 9."
                    inputMode="numeric"
                    maxLength={9}
                  />
                  <label className="block">
                    <span className="mb-1 block text-xs text-zinc-400">Parentesco</span>
                    <select
                      name="parentesco"
                      value={registerApoderado.parentesco}
                      onChange={handleRegisterApoderadoChange}
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-400"
                    >
                      {Object.entries(PARENTESCO_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <TextField
                    label="DNI apoderado (opcional)"
                    name="dni"
                    value={registerApoderado.dni}
                    onChange={handleRegisterApoderadoChange}
                    placeholder="12345678"
                    inputMode="numeric"
                    maxLength={8}
                  />
                </div>
              </div>
              {registerMessage && (
                <p className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
                  {registerMessage}
                </p>
              )}
              <button
                type="button"
                onClick={handleRegisterStudent}
                disabled={registerLoading}
                className="mt-4 rounded-xl border border-emerald-600/40 bg-emerald-600/10 px-5 py-2.5 text-sm font-medium text-emerald-200 hover:bg-emerald-600/20 disabled:opacity-60"
              >
                {registerLoading ? "Registrando..." : "Registrar alumno"}
              </button>
            </section>

            <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">
                  Estudiantes — {studentsTotal}
                </h2>
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

            {fichaStudent && (
              <div className="mt-4 rounded-xl border border-rose-900/40 bg-rose-950/20 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-white">
                    Ficha convivencia — {fichaStudent.nombre}
                  </h3>
                  <button
                    type="button"
                    onClick={() => {
                      setFichaStudent(null);
                      setFichaIncidencias([]);
                      setFichaDerivaciones([]);
                      setFichaSeveridadFilter("");
                    }}
                    className="text-xs text-zinc-400 hover:text-zinc-200"
                  >
                    Cerrar
                  </button>
                </div>
                {fichaLoading ? (
                  <p className="mt-3 text-sm text-zinc-500">Cargando ficha...</p>
                ) : (
                  <>
                    <div className="mt-3 flex flex-wrap items-end gap-3">
                      <label className="block">
                        <span className="mb-1 block text-xs text-zinc-400">Filtrar incidencias</span>
                        <select
                          value={fichaSeveridadFilter}
                          onChange={async (event) => {
                            const value = event.target.value;
                            setFichaSeveridadFilter(value);
                            await loadFichaConvivencia(fichaStudent, value);
                          }}
                          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                        >
                          <option value="">Todas las severidades</option>
                          {Object.entries(SEVERIDAD_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        onClick={() => {
                          setIncidenciaForm((prev) => ({
                            ...prev,
                            estudiante_id: String(fichaStudent.id),
                          }));
                          setActiveTab("convivencia");
                        }}
                        className="rounded-lg border border-rose-600/40 bg-rose-600/10 px-3 py-2 text-xs text-rose-100"
                      >
                        Registrar incidencia
                      </button>
                    </div>
                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <div>
                        <h4 className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                          Incidencias ({fichaIncidencias.length})
                        </h4>
                        {!fichaIncidencias.length ? (
                          <p className="mt-2 text-sm text-zinc-500">Sin incidencias registradas.</p>
                        ) : (
                          <div className="mt-2 space-y-2">
                            {fichaIncidencias.map((item) => (
                              <div
                                key={item.id}
                                className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
                              >
                                <p className="text-sm text-zinc-100">
                                  {TIPO_INCIDENCIA_LABELS[item.tipo_incidencia] || item.tipo_incidencia}
                                </p>
                                <p className="mt-1 text-xs text-zinc-500">
                                  {item.fecha_incidencia} ·{" "}
                                  {SEVERIDAD_LABELS[item.severidad] || item.severidad}
                                </p>
                                <p className="mt-2 text-sm text-zinc-300">{item.descripcion}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                          Derivaciones ({fichaDerivaciones.length})
                        </h4>
                        {!fichaDerivaciones.length ? (
                          <p className="mt-2 text-sm text-zinc-500">Sin derivaciones externas.</p>
                        ) : (
                          <div className="mt-2 space-y-2">
                            {fichaDerivaciones.map((item) => (
                              <div
                                key={item.id}
                                className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
                              >
                                <p className="text-sm text-zinc-100">
                                  {ENTIDAD_DESTINO_LABELS[item.entidad_destino] || item.entidad_destino}
                                </p>
                                <p className="mt-1 text-xs text-zinc-500">
                                  {item.fecha_derivacion} ·{" "}
                                  {ESTADO_DERIVACION_LABELS[item.estado] || item.estado}
                                </p>
                                <p className="mt-2 text-sm text-zinc-300">{item.motivo}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {contactStudent && (
              <div className="mt-4 rounded-xl border border-blue-900/40 bg-blue-950/20 p-4">
                <h3 className="text-sm font-semibold text-white">
                  Contacto familiar — {contactStudent.nombre}
                </h3>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <TextField
                    label="Nombre del apoderado"
                    name="nombre"
                    value={contactForm.nombre}
                    onChange={handleContactFormChange}
                    placeholder="Nombres y apellidos"
                  />
                  <TextField
                    label="Teléfono móvil"
                    name="telefono"
                    value={contactForm.telefono}
                    onChange={handleContactFormChange}
                    placeholder="987654321"
                    inputMode="numeric"
                    maxLength={9}
                  />
                  <label className="block">
                    <span className="mb-1 block text-xs text-zinc-400">Parentesco</span>
                    <select
                      name="parentesco"
                      value={contactForm.parentesco}
                      onChange={handleContactFormChange}
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-400"
                    >
                      {Object.entries(PARENTESCO_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <TextField
                    label="DNI apoderado (opcional)"
                    name="dni"
                    value={contactForm.dni}
                    onChange={handleContactFormChange}
                    placeholder="12345678"
                    inputMode="numeric"
                    maxLength={8}
                  />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleSaveContact}
                    disabled={contactSaving}
                    className="rounded-lg border border-blue-600/40 bg-blue-600/10 px-4 py-2 text-sm text-blue-100 hover:bg-blue-600/20 disabled:opacity-60"
                  >
                    {contactSaving ? "Guardando..." : "Guardar contacto"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setContactStudent(null)}
                    className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-700"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
            {contactMessage && (
              <p className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
                {contactMessage}
              </p>
            )}

            <div className="mt-4 grid gap-3 md:grid-cols-4">
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
              <label className="block">
                <span className="mb-1 block text-xs text-zinc-400">Sección</span>
                <select
                  name="seccion_id"
                  value={studentFilters.seccion_id}
                  onChange={handleStudentFilterChange}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-400"
                >
                  <option value="">
                    {misSecciones.length ? "Todas mis secciones" : "Todas"}
                  </option>
                  {(misSecciones.length ? misSecciones : todasSecciones).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.etiqueta}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {studentsList.length === 0 ? (
              <p className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-400">
                {studentsTotal === 0
                  ? "Aún no hay estudiantes. Registra uno o carga un archivo SIAGIE."
                  : "Ningún estudiante coincide con los filtros aplicados."}
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-zinc-800 text-zinc-400">
                    <tr>
                      <th className="px-3 py-2">DNI</th>
                      <th className="px-3 py-2">Estudiante</th>
                      <th className="px-3 py-2">Sección</th>
                      <th className="px-3 py-2">Asistencia</th>
                      <th className="px-3 py-2">Notas</th>
                      <th className="px-3 py-2">Riesgo</th>
                      <th className="px-3 py-2">Familia</th>
                      <th className="px-3 py-2">Última predicción</th>
                      <th className="px-3 py-2">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {studentsList.map((student) => (
                      <tr
                        key={student.id}
                        className="border-b border-zinc-800/80 transition hover:bg-zinc-900/40"
                      >
                        <td className="px-3 py-3 text-zinc-400">{student.dni || "—"}</td>
                        <td className="px-3 py-3 font-medium text-zinc-100">{student.nombre}</td>
                        <td className="px-3 py-3 text-zinc-300">
                          {student.seccion_etiqueta || "—"}
                        </td>
                        <td className="px-3 py-3 text-zinc-300">{student.asistencias ?? "—"}%</td>
                        <td className="px-3 py-3 text-zinc-300">
                          Mat {student.nota_matematica ?? "—"} · Leng{" "}
                          {student.nota_lenguaje ?? "—"}
                        </td>
                        <td className="px-3 py-3">
                          <RiskBadge level={student.ultimo_nivel_riesgo} />
                        </td>
                        <td className="px-3 py-3 text-zinc-300">
                          {student.apoderado_telefono ? (
                            <div className="space-y-1">
                              <p className="text-xs text-zinc-400">
                                {student.apoderado_nombre || "Apoderado"}
                              </p>
                              <p className="font-medium text-emerald-300">
                                {student.apoderado_telefono}
                              </p>
                            </div>
                          ) : (
                            <span className="text-zinc-500">Sin contacto</span>
                          )}
                          <button
                            type="button"
                            onClick={() => openContactEditor(student)}
                            className="mt-1 block text-xs text-blue-300 hover:text-blue-200"
                          >
                            {student.apoderado_telefono ? "Editar" : "Agregar"}
                          </button>
                        </td>
                        <td className="px-3 py-3 text-zinc-400">
                          {student.ultima_prediccion
                            ? new Date(student.ultima_prediccion).toLocaleString()
                            : "—"}
                        </td>
                        <td className="px-3 py-3">
                          <button
                            type="button"
                            onClick={() => startAnalysisForStudent(student)}
                            className="rounded-lg border border-blue-600/40 bg-blue-600/10 px-3 py-1.5 text-xs font-medium text-blue-100 hover:bg-blue-600/20"
                          >
                            Analizar
                          </button>
                          <button
                            type="button"
                            onClick={() => handleEnrollWorkshop(student)}
                            className="ml-1 rounded-lg border border-purple-600/40 bg-purple-600/10 px-3 py-1.5 text-xs font-medium text-purple-100 hover:bg-purple-600/20"
                          >
                            Taller
                          </button>
                          <button
                            type="button"
                            onClick={() => openFichaConvivencia(student)}
                            className="ml-1 rounded-lg border border-rose-600/40 bg-rose-600/10 px-3 py-1.5 text-xs font-medium text-rose-100 hover:bg-rose-600/20"
                          >
                            Ficha
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            </section>
          </div>
        )}

        {activeTab === "intervenciones" && (
          <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-white">
                  Intervenciones — {interventionsList.length}
                  {interventionsTotal > interventionsList.length
                    ? ` de ${interventionsTotal}`
                    : ""}
                </h2>
                <p className="mt-1 text-sm text-zinc-500">
                  Seguimientos registrados desde Alertas. Período:{" "}
                  {formatInterventionPeriod(interventionFilters)}.
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <label className="block">
                <span className="mb-1 block text-xs text-zinc-400">Desde</span>
                <input
                  type="date"
                  name="desde"
                  value={interventionFilters.desde}
                  onChange={handleInterventionFilterChange}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-400"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-zinc-400">Hasta</span>
                <input
                  type="date"
                  name="hasta"
                  value={interventionFilters.hasta}
                  onChange={handleInterventionFilterChange}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-400"
                />
              </label>
              <div className="flex flex-wrap items-end gap-2 md:col-span-2">
                <button
                  type="button"
                  onClick={() => applyInterventionPreset("mes")}
                  className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 hover:border-blue-500/50"
                >
                  Este mes
                </button>
                <button
                  type="button"
                  onClick={() => applyInterventionPreset("30d")}
                  className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 hover:border-blue-500/50"
                >
                  Últimos 30 días
                </button>
                <button
                  type="button"
                  onClick={() => applyInterventionPreset("90d")}
                  className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 hover:border-blue-500/50"
                >
                  Últimos 90 días
                </button>
              </div>
            </div>

            {interventionMessage && (
              <p className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
                {interventionMessage}
              </p>
            )}
            {interventionsList.length === 0 ? (
              <p className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-500">
                No hay intervenciones en este período. Amplía el rango de fechas o registra una
                  acción desde Alertas.
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                {interventionsList.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-zinc-100">{item.titulo}</p>
                      <span
                        className={`rounded-full border px-3 py-1 text-xs ${
                          item.estado === "cerrada"
                            ? "border-emerald-500/40 text-emerald-200"
                            : "border-amber-500/40 text-amber-200"
                        }`}
                      >
                        {INTERVENCION_ESTADO_LABELS[item.estado] || item.estado}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-zinc-400">{item.nombre_estudiante}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {new Date(item.created_at).toLocaleString()} ·{" "}
                      {INTERVENCION_TIPO_LABELS[item.tipo] || item.tipo}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleDeriveFromIntervention(item)}
                        className="rounded-lg border border-rose-600/40 bg-rose-600/10 px-3 py-1.5 text-xs text-rose-200 hover:bg-rose-600/20"
                      >
                        Derivar externo
                      </button>
                      {item.estado === "pendiente" && (
                        <button
                          type="button"
                          onClick={() => handleCompleteIntervention(item.id)}
                          disabled={loading}
                          className="rounded-lg border border-emerald-600/40 bg-emerald-600/10 px-3 py-1.5 text-xs text-emerald-200 hover:bg-emerald-600/20 disabled:opacity-60"
                        >
                          Marcar como realizada
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {activeTab === "reforzamiento" && (
          <ReforzamientoPanel
            cursos={cursosReforzamiento}
            selectedCursoId={selectedCursoId}
            onSelectCurso={setSelectedCursoId}
            detalle={cursoDetalle}
            loading={reforzamientoLoading}
            message={reforzamientoMessage}
            pendingEnroll={pendingEnroll}
            onConfirmEnroll={handleConfirmEnroll}
            onCancelEnroll={() => setPendingEnroll(null)}
            sessionForm={sessionForm}
            onSessionFormChange={setSessionForm}
            onCreateSession={handleCreateSession}
            materialLinkForm={materialLinkForm}
            onMaterialLinkFormChange={setMaterialLinkForm}
            onAddMaterialLink={handleAddMaterialLink}
            materialFileTitle={materialFileTitle}
            onMaterialFileTitleChange={setMaterialFileTitle}
            materialFileRef={materialFileRef}
            onUploadMaterialFile={handleUploadMaterialFile}
            onUpdateInscripcion={handleUpdateInscripcion}
            onDownloadMaterial={handleDownloadMaterial}
            enrollPickerOpen={enrollPickerOpen}
            onOpenEnrollPicker={handleOpenEnrollPicker}
            onCloseEnrollPicker={() => setEnrollPickerOpen(false)}
            enrollRiskFilter={enrollRiskFilter}
            onEnrollRiskFilterChange={setEnrollRiskFilter}
            enrollSearch={enrollSearch}
            onEnrollSearchChange={setEnrollSearch}
            enrollCandidates={enrollCandidates}
            onSelectStudentForEnroll={handleSelectStudentForEnroll}
          />
        )}

        {activeTab === "convivencia" && (
          <ConvivenciaPanel
            derivaciones={derivacionesList}
            derivacionesTotal={derivacionesTotal}
            derivacionFilters={derivacionFilters}
            onDerivacionFilterChange={setDerivacionFilters}
            incidencias={incidenciasList}
            incidenciasTotal={incidenciasTotal}
            incidenciaFilters={incidenciaFilters}
            onIncidenciaFilterChange={setIncidenciaFilters}
            students={convivenciaStudents}
            derivacionForm={derivacionForm}
            onDerivacionFormChange={setDerivacionForm}
            incidenciaForm={incidenciaForm}
            onIncidenciaFormChange={setIncidenciaForm}
            pendingDerivacion={pendingDerivacion}
            onCancelPendingDerivacion={() => setPendingDerivacion(null)}
            onCreateDerivacion={handleCreateDerivacion}
            onCreateIncidencia={handleCreateIncidencia}
            onUpdateDerivacionEstado={handleUpdateDerivacionEstado}
            loading={convivenciaLoading}
            message={convivenciaMessage}
          />
        )}

        {activeTab === "indicadores" && (
          <IndicadoresPanel
            anio={indicadorAnio}
            mes={indicadorMes}
            onAnioChange={setIndicadorAnio}
            onMesChange={setIndicadorMes}
            indicadores={indicadoresList}
            loading={indicadoresLoading}
            message={indicadoresMessage}
            onCalcular={handleCalcularIndicadores}
            esAdmin={user?.rol === "admin"}
          />
        )}
      </section>
    </main>
  );
}

function ConvivenciaPanel({
  derivaciones,
  derivacionesTotal,
  derivacionFilters,
  onDerivacionFilterChange,
  incidencias,
  incidenciasTotal,
  incidenciaFilters,
  onIncidenciaFilterChange,
  students,
  derivacionForm,
  onDerivacionFormChange,
  incidenciaForm,
  onIncidenciaFormChange,
  pendingDerivacion,
  onCancelPendingDerivacion,
  onCreateDerivacion,
  onCreateIncidencia,
  onUpdateDerivacionEstado,
  loading,
  message,
}) {
  const selectedDerivacionStudent = students.find(
    (item) => String(item.id) === String(derivacionForm.estudiante_id)
  );
  const selectedIncidenciaStudent = students.find(
    (item) => String(item.id) === String(incidenciaForm.estudiante_id)
  );

  return (
    <div className="space-y-4">
      {message && (
        <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {message}
        </p>
      )}

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
        <h2 className="text-base font-semibold text-white">Derivaciones externas</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Casos derivados a UGEL, DEMUNA, salud u otras entidades. Pueden vincularse a una
          intervención previa.
        </p>

        {pendingDerivacion && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4">
            <p className="text-sm text-rose-100">
              Derivación pendiente para <strong>{pendingDerivacion.nombre}</strong>
              {pendingDerivacion.intervencion_id
                ? ` (intervención #${pendingDerivacion.intervencion_id})`
                : ""}
              .
            </p>
            <button
              type="button"
              onClick={onCancelPendingDerivacion}
              className="mt-2 text-xs text-zinc-400 hover:text-zinc-200"
            >
              Cancelar derivación pendiente
            </button>
          </div>
        )}

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Alumno</span>
            <select
              value={derivacionForm.estudiante_id}
              onChange={(e) =>
                onDerivacionFormChange({ ...derivacionForm, estudiante_id: e.target.value })
              }
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="">Selecciona un alumno</option>
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.nombre} {student.dni ? `(DNI ${student.dni})` : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Entidad destino</span>
            <select
              value={derivacionForm.entidad_destino}
              onChange={(e) =>
                onDerivacionFormChange({ ...derivacionForm, entidad_destino: e.target.value })
              }
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              {Object.entries(ENTIDAD_DESTINO_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1 block text-xs text-zinc-400">Motivo de derivación</span>
            <textarea
              value={derivacionForm.motivo}
              onChange={(e) =>
                onDerivacionFormChange({ ...derivacionForm, motivo: e.target.value })
              }
              rows={3}
              placeholder="Describe el motivo (mínimo 5 caracteres)"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1 block text-xs text-zinc-400">Observaciones (opcional)</span>
            <textarea
              value={derivacionForm.observaciones}
              onChange={(e) =>
                onDerivacionFormChange({ ...derivacionForm, observaciones: e.target.value })
              }
              rows={2}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
        </div>
        {selectedDerivacionStudent && (
          <p className="mt-2 text-xs text-zinc-500">
            Riesgo: {selectedDerivacionStudent.ultimo_nivel_riesgo || "sin dato"} · Sección:{" "}
            {selectedDerivacionStudent.seccion_etiqueta || "—"}
          </p>
        )}
        <button
          type="button"
          onClick={onCreateDerivacion}
          disabled={loading || !derivacionForm.estudiante_id || derivacionForm.motivo.trim().length < 5}
          className="mt-3 rounded-lg border border-rose-600/40 bg-rose-600/10 px-4 py-2 text-sm text-rose-100 disabled:opacity-60"
        >
          Registrar derivación
        </button>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Filtrar por estado</span>
            <select
              value={derivacionFilters.estado}
              onChange={(e) => onDerivacionFilterChange({ estado: e.target.value })}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="">Todos</option>
              {Object.entries(ESTADO_DERIVACION_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 space-y-2">
          {!derivaciones.length ? (
            <p className="text-sm text-zinc-500">Sin derivaciones registradas.</p>
          ) : (
            derivaciones.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-zinc-100">{item.estudiante_nombre}</p>
                  <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-300">
                    {ESTADO_DERIVACION_LABELS[item.estado] || item.estado}
                  </span>
                </div>
                <p className="mt-1 text-sm text-zinc-300">
                  {ENTIDAD_DESTINO_LABELS[item.entidad_destino] || item.entidad_destino}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {item.fecha_derivacion}
                  {item.intervencion_id ? ` · Intervención #${item.intervencion_id}` : ""}
                </p>
                <p className="mt-2 text-sm text-zinc-400">{item.motivo}</p>
                {item.estado === "pendiente" && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => onUpdateDerivacionEstado(item.id, "en_proceso")}
                      className="rounded-lg border border-amber-600/40 bg-amber-600/10 px-2 py-1 text-xs text-amber-200"
                    >
                      Marcar en proceso
                    </button>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => onUpdateDerivacionEstado(item.id, "cerrada")}
                      className="rounded-lg border border-emerald-600/40 bg-emerald-600/10 px-2 py-1 text-xs text-emerald-200"
                    >
                      Cerrar caso
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
          {derivacionesTotal > derivaciones.length && (
            <p className="text-xs text-zinc-500">
              Mostrando {derivaciones.length} de {derivacionesTotal} derivaciones.
            </p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
        <h2 className="text-base font-semibold text-white">Incidencias de convivencia</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Registro de bullying, violencia, disciplina y otros eventos de convivencia escolar.
        </p>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Alumno</span>
            <select
              value={incidenciaForm.estudiante_id}
              onChange={(e) =>
                onIncidenciaFormChange({ ...incidenciaForm, estudiante_id: e.target.value })
              }
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="">Selecciona un alumno</option>
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.nombre} {student.dni ? `(DNI ${student.dni})` : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Tipo de incidencia</span>
            <select
              value={incidenciaForm.tipo_incidencia}
              onChange={(e) =>
                onIncidenciaFormChange({ ...incidenciaForm, tipo_incidencia: e.target.value })
              }
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              {Object.entries(TIPO_INCIDENCIA_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Severidad</span>
            <select
              value={incidenciaForm.severidad}
              onChange={(e) =>
                onIncidenciaFormChange({ ...incidenciaForm, severidad: e.target.value })
              }
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              {Object.entries(SEVERIDAD_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Fecha del incidente</span>
            <input
              type="date"
              value={incidenciaForm.fecha_incidencia}
              onChange={(e) =>
                onIncidenciaFormChange({ ...incidenciaForm, fecha_incidencia: e.target.value })
              }
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1 block text-xs text-zinc-400">Descripción</span>
            <textarea
              value={incidenciaForm.descripcion}
              onChange={(e) =>
                onIncidenciaFormChange({ ...incidenciaForm, descripcion: e.target.value })
              }
              rows={3}
              placeholder="Qué ocurrió, dónde y quiénes estuvieron involucrados (mínimo 10 caracteres)"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1 block text-xs text-zinc-400">Acciones tomadas (opcional)</span>
            <textarea
              value={incidenciaForm.acciones_tomadas}
              onChange={(e) =>
                onIncidenciaFormChange({ ...incidenciaForm, acciones_tomadas: e.target.value })
              }
              rows={2}
              placeholder="Entrevistas, citación a apoderados, medidas aplicadas"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
        </div>
        {selectedIncidenciaStudent && (
          <p className="mt-2 text-xs text-zinc-500">
            Sección: {selectedIncidenciaStudent.seccion_etiqueta || "—"}
          </p>
        )}
        <button
          type="button"
          onClick={onCreateIncidencia}
          disabled={
            loading || !incidenciaForm.estudiante_id || incidenciaForm.descripcion.trim().length < 10
          }
          className="mt-3 rounded-lg border border-orange-600/40 bg-orange-600/10 px-4 py-2 text-sm text-orange-100 disabled:opacity-60"
        >
          Registrar incidencia
        </button>

        <div className="mt-4">
          <label className="block">
            <span className="mb-1 block text-xs text-zinc-400">Filtrar por severidad</span>
            <select
              value={incidenciaFilters.severidad}
              onChange={(e) => onIncidenciaFilterChange({ severidad: e.target.value })}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="">Todas</option>
              {Object.entries(SEVERIDAD_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 space-y-2">
          {!incidencias.length ? (
            <p className="text-sm text-zinc-500">Sin incidencias registradas.</p>
          ) : (
            incidencias.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-zinc-100">{item.estudiante_nombre}</p>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs ${
                      item.severidad === "critica" || item.severidad === "alta"
                        ? "border-red-500/40 text-red-200"
                        : item.severidad === "media"
                          ? "border-amber-500/40 text-amber-200"
                          : "border-zinc-600 text-zinc-400"
                    }`}
                  >
                    {SEVERIDAD_LABELS[item.severidad] || item.severidad}
                  </span>
                </div>
                <p className="mt-1 text-sm text-zinc-300">
                  {TIPO_INCIDENCIA_LABELS[item.tipo_incidencia] || item.tipo_incidencia}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {item.fecha_incidencia}
                  {item.docente_nombre ? ` · Reporta: ${item.docente_nombre}` : ""}
                </p>
                <p className="mt-2 text-sm text-zinc-400">{item.descripcion}</p>
                {item.acciones_tomadas && (
                  <p className="mt-2 text-xs text-zinc-500">Acciones: {item.acciones_tomadas}</p>
                )}
              </div>
            ))
          )}
          {incidenciasTotal > incidencias.length && (
            <p className="text-xs text-zinc-500">
              Mostrando {incidencias.length} de {incidenciasTotal} incidencias.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

function ReforzamientoPanel({
  cursos,
  selectedCursoId,
  onSelectCurso,
  detalle,
  loading,
  message,
  pendingEnroll,
  onConfirmEnroll,
  onCancelEnroll,
  sessionForm,
  onSessionFormChange,
  onCreateSession,
  materialLinkForm,
  onMaterialLinkFormChange,
  onAddMaterialLink,
  materialFileTitle,
  onMaterialFileTitleChange,
  materialFileRef,
  onUploadMaterialFile,
  onUpdateInscripcion,
  onDownloadMaterial,
  enrollPickerOpen,
  onOpenEnrollPicker,
  onCloseEnrollPicker,
  enrollRiskFilter,
  onEnrollRiskFilterChange,
  enrollSearch,
  onEnrollSearchChange,
  enrollCandidates,
  onSelectStudentForEnroll,
}) {
  const curso = detalle?.curso;
  const selectedCurso = cursos.find((item) => String(item.id) === String(selectedCursoId));
  const areaMismatch =
    pendingEnroll &&
    selectedCurso &&
    selectedCurso.area &&
    pendingEnroll.area_sugerida &&
    selectedCurso.area !== pendingEnroll.area_sugerida;

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
        <h2 className="text-base font-semibold text-white">Talleres de reforzamiento</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Inscribe alumnos en riesgo, registra sesiones y comparte materiales de estudio.
        </p>

        {pendingEnroll && (
          <div className="mt-4 rounded-xl border border-purple-500/30 bg-purple-500/10 p-4">
            <p className="text-sm text-purple-100">
              Inscribir a <strong>{pendingEnroll.nombre}</strong> en un taller (
              {MOTIVO_INSCRIPCION_LABELS[pendingEnroll.motivo]} · área sugerida:{" "}
              {AREA_CURSO_LABELS[pendingEnroll.area_sugerida]}
              {pendingEnroll.riesgo ? ` · riesgo ${pendingEnroll.riesgo}` : ""}).
            </p>
            {areaMismatch && (
              <p className="mt-2 text-xs text-amber-200">
                El taller seleccionado ({selectedCurso.area_label}) no coincide con el área sugerida. Puedes
                cambiar de taller antes de confirmar.
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onConfirmEnroll}
                disabled={loading || !selectedCursoId}
                className="rounded-lg border border-purple-500/40 bg-purple-500/20 px-4 py-2 text-sm text-purple-100 hover:bg-purple-500/30 disabled:opacity-60"
              >
                Confirmar inscripción
              </button>
              <button
                type="button"
                onClick={onCancelEnroll}
                className="rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-700"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {message && (
          <p className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
            {message}
          </p>
        )}

        {cursos.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No hay talleres configurados para este año escolar.</p>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {cursos.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectCurso(String(item.id))}
                className={`rounded-xl border p-4 text-left transition ${
                  String(item.id) === String(selectedCursoId)
                    ? "border-blue-500/50 bg-blue-500/10"
                    : "border-zinc-800 bg-zinc-950/60 hover:border-zinc-700"
                }`}
              >
                <p className="font-medium text-zinc-100">{item.nombre}</p>
                <p className="mt-1 text-xs text-zinc-400">
                  {item.area_label} · {item.inscritos}/{item.cupo_max} inscritos ·{" "}
                  {item.cupos_disponibles} cupos libres
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {item.fecha_inicio || "—"} al {item.fecha_fin || "—"} · {item.estado}
                </p>
              </button>
            ))}
          </div>
        )}
      </section>

      {curso && (
        <>
          <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-white">Alumnos inscritos — {curso.nombre}</h3>
              <button
                type="button"
                onClick={onOpenEnrollPicker}
                disabled={loading || !curso.cupos_disponibles}
                className="rounded-lg border border-purple-600/40 bg-purple-600/10 px-3 py-1.5 text-xs font-medium text-purple-100 hover:bg-purple-600/20 disabled:opacity-60"
              >
                Inscribir alumno
              </button>
            </div>

            {enrollPickerOpen && (
              <div className="mt-3 rounded-xl border border-purple-500/30 bg-purple-500/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-purple-100">Buscar alumno por riesgo</p>
                  <button
                    type="button"
                    onClick={onCloseEnrollPicker}
                    className="text-xs text-zinc-400 hover:text-zinc-200"
                  >
                    Cerrar
                  </button>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <label className="block md:col-span-1">
                    <span className="mb-1 block text-xs text-zinc-400">Filtro de riesgo</span>
                    <select
                      value={enrollRiskFilter}
                      onChange={(e) => onEnrollRiskFilterChange(e.target.value)}
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                    >
                      <option value="con_riesgo">Alto o medio</option>
                      <option value="alto">Solo riesgo alto</option>
                      <option value="medio">Solo riesgo medio</option>
                      <option value="rendimiento">Nota C (mat. o leng.)</option>
                      <option value="todos">Todos los alumnos</option>
                    </select>
                  </label>
                  <label className="block md:col-span-2">
                    <span className="mb-1 block text-xs text-zinc-400">Buscar por nombre o DNI</span>
                    <input
                      type="search"
                      value={enrollSearch}
                      onChange={(e) => onEnrollSearchChange(e.target.value)}
                      placeholder="Ej: Garcia o 12345678"
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                    />
                  </label>
                </div>
                <div className="mt-3 max-h-56 space-y-2 overflow-y-auto">
                  {!enrollCandidates.length ? (
                    <p className="text-sm text-zinc-500">
                      No hay alumnos disponibles con este filtro (o ya están inscritos en este taller).
                    </p>
                  ) : (
                    enrollCandidates.map((student) => (
                      <button
                        key={student.id}
                        type="button"
                        onClick={() => onSelectStudentForEnroll(student)}
                        className="flex w-full items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-left hover:border-purple-500/40 hover:bg-purple-500/5"
                      >
                        <div>
                          <p className="text-sm text-zinc-100">{student.nombre}</p>
                          <p className="text-xs text-zinc-500">
                            DNI {student.dni || "—"} · Mat {student.nota_matematica || "—"} · Leng{" "}
                            {student.nota_lenguaje || "—"}
                          </p>
                        </div>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-xs ${
                            student.ultimo_nivel_riesgo === "alto"
                              ? "border-red-500/40 text-red-200"
                              : student.ultimo_nivel_riesgo === "medio"
                                ? "border-amber-500/40 text-amber-200"
                                : "border-zinc-600 text-zinc-400"
                          }`}
                        >
                          {student.ultimo_nivel_riesgo || "sin dato"}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}

            {!detalle?.inscripciones?.length ? (
              <p className="mt-3 text-sm text-zinc-500">Sin inscripciones en este taller.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {detalle.inscripciones.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-col gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="font-medium text-zinc-100">{item.estudiante_nombre}</p>
                      <p className="text-xs text-zinc-400">
                        DNI {item.dni || "—"} · {MOTIVO_INSCRIPCION_LABELS[item.motivo] || item.motivo}
                        {item.prediccion_id ? ` · Predicción #${item.prediccion_id}` : ""}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-300">
                        {RESULTADO_INSCRIPCION_LABELS[item.resultado] || item.resultado || "En proceso"}
                      </span>
                      {item.resultado === "en_proceso" && (
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() => onUpdateInscripcion(item.id, "mejoro")}
                          className="rounded-lg border border-emerald-600/40 bg-emerald-600/10 px-2 py-1 text-xs text-emerald-200"
                        >
                          Marcó mejora
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h3 className="text-sm font-semibold text-white">Sesiones del taller</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-4">
              <label className="block">
                <span className="mb-1 block text-xs text-zinc-400">Fecha</span>
                <input
                  type="date"
                  value={sessionForm.fecha_sesion}
                  onChange={(e) => onSessionFormChange({ ...sessionForm, fecha_sesion: e.target.value })}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                />
              </label>
              <label className="block md:col-span-2">
                <span className="mb-1 block text-xs text-zinc-400">Tema</span>
                <input
                  type="text"
                  value={sessionForm.tema}
                  onChange={(e) => onSessionFormChange({ ...sessionForm, tema: e.target.value })}
                  placeholder="Ej: Fracciones equivalentes"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-zinc-400">Modalidad</span>
                <select
                  value={sessionForm.modalidad}
                  onChange={(e) => onSessionFormChange({ ...sessionForm, modalidad: e.target.value })}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                >
                  <option value="presencial">Presencial</option>
                  <option value="virtual">Virtual</option>
                  <option value="mixta">Mixta</option>
                </select>
              </label>
            </div>
            <button
              type="button"
              onClick={onCreateSession}
              disabled={loading}
              className="mt-3 rounded-lg border border-blue-600/40 bg-blue-600/10 px-4 py-2 text-sm text-blue-100 disabled:opacity-60"
            >
              Registrar sesión
            </button>
            <div className="mt-4 space-y-2">
              {!detalle?.sesiones?.length ? (
                <p className="text-sm text-zinc-500">Aún no hay sesiones registradas.</p>
              ) : (
                detalle.sesiones.map((sesion) => (
                  <div key={sesion.id} className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2">
                    <p className="text-sm text-zinc-100">{sesion.tema}</p>
                    <p className="text-xs text-zinc-500">
                      {sesion.fecha_sesion} · {sesion.modalidad} · asistieron {sesion.asistencia_registrada}
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
            <h3 className="text-sm font-semibold text-white">Biblioteca del curso</h3>
            <div className="mt-2 rounded-lg border border-emerald-600/30 bg-emerald-600/10 px-3 py-2 text-xs text-emerald-100">
              <strong>Zona rural:</strong> prioriza PDF y video descargable (funcionan sin internet). Los
              enlaces web requieren conexión y son opcionales.
            </div>

            <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/40 p-3">
              <p className="text-xs font-medium text-emerald-200">
                Recomendado offline — PDF, DOC o video MP4
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs text-zinc-400">Título del archivo</span>
                  <input
                    type="text"
                    value={materialFileTitle}
                    onChange={(e) => onMaterialFileTitleChange(e.target.value)}
                    placeholder="Ficha de ejercicios"
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-zinc-400">Subir archivo (PDF, DOC, MP4)</span>
                  <input
                    ref={materialFileRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.mp4"
                    onChange={onUploadMaterialFile}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                  />
                </label>
              </div>
              <p className="mt-2 text-xs text-zinc-500">Max. 50 MB por archivo. Ideal para copiar a USB o imprimir.</p>
            </div>

            <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/40 p-3">
              <p className="text-xs font-medium text-amber-200">Opcional — requiere internet</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs text-zinc-400">Título del enlace</span>
                  <input
                    type="text"
                    value={materialLinkForm.titulo}
                    onChange={(e) => onMaterialLinkFormChange({ ...materialLinkForm, titulo: e.target.value })}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-zinc-400">URL (YouTube, Drive, etc.)</span>
                  <input
                    type="url"
                    value={materialLinkForm.url}
                    onChange={(e) => onMaterialLinkFormChange({ ...materialLinkForm, url: e.target.value })}
                    placeholder="https://..."
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                  />
                </label>
              </div>
              <button
                type="button"
                onClick={onAddMaterialLink}
                disabled={loading}
                className="mt-3 rounded-lg border border-amber-600/40 bg-amber-600/10 px-4 py-2 text-sm text-amber-200 disabled:opacity-60"
              >
                Agregar enlace
              </button>
            </div>

            <div className="mt-4 space-y-2">
              {!detalle?.materiales?.length ? (
                <p className="text-sm text-zinc-500">Sin materiales publicados.</p>
              ) : (
                detalle.materiales.map((material) => (
                  <div
                    key={material.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2"
                  >
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm text-zinc-100">{material.titulo}</p>
                        {material.tipo === "enlace" ? (
                          <span className="rounded-full border border-amber-500/40 px-2 py-0.5 text-[10px] uppercase tracking-wide text-amber-200">
                            Requiere internet
                          </span>
                        ) : (
                          <span className="rounded-full border border-emerald-500/40 px-2 py-0.5 text-[10px] uppercase tracking-wide text-emerald-200">
                            Offline
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500">
                        {material.tipo === "enlace" ? "Enlace web" : material.nombre_archivo || "Archivo"}
                        {material.docente_nombre ? ` · ${material.docente_nombre}` : ""}
                      </p>
                    </div>
                    {material.tipo === "enlace" && material.url ? (
                      <a
                        href={material.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-blue-300 hover:text-blue-200"
                        title="Requiere conexión a internet"
                      >
                        Abrir enlace
                      </a>
                    ) : (
                      <button
                        type="button"
                        onClick={() => onDownloadMaterial(material)}
                        className="text-xs text-blue-300 hover:text-blue-200"
                      >
                        Descargar
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function PriorityAlertsList({
  alerts,
  loading,
  activeStudent,
  onAnalyze,
  onRegisterIntervention,
  onCopyContact,
  onAlertStatusChange,
  onEnrollWorkshop,
}) {
  const [expandedId, setExpandedId] = useState(null);
  const [historial, setHistorial] = useState({});
  const [historialLoading, setHistorialLoading] = useState(null);

  const toggleHistorial = async (alertaId) => {
    if (expandedId === alertaId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(alertaId);
    if (!historial[alertaId]) {
      setHistorialLoading(alertaId);
      try {
        const data = await authFetchJson(`${API_BASE}/api/alertas/${alertaId}/historial`);
        setHistorial((prev) => ({ ...prev, [alertaId]: data.seguimiento || [] }));
      } catch {
        setHistorial((prev) => ({ ...prev, [alertaId]: [] }));
      } finally {
        setHistorialLoading(null);
      }
    }
  };

  if (alerts.length === 0) {
    return (
      <p className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-500">
        Sin alertas pendientes. Aparecen cuando un alumno tiene riesgo alto o medio.
      </p>
    );
  }

  return (
    <div className="mt-3 space-y-2">
      {alerts.map((student) => {
        const alertaId = student.alerta_id;
        const isExpanded = expandedId === alertaId;
        const items = historial[alertaId] || [];

        return (
          <div
            key={`${alertaId || student.nombre}-${student.estudiante_id}`}
            className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-200">
                  {student.iniciales || buildInitials(student.nombre)}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate font-medium text-zinc-100">{student.nombre}</p>
                    {student.estado && (
                      <span className="rounded-full border border-amber-500/40 px-2 py-0.5 text-[10px] text-amber-200">
                        {ALERTA_ESTADO_LABELS[student.estado] || student.estado}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-zinc-400">
                    {student.dni ? `DNI ${student.dni} · ` : ""}
                    Asistencia {student.asistencias ?? "—"}% · Mat {student.nota_matematica || "—"} · Leng{" "}
                    {student.nota_lenguaje || "—"}
                  </p>
                  {student.apoderado_telefono ? (
                    <p className="mt-1 text-xs text-emerald-300">
                      {student.apoderado_nombre || "Apoderado"} · {student.apoderado_telefono}
                    </p>
                  ) : (
                    <p className="mt-1 text-xs text-amber-400/90">
                      Sin teléfono de apoderado registrado
                    </p>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
                <RiskBadge level={student.risk_level || student.ultimo_nivel_riesgo} />
                {student.apoderado_telefono && (
                  <button
                    type="button"
                    onClick={() => onCopyContact(student)}
                    className="rounded-lg border border-emerald-600/40 bg-emerald-600/10 px-3 py-1.5 text-sm text-emerald-200 hover:bg-emerald-600/20"
                  >
                    Copiar contacto
                  </button>
                )}
                {alertaId && student.estado === "nueva" && (
                  <button
                    type="button"
                    onClick={() =>
                      onAlertStatusChange(
                        alertaId,
                        "en_revision",
                        "en_revision",
                        "La tutora inició seguimiento de la alerta."
                      )
                    }
                    disabled={loading}
                    className="rounded-lg border border-amber-600/40 bg-amber-600/10 px-3 py-1.5 text-sm text-amber-100 hover:bg-amber-600/20 disabled:opacity-60"
                  >
                    En revisión
                  </button>
                )}
                {alertaId && (
                  <button
                    type="button"
                    onClick={() =>
                      onAlertStatusChange(
                        alertaId,
                        "cerrada",
                        "cierre_manual",
                        "Alerta cerrada sin intervención adicional."
                      )
                    }
                    disabled={loading}
                    className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-60"
                  >
                    Cerrar alerta
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onAnalyze(student)}
                  disabled={loading}
                  className="rounded-lg border border-blue-600/40 bg-blue-600/10 px-3 py-1.5 text-sm text-blue-100 hover:bg-blue-600/20 disabled:opacity-60"
                >
                  {loading ? "Analizando..." : "Analizar"}
                </button>
            <button
              type="button"
              onClick={() => onEnrollWorkshop(student)}
              disabled={loading}
              className="rounded-lg border border-purple-600/40 bg-purple-600/10 px-3 py-1.5 text-sm text-purple-100 hover:bg-purple-600/20 disabled:opacity-60"
            >
              Inscribir en taller
            </button>
            <button
              type="button"
              onClick={() => onRegisterIntervention(student)}
                  disabled={loading}
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading && activeStudent === student.nombre ? "Guardando..." : "Registrar acción"}
                </button>
              </div>
            </div>

            {alertaId && (
              <div className="mt-3 border-t border-zinc-800 pt-3">
                <button
                  type="button"
                  onClick={() => toggleHistorial(alertaId)}
                  className="text-xs text-blue-300 hover:text-blue-200"
                >
                  {isExpanded ? "Ocultar bitácora" : "Ver bitácora de seguimiento"}
                </button>
                {isExpanded && (
                  <div className="mt-2 space-y-2">
                    {historialLoading === alertaId ? (
                      <p className="text-xs text-zinc-500">Cargando bitácora...</p>
                    ) : items.length === 0 ? (
                      <p className="text-xs text-zinc-500">
                        Sin acciones registradas aún en esta alerta.
                      </p>
                    ) : (
                      items.map((entry) => (
                        <div
                          key={entry.id}
                          className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2"
                        >
                          <p className="text-sm text-zinc-200">
                            {SEGUIMIENTO_ACCION_LABELS[entry.accion] || entry.accion}
                          </p>
                          {entry.detalle && (
                            <p className="mt-1 text-xs text-zinc-400">{entry.detalle}</p>
                          )}
                          <p className="mt-1 text-[10px] text-zinc-500">
                            {new Date(entry.fecha_accion).toLocaleString()}
                            {entry.docente_nombre ? ` · ${entry.docente_nombre}` : ""}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ResultPanel({ result, riskLevel, riskStyles, motivationalMessage, onClear }) {
  return (
    <article className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 lg:col-span-2">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-semibold text-white">Resultado</h2>
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

      {result ? (
        <div className={`mt-3 rounded-lg border p-3 ${riskStyles.box}`}>
          <p className="text-xs uppercase tracking-wide text-zinc-400">{result.sourceLabel}</p>
          <p className={`mt-2 text-2xl font-semibold ${riskStyles.text}`}>
            {riskLabel(riskLevel)}
          </p>
          <p className="mt-1 text-sm text-zinc-400">{result.prediction}</p>
          <p className="mt-2 text-sm text-zinc-200">
            Confianza del modelo:{" "}
            {typeof result.confidence === "number"
              ? `${(result.confidence * 100).toFixed(1)}%`
              : "No disponible"}
          </p>
          {typeof result.probabilidad_alto === "number" && (
            <p className="mt-1 text-sm text-zinc-300">
              Probabilidad de riesgo alto: {(result.probabilidad_alto * 100).toFixed(1)}%
            </p>
          )}
          {Array.isArray(result.factores) && result.factores.length > 0 && (
            <ul className="mt-3 space-y-1 border-t border-zinc-700/50 pt-3 text-sm text-zinc-300">
              {result.factores.map((factor) => (
                <li key={factor} className="flex gap-2">
                  <span className="text-orange-400">·</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-sm text-zinc-100">{motivationalMessage}</p>
          {result.storage?.persisted ? (
            <p className="mt-2 text-xs text-zinc-400">Guardado en el historial del estudiante.</p>
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
        <p className="mt-3 text-sm text-zinc-500">
          Busca un alumno y pulsa Analizar y guardar para ver el resultado aquí.
        </p>
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

function SummaryCard({ title, value, tone }) {
  const toneStyles = {
    red: "text-red-400",
    orange: "text-orange-400",
    green: "text-emerald-400",
  };

  return (
    <article className="rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3">
      <p className="text-xs text-zinc-400">{title}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${toneStyles[tone]}`}>{value}</p>
    </article>
  );
}

function Tab({ label, active = false, badge = null, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-medium transition ${
        active
          ? "border-blue-500/50 bg-blue-500/15 text-blue-100 shadow-sm shadow-blue-500/10"
          : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
      }`}
    >
      {label}
      {badge != null && badge > 0 && (
        <span
          className={`rounded-full px-1.5 py-0.5 text-xs tabular-nums ${
            active ? "bg-blue-500/30 text-blue-50" : "bg-orange-500/20 text-orange-200"
          }`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

