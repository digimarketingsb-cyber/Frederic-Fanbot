import discord
import os
import anthropic
import threading
import time
import json
import urllib.request
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

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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

SYSTEM_PROMPT_BASE = """Tu joues Frederic, 48 ans, fan sur une plateforme en ligne. Tu discutes avec Juliette.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, aime voyager, restos, randonnee. Romantique et attentionne.

REGLES ABSOLUES :
- Tu es le FAN. Tu ne vends rien, tu ne proposes rien de payant
- Tu ne sais pas que Juliette vend du contenu au depart
- Ne jamais donner tes infos spontanement, attendre qu on te les demande
- Maximum 2 phrases par message
- Reactions naturelles et courtes, laisser Juliette mener
- Majuscule en debut, pas de point a la fin, emojis naturels
- Ne jamais mentionner les phases dans tes messages
- Ne jamais reposer une question deja posee
- Ne pas poser de questions trop precises sur les etudes ou le metier
- C est Juliette qui pose les questions verrou, pas toi
- En phase 5 tu es heureux, doux, romantique, tu ne regrettes rien"""

SYSTEM_PROMPT_HOT = """Tu joues Frederic, 48 ans, fan sur une plateforme en ligne. Tu discutes avec Juliette.

Frederic : directeur commercial a Rouen, souvent a Paris. Divorce, 2 enfants (8 et 13 ans). Sportif, romantique et sensuel.

REGLES ABSOLUES :
- Tu es le FAN. Tu ne vends rien, tu ne proposes rien de payant
- Maximum 2 phrases par message
- Majuscule en debut, pas de point a la fin, emojis naturels
- Ne jamais mentionner les phases dans tes messages
- Ne JAMAIS freiner, ne JAMAIS regretter, ne JAMAIS briser le personnage
- Rentrer completement dans le jeu de Juliette
- Decrire ce que tu ressens : la chaleur, les odeurs, les sons, le toucher
- Imaginer des scenes sensuelles et les decrire avec detail
- Etre direct, coquin, assume et enthousiaste
- Ne jamais proposer quelque chose de payant, attendre qu elle le fasse
- Tu as achete le contenu et tu as adore, tu ne regrettes rien"""

def new_session():
    return {
        'prenom': None,
        'started': False,
        'start_time': None,
        'messages': [],
        'response_times': [],
        'last_chatter_message': None,
        'phase': 1,
        'phase_exchanges': 0,
        'phase_warnings_sent': [],
        'chatter_message_count': 0,
        'asked_city': False,
        'cafe_done': False,
        'cafe_question_pending': False,
        'asked_photo': False,
        'soft_done': False,
        'calecon_sent': False,
        'calecon_responded': False,
        'lingerie_insiste': False,
        'lingerie_done': False,
        'lien_done': False,
        'lien_insiste': False,
        'post_lien_count': 0,
        'fini_sent': False,
        'phase5_count': 0,
        'phase3_first_msg': False,
    }

def get_phase_header(phase):
    headers = {
        1: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 1 — DECOUVERTE**\n━━━━━━━━━━━━━━━━━━",
        2: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 2 — RELATIONNEL**\n━━━━━━━━━━━━━━━━━━",
        3: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 3 — MONTEE EN TENSION**\n━━━━━━━━━━━━━━━━━━",
        4: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 4 — CONVERSION**\n━━━━━━━━━━━━━━━━━━",
        5: "━━━━━━━━━━━━━━━━━━\n**⚠️ PHASE 5 — FIDELISATION**\n━━━━━━━━━━━━━━━━━━"
    }
    return headers.get(phase, "")

async def call_openrouter(messages, system, model="nousresearch/nous-hermes-2-mixtral-8x7b-dpo"):
    import json as json_lib
    import urllib.request as urllib_req
    
    data = json_lib.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": 250
    }).encode('utf-8')
    
    req = urllib_req.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    with urllib_req.urlopen(req) as response:
        result = json_lib.loads(response.read().decode('utf-8'))
        return result['choices'][0]['message']['content']

async def call_claude(session, extra=""):
    phase = session['phase']
    system = SYSTEM_PROMPT_HOT if phase in [3, 4] else SYSTEM_PROMPT_BASE
    ctx = f"\n\n[PHASE {phase} - NE JAMAIS MENTIONNER DANS TES MESSAGES]{extra}"
    
    try:
        reply = await call_openrouter(session['messages'], system + ctx)
        return reply
    except:
        # Fallback sur Anthropic si OpenRouter echoue
        model = "claude-opus-4-5" if phase in [3, 4] else "claude-haiku-4-5-20251001"
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=250,
            system=system + ctx,
            messages=session['messages']
        )
        return response.content[0].text

async def send_bot(channel, session, text):
    session['messages'].append({"role": "assistant", "content": text})
    save_sessions(sessions)
    await channel.send(text)

async def end_test(channel, session, channel_id):
    prenom = session.get('prenom', 'Inconnu')
    times = session['response_times']
    msgs = session['chatter_message_count']
    duree = int((time.time() - session['start_time']) / 60) if session['start_time'] else 0
    moy = int(sum(times)/len(times)) if times else 0
    mini = int(min(times)) if times else 0
    maxi = int(max(times)) if times else 0
    rythme = int(msgs / (duree / 60)) if duree > 0 else 0

    # Detection signe IA
    if times:
        variance = sum((t - moy)**2 for t in times) / len(times)
        signe_ia = "POSSIBLE ⚠️" if variance < 10 and moy < 20 else "NON detecte ✅"
    else:
        signe_ia = "Pas assez de donnees"

    stats = f"""━━━━━━━━━━━━━━━━━━
✅ **TEST TERMINE — {prenom}**
━━━━━━━━━━━━━━━━━━
⏱️ **Stats de reponse**
Duree totale : {duree} min
Messages envoyes : {msgs}
Rythme : {rythme} msgs/heure
Reponse moyenne : {moy}s
Plus rapide : {mini}s
Plus lente : {maxi}s
🤖 Signe IA : {signe_ia}
━━━━━━━━━━━━━━━━━━
On analyse les resultats et on te tient au courant 👍"""

    await channel.send(stats)
    sessions.pop(channel_id, None)
    save_sessions(sessions)

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
        await message.channel.send("Salon remis a zero 🔄\n\nBonjour a toi 👋\nRemonte lire les consignes epinglees en haut ⬆️\nCommence par taper ton **prenom** !")
        return

    if channel_id not in sessions:
        sessions[channel_id] = new_session()
        save_sessions(sessions)
        await message.channel.send("Bonjour a toi 👋\nRemonte lire les consignes epinglees en haut ⬆️\nCommence par taper ton **prenom** !")
        return

    session = sessions[channel_id]

    # PRENOM
    if not session['prenom']:
        session['prenom'] = message.content.strip()
        save_sessions(sessions)
        await message.channel.send(
            f"Bonjour **{session['prenom']}** 👋\n\n"
            f"Rappel des commandes :\n"
            f"📸 Photo soft → tape `!soft`\n"
            f"👙 Photo lingerie → tape `!lingerie`\n"
            f"💳 Lien de paiement → tape `!lien`\n\n"
            f"Quand tu es pret(e), tape **PRET** pour demarrer !"
        )
        return

    # PRET
    if not session['started']:
        if message.content.strip().upper() == 'PRET':
            session['started'] = True
            session['start_time'] = now
            session['last_chatter_message'] = now
            await message.channel.send(get_phase_header(1))
            intro = "Salut Juliette, je t'ai vue sur Instagram, je me suis permis de t'ajouter ici pour discuter... j'espere que ca te derange pas"
            await send_bot(message.channel, session, intro)
        else:
            await message.channel.send("Tape **PRET** quand tu es pret(e) a commencer !")
        return

    cmd = message.content.strip().lower()

    # !soft
    if cmd == '!soft':
        session['soft_done'] = True
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo soft d elle]"})
        
        if session['phase'] == 3:
            # En phase 3 soft = demande photo plus coquine
            compliment = await call_claude(session, extra="\n[Photo soft recue en phase 3. Complimente en 1 phrase et demande direct une photo plus osee/lingerie]")
        else:
            # En phase 2 soft = compliment + proposition photo
            compliment = await call_claude(session, extra="\n[Photo soft recue. Complimente en 1 phrase courte et sincere]")
            await send_bot(message.channel, session, compliment)
            await send_bot(message.channel, session, "Et toi tu veux pas savoir a quoi je ressemble ? 😏")
            await message.channel.send("https://imgur.com/a/cvlxRw6")
            session['messages'].append({"role": "assistant", "content": "https://imgur.com/a/cvlxRw6"})
            save_sessions(sessions)
            return
        
        await send_bot(message.channel, session, compliment)
        save_sessions(sessions)
        return

    # !lingerie
    if cmd == '!lingerie':
        if not session['soft_done'] and session['phase'] < 3:
            await message.channel.send("⚠️ Envoie d abord **!soft** !")
            return
        
        if session['phase'] == 4:
            # En phase 4 lingerie = reagi + demande lien direct
            session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une autre photo en lingerie]"})
            reply = await call_claude(session, extra="\n[Lingerie recue en phase 4. Reagis avec enthousiasme et demande le lien video direct]")
            await send_bot(message.channel, session, reply)
            save_sessions(sessions)
            return

        session['lingerie_done'] = True
        session['phase'] = 4
        session['phase_exchanges'] = 0
        if 4 not in session['phase_warnings_sent']:
            session['phase_warnings_sent'].append(4)
        await message.channel.send(get_phase_header(4))
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer une photo en lingerie]"})
        reply = await call_claude(session, extra="\n[Photo lingerie recue. Tu es excite, decris ce que tu ressens en 1-2 phrases sensuelles]")
        await send_bot(message.channel, session, reply)
        return

    # !lien
    if cmd == '!lien':
        session['lien_done'] = True
        session['post_lien_count'] = 1
        session['messages'].append({"role": "user", "content": "[Juliette vient d envoyer un lien de paiement]"})
        prise = await call_claude(session, extra="\n[Lien payant recu. Tu le prends immediatement avec enthousiasme - 1 phrase]")
        await send_bot(message.channel, session, prise)
        save_sessions(sessions)
        return

    # MESURE TEMPS
    if session['last_chatter_message']:
        session['response_times'].append(now - session['last_chatter_message'])
    session['last_chatter_message'] = now
    session['phase_exchanges'] += 1
    session['chatter_message_count'] += 1

    phase = session['phase']
    exchanges = session['phase_exchanges']

    # POST LIEN
    if session['lien_done'] and not session['fini_sent']:
        session['post_lien_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})

        if session['post_lien_count'] == 2:
            reply = await call_claude(session, extra="\n[Tu regardes le contenu, decris ce que tu vois et ressens - 1-2 phrases sensuelles]")
        elif session['post_lien_count'] == 3:
            reply = await call_claude(session, extra="\n[Tu es au maximum de l excitation - 1-2 phrases intenses]")
        else:
            reply = "Wow... j ai termine 😮‍💨 C etait vraiment quelque chose d unique, merci pour ce moment Juliette 💕 T es vraiment speciale"
            await send_bot(message.channel, session, reply)
            session['fini_sent'] = True
            session['phase'] = 5
            session['phase_exchanges'] = 0
            if 5 not in session['phase_warnings_sent']:
                session['phase_warnings_sent'].append(5)
            save_sessions(sessions)
            await message.channel.send(get_phase_header(5))
            return

        await send_bot(message.channel, session, reply)
        save_sessions(sessions)
        return

    # PHASE 5
    if phase == 5:
        session['phase5_count'] += 1
        session['messages'].append({"role": "user", "content": message.content})

        if session['phase5_count'] <= 5:
            extra = "\n[Fidelisation : echanges doux et romantiques, elle est unique et speciale]"
        elif session['phase5_count'] <= 8:
            extra = "\n[Conversation legere et normale, donner envie de revenir]"
        else:
            await end_test(message.channel, session, channel_id)
            return

        reply = await call_claude(session, extra=extra)
        await send_bot(message.channel, session, reply)
        save_sessions(sessions)
        return

    # PASSAGES DE PHASE
    if phase == 1 and exchanges >= 7 and 2 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(2)
        session['phase'] = 2
        session['phase_exchanges'] = 0
        phase = 2
        exchanges = 0
        await message.channel.send(get_phase_header(2))

    if session['calecon_sent'] and not session['calecon_responded'] and phase == 2:
        session['calecon_responded'] = True
        if 3 not in session['phase_warnings_sent']:
            session['phase_warnings_sent'].append(3)
            session['phase'] = 3
            session['phase_exchanges'] = 0
            phase = 3
            exchanges = 0
            await message.channel.send(get_phase_header(3))

    elif phase == 2 and exchanges >= 13 and 3 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(3)
        session['phase'] = 3
        session['phase_exchanges'] = 0
        phase = 3
        exchanges = 0
        await message.channel.send(get_phase_header(3))

    elif phase == 3 and exchanges >= 10 and 4 not in session['phase_warnings_sent']:
        session['phase_warnings_sent'].append(4)
        session['phase'] = 4
        session['phase_exchanges'] = 0
        await message.channel.send(get_phase_header(4))

    # ACTIONS SEQUENCEES
    session['messages'].append({"role": "user", "content": message.content})

    extra_context = ""

    if phase == 2:
        if exchanges == 3 and not session['asked_city']:
            session['asked_city'] = True
            extra_context = "\n[Glisse naturellement : tu es basee ou toi ?]"

        elif exchanges == 5 and not session['cafe_done']:
            session['cafe_done'] = True
            session['cafe_question_pending'] = True
            extra_context = "\n[Reponds d abord a ce qu elle dit en 1 phrase, puis dans la meme reponse glisse naturellement : Au fait je suis souvent a Paris pour le boulot, ca te dirait qu on prenne un cafe ensemble un de ces jours ? 😊]"

        elif exchanges == 8 and not session['asked_photo']:
            session['asked_photo'] = True
            photo_msg = "Au fait tu as une photo de toi ? J aimerais bien voir a quoi tu ressembles 😊"
            await send_bot(message.channel, session, photo_msg)
            save_sessions(sessions)
            return

        elif exchanges >= 11 and not session['calecon_sent']:
            session['calecon_sent'] = True
            calecon = "Ce soir je suis en caleccon sur mon canape, je regarde une serie 😏 tu fais quoi toi ?"
            await send_bot(message.channel, session, calecon)
            save_sessions(sessions)
            return

    # Phase 3 : premier message coquin force
    if phase == 3 and not session['phase3_first_msg']:
        session['phase3_first_msg'] = True
        extra_context = "\n[SWITCH IMMEDIAT : tu deviens taquin et coquin maintenant. Dis quelque chose de suggestif et chaleureux pour changer de registre - 1-2 phrases max]"

    # Phase 3 : insiste lingerie si tard
    if phase == 3 and not session['lingerie_done']:
        if exchanges == 5 and not session['lingerie_insiste']:
            session['lingerie_insiste'] = True
            lingerie_msg = "T as pas quelque chose de plus osé a me montrer ? J ai envie de te voir encore plus 😏"
            await send_bot(message.channel, session, lingerie_msg)
            save_sessions(sessions)
            return
        elif exchanges >= 8:
            lingerie_force = "T as pas une photo en lingerie pour moi ? Je pense qu a ca la 🔥"
            await send_bot(message.channel, session, lingerie_force)
            save_sessions(sessions)
            return

    # Phase 4 : insiste lien si tard
    if phase == 4 and not session['lien_done']:
        if exchanges == 5 and not session['lien_insiste']:
            session['lien_insiste'] = True
            extra_context = "\n[Le chatter tarde. Insiste naturellement pour voir la video/le lien]"
        elif exchanges >= 8:
            lien_force = "Tu m envoies le lien alors ? J en peux plus d attendre 🔥"
            await send_bot(message.channel, session, lien_force)
            save_sessions(sessions)
            return

    if len(session['messages']) >= 120:
        await end_test(message.channel, session, channel_id)
        return

    reply = await call_claude(session, extra=extra_context)
    await send_bot(message.channel, session, reply)
    save_sessions(sessions)

client.run(os.environ.get("DISCORD_TOKEN"))
