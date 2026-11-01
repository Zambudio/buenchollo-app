/** Tests unitarios de errorMessage().
 *
 *  Convierte un `unknown` capturado en un catch a string legible. Crítico:
 *  toda la UI lo usa para mostrar errores de la API; un fallo aquí filtra
 *  "[object Object]" o cosas peores al usuario.
 */
import { describe, expect, it } from "vitest";
import { errorMessage, translateAuthError } from "@/lib/errors";

describe("errorMessage", () => {
  it("extrae el mensaje de una instancia de Error", () => {
    expect(errorMessage(new Error("conexión perdida"))).toBe("conexión perdida");
  });

  it("devuelve un string tal cual cuando lo lanzado es un string", () => {
    expect(errorMessage("fallo manual")).toBe("fallo manual");
  });

  it("usa el fallback por defecto con un valor desconocido", () => {
    expect(errorMessage({ raw: "objeto random" })).toBe("Error inesperado");
  });

  it("usa el fallback personalizado cuando lo damos", () => {
    expect(errorMessage(null, "no se pudo cargar")).toBe("no se pudo cargar");
  });

  it("trata undefined como desconocido y aplica el fallback", () => {
    expect(errorMessage(undefined, "vacío")).toBe("vacío");
  });

  it("subclases de Error también se procesan", () => {
    class CustomError extends Error {}
    expect(errorMessage(new CustomError("custom"))).toBe("custom");
  });
});

describe("translateAuthError", () => {
  it("devuelve el fallback por defecto si no se pasa mensaje", () => {
    expect(translateAuthError()).toBe("Ha ocurrido un error al procesar la solicitud");
    expect(translateAuthError(null)).toBe("Ha ocurrido un error al procesar la solicitud");
    expect(translateAuthError("")).toBe("Ha ocurrido un error al procesar la solicitud");
  });

  it("devuelve el fallback personalizado si no se pasa mensaje", () => {
    expect(translateAuthError(undefined, "Fallback custom")).toBe("Fallback custom");
  });

  it("extrae los segundos del rate limit de Supabase", () => {
    const raw = "For security purposes, you can only request this after 28 seconds.";
    expect(translateAuthError(raw)).toBe(
      "Por seguridad, debes esperar 28 segundos antes de volver a solicitar otro correo.",
    );
  });

  it("traduce error genérico de rate limit", () => {
    expect(translateAuthError("Rate limit exceeded")).toBe(
      "Has realizado demasiados intentos. Por favor, espera unos instantes.",
    );
    expect(translateAuthError("Too many requests")).toBe(
      "Has realizado demasiados intentos. Por favor, espera unos instantes.",
    );
  });

  it("traduce usuario ya registrado", () => {
    expect(translateAuthError("User already registered")).toBe(
      "Ya existe una cuenta con este correo electrónico. Inicia sesión o recupera tu contraseña.",
    );
    expect(translateAuthError("Account already exists with this email")).toBe(
      "Ya existe una cuenta con este correo electrónico. Inicia sesión o recupera tu contraseña.",
    );
  });

  it("traduce email no confirmado", () => {
    expect(translateAuthError("Email not confirmed")).toBe(
      "Debes confirmar tu correo electrónico antes de entrar. Revisa tu bandeja de entrada.",
    );
  });

  it("traduce credenciales incorrectas", () => {
    expect(translateAuthError("Invalid login credentials")).toBe(
      "Correo o contraseña incorrectos.",
    );
    expect(translateAuthError("invalid credentials")).toBe("Correo o contraseña incorrectos.");
  });

  it("traduce longitud mínima de contraseña", () => {
    expect(translateAuthError("Password should be at least 6 characters")).toBe(
      "La contraseña debe tener al menos 6 caracteres.",
    );
    expect(translateAuthError("Password is too short")).toBe(
      "La contraseña debe tener al menos 6 caracteres.",
    );
  });

  it("traduce enlace o token OTP caducado o inválido", () => {
    expect(translateAuthError("Email link is invalid or has expired")).toBe(
      "El enlace de confirmación ha caducado o ya ha sido utilizado.",
    );
    expect(translateAuthError("otp_expired")).toBe(
      "El enlace de confirmación ha caducado o ya ha sido utilizado.",
    );
  });

  it("traduce token expirado o inválido genérico", () => {
    expect(translateAuthError("Token has expired")).toBe(
      "El enlace de seguridad ha caducado o no es válido.",
    );
    expect(translateAuthError("Token is invalid")).toBe(
      "El enlace de seguridad ha caducado o no es válido.",
    );
  });

  it("mantiene el mensaje original si no coincide con ningún patrón conocido", () => {
    expect(translateAuthError("Un error completamente desconocido de la red")).toBe(
      "Un error completamente desconocido de la red",
    );
  });
});
