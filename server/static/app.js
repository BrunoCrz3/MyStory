/* Taller de novelas: cuatro pantallas, sin compilar y sin librerias.
   Nada de jerga en lo que se ve: el usuario no tiene por que saber que es un
   beat, un n-grama ni una severidad. */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const dinero = (n) =>
  (Number(n) || 0).toLocaleString("es-ES", { minimumFractionDigits: 2,
                                             maximumFractionDigits: 2 }) + " $";

const hora = (iso) => {
  if (!iso) return "";
  try { return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit",
                                                           minute: "2-digit" }); }
  catch { return ""; }
};

async function traer(url, opciones) {
  const r = await fetch(url, opciones);
  if (!r.ok) {
    let detalle = r.statusText;
    try { detalle = (await r.json()).detail || detalle; } catch {}
    throw new Error(detalle);
  }
  return r.json();
}

/* ------------------------------------------------ navegacion ------------ */

function mostrar(nombre) {
  $$(".pantalla").forEach((s) => s.classList.toggle("visible", s.id === nombre));
  $$("nav button").forEach((b) => b.classList.toggle("activa",
                                                     b.dataset.pantalla === nombre));
  if (nombre === "lector") cargarListaNovelas($("#novela"), pintarLector);
  if (nombre === "coste") cargarListaNovelas($("#novela-coste"), pintarCoste);
  if (nombre === "progreso") escuchar();
}

$$("nav button").forEach((b) =>
  b.addEventListener("click", () => mostrar(b.dataset.pantalla)));

/* ------------------------------------------------ 1. nueva novela ------- */

(async function prepararFormulario() {
  try {
    const c = await traer("/api/configuracion");
    $("#premisa").value = c.premisa || "";
    $("#capitulos").value = c.capitulos || 3;
    $("#objetivo").value = c.objetivo || 4;
    $("#ayuda-objetivo").textContent =
      c.unidad === "lineas" ? "Se mide en líneas de texto."
                            : `Se mide en ${c.unidad}.`;
    $("#aviso-tope").textContent =
      `La generación se detiene sola si llega a ${dinero(c.tope_usd)}, ` +
      `para que no se dispare el gasto.`;
  } catch (e) { /* el formulario funciona igual con los valores en blanco */ }
})();

$("#formulario").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const boton = $("#generar");
  const error = $("#error-nueva");
  error.hidden = true;
  boton.disabled = true;
  boton.textContent = "Arrancando…";
  try {
    await traer("/api/novelas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        premisa: $("#premisa").value.trim(),
        capitulos: Number($("#capitulos").value),
        objetivo: Number($("#objetivo").value),
      }),
    });
    $("#bitacora").innerHTML = "";
    mostrar("progreso");
  } catch (e) {
    error.textContent = e.message;
    error.hidden = false;
  } finally {
    boton.disabled = false;
    boton.textContent = "Escribir la novela";
  }
});

/* ------------------------------------------------ 2. progreso ----------- */

let fuente = null;
let reescrituras = 0;

function anotar(texto, malo, ts) {
  const lista = $("#bitacora");
  $$("#bitacora li").forEach((l) => l.classList.remove("ultima"));
  const li = document.createElement("li");
  li.className = "ultima" + (malo ? " malo" : "");
  li.textContent = texto;
  const cuando = document.createElement("span");
  cuando.className = "hora";
  cuando.textContent = hora(ts);
  li.appendChild(cuando);
  lista.appendChild(li);
  li.scrollIntoView({ block: "nearest" });
}

function escuchar() {
  if (fuente) return;
  fuente = new EventSource("/api/novelas/actual/eventos");
  fuente.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    if (d.tipo === "paso") {
      if (d.evento === "reescritura" || d.evento === "parche") reescrituras++;
      anotar(d.texto, d.evento === "escalado", d.ts);
      if (d.evento === "fase_inicio" || d.evento === "capitulo_inicio" ||
          d.evento === "borrador") $("#p-fase").textContent = d.texto;
      $("#p-reescrituras").textContent = reescrituras;
    } else if (d.tipo === "estado") {
      $("#p-capitulos").textContent = (d.capitulos_escritos || []).length;
      $("#p-coste").textContent = dinero(d.gastado_usd);
      $("#p-tope").textContent = `de ${dinero(d.tope_usd)} como máximo`;
      $("#detener").hidden = !d.generando;
      $("#p-estado").textContent = d.generando
        ? "Escribiendo ahora mismo. Puedes cerrar esta página: el trabajo sigue."
        : (d.escalado
            ? "Se ha parado: un capítulo no ha salido bien y hace falta que decidas."
            : "No se está escribiendo nada ahora mismo.");
      if (!d.generando) $("#p-fase").textContent = "En reposo";
    } else if (d.tipo === "fin") {
      fuente.close();
      fuente = null;
    }
  };
  fuente.onerror = () => { if (fuente) { fuente.close(); fuente = null; } };
}

$("#detener").addEventListener("click", async () => {
  $("#detener").disabled = true;
  try {
    await traer("/api/novelas/actual/detener", { method: "POST" });
    anotar("Has pedido detener. Termina el paso en curso y para.", false);
  } catch (e) { anotar("No se ha podido detener: " + e.message, true); }
  $("#detener").disabled = false;
});

/* ------------------------------------------------ listas de novelas ----- */

async function cargarListaNovelas(select, alElegir) {
  const previa = select.value;
  const { novelas } = await traer("/api/novelas");
  select.innerHTML = "";
  if (!novelas.length) {
    select.innerHTML = "<option value=''>Todavía no hay ninguna</option>";
    return;
  }
  novelas.forEach((n) => {
    const o = document.createElement("option");
    o.value = n.id;
    o.textContent = n.titulo + (n.en_curso ? " (la de ahora)" : "") +
      ` — ${n.capitulos_escritos} capítulo(s)`;
    select.appendChild(o);
  });
  select.value = previa && novelas.some((n) => n.id === previa)
    ? previa : novelas[0].id;
  select.onchange = () => alElegir(select.value);
  alElegir(select.value);
}

/* ------------------------------------------------ 3. lector ------------- */

function comoParrafos(markdown) {
  const trozos = [];
  markdown.split(/\n{2,}/).forEach((bloque) => {
    const limpio = bloque.trim();
    if (!limpio) return;
    if (limpio.startsWith("#")) return;        // el titulo ya lo ponemos
    trozos.push(limpio.replace(/\n/g, " "));
  });
  return trozos;
}

async function pintarLector(id) {
  const destino = $("#manuscrito");
  destino.innerHTML = "<p class='intro'>Cargando…</p>";
  const novela = await traer(`/api/novelas/${encodeURIComponent(id)}`);

  const ficha = (lista, nodo, formato) => {
    nodo.innerHTML = "";
    if (!lista.length) {
      nodo.innerHTML = "<li class='vacio'>Ninguno todavía.</li>";
      return;
    }
    lista.forEach((x) => {
      const li = document.createElement("li");
      li.innerHTML = formato(x);
      nodo.appendChild(li);
    });
  };
  ficha(novela.personajes, $("#personajes"),
        (p) => `<b>${p.nombre || p.id || p}</b>` +
               (p.tipo ? ` <span class="etiqueta">${p.tipo}</span>` : ""));
  ficha(novela.hilos_abiertos, $("#hilos-abiertos"),
        (h) => `<b>${h.titulo || h.id}</b>`);
  ficha(novela.hilos_cerrados, $("#hilos-cerrados"),
        (h) => `<b>${h.titulo || h.id}</b>`);

  destino.innerHTML = "";
  const h1 = document.createElement("h2");
  h1.textContent = novela.titulo;
  destino.appendChild(h1);

  if (!novela.capitulos.length) {
    destino.insertAdjacentHTML("beforeend",
      "<p class='intro'>Todavía no hay ningún capítulo escrito.</p>");
    return;
  }

  for (const cap of novela.capitulos) {
    const h3 = document.createElement("h3");
    h3.className = "capitulo";
    h3.textContent = `${cap.n}. ${cap.titulo}`;
    destino.appendChild(h3);

    const datos = await traer(
      `/api/novelas/${encodeURIComponent(id)}/capitulos/${cap.n}`);
    comoParrafos(datos.texto).forEach((p) => {
      const nodo = document.createElement("p");
      nodo.textContent = p;
      destino.appendChild(nodo);
    });

    const boton = document.createElement("button");
    boton.className = "enlace-historial";
    const intentos = datos.historial.intentos.filter((i) => !i.es_pulido).length;
    boton.textContent = intentos > 1
      ? `Ver cómo se llegó a este capítulo (${intentos} intentos)`
      : "Ver cómo se llegó a este capítulo";
    boton.onclick = () => abrirHistorial(cap, datos.historial);
    destino.appendChild(boton);
  }
}

/* ------------------------------------------------ historial ------------- */

function trozos(lista, etiqueta) {
  return lista.map((t) => t.cambia
    ? `<${etiqueta}>${escapar(t.texto)}</${etiqueta}>`
    : escapar(t.texto)).join(" ");
}

function escapar(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : s;
  return d.innerHTML;
}

function pintarMedidas(m) {
  const partes = [];
  const l = m.longitud || {};
  if (l.medido != null) {
    partes.push(`<span>Tamaño: ${l.medido} de ${l.objetivo} ` +
      `${l.en_norma ? "✓" : "✗"}</span>`);
  }
  const r = m.repeticion || {};
  if (r.solape != null) {
    partes.push(`<span>Frases repetidas: ${Math.round(r.solape * 100)}%</span>`);
  }
  if (r.frases_recicladas != null) {
    partes.push(`<span>Frases ya usadas antes: ${r.frases_recicladas}</span>`);
  }
  const c = m.continuidad || {};
  if (Array.isArray(c.comprobaciones)) {
    const bien = c.comprobaciones.filter((x) => x.ok).length;
    partes.push(`<span>Comprobaciones superadas: ${bien} de ` +
      `${c.comprobaciones.length}</span>`);
  }
  return partes.length ? `<p class="medidas">${partes.join("")}</p>` : "";
}

function abrirHistorial(cap, historial) {
  $("#h-titulo").textContent = `Cómo se llegó al capítulo ${cap.n}: ${cap.titulo}`;
  const reescritos = historial.intentos.filter((i) => !i.es_pulido).length;
  $("#h-resumen").textContent = reescritos > 1
    ? `Hizo falta escribirlo ${reescritos} veces antes de darlo por bueno.`
    : "Salió bien a la primera.";

  const cuerpo = $("#h-cuerpo");
  cuerpo.innerHTML = "";

  historial.intentos.forEach((intento) => {
    const caja = document.createElement("div");
    caja.className = "intento";

    const graves = (intento.resumen || {}).bloqueante || 0;
    const avisos = (intento.resumen || {}).mayor || 0;
    const clase = graves ? "mal" : (avisos ? "regular" : "bien");
    const veredicto = graves
      ? `${graves} cosa(s) que hay que corregir`
      : (avisos ? `${avisos} cosa(s) que conviene corregir`
                : "Sin problemas");

    const titulo = intento.es_pulido
      ? "Pulido final de la prosa"
      : `Intento ${intento.intento} — ${intento.como_se_hizo}`;

    caja.innerHTML =
      `<header><h4>${escapar(titulo)}</h4>` +
      `<span class="veredicto ${clase}">${escapar(veredicto)}</span></header>` +
      pintarMedidas(intento.metricas || {});

    if ((intento.incidencias || []).length) {
      const ul = document.createElement("ul");
      ul.className = "incidencias";
      intento.incidencias.forEach((i) => {
        const li = document.createElement("li");
        li.className = i.severidad || "menor";
        li.innerHTML = `${escapar(i.detalle || i.tipo)}` +
          `<div class="tipo">${escapar(i.que_es || "")}</div>`;
        ul.appendChild(li);
      });
      caja.appendChild(ul);
    }

    if (intento.cambios && intento.cambios.hay_cambios) {
      const div = document.createElement("div");
      div.className = "cambios";
      div.innerHTML = `<p class="resumen-cambios">Qué cambió respecto a lo ` +
        `anterior: ${escapar(intento.cambios.resumen)}</p>`;
      intento.cambios.lineas.forEach((l) => {
        if (l.estado === "igual") return;
        const p = document.createElement("p");
        p.className = "linea " + l.estado;
        if (l.estado === "cambiada") {
          p.innerHTML = `<span class="marca">antes</span>` +
            trozos(l.antes, "del") +
            `<br><span class="marca">ahora</span>` + trozos(l.despues, "ins");
        } else {
          p.innerHTML = `<span class="marca">` +
            (l.estado === "anadida" ? "nueva" : "quitada") + `</span>` +
            escapar(l.texto);
        }
        div.appendChild(p);
      });
      caja.appendChild(div);
    }
    cuerpo.appendChild(caja);
  });

  $("#capa").hidden = false;
}

$("#cerrar-capa").addEventListener("click", () => { $("#capa").hidden = true; });
$("#capa").addEventListener("click", (e) => {
  if (e.target.id === "capa") $("#capa").hidden = true;
});

/* ------------------------------------------------ 4. coste -------------- */

async function pintarCoste(id) {
  const c = await traer(`/api/novelas/${encodeURIComponent(id)}/coste`);
  const nota = $("#nota-coste");
  nota.hidden = c.hay_datos;
  if (!c.hay_datos) {
    nota.textContent = "De esta novela no hay gasto anotado: se escribió " +
      "conversando con el asistente, y entonces el coste no quedaba guardado " +
      "aquí. Las que se generen desde esta web sí lo anotan.";
  }
  $("#c-total").textContent = dinero(c.total_usd);
  $("#c-trabajo").textContent = dinero(c.trabajo_usd);
  $("#c-arranque").textContent = dinero(c.arranque_usd);
  $("#c-cache").textContent =
    `${c.llamadas_con_cache} de ${c.llamadas_con_cache + c.llamadas_sin_cache}`;

  const cuerpoCap = $("#tabla-capitulos tbody");
  cuerpoCap.innerHTML = "";
  if (!c.por_capitulo.length) {
    cuerpoCap.innerHTML = "<tr><td colspan='4'>Todavía no hay gasto anotado.</td></tr>";
  }
  c.por_capitulo.forEach((f) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${f.capitulo == null ? "Antes de empezar los capítulos"
                                : "Capítulo " + f.capitulo}</td>` +
      `<td class="num">${dinero(f.coste_usd)}</td>` +
      `<td class="num">${f.llamadas}</td>` +
      `<td class="num">${f.reescrituras || 0}</td>`;
    cuerpoCap.appendChild(tr);
  });

  const cuerpoAg = $("#tabla-agentes tbody");
  cuerpoAg.innerHTML = "";
  c.por_agente.forEach((f) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${escapar(f.nombre)}</td>` +
      `<td class="num">${dinero(f.coste_usd)}</td>` +
      `<td class="num">${f.llamadas}</td>` +
      `<td class="num">${Math.round(f.tokens_escritos * 0.75)}</td>`;
    cuerpoAg.appendChild(tr);
  });

  // Comprobaciones de cada capitulo, del ultimo intento de cada uno.
  const destino = $("#metricas");
  destino.innerHTML = "";
  const novela = await traer(`/api/novelas/${encodeURIComponent(id)}`);
  for (const cap of novela.capitulos) {
    const datos = await traer(
      `/api/novelas/${encodeURIComponent(id)}/capitulos/${cap.n}`);
    const ultimos = datos.historial.intentos.filter((i) => !i.es_pulido);
    const ultimo = ultimos[ultimos.length - 1];
    if (!ultimo) continue;
    const bloque = document.createElement("div");
    bloque.innerHTML = `<p><b>Capítulo ${cap.n}</b> — ${escapar(cap.titulo)}` +
      `, ${ultimos.length} intento(s)</p>` + pintarMedidas(ultimo.metricas || {});
    destino.appendChild(bloque);
  }
}

/* ------------------------------------------------ arranque -------------- */

escuchar();
