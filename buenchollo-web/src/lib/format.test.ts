/** Tests unitarios de los helpers de formato.
 *
 *  Funciones puras → tests deterministas con AAA. `formatRelativeTime` se
 *  testea con fake timers porque depende de Date.now(); el resto son
 *  cálculos sin efectos.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  calculateDiscount,
  formatPrice,
  formatRelativeTime,
  slugify,
  temperatureColor,
  toDatetimeLocal,
} from "@/lib/format";

describe("formatPrice", () => {
  it("muestra entero sin decimales cuando el precio es entero", () => {
    // Intl normaliza el espacio antes del símbolo a NBSP (\u00a0) en es-ES.
    expect(formatPrice(99)).toBe("99\u00a0€");
  });

  it("muestra dos decimales cuando hay parte fraccionaria", () => {
    expect(formatPrice(99.95)).toBe("99,95\u00a0€");
  });

  it("devuelve el placeholder '—' cuando el precio es null", () => {
    expect(formatPrice(null)).toBe("—");
  });

  it("devuelve el placeholder '—' cuando el precio es undefined", () => {
    expect(formatPrice(undefined)).toBe("—");
  });
});

describe("calculateDiscount", () => {
  it("calcula el porcentaje entero redondeado", () => {
    expect(calculateDiscount(75, 100)).toBe(25);
    expect(calculateDiscount(33.33, 100)).toBe(67); // redondea a entero
  });

  it("devuelve null si el precio anterior es menor o igual al actual", () => {
    expect(calculateDiscount(100, 100)).toBeNull();
    expect(calculateDiscount(100, 80)).toBeNull();
  });

  it("devuelve null cuando falta cualquiera de los dos precios", () => {
    expect(calculateDiscount(null, 100)).toBeNull();
    expect(calculateDiscount(75, null)).toBeNull();
    expect(calculateDiscount(undefined, undefined)).toBeNull();
  });

  it("devuelve null cuando el previo es 0 (no se puede calcular descuento)", () => {
    expect(calculateDiscount(50, 0)).toBeNull();
  });
});

describe("slugify", () => {
  it("convierte a minúsculas y reemplaza espacios por guiones", () => {
    expect(slugify("Hola Mundo")).toBe("hola-mundo");
  });

  it("elimina acentos y diacríticos", () => {
    expect(slugify("Cafetería Niño")).toBe("cafeteria-nino");
  });

  it("descarta caracteres no alfanuméricos", () => {
    expect(slugify("¡Hola, mundo!")).toBe("hola-mundo");
  });

  it("limita la longitud a 80 caracteres", () => {
    const input = "a".repeat(200);
    expect(slugify(input)).toHaveLength(80);
  });

  it("colapsa espacios múltiples en un único guion", () => {
    expect(slugify("a   b    c")).toBe("a-b-c");
  });
});

describe("toDatetimeLocal", () => {
  it("recorta un ISO 8601 al formato de <input type=datetime-local>", () => {
    expect(toDatetimeLocal("2026-05-30T14:30:00.000Z")).toBe("2026-05-30T14:30");
  });

  it("devuelve string vacío cuando el valor es null", () => {
    expect(toDatetimeLocal(null)).toBe("");
  });

  it("devuelve string vacío cuando el valor es undefined", () => {
    expect(toDatetimeLocal(undefined)).toBe("");
  });
});

describe("temperatureColor", () => {
  it("devuelve rojo cuando supera el umbral HOT", () => {
    expect(temperatureColor(250)).toBe("text-alert-red");
  });

  it("devuelve cian para temperaturas templadas", () => {
    expect(temperatureColor(150)).toBe("text-cyan-glow");
  });

  it("devuelve muted para temperaturas bajas", () => {
    expect(temperatureColor(50)).toBe("text-muted-foreground");
  });
});

describe("formatRelativeTime", () => {
  // Usamos fake timers para fijar 'ahora' y que los tests sean deterministas.
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-30T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("devuelve 'ahora' si han pasado menos de 60 segundos", () => {
    const date = new Date("2026-05-30T11:59:30Z");
    expect(formatRelativeTime(date)).toBe("ahora");
  });

  it("devuelve minutos si han pasado menos de una hora", () => {
    const date = new Date("2026-05-30T11:30:00Z");
    expect(formatRelativeTime(date)).toBe("hace 30 min");
  });

  it("devuelve horas si han pasado menos de un día", () => {
    const date = new Date("2026-05-30T05:00:00Z");
    expect(formatRelativeTime(date)).toBe("hace 7 h");
  });

  it("devuelve días si han pasado menos de un mes", () => {
    const date = new Date("2026-05-25T12:00:00Z");
    expect(formatRelativeTime(date)).toBe("hace 5 d");
  });

  it("devuelve meses para fechas hace menos de un año", () => {
    const date = new Date("2026-02-01T12:00:00Z");
    expect(formatRelativeTime(date)).toBe("hace 3 meses");
  });

  it("usa singular 'mes' para un único mes", () => {
    const date = new Date("2026-04-28T12:00:00Z");
    expect(formatRelativeTime(date)).toBe("hace 1 mes");
  });

  it("devuelve el placeholder '—' cuando el valor es null", () => {
    expect(formatRelativeTime(null)).toBe("—");
  });

  it("devuelve el placeholder '—' con strings de fecha inválidos", () => {
    expect(formatRelativeTime("no es una fecha")).toBe("—");
  });

  it("acepta también strings ISO 8601", () => {
    expect(formatRelativeTime("2026-05-30T11:30:00Z")).toBe("hace 30 min");
  });
});
