// Pasarela mínima a WhatsApp para publicar en el Canal de BuenCholloTech.
//
// Va vinculada a la cuenta que administra el Canal como un «dispositivo
// vinculado» más (igual que WhatsApp Web) mediante Baileys, sin navegador.
// Solo publica: no lee chats, no responde y no sincroniza el historial.
//
// Solo la usa la API (red interna de Docker, sin puerto publicado) con
// `Authorization: Bearer $GATEWAY_TOKEN`. El ritmo de publicación (como mucho
// uno cada X minutos y N al día) lo decide la API, no este proceso.
//
//   GET  /status                       → estado de la vinculación
//   GET  /channel?invite=CODIGO        → JID, nombre y rol en un Canal
//   POST /send {jid, text, image_base64?, width?, height?} → {ok, id}
//        200 solo con el acuse de WhatsApp; 502 fallo/rechazo (reintentable);
//        503 sin vincular; 504 enviado pero sin acuse (no reintentar)

import { rm, writeFile } from 'node:fs/promises'
import http from 'node:http'
import { join } from 'node:path'
import { timingSafeEqual } from 'node:crypto'

import makeWASocket, {
  Browsers,
  DisconnectReason,
  fetchLatestBaileysVersion,
  generateMessageIDV2,
  proto,
  useMultiFileAuthState,
} from 'baileys'
import pino from 'pino'
import QRCode from 'qrcode'

import { isNewsletterJid, sendNewsletterImage, sendNewsletterText } from './newsletter.js'

const PORT = Number(process.env.PORT || 3000)
// Mismo .env que la API (WHATSAPP_*); GATEWAY_TOKEN/PAIRING_PHONE valen para pruebas.
const TOKEN = process.env.WHATSAPP_GATEWAY_TOKEN || process.env.GATEWAY_TOKEN || ''
const DATA_DIR = process.env.DATA_DIR || '/data'
const AUTH_DIR = join(DATA_DIR, 'auth')
const QR_FILE = join(DATA_DIR, 'qr.png')
const PAIRING_PHONE = (process.env.WHATSAPP_PAIRING_PHONE || process.env.PAIRING_PHONE || '').replace(/\D/g, '')
const MAX_BODY = 8 * 1024 * 1024

const logger = pino({ level: process.env.LOG_LEVEL || 'info' })


const state = {
  connection: 'connecting', // connecting | open | pairing | logged_out
  me: null,
  pairingCode: null,
  lastError: null,
  connectedAt: null,
}
let sock = null
let retries = 0
let sending = Promise.resolve()

const encode = (message) => proto.Message.encode(proto.Message.fromObject(message)).finish()

async function connect() {
  const { state: auth, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
  let version
  try {
    ;({ version } = await fetchLatestBaileysVersion())
  } catch {
    version = undefined // la que trae Baileys
  }
  sock = makeWASocket({
    auth,
    version,
    logger: logger.child({ module: 'baileys' }, { level: 'warn' }),
    browser: Browsers.macOS('Desktop'),
    markOnlineOnConnect: false,
    syncFullHistory: false,
    generateHighQualityLinkPreview: false,
  })
  sock.ev.on('creds.update', saveCreds)

  if (PAIRING_PHONE && !auth.creds.registered) {
    // Vincular con número de teléfono: el código sale en el log y en /status.
    setTimeout(async () => {
      try {
        state.pairingCode = await sock.requestPairingCode(PAIRING_PHONE)
        state.connection = 'pairing'
        logger.warn(`Código para vincular WhatsApp: ${state.pairingCode} (WhatsApp → Dispositivos vinculados → Vincular con número de teléfono)`)
      } catch (err) {
        logger.error({ err: err?.message }, 'No se pudo pedir el código de vinculación')
      }
    }, 3000)
  }

  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr && !PAIRING_PHONE) {
      state.connection = 'pairing'
      await QRCode.toFile(QR_FILE, qr, { width: 480, margin: 2 }).catch(() => {})
      logger.warn(`Escanea el QR para vincular WhatsApp (se renueva cada ~20 s): ${QR_FILE}`)
    }
    if (connection === 'open') {
      retries = 0
      state.connection = 'open'
      state.me = sock.user?.id || null
      state.pairingCode = null
      state.lastError = null
      state.connectedAt = new Date().toISOString()
      await rm(QR_FILE, { force: true })
      logger.info({ me: state.me }, 'WhatsApp conectado')
    }
    if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode
      state.lastError = lastDisconnect?.error?.message || `cerrada (${code})`
      if (code === DisconnectReason.loggedOut) {
        // Se cerró la sesión desde el móvil (o WhatsApp la invalidó): hay que volver a vincular.
        state.connection = 'logged_out'
        state.me = null
        logger.error('Sesión de WhatsApp cerrada desde el móvil: se borra y se pide vincular de nuevo')
        await rm(AUTH_DIR, { recursive: true, force: true })
        setTimeout(connect, 5_000)
        return
      }
      state.connection = 'connecting'
      const wait = Math.min(60_000, 2_000 * 2 ** Math.min(retries++, 5))
      logger.warn({ code, wait }, 'Conexión con WhatsApp cerrada; se reconecta')
      setTimeout(connect, wait)
    }
  })
}

// ── HTTP ─────────────────────────────────────────────────────────────────────

function authorized(req) {
  const header = req.headers.authorization || ''
  const given = Buffer.from(header.startsWith('Bearer ') ? header.slice(7) : '')
  const expected = Buffer.from(TOKEN)
  return given.length === expected.length && timingSafeEqual(given, expected)
}

function reply(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' })
  res.end(JSON.stringify(body))
}

async function readJson(req) {
  let size = 0
  const chunks = []
  for await (const chunk of req) {
    size += chunk.length
    if (size > MAX_BODY) throw Object.assign(new Error('cuerpo demasiado grande'), { status: 413 })
    chunks.push(chunk)
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')
  } catch {
    throw Object.assign(new Error('JSON no válido'), { status: 400 })
  }
}

function requireOpen() {
  if (state.connection !== 'open' || !sock) {
    throw Object.assign(new Error(`WhatsApp no está conectado (${state.connection})`), { status: 503 })
  }
}

async function channelInfo(url) {
  requireOpen()
  const invite = (url.searchParams.get('invite') || '').trim().split('/').pop()
  const jid = (url.searchParams.get('jid') || '').trim()
  let meta = jid ? await sock.newsletterMetadata('jid', jid) : await sock.newsletterMetadata('invite', invite)
  if (!meta) throw Object.assign(new Error('Canal no encontrado'), { status: 404 })
  // Por enlace de invitación WhatsApp no devuelve el rol de quien pregunta: se pide por JID.
  if (!meta.viewer_metadata && meta.id) meta = (await sock.newsletterMetadata('jid', meta.id)) || meta
  return {
    jid: meta.id,
    name: meta.thread_metadata?.name?.text ?? null,
    subscribers: Number(meta.thread_metadata?.subscribers_count ?? 0) || null,
    role: meta.viewer_metadata?.role ?? null,
  }
}

async function send(body) {
  requireOpen()
  const { jid, text, image_base64: imageB64, width, height } = body
  if (!isNewsletterJid(jid)) throw Object.assign(new Error('jid debe ser un Canal (…@newsletter)'), { status: 400 })
  if (!text || typeof text !== 'string') throw Object.assign(new Error('falta text'), { status: 400 })
  // Uno detrás de otro: nunca dos envíos a la vez.
  const job = sending.then(async () => {
    if (imageB64) {
      const image = Buffer.from(imageB64, 'base64')
      return sendNewsletterImage(
        sock,
        { jid, image, caption: text, width, height },
        { encode, newId: () => generateMessageIDV2(sock.user?.id) },
      )
    }
    return sendNewsletterText(sock, { jid, text }, { newId: () => generateMessageIDV2(sock.user?.id) })
  })
  sending = job.catch(() => {})
  return { ok: true, id: await job }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  try {
    if (url.pathname === '/health') return reply(res, 200, { ok: true })
    if (!authorized(req)) return reply(res, 401, { error: 'no autorizado' })
    if (req.method === 'GET' && url.pathname === '/status') {
      return reply(res, 200, {
        connection: state.connection,
        me: state.me,
        pairing_code: state.pairingCode,
        connected_at: state.connectedAt,
        last_error: state.lastError,
      })
    }
    if (req.method === 'GET' && url.pathname === '/channel') return reply(res, 200, await channelInfo(url))
    if (req.method === 'POST' && url.pathname === '/send') return reply(res, 200, await send(await readJson(req)))
    return reply(res, 404, { error: 'no encontrado' })
  } catch (err) {
    const status = err.status || 500
    if (status >= 500) logger.error({ err: err?.message, path: url.pathname }, 'Fallo atendiendo la petición')
    return reply(res, status, { error: String(err?.message || err).slice(0, 300) })
  }
})

function start() {
  server.listen(PORT, () => logger.info(`Pasarela de WhatsApp escuchando en :${PORT}`))
  connect().catch((err) => {
    logger.fatal({ err: err?.message }, 'No se pudo iniciar la conexión con WhatsApp')
    process.exit(1)
  })
}

if (TOKEN.length < 24) {
  // Sin salir con error: con `restart: always` el contenedor entraría en bucle.
  logger.warn('WHATSAPP_GATEWAY_TOKEN no configurado (mínimo 24 caracteres): la pasarela queda en espera, sin conectar')
  setInterval(() => {}, 1 << 30)
} else {
  start()
}
