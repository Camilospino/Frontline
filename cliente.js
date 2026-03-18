const API_BASE = "";
let usuarioLogueado = null;

async function login() {
  const usuario = document.getElementById("login-usuario").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const estado = document.getElementById("login-estado");

  if (!usuario || !password) {
    estado.textContent = "Debes ingresar usuario y contraseña.";
    return;
  }

  estado.textContent = "Verificando credenciales...";

  try {
    const data = await fetchJSON("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ usuario, password }),
    });

    if (!data.ok) {
      estado.textContent = data.mensaje || "Credenciales incorrectas.";
      return;
    }

    usuarioLogueado = data.usuario;


    estado.textContent = "Inicio de sesión correcto.";

    document.getElementById("login-box").style.display = "none";
    document.getElementById("facturas-area").style.display = "block";

    document.getElementById("usuario-id").value = usuarioLogueado;

    document.getElementById("btn-cargar-facturas").click();
  } catch (err) {
    console.error(err);
    estado.textContent = "Error conectando con el servidor.";
  }
}


async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Error al llamar a ${url}: ${response.status}`);
  }
  return response.json();
}

function formatoPesos(valor) {
  try {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(valor);
  } catch {
    return `$${valor}`;
  }
}

function renderFacturas(facturas, container, estadoEl) {
  container.innerHTML = "";

  if (!facturas.length) {
    estadoEl.textContent = "No encontramos facturas para este usuario.";
    return;
  }

  estadoEl.textContent = `Encontramos ${facturas.length} factura(s) asociadas a tu usuario.`;

  facturas.forEach((factura) => {
    const card = document.createElement("article");
    card.className = "factura-card";
    card.dataset.facturaId = factura.id;
    card.dataset.monto = String(factura.monto_total);
    card.dataset.fecha = factura.fecha_limite;

    const chipClass =
      factura.estado === "pagada"
        ? "chip-estado chip-estado-pagada"
        : "chip-estado chip-estado-pendiente";
    const chipText =
      factura.estado === "pagada" ? "Factura pagada" : "Pendiente de pago";

    const accionesPendiente = `
      <div class="factura-actions">
        <span style="font-size:0.8rem;color:#9ca3af;margin-right:auto;">
          Elige un medio de pago:
        </span>
        <button class="btn btn-outline" data-action="pagar" data-metodo="tarjeta">
          Tarjeta
        </button>
        <button class="btn btn-outline" data-action="pagar" data-metodo="pse">
          PSE
        </button>
        <button class="btn btn-outline" data-action="pagar" data-metodo="nequi">
          Nequi / Daviplata
        </button>
      </div>
    `;

    const accionesPagada = `
      <div class="factura-actions">
        <span style="font-size:0.85rem;color:#bbf7d0;">
          Pago registrado correctamente. Gracias por estar al día.
        </span>
      </div>
    `;

    card.innerHTML = `
      <div class="factura-main">
        <div class="factura-monto">${formatoPesos(factura.monto_total)}</div>
        <div class="factura-fecha">
          Fecha límite de pago: <strong>${factura.fecha_limite}</strong>
        </div>
        <div class="factura-id">
          ID factura: #${factura.id} · Usuario: ${factura.usuario_id}
        </div>
        <div class="factura-meta">
          <span class="${chipClass}">${chipText}</span>
        </div>
      </div>
      ${
        factura.estado === "pendiente"
          ? accionesPendiente
          : accionesPagada
      }
    `;

    container.appendChild(card);
  });
}

function initYear() {
  const span = document.getElementById("year");
  if (span) {
    span.textContent = new Date().getFullYear().toString();
  }
}

function initPortal() {
  const inputUsuario = document.getElementById("usuario-id");
  const btnCargar = document.getElementById("btn-cargar-facturas");
  const list = document.getElementById("facturas-list");
  const estadoEl = document.getElementById("facturas-estado");
  const btnLogin = document.getElementById("btn-login");

if (btnLogin) {
  btnLogin.addEventListener("click", login);
}


  if (!inputUsuario || !btnCargar || !list || !estadoEl) return;

  async function cargarFacturas() {
    const usuario = inputUsuario.value.trim();
    if (!usuario) {
      estadoEl.textContent = "Ingresa tu ID de usuario para continuar.";
      return;
    }

    estadoEl.textContent = "Cargando facturas...";
    list.innerHTML = "";
    btnCargar.disabled = true;

    try {
      const data = await fetchJSON(
        `/api/facturas?usuario_id=${encodeURIComponent(usuario)}`
      );
      if (!data.ok) {
        estadoEl.textContent =
          data.mensaje || "No se pudieron obtener tus facturas.";
        return;
      }
      renderFacturas(data.facturas || [], list, estadoEl);
    } catch (error) {
      console.error("Error al cargar facturas", error);
      estadoEl.textContent =
        "Ocurrió un error al consultar tus facturas. Intenta nuevamente.";
    } finally {
      btnCargar.disabled = false;
    }
  }

  btnCargar.addEventListener("click", () => {
    cargarFacturas();
  });

  inputUsuario.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      cargarFacturas();
    }
  });

  list.addEventListener("click", async (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    const action = target.getAttribute("data-action");
    if (!action || action !== "pagar") return;

    const card = target.closest(".factura-card");
    if (!card) return;
    const facturaId = card.dataset.facturaId;
    const usuario = inputUsuario.value.trim();
    if (!facturaId || !usuario) return;

    const metodo = target.getAttribute("data-metodo") || "tarjeta";
    const monto = Number(card.dataset.monto || 0);
    const fecha = card.dataset.fecha || "";

    const metodoLegible =
      metodo === "pse"
        ? "PSE"
        : metodo === "nequi"
        ? "Nequi / Daviplata"
        : "Tarjeta";

    const confirma = window.confirm(
      `Vas a pagar la factura #${facturaId} por ${formatoPesos(
        monto
      )} con ${metodoLegible}.\n\n¿Confirmas que deseas continuar con el pago (simulado)?`
    );
    if (!confirma) {
      return;
    }

    target.disabled = true;
    target.textContent = "Procesando pago...";

    try {
      const data = await fetchJSON(
        `/api/facturas/${facturaId}?usuario_id=${encodeURIComponent(usuario)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ estado: "pagada" }),
        }
      );
      if (!data.ok) {
        alert(
          data.mensaje ||
            "No fue posible registrar el pago de la factura. Intenta de nuevo."
        );
        return;
      }
      alert(
        `Tu pago se ha registrado correctamente (simulado).\n\nFactura #${facturaId} con fecha límite ${fecha}.`
      );
      await cargarFacturas();
    } catch (error) {
      console.error("Error al actualizar factura", error);
      alert(
        "Ocurrió un error al registrar el pago. Intenta nuevamente en unos minutos."
      );
    } finally {
      target.disabled = false;
      target.textContent = metodoLegible;
    }
  });
}

async function verificarSesion() {
  try {
    const res = await fetch("/api/session", {
      credentials: "include"
    });

    const data = await res.json();

    if (data.login) {
      usuarioLogueado = data.usuario;

      document.getElementById("login-box").style.display = "none";
      document.getElementById("facturas-area").style.display = "block";

      document.getElementById("usuario-id").value = data.usuario;
    }
  } catch (error) {
    console.error("Error verificando sesión", error);
  }
}



document.addEventListener("DOMContentLoaded", () => {
  initPortal();
  initYear();
  verificarSesion();
});


