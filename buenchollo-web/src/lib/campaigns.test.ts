import { describe, expect, it } from "vitest";
import {
  BLACK_FRIDAY,
  campaignStatus,
  countdownTo,
  formatCampaignDate,
  formatCountdown,
  type Campaign,
} from "./campaigns";

const at = (iso: string) => new Date(iso);

describe("campaignStatus", () => {
  it("antes de anunciarse: próxima y fuera del hero", () => {
    const s = campaignStatus(BLACK_FRIDAY, at("2026-10-15T12:00:00+02:00"));
    expect(s.phase).toBe("upcoming");
    expect(s.promoted).toBe(false);
  });

  it("en la semana previa: próxima, en el hero y con cuenta atrás al inicio", () => {
    const s = campaignStatus(BLACK_FRIDAY, at("2026-11-20T12:00:00+01:00"));
    expect(s.phase).toBe("upcoming");
    expect(s.promoted).toBe(true);
    expect(s.target?.toISOString()).toBe("2026-11-26T23:00:00.000Z");
  });

  it("durante el evento (incluido el Cyber Monday) cuenta atrás hasta el final", () => {
    const s = campaignStatus(BLACK_FRIDAY, at("2026-11-30T22:00:00+01:00"));
    expect(s.phase).toBe("live");
    expect(s.promoted).toBe(true);
    expect(s.target?.toISOString()).toBe("2026-11-30T23:00:00.000Z");
  });

  it("al terminar sale del hero y no hay cuenta atrás", () => {
    const s = campaignStatus(BLACK_FRIDAY, at("2026-12-01T00:00:00+01:00"));
    expect(s.phase).toBe("ended");
    expect(s.promoted).toBe(false);
    expect(s.target).toBeNull();
  });

  it("elige la siguiente edición cuando la anterior ya terminó", () => {
    const campaign: Campaign = {
      ...BLACK_FRIDAY,
      editions: [
        {
          year: 2027,
          promoteFrom: "2027-11-01T00:00:00+01:00",
          start: "2027-11-26T00:00:00+01:00",
          end: "2027-11-30T00:00:00+01:00",
        },
        ...BLACK_FRIDAY.editions,
      ],
    };
    const s = campaignStatus(campaign, at("2026-12-15T12:00:00+01:00"));
    expect(s.edition.year).toBe(2027);
    expect(s.phase).toBe("upcoming");
    expect(s.promoted).toBe(false);
  });
});

describe("countdown", () => {
  it("descompone en días, horas y minutos y nunca es negativa", () => {
    const now = at("2026-11-20T10:00:00Z");
    expect(countdownTo(at("2026-11-26T23:00:00Z"), now)).toEqual({
      days: 6,
      hours: 13,
      minutes: 0,
    });
    expect(countdownTo(at("2026-11-19T00:00:00Z"), now)).toEqual({
      days: 0,
      hours: 0,
      minutes: 0,
    });
  });

  it("formatea omitiendo los días a cero", () => {
    expect(formatCountdown({ days: 6, hours: 7, minutes: 12 })).toBe("6 d 7 h 12 min");
    expect(formatCountdown({ days: 0, hours: 3, minutes: 5 })).toBe("3 h 5 min");
  });

  it("formatea la fecha del evento en hora de Madrid", () => {
    expect(formatCampaignDate("2026-11-27T00:00:00+01:00")).toBe("viernes 27 de noviembre");
  });
});
