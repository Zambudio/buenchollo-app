# Banner de tops comunitarios — 2026-11-07

La portada sustituye el aviso de tops por un podio con fotografías reales, colores del tema y una composición fluida para móvil. El CTA principal abre las categorías y el nombre/productos del podio abren su categoría.

`loadBannerTops` consulta las primeras seis categorías raíz con ofertas y sus clasificaciones mediante la API existente. Las consultas de tops se ejecutan en paralelo y cada fallo se aísla. Se conservan las posiciones de la API, sin mezclar categorías ni inventar puestos. No se persisten imágenes ni clasificaciones: se actualizan al ejecutar el loader de portada (en el navegador se reutiliza el resultado durante 60 s para que cambiar de filtro o de página no repita las 7 peticiones; el SSR consulta siempre). No se hace polling en segundo plano.

El banner rota entre categorías cada cinco segundos y solo muestra flechas para navegar. Tras usar una flecha, el siguiente cambio automático espera cinco segundos. Respeta movimiento reducido y no avanza con la pestaña oculta. El diseño compacto reduce imágenes, podio y espaciado vertical. Si no hay votos se indica explícitamente. Si falla una imagen se muestra un icono; si no hay tops se conserva el CTA con una corona decorativa.

Validación: 468 pruebas frontend, TypeScript, ESLint sin errores y build SSR. Revisión Playwright con API local en 320/375/390/640/1280 px y ambos temas: imágenes cargadas, productos dentro del banner y navegación entre categorías. Sin cambios de API, base de datos ni dependencias.
