---
name: feedback_no_continuar_con_critico
description: No ofrecer seguir adelante si hay un aspecto crítico sin resolver; parar y arreglarlo primero.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1126b10b-ffa1-4fb6-855d-3105e06fde72
---

Cuando aparezca un problema crítico (entorno roto, hooks fallando, build/datos en riesgo, seguridad), **NO** sugerir continuar con la siguiente tarea dejándolo pendiente. Hay que parar, resolverlo y verificar antes de avanzar.

**Why:** Pedro lo pidió expresamente tras un caso en que ofrecí "seguir a T1 o arreglar el node_modules corrupto"; dejar pendiente algo crítico arrastra fallos a todos los pasos siguientes.

**How to apply:** ante un fallo crítico, plantear solo opciones para resolverlo (no "¿seguimos o lo arreglamos?"). Relacionado con [[feedback_forma_trabajo_iterativa]] y [[project_synology_excluir_node_modules]].
