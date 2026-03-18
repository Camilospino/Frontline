from __future__ import annotations

import os
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
import io
from reportlab.pdfgen import canvas



app = Flask(
    __name__,
    template_folder=".",
    static_folder=".",
    static_url_path="",
)
app.secret_key = "super_secreto_123"

CORS(app, resources={r"/api/*": {"origins": "*"}})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


DB_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "data.sqlite3")


def _use_postgres() -> bool:
    return os.getenv("POSTGRES_ENABLED") == "1"



def _get_db():
    """
    Si hay configuración de Postgres en variables de entorno => usa Postgres.
    Si no, usa SQLite local (data.sqlite3).
    """
    if _use_postgres():
        host = os.getenv("POSTGRES_HOST")
        port = int(os.getenv("POSTGRES_PORT"))
        dbname = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")

        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=RealDictCursor,
        )
        return conn

    # Fallback: SQLite
    conn = sqlite3.connect(DB_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    conn = _get_db()
    try:
        if isinstance(conn, sqlite3.Connection):
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS facturas (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      usuario_id TEXT NOT NULL,
                      monto_total REAL NOT NULL,
                      fecha_limite TEXT NOT NULL,
                      estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'pagada')),
                      created_at TEXT NOT NULL,
                      updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_facturas_usuario_id
                      ON facturas(usuario_id);
                    """
                )
                conn.commit()
            except sqlite3.DatabaseError as e:
                # Si la base de datos está corrupta, la eliminamos y la recreamos.
                if "malformed" in str(e).lower():
                    conn.close()
                    if os.path.exists(DB_SQLITE_PATH):
                        os.remove(DB_SQLITE_PATH)
                    # Reintentar una vez con una base limpia
                    new_conn = sqlite3.connect(DB_SQLITE_PATH)
                    new_conn.row_factory = sqlite3.Row
                    new_conn.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS facturas (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          usuario_id TEXT NOT NULL,
                          monto_total REAL NOT NULL,
                          fecha_limite TEXT NOT NULL,
                          estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'pagada')),
                          created_at TEXT NOT NULL,
                          updated_at TEXT NOT NULL
                        );

                        CREATE INDEX IF NOT EXISTS idx_facturas_usuario_id
                          ON facturas(usuario_id);
                        """
                    )
                    new_conn.commit()
                    new_conn.close()
                else:
                    raise
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS facturas (
                      id SERIAL PRIMARY KEY,
                      usuario_id TEXT NOT NULL,
                      monto_total NUMERIC(12, 2) NOT NULL,
                      fecha_limite DATE NOT NULL,
                      estado VARCHAR(20) NOT NULL CHECK (estado IN ('pendiente', 'pagada')),
                      created_at TIMESTAMPTZ NOT NULL,
                      updated_at TIMESTAMPTZ NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_facturas_usuario_id
                      ON facturas(usuario_id);
                    """
                )
            conn.commit()
    finally:
        conn.close()


def _seed_facturas_si_vacio() -> None:
    conn = _get_db()
    try:
        if isinstance(conn, sqlite3.Connection):
            # Siempre garantizamos algunas facturas de demo,
            # sin importar si ya hay otras facturas en la tabla.
            conn.execute("DELETE FROM facturas WHERE usuario_id = 'demo';")

            now = _utc_now_iso()
            demo = [
                ("demo", 89000, "2026-03-20", "pendiente", now, now),
                ("demo", 99000, "2026-04-20", "pendiente", now, now),
                ("demo", 69000, "2026-02-20", "pagada", now, now),
            ]
            conn.executemany(
                """
                INSERT INTO facturas (usuario_id, monto_total, fecha_limite, estado, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                demo,
            )
            conn.commit()
        else:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM facturas;")
                row = cur.fetchone()
                if row and int(row["c"]) > 0:
                    return

                now = _utc_now_iso()
                demo = [
                    ("demo", 89000, "2026-03-20", "pendiente", now, now),
                    ("demo", 99000, "2026-04-20", "pendiente", now, now),
                    ("demo", 69000, "2026-02-20", "pagada", now, now),
                    ("demo", 69000, "2026-02-20", "pendiente", now, now),
                    ("demo", 69000, "2026-02-20", "pendiente", now, now),
                    ("demo", 69000, "2026-02-20", "pendiente", now, now),
                ]
                cur.executemany(
                    """
                    INSERT INTO facturas (usuario_id, monto_total, fecha_limite, estado, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    demo,
                )
            conn.commit()
    finally:
        conn.close()

        


_init_db()
_seed_facturas_si_vacio()


@dataclass
class Plan:
    id: str
    nombre: str
    velocidad: int
    unidad: str
    precio: float
    moneda: str
    periodo: str
    uso: str
    destacado: bool
    detalles: List[str]
    meta: List[str]


PLANES: List[Plan] = [
    Plan(
        id="basico",
        nombre="Básico Hogar Cartagena",
        velocidad=50,
        unidad="Mbps",
        precio=69000,
        moneda="$",
        periodo="mes",
        uso="hogar",
        destacado=False,
        detalles=[
            "Streaming HD",
            "Hasta 5 dispositivos",
            "Router Wi‑Fi incluido",
        ],
        meta=["Sin cláusula de permanencia"],
    ),
    Plan(
        id="familia",
        nombre="Familia Plus Cartagena",
        velocidad=150,
        unidad="Mbps",
        precio=99000,
        moneda="$",
        periodo="mes",
        uso="hogar",
        destacado=True,
        detalles=[
            "Streaming 4K",
            "Hasta 10 dispositivos",
            "Wi‑Fi de doble banda",
            "Instalación express en 48h",
        ],
        meta=["Ideal teletrabajo", "Soporte prioritario en Cartagena"],
    ),
    Plan(
        id="gaming",
        nombre="Pro Gaming",
        velocidad=300,
        unidad="Mbps",
        precio=139000,
        moneda="$",
        periodo="mes",
        uso="gaming",
        destacado=False,
        detalles=[
            "Baja latencia optimizada para juegos en línea",
            "Conexión por cable incluida",
            "Prioridad en tráfico de juegos",
        ],
        meta=["Ping optimizado", "Ideal para streamers"],
    ),
    Plan(
        id="emprende",
        nombre="Emprende Local",
        velocidad=200,
        unidad="Mbps",
        precio=159000,
        moneda="$",
        periodo="mes",
        uso="empresa",
        destacado=False,
        detalles=[
            "IP dinámica",
            "Soporte en horario extendido",
            "Wi‑Fi empresarial básico",
        ],
        meta=["Negocios de barrio", "Videollamadas estables"],
    ),
    Plan(
        id="pyme",
        nombre="PyME Cartagena Fibra",
        velocidad=500,
        unidad="Mbps",
        precio=239000,
        moneda="$",
        periodo="mes",
        uso="empresa",
        destacado=True,
        detalles=[
            "Fibra dedicada",
            "IP fija",
            "Soporte 24/7 con SLA",
            "Wi‑Fi avanzado para oficinas",
        ],
        meta=["Sucursales", "Cámaras de seguridad"],
    ),
    Plan(
        id="simetrico",
        nombre="Simétrico Creators",
        velocidad=300,
        unidad="Mbps",
        precio=179000,
        moneda="$",
        periodo="mes",
        uso="gaming",
        destacado=False,
        detalles=[
            "Subida y bajada simétrica",
            "Perfecto para subir contenido",
            "Soporte especializado",
        ],
        meta=["Creadores de contenido", "Estudios pequeños"],
    ),
    Plan(
        id="simetrico",
        nombre="Simétrico Creators",
        velocidad=300,
        unidad="Mbps",
        precio=179000,
        moneda="$",
        periodo="mes",
        uso="gaming",
        destacado=False,
        detalles=[
            "Subida y bajada simétrica",
            "Perfecto para subir contenido",
            "Soporte especializado",
        ],
        meta=["Creadores de contenido", "Estudios pequeños"],
    ),
]


@dataclass
class ZonaCobertura:
    id: str
    nombre: str
    estado: str  # full | partial | soon
    barrios: List[str]


ZONAS_COBERTURA: List[ZonaCobertura] = [
    ZonaCobertura(
        id="centro",
        nombre="Centro Histórico y San Diego",
        estado="full",
        barrios=["Centro", "San Diego", "Getsemaní"],
    ),
    ZonaCobertura(
        id="bocagrande",
        nombre="Bocagrande, Castillogrande y El Laguito",
        estado="full",
        barrios=["Bocagrande", "Castillogrande", "El Laguito"],
    ),
    ZonaCobertura(
        id="manga",
        nombre="Manga y Pie de la Popa",
        estado="full",
        barrios=["Manga", "Pie de la Popa"],
    ),
    ZonaCobertura(
        id="norte",
        nombre="Zona Norte (Crespo, Marbella, La Boquilla)",
        estado="partial",
        barrios=["Crespo", "Marbella", "La Boquilla"],
    ),
    ZonaCobertura(
        id="residencial_sur",
        nombre="Zonas residenciales sur (Los Alpes, El Recreo, El Campestre)",
        estado="soon",
        barrios=["Los Alpes", "El Recreo", "El Campestre"],
    ),
]


def _normalizar(texto: str) -> str:
    return (
        texto.strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def _buscar_zona_por_barrio(barrio: str) -> Tuple[Optional[ZonaCobertura], Optional[str]]:
    if not barrio:
        return None, None

    barrio_norm = _normalizar(barrio)
    for zona in ZONAS_COBERTURA:
        for b in zona.barrios:
            if _normalizar(b) == barrio_norm:
                return zona, b
    return None, None


def _buscar_zona_por_id(zona_id: str) -> Optional[ZonaCobertura]:
    for zona in ZONAS_COBERTURA:
        if zona.id == zona_id:
            return zona
    return None


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/cliente")
def portal_cliente():
    return render_template("cliente.html")


@app.post("/api/login")
def api_login():
    data = request.get_json()

    usuario = data.get("usuario")
    password = data.get("password")

    if usuario == "demo" and password == "1234":
        session["usuario"] = usuario

        return jsonify({
            "ok": True,
            "usuario": usuario
        })

    return jsonify({
        "ok": False,
        "mensaje": "Usuario o contraseña incorrectos"
    }), 401

@app.get("/api/session")
def api_session():
    usuario = session.get("usuario")

    if usuario:
        return jsonify({
            "login": True,
            "usuario": usuario
        })

    return jsonify({
        "login": False
    })

@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/planes")
def api_planes():
    uso = request.args.get("uso")
    planes_filtrados = PLANES

    if uso and uso != "todos":
        planes_filtrados = [p for p in PLANES if p.uso == uso]

    return jsonify(
        {
            "planes": [
                {
                    **asdict(plan),
                    # aseguramos tipos simples para JSON
                    "velocidad": int(plan.velocidad),
                    "precio": float(plan.precio),
                }
                for plan in planes_filtrados
            ]
        }
    )


@app.get("/api/cobertura/zonas")
def api_cobertura_zonas():
    return jsonify(
        {
            "zonas": [
                {
                    "id": zona.id,
                    "nombre": zona.nombre,
                    "estado": zona.estado,
                    "barrios": zona.barrios,
                }
                for zona in ZONAS_COBERTURA
            ]
        }
    )


@app.get("/api/cobertura")
def api_cobertura():
    barrio = (request.args.get("barrio") or "").strip()
    zona_id = (request.args.get("zona_id") or "").strip()

    if not barrio and not zona_id:
        return (
            jsonify(
                {
                    "estado": "none",
                    "mensaje": "Debes indicar un barrio o seleccionar una zona.",
                    "zona_id": None,
                    "zona_nombre": None,
                    "barrio": None,
                }
            ),
            400,
        )

    zona: Optional[ZonaCobertura] = None
    barrio_encontrado: Optional[str] = None

    if barrio:
        zona, barrio_encontrado = _buscar_zona_por_barrio(barrio)
    elif zona_id:
        zona = _buscar_zona_por_id(zona_id)

    if not zona:
        return jsonify(
            {
                "estado": "none",
                "mensaje": "Por ahora no tenemos registro de cobertura en esta zona de Cartagena. Déjanos tus datos y un asesor validará tu dirección.",
                "zona_id": None,
                "zona_nombre": None,
                "barrio": barrio or None,
            }
        )

    estado = zona.estado
    nombre_referencia = barrio_encontrado or barrio or zona.nombre

    if estado == "full":
        mensaje = f"¡Excelente! Tenemos cobertura total de fibra óptica en {nombre_referencia} (Cartagena de Indias)."
    elif estado == "partial":
        mensaje = (
            f"Tenemos cobertura parcial en {nombre_referencia}. "
            "Verificaremos tu dirección exacta para confirmarte la disponibilidad."
        )
    elif estado == "soon":
        mensaje = (
            f"Aún no tenemos cobertura activa en {nombre_referencia}, "
            "pero estamos en despliegue. Puedes dejar tus datos para avisarte cuando esté disponible."
        )
    else:
        mensaje = "Por ahora no tenemos registro de cobertura en esta zona."

    return jsonify(
        {
            "estado": estado,
            "mensaje": mensaje,
            "zona_id": zona.id,
            "zona_nombre": zona.nombre,
            "barrio": barrio_encontrado or (barrio or None),
        }
    )


@app.post("/api/contacto")
def api_contacto():
    data = request.get_json(silent=True) or {}

    nombre = data.get("nombre")
    telefono = data.get("telefono")
    email = data.get("email")
    direccion = data.get("direccion")
    plan_id = data.get("plan_id")

    plan = next((p for p in PLANES if p.id == plan_id), None)

    # Aquí podrías integrar envío de correo, CRM, base de datos, etc.
    # De momento simplemente registramos en los logs del servidor.
    app.logger.info(
        "Nuevo contacto desde la web",
        extra={
            "nombre": nombre,
            "telefono": telefono,
            "email": email,
            "direccion": direccion,
            "plan": plan.nombre if plan else None,
        },
    )

    return jsonify(
        {
            "ok": True,
            "mensaje": "Tu solicitud fue enviada correctamente. Un asesor se pondrá en contacto contigo.",
        }
    )


def _factura_to_dict(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(row["id"]),
        "usuario_id": row["usuario_id"],
        "monto_total": float(row["monto_total"]),
        "fecha_limite": str(row["fecha_limite"]),
        "estado": row["estado"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


@app.get("/api/facturas")
def api_facturas_listar():
    """
    Lista facturas por usuario.
    Uso: GET /api/facturas?usuario_id=<id>
    """
    usuario_id = (request.args.get("usuario_id") or "").strip()
    if not usuario_id:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Falta usuario_id",
                    "mensaje": "Debes enviar ?usuario_id=... para consultar facturas.",
                }
            ),
            400,
        )

    conn = _get_db()
    try:
        if isinstance(conn, sqlite3.Connection):
            rows = conn.execute(
                """
                SELECT id, usuario_id, monto_total, fecha_limite, estado, created_at, updated_at
                FROM facturas
                WHERE usuario_id = ?
                ORDER BY fecha_limite DESC, id DESC;
                """,
                (usuario_id,),
            ).fetchall()
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, usuario_id, monto_total, fecha_limite, estado, created_at, updated_at
                    FROM facturas
                    WHERE usuario_id = %s
                    ORDER BY fecha_limite DESC, id DESC;
                    """,
                    (usuario_id,),
                )
                rows = cur.fetchall()
        return jsonify({"ok": True, "facturas": [_factura_to_dict(r) for r in rows]})
    finally:
        conn.close()


@app.get("/api/facturas/<int:factura_id>")
def api_facturas_detalle(factura_id: int):
    """
    Detalle de factura por id, validando el usuario.
    Uso: GET /api/facturas/<id>?usuario_id=<id>
    """
    usuario_id = (request.args.get("usuario_id") or "").strip()
    if not usuario_id:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Falta usuario_id",
                    "mensaje": "Debes enviar ?usuario_id=... para consultar la factura.",
                }
            ),
            400,
        )

    conn = _get_db()
    try:
        if isinstance(conn, sqlite3.Connection):
            row = conn.execute(
                """
                SELECT id, usuario_id, monto_total, fecha_limite, estado, created_at, updated_at
                FROM facturas
                WHERE id = ? AND usuario_id = ?;
                """,
                (factura_id, usuario_id),
            ).fetchone()
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, usuario_id, monto_total, fecha_limite, estado, created_at, updated_at
                    FROM facturas
                    WHERE id = %s AND usuario_id = %s;
                    """,
                    (factura_id, usuario_id),
                )
                row = cur.fetchone()
        if not row:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "No encontrada",
                        "mensaje": "No existe una factura con ese id para este usuario.",
                    }
                ),
                404,
            )

        return jsonify({"ok": True, "factura": _factura_to_dict(row)})
    finally:
        conn.close()


@app.patch("/api/facturas/<int:factura_id>")
def api_facturas_actualizar(factura_id: int):
    """
    Actualiza el estado de una factura.
    Uso:
      PATCH /api/facturas/<id>?usuario_id=<id>
      Body JSON: { "estado": "pagada" } o { "estado": "pendiente" }
    """
    usuario_id = (request.args.get("usuario_id") or "").strip()
    if not usuario_id:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Falta usuario_id",
                    "mensaje": "Debes enviar ?usuario_id=... para actualizar la factura.",
                }
            ),
            400,
        )

    data = request.get_json(silent=True) or {}
    estado = (data.get("estado") or "").strip().lower()
    if estado not in {"pagada", "pendiente"}:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Estado inválido",
                    "mensaje": "El campo estado debe ser 'pagada' o 'pendiente'.",
                }
            ),
            400,
        )

    conn = _get_db()
    try:
        if isinstance(conn, sqlite3.Connection):
            row = conn.execute(
                "SELECT id FROM facturas WHERE id = ? AND usuario_id = ?;",
                (factura_id, usuario_id),
            ).fetchone()
            if not row:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "No encontrada",
                            "mensaje": "No existe una factura con ese id para este usuario.",
                        }
                    ),
                    404,
                )

            updated_at = _utc_now_iso()
            conn.execute(
                """
                UPDATE facturas
                SET estado = ?, updated_at = ?
                WHERE id = ? AND usuario_id = ?;
                """,
                (estado, updated_at, factura_id, usuario_id),
            )
            conn.commit()

            row2 = conn.execute(
                """
                SELECT id, usuario_id, monto_total, fecha_limite, estado, created_at, updated_at
                FROM facturas
                WHERE id = ? AND usuario_id = ?;
                """,
                (factura_id, usuario_id),
            ).fetchone()
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM facturas WHERE id = %s AND usuario_id = %s;",
                    (factura_id, usuario_id),
                )
                row = cur.fetchone()
                if not row:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "No encontrada",
                                "mensaje": "No existe una factura con ese id para este usuario.",
                            }
                        ),
                        404,
                    )

                updated_at = _utc_now_iso()
                cur.execute(
                    """
                    UPDATE facturas
                    SET estado = %s, updated_at = %s
                    WHERE id = %s AND usuario_id = %s;
                    """,
                    (estado, updated_at, factura_id, usuario_id),
                )

                cur.execute(
                    """
                    SELECT id, usuario_id, monto_total, fecha_limite, estado, created_at, updated_at
                    FROM facturas
                    WHERE id = %s AND usuario_id = %s;
                    """,
                    (factura_id, usuario_id),
                )
                row2 = cur.fetchone()

            conn.commit()

        return jsonify({"ok": True, "factura": _factura_to_dict(row2)})
    finally:
        conn.close()



@app.get("/api/factura/<int:factura_id>/pdf")
def api_factura_pdf(factura_id):
    # código pdf aquí
    pass

       


if __name__ == "__main__":
    app.run(debug=True)

