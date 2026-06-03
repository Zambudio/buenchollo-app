# 🛡️ Security Policy — BuenCholloTech

> **TL;DR** · Si encuentras una vulnerabilidad, escribe a
> `pjzambudio@gmail.com` con asunto `[SECURITY] ...` antes de
> divulgarla públicamente. Respuesta en < 7 días.
>
> 📚 Política operativa completa y controles aplicados:
> [`docs/project/07 · Seguridad`](docs/project/07-security.md).
> Auditoría OWASP con hallazgos detallados:
> [`docs/reference/SECURITY_AUDIT.md`](docs/reference/SECURITY_AUDIT.md).

---

## 📦 Versiones soportadas

| Versión | Soporte de seguridad |
|---|---|
| 🟢 `v1.0.0-tfm` (rama `main`) | ✅ Soporte activo |
| 🔴 Versiones anteriores | ❌ Sin soporte |

---

## 🚨 Cómo reportar una vulnerabilidad

> ⚠️ **NO abras un issue público** ni hagas pull request describiendo
> el problema.

```
1. 📧 Email a pjzambudio@gmail.com
        │
        │  Asunto: [SECURITY] BuenChollo — <título corto>
        │
        ▼
2. 📝 Incluye:
        ├── El problema y dónde se encuentra
        ├── Pasos para reproducir
        ├── PoC mínima (si es posible)
        └── Tu evaluación del impacto
        │
        ▼
3. ⏱️ Compromiso de respuesta:
        ├── 📬 Respuesta inicial en < 7 días
        ├── 🔧 Fix coordinado antes de divulgación pública
        └── 🙏 Reconocimiento al reporter si se acepta divulgación
```

---

## ✅ Qué consideramos vulnerabilidad

Cualquiera de los siguientes en cualquier capa del sistema (backend,
frontend, CI/CD, despliegue):

- 🔓 Bypass de **autenticación** o **autorización**
- 💉 Inyecciones (SQL, XSS, command injection, SSRF)
- 🔑 Exposición de credenciales o datos privados
- 📦 Vulnerabilidades en dependencias de producción no detectadas por
  `pip-audit` o `npm audit`
- 🔒 Bypass de RLS de Supabase
- 📝 Fugas de información sensible en logs o errores

## ❌ Qué NO consideramos vulnerabilidad

- 🛠️ Vulnerabilidades en dependencias de **desarrollo**
  (`wrangler`, `miniflare`, etc.) que no se usan para deploy
- 🤔 Avisos **teóricos** sin prueba de explotación
- 📋 Limitaciones documentadas como **deuda asumida** en
  [`docs/master/09 · Limitaciones`](docs/master/09-limitaciones-y-mejoras-futuras.md)
- ⏱️ Rate limit alcanzado tras intentos legítimos

---

## 🎯 Buenas prácticas si despliegas tu propia instancia

> Si despliegas tu propia copia de BuenCholloTech:

```
✅ Sigue la checklist pre-go-live en docs/project/07
✅ Activa 2FA TOTP en tu cuenta de Supabase del admin
✅ Nunca subas el .env al repositorio
✅ Mantén deps actualizadas vía Dependabot (semanal en CI)
✅ Revisa los reportes del job security-audit en cada release
```

---

> 🕒 *Última actualización: 2026-06-03 · tras sprint S1–S7 de seguridad.*
