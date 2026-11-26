import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { EventEmitter } from 'node:events'
import { test } from 'node:test'

import { proto } from 'baileys'

import {
  buildImageMessage,
  buildStanza,
  isNewsletterJid,
  sendNewsletterImage,
  sendNewsletterText,
  uploadToken,
} from '../src/newsletter.js'

const JID = '120363401234567890@newsletter'
const encode = (m) => proto.Message.encode(proto.Message.fromObject(m)).finish()

// `ack`: 'ok' (WhatsApp acepta), 'error' (rechaza) o 'none' (no contesta).
function fakeSock({ ack = 'ok' } = {}) {
  const sent = []
  const refresh = []
  const ws = new EventEmitter()
  const answer = (id) => {
    if (ack === 'ok') ws.emit(`CB:ack,id:${id}`, { tag: 'ack', attrs: { id, class: 'message' } })
    if (ack === 'error') ws.emit(`CB:ack,id:${id}`, { tag: 'ack', attrs: { id, error: '479' } })
  }
  return {
    sent,
    refresh,
    ws,
    refreshMediaConn: async (force) => {
      refresh.push(force)
      return { auth: 'a+b/c', hosts: [{ hostname: 'mmg.whatsapp.net' }] }
    },
    sendNode: async (node) => {
      sent.push(node)
      setImmediate(() => answer(node.attrs.id))
    },
    sendMessage: async (jid, content, opts) => {
      sent.push({ jid, content, opts })
      setImmediate(() => answer(opts.messageId))
    },
  }
}

const okUpload = async () => ({ status: 200, json: async () => ({ direct_path: '/m1/x' }) })

test('solo acepta JID de canal', () => {
  assert.ok(isNewsletterJid(JID))
  assert.ok(!isNewsletterJid('34600000000@s.whatsapp.net'))
  assert.ok(!isNewsletterJid('123@g.us'))
  assert.ok(!isNewsletterJid(undefined))
})

test('el token de subida es base64 url-safe sin relleno', () => {
  const token = uploadToken(Buffer.from([0xfb, 0xff, 0xfe]))
  assert.equal(token, '-__-')
})

test('sube a la ruta de canales y envía <plaintext mediatype="image">', async () => {
  const sock = fakeSock()
  const image = Buffer.from('jpeg-bytes')
  const calls = []
  const fetchImpl = async (url, init) => {
    calls.push({ url, init })
    return {
      status: 200,
      json: async () => ({
        url: 'https://mmg.whatsapp.net/m1/v/t24/abc',
        direct_path: '/m1/v/t24/abc',
        thumbnail_info: { thumbnail_direct_path: '/m1/thumb', thumbnail_sha256: Buffer.from('th').toString('base64') },
      }),
    }
  }

  const id = await sendNewsletterImage(
    sock,
    { jid: JID, image, caption: '🔥 *Chollo*', width: 1200, height: 800 },
    { encode, newId: () => 'MSG1', fetchImpl },
  )

  assert.equal(id, 'MSG1')
  assert.equal(calls.length, 1)
  const token = uploadToken(createHash('sha256').update(image).digest())
  assert.ok(calls[0].url.startsWith(`https://mmg.whatsapp.net/newsletter/newsletter-image/${token}?`))
  assert.ok(calls[0].url.includes('auth=a%2Bb%2Fc'))
  assert.ok(calls[0].url.includes('server_thumb_gen=1'))
  assert.equal(calls[0].init.headers.Origin, 'https://web.whatsapp.com')

  const [node] = sock.sent
  assert.deepEqual(node.attrs, { to: JID, id: 'MSG1', type: 'media' })
  assert.equal(node.content[0].tag, 'plaintext')
  assert.deepEqual(node.content[0].attrs, { mediatype: 'image' })

  const decoded = proto.Message.decode(node.content[0].content).imageMessage
  assert.equal(decoded.caption, '🔥 *Chollo*')
  assert.equal(decoded.directPath, '/m1/v/t24/abc')
  assert.equal(decoded.mimetype, 'image/jpeg')
  assert.equal(Number(decoded.fileLength), image.length)
  assert.equal(decoded.thumbnailDirectPath, '/m1/thumb')
  assert.equal(Buffer.from(decoded.fileSha256).toString('hex'), createHash('sha256').update(image).digest('hex'))
  assert.equal(decoded.width, 1200)
  assert.ok(!decoded.mediaKey?.length, 'los canales no llevan clave de cifrado')
})

test('si la subida falla pide credenciales nuevas, reintenta y al final lanza sin enviar', async () => {
  const sock = fakeSock()
  const fetchImpl = async () => ({ status: 401, json: async () => ({ error: 'bad auth' }) })
  await assert.rejects(
    sendNewsletterImage(sock, { jid: JID, image: Buffer.from('x'), caption: 'c' }, { encode, newId: () => 'X', fetchImpl }),
    /subida rechazada/,
  )
  assert.deepEqual(sock.refresh, [false, true, true])
  assert.equal(sock.sent.length, 0)
})

test('no envía a un chat normal', async () => {
  await assert.rejects(
    sendNewsletterImage(fakeSock(), { jid: '34600@s.whatsapp.net', image: Buffer.from('x') }, { encode, newId: () => 'X' }),
    /JID de canal/,
  )
})

test('el mensaje de texto de un canal no lleva mediatype', () => {
  const node = buildStanza({ jid: JID, id: 'T', payload: Buffer.from('p') })
  assert.equal(node.attrs.type, 'text')
  assert.deepEqual(node.content[0].attrs, {})
  assert.equal(buildImageMessage({ upload: { direct_path: '/d' }, sha256: Buffer.alloc(32), length: 1 }).imageMessage.caption, undefined)
})

test('si WhatsApp rechaza el mensaje es un error reintentable (502)', async () => {
  const sock = fakeSock({ ack: 'error' })
  await assert.rejects(
    sendNewsletterImage(sock, { jid: JID, image: Buffer.from('x'), caption: 'c' }, { encode, newId: () => 'R', fetchImpl: okUpload }),
    (err) => err.status === 502 && /rechazó/.test(err.message),
  )
  assert.equal(sock.ws.listenerCount('CB:ack,id:R'), 0)
})

test('sin acuse a tiempo es 504 (enviado, resultado desconocido)', async () => {
  const sock = fakeSock({ ack: 'none' })
  await assert.rejects(
    sendNewsletterText(sock, { jid: JID, text: 'hola' }, { newId: () => 'N', ackTimeoutMs: 30 }),
    (err) => err.status === 504,
  )
  assert.equal(sock.ws.listenerCount('CB:ack,id:N'), 0)
})

test('el texto solo usa el id propio para esperar su acuse', async () => {
  const sock = fakeSock()
  assert.equal(await sendNewsletterText(sock, { jid: JID, text: 'hola' }, { newId: () => 'T1' }), 'T1')
  assert.deepEqual(sock.sent[0], { jid: JID, content: { text: 'hola' }, opts: { messageId: 'T1' } })
})

test('la subida no pasa de su presupuesto (llega como 502, no como tiempo agotado)', async () => {
  const sock = fakeSock()
  const slow = () => new Promise((resolve) => setTimeout(() => resolve({ status: 500, json: async () => ({}) }), 40))
  await assert.rejects(
    sendNewsletterImage(sock, { jid: JID, image: Buffer.from('x'), caption: 'c' }, { encode, newId: () => 'S', fetchImpl: slow, budgetMs: 60 }),
    (err) => err.status === 502,
  )
  assert.equal(sock.sent.length, 0)
})
