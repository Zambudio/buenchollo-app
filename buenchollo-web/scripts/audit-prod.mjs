#!/usr/bin/env node
/**
 * npm audit de las dependencias de producción que falla con avisos `high` o
 * `critical`, salvo los aceptados en audit-allowlist.json (con motivo y fecha
 * de revisión). Una excepción vencida también hace fallar: obliga a revisarla.
 *
 * Uso (CI y local): `npm run audit:prod`
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const BLOCKING = new Set(["high", "critical"]);
const today = new Date().toISOString().slice(0, 10);

// Con `npm run`, npm_execpath apunta al CLI de npm: se ejecuta con el mismo Node
// y sin shell (en Windows `npm` es un .cmd que execFile no puede lanzar).
const npmCli = process.env.npm_execpath;
const [command, prefix] = npmCli ? [process.execPath, [npmCli]] : ["npm", []];

let raw;
try {
  raw = execFileSync(command, [...prefix, "audit", "--omit=dev", "--json"], {
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
} catch (error) {
  // npm audit sale con código 1 cuando encuentra vulnerabilidades; el JSON sigue en stdout.
  raw = error.stdout;
  if (!raw) throw error;
}

const report = JSON.parse(raw);
if (report.error) {
  console.error("npm audit no pudo ejecutarse:", report.error.summary ?? report.error);
  process.exit(2);
}

const allowlist = JSON.parse(readFileSync(new URL("../audit-allowlist.json", import.meta.url)));
const accepted = new Map(allowlist.advisories.map((a) => [a.id, a]));

// Los avisos reales son los objetos de `via`; las cadenas solo indican que el
// paquete depende de otro vulnerable (se cubren con el aviso de origen).
const advisories = new Map();
for (const vuln of Object.values(report.vulnerabilities ?? {})) {
  for (const via of vuln.via) {
    if (typeof via !== "object" || !BLOCKING.has(via.severity)) continue;
    const id = via.url?.split("/").pop() ?? String(via.source);
    advisories.set(id, via);
  }
}

let failed = false;
for (const [id, via] of advisories) {
  const exception = accepted.get(id);
  if (!exception) {
    console.error(`✗ ${via.severity} ${via.name} ${via.range}: ${via.title} (${via.url})`);
    failed = true;
  } else if (exception.review_by < today) {
    console.error(`✗ Excepción vencida el ${exception.review_by}: ${id} (${via.name}). Revísala.`);
    failed = true;
  } else {
    console.log(
      `• Aceptado hasta ${exception.review_by}: ${id} (${via.name}). ${exception.reason}`,
    );
  }
}

for (const id of accepted.keys()) {
  if (!advisories.has(id)) console.log(`ℹ ${id} ya no aparece en el audit: quita la excepción.`);
}

if (failed) process.exit(1);
console.log("✓ Sin vulnerabilidades high/critical no aceptadas en dependencias de producción.");
