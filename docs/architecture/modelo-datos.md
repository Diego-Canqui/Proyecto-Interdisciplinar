# Modelo de Datos (Entidad-Relación)

Vista simplificada de las entidades y relaciones del sistema **Préstamos de Recursos** (sin capas ni divisiones técnicas de DDD).

```mermaid
erDiagram
    USUARIO ||--|| PERFIL_REPUTACION : "tiene (1 a 1)"
    PERFIL_REPUTACION ||--o{ SANCION : "acumula (1 a N)"
    USUARIO ||--o{ EXCEPCION_ACADEMICA : "recibe (1 a N)"

    USUARIO ||--o{ RESERVA : "solicita (1 a N)"
    RECURSO ||--o{ RESERVA : "es reservado en (1 a N)"

    RESERVA ||--o| PRESTAMO : "se convierte en (1 a 1, al entregar)"
    USUARIO ||--o{ PRESTAMO : "recibe (1 a N)"
    RECURSO ||--o{ PRESTAMO : "se presta en (1 a N)"

    PRESTAMO ||--o| GARANTIA : "respaldado por (1 a 1, opcional)"
    PRESTAMO ||--o{ CHECKLIST : "inspeccionado en (1 a N)"

    USUARIO {
        uuid id PK
        string nombre
        string correo UK
        string telefono
        bool estado
        array roles
    }

    PERFIL_REPUTACION {
        uuid id PK
        uuid usuario_id FK
        int puntos
        enum nivel
        datetime fecha_actualizacion
    }

    SANCION {
        uuid id PK
        uuid perfil_reputacion_id FK
        enum tipo
        int puntos_descuento
        decimal monto_descuento
        string motivo
        datetime fecha_aplicacion
        datetime fecha_fin
        bool activa
    }

    EXCEPCION_ACADEMICA {
        uuid id PK
        uuid usuario_id FK
        string motivo
        datetime fecha_inicio
        datetime fecha_fin
        bool activa
    }

    RECURSO {
        uuid id PK
        string nombre
        string categoria
        enum estado
        string marca
        string modelo
        string numero_serie UK
        string color
        string estado_fisico
        json especificaciones
    }

    RESERVA {
        uuid id PK
        uuid usuario_id FK
        uuid recurso_id FK
        datetime fecha_inicio
        datetime fecha_fin
        enum estado
    }

    PRESTAMO {
        uuid id PK
        uuid reserva_id UK
        uuid usuario_id FK
        uuid recurso_id FK
        datetime fecha_inicio
        datetime fecha_fin
        enum estado
        datetime fecha_entrega_real
        datetime fecha_devolucion_real
    }

    GARANTIA {
        uuid id PK
        uuid prestamo_id FK
        enum tipo
        enum estado
        datetime fecha_registro
        datetime fecha_liberacion
        string compromiso_contenido
        string compromiso_testigo
    }

    CHECKLIST {
        uuid id PK
        uuid prestamo_id FK
        enum tipo
        datetime fecha_inspeccion
        string observaciones
        array fotos_urls
        bool completo
    }
```

## Lectura rápida

* **`(1 a 1)`**: relación directa única (`Usuario` ↔ `PerfilReputacion`).
* **`(1 a 1, al entregar)` / `(1 a 1, opcional)`**: relación uno a uno que solo se crea cuando la reserva se entrega en ventanilla (una reserva nunca genera más de un préstamo).
* **`(1 a N)`**: uno a muchos (`1` usuario, recurso, perfil o préstamo puede tener `N` registros asociados a lo largo del tiempo).
