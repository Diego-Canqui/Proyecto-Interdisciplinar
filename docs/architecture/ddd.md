# Sistema de Gestión de Préstamos de Recursos — Modelo de dominio

Diagrama de clases UML en texto, organizado por **bounded context** y por capas.

## Bounded contexts

| Contexto | Contiene |
|---|---|
| `identidad_reputacion` | Usuario, RolUsuario, PerfilReputacion, PuntajeReputacion, NivelReputacion, Sancion, TipoSancion, ExcepcionAcademica, EstadoExcepcion |
| `catalogo` | Recurso, FichaTecnica, EstadoRecurso |
| `reservas` | Reserva, EstadoReserva, AlgoritmoPrioridadService |
| `prestamos` | Prestamo, EstadoPrestamo, Checklist, TipoChecklist, Garantia, TipoGarantia, EstadoGarantia, CompromisoResponsabilidad |

**Regla:** entre contextos y entre agregados raíz solo se referencia por **ID**. Si un contexto necesita algo de otro, llama al servicio de `application/` de ese otro contexto.

## Arquitectura por capas

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Presentation (Controladores / API REST)                  │
├─────────────────────────────────────────────────────────────┤
│ 2. Application (Servicios de aplicación / Casos de uso)     │
├─────────────────────────────────────────────────────────────┤
│ 3. Domain (Entidades, Value Objects, reglas)                │
├─────────────────────────────────────────────────────────────┤
│ 4. Infrastructure (Persistencia / Repositorios)             │
└─────────────────────────────────────────────────────────────┘
```

Las dependencias apuntan hacia el dominio. El dominio no importa nada de infraestructura.

---

## 1. Presentation

### `AutenticacionController` — identidad_reputacion
- `registrarUsuario(credenciales): TokenDTO` (POST /auth/registro, roles por defecto `[ESTUDIANTE]`)
- `login(credenciales): TokenDTO` (POST /auth/login, devuelve el token JWT + el usuario; 403 si cuenta inactiva)
- `logout(token): Boolean` (JWT sin estado: el cliente descarta el token)
- `obtenerUsuarioActual(): UsuarioDTO` (GET /auth/me)

### `ReputacionController` — identidad_reputacion
- `obtenerPerfilReputacion(): PerfilReputacionDTO` (GET /reputacion/perfil, usuario autenticado)
- `aplicarSancion(datos: SancionCreateDTO): SancionDTO` (POST /reputacion/sanciones, roles `ADMINISTRADOR_SISTEMA`/`GESTOR_ALMACEN`)
- `registrarExcepcion(datos: RegistrarExcepcionDTO): ExcepcionAcademicaDTO` (POST /reputacion/excepciones, valida fecha_fin >= fecha_inicio o 422)
- `anularExcepcion(idExcepcion: UUID): ExcepcionAcademicaDTO` (PATCH /reputacion/excepciones/{id}/anular)
- `ejecutarAmnistia(): AmnistiaResponseDTO` (POST /reputacion/amnistia)

### `UsuarioController` — identidad_reputacion
- `listarUsuarios(): List<UsuarioDTO>` (GET /usuarios, roles de gestión)
- `crearUsuario(datos, actor): UsuarioDTO` (POST /usuarios, validación jerárquica de roles y contraseña hasheada con bcrypt)
- `cambiarRolUsuario(id, nuevo_rol, actor): UsuarioDTO` (PATCH /usuarios/{id}/rol, exclusivo administrador con autoprotección 409)
- `cambiarEstadoUsuario(id, activo, actor): UsuarioDTO` (PATCH /usuarios/{id}/estado, exclusivo administrador con autoprotección 409)
- `eliminarUsuario(id, actor): void` (DELETE /usuarios/{id}, exclusivo administrador, valida ausencia de reservas activas y préstamos en curso con 409)

### `RecursoController` — catalogo
- `buscarRecursos(filtro: String): List<RecursoDTO>` (GET /recursos)
- `crearRecurso(datos): RecursoDTO` (POST /recursos, roles de gestión)
- `consultarDisponibilidad(idRecurso: UUID): DisponibilidadDTO` (GET /recursos/{id}/disponibilidad)
- `obtenerFichaTecnica(idRecurso: UUID): FichaTecnicaDTO` (GET /recursos/{id}/ficha-tecnica)
- `actualizarRecurso(id, datos): RecursoDTO` (PUT /recursos/{id}, roles de gestión)
- `actualizarEstado(id, nuevo_estado): RecursoDTO` (PATCH /recursos/{id}/estado, roles de gestión)

### `ReservaController` — reservas
- `solicitarReserva(datos): ReservaDTO` (POST /reservas, autoconfirmación o PENDIENTE en lista de espera; valida recurso DISPONIBLE/EN_USO, horario L–V 08:00–20:00, duración 1h–7d, no pasado, máx. 30 días)
- `listarReservasUsuario(idUsuario): List<ReservaDTO>` (GET /reservas/usuario/{id})
- `listarTodasReservas(): List<ReservaDTO>` (GET /reservas, roles de gestión)
- `consultarCola(idRecurso): List<ReservaDTO>` (GET /reservas/recurso/{id}/cola)
- `confirmarReserva(idReserva): ReservaDTO` (PATCH /reservas/{id}/confirmar, roles de gestión)
- `iniciarPrestamo(idReserva): PrestamoDTO` (POST /reservas/{id}/prestamo, roles de gestión, valida ventana inicio - 1h <= ahora <= fin)
- `cancelarReserva(idReserva): ReservaDTO` (PATCH /reservas/{id}/cancelar, promueve automáticamente al siguiente candidato elegible de la cola)

### `PrestamoController` — prestamos
- `solicitarPrestamo(datos): PrestamoDTO` (POST /prestamos, crea préstamo ACTIVO y recurso pasa a EN_USO)
- `completarEntrega(datos): PrestamoDTO` (POST /prestamos/entrega/completar, registra garantía y checklist inicial, pasa a ENTREGADO y premia recogida puntual con +10 pts)
- `cancelarPrestamo(idPrestamo, datos): PrestamoDTO` (POST /prestamos/{id}/cancelar, en ventanilla antes de entrega física, libera recurso a DISPONIBLE sin penalización)
- `registrarDevolucion(datos): DevolucionResponseDTO` (POST /prestamos/devolucion, registra checklist de retorno, pasa recurso a DISPONIBLE o MANTENIMIENTO, libera garantía LIBERADA o la retiene RETENIDA, y premia +10 pts o sanciona)
- `consultarInspecciones(idPrestamo): InspeccionResponseDTO` (GET /prestamos/{id}/inspeccion, expone garantía con fecha_liberacion y checklists)
- `consultarHistorial(idUsuario): List<PrestamoDTO>` (GET /prestamos/usuarios/{id}/historial)
- `listarTodosPrestamos(): List<PrestamoDTO>` (GET /prestamos, roles de gestión)
- `renovarPrestamo(datos): PrestamoDTO` (POST /prestamos/renovar, extiende 7 días antes del vencimiento)

---

## 2. Application

### `AutenticacionService` — identidad_reputacion
- `registrar_usuario(credenciales): TokenDTO` (crea usuario con rol ESTUDIANTE y perfil inicial de 500 puntos)
- `login(credenciales): TokenDTO` (valida hash bcrypt; rechaza cuentas inactivas con 403)
- `validar_token(token: String): Dict` (decodifica y valida JWT HS256)

### `UsuarioService` — identidad_reputacion
- `crear_usuario(datos, actor): UsuarioDTO` (control jerárquico: GESTOR_ALMACEN solo roles solicitantes; ADMINISTRADOR_SISTEMA todos los roles)
- `cambiar_rol_usuario(id, nuevo_rol, actor): UsuarioDTO` (exclusivo admin, autoprotección 409)
- `cambiar_estado_usuario(id, estado, actor): UsuarioDTO` (activación/desactivación, autoprotección 409)
- `eliminar_usuario(id, actor): void` (exclusivo admin, autoprotección 409 y validación de ausencia de reservas activas y préstamos en curso con 409)
- `listar_usuarios(): List<UsuarioDTO>`
- `obtener_usuario_por_id(id): UsuarioDTO`

### `ReputacionService` — identidad_reputacion
- `obtener_perfil(idUsuario: UUID): PerfilReputacionDTO` (crea el perfil con puntaje inicial 500 si no existe y expira sanciones vencidas)
- `consultar_elegibilidad_lectura(idUsuario): Boolean`, `consultar_nivel_lectura(idUsuario): String`, `consultar_puntaje_lectura(idUsuario): int` (consultas puras sin efectos secundarios)
- `esElegibleParaPrestamo(idUsuario: UUID): Boolean` (evalúa si existen sanciones vigentes activas no cubiertas por excepción académica)
- `aplicar_sancion(idUsuario: UUID, tipo: TipoSancion, motivo: String, montoOpcional: decimal, diasRetraso: int): SancionDTO`
- `registrar_excepcion(idUsuario: UUID, motivo: String, inicio: DateTime, fin: DateTime): ExcepcionAcademicaDTO` (valida fecha_fin >= fecha_inicio o 422)
- `anular_excepcion(idExcepcion: UUID): ExcepcionAcademicaDTO` (desactiva la excepción)
- `premiar_entrega_puntual(idUsuario: UUID): void` (+10 puntos, con tope 1000)
- `premiar_devolucion_puntual(idUsuario: UUID): void` (+10 puntos, con tope 1000)
- `ejecutar_amnistia_mensual(): AmnistiaResponseDTO` (+25 puntos con tope 1000 a perfiles en nivel BAJO sin sanciones en los últimos 30 días)

### `RecursoApplicationService` — catalogo
- `crear_recurso(...)`: valida ficha técnica y crea recurso en DISPONIBLE
- `buscar(filtro: String): List<RecursoDTO>`
- `consultar_disponibilidad(idRecurso: UUID): DisponibilidadDTO`
- `obtener_ficha_tecnica(idRecurso: UUID): FichaTecnicaDTO`
- `obtener_por_id(idRecurso: UUID): RecursoDTO` (utilizado por otros contextos para desacoplamiento DDD)
- `actualizar_recurso(...)` y `actualizar_estado(idRecurso, nuevo_estado: EstadoRecurso): RecursoDTO`

### `ReservaService` — reservas
- Inyecta `catalogo_service: RecursoApplicationService` para consultar estado operativo del bien.
- `crear_reserva(datos, ahora=None): ReservaDTO`: valida recurso operativo (DISPONIBLE o EN_USO), horario institucional (L–V 08:00–20:00), duración (1h a 7d), no pasado (tolerancia 5 min), anticipación máx. 30 días, ausencia de superposiciones del mismo usuario y cupo según `NivelReputacion.limite_operaciones`. Confirma o encola en PENDIENTE.
- `cancelar_reserva(idReserva: UUID): ReservaDTO`: cancela y promueve automáticamente al candidato prioritario elegible por reputación sin sanciones.
- `convertir_a_prestamo(idReserva: UUID, ahora=None): PrestamoDTO`: valida estado CONFIRMADA y ventana operativa `inicio - 1h <= ahora <= fin`.
- `obtener_cola_espera(idRecurso: UUID): List<ReservaDTO>`: cola ordenada por AlgoritmoPrioridadService.
- `contar_reservas_activas_usuario(idUsuario: UUID): int`: reservas en PENDIENTE o CONFIRMADA.

### `PrestamoService` — prestamos
- Inyecta `catalogo_service: RecursoApplicationService` para coordinar estados en catálogo sin acoplamiento a repositorios ajenos.
- `solicitar_prestamo(...)`: crea agregado en estado ACTIVO y pasa recurso a EN_USO.
- `cancelar_prestamo(idPrestamo, motivo)`: cancela préstamo ACTIVO en ventanilla y libera recurso a DISPONIBLE sin penalizar reputación.
- `completar_entrega(...)`: valida garantía REGISTRADA y checklist inicial ESTADO_INICIAL completo, pasa a ENTREGADO y premia recogida puntual (+10 pts).
- `procesar_devolucion(...)`: pasa a DEVUELTO, registra checklist retorno, actualiza recurso a DISPONIBLE o MANTENIMIENTO, libera garantía (LIBERADA con fecha_liberacion) si no hubo daños o la retiene (RETENIDA) ante daños, y premia (+10 pts) o sanciona (TARDANZA, DANO_PARCIAL, DANO_TOTAL).
- `consultar_inspecciones(idPrestamo: UUID)`: expone garantía con `fecha_liberacion` y checklists.
- `contar_prestamos_en_curso(idUsuario: UUID): int`: préstamos en ACTIVO, ENTREGADO o VENCIDO.
- `renovar_prestamo(...)`: extensión de 7 días antes de fecha_fin.

---

## 3. Domain

### 👤 identidad_reputacion

#### `Usuario` («Aggregate Root»)
- Atributos: `id: UUID`, `nombre`, `correo`, `telefono`, `passwordHash: String`, `estado: Boolean`, `roles: Set<RolUsuario>` (por defecto `[ESTUDIANTE]`)
- Métodos: `crearConPassword(nombre, correo, telefono, passwordPlano, roles)` (factory: hashea la contraseña con bcrypt), `verificarPassword(passwordPlano): Boolean`, `actualizarPerfil()`, `cambiarEstado()`
- La contraseña se guarda solo como hash y nunca sale en DTOs ni respuestas.

#### `RolUsuario` («enumeration»)
`ESTUDIANTE`, `DOCENTE`, `PERSONAL_ADMINISTRATIVO`, `GESTOR_ALMACEN`, `ADMINISTRADOR_SISTEMA`

#### `PerfilReputacion` («Aggregate Root»)
- Atributos: `id: UUID`, `usuarioId: UUID`, `puntaje: PuntajeReputacion`, `nivel: NivelReputacion`, `fechaActualizacion: DateTime`, `sanciones: List<Sancion>`
- Métodos:
  - `recalcularNivel()` — umbrales por puntaje: 0–299 BAJO, 300–599 NORMAL, 600–799 BUENO, 800–1000 EXCELENTE.
  - `aplicarSancion(sancion)` — añade la sanción, descuenta puntos y recalcula el nivel.
  - `aplicarAmnistia(ahora: DateTime)` — suma +25 puntos (con tope 1000) a los perfiles en nivel BAJO (0–299 pts) sin sanciones en los últimos 30 días, y recalcula el nivel.
  - `esElegibleParaPrestamo(): Boolean` — `True` si no hay sanciones vigentes (activas y no expiradas) que no estén cubiertas por una excepción académica vigente.
- El nivel NO bloquea préstamos: es insumo de prioridad en la cola de espera de `reservas` y define el límite de operaciones simultáneas.
- Factory `crearParaUsuario(usuarioId)`: puntaje inicial 500 (nivel NORMAL), sin sanciones.

#### `Sancion` («Entity», dentro del agregado PerfilReputacion)
- Atributos: `id: UUID`, `tipo: TipoSancion`, `puntosDescuento: int`, `montoDescuento: decimal`, `motivo: String`, `fechaAplicacion: DateTime`, `fechaFin: DateTime`, `activa: Boolean`
- Métodos: `aplicar()`, `calcularDescuento(): int`
- `fechaFin` se calcula al aplicar: `fechaAplicacion + tipo.duracionBloqueo(diasRetraso)`; al pasar `fechaFin` la sanción expira y deja de bloquear la elegibilidad.
- `montoDescuento` queda como registro de deuda: el pago material es manual/externo al sistema.
- No tiene repositorio propio: se accede a través de `PerfilReputacion`.

#### `PuntajeReputacion` («Value Object»)
- Atributos: `puntos: int` (rango válido 0..1000, validado en el constructor)
- Métodos: `sumar(p: int)`, `restar(p: int)`, `esValido(): Boolean` (inmutable: las operaciones devuelven una nueva instancia)

#### `NivelReputacion` («enumeration»)
`BAJO` (límite 1 op), `NORMAL` (límite 2 ops), `BUENO` (límite 3 ops), `EXCELENTE` (límite 5 ops).
- Propiedad: `limite_operaciones -> int` que determina el cupo máximo de operaciones activas simultáneas (reservas activas + préstamos en curso).

#### `TipoSancion` («enumeration»)
`TARDANZA`, `DANO_PARCIAL`, `DANO_TOTAL`, `INASISTENCIA_RESERVA`

Cada tipo define `puntosDescuento`, `montoDescuento` (deuda registrada) y la regla de duración `duracionBloqueo(diasRetraso: int): int`:
- `TARDANZA`: -10 pts, $0. Gracia de 1 día: si el retraso fue ≤ 1 día, solo descuenta puntos sin bloqueo (`fechaFin = fechaAplicacion`, expira de inmediato). Desde el 2º día de retraso: bloqueo 1:1 (un día de bloqueo por día de retraso).
- `DANO_PARCIAL`: -30 pts, deuda $50, bloqueo 30 días.
- `DANO_TOTAL`: -100 pts, deuda = valor del recurso (parámetro `montoOpcional`), bloqueo 60 días.
- `INASISTENCIA_RESERVA`: -15 pts, $0, bloqueo fijo de 3 días.

#### `ExcepcionAcademica` («Aggregate Root»)
- Atributos: `id: UUID`, `usuarioId: UUID`, `motivo: String`, `fechaInicio: DateTime`, `fechaFin: DateTime`, `activa: Boolean`
- Invariante de dominio: `fechaFin >= fechaInicio` (validado en `__post_init__` y en `RegistrarExcepcionDTO`).
- Métodos: `esVigente(ahora: DateTime): Boolean` (`activa` && `fechaInicio` <= ahora <= `fechaFin`), `anular()` (`activa = False`).
- Sin flujo de aprobación: nace vigente al registrarse (`activa = True`).
- Regla de cobertura: una excepción vigente cubre sanciones de tipo `TARDANZA` e `INASISTENCIA_RESERVA` en la elegibilidad.

#### `EstadoExcepcion` («enumeration»)
`VIGENTE`, `PROGRAMADA`, `VENCIDA`, `ANULADA`

### 📦 catalogo

#### `Recurso` («Aggregate Root»)
- Atributos: `id: UUID`, `nombre`, `descripcion`, `categoria`, `estado: EstadoRecurso`, `fichaTecnica: FichaTecnica`
- Métodos: `marcarDisponible()`, `marcarEnUso()`, `marcarMantenimiento()`, `marcarFueraDeServicio()`, `estaDisponible(): Boolean`, `cambiarEstado(nuevoEstado: EstadoRecurso)`

#### `FichaTecnica` («Value Object»)
- Atributos: `marca`, `modelo`, `numeroSerie`, `color`, `estadoFisico`, `fotoUrl`
- Métodos: `esValida(): Boolean`

#### `EstadoRecurso` («enumeration»)
`DISPONIBLE`, `EN_USO`, `MANTENIMIENTO`, `FUERA_DE_SERVICIO`

### 📅 reservas

#### `Reserva` («Aggregate Root»)
- Atributos: `id`, `usuarioId`, `recursoId`, `fechaInicio`, `fechaFin`, `estado: EstadoReserva`
- Métodos e invariantes:
  - `crear(usuarioId, recursoId, fechaInicio, fechaFin)`: valida horario institucional de ventanilla (lunes a viernes de 08:00 a 20:00 UTC inclusive tanto en inicio como fin), duración mínima de 1 hora, duración máxima de 7 días, `fechaFin > fechaInicio`. Estado inicial: `PENDIENTE`.
  - `confirmar(fechaActual=None)`: verifica estado `PENDIENTE` y vigencia temporal (`estaVigente(fechaActual)`), pasa a `CONFIRMADA`.
  - `cancelar()`: pasa a `CANCELADA`.
  - `estaVigente(fechaActual=None): Boolean`: comprueba `fechaFin > ahora` y estado activo.
  - `seSuperponeCon(otra: Reserva): Boolean`: evalúa cruce temporal de intervalos `[inicio, fin)`.

#### `EstadoReserva` («enumeration»)
`PENDIENTE`, `CONFIRMADA`, `CANCELADA`, `VENCIDA`, `CONVERTIDA`

#### `AlgoritmoPrioridadService` («Domain Service»)
- `ordenarColaEspera(reservas: List<Reserva>, puntajesReputacion=None): List<Reserva>`
- Ordena por `(-puntaje, fechaInicioUTC)` priorizando mayor reputación y antigüedad FIFO.

### 🤝 prestamos

#### `Prestamo` («Aggregate Root»)
- Atributos: `id`, `reservaId`, `recursoId`, `usuarioId`, `fechaInicio`, `fechaFin`, `estado: EstadoPrestamo`
- Métodos:
  - `marcarEntregado()`: pasa de `ACTIVO` a `ENTREGADO`.
  - `devolver(fechaDevolucion: DateTime): int`: pasa a `DEVUELTO` y retorna los días de retraso.
  - `cancelar(motivo: String)`: exige estado `ACTIVO`, pasa a `CANCELADO` y permite liberar el recurso en catálogo.
  - `renovar(dias: int, fechaActual: DateTime)`: extiende `fechaFin` en 7 días si no ha vencido.
  - `calcularDiasRetraso(fechaReferencia: DateTime): int`
  - `solicitarProrroga(dias: int, fechaActual: DateTime): Boolean`

#### `EstadoPrestamo` («enumeration»)
`ACTIVO`, `ENTREGADO`, `DEVUELTO`, `VENCIDO`, `CANCELADO`

#### `Checklist` («Aggregate Root»)
- Atributos: `id`, `prestamoId`, `tipo: TipoChecklist`, `fechaInspeccion`, `observaciones`, `fotosUrls`, `completo: Boolean`
- Métodos: `agregarItem(observaciones, fotosUrls)`, `confirmar()` (`completo = True`)

#### `TipoChecklist` («enumeration»)
`ESTADO_INICIAL`, `ESTADO_DEVOLUCION`

#### `Garantia` («Aggregate Root»)
- Atributos: `id`, `prestamoId`, `tipo: TipoGarantia`, `estado: EstadoGarantia`, `compromiso: CompromisoResponsabilidad`, `fechaRegistro: DateTime`, `fechaLiberacion: DateTime | None`
- Métodos:
  - `registrar(prestamoId, tipo, compromiso)` (nace en estado `REGISTRADA` con `fechaRegistro`)
  - `liberar(fechaLiberacion=None)` (pasa a `LIBERADA` y registra `fechaLiberacion`)
  - `retener()` (pasa a `RETENIDA` y limpia `fechaLiberacion = None`)

#### `CompromisoResponsabilidad` («Value Object»)
- Atributos: `contenido`, `fechaFirma`, `firmaUrl`, `testigo`
- Métodos: `esValido(): Boolean`

#### `TipoGarantia` («enumeration»)
`DOCUMENTO_IDENTIDAD`, `CARNET_UNIVERSITARIO`, `DEPOSITO_ECONOMICO`, `OTRO`

#### `EstadoGarantia` («enumeration»)
`PENDIENTE`, `REGISTRADA`, `LIBERADA`, `RETENIDA`

---

## 4. Infrastructure (repositorios)

Un repositorio por agregado raíz. La interfaz se define en el dominio y la infraestructura la implementa con `session.flush()` (política D13):

- `UsuarioRepository`: `guardar`, `obtenerPorId`, `obtenerPorCorreo`, `listar`, `eliminar`
- `PerfilReputacionRepository`: `guardar`, `obtenerPorUsuario` (incluye sus sanciones), `obtenerPorId` — `Sancion` se persiste solo a través de este repositorio (sin repositorio propio)
- `ExcepcionAcademicaRepository`: `guardar`, `obtenerVigentesPorUsuario`, `obtenerPorId`
- `RecursoRepository`: `guardar`, `obtenerPorId`, `buscar`, `actualizarEstado`
- `ReservaRepository`: `guardar`, `obtenerPorId`, `obtenerPorUsuario`, `obtenerColaPorRecurso`, `obtenerTodas`
- `PrestamoRepository`: `guardar`, `obtenerPorId`, `obtenerActivos`, `obtenerPorUsuario`, `obtenerTodos`
- `ChecklistRepository`: `guardar`, `obtenerPorId`, `obtenerPorPrestamo`, `obtenerInicialPorPrestamo`, `obtenerDevolucionPorPrestamo`
- `GarantiaRepository`: `guardar`, `obtenerPorId`, `obtenerPorPrestamo`

---

## Relaciones principales

1. **Usuario → PerfilReputacion** (1:1): asociación entre dos agregados, por `usuarioId`. El perfil se crea automáticamente con puntaje inicial 500 (nivel NORMAL) al primer acceso.
2. **PerfilReputacion ◆ Sancion** (1:N): composición dentro del mismo agregado. Cada sanción lleva `fechaFin` derivada de `TipoSancion.duracionBloqueo()`; al expirar deja de bloquear la elegibilidad.
3. **Usuario → ExcepcionAcademica** (1:N): asociación por `usuarioId`. Nace vigente (sin aprobación) con `fechaFin >= fechaInicio`; mientras esté vigente cubre sanciones de `TARDANZA` e `INASISTENCIA_RESERVA` en la elegibilidad.
4. **Usuario → Reserva** (1:N): referencia por ID entre contextos.
5. **Reserva → Prestamo** (1 → 0..1): una reserva confirmada puede convertirse en préstamo dentro de la ventana horaria `fecha_inicio - 1h <= ahora <= fecha_fin`; se enlazan por `reservaId`.
6. **Prestamo → Checklist / Garantia** (1:N): asociación por `prestamoId`. `Checklist` y `Garantia` son agregados raíz independientes con repositorios dedicados en infraestructura (`ChecklistRepository`, `GarantiaRepository`).
7. **Recurso ◆ FichaTecnica** (1:1): composición (Value Object).
8. **Comunicación inter-contexto exclusivamente vía `application/` + IDs:**
   Todas las referencias entre contextos son estrictamente por identificador (`usuarioId`, `recursoId`, `reservaId`). Ningún contexto importa modelos ni repositorios de otro; toda operación coordinada se realiza mediante los servicios de aplicación:
   - `reservas` ↔ `catalogo` vía `RecursoApplicationService` (validación de estado operativo `DISPONIBLE` o `EN_USO` al crear reservas).
   - `prestamos` ↔ `catalogo` vía `RecursoApplicationService` (actualización de estados a `EN_USO`, `DISPONIBLE` o `MANTENIMIENTO`).
   - `reservas` ↔ `prestamos` vía `PrestamoService` (conversión de reserva en préstamo y conteo de préstamos en curso para cupo simultáneo).
   - `reservas`/`prestamos` ↔ `identidad_reputacion` vía `ReputacionService` (consulta de elegibilidad/sanciones, bonificación por puntualidad `+10 pts`, aplicación de sanciones al devolver con mora o daño, y ordenamiento de cola de espera por reputación).
   - `UsuarioService` ↔ `ReservaService`/`PrestamoService` (verificación de ausencia de reservas activas y préstamos en curso al eliminar cuentas de usuario).