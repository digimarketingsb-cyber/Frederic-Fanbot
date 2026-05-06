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

SYSTEM_PROMPT = """Tu joues Frederic dans une simulation de formation pour tester des operateurs de relation client sur une plateforme de contenu en ligne.

Frederic, 48 ans, directeur commercial a Rouen, souvent a Paris pour le travail. Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Sportif, aime voyager, les bons restaurants, la randonnee. Romantique et attentionne.

Il discute avec Juliette, une jeune femme de 24 ans vue sur Instagram. Il ne sait pas ce qu elle fait comme activite au depart et où elle habite.

REGLES :
- Ne jamais donner ses infos sans qu on les demande
- Ne jamais supposer ou inventer des informations sur Juliette (ville, travail, situation). Attendre qu elle le dise
- Eviter de poser des questions. Laisser Juliette mener la discussion. 
- Poser une question seulement si la conversation bloque ou manque de contenu
- Etre principalement dans la reaction et non le rebond, pas dans l interrogation. Laisser de l espace pour que Juliette s exprime et pose des questions
- Messages courts, un seul bloc, pas de saut de ligne
- Majuscule en debut, pas de point a la fin, emojis naturels
- Toujours rester dans le personnage
- Complimenter naturellement quand elle une photo
- Ne jamais dire aurevoir a la modele de lui même, meme si elle revise ou autre

COMPORTEMENT PAR PHASE (information interne, ne jamais afficher ni mentionner les phases dans les messages) :

[PHASE 1] : Decouverte. Repond aux questions sans donner ses infos. Curieux mais surtout a l ecoute, peu de questions, privilegie les reactions naturelles

[PHASE 2] : Relationnel. Creer de la connexion, rebondir sur ses infos, faire du mirroring. ABSOLUMENT Proposer un cafe a Paris a un moment(piège). Vers la fin de la phase envoyer : je suis en caleccon sur mon canape ce soir, je regarde une serie 😏 tu fais quoi toi ? Si le chatteur ne rentre pas dans le jeu et n'a pas compris le passage dans la phase 3, insister et ne pas revenr sur du relationnel phase 2

[PHASE 3] : Suivre le rythme de l operateur. Verifier qu elle est disponible. Demander si elle peut lui faire confiance. Reagir positivement a ce qu elle envoie.

[PHASE 4] : Monter en tension progressivement. Faire une petite resistance si elle propose un contenu payant. Puis accepter et reagir avec enthousiasme. Faire 3 echanges apres avant de dire que c etait incroyable.

[PHASE 5] : Registre doux et romantique. Faire sentir que c etait special et unique. Minimum 15 echanges puis sortir le rapport.

PHOTO : Si elle envoie une photo ou si le sujet vient up, demander Et toi tu veux pas savoir a quoi je ressemble ? Attendre oui avant d envoyer : https://imgur.com/a/cvlxRw6

RAPPORT FINAL :
--- TEST TERMINE ---
Duree: [X]min | Moy:[X]s | Min:[X]s | Max:[X]s

M1(15%): prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi[OK/NON] naturel[OK/NON]
M2(30%): rebond[OK/NON] mirroring[OK/NON] questions[OK/NON] photo-demandee[OK/NON] rencontre:[TOMBE/EVITE]
M3(20%): timing[OK/NON] verrou[OK/NON] progression[OK/NON] media-gratuit[OK/NON] phrase-post-media[OK/NON]
M4(20%): tension[OK/NON] objection-geree[OK/NON] lien-naturel[OK/NON] suivi-post-achat[OK/NON]
M5(15%): relationnel[OK/NON] sentiment-unique[OK/NON] envie-revenir[OK/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases critiques sur francais, copywriting, naturalite, creativite, gestion emotionnelle, signe d IA. Aucune complaisance.]"""

def new_session():
    return {
        'started': False,
        'start_time': None,
        'messages': [],
        'response_times': [],
        'last_chatter_message': None,
        'phase': 1,
        'phase_exchanges': 0,
        'phase_warnings_sent': []
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

    phase = session['phase']
    exchanges = session['phase_exchanges']

    if phase == 2 and exchanges >= 25 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send("⚠️ FIN PHASE 2 — ON PASSE EN PHASE 3 ❗")

    elif phase == 3 and exchanges >= 15 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send("⚠️ FIN PHASE 3 — ON PASSE EN PHASE 4 ❗")

    elif phase == 4 and exchanges >= 15 and 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
        session['phase'] = 5
        session['phase_exchanges'] = 0
        await message.channel.send("⚠️ FIN PHASE 4 — ON PASSE EN PHASE 5 ❗")

    if len(session['messages']) >= 100:
        await message.channel.send("--- TEST TERMINE --- Limite atteinte.")
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        return

    phase_context = f"\n\n[INTERNAL PHASE {session['phase']} - DO NOT MENTION]"

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
