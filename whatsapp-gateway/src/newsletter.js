// Publicar en un Canal de WhatsApp (JID «…@newsletter»).
//
// Los Canales no van cifrados de extremo a extremo: el mensaje sale en claro
// (<plaintext>) y la imagen se sube sin cifrar a las rutas propias de canales
// (/newsletter/newsletter-image). Baileys 7.0.0-rc14 todavía la sube a la ruta
// de chats (/mms/image) y sin el atributo `mediatype`, y la imagen no llega a
// verse en el canal (issue WhiskeySockets/Baileys#2199, PR #2434 sin integrar).
// Aquí se hace como WhatsApp Web, sin tocar la librería: si Baileys lo integra,
// basta con cambiar `sendNewsletterImage` por `sock.sendMessage`.

import { createHash } from 'node:crypto'

const ORIGIN = 'https://web.whatsapp.com'
const UPLOAD_PATH = '/newsletter/newsletter-image'

export const isNewsletterJid = (jid) => typeof jid === 'string' && /^\d+@newsletter$/.test(jid)

// base64 «url-safe» sin relleno: así espera WhatsApp el hash en la URL de subida.
export const uploadToken = (sha256) =>
  sha256.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')

/** Mensaje de imagen para un canal a partir de la respuesta de la subida. */
export function buildImageMessage({ upload, sha256, length, caption, width, height }) {
  const message = {
    imageMessage: {
      url: upload.url || undefined,
      directPath: upload.direct_path,
      fileSha256: sha256,
      fileLength: length,
      mimetype: 'image/jpeg',
      caption: caption || undefined,
      width: width || undefined,
      height: height || undefined,
    },
  }
  const thumb = upload.thumbnail_info
  if (thumb?.thumbnail_direct_path) {
    message.imageMessage.thumbnailDirectPath = thumb.thumbnail_direct_path
  }
  if (thumb?.thumbnail_sha256) {
    message.imageMessage.thumbnailSha256 = Buffer.from(thumb.thumbnail_sha256, 'base64')
  }
  return message
}

/** Nodo binario que se envía (igual que el de WhatsApp Web para un canal). */
export function buildStanza({ jid, id, payload, mediatype }) {
  return {
    tag: 'message',
    attrs: { to: jid, id, type: mediatype ? 'media' : 'text' },
    content: [{ tag: 'plaintext', attrs: mediatype ? { mediatype } : {}, content: payload }],
  }
}

// Presupuesto total de la subida: por debajo del tiempo que la API espera a
// `/send` (120 s), para que un fallo de subida llegue como error (reintento o
// solo texto) y no como «tiempo agotado» (que la API da por publicado).
export const UPLOAD_BUDGET_MS = 75_000
const UPLOAD_REQUEST_MS = 30_000
// Espera máxima al acuse de WhatsApp tras enviar el mensaje.
export const ACK_TIMEOUT_MS = 20_000

export class SendError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function uploadImage(sock, image, { fetchImpl = fetch, budgetMs = UPLOAD_BUDGET_MS, now = Date.now } = {}) {
  const sha256 = createHash('sha256').update(image).digest()
  const token = uploadToken(sha256)
  const deadline = now() + budgetMs
  let conn = await sock.refreshMediaConn(false)
  let lastError
  for (let round = 0; round < 2; round++) {
    for (const { hostname } of conn.hosts) {
      const remaining = deadline - now()
      if (remaining <= 0) throw new SendError(`subida sin terminar en ${budgetMs / 1000} s`, 502)
      const url =
        `https://${hostname}${UPLOAD_PATH}/${token}` +
        `?auth=${encodeURIComponent(conn.auth)}&token=${token}&server_thumb_gen=1`
      try {
        const res = await fetchImpl(url, {
          method: 'POST',
          body: image,
          headers: { 'Content-Type': 'application/octet-stream', Origin: ORIGIN },
          signal: AbortSignal.timeout(Math.min(UPLOAD_REQUEST_MS, remaining)),
        })
        const data = await res.json().catch(() => undefined)
        if (data?.direct_path) return { upload: data, sha256 }
        lastError = new Error(`subida rechazada (${res.status}): ${JSON.stringify(data)?.slice(0, 200)}`)
      } catch (err) {
        lastError = err
      }
    }
    conn = await sock.refreshMediaConn(true) // credenciales de subida caducadas: se piden otras
  }
  throw new SendError(String(lastError?.message || 'subida fallida'), 502)
}

/**
 * Espera el acuse de WhatsApp del mensaje `id`. Escribir en el socket no
 * significa que WhatsApp lo haya aceptado: rechazado → 502 (la API reintenta);
 * sin acuse a tiempo → 504 (la API lo da por publicado y avisa, sin duplicar).
 * Hay que llamarla ANTES de enviar, para no perder un acuse muy rápido.
 */
export function waitForAck(sock, id, timeoutMs = ACK_TIMEOUT_MS) {
  const event = `CB:ack,id:${id}`
  let timer
  let handler
  const promise = new Promise((resolve, reject) => {
    handler = (node) => {
      const error = node?.attrs?.error
      if (error) reject(new SendError(`WhatsApp rechazó el mensaje (error ${error})`, 502))
      else resolve(node)
    }
    sock.ws.on(event, handler)
    timer = setTimeout(() => reject(new SendError('WhatsApp no confirmó el mensaje a tiempo', 504)), timeoutMs)
  })
  return promise.finally(() => {
    clearTimeout(timer)
    sock.ws.off(event, handler)
  })
}

/**
 * Publica una imagen JPEG con pie de foto en un canal y espera el acuse.
 * Devuelve el id del mensaje. `encode` es `proto.Message.encode` (inyectado
 * para poder probarlo sin Baileys).
 */
export async function sendNewsletterImage(
  sock,
  { jid, image, caption, width, height },
  { encode, newId, fetchImpl, budgetMs, ackTimeoutMs } = {},
) {
  if (!isNewsletterJid(jid)) throw new SendError(`JID de canal no válido: ${jid}`, 400)
  const { upload, sha256 } = await uploadImage(sock, image, { fetchImpl, budgetMs })
  const message = buildImageMessage({ upload, sha256, length: image.length, caption, width, height })
  const id = newId()
  const ack = waitForAck(sock, id, ackTimeoutMs)
  try {
    await sock.sendNode(buildStanza({ jid, id, payload: encode(message), mediatype: 'image' }))
  } catch (err) {
    ack.catch(() => {})
    throw err
  }
  await ack
  return id
}

/** Texto solo, con la misma espera del acuse. */
export async function sendNewsletterText(sock, { jid, text }, { newId, ackTimeoutMs } = {}) {
  if (!isNewsletterJid(jid)) throw new SendError(`JID de canal no válido: ${jid}`, 400)
  const id = newId()
  const ack = waitForAck(sock, id, ackTimeoutMs)
  try {
    await sock.sendMessage(jid, { text }, { messageId: id })
  } catch (err) {
    ack.catch(() => {})
    throw err
  }
  await ack
  return id
}
