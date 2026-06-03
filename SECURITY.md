# Security Policy — BuenCholloTech

> Política de divulgación responsable. La documentación completa de
> controles, política operativa y plan de respuesta a incidentes vive
> en [`docs/project/07-security.md`](docs/project/07-security.md).
> La auditoría OWASP Top 10 con hallazgos priorizados está en
> [`docs/reference/SECURITY_AUDIT.md`](docs/reference/SECURITY_AUDIT.md).

## Versiones soportadas

| Versión | Soporte de seguridad |
|---|---|
| `v1.0.0-tfm` (rama `main`) | ✅ Soporte activo |
| Versiones anteriores | ❌ Sin soporte |

## Cómo reportar una vulnerabilidad

Si encuentras una vulnerabilidad en BuenCholloTech:

1. **NO abras un issue público** ni hagas pull request describiendo
   el problema.
2. Envía un correo a [`pjzambudio@gmail.com`](mailto:pjzambudio@gmail.com)
   con asunto **`[SECURITY] BuenChollo — <título corto>`** describiendo:
   - El problema y dónde se encuentra.
   - Pasos para reproducir.
   - Si es posible, una prueba de concepto mínima (PoC).
   - Tu evaluación del impacto.
3. Compromiso de respuesta:
   - Respuesta inicial en **< 7 días** desde el envío.
   - Fix coordinado **antes de divulgación pública**.
   - Reconocimiento explícito al reporter si se acepta divulgación
     coordinada (a menos que prefieras anonimato).

## Qué consideramos vulnerabilidad

Cualquiera de los siguientes en cualquier capa del sistema (backend,
frontend, CI/CD, despliegue):

- Bypass de autenticación o autorización.
- Inyecciones (SQL, XSS, command injection, SSRF).
- Exposición de credenciales o datos privados.
- Vulnerabilidades en dependencias de producción no detectadas por
  `pip-audit` o `npm audit`.
- Bypass de RLS de Supabase.
- Fugas de información sensible en logs o errores.

## Qué NO consideramos vulnerabilidad

- Vulnerabilidades en dependencias de desarrollo (`wrangler`,
  `miniflare`, etc.) que no se usan para deploy.
- Avisos teóricos sin prueba de explotación.
- Limitaciones documentadas como deuda asumida en
  [`docs/master/09-limitaciones-y-mejoras-futuras.md`](docs/master/09-limitaciones-y-mejoras-futuras.md).
- Rate limit alcanzado tras intentos legítimos.

## Buenas prácticas para usuarios y administradores

Si despliegas tu propia instancia de BuenCholloTech:

- Sigue la **checklist pre-go-live** en
  [`docs/project/07-security.md`](docs/project/07-security.md).
- Activa **2FA TOTP** en tu cuenta de Supabase del admin.
- Nunca subas el `.env` al repositorio.
- Mantén las dependencias actualizadas vía Dependabot (semanal en CI).
- Revisa los reportes del job `security-audit` en cada release.

---

*Última actualización: 2026-06-02 · tras sprint S1–S7 de seguridad.*
