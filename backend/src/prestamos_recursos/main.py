from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from prestamos_recursos.contexts.identidad_reputacion.presentation.autenticacion_controller import router as autenticacion_router
from prestamos_recursos.contexts.catalogo.presentation.recurso_controller import router as recurso_router
from prestamos_recursos.contexts.reservas.presentation.reserva_controller import router as reserva_router
from prestamos_recursos.contexts.prestamos.presentation.prestamo_controller import router as prestamo_router

app = FastAPI(
    title="Proyecto Interdisciplinar - Préstamo de Recursos",
    docs_url=None,
    swagger_ui_parameters={"docExpansion": "none", "defaultModelsExpandDepth": -1},
)


@app.get("/docs", include_in_schema=False)
def documentacion() -> HTMLResponse:
    pagina = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Documentación",
        swagger_ui_parameters=app.swagger_ui_parameters,
    )
    estilos = """
    <style>
      body, .swagger-ui, .swagger-ui .scheme-container,
      .swagger-ui .opblock-body, .swagger-ui .responses-wrapper,
      .swagger-ui table tbody tr td {
        background: #fff !important;
        color: #111 !important;
      }
      .swagger-ui .topbar { display: none; }
      .swagger-ui .opblock,
      .swagger-ui .opblock.opblock-get,
      .swagger-ui .opblock.opblock-post,
      .swagger-ui .opblock.opblock-put,
      .swagger-ui .opblock.opblock-patch,
      .swagger-ui .opblock.opblock-delete {
        background: #fff !important;
        border: 1px solid #555 !important;
        box-shadow: none !important;
      }
      .swagger-ui .opblock-summary-method {
        background: #111 !important;
        color: #fff !important;
        text-shadow: none !important;
      }
      .swagger-ui .btn,
      .swagger-ui input,
      .swagger-ui select,
      .swagger-ui textarea {
        background: #fff !important;
        border: 1px solid #555 !important;
        color: #111 !important;
        box-shadow: none !important;
      }
      .swagger-ui .btn.execute {
        background: #111 !important;
        color: #fff !important;
      }
      .swagger-ui .opblock-tag,
      .swagger-ui .opblock .opblock-summary-description,
      .swagger-ui .response-col_status,
      .swagger-ui .model-title,
      .swagger-ui .parameter__name,
      .swagger-ui .parameter__type {
        color: #111 !important;
      }
      .swagger-ui a { color: #222 !important; }
    </style>
    """
    contenido = pagina.body.decode().replace("</head>", f"{estilos}</head>")
    return HTMLResponse(content=contenido)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend en desarrollo (Vite)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(autenticacion_router)
app.include_router(recurso_router)
app.include_router(reserva_router)
app.include_router(prestamo_router)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
