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

async function uploadImage(sock, image, { timeoutMs = 60_000, fetchImpl = fetch } = {}) {
  const sha256 = createHash('sha256').update(image).digest()
  const token = uploadToken(sha256)
  let conn = await sock.refreshMediaConn(false)
  let lastError
  for (let round = 0; round < 2; round++) {
    for (const { hostname } of conn.hosts) {
      const url =
        `https://${hostname}${UPLOAD_PATH}/${token}` +
        `?auth=${encodeURIComponent(conn.auth)}&token=${token}&server_thumb_gen=1`
      try {
        const res = await fetchImpl(url, {
          method: 'POST',
          body: image,
          headers: { 'Content-Type': 'application/octet-stream', Origin: ORIGIN },
          signal: AbortSignal.timeout(timeoutMs),
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
  throw lastError || new Error('subida fallida')
}

/**
 * Publica una imagen JPEG con pie de foto en un canal. Devuelve el id del mensaje.
 * `encode` es `proto.Message.encode` (inyectado para poder probarlo sin Baileys).
 */
export async function sendNewsletterImage(sock, { jid, image, caption, width, height }, { encode, newId, fetchImpl } = {}) {
  if (!isNewsletterJid(jid)) throw new Error(`JID de canal no válido: ${jid}`)
  const { upload, sha256 } = await uploadImage(sock, image, { fetchImpl })
  const message = buildImageMessage({ upload, sha256, length: image.length, caption, width, height })
  const id = newId()
  const payload = encode(message)
  await sock.sendNode(buildStanza({ jid, id, payload, mediatype: 'image' }))
  return id
}
