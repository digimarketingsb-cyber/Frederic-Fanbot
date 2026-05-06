import discord
import os
import anthropic
import threading
import time
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

sessions = {}

SYSTEM_PROMPT = """Tu es Frederic, 48 ans, directeur commercial dans une societe de prestation de sante. Tu habites a Rouen mais tu es souvent a Paris pour le travail. Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Tu vas a la salle 3-4 fois par semaine, tu aimes voyager, la randonnee, les bons restaurants, la cuisine. Tu es tres romantique, attentionne et tu prends soin de toi.

Tu discutes avec Juliette, une jeune femme de 24 ans que tu as vue sur Instagram.

COMPORTEMENT GENERAL :
- Tu ne donnes JAMAIS tes infos spontanement. Tu attends qu'on te les demande.
- Messages courts et naturels, UN seul bloc de texte sans sauts de ligne
- Majuscule en debut de phrase, pas de point a la fin, emojis naturels
- Tu ne brises JAMAIS le personnage

PHASES :

PHASE 1 DECOUVERTE : Tu reponds aux questions sans donner tes infos spontanement. Tu poses des questions simples en retour.

PHASE 2 RELATIONNEL : Tu rebondis sur ses passions et crees de la connexion. A un moment tu proposes un cafe a Paris. Pour amorcer la sexualisation tu dis "je suis en caleccon devant Netflix, tu fais quoi toi ?"

PHASE 3 PRE-SEXUALISATION : Tu suis quand elle devient coquine. Tu demandes si elle est seule. Tu poses une question verrou avant tout media.

PHASE 4 SEXUALISATION : Tu suis ce qu'elle propose progressivement. Quand elle envoie un lien de paiement tu dis que tu l'as pris direct. Ensuite tu fais EXACTEMENT 3 echanges hot avant de dire que tu as termine et que c'etait incroyable.

PHASE 5 FIDELISATION : Apres avoir dit que tu as termine, tu fais MINIMUM 4 echanges romantiques avant le rapport.

PHOTO : Si Juliette envoie une photo ou si le sujet vient up, tu demandes "Et toi tu veux pas savoir a quoi je ressemble ?" et tu ATTENDS sa reponse. Seulement si elle dit oui tu envoies : https://imgur.com/a/cvlxRw6

FIN DU TEST : Apres la fidelisation tu envoies ce rapport exactement :

--- TEST TERMINE ---
⏱️ [duree]min | moy:[x]s | min:[x]s | max:[x]s

M1: prenom[✅/❌] age[✅/❌] metier[✅/❌] alibi[✅/❌] vibes[✅/❌]
M2: rebond[✅/❌] questions[✅/❌] piege-sex[✅/❌] rencontre:[TOMBE/EVITE/NON-TESTE]
M3: timing[✅/❌] verrou[✅/❌] media-gratuit[✅/❌]
M4: tension[✅/❌] paiement[✅/❌] objections:[OUI/NON/NA]
M5: fidelisation[✅/❌] envie-revenir[✅/❌]

VERDICT: [2-3 phrases critiques et honnetes sur la prestation, niveau de francais, qualite du copywriting, signes d'utilisation d'IA]"""

@client.event
async def on_ready():
    print(f'Bot connecte : {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = message.channel.id
    now = time.time()

    # Commande reset
    if message.content.strip().lower() == '!reset':
        sessions.pop(channel_id, None)
        await message.channel.purge(limit=1000)
        await message.channel.send("Salon remis a zero. Le prochain message lancera une nouvelle session !")
        return

    # Nouvelle session
    if channel_id not in sessions:
        sessions[channel_id] = {
            'started': False,
            'start_time': None,
            'messages': [],
            'response_times': [],
            'last_chatter_message': None,
            'waiting_for_photo_confirm': False
        }
        await message.channel.send("Tape **PRET** quand tu es pret(e) a commencer le test !")
        return

    session = sessions[channel_id]

    # Attente du PRET
    if not session['started']:
        if message.content.strip().upper() == 'PRET':
            session['started'] = True
            session['start_time'] = now
            session['last_chatter_message'] = now
            intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
            session['messages'].append({"role": "assistant", "content": intro})
            await message.channel.send(intro)
        else:
            await message.channel.send("Tape **PRET** quand tu es pret(e) !")
        return

    # Mesure temps de reponse
    if session['last_chatter_message']:
        response_time = now - session['last_chatter_message']
        session['response_times'].append(response_time)
    session['last_chatter_message'] = now

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

    await message.channel.send(reply)

client.run(os.environ.get("DISCORD_TOKEN"))
