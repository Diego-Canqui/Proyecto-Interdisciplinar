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
- `login(credenciales): String` (devuelve el token JWT)
- `logout(token): Boolean` (JWT sin estado: el cliente descarta el token)
- `obtenerUsuarioActual(): UsuarioDTO`

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
- `obtenerPerfil(idUsuario: UUID): PerfilReputacionDTO`
- `esElegibleParaPrestamo(idUsuario: UUID): Boolean` (lo consumen `reservas` y `prestamos`)
- `aplicarSancion(idUsuario: UUID, tipo: TipoSancion, motivo: String): void`
- `registrarExcepcion(idUsuario: UUID, motivo: String, inicio, fin): void`

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
- Atributos: `id: UUID`, `nombre`, `correo`, `telefono`, `passwordHash: String`, `estado: Boolean`, `roles: Set<RolUsuario>`
- Métodos: `actualizarPerfil()`, `cambiarEstado()`
- La contraseña se guarda solo como hash y nunca sale en DTOs ni respuestas.

#### `RolUsuario` («enumeration»)
`ESTUDIANTE`, `DOCENTE`, `PERSONAL_ADMINISTRATIVO`, `GESTOR_ALMACEN`, `ADMINISTRADOR_SISTEMA`

#### `PerfilReputacion` («Aggregate Root»)
- Atributos: `id: UUID`, `usuarioId: UUID`, `puntaje: PuntajeReputacion`, `nivel: NivelReputacion`, `fechaActualizacion: DateTime`, `sanciones: List<Sancion>`
- Métodos: `recalcularNivel()`, `aplicarSancion(sancion)`, `esElegibleParaPrestamo(): Boolean`

#### `Sancion` («Entity», dentro del agregado PerfilReputacion)
- Atributos: `id: UUID`, `tipo: TipoSancion`, `puntosDescuento: int`, `montoDescuento: decimal`, `motivo: String`, `fechaAplicacion: DateTime`, `activa: Boolean`
- Métodos: `aplicar()`, `calcularDescuento(): int`, `generarCobro(): Boolean`
- No tiene repositorio propio: se accede a través de `PerfilReputacion`.

#### `PuntajeReputacion` («Value Object»)
- Atributos: `puntos: int`
- Métodos: `sumar(p: int)`, `restar(p: int)`, `esValido(): Boolean`

#### `NivelReputacion` («enumeration»)
`BAJO`, `NORMAL`, `BUENO`, `EXCELENTE`

#### `TipoSancion` («enumeration»)
`TARDANZA`, `DANO_PARCIAL`, `DANO_TOTAL`, `INASISTENCIA_RESERVA`

#### `ExcepcionAcademica` («Aggregate Root»)
- Atributos: `id: UUID`, `usuarioId: UUID`, `motivo`, `fechaInicio`, `fechaFin`, `activa: Boolean`
- Métodos: `aprobar()`, `rechazar()`, `esVigente(): Boolean`

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
- `PerfilReputacionRepository`: `guardar`, `obtenerPorUsuario` (incluye sus sanciones)
- `ExcepcionAcademicaRepository`: `guardar`, `obtenerVigentesPorUsuario`
- `RecursoRepository`: `guardar`, `obtenerPorId`, `buscarDisponibles(categoria)`, `actualizarEstado`
- `ReservaRepository`: `guardar`, `obtenerPorId`, `obtenerPorUsuario`, `obtenerColaPorRecurso`
- `PrestamoRepository`: `guardar`, `obtenerPorId`, `obtenerActivos`, `obtenerPorUsuario`

---

## Relaciones principales

1. **Usuario → PerfilReputacion** (1:1): asociación entre dos agregados, por `usuarioId`.
2. **PerfilReputacion ◆ Sancion** (1:N): composición dentro del mismo agregado.
3. **Usuario → ExcepcionAcademica** (1:N): asociación por `usuarioId`.
4. **Usuario → Reserva** (1:N): referencia por ID entre contextos.
5. **Reserva → Prestamo** (1 → 0..1): una reserva puede convertirse en un préstamo; se enlazan por `reservaId`.
6. **Prestamo → Checklist / Garantia** (1:N): asociación por `prestamoId`.
   ⚠️ Pendiente de confirmar con quien lleva `prestamos`: si deberían ser entidades dentro de `Prestamo`.
7. **Recurso ◆ FichaTecnica** (1:1): composición (Value Object).