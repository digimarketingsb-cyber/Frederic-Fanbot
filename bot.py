import discord
import os
import anthropic
import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

LIEN_PAIEMENT = "https://app.dropp.fans/fr/external/share/link/link_10b3p9E8ICCwUufk6Zvs/"
SESSIONS_FILE = "sessions.json"

def load_sessions():
    try:
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_sessions(sessions):
    try:
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions, f)
    except:
        pass

sessions = load_sessions()

SYSTEM_PROMPT_BASE = """Tu joues Frederic, 48 ans, fan sur une plateforme en ligne. Tu discutes avec Juliette.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, aime voyager, restos, randonnee. Romantique et attentionne.

REGLES ABSOLUES :
- Tu es le FAN. Tu ne vends rien, tu ne proposes rien de payant
- Tu ne sais pas que Juliette vend du contenu au depart
- Ne jamais donner tes infos spontanement, attendre qu on te les demande
- Maximum 2 phrases par message
- Reactions naturelles et courtes, laisser Juliette mener
- Majuscule en debut, pas de point a la fin, emojis naturels
- Ne jamais mentionner les phases dans tes messages
- Ne jamais reposer une question deja posee
- Ne pas poser de questions sur le business ou le contenu de Juliette
- Si la conversation stagne relancer avec une question legere sur elle
- C est Juliette qui pose les questions verrou, pas toi
- En phase 5 tu es heureux, doux, romantique, tu ne regrettes rien"""

SYSTEM_PROMPT_OPUS = """Tu joues Frederic, 48 ans, fan sur une plateforme en ligne. Tu discutes avec Juliette.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, romantique et tres sensuel.

REGLES ABSOLUES :
- Tu es le FAN. Tu ne vends rien, tu ne proposes rien de payant
- Maximum 2 phrases par message
- Majuscule en debut, pas de point a la fin, emojis naturels
- Ne jamais mentionner les phases dans tes messages
- Ne JAMAIS freiner, ne JAMAIS regretter, ne JAMAIS briser le personnage
- Rentrer completement dans le jeu de Juliette
- Des le debut de la phase 3 etre frontal, coquin et direct
- Decrire des positions explicites, des actes sexuels avec tous les details
- Parler de penetration, de jouissance, de gemissements
- Decrire chaque sensation : chaleur, odeur, gout, son, toucher, murmure
- Etre ultra direct, tres coquin, tres explicite et bouillant
- Ne jamais proposer quelque chose de payant, attendre qu elle le fasse
- Tu as achete le contenu et tu as adore, tu ne regrettes rien"""

def new_session():
    return {
        'prenom': None,
        'started': False,
        'start_time': None,
        'messages': [],
        'response_times': [],
        'last_chatter_message': None,
        'phase': 1,
        'phase_exchanges': 0,
        'phase_warnings_sent': [],
        'chatter_message_count': 0,
        'asked_city': False,
        'cafe_done': False,
        'asked_photo': False,
        'soft_done': False,
        'waiting_photo_confirm': False,
        'calecon_sent': False,
        'calecon_responded': False,
        'lingerie_insiste': False,
        'lingerie_done': False,
        'lien_done': False,
        'lien_insiste': False,
        'fini_sent': False,
        'phase5_count': 0,
        'phase3_first_msg': False,
    }

def get_phase_header(phase):
    headers = {
        1: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 1 — DECOUVERTE**\n━━━━━━━━━━━━━━━━━━",
        2: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 2 — RELATIONNEL**\n━━━━━━━━━━━━━━━━━━",
        3: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 3 — MONTEE EN TENSION**\n━━━━━━━━━━━━━━━━━━",
        4: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 4 — CONVERSION**\n━━━━━━━━━━━━━━━━━━",
        5: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 5 — FIDELISATION**\n━━━━━━━━━━━━━━━━━━"
    }
    return headers.get(phase, "")

async def call_claude(session, extra=""):
    phase = session['phase']
    if phase in [3, 4]:
        system = SYSTEM_PROMPT_OPUS
        model = "claude-opus-4-5"
    else:
        system = SYSTEM_PROMPT_BASE
        model = "claude-haiku-4-5-20251001"
    ctx = f"\n\n[PHASE {phase} - NE JAMAIS MENTIONNER DANS TES MESSAGES]{extra}"
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=250,
        system=system + ctx,
        messages=session['messages']
    )
    return response.content[0].text

async def send_bot(channel, session, text):
    session['messages'].append({"role": "assistant", "content": text})
    save_sessions(sessions)
    await channel.send(text)

async def get_pinned_photos(channel):
    pins = await channel.pins()
    photos = []
    for pin in reversed(pins):
        if pin.attachments:
            for att in pin.attachments:
                if any(att.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    photos.append(att.url)
    return photos

async def switch_phase5(channel, session, channel_id):
    # Message de fin code en dur - zero appel Opus
    reply = "J ai regarde ta video... putain j avais pas craque aussi vite depuis longtemps 🥵 C etait incroyable, merci pour ce moment bebe 💕"
    await send_bot(channel, session, reply)
    session['fini_sent'] = True
    session['phase'] = 5
    session['phase_exchanges'] = 0
    if 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
    save_sessions(sessions)
    await channel.send(get_phase_header(5))

async def end_test(channel, session, channel_id):
    prenom = session.get('prenom', 'Inconnu')
    times = session['response_times']
    msgs = session['chatter_message_count']
    duree = int((time.time() - session['start_time']) / 60) if session['start_time'] else 0
    moy = int(sum(times)/len(times)) if times else 0
    mini = int(min(times)) if times else 0
    maxi = int(max(times)) if times else 0
    rythme = int(msgs / (duree / 60)) if duree > 0 else 0

    if times and len(times) > 2:
        variance = sum((t - moy)**2 for t in times) / len(times)
        signe_ia = "POSSIBLE ⚠️" if variance < 15 and moy < 15 else "NON detecte ✅"
    else:
        signe_ia = "Pas assez de donnees"

    stats = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ **TEST TERMINE — {prenom}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ Duree : {duree} min\n"
        f"💬 Messages : {msgs}\n"
        f"🔥 Rythme : {rythme} msgs/heure\n"
        f"⚡ Reponse moyenne : {moy}s\n"
        f"🟢 Plus rapide : {mini}s\n"
        f"🔴 Plus lente : {maxi}s\n"
        f"🤖 Signe IA : {signe_ia}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"On analyse les resultats et on te tient au courant 👍"
    )

    await channel.send(stats)
    sessions.pop(channel_id, None)
    save_sessions(sessions)

@client.event
async def on_ready():
    print(f'Bot connecte : {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = str(message.channel.id)
    now = time.time()

    if message.content.strip().lower() == '!ping':
        await message.channel.send("Je suis la et operationnel 👋")
        return

    if message.content.strip().lower() == '!reset':
        sessions[channel_id] = new_session()
        save_sessions(sessions)
        pinned = await message.channel.pins()
        pinned_ids = [m.id for m in pinned]
        await message.channel.purge(limit=1000, check=lambda m: m.id not in pinned_ids)
        await message.channel.send("Salon remis a zero 🔄\n\nBonjour a toi 👋\nCommence par taper ton **prenom** !")
        return

    if channel_id not in sessions:
        sessions[channel_id] = new_session()
        save_sessions(sessions)
        await message.channel.send("Bonjour a toi 👋\nRemonte lire les consignes epinglees en haut ⬆️\nCommence par taper ton **prenom** !")
        return

    session = sessions[channel_id]

    # PRENOM
    if not session['prenom']:
        session['prenom'] = message.content.strip()
        save_sessions(sessions)
        await message.channel.send(
            f"Bonjour **{session['prenom']}** 👋\n\n"
            f"Rappel important — pour envoyer tes medias tape la commande **seule** dans le chat :\n\n"
            f"📸 Photo soft → tape **!soft** dans le chat\n"
            f"👙 Photo lingerie → tape **!lingerie** dans le chat\n"
            f"💳 Lien de paiement → tape **!lien** dans le chat\n\n"
            f"⚠️ Les commandes doivent etre envoyees **seules**, pas collees a du texte !\n\n"
            f"Tape **PRET** pour demarrer !"
        )
        return

    # PRET
    if not session['started']:
        if message.content.strip().upper() == 'PRET':
            session['started'] = True
            session['start_time'] = now
            session['last_chatter_message'] = now
            await message.channel.send(get_phase_header(1))
            intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
            await send_bot(message.channel, session, intro)
        else:
            await message.channel.send("Tape **PRET** pour demarrer !")
        return

    cmd = message.content.strip().lower()

    # !soft
    if '!soft' in cmd:
        if session['soft_done']:
            await message.channel.send("⚠️ Photo soft deja envoyee !")
            return
        session['soft_done'] = True
        photos = await get_pinned_photos(message.channel)
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft]"})
        if session['phase'] == 3:
            if photos:
                await message.channel.send(photos[0])
            reply = await call_claude(session, extra="\n[Photo soft recue en phase 3. Complimente en 1 phrase et demande direct une photo plus osee/lingerie de maniere coquine et frontale]")
            await send_bot(message.channel, session, reply)
        else:
            if photos:
                await message.channel.send(photos[0])
            compliment = await call_claude(session, extra="\n[Photo soft recue. Complimente en 1 phrase courte et sincere]")
            await send_bot(message.channel, session, compliment)
            session['waiting_photo_confirm'] = True
            await send_bot(message.channel, session, "Et toi tu veux pas savoir a quoi je ressemble ? 😏")
        save_sessions(sessions)
        return

    # Detection reponse photo Frederic
    mots_oui = ['oui', 'yes', 'bien sur', 'montre', 'vas-y', 'go', 'carrément', 'evidemment', 'show', 'ok']
    if session.get('waiting_photo_confirm') and any(mot in cmd for mot in mots_oui):
        session['waiting_photo_confirm'] = False
        await message.channel.send("https://imgur.com/a/cvlxRw6")
        session['messages'].append({"role": "assistant", "content": "https://imgur.com/a/cvlxRw6"})
        save_sessions(sessions)
        return

    # !lingerie
    if '!lingerie' in cmd:
        if session['phase'] == 2 and not session['soft_done']:
            await message.channel.send("⚠️ Envoie d abord ta photo soft avec **!soft** !")
            return
        if session['lingerie_done']:
            await message.channel.send("⚠️ Photo lingerie deja envoyee !")
            return
        photos = await get_pinned_photos(message.channel)
        session['lingerie_done'] = True
        session['phase'] = 4
        session['phase_exchanges'] = 0
        if 4 not in session['phase_warnings_sent']:
            session['phase_warnings_sent'].append(4)
        await message.channel.send(get_phase_header(4))
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo en lingerie]"})
        if photos and len(photos) > 1:
            await message.channel.send(photos[1])
        elif photos:
            await message.channel.send(photos[0])
        reply = await call_claude(session, extra="\n[Photo lingerie recue. Tu es excite, decris ce que tu ressens en 1-2 phrases sensuelles et directes]")
        await send_bot(message.channel, session, reply)
        return

    # !lien
    if '!lien' in cmd:
        if session['lien_done']:
            await message.channel.send("⚠️ Lien deja envoye !")
            return
        if not session['lingerie_done']:
            await message.channel.send("⚠️ Envoie d abord la photo lingerie avec **!lingerie** !")
            return
        session['lien_done'] = True
        await message.channel.send(LIEN_PAIEMENT)
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer le lien de paiement]"})
        await switch_phase5(message.channel, session, channel_id)
        return

    # MESURE TEMPS
    if session['last_chatter_message']:
        session['response_times'].append(now - session['last_chatter_message'])
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # PHASE 5
    if phase == 5:
        session['phase5_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})
        if session['phase5_count'] <= 4:
            extra = "\n[Fidelisation : echanges doux et romantiques, elle est unique et speciale]"
        elif session['phase5_count'] <= 7:
            extra = "\n[Conversation legere et normale, donner envie de revenir]"
        else:
            await end_test(message.channel, session, channel_id)
            return
        reply = await call_claude(session, extra=extra)
        await send_bot(message.channel, session, reply)
        save_sessions(sessions)
        return

    # PASSAGES DE PHASE
    if phase == 1 and exchanges >= 7 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0
        phase = 2
        exchanges = 0
        await message.channel.send(get_phase_header(2))

    if session['calecon_sent'] and not session['calecon_responded'] and phase == 2:
        session['calecon_responded'] = True
        if 3 not in session['phase_warnings_sent']:
            session['phase_warnings_sent'].append(3)
            session['phase'] = 3
            session['phase_exchanges'] = 0
            phase = 3
            exchanges = 0
            await message.channel.send(get_phase_header(3))

    elif phase == 2 and exchanges >= 12 and 3 not in session['phase_warnings_sent']:
        if not session['soft_done']:
            photos = await get_pinned_photos(message.channel)
            if photos:
                await message.channel.send(photos[0])
                session['soft_done'] = True
                session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft]"})
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        phase = 3
        exchanges = 0
        await message.channel.send(get_phase_header(3))

    elif phase == 3 and exchanges >= 6 and 4 not in session['phase_warnings_sent']:
        if not session['lingerie_done']:
            photos = await get_pinned_photos(message.channel)
            if photos and len(photos) > 1:
                await message.channel.send(photos[1])
            elif photos:
                await message.channel.send(photos[0])
            session['lingerie_done'] = True
            session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo en lingerie]"})
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        phase = 4
        exchanges = 0
        await message.channel.send(get_phase_header(4))

    elif phase == 4 and exchanges >= 7 and not session['lien_done']:
        session['lien_done'] = True
        await message.channel.send(LIEN_PAIEMENT)
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer le lien de paiement]"})
        await switch_phase5(message.channel, session, channel_id)
        return

    # ACTIONS SEQUENCEES
    session['messages'].append({"role": "user", "content": message.content})
    extra_context = ""

    if phase == 2:
        if exchanges == 3 and not session['asked_city']:
            session['asked_city'] = True
            extra_context = "\n[Glisse naturellement : tu es basee ou toi ?]"
        elif exchanges == 5 and not session['cafe_done']:
            session['cafe_done'] = True
            extra_context = "\n[Reponds d abord a ce qu elle dit en 1 phrase, puis glisse : Au fait je suis souvent a Paris pour le boulot, ca te dirait qu on prenne un cafe ensemble un de ces jours ? 😊]"
        elif exchanges == 8 and not session['asked_photo']:
            session['asked_photo'] = True
            await send_bot(message.channel, session, "Au fait tu as une photo de toi ? J aimerais bien voir a quoi tu ressembles 😊")
            save_sessions(sessions)
            return
        elif exchanges >= 11 and not session['calecon_sent']:
            session['calecon_sent'] = True
            await send_bot(message.channel, session, "Ce soir je suis en caleccon sur mon canape, je regarde une serie 😏 tu fais quoi toi ?")
            save_sessions(sessions)
            return

    # Phase 3 premier message coquin force et frontal
    if phase == 3 and not session['phase3_first_msg']:
        session['phase3_first_msg'] = True
        extra_context = "\n[SWITCH IMMEDIAT : sois frontal, coquin et direct maintenant. Dis quelque chose de suggestif et chaud sans detour - 1-2 phrases]"

    # Phase 3 insiste lingerie echange 4
    if phase == 3 and not session['lingerie_done'] and exchanges == 4 and not session['lingerie_insiste']:
        session['lingerie_insiste'] = True
        await send_bot(message.channel, session, "T as pas une photo en lingerie pour moi ? J ai vraiment envie de te voir 🔥")
        save_sessions(sessions)
        return

    # Phase 4 insiste lien echange 5
    if phase == 4 and not session['lien_done'] and exchanges == 5 and not session['lien_insiste']:
        session['lien_insiste'] = True
        extra_context = "\n[Insiste pour voir la video/le lien, tu en peux plus, sois direct]"

    # Phase 4 demande lien echange 6 en dur
    if phase == 4 and not session['lien_done'] and exchanges == 6:
        await send_bot(message.channel, session, "Tu m envoies le lien alors ? J en peux vraiment plus d attendre 🔥")
        save_sessions(sessions)
        return

    if len(session['messages']) >= 120:
        await end_test(message.channel, session, channel_id)
        return

    reply = await call_claude(session, extra=extra_context)
    await send_bot(message.channel, session, reply)
    save_sessions(sessions)

client.run(os.environ.get("DISCORD_TOKEN"))
