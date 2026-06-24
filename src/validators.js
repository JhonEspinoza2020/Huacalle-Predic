export function sanitizeDniInput(value) {
  return String(value || "").replace(/\D/g, "").slice(0, 8);
}

export function sanitizeTelefonoInput(value) {
  return String(value || "").replace(/\D/g, "").slice(0, 9);
}

export function validateDni(dni) {
  const clean = sanitizeDniInput(dni);
  if (clean.length !== 8) {
    return "El DNI debe tener exactamente 8 dígitos.";
  }
  return null;
}

export function validateNombre(nombre) {
  const clean = String(nombre || "").trim().replace(/\s+/g, " ");
  if (clean.length < 3) {
    return "El nombre completo debe tener al menos 3 caracteres.";
  }
  if (clean.length > 120) {
    return "El nombre completo es demasiado largo.";
  }
  return null;
}

export function validateUsername(username) {
  const clean = String(username || "").trim();
  if (clean.length < 3) {
    return "El usuario debe tener al menos 3 caracteres.";
  }
  if (!/^[a-zA-Z0-9._-]+$/.test(clean)) {
    return "El usuario solo puede contener letras, números, punto, guion o guion bajo.";
  }
  return null;
}

export function validatePassword(password) {
  if (!String(password || "").length) {
    return "La contraseña es obligatoria.";
  }
  if (String(password).length < 4) {
    return "La contraseña debe tener al menos 4 caracteres.";
  }
  return null;
}

export function validateTelefono(telefono) {
  const clean = sanitizeTelefonoInput(telefono);
  if (clean.length !== 9) {
    return "El teléfono debe tener 9 dígitos (ej. 987654321).";
  }
  if (!clean.startsWith("9")) {
    return "El teléfono móvil peruano debe comenzar con 9.";
  }
  return null;
}

export function validateAsistencias(value) {
  const n = Number(value);
  if (Number.isNaN(n) || n < 0 || n > 100) {
    return "La asistencia debe estar entre 0 y 100.";
  }
  return null;
}

export function validateParticipacion(value) {
  const n = Number(value);
  if (Number.isNaN(n) || n < 0 || n > 10) {
    return "La participación debe estar entre 0 y 10.";
  }
  return null;
}

export function validateSeccionRequerida(seccionId, misSecciones) {
  if (misSecciones?.length > 0 && !seccionId) {
    return "Selecciona la sección del alumno.";
  }
  return null;
}

const PARENTESCOS_VALIDOS = new Set(["padre", "madre", "apoderado", "tutor", "otro"]);

export function validateParentesco(parentesco) {
  const clean = String(parentesco || "apoderado").trim().toLowerCase();
  if (!PARENTESCOS_VALIDOS.has(clean)) {
    return "Parentesco no válido.";
  }
  return null;
}

export function validateDniOpcional(dni) {
  const clean = sanitizeDniInput(dni);
  if (!clean) return null;
  if (clean.length !== 8) {
    return "El DNI del apoderado debe tener 8 dígitos.";
  }
  return null;
}

export function looksLikeDniQuery(value) {
  const clean = String(value || "").trim();
  return clean.length > 0 && /^\d+$/.test(clean);
}

export function validateBusquedaEstudiante(value) {
  const clean = String(value || "").trim();
  if (!clean) return null;
  if (looksLikeDniQuery(clean)) {
    return validateDni(sanitizeDniInput(clean));
  }
  return null;
}
