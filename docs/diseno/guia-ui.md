# Guía de UI — Sistema de Gestión de Préstamos de Recursos

Propósito: que las cuatro personas (y la IA que usen) produzcan pantallas que parezcan parte del
mismo producto. Esta guía y `frontend/src/estilos/tokens.css` son la fuente de verdad.
**Si algo no está aquí, pregúntalo antes de inventarlo.**

## Resumen rápido (1 página)
**Dónde está cada cosa**

| Archivo | Qué contiene |
|---|---|
| `frontend/src/estilos/tokens.css` | los colores, tamaños y espaciados (se cambian aquí, no en las pantallas) |
| `frontend/src/estilos/global.css` | las clases ya hechas (botones, tablas, avisos…) |
| `frontend/src/features/identidad/pages/LoginPage.jsx` | el ejemplo canónico |
| `docs/diseno/guia-ui.md` | este documento, el detalle |

**Colores clave** (hex exacto de `tokens.css`; si algo no coincide, gana `tokens.css`)

| Token | Hex | Uso |
|---|---|---|
| `--primario` | `#0F766E` | marca, enlaces, botón principal, foco |
| `--primario-hover` | `#115E59` | hover del botón principal |
| `--texto` | `#14282B` | texto principal |
| `--texto-suave` | `#4F6366` | texto secundario, ayudas y metadatos |
| `--fondo` | `#F4F8F7` | fondo de la app |
| `--superficie` | `#FFFFFF` | tarjetas, tablas, navbar y controles |
| `--borde` | `#D9E3E2` | bordes y separadores |
| `--error` | `#BE123C` | error, peligro y botón de peligro |

Estados: `--exito #3F6212`, `--aviso #A94A07`, `--info #1D4ED8` y `--neutra #4F6366`, cada uno con su `-suave` para fondos (tabla completa en la sección 3).

**Letra y formas**
- Fuente del sistema (`--fuente-base`), sin fuentes externas.
- Cuerpo 16px, textos secundarios 14px, títulos de página 28px; máximo 3 tamaños por pantalla.
- Radio 8px en botones e inputs y 12px en tarjetas y tablas.
- Sombra solo en tarjetas y en hover.

**Las clases que existen** (todas en `global.css`; detalle en las secciones 6 y 7)
- Estructura: `.contenedor`, `.contenedor--estrecho`, `.pagina`, `.pagina__cabecera`, `.pagina__titulo`, `.pagina__subtitulo`
- Navegación: `.navbar`, `.navbar__contenido`, `.navbar__marca`, `.navbar__enlaces`, `.navbar__enlace`, `.navbar__enlace--activo`, `.navbar__menu-boton`, `.navbar__enlaces--abierto`
- Botones: `.boton` + `--primario`, `--secundario`, `--peligro`, `--fantasma`, `--bloque`, `--sm`
- Formularios y contenedores: `.formulario`, `.campo`, `.campo__etiqueta`, `.campo__control`, `.campo__ayuda`, `.campo__error`, `.formulario__acciones`; `.tarjeta`, `.tarjeta__cabecera`, `.tarjeta__cuerpo`, `.tarjeta__pie`, `.tarjeta--enlace`
- Mensajes y datos: `.alerta` + `--error`, `--exito`, `--aviso`, `--info`; `.insignia` + `--exito`, `--aviso`, `--error`, `--info`, `--neutra`; `.tabla__contenedor`, `.tabla`, `.tabla--apilada` (cada `td` con `data-etiqueta`), `.estado-vacio`, `.cargando`, `.grilla`

**Las 3 reglas que no se rompen**
1. Sin colores literales (`#hex`, `red`) fuera de `tokens.css`.
2. Sin `style={{}}` salvo valor dinámico justificado.
3. Sin dependencias nuevas: ni Tailwind, ni iconos, ni fuentes externas.

**Cómo usarlo en 3 pasos**: 1) lee `LoginPage.jsx`; 2) copia los snippets de la [sección 7](#7-componentes); 3) pega el prompt de la [sección 12](#12-prompt-base-para-ia) a la IA antes de pedir una pantalla.

---

## 1. Para qué sirve y cómo usarla

- Es el contrato visual común de los cuatro bounded contexts.
- Fuente de verdad: este documento y `frontend/src/estilos/tokens.css`; los valores no se duplican.
- Todo componente consume tokens (`var(--primario)`) o clases de `frontend/src/estilos/global.css`.
- Regla de oro: nada de colores literales (`#0F766E`, `red`, `rgb(...)`), nada de `style={{}}` salvo
  valores dinámicos que no se puedan expresar con una clase (por ejemplo, el ancho de una barra de
  progreso calculado en JS).
- Si falta un componente, se añade a `global.css` y se documenta aquí; no se improvisa por feature.
- Antes de escribir una pantalla nueva, lee las secciones 6 y 7.

## 2. Principios

1. **Consistencia sobre creatividad**: dos pantallas del mismo tipo se ven igual.
2. **Claridad antes que decoración**: sin degradados, sin animaciones llamativas, sin sombras fuertes.
3. **Móvil primero**: se diseña a 375px y se amplía; nunca al revés.
4. **Accesible por defecto**: contraste AA, foco visible, etiquetas y errores con texto.
5. **Español en la UI**: identificadores, textos y comentarios en español (ver `docs/constitution.md`).

## 3. Paleta

Tema claro únicamente. Los nombres son por **rol**, no por tono, para poder redefinirlos en oscuro.

| Token | Valor | Uso | Contraste sobre blanco |
|---|---|---|---|
| `--primario` | `#0F766E` | marca, enlaces, botón principal, foco | 5.47:1 |
| `--primario-hover` | `#115E59` | hover del botón principal | 7.58:1 |
| `--primario-suave` | `#DFF1EF` | fondo de enlace activo y selección | fondo (no texto) |
| `--sobre-primario` | `#FFFFFF` | texto sobre marca y estados | 5.47:1 sobre `--primario` |
| `--texto` | `#14282B` | texto principal | 15.35:1 |
| `--texto-suave` | `#4F6366` | texto secundario, ayudas, metadatos | 6.35:1 |
| `--fondo` | `#F4F8F7` | fondo de la app | fondo |
| `--superficie` | `#FFFFFF` | tarjetas, tablas, navbar, controles | fondo |
| `--borde` | `#D9E3E2` | bordes y separadores | no es texto |
| `--exito` | `#3F6212` | éxito, estado disponible | 7.08:1 |
| `--exito-suave` | `#EEF5E1` | fondo de éxito | fondo |
| `--aviso` | `#A94A07` | advertencia, mantenimiento, pendiente | 5.72:1 |
| `--aviso-suave` | `#FEF3DC` | fondo de advertencia | fondo |
| `--error` | `#BE123C` | error, peligro, vencido | 6.29:1 |
| `--error-hover` | `#9F1239` | hover del botón de peligro | 8.02:1 |
| `--error-suave` | `#FDE8ED` | fondo de error | fondo |
| `--info` | `#1D4ED8` | información, en curso | 6.70:1 |
| `--info-suave` | `#E8EEFC` | fondo de información | fondo |
| `--neutra` | `#4F6366` | estado neutro, cancelado | 6.35:1 |
| `--neutra-suave` | `#EDF2F1` | fondo neutro | fondo |

Notas:

- El verde de éxito inicial (`#4D7C0F`) sí cumplía AA sobre blanco (**4.99:1**), pero daba **4.47:1**
  sobre su propio fondo suave `#EEF5E1` y ahí no cumplía. El fallo estaba en el uso real —texto fuerte
  sobre fondo suave, que es como se pintan insignias y alertas—, no sobre blanco; por eso se oscureció
  a `#3F6212` (7.08:1 sobre blanco y 6.33:1 sobre `#EEF5E1`). No lo aclares "porque se ve mejor".
- `--primario` es teal y no verde para no competir con los colores de estado (éxito/error/aviso).
- Texto fuerte sobre fondo suave también cumple: éxito 6.33:1, aviso 5.20:1, error 5.37:1,
  info 5.77:1, neutro 5.61:1, primario 4.68:1.
- **Prohibido** usar colores fuera de los tokens: ni en CSS, ni en JSX, ni en `style={{}}`.

## 4. Tipografía y escala

Fuente del sistema (`--fuente-base`): nada de fuentes externas ni dependencias.

| Token | Tamaño | Uso |
|---|---|---|
| `--texto-xs` | 12px | ayudas, insignias, cabeceras de tabla |
| `--texto-sm` | 14px | texto secundario, tablas, botones pequeños |
| `--texto-base` | 16px | cuerpo (mínimo permitido en la UI) |
| `--texto-lg` | 18px | subtítulos y destacados |
| `--texto-xl` | 22px | título de sección |
| `--texto-2xl` | 28px | título de página (`.pagina__titulo`) |

| Token | Peso | Uso |
|---|---|---|
| `--peso-normal` | 400 | cuerpo |
| `--peso-medio` | 500 | etiquetas, botones, enlace activo |
| `--peso-fuerte` | 600 | marca, énfasis, cabeceras |
| `--peso-titulo` | 700 | títulos de página |

Reglas: cuerpo a 16px o más; **máximo 3 tamaños por pantalla**; títulos con
`--interlineado-titulo` (1.2); párrafos con `--interlineado` (1.5).

## 5. Espaciado, radios y sombras

- Escala de 4px: `--espacio-1` (4px) a `--espacio-8` (64px). No inventes valores intermedios.
- Separación entre campos: `--espacio-4`. Dentro de una tarjeta: `--espacio-5`.
  Entre secciones: `--espacio-6` o `--espacio-7`.
- Radios: `--radio-md` (8px) para botones e inputs; `--radio-lg` (12px) para tarjetas, tablas y
  contenedores; `--radio-completo` solo para insignias; `--radio-sm` para enlaces de navbar.
- Sombras: `--sombra-sm` en tarjetas en reposo; `--sombra-md` solo en hover o en elementos flotantes
  (menús, popovers); `--sombra-lg` solo para modales. Si dudas, no pongas sombra.

## 6. Layout y navegación

- Todo el contenido va dentro de `.contenedor` (máximo 1120px, padding lateral).
- Formularios y login usan `.contenedor--estrecho` (420px).
- **El layout monta la estructura; la página aporta solo su contenido.** El layout compartido
  (`frontend/src/layout/`, lo mantiene la Persona 1) pinta la barra superior y el
  `<main className="contenedor pagina">` donde se renderiza la ruta activa. **Cada página NO monta
  `<main>` ni la navbar**: entrega únicamente su contenido, con `.pagina__cabecera`,
  `.pagina__titulo` y `.pagina__subtitulo`. Debe haber un único `<main>` por documento, el del
  layout; `ReputacionPage`, `UsuariosPage`, `MisReservasPage` y `HistorialPage` ya lo cumplen (las
  páginas de `reservas` y `prestamos` ya no montan `<main>` propio tras la Spec 005).
- Barra superior (la monta el layout): `<header className="navbar">` con
  `.navbar__contenido contenedor`, `.navbar__marca` y un único
  `<nav className="navbar__enlaces" aria-label="Navegación principal">` con `.navbar__enlace`
  (activo con `.navbar__enlace--activo`) y «Cerrar sesión» como
  `<button className="boton boton--fantasma">`. La marca es texto plano y **no** es un enlace: no
  hay página de Inicio y la raíz `/` redirige a `/recursos`.
- **Sin menú móvil por ahora**: `.navbar__menu-boton` y `.navbar__enlaces--abierto` existen en
  `global.css`, pero el layout actual **no** los usa. Por debajo de 900px `.navbar__enlaces` se
  oculta y la barra se queda solo con la marca; es deuda de responsive aceptada (no es un fallo de
  las pantallas, pero tampoco hay forma de navegar por la barra a ese ancho).

### Rutas actuales y visibilidad por rol

Rutas existentes en `frontend/src/App.jsx`: `/login`, `/registro`, `/usuarios`, `/reputacion`,
`/recursos`, `/reservas`, `/historial`, `/gestion-reputacion`.

**Propuesta de navegación visible, pendiente de confirmar con el equipo.**

| Ruta | Pantalla | ESTUDIANTE / DOCENTE / PERSONAL_ADMINISTRATIVO | GESTOR_ALMACEN | ADMINISTRADOR_SISTEMA |
|---|---|---|---|---|
| `/login` | Iniciar sesión | pública | pública | pública |
| `/registro` | Registro | pública | pública | pública |
| `/recursos` | Buscar recursos | sí | sí | sí |
| `/reservas` | Mis reservas / Reservas | sí | sí | sí |
| `/historial` | Historial / Préstamos | sí | sí | sí |
| `/reputacion` | Mi reputación / Sanciones | sí | sí | sí |
| `/usuarios` | Usuarios | no | sí | sí |
| `/gestion-reputacion` | Gestión de reputación | no | sí | sí |

- `GESTOR_ALMACEN` ve las acciones de gestión de usuarios (`/usuarios`) y tiene una ruta propia para reputación (`/gestion-reputacion`); las acciones de gestión de préstamos siguen siendo de su propio contexto dentro de las mismas rutas.
- `ADMINISTRADOR_SISTEMA` ve todo, con la misma barra de navegación que `GESTOR_ALMACEN`.
- `PERSONAL_ADMINISTRATIVO` comparte exactamente la misma visibilidad que `ESTUDIANTE` y `DOCENTE`.
- **Rótulo largo en la barra**: «Gestión de reputación» es el rótulo más largo de la navegación. La guía no fija una longitud máxima para los rótulos de enlace (solo que sean únicos), pero debe tenerse en cuenta que `.navbar__enlaces` no envuelve líneas (`flex-wrap`). Por debajo de 900px la barra oculta los enlaces (deuda aceptada); en anchos intermedios (900–1100px) se vigila que no desborde horizontalmente (D8, R8).
- **Hoy no existen guardas por rol en el frontend**: esta tabla es solo navegación visible, no
  seguridad. La autorización real vive en el backend.

## 7. Componentes

LoginPage (`frontend/src/features/identidad/pages/LoginPage.jsx`) es el **ejemplo canónico**.

### Botón

Usa `.boton` más una variante. Primario: acción principal de la pantalla (una sola). Secundario:
acciones alternativas. Peligro: borrar o cancelar algo irreversible. Fantasma: acciones terciarias.

```jsx
<button type="submit" className="boton boton--primario">Guardar</button>
<button type="button" className="boton boton--secundario">Cancelar</button>
<button type="button" className="boton boton--peligro boton--sm">Eliminar</button>
```

### Campo de texto

Etiqueta siempre asociada con `htmlFor`/`id`; error con texto y `aria-invalid`.

```jsx
<div className="campo">
  <label className="campo__etiqueta" htmlFor="correo">Correo electrónico</label>
  <input className="campo__control" id="correo" type="email" required />
  <span className="campo__ayuda">Usa tu correo institucional.</span>
</div>
```

Con error:

```jsx
<input className="campo__control" id="correo" aria-invalid="true" aria-describedby="error-correo" />
<span className="campo__error" id="error-correo">El correo es obligatorio.</span>
```

### Tarjeta

Agrupa información relacionada. `.tarjeta--enlace` cuando toda la tarjeta navega.

```jsx
<article className="tarjeta">
  <div className="tarjeta__cabecera">Proyector Epson</div>
  <div className="tarjeta__cuerpo">Disponible en el laboratorio 2.</div>
  <div className="tarjeta__pie">
    <span className="insignia insignia--exito">DISPONIBLE</span>
  </div>
</article>
```

### Alerta

Mensaje de resultado o error de formulario. Siempre con texto, nunca solo color.

```jsx
<div className="alerta alerta--error" role="alert">Correo o contraseña incorrectos</div>
<div className="alerta alerta--exito">Reserva confirmada.</div>
```

### Insignia

Estado breve dentro de tarjetas y tablas. El texto es obligatorio; el color acompaña, no informa solo.

```jsx
<span className="insignia insignia--aviso">PENDIENTE</span>
<span className="insignia insignia--neutra">CANCELADA</span>
```

### Tabla

Con `.tabla__contenedor` para el scroll horizontal. En móvil usa `.tabla--apilada`: cada `td` debe
llevar `data-etiqueta` con el nombre de su columna.

```jsx
<div className="tabla__contenedor">
  <table className="tabla tabla--apilada">
    <thead>
      <tr>
        <th>Recurso</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td data-etiqueta="Recurso">Proyector Epson</td>
        <td data-etiqueta="Estado"><span className="insignia insignia--exito">DISPONIBLE</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

### Estado vacío

Cuando una lista no tiene resultados. Explica qué pasa y qué puede hacer la persona.

```jsx
<div className="estado-vacio">
  <p className="estado-vacio__titulo">No hay reservas</p>
  <p>Todavía no has reservado ningún recurso.</p>
  <Link className="boton boton--primario" to="/recursos">Buscar recursos</Link>
</div>
```

Para navegar dentro de la app se usa `Link` de `react-router-dom` (con `to`); `href` solo para enlaces
externos.

### Cargando

Mientras llega la respuesta. Texto claro, sin spinners caseros.

```jsx
<p className="cargando" role="status">Cargando reservas...</p>
```

## 8. Responsive

- Móvil primero: escribe el estilo base para 375px y amplía después.
- Breakpoints literales: **640px** (móvil/tableta) y **900px** (tableta/escritorio). Los tokens no
  funcionan dentro de media queries; por eso van en píxeles.
- Tablas: `.tabla--apilada` convierte cada fila en tarjeta por debajo de 640px.
- Formularios: una sola columna siempre; no metas dos campos en la misma línea en móvil.
- Áreas táctiles de al menos 44px de alto (los botones y controles ya lo cumplen).
- Prueba toda pantalla a 375px de ancho antes de dar el PR por listo.

## 9. Estados del dominio → insignias

| Entidad | Estado | Clase | Color |
|---|---|---|---|
| Reserva | `PENDIENTE` | `insignia--aviso` | ámbar |
| Reserva | `CONFIRMADA` | `insignia--exito` | verde |
| Reserva | `CANCELADA` | `insignia--neutra` | gris |
| Reserva | `VENCIDA` | `insignia--error` | rojo |
| Reserva | `CONVERTIDA` | `insignia--info` | azul |
| Préstamo | `ACTIVO` | `insignia--info` | azul |
| Préstamo | `ENTREGADO` | `insignia--info` | azul |
| Préstamo | `DEVUELTO` | `insignia--exito` | verde |
| Préstamo | `VENCIDO` | `insignia--error` | rojo |
| Préstamo | `CANCELADO` | `insignia--neutra` | gris |
| Recurso | `DISPONIBLE` | `insignia--exito` | verde |
| Recurso | `EN_USO` | `insignia--info` | azul |
| Recurso | `MANTENIMIENTO` | `insignia--aviso` | ámbar |
| Recurso | `FUERA_DE_SERVICIO` | `insignia--error` | rojo |
| Reputación | `BAJO` | `insignia--error` | rojo |
| Reputación | `NORMAL` | `insignia--neutra` | gris |
| Reputación | `BUENO` | `insignia--info` | azul |
| Reputación | `EXCELENTE` | `insignia--exito` | verde |
| Sanción | `Vigente` | `insignia--error` | rojo |
| Sanción | `Expirada` | `insignia--neutra` | gris |
| Excepción | `VIGENTE` | `insignia--exito` | verde |
| Excepción | `PROGRAMADA` | `insignia--info` | azul |
| Excepción | `VENCIDA` | `insignia--aviso` | ámbar |
| Excepción | `ANULADA` | `insignia--neutra` | gris |

Regla: **el color nunca es la única señal**; la insignia siempre muestra el estado como texto.

## 10. Accesibilidad

- Contraste mínimo 4.5:1 en texto normal (la paleta ya lo cumple; no la modifiques a ojo).
- Foco visible siempre: no elimines `outline` ni `:focus-visible`.
- Toda etiqueta asociada a su control con `htmlFor`/`id`; ningún input sin etiqueta.
- Los errores llevan texto: nunca solo borde rojo. Usa `aria-invalid` y `aria-describedby`.
- El color no comunica nada por sí solo: añade texto o forma.
- El documento ya declara `lang="es"`; no lo cambies.
- Mensajes de resultado con `role="alert"` o `aria-live="polite"`.
- Objetivos táctiles de 44x44px como mínimo.

## 11. Haz / No hagas

| Haz | No hagas |
|---|---|
| `color: var(--primario)` | `color: #0F766E` |
| `<button className="boton boton--primario">` | `<button style={{ background: "blue" }}>` |
| Reutilizar clases de `global.css` | Copiar CSS de otra feature |
| Textos en español: "Guardar" | Textos en inglés: "Submit" |
| Una acción primaria por pantalla | Tres botones primarios compitiendo |
| `4.5:1` verificado con los tokens | Aclarar un color "porque se ve mejor" |
| Insignia con el estado como texto | Cuadradito de color sin texto |
| `data-etiqueta` en cada `td` apilable | Tabla que se corta en móvil |
| Probar a 375px y con teclado | Diseñar solo en 1920px |
| `.contenedor` para el ancho | `maxWidth: "1200px"` inline |

## 12. Prompt base para IA

Copia esto al inicio de cualquier petición de pantalla:

```text
Vas a construir una pantalla de este proyecto (React 18 + Vite, español).

Antes de escribir código, lee:
- docs/diseno/guia-ui.md (guía de UI, fuente de verdad)
- frontend/src/estilos/tokens.css (tokens)
- frontend/src/estilos/global.css (clases disponibles)
- frontend/src/features/identidad/pages/LoginPage.jsx (ejemplo canónico)

Reglas obligatorias:
- Usa las clases existentes de global.css. Si falta un componente, dilo y propón añadirlo a
  global.css; no lo inventes dentro de la feature.
- No añadas dependencias ni librerías de UI, iconos o fuentes.
- No uses style={{}} ni colores literales. Solo var(--token) si escribes CSS.
- Textos, identificadores y comentarios en español.
- Accesibilidad AA: etiquetas asociadas, foco visible, errores con texto, contraste 4.5:1.
- Móvil primero, breakpoints 640px y 900px; probar a 375px.
- Al terminar, enumera qué componentes y clases has usado y qué has tenido que decidir.
```

## 13. Checklist antes de un PR

- [ ] La pantalla usa `.contenedor`, `.pagina` y los títulos con `.pagina__titulo`/`.pagina__subtitulo`.
- [ ] No hay ni un color literal ni `style={{}}` (salvo valor dinámico justificado).
- [ ] Todos los botones usan `.boton` con su variante y hay una sola acción primaria.
- [ ] Los formularios usan `.campo`, `.campo__etiqueta` y `.campo__control`, con etiquetas asociadas.
- [ ] Los errores muestran texto además del color (`aria-invalid`, `role="alert"`).
- [ ] Los estados usan `.insignia` con el mapeo de la sección 9 y texto visible.
- [ ] Las tablas usan `.tabla__contenedor` y, si son apilables, cada `td` tiene `data-etiqueta`.
- [ ] Se ha probado a 375px, 900px y escritorio.
- [ ] Se ha revisado con teclado (foco visible en todo).
- [ ] No se ha tocado `package.json` ni archivos de otro contexto.

## 14. Modo oscuro futuro

Basta con redefinir los tokens en `[data-tema="oscuro"]` (plantilla comentada al final de
`tokens.css`); ningún componente cambia. Hay que ajustar fondo, superficie, texto, texto suave,
borde, primario suave y los fondos semánticos suaves. Si alguien escribió un hex a mano, eso hay que
corregirlo antes. El tema oscuro no se implementa hasta que el equipo lo acuerde.

## 15. Cambios en esta guía

Cualquier cambio de token, clase o patrón se avisa al equipo y se actualiza este documento y
`tokens.css` en el mismo PR. Los archivos compartidos se avisan antes de tocarlos (ver `README.md`).
No se crean variantes locales por feature.

Cambios registrados:

- **2026-10-20** — El layout compartido (`frontend/src/layout/`) pasa a montar la navbar y el
  `<main className="contenedor pagina">`, y cada página aporta solo su contenido (§6).
  `ReputacionPage` y `UsuariosPage` dejan de aportar su propio `<main>`, la raíz `/` redirige a
  `/recursos` (no hay página de Inicio) y el menú móvil queda sin implementar. Spec 003.
- **2026-10-21** — Incorporación del panel de gestión en `/gestion-reputacion` para `GESTOR_ALMACEN` y
  `ADMINISTRADOR_SISTEMA`. Se actualiza la visibilidad de `/usuarios` para el gestor, se incorpora
  `PERSONAL_ADMINISTRATIVO` a la tabla de visibilidad, se añade la nota sobre el rótulo largo en la
  navbar (§6) y se documentan en §9 las insignias para estados de sanción (`Vigente`, `Expirada`) y de
  excepción académica (`VIGENTE`, `PROGRAMADA`, `VENCIDA`, `ANULADA`). Spec 004.
- **2026-10-27** — Las páginas de reservas (`MisReservasPage`) y préstamos (`HistorialPage`) eliminan
  su `<main>` anidado y estilos en línea (§6), adoptando el layout compartido y las clases de
  `global.css`. Se añade el estado `ENTREGADO` a la tabla de estados de préstamo con insignia
  `insignia--info` (§9). Spec 005.
