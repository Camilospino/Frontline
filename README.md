# ConectaNet Cartagena

Landing profesional para un proveedor de servicio de internet en **Cartagena de Indias**, con backend en **Python (Flask)**.

## Estructura del proyecto

- `app.py`: servidor Flask que:
  - Sirve la página principal (`/`) usando `index.html`.
  - Expone las APIs:
    - `GET /api/planes` — devuelve los planes de internet disponibles.
    - `GET /api/cobertura/zonas` — devuelve las zonas y barrios con cobertura en Cartagena.
    - `GET /api/cobertura?barrio=...` o `?zona_id=...` — verifica la cobertura para un barrio/zona.
    - `POST /api/contacto` — recibe los datos del formulario de contacto.
- `index.html`: landing principal (hero, planes, cobertura, contacto).
- `styles.css`: estilos modernos y responsivos.
- `app.js`: lógica de frontend para consumir las APIs y manejar la UI.
- `requirements.txt`: dependencias de Python.

## Requisitos previos

- Python 3.10 o superior recomendado.
- `pip` instalado.
- Una base de datos **PostgreSQL** accesible.

## Instalación y ejecución

Dentro de la carpeta del proyecto (`learn`):

```bash
python -m venv .venv
source .venv/bin/activate  # En macOS / Linux
# En Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Variables de entorno para PostgreSQL (ejemplo)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=conectanet
export POSTGRES_USER=conectanet
export POSTGRES_PASSWORD=conectanet

python app.py
```

Luego abre en tu navegador:

```text
http://127.0.0.1:5000
```

## Personalización

- **Planes**: edita la lista `PLANES` en `app.py` (precios, velocidades, descripciones).
- **Cobertura Cartagena**: ajusta `ZONAS_COBERTURA` en `app.py` para agregar/quitar barrios y estados (`full`, `partial`, `soon`).
- **Textos / diseño**: modifica `index.html` y `styles.css` según tu marca (nombre comercial, colores, logo, etc.).

## API de facturas digitales (para app móvil)

Este backend incluye una API lista para que una app móvil pueda **consultar y actualizar** facturas digitales.

### Campos que devuelve una factura

- **`monto_total`**: número (total a pagar)
- **`fecha_limite`**: string en formato `YYYY-MM-DD`
- **`estado`**: `pendiente` o `pagada`

Además incluye: `id`, `usuario_id`, `created_at`, `updated_at`.

### 1) Listar facturas por usuario

- **Ruta**: `GET /api/facturas?usuario_id=<usuario>`
- **Ejemplo**:

```bash
curl "http://127.0.0.1:5000/api/facturas?usuario_id=demo"
```

### 2) Consultar una factura (detalle)

- **Ruta**: `GET /api/facturas/<id>?usuario_id=<usuario>`
- **Ejemplo**:

```bash
curl "http://127.0.0.1:5000/api/facturas/1?usuario_id=demo"
```

### 3) Actualizar el estado de una factura

- **Ruta**: `PATCH /api/facturas/<id>?usuario_id=<usuario>`
- **Body JSON**:
  - `{ "estado": "pagada" }` o `{ "estado": "pendiente" }`
- **Ejemplo**:

```bash
curl -X PATCH "http://127.0.0.1:5000/api/facturas/1?usuario_id=demo" \
  -H "Content-Type: application/json" \
  -d '{"estado":"pagada"}'
```

### Base de datos

- Se usa PostgreSQL; al iniciar el servidor se crea (si no existe) la tabla `facturas`.
- Se insertan facturas de ejemplo para el usuario **`demo`** la primera vez (seed).

### Nota importante (seguridad / login)

Por ahora la API usa `usuario_id` como parámetro para simplificar el ejemplo.
Para producción, lo ideal es agregar **autenticación** (por ejemplo JWT) para que cada usuario solo vea sus facturas.

