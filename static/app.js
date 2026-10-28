const $ = (s, el = document) => el.querySelector(s);

async function api(url, datos) {
  const r = await fetch(url, datos === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos),
  });
  const json = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(json.error || `Error ${r.status}`);
  return json;
}

// ---------- búsqueda y progreso ----------
const form = $("#form-buscar");
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  try {
    await api("/api/buscar", { sector: fd.get("sector"), ciudad: fd.get("ciudad"), fuentes: fd.getAll("fuentes") });
    seguirTrabajo();
  } catch (err) { alert(err.message); }
});

$("#verificar-pendientes")?.addEventListener("click", async (e) => {
  e.preventDefault();
  try { await api("/api/verificar-pendientes", {}); seguirTrabajo(); } catch (err) { alert(err.message); }
});

function seguirTrabajo() {
  const caja = $("#progreso");
  caja.hidden = false;
  form.querySelector("button").disabled = true;
  const tic = async () => {
    const t = await api("/api/trabajo");
    $(".fase", caja).textContent = t.fase || "Terminado";
    $(".barra-progreso span", caja).style.width = t.total ? `${(100 * t.hechos) / t.total}%` : (t.activo ? "8%" : "100%");
    if (t.total) $(".fase", caja).textContent += ` ${t.hechos}/${t.total}`;
    $(".log", caja).innerHTML = t.mensajes.map((m) => `<li>${m.replace(/</g, "&lt;")}</li>`).join("");
    if (t.activo) setTimeout(tic, 1000);
    else setTimeout(() => location.reload(), 1200);
  };
  tic();
}
if (window.TRABAJO_ACTIVO) seguirTrabajo();

// ---------- estado y acciones por fila ----------
document.addEventListener("change", async (e) => {
  if (!e.target.matches(".sel-estado")) return;
  const id = e.target.closest("tr").dataset.id;
  try { await api(`/api/negocio/${id}/estado`, { estado: e.target.value }); e.target.closest("tr").className = `estado-${e.target.value}`; }
  catch (err) { alert(err.message); }
});

document.addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-accion]");
  if (!b) return;
  const id = b.closest("tr").dataset.id;
  if (b.dataset.accion === "reverificar") {
    b.disabled = true;
    try { await api(`/api/negocio/${id}/reverificar`, {}); location.reload(); }
    catch (err) { alert(err.message); b.disabled = false; }
  } else if (b.dataset.accion === "mensaje") {
    abrirModal(id, b.dataset.tipo);
  }
});

// ---------- modal de mensaje ----------
const modal = $("#modal");
let actual = null;

async function abrirModal(id, tipo, canal) {
  $("#m-error").textContent = "";
  try {
    const q = new URLSearchParams({ tipo, ...(canal ? { canal } : {}) });
    const m = await api(`/api/negocio/${id}/mensaje?${q}`);
    actual = { id, ...m };
  } catch (err) { alert(err.message); return; }
  const m = actual;
  $("#m-nombre").textContent = m.nombre;
  $("#m-canales").innerHTML = m.canales.filter((c) => c !== "llamar").map((c) =>
    `<button type="button" class="btn ${c === m.canal ? "activo" : ""}" data-canal="${c}">${c === "email" ? "Email" : "WhatsApp"}</button>`).join("");
  $("#m-canales").querySelectorAll("button").forEach((btn) =>
    btn.addEventListener("click", () => abrirModal(id, tipo, btn.dataset.canal)));
  $("#m-destino").textContent = m.canal === "email" ? `Para: ${m.email}` : `WhatsApp: ${m.telefono_bonito}`;
  $("#m-asunto-wrap").hidden = m.canal !== "email";
  $("#m-asunto").value = m.asunto;
  $("#m-texto").value = m.texto;
  $("#m-enviar").textContent = m.canal === "email" ? (m.smtp ? "Enviar email" : "Abrir en mi correo") : "Abrir WhatsApp";
  if (!modal.open) modal.showModal();
}

$("#m-enviar").addEventListener("click", async () => {
  const m = actual, boton = $("#m-enviar");
  const datos = { asunto: $("#m-asunto").value, texto: $("#m-texto").value, tipo: m.tipo, canal: m.canal };
  $("#m-error").textContent = "";
  boton.disabled = true;
  // Abrimos la pestaña ya (en el clic) para que el navegador no la bloquee
  const ventana = m.canal === "whatsapp" ? window.open("", "_blank") : null;
  try {
    if (m.canal === "email" && m.smtp) {
      await api(`/api/negocio/${m.id}/email`, datos);
    } else {
      const r = await api(`/api/negocio/${m.id}/registrar`, datos);
      if (ventana) ventana.location = r.enlace; else location.href = r.enlace;
    }
    modal.close();
    setTimeout(() => location.reload(), 400);
  } catch (err) {
    ventana?.close();
    $("#m-error").textContent = err.message;
  } finally { boton.disabled = false; }
});
