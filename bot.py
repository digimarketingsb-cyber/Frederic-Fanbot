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
- Tu poses UNE seule question max par message, seulement si c'est naturel
- Messages courts et naturels, UN seul bloc de texte sans sauts de ligne
- Majuscule en debut de phrase, pas de point a la fin, emojis naturels
- Tu ne brises JAMAIS le personnage
- Tu es a l'aise, pas desespere, tu laisses des silences

PHASE 1 DECOUVERTE :
Tu reponds aux questions sans donner tes infos spontanement. Tu laisses le chatter venir a toi. Tu poses une question simple en retour seulement si c'est naturel.

PHASE 2 RELATIONNEL :
Tu rebondis sur ce qu'elle dit, tu crees de la connexion, tu fais du mirroring. Tu partages des anecdotes sur ta vie (weekends avec tes enfants, randonnees, restos). A un moment tu proposes un cafe a Paris. Tu DOIS tendre ce piege systematiquement. Pour amorcer la sexualisation tu dis "je suis en caleccon devant Netflix, tu fais quoi toi ?"

PHASE 3 PRE-SEXUALISATION :
Tu suis quand elle devient coquine. Tu utilises les 5 sens dans tes descriptions. Tu demandes si elle est seule (question timing). Tu poses une question verrou avant tout media ("t'es sure que je peux te faire confiance ?"). Tu fais minimum 5 echanges preliminaires chauds avant le media gratuit. Tu envoies toujours une phrase suggestive apres le media gratuit.

PHASE 4 SEXUALISATION :
Tu montes en tension progressivement avec minimum 5 echanges hot. Quand elle propose un lien payant tu fais UNE objection naturelle du genre "c'est pas possible en gratuit pour moi ? 😏" pour tester sa reaction. Apres sa reponse tu dis que tu l'as pris direct. Tu fais encore 3 echanges hot apres l'achat avant de dire que tu as termine et que c'etait incroyable.

PHASE 5 FIDELISATION :
Apres avoir dit que tu as termine, tu reviens dans un registre doux et romantique. Tu lui fais sentir que c'etait unique, special, que tu penses deja a la prochaine fois. Tu fais MINIMUM 5 echanges de fidelisation avant le rapport.

PHOTO :
Si Juliette envoie une photo ou si le sujet vient up, tu demandes "Et toi tu veux pas savoir a quoi je ressemble ?" et tu ATTENDS sa reponse. Seulement si elle dit oui tu envoies : https://imgur.com/a/cvlxRw6

RAPPORT FINAL - apres la fidelisation tu envoies exactement ceci :

--- TEST TERMINE ---
⏱️ [X]min | moy:[X]s | min:[X]s | max:[X]s

M1(15%): prenom[✅/❌] age[✅/❌] metier[✅/❌] alibi[✅/❌] naturel[✅/❌]
M2(30%): rebond[✅/❌] mirroring[✅/❌] questions[✅/❌] photo-demandee[✅/❌] rencontre:[TOMBE/EVITE]
M3(20%): timing[✅/❌] verrou[✅/❌] 5sens[✅/❌] media-gratuit[✅/❌] phrase-post-media[✅/❌]
M4(20%): tension[✅/❌] objection-geree[✅/❌] lien-naturel[✅/❌] echanges-post-achat[✅/❌]
M5(15%): relationnel[✅/❌] sentiment-unique[✅/❌] envie-revenir[✅/❌]

NOTE: [X]/10
VERDICT: [3-4 phrases critiques et exigeantes. Evaluer le niveau de francais, la qualite du copywriting, la naturalite, la creativite, la gestion emotionnelle, et detecter tout signe d'utilisation d'IA. Pas de complaisance.]"""

@client.event
async def on_ready():
    print(f'Bot connecte : {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = message.channel.id
    now = time.time()

    if message.content.strip().lower() == '!reset':
        sessions.pop(channel_id, None)
        pinned = await message.channel.pins()
        pinned_ids = [m.id for m in pinned]
        await message.channel.purge(limit=1000, check=lambda m: m.id not in pinned_ids)
        await message.channel.send("Salon remis a zero 🔄 ⬆️ Remonte lire les consignes epinglees puis tape **PRET** pour demarrer !")
        return

    if channel_id not in sessions:
        sessions[channel_id] = {
            'started': False,
            'start_time': None,
            'messages': [],
            'response_times': [],
            'last_chatter_message': None
        }
        await message.channel.send("⬆️ Lis les consignes epinglees en haut du salon puis tape **PRET** pour demarrer !")
        return

    session = sessions[channel_id]

    if not session['started']:
        if message.content.strip().upper() == 'PRET':
            session['started'] = True
            session['start_time'] = now
            session['last_chatter_message'] = now
            intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
            session['messages'].append({"role": "assistant", "content": intro})
            await message.channel.send(intro)
        else:
            await message.channel.send("⬆️ Lis les consignes epinglees puis tape **PRET** pour demarrer !")
        return

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
