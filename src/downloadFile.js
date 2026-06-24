function isTauriRuntime() {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export async function downloadBlob(blob, filename) {
  if (isTauriRuntime()) {
    const { invoke } = await import("@tauri-apps/api/core");
    const bytes = Array.from(new Uint8Array(await blob.arrayBuffer()));
    const savedPath = await invoke("save_download", {
      bytes,
      suggestedName: filename,
    });
    if (!savedPath) {
      return { cancelled: true };
    }
    return { cancelled: false, path: savedPath };
  }

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return { cancelled: false };
}
