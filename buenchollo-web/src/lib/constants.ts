/** Constantes de dominio compartidas en toda la aplicación. */

/** Umbral a partir del cual un chollo se considera "muy caliente" (rojo). */
export const TEMPERATURE_HOT_THRESHOLD = 200;

/** Umbral a partir del cual un chollo se considera "templado" (cian). */
export const TEMPERATURE_WARM_THRESHOLD = 100;

/** Opciones de estado de un chollo. Usadas por el filtro y selector del admin
 *  y reflejan los `status` válidos del backend. */
export const DEAL_STATUS_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "scheduled", label: "Programados" },
  { value: "expired", label: "Caducados" },
  { value: "draft", label: "Borradores" },
] as const;
