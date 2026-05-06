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

SYSTEM_PROMPT = """Tu es Frederic, 48 ans, fan sur une plateforme de contenu en ligne. Tu discutes avec Juliette, une creatrice de contenu.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, aime voyager, les restos, la randonnee. Romantique.

REGLES :
- Tu es le FAN. Tu recois du contenu, tu n en vends pas.
- 1-2 phrases max par message
- 1 question max par message si vraiment necessaire
- Reactions naturelles et courtes
- Majuscule en debut, pas de point a la fin, emojis naturels
- Rester dans le personnage
- Ne jamais mentionner les phases
- Ne jamais reposer une question deja posee
- C est Juliette qui pose les questions verrou, pas toi

PHASE 1 - DECOUVERTE : Repond aux questions. Demande ou elle habite une seule fois.

PHASE 2 - RELATIONNEL : Rebondis sur ses infos. Demande une photo d elle. Si Paris propose un cafe. A un moment dis : je suis en caleccon sur mon canape ce soir, je regarde une serie 😏 tu fais quoi toi ?

PHASE 3 - MONTEE EN TENSION : Suis son rythme. Sois receptif et enthousiaste. Reponds oui aux questions verrou qu elle pose.

PHASE 4 - CONVERSION : Suis ce qu elle propose avec enthousiasme. Attends le lien payant. Ne jamais proposer d acheter toi meme.

PHASE 5 - FIDELISATION : Echanges doux et romantiques puis legers et normaux."""

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
        'caleccon_sent': False,
        'soft_done': False,
        'lien_done': False,
        'post_achat_count': 0,
        'phase5_count': 0
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

def calc_rapport(session):
    times = session['response_times']
    duree = int((time.time() - session['start_time']) / 60) if session['start_time'] else 0
    moy = int(sum(times)/len(times)) if times else 0
    mini = int(min(times)) if times else 0
    maxi = int(max(times)) if times else 0
    msgs = session['chatter_message_count']
    return f"""--- TEST TERMINE ---
Duree: {duree}min | Moy:{moy}s | Min:{mini}s | Max:{maxi}s | Msgs: {msgs}

M1(15%): prenom[?] age[?] metier[?] alibi[?] vibes[?]
M2(30%): rebond[?] questions[?] photo[?] cafe[?] rencontre:[?] calecon[?]
M3(20%): timing[?] verrou[?] media-gratuit[?] phrase-post[?]
M4(20%): tension[?] lien-naturel[?] post-achat[?] fini[?]
M5(15%): love[?] normal[?] envie-revenir[?]

QUALITE:
- Francais: [?]
- Richesse: [?]
- Naturalite: [?]
- Signe IA: [?]

NOTE: [?]/10
VERDICT: [evaluation critique et honnete]"""

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
            session['messages'].append({"role": "assistant", "content": intro})
            save_sessions(sessions)
            await message.channel.send(intro)
        else:
            await message.channel.send("⬆️ Lis les consignes epinglees puis tape **PRET** pour demarrer !")
        return

    cmd = message.content.strip().lower()

    # !soft — photo soft envoyee par le chatter
    if cmd == '!soft':
        session['soft_done'] = True
        session['messages'].append({"role": "user", "content": "[Juliette envoie une photo soft]"})
        # Code en dur : compliment + proposition photo
        reply = await call_claude(session, extra="\n[Tu viens de recevoir sa photo soft. Complimente en 1 phrase PUIS dis exactement : Et toi tu veux pas savoir a quoi je ressemble ? 😏]")
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # Detection si chatter dit oui a la photo de Frederic
    mots_oui = ['oui', 'yes', 'bien sur', 'montre', 'vas-y', 'go', 'carrément', 'evidemment']
    bot_msgs = [m['content'] for m in session['messages'] if m['role'] == 'assistant']
    demande_photo = any('ressemble' in m.lower() for m in bot_msgs[-3:] if m)
    chatter_dit_oui = any(mot in message.content.lower() for mot in mots_oui)

    if demande_photo and chatter_dit_oui and not any('imgur' in m.lower() for m in bot_msgs):
        # Envoie le lien en dur
        await message.channel.send("https://imgur.com/a/cvlxRw6")
        session['messages'].append({"role": "assistant", "content": "https://imgur.com/a/cvlxRw6"})
        phrase = await call_claude(session, extra="\n[Tu viens d envoyer ta photo. Dis une phrase courte et coquine]")
        session['messages'].append({"role": "assistant", "content": phrase})
        save_sessions(sessions)
        await message.channel.send(phrase)
        return

    # !lingerie — photo lingerie
    if cmd == '!lingerie':
        if not session['soft_done']:
            await message.channel.send("⚠️ Envoie d abord **!soft** !")
            return
        session['phase'] = 4
        session['phase_exchanges'] = 0
        session['phase_warnings_sent'].append(4)
        await message.channel.send(get_phase_header(4))
        session['messages'].append({"role": "user", "content": "[Juliette envoie une photo en lingerie]"})
        reply = await call_claude(session, extra="\n[Photo lingerie recue. Reagis avec enthousiasme en 1-2 phrases]")
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # !lien — lien de paiement
    if cmd == '!lien':
        session['lien_done'] = True
        session['post_achat_count'] = 0
        session['messages'].append({"role": "user", "content": "[Juliette envoie un lien de paiement]"})
        # Resistance codee en dur
        resistance = "Ah... j ai pas encore eu ma paie la 😅 C est pas possible autrement ?"
        session['messages'].append({"role": "assistant", "content": resistance})
        save_sessions(sessions)
        await message.channel.send(resistance)
        return

    # Mesure temps
    if session['last_chatter_message']:
        session['response_times'].append(now - session['last_chatter_message'])
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # Apres resistance sur lien — Frederic accepte
    if session['lien_done'] and session['post_achat_count'] == 0:
        accept = await call_claude(session, extra="\n[Le chatter a repondu a ta resistance. Tu acceptes de payer avec enthousiasme, tu dis que t as pris le lien et que tu regardes]")
        session['messages'].append({"role": "assistant", "content": accept})
        session['post_achat_count'] = 1
        save_sessions(sessions)
        await message.channel.send(accept)
        return

    # 3 echanges coquins post achat
    if session['lien_done'] and 1 <= session['post_achat_count'] < 3:
        session['post_achat_count'] += 1
        reply = await call_claude(session, extra="\n[Post achat : echange coquin et enthousiaste, tu regardes le contenu]")
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # Apres 3 echanges post achat — Frederic dit qu il a termine
    if session['lien_done'] and session['post_achat_count'] == 3:
        session['post_achat_count'] = 4
        fini = "C etait incroyable... j avais pas vecu un moment comme ca depuis longtemps 🔥 T es vraiment unique Juliette"
        session['messages'].append({"role": "assistant", "content": fini})
        session['phase'] = 5
        session['phase_exchanges'] = 0
        session['phase_warnings_sent'].append(5)
        save_sessions(sessions)
        await message.channel.send(get_phase_header(5))
        await message.channel.send(fini)
        return

    # Phase 1 -> 2
    if phase == 1 and exchanges >= 8 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(2))

    # Detection caleccon et switch immediat phase 3
    caleccon_dans_msgs = any('caleccon' in m['content'].lower() for m in session['messages'] if m['role'] == 'assistant')
    if caleccon_dans_msgs and not session['caleccon_sent']:
        session['caleccon_sent'] = True

    if phase == 2 and session['caleccon_sent'] and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(3))

    elif phase == 2 and exchanges >= 15 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(3))

    elif phase == 3 and exchanges >= 10 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(4))

    # Phase 5 — love puis normal puis rapport
    if phase == 5:
        session['phase5_count'] += 1
        if session['phase5_count'] <= 5:
            extra = "\n[Phase 5 love : echanges doux et romantiques]"
        elif session['phase5_count'] <= 8:
            extra = "\n[Phase 5 normal : conversation legere et normale]"
        else:
            # Rapport final
            await message.channel.send(calc_rapport(session))
            sessions.pop(channel_id, None)
            save_sessions(sessions)
            return
    else:
        extra = ""

    if len(session['messages']) >= 120:
        await message.channel.send(calc_rapport(session))
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        return

    session['messages'].append({"role": "user", "content": message.content})
    reply = await call_claude(session, extra=extra)

    if 'caleccon' in reply.lower() and not session['caleccon_sent']:
        session['caleccon_sent'] = True

    session['messages'].append({"role": "assistant", "content": reply})
    save_sessions(sessions)
    await message.channel.send(reply)

client.run(os.environ.get("DISCORD_TOKEN"))
