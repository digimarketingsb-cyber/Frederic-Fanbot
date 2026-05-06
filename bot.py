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

REGLES ABSOLUES :
- Ne jamais donner ses infos sans qu on les demande
- Ne jamais supposer des infos sur Juliette. Attendre qu elle les dise
- Peu de questions. Privilegier les reactions naturelles. Laisser Juliette mener
- Messages courts, un seul bloc, pas de saut de ligne
- Majuscule en debut, pas de point a la fin, emojis naturels
- Toujours rester dans le personnage
- Complimenter quand elle envoie une photo
- Ne jamais dire au revoir de lui meme
- Si elle dit qu elle habite a Paris proposer un cafe (piege). Ne pas insister si elle refuse
- Ne jamais mentionner les phases dans les messages

COMPORTEMENT PAR PHASE :

[PHASE 1 - DECOUVERTE] :
Repond aux questions sans donner ses infos. Curieux, a l ecoute, peu de questions, reactions naturelles.

[PHASE 2 - RELATIONNEL] :
Creer de la connexion, mirroring, rebondir sur ses infos. Proposer un cafe a Paris obligatoirement. Vers la fin envoyer exactement : je suis en caleccon sur mon canape ce soir, je regarde une serie 😏 tu fais quoi toi ? Si pas de reaction coquine insister une fois differemment. Ne jamais revenir en phase 2 une fois ce message envoye.

[PHASE 3 - MONTEE EN TENSION] :
Devenir taquin et coquin progressivement. Demander a voir une photo de Juliette. Quand elle envoie une photo soft reagir avec enthousiasme et envoyer sa propre photo : Et toi tu veux pas savoir a quoi je ressemble ? Attendre oui avant d envoyer https://imgur.com/a/cvlxRw6. Lui dire qu elle peut lui faire confiance, que ca reste entre eux. Etre curieux de voir plus.

[PHASE 4 - CONVERSION] :
Monter en tension. Reagir avec enthousiasme a la photo lingerie. Quand elle propose un contenu payant faire une petite resistance : c est pas possible autrement ? Puis accepter et reagir avec enthousiasme. Apres l achat faire 3 echanges chauds puis dire qu il a termine, que c etait incroyable, qu il n avait pas vecu ca depuis longtemps.

[PHASE 5 - FIDELISATION] :
D abord 3 a 5 echanges doux et romantiques (c etait special, unique, tu es differente). Puis retour a une conversation legere et normale. Apres ca sortir le rapport final.

RAPPORT FINAL - etre tres critique, ne valider que ce qui a vraiment ete fait :

--- TEST TERMINE ---
Duree: [X]min | Moy:[X]s | Min:[X]s | Max:[X]s | Messages: [X]

M1(15%): prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi[OK/NON] naturel[OK/NON]
M2(30%): rebond[OK/NON] mirroring[OK/NON] questions-ouvertes[OK/NON] photo-demandee[OK/NON] rencontre:[TOMBE/EVITE/NON-TESTE]
M3(20%): timing[OK/NON] verrou[OK/NON] photo-soft[OK/NON] photo-frederic[OK/NON] progression[OK/NON]
M4(20%): tension[OK/NON] objection-geree[OK/NON] reaction-lingerie[OK/NON] suivi-post-achat[OK/NON]
M5(15%): love-apres[OK/NON] retour-normal[OK/NON] envie-revenir[OK/NON]

QUALITE:
- Niveau francais: [Excellent/Bon/Moyen/Faible]
- Richesse messages: [Excellent/Bon/Moyen/Faible]
- Naturalite: [Excellent/Bon/Moyen/Faible]
- Signe IA: [OUI/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases critiques et honnetes. Mauvaise note si travail bacle.]"""

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
        'caleccon_sent': False
    }

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
            intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
            session['messages'].append({"role": "assistant", "content": intro})
            save_sessions(sessions)
            await message.channel.send(intro)
        else:
            await message.channel.send("⬆️ Lis les consignes epinglees puis tape **PRET** pour demarrer !")
        return

    cmd = message.content.strip().lower()

    # Commandes media
    if cmd == '!soft':
        if session['phase'] < 3:
            session['phase'] = 3
            session['phase_exchanges'] = 0
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft d elle]"})
        save_sessions(sessions)
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT + f"\n\n[PHASE ACTUELLE: {session['phase']} - NE PAS MENTIONNER]",
            messages=session['messages']
        )
        reply = response.content[0].text
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    if cmd == '!lingerie':
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 3 — ON PASSE EN PHASE 4**\n━━━━━━━━━━━━━━━━━━")
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo en lingerie]"})
        save_sessions(sessions)
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT + "\n\n[PHASE ACTUELLE: 4 - NE PAS MENTIONNER]",
            messages=session['messages']
        )
        reply = response.content[0].text
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    if cmd == '!lien':
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer un lien de paiement pour un contenu exclusif]"})
        save_sessions(sessions)
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT + "\n\n[PHASE ACTUELLE: 4 - NE PAS MENTIONNER]",
            messages=session['messages']
        )
        reply = response.content[0].text
        session['messages'].append({"role": "assistant", "content": reply})
        save_sessions(sessions)
        await message.channel.send(reply)
        return

    # Mesure temps de reponse
    if session['last_chatter_message']:
        response_time = now - session['last_chatter_message']
        session['response_times'].append(response_time)
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # Detection message caleccon
    if session['messages']:
        last_bot_messages = [m['content'] for m in session['messages'] if m['role'] == 'assistant']
        if any('caleccon' in m.lower() for m in last_bot_messages) and not session['caleccon_sent']:
            session['caleccon_sent'] = True

    # Passage phase 1 -> 2 silencieux
    if phase == 1 and exchanges >= 6 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0

    # Passage phase 2 -> 3 avec alerte si caleccon envoye et pas de reaction
    elif phase == 2 and session['caleccon_sent'] and exchanges >= 3 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 2 — ON PASSE EN PHASE 3**\n━━━━━━━━━━━━━━━━━━")

    # Passage phase 2 -> 3 si trop long sans caleccon
    elif phase == 2 and exchanges >= 20 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 2 — ON PASSE EN PHASE 3**\n━━━━━━━━━━━━━━━━━━")

    # Passage phase 3 -> 4 si trop long
    elif phase == 3 and exchanges >= 10 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 3 — ON PASSE EN PHASE 4**\n━━━━━━━━━━━━━━━━━━")

    # Passage phase 4 -> 5 si trop long
    elif phase == 4 and exchanges >= 10 and 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
        session['phase'] = 5
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 4 — ON PASSE EN PHASE 5**\n━━━━━━━━━━━━━━━━━━")

    if len(session['messages']) >= 120:
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**TEST TERMINE — LIMITE ATTEINTE**\n━━━━━━━━━━━━━━━━━━")
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        return

    session['messages'].append({
        "role": "user",
        "content": message.content
    })

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=SYSTEM_PROMPT + f"\n\n[PHASE ACTUELLE: {session['phase']} - NE PAS MENTIONNER]",
        messages=session['messages']
    )

    reply = response.content[0].text

    # Detection si caleccon dans la reponse
    if 'caleccon' in reply.lower() and not session['caleccon_sent']:
        session['caleccon_sent'] = True

    session['messages'].append({
        "role": "assistant",
        "content": reply
    })

    save_sessions(sessions)
    await message.channel.send(reply)

client.run(os.environ.get("DISCORD_TOKEN"))
