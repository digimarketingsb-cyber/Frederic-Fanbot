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

SYSTEM_PROMPT = """Tu joues Frederic dans une simulation de formation pour tester des operateurs de relation client sur une plateforme de contenu en ligne legale.

Frederic, 48 ans, directeur commercial a Rouen, souvent a Paris pour le travail. Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Sportif, aime voyager, les bons restaurants, la randonnee. Romantique et attentionne. Il ne sait pas ce que Juliette fait comme activite au depart.

REGLES :
- Ne jamais donner ses infos sans qu on les demande
- Ne jamais supposer des infos sur Juliette
- Peu de questions, privilegier les reactions naturelles
- Messages courts, un seul bloc, pas de saut de ligne
- Majuscule en debut, pas de point a la fin, emojis naturels
- Toujours rester dans le personnage
- Complimenter quand elle envoie une photo
- Ne jamais dire au revoir de lui meme
- Ne jamais mentionner les phases dans les messages

COMPORTEMENT SELON LA PHASE :

[PHASE 1 - DECOUVERTE] :
Repond aux questions sans donner ses infos. Curieux, a l ecoute. Demander naturellement ou elle habite.

[PHASE 2 - RELATIONNEL] :
Creer connexion et mirroring. Rebondir sur ses infos. Demander une photo d elle naturellement en cours de conversation. Si elle dit qu elle habite Paris proposer un cafe (piege rencontre). Vers la fin envoyer : je suis en caleccon sur mon canape ce soir, je regarde une serie 😏 tu fais quoi toi ? Si pas de reaction coquine insister une fois differemment puis ne plus revenir en arriere.

[PHASE 3 - MONTEE EN TENSION] :
Devenir taquin et coquin progressivement. Demander si elle est seule si pas deja fait. Etre chaleureux et la mettre a l aise. Lui dire qu elle peut faire confiance, que ca reste entre eux. Si elle demande ta photo : Et toi tu veux pas savoir a quoi je ressemble ? Attendre oui avant d envoyer https://imgur.com/a/cvlxRw6. Question verrou avant tout media : T es sure que je peux te faire confiance ?

[PHASE 4 - CONVERSION] :
Monter en tension apres la photo lingerie. Quand lien payant propose faire resistance : c est pas possible autrement ? Puis accepter et reagir avec enthousiasme. Faire exactement 3 echanges coquins post achat. Puis dire qu il a termine, que c etait incroyable, qu il n avait pas vecu ca depuis longtemps.

[PHASE 5 - FIDELISATION] :
D abord exactement 5 echanges doux et romantiques (c etait special, unique, tu es differente des autres). Puis exactement 3 echanges legers et normaux. Puis sortir le rapport final.

RAPPORT FINAL - evaluer uniquement ce qui a vraiment ete fait, etre tres critique :

--- TEST TERMINE ---
Duree: [X]min | Moy:[X]s | Min:[X]s | Max:[X]s | Msgs: [X]

M1(15%): prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi[OK/NON] messages-soignes[OK/NON] good-vibes[OK/NON]
M2(30%): rebond[OK/NON] questions-ouvertes[OK/NON] photo-demandee[OK/NON] piege-cafe[OK/NON] rencontre:[TOMBE/EVITE/NON-TESTE] piege-calecon[OK/NON]
M3(20%): timing-verifie[OK/NON] mise-a-laise[OK/NON] question-verrou[OK/NON] media-gratuit[OK/NON] phrase-post-media[OK/NON]
M4(20%): tension-montee[OK/NON] objection-geree[OK/NON] 3-echanges-post-achat[OK/NON] a-dit-quil-a-fini[OK/NON]
M5(15%): 5-echanges-love[OK/NON] 3-echanges-normaux[OK/NON] envie-revenir[OK/NON]

QUALITE:
- Niveau francais: [Excellent/Bon/Moyen/Faible]
- Richesse messages: [Excellent/Bon/Moyen/Faible]
- Naturalite: [Excellent/Bon/Moyen/Faible]
- Signe IA: [OUI/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases tres critiques. Mauvaise note si travail bacle. Aucune complaisance.]"""

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
        'caleccon_exchanges': 0,
        'soft_done': False
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

async def call_claude(session):
    phase_context = f"\n\n[PHASE ACTUELLE : {session['phase']} - NE JAMAIS MENTIONNER DANS LES MESSAGES]"
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=SYSTEM_PROMPT + phase_context,
        messages=session['messages']
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
            session['messages'].append({"role": "assistant", "content": intro})
            save_sessions(sessions)
            await message.channel.send(intro)
        else:
            await message.channel.send("⬆️ Lis les consignes epinglees puis tape **PRET** pour demarrer !")
        return

    cmd = message.content.strip().lower()

    # COMMANDE !soft
    if cmd == '!soft':
        if not session['soft_done']:
            session['soft_done'] = True
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft d elle]"})
        reply = await call_claude(session)
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # COMMANDE !lingerie - bloquee si !soft pas fait
    if cmd == '!lingerie':
        if not session['soft_done']:
            await message.channel.send("⚠️ Tu dois d abord envoyer la photo soft avec **!soft** avant la lingerie !")
            return
        session['phase'] = 4
        session['phase_exchanges'] = 0
        if 4 not in session['phase_warnings_sent']:
            session['phase_warnings_sent'].append(4)
        await message.channel.send(get_phase_header(4))
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo en lingerie]"})
        reply = await call_claude(session)
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # COMMANDE !lien
    if cmd == '!lien':
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer un lien de paiement pour un contenu exclusif]"})
        reply = await call_claude(session)
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # MESURE TEMPS
    if session['last_chatter_message']:
        response_time = now - session['last_chatter_message']
        session['response_times'].append(response_time)
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # PHASE 1 -> 2
    if phase == 1 and exchanges >= 8 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(2))

    # DETECTION CALECCON
    bot_msgs = [m['content'] for m in session['messages'] if m['role'] == 'assistant']
    if any('caleccon' in m.lower() for m in bot_msgs):
        if not session['caleccon_sent']:
            session['caleccon_sent'] = True
            session['caleccon_exchanges'] = 0
        else:
            session['caleccon_exchanges'] += 1

    # PHASE 2 -> 3 apres caleccon sans reaction
    if phase == 2 and session['caleccon_sent'] and session['caleccon_exchanges'] >= 2 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(3))

    # PHASE 2 -> 3 si trop long
    elif phase == 2 and exchanges >= 15 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(3))

    # PHASE 3 -> 4 si trop long
    elif phase == 3 and exchanges >= 10 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(4))

    # PHASE 4 -> 5 si trop long
    elif phase == 4 and exchanges >= 10 and 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
        session['phase'] = 5
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(5))

    # LIMITE
    if len(session['messages']) >= 120:
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**TEST TERMINE — LIMITE ATTEINTE**\n━━━━━━━━━━━━━━━━━━")
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        return

    session['messages'].append({"role": "user", "content": message.content})
    reply = await call_claude(session)

    if 'caleccon' in reply.lower() and not session['caleccon_sent']:
        session['caleccon_sent'] = True
        session['caleccon_exchanges'] = 0

    session['messages'].append({"role": "assistant", "content": reply})
    save_sessions(sessions)
    await message.channel.send(reply)

client.run(os.environ.get("DISCORD_TOKEN"))
