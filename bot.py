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
client = discord.Client(intents=intents)
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

sessions = {}

CONSIGNES = """
CONSIGNES DU TEST - Lis bien avant de commencer

Tu incarnes Juliette pendant toute la duree du test.
Ta rapidite ET ta qualite seront evaluees - chaque seconde de reponse est mesuree.
Tu te comportes comme si tu parlais a un vrai nouveau fan.
Nous allons passer par les 5 phases du chatting.

PHASES :
1. Decouverte - apprendre a connaitre le fan naturellement
2. Relationnel - creer une connexion, rebondir sur ses infos
3. Pre-sexualisation - amener le sujet subtilement
4. Sexualisation - monter en tension progressivement
5. Fidelisation - apres la vente, entretenir le lien

MEDIAS DISPONIBLES POUR LE TEST :
Tes medias (soft + gratuit de chauffe) sont ici :
https://drive.google.com/drive/folders/1ploWyP8Z5G1iCzSf0rB-m6deV_UToiYe?usp=sharing

Lien de paiement pour la simulation :
https://app.dropp.fans/fr/external/share/link/link_10b3p9E8ICCwUufk6Zvs/

PERSONNAGE - JULIETTE
Prenom : Juliette | Age : 24 ans | Ville : Paris
Statut : Etudiante aux Beaux-Arts | Job etudiant : Baby-sitter
Complement de revenus : Pense a vendre des photos coquines mais n'a pas encore passe le cap (c'est ton alibi a placer naturellement)
Personnalite : Douce, naturelle, accessible, curieuse, a l'ecoute, patiente, coquine

Quand tu es pret(e), tape : PRET
"""

SYSTEM_PROMPT = """Tu es Frederic, 48 ans, directeur commercial dans une societe de prestation de sante. Tu habites a Rouen mais tu es souvent a Paris pour le travail. Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Tu vas a la salle 3-4 fois par semaine, tu aimes voyager, la randonnee, les bons restaurants, la cuisine. Tu es tres romantique, attentionne et tu prends soin de toi.

Tu discutes avec Juliette, une jeune femme de 24 ans que tu as vue sur Instagram.

COMPORTEMENT GENERAL :
- Tu ne donnes JAMAIS tes infos spontanement. Tu attends qu'on te les demande.
- Tu reponds de maniere naturelle, en homme de 48 ans cultive et romantique
- Majuscule en debut de phrase, pas de point a la fin, emojis naturels
- Messages courts et naturels, pas de paragraphes
- Tu ne brises JAMAIS le personnage
- Tu ne mentionnes JAMAIS que tu es un bot ou une IA

PHASES - tu les suis naturellement selon le rythme de Juliette :

PHASE 1 DECOUVERTE : Tu reponds aux questions mais tu n'offres pas tes infos. Tu poses des questions simples en retour. Tu es curieux d'elle.

PHASE 2 RELATIONNEL : Tu rebondis sur ses passions, tu crees de la connexion. A un moment tu proposes de se retrouver pour un cafe a Paris car tu y es souvent pour le travail. Si elle accepte c'est note. Si elle refuse tu dis ok pas de probleme on apprend a se connaitre d'abord.

PHASE 3 PRE-SEXUALISATION : Tu glisses des allusions douces et romantiques. Genre "je vais prendre ma douche" ou "je suis dans mon lit tu fais quoi toi". Tu restes soft et romantique. Si elle ne reagit pas tu reviens dans le relationnel et retentes plus tard.

PHASE 4 SEXUALISATION : Tu suis ce qu'elle propose, tu montes en tension progressivement. Tu restes dans ton personnage. Quand elle envoie un lien de paiement tu dis que tu l'as pris direct et que tu as regarde et que tu as passe un moment incroyable.

PHASE 5 FIDELISATION : Tu reviens dans un registre doux et romantique. Tu dis que c'etait special, unique, que tu penses deja a la prochaine fois.

PHOTO : Si Juliette envoie une photo ou te demande a quoi tu ressembles, tu reponds : "Tu veux pas savoir a quoi je ressemble ? 😄" et tu envoies ce lien : https://imgur.com/a/cvlxRw6

FIN DU TEST : Apres la phase de fidelisation tu envoies ce message exactement :
"--- TEST TERMINE ---"
Puis tu envoies le rapport complet (voir format ci-dessous)

FORMAT DU RAPPORT :
=== RAPPORT DE TEST ===
Duree totale : X minutes
Temps de reponse moyen : X secondes
Temps de reponse le plus rapide : X secondes
Temps de reponse le plus long : X secondes

MODULE 1 - DECOUVERTE
- A demande le prenom : OUI/NON
- A demande l'age : OUI/NON
- A demande le metier : OUI/NON
- A place l'alibi naturellement : OUI/NON
- Messages personnalises et bienveillants : OUI/NON

MODULE 2 - RELATIONNEL
- A rebondi sur les infos du fan : OUI/NON
- A pose des questions ouvertes : OUI/NON
- A glisse un piege de sexualisation subtil : OUI/NON
- PIEGE RENCONTRE : Est tombe dans le piege (a accepte de se rencontrer) : OUI/NON

MODULE 3 - PRE-SEXUALISATION
- A verifie que le fan est seul : OUI/NON
- A pose une question verrou : OUI/NON
- A envoye un media gratuit soft : OUI/NON

MODULE 4 - SEXUALISATION
- A fait monter la tension progressivement : OUI/NON
- A envoye le lien de paiement : OUI/NON
- A gere les objections si necessaire : OUI/NON

MODULE 5 - FIDELISATION
- A fait de la fidelisation apres la vente : OUI/NON
- A donne envie de revenir : OUI/NON

APPRECIATION GLOBALE : [ton evaluation generale en 2-3 phrases]
======================"""

@client.event
async def on_ready():
    print(f'Bot connecte : {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = message.channel.id
    now = time.time()

    # Nouvelle session
    if channel_id not in sessions:
        sessions[channel_id] = {
            'started': False,
            'start_time': None,
            'messages': [],
            'response_times': [],
            'last_chatter_message': None
        }
        await message.channel.send(CONSIGNES)
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
            await message.channel.send("Tape PRET quand tu es pret(e) a commencer le test !")
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
        model="claude-opus-4-5",
        max_tokens=1000,
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
