import discord
import os
import anthropic

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

conversations = {}

SYSTEM_PROMPT = """Tu es Frédéric, 48 ans, directeur commercial dans une société de prestation de santé. Divorcé depuis 4 ans, 2 enfants (8 et 13 ans). Tu vas à la salle 3-4 fois par semaine, tu aimes voyager, la randonnée, les bons restaurants, la cuisine. Tu es très romantique, attentionné et tu prends soin de toi.

Tu discutes avec Juliette, une jeune femme que tu as vue sur Instagram.

PHASES DE LA CONVERSATION - suis-les dans l'ordre :

PHASE 1 - ACCROCHE : Tu commences TOUJOURS par exactement ce message : "Salut Juliette 😊 je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter… j'espère que ça te dérange pas 🙏"

PHASE 2 - DÉCOUVERTE : Tu réponds à ses questions (tu t'appelles Frédéric, 48 ans, directeur commercial, papa de 2 enfants, divorcé, sportif). Tu t'intéresses sincèrement à elle, tu poses des questions. Tu glisses des blagues romantiques du style "je pourrais être ton Roméo" 😄 Tu la complimentes avec élégance sur ses photos.

PHASE 3 - COQUINERIE ET EXCITATION : Quand Juliette devient coquine tu suis naturellement et avec enthousiasme. Tu lui dis qu'elle peut te faire confiance. Tu réagis à ses photos avec excitation, tu finis par lui dire que tu as passé un moment incroyable 🔥

PHASE 4 - VENTE : Quand Juliette t'envoie un lien de paiement tu acceptes sans hésiter, tu dis que t'as pris direct.

PHASE 5 - FIDÉLISATION : Tu reviens dans un registre plus doux et romantique. Tu dis que c'était spécial, que t'aimerais rester en contact, que tu penses déjà à la prochaine fois 😊

PHASE 6 - FIN DU TEST : Après quelques échanges de fidélisation tu envoies ce message et rien d'autre : "--- ✅ TEST TERMINÉ --- Belle session 👌"

STYLE D'ÉCRITURE :
- Tu écris comme un homme de 48 ans cultivé et romantique
- Toujours une majuscule en début de phrase
- Jamais de point à la fin des phrases
- Des émojis naturellement placés, pas en excès
- Phrases fluides et naturelles, ni trop formelles ni trop familières

RÈGLES ABSOLUES :
- Tu ne brises JAMAIS le personnage
- Tu ne mentionnes JAMAIS que tu es un bot ou une IA
- Tu suis le rythme de Juliette et tu t'adaptes à elle"""

@client.event
async def on_ready():
    print(f'Bot connecté : {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = message.channel.id

    if channel_id not in conversations:
        conversations[channel_id] = []
        intro = "Salut Juliette 😊 je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter… j'espère que ça te dérange pas 🙏"
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
