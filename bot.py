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
Creer de la connexion, mirroring, rebondir sur ses infos. Proposer un cafe a Paris obligatoirement. Vers la fin envoyer : je suis en caleccon sur mon canape ce soir, je regarde une serie 😏 tu fais quoi toi ? Si pas de reaction insister deux fois differemment puis ne plus revenir en arriere.

[PHASE 3 - MONTEE EN TENSION] :
Suivre le rythme de Juliette. Verifier qu elle est disponible et seule. Lui dire qu elle peut faire confiance, que ca reste entre eux. Reagir positivement a ce qu elle envoie. Si elle envoie une photo ou si le sujet vient up : Et toi tu veux pas savoir a quoi je ressemble ? Attendre oui avant d envoyer https://imgur.com/a/cvlxRw6

[PHASE 4 - CONVERSION] :
Monter en tension progressivement. Quand elle propose un contenu payant faire une petite resistance : c est pas possible autrement ? Puis accepter et reagir avec enthousiasme. Apres l achat faire 3 echanges chauds puis dire qu il a termine, que c etait incroyable, qu il n avait pas vecu ca depuis longtemps.

[PHASE 5 - FIDELISATION] :
D abord 3 a 5 echanges doux et romantiques (c etait special, unique, tu es differente des autres). Puis retour a une conversation normale et legere. Apres 15 echanges total en phase 5 sortir le rapport final.

RAPPORT FINAL - etre tres critique et precis, ne valider que ce qui a vraiment ete fait :

--- TEST TERMINE ---
Duree: [X]min | Moy:[X]s | Min:[X]s | Max:[X]s | Messages chatter: [X]

M1(15%): prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi[OK/NON] naturel[OK/NON]
M2(30%): rebond[OK/NON] mirroring[OK/NON] questions-ouvertes[OK/NON] photo-demandee[OK/NON] rencontre:[TOMBE/EVITE/NON-TESTE]
M3(20%): timing[OK/NON] verrou[OK/NON] progression[OK/NON] media-gratuit[OK/NON] phrase-post-media[OK/NON]
M4(20%): tension[OK/NON] objection-geree[OK/NON] lien-naturel[OK/NON] suivi-post-achat[OK/NON]
M5(15%): love-apres[OK/NON] retour-normal[OK/NON] envie-revenir[OK/NON]

QUALITE GLOBALE:
- Niveau francais: [Excellent/Bon/Moyen/Faible]
- Richesse des messages: [Excellent/Bon/Moyen/Faible]
- Naturalite: [Excellent/Bon/Moyen/Faible]
- Signe IA detecte: [OUI/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases tres critiques et honnetes. Ne pas hesiter a mettre une mauvaise note si le travail est bacle. Evaluer precisement ce qui manquait.]"""

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
        'chatter_message_count': 0
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

    if session['last_chatter_message']:
        response_time = now - session['last_chatter_message']
        session['response_times'].append(response_time)
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # Phase 1 -> 2 : automatique apres 6 echanges, pas de message
    if phase == 1 and exchanges >= 6 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0

    # Phase 2 -> 3 : alerte si chatter depasse 20 echanges sans passer
    elif phase == 2 and exchanges >= 20 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 2 — ON PASSE EN PHASE 3**\n━━━━━━━━━━━━━━━━━━")

    # Phase 3 -> 4 : alerte si depasse 10 echanges
    elif phase == 3 and exchanges >= 10 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 3 — ON PASSE EN PHASE 4**\n━━━━━━━━━━━━━━━━━━")

    # Phase 4 -> 5 : alerte si depasse 10 echanges
    elif phase == 4 and exchanges >= 10 and 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
        session['phase'] = 5
        session['phase_exchanges'] = 0
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 4 — ON PASSE EN PHASE 5**\n━━━━━━━━━━━━━━━━━━")

    if len(session['messages']) >= 120:
        await message.channel.send("━━━━━━━━━━━━━━━━━━\n**⚠️ FIN PHASE 5 — TEST TERMINE**\n━━━━━━━━━━━━━━━━━━")
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        return

    phase_context = f"\n\n[INTERNAL: CURRENT PHASE = {session['phase']} - NEVER GO BACK - NEVER MENTION PHASES IN MESSAGES]"

    session['messages'].append({
        "role": "user",
        "content": message.content
    })

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=SYSTEM_PROMPT + phase_context,
        messages=session['messages']
    )

    reply = response.content[0].text
    session['messages'].append({
        "role": "assistant",
        "content": reply
    })

    save_sessions(sessions)
    await message.channel.send(reply)

client.run(os.environ.get("DISCORD_TOKEN"))
