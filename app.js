let planes = [];
let zonasCobertura = [];

async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Error al llamar a ${url}: ${response.status}`);
  }
  return response.json();
}

function renderPlanes(filtroUso = "todos") {
  const grid = document.getElementById("planes-grid");
  if (!grid) return;

  const filtrados =
    filtroUso === "todos"
      ? planes
      : planes.filter((plan) => plan.uso === filtroUso);

  grid.innerHTML = "";

  filtrados.forEach((plan) => {
    const card = document.createElement("article");
    card.className =
      "plan-card" + (plan.destacado ? " plan-card--featured" : "");

    const metaHTML =
      plan.meta && plan.meta.length
        ? `<div class="plan-meta">
          ${plan.meta.map((m) => `<span>${m}</span>`).join("")}
        </div>`
        : "";

    card.innerHTML = `
      ${plan.destacado ? '<span class="plan-chip">Más elegido</span>' : ""}
      <h3 class="plan-name">${plan.nombre}</h3>
      <div class="plan-speed">
        ${plan.velocidad} <span>${plan.unidad}</span>
      </div>
      <div class="plan-price">
        <strong>${plan.moneda}${plan.precio}</strong> / ${plan.periodo}
      </div>
      ${metaHTML}
      <ul class="plan-features">
        ${plan.detalles.map((d) => `<li>${d}</li>`).join("")}
      </ul>
      <button class="btn btn-outline" data-plan-id="${plan.id}">
        Lo quiero
      </button>
    `;

    grid.appendChild(card);
  });
}

function initFiltrosPlanes() {
  const chips = document.querySelectorAll("#usage-filters .chip");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("chip-active"));
      chip.classList.add("chip-active");

      const uso = chip.getAttribute("data-usage") || "todos";
      renderPlanes(uso);
    });
  });
}

function initCobertura() {
  const selectZona = document.getElementById("zona-select");
  const inputCiudad = document.getElementById("ciudad-input");
  const btnVerificar = document.getElementById("btn-verificar");
  const resultado = document.getElementById("cobertura-resultado");

  if (!selectZona || !inputCiudad || !btnVerificar || !resultado) return;

  if (!zonasCobertura.length) {
    fetchJSON("/api/cobertura/zonas")
      .then((data) => {
        zonasCobertura = data.zonas || [];
        selectZona.innerHTML = zonasCobertura
          .map((z) => `<option value="${z.id}">${z.nombre}</option>`)
          .join("");
      })
      .catch((error) => {
        console.error("No se pudo obtener la información de cobertura", error);
      });
  } else {
    selectZona.innerHTML = zonasCobertura
      .map((z) => `<option value="${z.id}">${z.nombre}</option>`)
      .join("");
  }

  function aplicarEstado(estado, mensaje) {
    resultado.classList.remove(
      "cobertura-resultado--ok",
      "cobertura-resultado--no",
      "cobertura-resultado--soon"
    );

    if (estado === "full") {
      resultado.classList.add("cobertura-resultado--ok");
    } else if (estado === "partial" || estado === "soon") {
      resultado.classList.add("cobertura-resultado--soon");
    } else {
      resultado.classList.add("cobertura-resultado--no");
    }

    resultado.textContent = mensaje;
  }

  function consultarCobertura(params) {
    const url = new URL("/api/cobertura", window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(key, value);
      }
    });
    fetchJSON(url.toString())
      .then((data) => {
        aplicarEstado(data.estado, data.mensaje);
        if (data.zona_id) {
          selectZona.value = data.zona_id;
        }
      })
      .catch((error) => {
        console.error("Error al consultar cobertura", error);
      });
  }

  selectZona.addEventListener("change", () => {
    const zonaId = selectZona.value;
    if (!zonaId) return;
    consultarCobertura({ zona_id: zonaId });
  });

  btnVerificar.addEventListener("click", () => {
    const ciudad = inputCiudad.value.trim();
    if (!ciudad) {
      resultado.textContent =
        "Escribe un barrio o selecciona una zona para verificar la cobertura.";
      resultado.classList.remove(
        "cobertura-resultado--ok",
        "cobertura-resultado--no",
        "cobertura-resultado--soon"
      );
      return;
    }
    consultarCobertura({ barrio: ciudad });
  });
}

function initPlanSelectContacto() {
  const select = document.getElementById("plan-interes");
  if (!select) return;
  planes.forEach((plan) => {
    const opt = document.createElement("option");
    opt.value = plan.id;
    opt.textContent = `${plan.nombre} - ${plan.velocidad} ${plan.unidad}`;
    select.appendChild(opt);
  });
}

function initAccionesPlan() {
  const grid = document.getElementById("planes-grid");
  const selectPlan = document.getElementById("plan-interes");
  if (!grid || !selectPlan) return;

  grid.addEventListener("click", (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (!target.matches("button[data-plan-id]")) return;

    const id = target.getAttribute("data-plan-id");
    if (!id) return;

    selectPlan.value = id;
    document.getElementById("contacto")?.scrollIntoView({
      behavior: "smooth",
    });
  });
}

function initYear() {
  const span = document.getElementById("year");
  if (span) {
    span.textContent = new Date().getFullYear().toString();
  }
}

async function initPlanes() {
  try {
    const data = await fetchJSON("/api/planes");
    planes = data.planes || [];
  } catch (error) {
    console.error("No se pudieron cargar los planes", error);
  }
}

function initContactoForm() {
  const form = document.querySelector(".contact-form");
  if (!form) return;

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const nombre = document.getElementById("nombre")?.value || "";
    const telefono = document.getElementById("telefono")?.value || "";
    const email = document.getElementById("email")?.value || "";
    const direccion = document.getElementById("direccion")?.value || "";
    const planId = document.getElementById("plan-interes")?.value || "";

    const payload = {
      nombre,
      telefono,
      email,
      direccion,
      plan_id: planId || null,
    };

    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton?.textContent;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Enviando...";
    }

    fetchJSON("/api/contacto", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((data) => {
        alert(data.mensaje || "¡Gracias! Nos pondremos en contacto contigo.");
        form.reset();
      })
      .catch((error) => {
        console.error("Error al enviar contacto", error);
        alert(
          "Ocurrió un error al enviar tu solicitud. Inténtalo de nuevo en unos minutos."
        );
      })
      .finally(() => {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = originalText || "Quiero más información";
        }
      });
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  await initPlanes();
  renderPlanes("todos");
  initFiltrosPlanes();
  initCobertura();
  initPlanSelectContacto();
  initAccionesPlan();
  initContactoForm();
  initYear();
});

