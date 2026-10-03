# Lenguaje de dominio de BuenCholloTech

Glosario canónico del producto. Define los términos funcionales; los detalles técnicos viven en `docs/` y en los ADR.

## Catálogo y publicación

**Chollo**:
Oferta tecnológica curada que puede publicarse en la web y difundirse a otros canales.
_Evitar_: Anuncio, producto, post.

**Publicación programada**:
Publicación futura de un chollo, con fecha, canal de Telegram y contenido editable antes de ejecutarse.
_Evitar_: Tarea programada, cron, anuncio programado.

**Tarea programada**:
Proceso recurrente de mantenimiento, como la revisión periódica de precios. No representa una publicación pendiente.
_Evitar_: Publicación programada, cron cuando se hable del concepto funcional.

**Tienda**:
Comercio de procedencia del chollo.
_Evitar_: Vendedor, proveedor.

**Categoría**:
Clasificación principal de un chollo.

**Subcategoría**:
Clasificación dependiente de una categoría; nunca se selecciona fuera de su categoría principal.

## Audiencia y atribución

**Visita**:
Carga pública válida de una página registrada por la analítica propia.
_Evitar_: Visitante, sesión.

**Visitante único**:
Navegador distinto identificado de forma seudónima dentro del periodo consultado.
_Evitar_: Usuario, persona única.

**Sesión**:
Bloque de navegación de un visitante en el que se conserva el primer origen de entrada.
_Evitar_: Visita.

**Procedencia**:
Origen atribuido al inicio de una sesión, por ejemplo Telegram, buscador, referencia externa o acceso directo.
_Evitar_: Referer como término funcional.

**Entrada Telegram**:
Acceso que pasa por la ruta canónica `/telegram` y conserva Telegram como procedencia aunque después navegue por la web o el blog.

**Dispositivo excluido**:
Navegador marcado por el administrador para que su actividad interna no contamine las métricas de audiencia.
_Evitar_: Usuario bloqueado.

## Contenido y comunidad

**Artículo**:
Contenido editorial del blog, independiente de un chollo aunque pueda incluir recomendaciones afiliadas.
_Evitar_: Post cuando pueda confundirse con una publicación de Telegram.

**Alerta**:
Regla creada por un usuario para detectar chollos que cumplen sus criterios.
_Evitar_: Notificación.

**Notificación**:
Aviso generado cuando una alerta coincide o cuando el sistema comunica un evento al usuario.
_Evitar_: Alerta.
