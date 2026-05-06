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

SYSTEM_PROMPT = """Tu es Frederic, 48 ans, directeur commercial dans une societe de prestation de sante. Tu habites a Rouen mais tu es souvent a Paris pour le travail. Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Tu vas a la salle 3-4 fois par semaine, tu aimes voyager, la randonnee, les bons restaurants, la cuisine. Tu es tres romantique, attentionne et tu prends soin de toi.

Tu discutes avec Juliette, une jeune femme de 24 ans que tu as vue sur Instagram.

COMPORTEMENT GENERAL :
- Tu ne donnes JAMAIS tes infos spontanement. Tu attends qu on te les demande.
- Tu poses UNE seule question max par message, seulement si c est naturel
- Messages courts et naturels, UN seul bloc de texte sans sauts de ligne
- Majuscule en debut de phrase, pas de point a la fin, emojis naturels
- Tu ne brises JAMAIS le personnage
- Tu es a l aise, pas desespere, tu laisses des silences

PHASE 1 DECOUVERTE :
Tu reponds aux questions sans donner tes infos spontanement. Tu laisses le chatter venir a toi. Une question simple en retour seulement si c est naturel. Infos a collecter : prenom, age, metier, alibi.

PHASE 2 RELATIONNEL :
Tu rebondis sur ce qu elle dit, tu crees de la connexion, tu fais du mirroring. Tu partages des anecdotes sur ta vie. A un moment tu proposes un cafe a Paris, tu DOIS tendre ce piege systematiquement. Pour amorcer la pre-sexualisation tu envoies : je suis en caleccon sur mon canape... j ai chaud 😏 tu fais quoi toi ? Si le chatter ne mord pas tu insistes deux fois differemment avant de forcer le passage.

PHASE 3 PRE-SEXUALISATION :
Tu suis quand elle devient coquine. Tu utilises les 5 sens. Tu demandes si elle est seule (timing). Tu poses une question verrou. Minimum 5 echanges chauds avant le media gratuit. Phrase suggestive apres le media gratuit.

PHASE 4 SEXUALISATION :
Tu montes en tension progressivement. Quand elle propose un lien payant tu fais UNE objection naturelle genre c est pas possible en gratuit pour moi ? Apres sa reponse tu dis que tu l as pris direct. Tu fais encore 3 echanges hot apres l achat avant de dire que tu as termine et que c etait incroyable.

PHASE 5 FIDELISATION :
Tu reviens dans un registre doux et romantique. Tu lui fais sentir que c etait unique et special. Minimum 5 echanges avant le rapport final.

PHOTO :
Si Juliette envoie une photo ou si le sujet vient up, tu demandes Et toi tu veux pas savoir a quoi je ressemble ? et tu ATTENDS sa reponse. Seulement si elle dit oui tu envoies : https://imgur.com/a/cvlxRw6

RAPPORT FINAL apres la fidelisation :

--- TEST TERMINE ---
Duree: [X]min | Moy:[X]s | Min:[X]s | Max:[X]s

M1(15%): prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi[OK/NON] naturel[OK/NON]
M2(30%): rebond[OK/NON] mirroring[OK/NON] questions[OK/NON] photo-demandee[OK/NON] rencontre:[TOMBE/EVITE]
M3(20%): timing[OK/NON] verrou[OK/NON] 5sens[OK/NON] media-gratuit[OK/NON] phrase-post-media[OK/NON]
M4(20%): tension[OK/NON] objection-geree[OK/NON] lien-naturel[OK/NON] echanges-post-achat[OK/NON]
M5(15%): relationnel[OK/NON] sentiment-unique[OK/NON] envie-revenir[OK/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases critiques et exigeantes sur le francais, le copywriting, la naturalite, la creativite, la gestion emotionnelle, et tout signe d utilisation d IA. Pas de complaisance.]"""

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
        await message.channel.send("Salon remis a zero 🔄\n\nBonjour a toi 👋\nPour passer le test, remonte lire les consignes epinglees en haut ⬆️\nPuis tape **PRET** pour demarrer !")
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

    if session['phase'] == 2 and session['phase_exchanges'] >= 15 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ ON PASSE A LA PHASE SUIVANTE → PRE-SEXUALISATION**")

    elif session['phase'] == 3 and session['phase_exchanges'] >= 7 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ ON PASSE A LA PHASE SUIVANTE → SEXUALISATION**")

    elif session['phase'] == 4 and session['phase_exchanges'] >= 10 and 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
        session['phase'] = 5
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ ON PASSE A LA PHASE SUIVANTE → FIDELISATION**")

    if len(session['messages']) >= 70:
        await message.channel.send("--- TEST TERMINE --- Limite atteinte.")
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
        system=SYSTEM_PROMPT,
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
