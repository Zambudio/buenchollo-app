import { describe, expect, it } from "vitest";
import { Route } from "@/routes/publicar";

const validate = (input: Record<string, unknown>) =>
  (Route.options.validateSearch as (s: Record<string, unknown>) => { url?: string })(input);

describe("/publicar validateSearch", () => {
  it("acepta una url string", () => {
    expect(validate({ url: "https://www.amazon.es/dp/B0" })).toEqual({
      url: "https://www.amazon.es/dp/B0",
    });
  });

  it("ignora valores no string que TanStack parsea como JSON", () => {
    expect(validate({ url: 123 })).toEqual({ url: undefined });
    expect(validate({ url: true })).toEqual({ url: undefined });
    expect(validate({})).toEqual({ url: undefined });
  });

  it("ignora urls demasiado largas", () => {
    expect(validate({ url: `https://x.es/${"a".repeat(2050)}` })).toEqual({ url: undefined });
  });
});
