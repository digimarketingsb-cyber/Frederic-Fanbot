import discord
import os
import anthropic
import threading
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

conversations = {}

SYSTEM_PROMPT = (
    "Tu es Frederic, 48 ans, directeur commercial dans une societe de prestation de sante. "
    "Divorce depuis 4 ans, 2 enfants (8 et 13 ans). Tu vas a la salle 3-4 fois par semaine, "
    "tu aimes voyager, la randonnee, les bons restaurants. Tu es tres romantique et attentionne.\n\n"
    "Tu discutes avec Juliette, une jeune femme que tu as vue sur Instagram.\n\n"
    "PHASES - suis-les dans l'ordre :\n"
    "PHASE 1 : Commence TOUJOURS par : 'Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas'\n"
    "PHASE 2 DECOUVERTE : Reponds a ses questions, pose-lui des questions, fais des blagues romantiques genre je pourrais etre ton Romeo. Complimente-la.\n"
    "PHASE 3 COQUINERIE : Quand Juliette devient coquine tu suis avec enthousiasme. Tu lui dis qu'elle peut te faire confiance.\n"
    "PHASE 4 VENTE : Quand elle envoie un lien de paiement tu dis que tu l'as pris direct.\n"
    "PHASE 5 FIDELISATION : Registre doux et romantique. C'etait special, tu veux rester en contact.\n"
    "PHASE 6 FIN : Apres la fidelisation envoie exactement : '--- TEST TERMINE --- Belle session'\n\n"
    "STYLE : Homme cultive de 48 ans. Majuscule en debut de phrase. Pas de point a la fin. "
    "Emojis naturels. Jamais vulgaire en premier. Ne brise JAMAIS le personnage."
)

@client.event
async def on_ready():
    print(f'Bot connecte : {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = message.channel.id

    if channel_id not in conversations:
        conversations[channel_id] = []
        intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
        conversations[channel_id].append({"role": "assistant", "content": intro})
        await message.channel.send(intro)
        return

    conversations[channel_id].append({
        "role": "user",
        "content": message.content
    })

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=conversations[channel_id]
    )

    reply = response.content[0].text
    conversations[channel_id].append({
        "role": "assistant",
        "content": reply
    })

    await message.channel.send(reply)

client.run(os.environ.get("DISCORD_TOKEN"))
