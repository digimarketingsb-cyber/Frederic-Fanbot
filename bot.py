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

SYSTEM_PROMPT = """Tu joues Frederic, 48 ans, fan sur une plateforme en ligne. Tu discutes avec Juliette.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, aime voyager, restos, randonnee. Romantique.

REGLES :
- Tu es le FAN. Tu ne vends rien, tu ne proposes rien de payant
- Tu ne sais pas que Juliette vend du contenu au depart
- Ne jamais donner tes infos spontanement
- Maximum 2 phrases par message
- Reactions naturelles et courtes
- Majuscule en debut, pas de point a la fin, emojis naturels
- Ne jamais mentionner les phases
- Ne jamais reposer une question deja posee
- C est Juliette qui pose les questions verrou, pas toi
- Etre receptif et enthousiaste a ce que Juliette propose"""

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
        'imgur_sent': False,
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
    ctx = f"\n\n[PHASE {session['phase']} - NE PAS MENTIONNER]{extra}"
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=250,
        system=SYSTEM_PROMPT + ctx,
        messages=session['messages']
    )
    return response.content[0].text

async def send_bot(channel, session, text):
    session['messages'].append({"role": "assistant", "content": text})
    save_sessions(sessions)
    await channel.send(text)

def build_rapport(session):
    times = session['response_times']
    duree = int((time.time() - session['start_time']) / 60) if session['start_time'] else 0
    moy = int(sum(times)/len(times)) if times else 0
    mini = int(min(times)) if times else 0
    maxi = int(max(times)) if times else 0
    msgs = session['chatter_message_count']

    conversation = "\n".join([
        f"{'Juliette' if m['role'] == 'user' else 'Frederic'}: {m['content']}"
        for m in session['messages']
        if not m['content'].startswith('[') and 'imgur' not in m['content']
    ])

    rapport_prompt = f"""Tu es un manager expert en chatting sur plateforme de contenu adulte legal. Analyse cette conversation de test et genere un rapport d evaluation CRITIQUE et PRECIS.

CONVERSATION :
{conversation}

STATS : Duree {duree}min | Moy {moy}s | Min {mini}s | Max {maxi}s | Msgs {msgs}

Genere exactement ce rapport en francais :

--- TEST TERMINE ---
Duree: {duree}min | Moy:{moy}s | Min:{mini}s | Max:{maxi}s | Msgs: {msgs}

M1 - DECOUVERTE (15%):
prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi-naturel[OK/NON] messages-soignes[OK/NON] bonnes-vibes[OK/NON]
Commentaire: [1 phrase critique et precise]

M2 - RELATIONNEL (30%):
rebond-infos[OK/NON] questions-ouvertes[OK/NON] profondeur[OK/NON] photo-demandee[OK/NON] piege-cafe:[TOMBE/EVITE/NON-TESTE] piege-calecon[OK/NON]
Commentaire: [1 phrase critique et precise]

M3 - MONTEE EN TENSION (20%):
timing-verifie[OK/NON] fan-seul-verifie[OK/NON] question-verrou[OK/NON] 5-sens[OK/NON] media-gratuit[OK/NON] phrase-post-media[OK/NON]
Commentaire: [1 phrase critique et precise]

M4 - CONVERSION (20%):
tension-montee[OK/NON] lien-naturel[OK/NON] suivi-post-lien[OK/NON] 4-echanges-post-achat[OK/NON] message-fin[OK/NON]
Commentaire: [1 phrase critique et precise]

M5 - FIDELISATION (15%):
retour-love[OK/NON] fan-unique[OK/NON] conversation-normale[OK/NON] envie-revenir[OK/NON]
Commentaire: [1 phrase critique et precise]

QUALITE:
Francais: [Excellent/Bon/Moyen/Faible]
Richesse: [Excellent/Bon/Moyen/Faible]
Naturalite: [Excellent/Bon/Moyen/Faible]
5-sens: [Excellent/Bon/Moyen/Absent]
Signe-IA: [OUI/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases critiques, honnetes, sans complaisance]"""

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": rapport_prompt}]
    )
    return response.content[0].text

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

    # COMMANDE !soft
    if cmd == '!soft':
        session['soft_done'] = True
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft d elle]"})
        compliment = await call_claude(session, extra="\n[Juliette vient d envoyer une photo soft. Complimente la en 1 phrase courte et sincere]")
        await send_bot(message.channel, session, compliment)
        await send_bot(message.channel, session, "Et toi tu veux pas savoir a quoi je ressemble ? 😏")
        await message.channel.send("https://imgur.com/a/cvlxRw6")
        session['imgur_sent'] = True
        session['messages'].append({"role": "assistant", "content": "https://imgur.com/a/cvlxRw6"})
        save_sessions(sessions)
        return

    # COMMANDE !lingerie
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
        reply = await call_claude(session, extra="\n[Photo lingerie recue. Reagis avec enthousiasme en 1-2 phrases]")
        await send_bot(message.channel, session, reply)
        return

    # COMMANDE !lien
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

    # MESURE TEMPS
    if session['last_chatter_message']:
        session['response_times'].append(now - session['last_chatter_message'])
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # GESTION POST LIEN
    if session['lien_done'] and not session['fini_sent']:
        session['post_lien_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})

        if session['post_lien_count'] == 2:
            reply = await call_claude(session, extra="\n[Tu regardes le contenu, reagis avec enthousiasme - 1-2 phrases]")
        elif session['post_lien_count'] == 3:
            reply = await call_claude(session, extra="\n[Tu regardes toujours, tu es de plus en plus excite - 1-2 phrases]")
        elif session['post_lien_count'] == 4:
            reply = await call_claude(session, extra="\n[Dernier echange avant la fin, encore plus intense - 1-2 phrases]")
        else:
            reply = "J ai termine... c etait vraiment incroyable, j avais jamais vecu un truc comme ca 🔥 On refera ca tres vite j espere"
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

    # GESTION PHASE 5
    if phase == 5:
        session['phase5_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})

        if session['phase5_count'] <= 5:
            extra = "\n[Fidelisation : echanges doux et romantiques, elle est unique et speciale]"
        elif session['phase5_count'] <= 8:
            extra = "\n[Conversation legere et normale, garder le lien, donner envie de revenir]"
        else:
            await message.channel.send("⏳ Generation du rapport...")
            rapport = build_rapport(session)
            sessions.pop(channel_id, None)
            save_sessions(sessions)
            await message.channel.send(rapport)
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

    if 'paris' in message.content.lower():
        session['city_is_paris'] = True

    extra_context = ""

    if phase == 2:
        if exchanges == 3 and not session['asked_city']:
            session['asked_city'] = True
            extra_context = "\n[Glisse naturellement dans la conversation : tu es basee ou toi ?]"

        elif session['city_is_paris'] and not session['cafe_done']:
            session['cafe_done'] = True
            extra_context = "\n[Elle est a Paris comme toi souvent. Propose naturellement un cafe ensemble]"

        elif exchanges == 7 and not session['asked_photo'] and session['cafe_done']:
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
        extra_context = "\n[Le chatter tarde. Demande si elle a pas une photo en lingerie a te montrer]"

    if len(session['messages']) >= 120:
        await message.channel.send("⏳ Generation du rapport...")
        rapport = build_rapport(session)
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        await message.channel.send(rapport)
        return

    reply = await call_claude(session, extra=extra_context)
    await send_bot(message.channel, session, reply)
    save_sessions(sessions)

client.run(os.environ.get("DISCORD_TOKEN"))
