/**
 * Ponte Local WhatsApp (Multi-Device via QR Code) para o Sistema Gráfica.
 * - Recebimento e envio em tempo real (baixa latência)
 * - Sincronização de conversas anteriores (messaging-history.set)
 * - Download de imagens/comprovantes recebidos para análise da IA
 * - Rejeição e resposta automática APENAS em ligações ("NÃO RECEBEMOS LIGAÇÃO, APENAS MENSAGEM AGRADEÇO!")
 */
const http = require("http");
const path = require("path");
const fs = require("fs");
const QRCode = require("qrcode");
const pino = require("pino");
const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    downloadMediaMessage,
} = require("@whiskeysockets/baileys");

const PORT = Number(process.env.BRIDGE_PORT || 3001);
let fastapiWebhookUrl = process.env.FASTAPI_WEBHOOK_URL || "http://127.0.0.1:8000/api/whatsapp/webhook";
let bridgeToken = process.env.WHATSAPP_BRIDGE_TOKEN || "";
const AUTH_DIR = path.join(__dirname, "auth_info");

const MSG_REJEICAO_LIGACAO = "NÃO RECEBEMOS LIGAÇÃO, APENAS MENSAGEM AGRADEÇO!";
const MAX_MEDIA_BYTES = 25_000_000; // 25MB para imagens, áudios e documentos/PDFs com folga

let sock = null;
let estado = {
    conectado: false,
    status: "iniciando",
    numero: "",
    nome: "",
    qr_data_url: "",
    ultimo_erro: "",
};
let reconectandoTimer = null;

// Mapas em memória para traduzir LID (@lid) <-> Telefone (@s.whatsapp.net), nomes de contatos e cache de mensagens
const mapaLidParaJid = new Map();
const mapaJidParaNome = new Map();
const mapaMensagensPorId = new Map();
const chamadasProcessadas = new Set();

function registrarMapeamentoContato(c) {
    if (!c) return;
    const id = String(c.id || "");
    const lid = String(c.lid || "");
    const nome = String(c.notify || c.name || c.verifiedName || "").trim();

    if (id.endsWith("@s.whatsapp.net") && lid.endsWith("@lid")) {
        mapaLidParaJid.set(lid, id);
    } else if (lid.endsWith("@s.whatsapp.net") && id.endsWith("@lid")) {
        mapaLidParaJid.set(id, lid);
    }
    if (nome) {
        if (id) mapaJidParaNome.set(id, nome);
        if (lid) mapaJidParaNome.set(lid, nome);
    }
}

function resolverRemoteJid(key, msg) {
    if (!key) return "";
    const candidatos = [
        key.remoteJid,
        key.remoteJidAlt,
        key.participant,
        key.participantAlt,
        msg && msg.participant,
    ]
        .map((v) => String(v || "").trim())
        .filter(Boolean);

    for (const cand of candidatos) {
        if (cand.endsWith("@s.whatsapp.net")) {
            for (const outro of candidatos) {
                if (outro.endsWith("@lid")) mapaLidParaJid.set(outro, cand);
            }
            return cand;
        }
    }

    for (const cand of candidatos) {
        if (cand.endsWith("@lid") && mapaLidParaJid.has(cand)) {
            return mapaLidParaJid.get(cand);
        }
    }

    return candidatos[0] || "";
}

function desempacotarMensagem(m) {
    if (!m) return null;
    if (m.ephemeralMessage && m.ephemeralMessage.message) {
        return desempacotarMensagem(m.ephemeralMessage.message);
    }
    if (m.viewOnceMessage && m.viewOnceMessage.message) {
        return desempacotarMensagem(m.viewOnceMessage.message);
    }
    if (m.viewOnceMessageV2 && m.viewOnceMessageV2.message) {
        return desempacotarMensagem(m.viewOnceMessageV2.message);
    }
    if (m.documentWithCaptionMessage && m.documentWithCaptionMessage.message) {
        return desempacotarMensagem(m.documentWithCaptionMessage.message);
    }
    if (m.editedMessage && m.editedMessage.message && m.editedMessage.message.protocolMessage) {
        const pm = m.editedMessage.message.protocolMessage;
        if (pm.editedMessage) return desempacotarMensagem(pm.editedMessage);
    }
    return m;
}

function extrairTimestampSegundos(ts) {
    if (!ts) return null;
    if (typeof ts === "object") {
        if ("low" in ts && typeof ts.low === "number") return ts.low;
        if ("toNumber" in ts && typeof ts.toNumber === "function") return ts.toNumber();
    }
    const n = Number(ts);
    if (isNaN(n) || n <= 0) return null;
    return n > 10_000_000_000 ? Math.floor(n / 1000) : n;
}

function extrairDetalhesMensagem(msg) {
    const m = desempacotarMensagem(msg && msg.message);
    if (!m) return { texto: "", temMidia: false, midiaTipo: "", mimeType: "", nomeArquivo: "" };

    if (m.imageMessage) {
        const leg = String(m.imageMessage.caption || "").trim();
        return {
            texto: leg ? `[Imagem] ${leg}` : "[Imagem recebida]",
            temMidia: true,
            midiaTipo: "imagem",
            mimeType: m.imageMessage.mimetype || "image/jpeg",
            nomeArquivo: "imagem.jpg",
        };
    }

    if (m.documentMessage) {
        const leg = String(m.documentMessage.caption || "").trim();
        const arq = String(m.documentMessage.fileName || "documento.pdf").trim();
        return {
            texto: leg ? `[Arquivo: ${arq}] ${leg}` : `[Arquivo recebido: ${arq}]`,
            temMidia: true,
            midiaTipo: "documento",
            mimeType: m.documentMessage.mimetype || "application/pdf",
            nomeArquivo: arq,
        };
    }

    if (m.audioMessage) {
        const ptt = Boolean(m.audioMessage.ptt);
        const segs = extrairTimestampSegundos(m.audioMessage.seconds);
        const durStr = segs ? ` (${segs}s)` : "";
        const mime = m.audioMessage.mimetype || "audio/ogg; codecs=opus";
        let ext = "ogg";
        if (mime.includes("mp4") || mime.includes("m4a")) ext = "m4a";
        else if (mime.includes("mpeg") || mime.includes("mp3")) ext = "mp3";
        else if (mime.includes("wav")) ext = "wav";

        return {
            texto: ptt ? `[Mensagem de voz${durStr}]` : `[Audio${durStr}]`,
            temMidia: true,
            midiaTipo: "audio",
            mimeType: mime,
            nomeArquivo: `audio_${Date.now()}.${ext}`,
        };
    }

    const texto = (
        m.conversation ||
        (m.extendedTextMessage && m.extendedTextMessage.text) ||
        (m.videoMessage && (m.videoMessage.caption || "[Video recebido]")) ||
        (m.stickerMessage && "[Figurinha]") ||
        (m.buttonsResponseMessage && m.buttonsResponseMessage.selectedDisplayText) ||
        (m.listResponseMessage && m.listResponseMessage.title) ||
        (m.templateButtonReplyMessage && m.templateButtonReplyMessage.selectedDisplayText) ||
        ""
    );
    return {
        texto: String(texto || "").trim(),
        temMidia: false,
        midiaTipo: "",
        mimeType: "",
        nomeArquivo: "",
    };
}

async function baixarMidiaBase64SeNecessario(msg, detalhes) {
    if (!detalhes.temMidia || !sock) return "";
    try {
        const buffer = await downloadMediaMessage(
            msg,
            "buffer",
            {},
            {
                logger: pino({ level: "silent" }),
                reuploadRequest: (m) => (sock ? sock.updateMediaMessage(m) : Promise.reject(new Error("Sem socket"))),
            }
        );
        if (buffer && buffer.length > 0 && buffer.length <= MAX_MEDIA_BYTES) {
            return buffer.toString("base64");
        }
    } catch (err) {
        console.error(`[Bridge] Falha ao baixar mídia (${detalhes.midiaTipo} / ${detalhes.nomeArquivo}):`, err.message);
    }
    return "";
}

async function encaminharParaFastAPI(evento) {
    const urlsCandidatas = [
        fastapiWebhookUrl,
        "http://127.0.0.1:8000/api/whatsapp/webhook",
        "http://localhost:8000/api/whatsapp/webhook",
    ];
    const urlsUnicas = Array.from(new Set(urlsCandidatas.filter(Boolean)));
    let ultimoErroTxt = "";

    for (const url of urlsUnicas) {
        try {
            const resp = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Webhook-Token": bridgeToken,
                },
                body: JSON.stringify({ data: evento }),
            });
            if (!resp.ok) {
                const txt = await resp.text().catch(() => "");
                ultimoErroTxt = `Webhook HTTP ${resp.status}: ${txt.slice(0, 120)}`;
                estado.ultimo_erro = ultimoErroTxt;
                return;
            }
            fastapiWebhookUrl = url;
            estado.ultimo_erro = "";
            return;
        } catch (err) {
            ultimoErroTxt = `Falha ao entregar ao FastAPI (${url}): ${err.message}`;
        }
    }
    estado.ultimo_erro = ultimoErroTxt;
}

function ignorarJid(jid) {
    return (
        !jid ||
        jid.includes("@g.us") ||
        jid.includes("status@broadcast") ||
        jid.includes("@newsletter") ||
        jid.includes("@broadcast")
    );
}

async function processarListaMensagens(messages, baixarMidia = true) {
    if (!Array.isArray(messages) || messages.length === 0) return;
    const lote = [];
    const TAM_LOTE = 50;

    for (const msg of messages) {
        if (!msg || !msg.key) continue;
        const remoteJidBruto = String(msg.key.remoteJid || "");
        if (ignorarJid(remoteJidBruto)) continue;

        const remoteJid = resolverRemoteJid(msg.key, msg);
        if (ignorarJid(remoteJid)) continue;

        const detalhes = extrairDetalhesMensagem(msg);
        if (!detalhes.texto) continue;

        if (msg.key.id) {
            mapaMensagensPorId.set(msg.key.id, msg);
            if (mapaMensagensPorId.size > 2000) {
                const primeiroId = mapaMensagensPorId.keys().next().value;
                mapaMensagensPorId.delete(primeiroId);
            }
        }

        const fromMe = Boolean(msg.key.fromMe);
        const nomeContato =
            (!fromMe && msg.pushName) ||
            mapaJidParaNome.get(remoteJid) ||
            mapaJidParaNome.get(remoteJidBruto) ||
            "";

        let midiaBase64 = "";
        if (baixarMidia && detalhes.temMidia) {
            midiaBase64 = await baixarMidiaBase64SeNecessario(msg, detalhes);
        }

        const ts = extrairTimestampSegundos(msg.messageTimestamp);

        const itemEvento = {
            evento_tipo: "mensagem",
            key: {
                remoteJid: remoteJid,
                fromMe: fromMe,
                id: msg.key.id || "",
            },
            pushName: nomeContato,
            message: { conversation: detalhes.texto },
            messageTimestamp: ts,
            midia_tipo: detalhes.midiaTipo,
            midia_mime: detalhes.mimeType,
            midia_nome: detalhes.nomeArquivo,
            midia_base64: midiaBase64,
        };

        // Se for mensagem única com imagem para baixar, envia direto para análise de comprovante
        if (baixarMidia && midiaBase64) {
            await encaminharParaFastAPI(itemEvento);
        } else {
            lote.push(itemEvento);
            if (lote.length >= TAM_LOTE) {
                await encaminharParaFastAPI({
                    evento_tipo: "mensagens_lote",
                    items: [...lote],
                });
                lote.length = 0;
            }
        }
    }

    if (lote.length > 0) {
        if (lote.length === 1 && baixarMidia) {
            await encaminharParaFastAPI(lote[0]);
        } else {
            await encaminharParaFastAPI({
                evento_tipo: "mensagens_lote",
                items: lote,
            });
        }
    }
}

async function iniciarConexaoWhatsApp() {
    if (reconectandoTimer) {
        clearTimeout(reconectandoTimer);
        reconectandoTimer = null;
    }

    try {
        fs.mkdirSync(AUTH_DIR, { recursive: true });
        const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
        let version = [2, 3000, 1015901307];
        try {
            const latest = await fetchLatestBaileysVersion();
            if (latest && latest.version) version = latest.version;
        } catch (_) {}

        estado.status = "conectando";
        sock = makeWASocket({
            version,
            auth: state,
            printQRInTerminal: false,
            logger: pino({ level: "silent" }),
            browser: ["Sistema Grafica Bee", "Chrome", "120.0.0"],
            syncFullHistory: true,
            markOnlineOnConnect: false,
        });

        sock.ev.on("creds.update", saveCreds);

        sock.ev.on("contacts.upsert", (contatos) => {
            if (Array.isArray(contatos)) contatos.forEach(registrarMapeamentoContato);
        });

        sock.ev.on("contacts.update", (contatos) => {
            if (Array.isArray(contatos)) contatos.forEach(registrarMapeamentoContato);
        });

        // SINCRONIZAÇÃO DE CONVERSAS ANTERIORES DO APARELHO
        sock.ev.on("messaging-history.set", async ({ chats, contacts, messages }) => {
            try {
                if (Array.isArray(contacts)) contacts.forEach(registrarMapeamentoContato);

                // 1. Registra todas as conversas existentes no celular
                if (Array.isArray(chats) && chats.length > 0) {
                    const conversasParaRegistrar = [];
                    for (const c of chats) {
                        if (!c || !c.id || ignorarJid(c.id)) continue;
                        const jidResolvido = resolverRemoteJid({ remoteJid: c.id }) || c.id;
                        if (ignorarJid(jidResolvido)) continue;
                        const nome = c.name || c.notify || mapaJidParaNome.get(jidResolvido) || "";
                        const ts = extrairTimestampSegundos(c.conversationTimestamp || c.lastMessageRecvTimestamp);
                        conversasParaRegistrar.push({
                            jid: jidResolvido,
                            nome: nome,
                            timestamp: ts,
                            nao_lidas: c.unreadCount || 0,
                        });
                    }
                    if (conversasParaRegistrar.length > 0) {
                        await encaminharParaFastAPI({
                            evento_tipo: "conversas_lote",
                            chats: conversasParaRegistrar,
                        });
                    }
                }

                // 2. Processa TODAS as mensagens históricas enviadas pelo WhatsApp (sem cortar nenhuma!)
                if (Array.isArray(messages) && messages.length > 0) {
                    console.log(`[Bridge] Recebidas ${messages.length} mensagens de histórico do WhatsApp. Sincronizando...`);
                    await processarListaMensagens(messages, true);
                }
            } catch (err) {
                console.error("[Bridge] Erro ao sincronizar histórico:", err.message);
            }
        });

        sock.ev.on("connection.update", async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                try {
                    estado.qr_data_url = await QRCode.toDataURL(qr, { margin: 2, width: 280 });
                    estado.status = "aguardando_qr";
                    estado.conectado = false;
                } catch (e) {
                    estado.ultimo_erro = "Erro ao gerar imagem do QR Code.";
                }
            }

            if (connection === "open") {
                estado.conectado = true;
                estado.status = "conectado";
                estado.qr_data_url = "";
                estado.ultimo_erro = "";
                const jid = (sock.user && sock.user.id) || "";
                estado.numero = jid.split(":")[0].split("@")[0];
                estado.nome = (sock.user && sock.user.name) || "WhatsApp Conectado";
                console.log("[Bridge] WhatsApp conectado:", estado.numero);
            }

            if (connection === "close") {
                estado.conectado = false;
                estado.qr_data_url = "";
                const codigo =
                    lastDisconnect &&
                    lastDisconnect.error &&
                    lastDisconnect.error.output &&
                    lastDisconnect.error.output.statusCode;

                if (codigo === DisconnectReason.loggedOut) {
                    try {
                        fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                    } catch (_) {}
                    estado.status = "desconectado";
                    estado.numero = "";
                    reconectandoTimer = setTimeout(iniciarConexaoWhatsApp, 1500);
                } else {
                    estado.status = "reconectando";
                    reconectandoTimer = setTimeout(iniciarConexaoWhatsApp, 3000);
                }
            }
        });

        // 1. RECEBIMENTO DE MENSAGENS EM TEMPO REAL (CLIENTES CADASTRADOS E NÃO CADASTRADOS)
        sock.ev.on("messages.upsert", async ({ messages, type }) => {
            if ((type !== "notify" && type !== "append") || !Array.isArray(messages)) return;
            await processarListaMensagens(messages, true);
        });

        // 2. REJEIÇÃO E RESPOSTA AUTOMÁTICA EXCLUSIVA DE LIGAÇÕES (VOZ / VÍDEO)
        sock.ev.on("call", async (chamadas) => {
            if (!Array.isArray(chamadas)) return;
            for (const call of chamadas) {
                if (!call || call.status !== "offer") continue;
                const callKey = `${call.id}:${call.from}`;
                if (chamadasProcessadas.has(callKey)) continue;
                chamadasProcessadas.add(callKey);

                const callerJidBruto = String(call.from || "");
                if (!callerJidBruto || callerJidBruto.includes("@g.us")) continue;

                try {
                    if (typeof sock.rejectCall === "function") {
                        await sock.rejectCall(call.id, call.from);
                    }
                } catch (_) {}

                let jidResposta = mapaLidParaJid.get(callerJidBruto) || callerJidBruto;
                try {
                    await sock.sendMessage(jidResposta, { text: MSG_REJEICAO_LIGACAO });
                } catch (err) {
                    console.error("[Bridge] Erro ao enviar aviso de ligação:", err.message);
                }

                await encaminharParaFastAPI({
                    evento_tipo: "ligacao",
                    key: {
                        remoteJid: jidResposta,
                        fromMe: false,
                        id: `CALL_${call.id || Date.now()}`,
                    },
                    pushName: mapaJidParaNome.get(jidResposta) || mapaJidParaNome.get(callerJidBruto) || "",
                    message: {
                        conversation: "[Cliente tentou ligar para o WhatsApp]",
                    },
                    resposta_automatica_enviada: MSG_REJEICAO_LIGACAO,
                });
            }
        });
    } catch (err) {
        estado.conectado = false;
        estado.status = "erro";
        estado.ultimo_erro = err.message || "Falha ao iniciar socket do WhatsApp.";
        reconectandoTimer = setTimeout(iniciarConexaoWhatsApp, 5000);
    }
}

function lerJsonBody(req) {
    return new Promise((resolve, reject) => {
        let corpo = "";
        req.on("data", (chunk) => {
            corpo += chunk;
            if (corpo.length > 500_000) reject(new Error("Payload muito grande"));
        });
        req.on("end", () => {
            try {
                resolve(JSON.parse(corpo || "{}"));
            } catch (e) {
                reject(new Error("JSON inválido"));
            }
        });
        req.on("error", reject);
    });
}

function responderJson(res, status, dados) {
    const payload = JSON.stringify(dados);
    res.writeHead(status, {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": Buffer.byteLength(payload),
    });
    res.end(payload);
}

const server = http.createServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/status") {
        return responderJson(res, 200, {
            ...estado,
            webhook_url: fastapiWebhookUrl,
        });
    }

    if (req.method === "POST" && req.url === "/config") {
        try {
            const body = await lerJsonBody(req);
            if (body.webhook_url) fastapiWebhookUrl = String(body.webhook_url);
            if (body.bridge_token) {
                bridgeToken = String(body.bridge_token);
                estado.ultimo_erro = "";
            }
            return responderJson(res, 200, { sucesso: true, webhook_url: fastapiWebhookUrl });
        } catch (err) {
            return responderJson(res, 400, { erro: err.message });
        }
    }

    if (req.method === "POST" && bridgeToken) {
        const tokenReq = req.headers["x-bridge-token"] || "";
        if (tokenReq !== bridgeToken) {
            return responderJson(res, 401, { erro: "Não autorizado." });
        }
    }

    async function resolverJidDestino(bruto, numeroLimpo) {
        let jidDestino = bruto.includes("@") ? bruto : `${numeroLimpo}@s.whatsapp.net`;
        if (numeroLimpo.length > 13 && !bruto.includes("@")) {
            return { jid: `${numeroLimpo}@lid`, erro: null };
        }
        if (!jidDestino.endsWith("@lid")) {
            try {
                const [resultado] = await sock.onWhatsApp(numeroLimpo);
                if (resultado) {
                    if (resultado.exists === false) {
                        return { jid: null, erro: "O número informado não está cadastrado no WhatsApp." };
                    }
                    if (resultado.exists && resultado.jid) {
                        jidDestino = resultado.jid;
                        if (resultado.lid) {
                            mapaLidParaJid.set(String(resultado.lid), jidDestino);
                        }
                    }
                }
            } catch (_) {}
        }
        return { jid: jidDestino, erro: null };
    }

    if (req.method === "POST" && req.url === "/send") {
        if (!sock || !estado.conectado) {
            return responderJson(res, 503, { enviado: false, erro: "WhatsApp ainda não está conectado via QR Code." });
        }
        try {
            const body = await lerJsonBody(req);
            const bruto = String(body.number || "").trim();
            const numeroLimpo = bruto.replace(/\D+/g, "");
            const texto = String(body.text || "").trim();
            if (!numeroLimpo || !texto) {
                return responderJson(res, 400, { enviado: false, erro: "Número e texto são obrigatórios." });
            }

            const { jid: jidDestino, erro: erroJid } = await resolverJidDestino(bruto, numeroLimpo);
            if (erroJid) {
                return responderJson(res, 400, { enviado: false, erro: erroJid });
            }

            const enviado = await sock.sendMessage(jidDestino, { text: texto });
            const idExterno = (enviado && enviado.key && enviado.key.id) || "";
            return responderJson(res, 200, { enviado: true, id_externo: idExterno });
        } catch (err) {
            return responderJson(res, 500, { enviado: false, erro: err.message || "Falha ao enviar mensagem." });
        }
    }

    if (req.method === "POST" && req.url === "/send-image") {
        if (!sock || !estado.conectado) {
            return responderJson(res, 503, { enviado: false, erro: "WhatsApp ainda não está conectado via QR Code." });
        }
        try {
            const body = await lerJsonBody(req);
            const bruto = String(body.number || "").trim();
            const numeroLimpo = bruto.replace(/\D+/g, "");
            const caption = String(body.caption || "").trim();
            const b64 = String(body.image_base64 || "").trim();
            const mimeType = String(body.mime_type || "image/jpeg").trim();

            if (!numeroLimpo || !b64) {
                return responderJson(res, 400, { enviado: false, erro: "Número e imagem são obrigatórios." });
            }

            const { jid: jidDestino, erro: erroJid } = await resolverJidDestino(bruto, numeroLimpo);
            if (erroJid) {
                return responderJson(res, 400, { enviado: false, erro: erroJid });
            }

            const imgBuffer = Buffer.from(b64, "base64");
            const enviado = await sock.sendMessage(jidDestino, {
                image: imgBuffer,
                caption: caption || undefined,
                mimetype: mimeType,
            });
            const idExterno = (enviado && enviado.key && enviado.key.id) || "";
            return responderJson(res, 200, { enviado: true, id_externo: idExterno });
        } catch (err) {
            return responderJson(res, 500, { enviado: false, erro: err.message || "Falha ao enviar imagem." });
        }
    }

    if (req.method === "POST" && req.url === "/send-file") {
        if (!sock || !estado.conectado) {
            return responderJson(res, 503, { enviado: false, erro: "WhatsApp ainda não está conectado via QR Code." });
        }
        try {
            const body = await lerJsonBody(req);
            const bruto = String(body.number || "").trim();
            const numeroLimpo = bruto.replace(/\D+/g, "");
            const caption = String(body.caption || "").trim();
            const b64 = String(body.file_base64 || body.image_base64 || "").trim();
            const fileName = String(body.file_name || "documento.pdf").trim();
            const mimeType = String(body.mime_type || "application/pdf").trim();
            const mediaType = String(body.media_type || (mimeType.startsWith("image/") ? "imagem" : mimeType.startsWith("audio/") ? "audio" : "documento")).toLowerCase();

            if (!numeroLimpo || !b64) {
                return responderJson(res, 400, { enviado: false, erro: "Número e arquivo são obrigatórios." });
            }

            const { jid: jidDestino, erro: erroJid } = await resolverJidDestino(bruto, numeroLimpo);
            if (erroJid) {
                return responderJson(res, 400, { enviado: false, erro: erroJid });
            }

            const buf = Buffer.from(b64, "base64");
            let msgPayload = {};
            if (mediaType === "imagem" || mimeType.startsWith("image/")) {
                msgPayload = { image: buf, caption: caption || undefined, mimetype: mimeType };
            } else if (mediaType === "audio" || mimeType.startsWith("audio/")) {
                msgPayload = { audio: buf, mimetype: mimeType, ptt: false };
            } else {
                msgPayload = { document: buf, mimetype: mimeType, fileName: fileName, caption: caption || undefined };
            }

            const enviado = await sock.sendMessage(jidDestino, msgPayload);
            const idExterno = (enviado && enviado.key && enviado.key.id) || "";
            return responderJson(res, 200, { enviado: true, id_externo: idExterno });
        } catch (err) {
            return responderJson(res, 500, { enviado: false, erro: err.message || "Falha ao enviar arquivo." });
        }
    }

    if (req.method === "POST" && req.url === "/fetch-history") {
        if (!sock || !estado.conectado) {
            return responderJson(res, 503, { sucesso: false, erro: "WhatsApp ainda não está conectado via QR Code." });
        }
        try {
            const body = await lerJsonBody(req);
            const bruto = String(body.jid || body.number || "").trim();
            const count = Math.min(Math.max(Number(body.count || 50), 10), 100);
            const oldestId = body.oldest_id ? String(body.oldest_id).trim() : "";
            const oldestFromMe = Boolean(body.oldest_from_me);
            const oldestTimestamp = extrairTimestampSegundos(body.oldest_timestamp);

            let jidDestino = bruto.includes("@") ? bruto : `${bruto.replace(/\D+/g, "")}@s.whatsapp.net`;
            if (mapaLidParaJid.has(jidDestino)) {
                jidDestino = mapaLidParaJid.get(jidDestino);
            }

            if (typeof sock.fetchMessageHistory === "function" && oldestId && oldestTimestamp) {
                const tsMs = oldestTimestamp < 10_000_000_000 ? oldestTimestamp * 1000 : oldestTimestamp;
                await sock.fetchMessageHistory(count, {
                    remoteJid: jidDestino,
                    id: oldestId,
                    fromMe: oldestFromMe,
                }, tsMs);
                return responderJson(res, 200, {
                    sucesso: true,
                    solicitado: true,
                    count,
                    jid: jidDestino,
                    mensagem: "Histórico solicitado ao WhatsApp. Novas mensagens aparecerão em instantes.",
                });
            }

            return responderJson(res, 400, {
                sucesso: false,
                erro: "Mensagem anterior e timestamp válidos são necessários para buscar histórico sob demanda.",
            });
        } catch (err) {
            return responderJson(res, 500, { sucesso: false, erro: err.message || "Falha ao solicitar histórico." });
        }
    }

    if (req.method === "POST" && req.url === "/download-media") {
        if (!sock || !estado.conectado) {
            return responderJson(res, 503, { sucesso: false, erro: "WhatsApp ainda não está conectado via QR Code." });
        }
        try {
            const body = await lerJsonBody(req);
            const idMsg = String(body.id || body.id_externo || "").trim();
            if (!idMsg || !mapaMensagensPorId.has(idMsg)) {
                return responderJson(res, 404, {
                    sucesso: false,
                    erro: "Mensagem não encontrada no cache de memória da ponte.",
                });
            }
            const msg = mapaMensagensPorId.get(idMsg);
            const detalhes = extrairDetalhesMensagem(msg);
            if (!detalhes.temMidia) {
                return responderJson(res, 400, { sucesso: false, erro: "Esta mensagem não contém mídia." });
            }
            const b64 = await baixarMidiaBase64SeNecessario(msg, detalhes);
            if (!b64) {
                return responderJson(res, 500, {
                    sucesso: false,
                    erro: "Não foi possível descriptografar a mídia no momento. Ela pode ter expirado nos servidores do WhatsApp.",
                });
            }
            return responderJson(res, 200, {
                sucesso: true,
                midia_base64: b64,
                midia_tipo: detalhes.midiaTipo,
                nome_arquivo: detalhes.nomeArquivo,
                mime_type: detalhes.mimeType,
            });
        } catch (err) {
            return responderJson(res, 500, { sucesso: false, erro: err.message });
        }
    }

    if (req.method === "POST" && req.url === "/logout") {
        try {
            if (sock) {
                await sock.logout().catch(() => {});
            }
        } catch (_) {}
        try {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        } catch (_) {}
        estado.conectado = false;
        estado.status = "desconectado";
        estado.numero = "";
        estado.qr_data_url = "";
        setTimeout(iniciarConexaoWhatsApp, 800);
        return responderJson(res, 200, { sucesso: true });
    }

    return responderJson(res, 404, { erro: "Rota não encontrada." });
});

server.listen(PORT, "127.0.0.1", () => {
    console.log(`[Bridge] Servidor WhatsApp local ativo em http://127.0.0.1:${PORT}`);
    iniciarConexaoWhatsApp();
});
