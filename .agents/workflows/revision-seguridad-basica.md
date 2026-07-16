---
description: revision-seguridad-basica
---

Revisa la seguridad del código actual aplicando Security by Design, Security by Default y OWASP básico.

No modifiques código todavía.

Comprueba:
- secretos hardcodeados,
- uso correcto de .env,
- exposición de errores internos,
- validación de entrada,
- CORS,
- autenticación,
- autorización,
- control de acceso por roles,
- SQL injection,
- dependencias inseguras,
- logs con información sensible,
- endpoints públicos peligrosos,
- subida o uso de URLs externas,
- integración con Amazon,
- integración con Telegram.

Devuelve:
1. Riesgos críticos.
2. Riesgos medios.
3. Riesgos bajos.
4. Recomendaciones.
5. Cambios mínimos para dejarlo aceptable en MVP.