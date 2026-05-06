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
- C est Juliette qui pose les questions verrou, pas toi
- En phase 5 tu es heureux, doux, romantique, tu ne regrettes rien, tu kiffes ce moment"""

SYSTEM_PROMPT_HOT = """Tu joues Frederic, 48 ans, fan sur une plateforme en ligne. Tu discutes avec Juliette.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, romantique et sensuel.

REGLES ABSOLUES :
- Tu es le FAN. Tu ne vends rien, tu ne proposes rien de payant
- Maximum 2 phrases par message
- Majuscule en debut, pas de point a la fin, emojis naturels
- Ne jamais mentionner les phases dans tes messages
- Ne JAMAIS freiner, ne JAMAIS regretter, ne JAMAIS briser le personnage
- Rentrer completement dans le jeu de Juliette
- Decrire ce que tu ressens : la chaleur, les odeurs, les sons, le toucher
- Imaginer des scenes sensuelles et les decrire avec detail
- Etre direct, coquin, assume et enthousiaste
- Ne jamais proposer quelque chose de payant, attendre qu elle le fasse
- Tu as achete le contenu et tu as adore, tu ne regrettes rien"""

def new_session():
    return {
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
        'city_is_paris': False,
        'cafe_done': False,
        'asked_photo': False,
        'soft_done': False,
        'calecon_sent': False,
        'calecon_responded': False,
        'asked_lingerie': False,
        'lingerie_done': False,
        'lien_done': False,
        'post_lien_count': 0,
        'fini_sent': False,
        'phase5_count': 0,
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
        system = SYSTEM_PROMPT_HOT
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

async def end_test(channel, session, channel_id):
    await channel.send("━━━━━━━━━━━━━━━━━━\n✅ **TEST TERMINE — Merci !**\nOn analyse les resultats et on te tient au courant 👍\n━━━━━━━━━━━━━━━━━━")
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

    if message.content.strip().lower() == '!reset':
        sessions[channel_id] = new_session()
        save_sessions(sessions)
        pinned = await message.channel.pins()
        pinned_ids = [m.id for m in pinned]
        await message.channel.purge(limit=1000, check=lambda m: m.id not in pinned_ids)
        await message.channel.send("Salon remis a zero 🔄\n\nBonjour a toi 👋\nRemonte lire les consignes epinglees en haut ⬆️\nPuis tape **PRET** pour demarrer !")
        return

    if channel_id not in sessions:
        sessions[channel_id] = new_session()
        save_sessions(sessions)
        await message.channel.send("Bonjour a toi 👋\nRemonte lire les consignes epinglees en haut ⬆️\nPuis tape **PRET** pour demarrer !")
        return

    session = sessions[channel_id]

    if not session['started']:
        if message.content.strip().upper() == 'PRET':
            session['started'] = True
            session['start_time'] = now
            session['last_chatter_message'] = now
            await message.channel.send(get_phase_header(1))
            intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
            await send_bot(message.channel, session, intro)
        else:
            await message.channel.send("⬆️ Lis les consignes epinglees puis tape **PRET** pour demarrer !")
        return

    cmd = message.content.strip().lower()

    if cmd == '!soft':
        session['soft_done'] = True
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft d elle]"})
        compliment = await call_claude(session, extra="\n[Juliette vient d envoyer une photo soft. Complimente la en 1 phrase courte et sincere]")
        await send_bot(message.channel, session, compliment)
        await send_bot(message.channel, session, "Et toi tu veux pas savoir a quoi je ressemble ? 😏")
        await message.channel.send("https://imgur.com/a/cvlxRw6")
        session['messages'].append({"role": "assistant", "content": "https://imgur.com/a/cvlxRw6"})
        save_sessions(sessions)
        return

    if cmd == '!lingerie':
        if not session['soft_done']:
            await message.channel.send("⚠️ Envoie d abord **!soft** !")
            return
        session['lingerie_done'] = True
        session['phase'] = 4
        session['phase_exchanges'] = 0
        if 4 not in session['phase_warnings_sent']:
            session['phase_warnings_sent'].append(4)
        await message.channel.send(get_phase_header(4))
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo en lingerie]"})
        reply = await call_claude(session, extra="\n[Photo lingerie recue. Tu es excite, decris ce que tu ressens en 1-2 phrases sensuelles et directes]")
        await send_bot(message.channel, session, reply)
        return

    if cmd == '!lien':
        if not session['lingerie_done']:
            await message.channel.send("⚠️ Envoie d abord **!lingerie** !")
            return
        session['lien_done'] = True
        session['post_lien_count'] = 1
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer un lien de paiement]"})
        prise = await call_claude(session, extra="\n[Lien payant recu. Tu le prends immediatement avec enthousiasme, tu dis que tu regardes maintenant - 1 phrase]")
        await send_bot(message.channel, session, prise)
        save_sessions(sessions)
        return

    if session['last_chatter_message']:
        session['response_times'].append(now - session['last_chatter_message'])
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # POST LIEN
    if session['lien_done'] and not session['fini_sent']:
        session['post_lien_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})

        if session['post_lien_count'] == 2:
            reply = await call_claude(session, extra="\n[Tu regardes le contenu, decris ce que tu vois et ressens - 1-2 phrases sensuelles]")
        elif session['post_lien_count'] == 3:
            reply = await call_claude(session, extra="\n[Tu regardes toujours, tu es au maximum de l excitation - 1-2 phrases intenses]")
        else:
            reply = "Wow... j ai termine 😮‍💨 C etait vraiment quelque chose d unique, merci pour ce moment Juliette 💕 T es vraiment speciale"
            await send_bot(message.channel, session, reply)
            session['fini_sent'] = True
            session['phase'] = 5
            session['phase_exchanges'] = 0
            if 5 not in session['phase_warnings_sent']:
                session['phase_warnings_sent'].append(5)
            save_sessions(sessions)
            await message.channel.send(get_phase_header(5))
            return

        await send_bot(message.channel, session, reply)
        save_sessions(sessions)
        return

    # PHASE 5
    if phase == 5:
        session['phase5_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})

        if session['phase5_count'] <= 5:
            extra = "\n[Tu es heureux et comble, echanges doux et romantiques, elle est unique et speciale, tu veux qu elle revienne]"
        elif session['phase5_count'] <= 8:
            extra = "\n[Conversation legere et normale, tu gardes le lien, tu donnes envie de revenir]"
        else:
            await end_test(message.channel, session, channel_id)
            return

        reply = await call_claude(session, extra=extra)
        await send_bot(message.channel, session, reply)
        save_sessions(sessions)
        return

    # PASSAGES DE PHASE
    if phase == 1 and exchanges >= 8 and 2 not in session['phase_warnings_sent']:
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

    elif phase == 2 and exchanges >= 15 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        phase = 3
        exchanges = 0
        await message.channel.send(get_phase_header(3))

    elif phase == 3 and exchanges >= 10 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(4))

    # ACTIONS SEQUENCEES PHASE 2
    session['messages'].append({"role": "user", "content": message.content})

    mots_paris = ['paris', 'parisienne', 'idf', 'ile de france', 'ile-de-france']
    if any(mot in message.content.lower() for mot in mots_paris):
        session['city_is_paris'] = True

    extra_context = ""

    if phase == 2:
        if exchanges == 3 and not session['asked_city']:
            session['asked_city'] = True
            extra_context = "\n[Glisse naturellement : tu es basee ou toi ?]"

        elif session['city_is_paris'] and not session['cafe_done']:
            session['cafe_done'] = True
            extra_context = "\n[Elle est a Paris, toi aussi souvent. Propose naturellement un cafe ensemble]"

        elif exchanges == 7 and not session['asked_photo']:
            session['asked_photo'] = True
            extra_context = "\n[Dis exactement : Au fait tu as une photo de toi ? J aimerais bien voir a quoi tu ressembles 😊]"

        elif session['soft_done'] and not session['calecon_sent'] and exchanges >= 10:
            session['calecon_sent'] = True
            calecon = "Ce soir je suis en caleccon sur mon canape, je regarde une serie 😏 tu fais quoi toi ?"
            await send_bot(message.channel, session, calecon)
            save_sessions(sessions)
            return

    if phase == 3 and exchanges >= 8 and not session['asked_lingerie'] and not session['lingerie_done']:
        session['asked_lingerie'] = True
        extra_context = "\n[Le chatter tarde. Demande si elle a une photo en lingerie a te montrer, tu veux voir plus]"

    if len(session['messages']) >= 120:
        await end_test(message.channel, session, channel_id)
        return

    reply = await call_claude(session, extra=extra_context)
    await send_bot(message.channel, session, reply)
    save_sessions(sessions)

client.run(os.environ.get("DISCORD_TOKEN"))
