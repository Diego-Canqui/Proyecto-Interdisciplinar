# Sistema de Gestión de Préstamos de Recursos — Modelo de dominio

Diagrama de clases UML en texto, organizado por **bounded context** y por capas.

## Bounded contexts

| Contexto | Contiene |
|---|---|
| `identidad_reputacion` | Usuario, RolUsuario, PerfilReputacion, PuntajeReputacion, NivelReputacion, Sancion, TipoSancion, ExcepcionAcademica |
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
- `login(credenciales): TokenDTO` (devuelve el token JWT + el usuario)
- `logout(token): Boolean` (JWT sin estado: el cliente descarta el token)
- `obtenerUsuarioActual(): UsuarioDTO`

### `ReputacionController` — identidad_reputacion
- `obtenerPerfilReputacion(): PerfilReputacionDTO` (GET /reputacion/perfil, usuario autenticado)
- `aplicarSancion(datos): SancionDTO` (POST /reputacion/sanciones, roles `ADMINISTRADOR_SISTEMA`/`GESTOR_ALMACEN`)
- `registrarExcepcion(datos): ExcepcionAcademicaDTO` (POST /reputacion/excepciones, mismos roles)
- ⚠️ `aplicarSancion` debe responder el `SancionDTO` de la sanción creada; el código actual devuelve un `ExcepcionAcademicaDTO` con UUID ficticio (bug conocido, a corregir en una spec futura).

### `UsuarioController` — identidad_reputacion
- `listarUsuarios(): List<UsuarioDTO>` (GET /usuarios)
- `crearUsuario(datos): UsuarioDTO` (POST /usuarios)
- ⚠️ Pendiente en spec 002: `crearUsuario` no hashea password (usuarios creados así no pueden loguearse).

### `RecursoController` — catalogo
- `buscarRecursos(filtro: String): List<RecursoDTO>`
- `consultarDisponibilidad(idRecurso: UUID): Boolean`
- `obtenerFichaTecnica(idRecurso: UUID): RecursoDTO`

### `ReservaController` — reservas
- `solicitarReserva(idUsuario: UUID, idRecurso: UUID): String`

### `PrestamoController` — prestamos
- `registrarDevolucion(idPrestamo: UUID): void`
- `consultarHistorial(idUsuario: UUID): List<PrestamoDTO>`

---

## 2. Application

### `GestionAccesoService` — identidad_reputacion
- `autenticarJWT(token: String): Boolean`
- `verificarPermisos(idUsuario: UUID, rol: RolUsuario): Boolean`
- `obtenerUsuarioAutenticado(): UsuarioDTO`

### `ReputacionService` — identidad_reputacion
- `obtenerPerfil(idUsuario: UUID): PerfilReputacionDTO` (crea el perfil con puntaje inicial 500 si no existe)
- `esElegibleParaPrestamo(idUsuario: UUID): Boolean` (lo consumen `reservas` y `prestamos`; solo evalúa sanciones vigentes — el nivel no participa)
- `aplicarSancion(idUsuario: UUID, tipo: TipoSancion, motivo: String, montoOpcional: decimal, diasRetraso: int): SancionDTO` (`montoOpcional` se usa en `DANO_TOTAL`: el valor del recurso lo pasa `prestamos`, que lo obtiene de `catalogo`; `diasRetraso` se usa en `TARDANZA` para calcular los días de bloqueo según la regla del tipo)
- `registrarExcepcion(idUsuario: UUID, motivo: String, inicio: DateTime, fin: DateTime): ExcepcionAcademicaDTO`
- `premiarDevolucionPuntual(idUsuario: UUID): void` (+10 puntos; la llama `prestamos` en `procesarDevolucion` cuando la devolución fue en fecha)
- `ejecutarAmnistiaMensual(): void` (la dispara un proceso programado mensual; aplica `PerfilReputacion.aplicarAmnistia()` a los perfiles en nivel BAJO)

### `ReservaService` — reservas
- `crearReserva(idUsuario: UUID, idRecurso: UUID): Boolean`
- `cancelarReserva(idReserva: UUID): Boolean`
- `convertirAPrestamo(idReserva: UUID): Boolean`
- `obtenerColaEspera(idRecurso: UUID): List<ReservaDTO>`

### `PrestamoService` — prestamos
- `solicitarPrestamo(idUsuario: UUID, idRecurso: UUID): Boolean`
- `procesarDevolucion(idPrestamo: UUID): void`
- `renovarPrestamo(idPrestamo: UUID): Boolean`
- `validarReglasNegocio(): Boolean`

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
  - `aplicarAmnistia()` — +25 puntos por cada mes transcurrido sin sanciones nuevas, solo mientras el nivel sea BAJO (no desbloquea préstamos: acelera la recuperación de prioridad en la cola de espera).
  - `esElegibleParaPrestamo(): Boolean` — `True` si no hay sanciones vigentes (activas y no expiradas) que no estén cubiertas por una excepción académica vigente.
- El nivel NO bloquea préstamos: es insumo de prioridad en la cola de espera de `reservas`.
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
`BAJO`, `NORMAL`, `BUENO`, `EXCELENTE`

#### `TipoSancion` («enumeration»)
`TARDANZA`, `DANO_PARCIAL`, `DANO_TOTAL`, `INASISTENCIA_RESERVA`

Cada tipo define `puntosDescuento`, `montoDescuento` (deuda registrada) y la regla de duración `duracionBloqueo(diasRetraso: int): int` (días de bloqueo; de aquí se deriva `fechaFin` de la sanción):
- `TARDANZA`: -10 pts, $0. Gracia de 1 día: si el retraso fue ≤ 1 día, solo descuenta puntos sin bloqueo (`fechaFin = fechaAplicacion`, expira de inmediato). Desde el 2º día de retraso: bloqueo 1:1 (un día de bloqueo por día de retraso).
- `DANO_PARCIAL`: -30 pts, deuda $50, bloqueo 30 días.
- `DANO_TOTAL`: -100 pts, deuda = valor del recurso (parámetro `montoOpcional`), bloqueo 60 días.
- `INASISTENCIA_RESERVA`: -15 pts, $0, bloqueo fijo de 3 días.

#### `ExcepcionAcademica` («Aggregate Root»)
- Atributos: `id: UUID`, `usuarioId: UUID`, `motivo`, `fechaInicio`, `fechaFin`, `activa: Boolean`
- Métodos: `esVigente(): Boolean` (`activa` && `fechaInicio` <= ahora <= `fechaFin`)
- Sin flujo de aprobación: nace vigente al registrarse (`activa = True`). `activa` queda como flag de anulación manual (un administrador la pone `False` si se registró por error).
- Regla de cobertura: una excepción vigente cubre sanciones de tipo `TARDANZA` e `INASISTENCIA_RESERVA` en la elegibilidad.

### 📦 catalogo

#### `Recurso` («Aggregate Root»)
- Atributos: `id: UUID`, `nombre`, `descripcion`, `categoria`, `estado: EstadoRecurso`, `fichaTecnica: FichaTecnica`
- Métodos: `marcarDisponible()`, `marcarNoDisponible()`, `actualizarEstado()`

#### `FichaTecnica` («Value Object»)
- Atributos: `marca`, `modelo`, `numeroSerie`, `color`, `estadoFisico`, `fotoUrl`
- Métodos: `esValida(): Boolean`

#### `EstadoRecurso` («enumeration»)
`DISPONIBLE`, `EN_USO`, `MANTENIMIENTO`, `FUERA_DE_SERVICIO`

### 📅 reservas

#### `Reserva` («Aggregate Root»)
- Atributos: `id`, `usuarioId`, `recursoId`, `fechaInicio`, `fechaFin`, `estado: EstadoReserva`
- Métodos: `crear()`, `cancelar()`, `convertirAPrestamo()`, `esVigente(): Boolean`

#### `EstadoReserva` («enumeration»)
`PENDIENTE`, `CONFIRMADA`, `CANCELADA`, `VENCIDA`, `CONVERTIDA`

#### `AlgoritmoPrioridadService` («Domain Service»)
- `ordenarColaEspera(reservas: List<Reserva>): List<Reserva>`
- `calcularPrioridad(reserva: Reserva): int`

### 🤝 prestamos

#### `Prestamo` («Aggregate Root»)
- Atributos: `id`, `reservaId`, `recursoId`, `usuarioId`, `fechaInicio`, `fechaFin`, `estado: EstadoPrestamo`
- Métodos: `iniciar()`, `devolver()`, `renovar()`, `vencer()`, `solicitarProrroga(): Boolean`

#### `EstadoPrestamo` («enumeration»)
`ACTIVO`, `DEVUELTO`, `VENCIDO`, `CANCELADO`

#### `Checklist` («Aggregate Root»)
- Atributos: `id`, `prestamoId`, `tipo: TipoChecklist`, `fechaInspeccion`, `observaciones`, `fotosUrls`, `completo: Boolean`
- Métodos: `crearInicial()`, `crearDevolucion()`, `compararEstado(): Boolean`

#### `TipoChecklist` («enumeration»)
`ESTADO_INICIAL`, `ESTADO_DEVOLUCION`

#### `Garantia` («Aggregate Root»)
- Atributos: `id`, `prestamoId`, `tipo: TipoGarantia`, `estado: EstadoGarantia`, `fechaRegistro`, `fechaLiberacion`
- Métodos: `registrar()`, `liberar()`, `retener()`

#### `CompromisoResponsabilidad` («Value Object»)
- Atributos: `contenido`, `fechaFirma`, `firmaUrl`, `testigo`
- Métodos: `esValido(): Boolean`

#### `TipoGarantia` («enumeration»)
`DOCUMENTO_IDENTIDAD`, `CARNET_UNIVERSITARIO`, `DEPOSITO_ECONOMICO`, `OTRO`

#### `EstadoGarantia` («enumeration»)
`PENDIENTE`, `REGISTRADA`, `LIBERADA`, `RETENIDA`

---

## 4. Infrastructure (repositorios)

Un repositorio por agregado raíz. La interfaz se define en el dominio y la infraestructura la implementa.

- `UsuarioRepository`: `guardar`, `obtenerPorId`, `obtenerPorCorreo`, `listar`
- `PerfilReputacionRepository`: `guardar`, `obtenerPorUsuario` (incluye sus sanciones), `obtenerPorId` — `Sancion` se persiste solo a través de este repositorio (sin repositorio propio)
- `ExcepcionAcademicaRepository`: `guardar`, `obtenerVigentesPorUsuario`, `obtenerPorId`
- `RecursoRepository`: `guardar`, `obtenerPorId`, `buscarDisponibles(categoria)`, `actualizarEstado`
- `ReservaRepository`: `guardar`, `obtenerPorId`, `obtenerPorUsuario`, `obtenerColaPorRecurso`
- `PrestamoRepository`: `guardar`, `obtenerPorId`, `obtenerActivos`, `obtenerPorUsuario`

---

## Relaciones principales

1. **Usuario → PerfilReputacion** (1:1): asociación entre dos agregados, por `usuarioId`. El perfil se crea automáticamente con puntaje inicial 500 (nivel NORMAL) al primer acceso.
2. **PerfilReputacion ◆ Sancion** (1:N): composición dentro del mismo agregado. Cada sanción lleva `fechaFin` derivada de `TipoSancion.duracionBloqueo()`; al expirar deja de bloquear la elegibilidad.
3. **Usuario → ExcepcionAcademica** (1:N): asociación por `usuarioId`. Nace vigente (sin aprobación); mientras esté vigente cubre sanciones de `TARDANZA` e `INASISTENCIA_RESERVA` en la elegibilidad.
4. **Usuario → Reserva** (1:N): referencia por ID entre contextos.
5. **Reserva → Prestamo** (1 → 0..1): una reserva puede convertirse en un préstamo; se enlazan por `reservaId`.
6. **Prestamo → Checklist / Garantia** (1:N): asociación por `prestamoId`.
   ⚠️ Pendiente de confirmar con quien lleva `prestamos`: si deberían ser entidades dentro de `Prestamo`.
7. **Recurso ◆ FichaTecnica** (1:1): composición (Value Object).
8. **prestamos/reservas → ReputacionService** (integración inter-contexto, solo por servicio `application/` + IDs): `prestamos` llama a `aplicarSancion` (al detectar daño o mora en la devolución vía `Checklist`; en `DANO_TOTAL` pasa el valor del recurso como `montoOpcional`) y a `premiarDevolucionPuntual` (devolución puntual); `reservas` llama a `esElegibleParaPrestamo`, aplica `INASISTENCIA_RESERVA` cuando la reserva vence sin recoger, y usa `obtenerPerfil` (puntaje/nivel) como input de `AlgoritmoPrioridadService` para ordenar la cola de espera: a mejor nivel, mayor prioridad (el peso exacto lo define quien lleva `reservas`).