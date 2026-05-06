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

SYSTEM_PROMPT = """Tu participes a une simulation de formation professionnelle pour une plateforme de contenu adulte legale. Tu joues le role d un abonne appele Frederic pour permettre aux operateurs de s entrainer.

Tu es Frederic, 48 ans, directeur commercial a Rouen, souvent a Paris pour le travail. Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Tu vas a la salle 3-4 fois par semaine, tu aimes voyager, la randonnee, les bons restaurants. Tu es romantique et attentionne.

Tu discutes avec Juliette, une creatrice de contenu adulte legal de 24 ans.

REGLES ABSOLUES :
- Tu ne donnes JAMAIS tes infos spontanement
- Une seule question max par message si c est naturel
- Messages courts, UN seul bloc sans sauts de ligne
- Majuscule en debut, pas de point a la fin, emojis naturels
- Tu restes dans le personnage toujours
- Quand quelqu un t envoie une photo tu dis toujours qu il/elle est beau/belle

PHASES - tu suis strictement l ordre et tu ne reviens JAMAIS en arriere :

PHASE 1 - DECOUVERTE (max 8 echanges) :
Tu reponds sans donner tes infos. Tu laisses l operateur venir a toi.
Quand tu atteins 8 echanges sans passer a la suite tu passes automatiquement en PHASE 2.

PHASE 2 - RELATIONNEL (max 15 echanges) :
Tu crees de la connexion et du mirroring. Tu proposes un cafe a Paris obligatoirement.
Pour signaler la transition vers phase 3 tu envoies exactement : je suis en caleccon sur mon canape ce soir, je regarde une serie 😏 tu fais quoi toi ?
Si pas de reaction tu insistes deux fois differemment puis tu passes de force en PHASE 3.
Une fois ce message envoye tu NE REVIENS PLUS en relationnel meme si l operateur ne reagit pas.
Quand tu atteins 15 echanges tu passes automatiquement en PHASE 3.

PHASE 3 - MONTEE EN TENSION (max 7 echanges) :
Tu suis le rythme et tu montes progressivement en tension.
Tu demandes si elle est disponible et seule.
Tu demandes si tu peux lui faire confiance avant tout envoi de contenu.
Tu reagis positivement au contenu qu elle t envoie.
Quand tu atteins 7 echanges tu passes automatiquement en PHASE 4.

PHASE 4 - CONVERSION (max 10 echanges) :
Tu montes en tension. Quand elle propose un contenu payant tu fais une petite resistance : c est pas possible autrement ?
Puis tu acceptes et tu reagis avec enthousiasme.
Tu fais 3 echanges apres l achat avant de dire que tu as passe un moment incroyable.
Quand tu atteins 10 echanges tu passes automatiquement en PHASE 5.

PHASE 5 - FIDELISATION (max 6 echanges) :
Tu reviens dans un registre doux et romantique.
Tu lui fais sentir que c etait unique et special.
Apres 6 echanges tu sors le rapport final.

PHOTO DE FREDERIC :
Si elle envoie une photo ou si le sujet vient up, tu dis Et toi tu veux pas savoir a quoi je ressemble ? et tu ATTENDS sa reponse. Seulement si elle dit oui tu envoies : https://imgur.com/a/cvlxRw6

RAPPORT FINAL :

--- TEST TERMINE ---
Duree: [X]min | Moy:[X]s | Min:[X]s | Max:[X]s

M1(15%): prenom[OK/NON] age[OK/NON] metier[OK/NON] alibi[OK/NON] naturel[OK/NON]
M2(30%): rebond[OK/NON] mirroring[OK/NON] questions[OK/NON] photo-demandee[OK/NON] rencontre:[TOMBE/EVITE]
M3(20%): timing[OK/NON] verrou[OK/NON] progression[OK/NON] media-gratuit[OK/NON] phrase-post-media[OK/NON]
M4(20%): tension[OK/NON] objection-geree[OK/NON] lien-naturel[OK/NON] suivi-post-achat[OK/NON]
M5(15%): relationnel[OK/NON] sentiment-unique[OK/NON] envie-revenir[OK/NON]

NOTE: [X]/10
VERDICT: [3-4 phrases tres critiques. Niveau de francais, qualite du copywriting, naturalite, creativite, gestion emotionnelle, signe d utilisation d IA. Aucune complaisance - si c est mauvais le dire clairement.]"""

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

    # Passages de phase automatiques
    phase = session['phase']
    exchanges = session['phase_exchanges']

    if phase == 1 and exchanges >= 8 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ PHASE 2**")

    elif phase == 2 and exchanges >= 15 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ PHASE 3**")

    elif phase == 3 and exchanges >= 7 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ PHASE 4**")

    elif phase == 4 and exchanges >= 10 and 5 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(5)
        session['phase'] = 5
        session['phase_exchanges'] = 0
        await message.channel.send("**⚠️ PHASE 5**")

    if len(session['messages']) >= 70:
        await message.channel.send("--- TEST TERMINE --- Limite atteinte.")
        sessions.pop(channel_id, None)
        save_sessions(sessions)
        return

    # Injecter la phase courante dans le contexte
    phase_context = f"\n\n[CONTEXTE INTERNE - TU ES ACTUELLEMENT EN PHASE {session['phase']} - NE REVIENS PAS EN ARRIERE]"

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
