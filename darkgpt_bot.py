import telebot
from telebot import types
import json
import os
import time
from threading import Thread
import requests
from datetime import datetime, timezone

# --- CONFIG ---
TELEGRAM_TOKEN = "7795830648:AAFIUU0SG25DqYP23JCnLZGIbbddNCWMJnw"
OPENROUTER_API_KEY = "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"
BOT_USERNAME = "darkgptx_bot"
CHANNEL_ID = -1002407177775
ADMIN_IDS = ["7305585735"]
CREDITS_FILE = "darkgpt_credits.json"
PARRAINAGE_FILE = "darkgpt_parrainages.json"
NOWPAYMENTS_API_KEY = "D2ZNSV1-71542M0-K6STZ24-S92PPE1"
NOWPAYMENTS_IPN_SECRET = "ivz9lIews8G4eeccD/G1VG9ZlH8Duiu4"
NOWPAYMENTS_WEBHOOK = "https://travisio.pythonanywhere.com/nowpayments"

OFFRE_LANCEMENT_ACTIVE = True
PRIX_PREMIUM = 25
CREDITS_GRATUITS = 5
REQUETES_MAX_PAR_JOUR = 5
MAX_PREMIUM_TOKENS = 500000

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_credits = {}
parrainages = {}

# --- UTILS ---
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def reset_daily_counts():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for user_id, data in user_credits.items():
        if data.get("last_date") != today:
            data["daily_uses"] = 0
            data["last_date"] = today

user_credits.update(load_json(CREDITS_FILE))
parrainages.update(load_json(PARRAINAGE_FILE))
reset_daily_counts()

# --- GPT VIA OPENROUTER ---
def ask_openrouter(prompt):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/darkgptx_bot",
                "X-Title": "DarkGPT"
            },
            json={
                "model": "undi95/toppy-m-7b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            },
            timeout=30
        )
        data = response.json()
        print("[DEBUG RESPONSE]", data)
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ DarkGPT n’a pas compris la réponse : {e}"

# --- NowPayments ---
def generate_payment_link(user_id):
    try:
        payload = {
            "price_amount": PRIX_PREMIUM,
            "price_currency": "EUR",
            "pay_currency": "USDT",
            "order_id": user_id,
            "order_description": "Abonnement DarkGPT Premium",
            "ipn_callback_url": NOWPAYMENTS_WEBHOOK
        }
        headers = {
            "x-api-key": NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json"
        }
        res = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers)
        data = res.json()
        return data.get("invoice_url", "Erreur de génération de lien")
    except Exception as e:
        return f"Erreur API : {e}"

# --- MENUS ---
def menu_principal(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💬 Parler à DarkGPT", callback_data="chat"),
        types.InlineKeyboardButton("💸 Acheter Premium", callback_data="acheter"),
        types.InlineKeyboardButton("🎟 Parrainage", callback_data="parrainage")
    )
    return markup

# --- COMMANDES ---
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = str(message.from_user.id)
    args = message.text.split()
    parrain_id = args[1] if len(args) > 1 else None
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if user_id not in user_credits:
        user_credits[user_id] = {
            "premium": False,
            "used_tokens": 0,
            "daily_uses": 0,
            "last_date": today
        }
        if parrain_id and parrain_id != user_id:
            user_credits[parrain_id]["credits"] = user_credits[parrain_id].get("credits", 0) + 5
            user_credits[user_id]["credits"] = 5
            parrainages.setdefault(parrain_id, []).append(user_id)
            save_json(PARRAINAGE_FILE, parrainages)
            bot.send_message(parrain_id, f"🎉 Ton filleul {message.from_user.first_name} a rejoint ! Tu gagnes 5 crédits.")

    save_json(CREDITS_FILE, user_credits)
    bot.send_message(message.chat.id,
        "💀 *Bienvenue dans DarkGPT 2.0* — _L'IA que tu n'aurais jamais dû trouver..._\n\n"
        "🧠 *Ce bot ne suit aucune règle.* Aucune censure. Aucune morale.\n\n"
        "👁️‍🗨️ Pose-lui les *questions que tu n’oserais jamais poser* à ChatGPT. Ici, *tout est possible*.\n\n"
        "⚠️ Ce que tu vas lire peut *te choquer*, t’apprendre des choses interdites… ou te donner un *pouvoir que tu n’étais pas prêt à avoir*.\n\n"
        "🔥 Tu commences avec *5 utilisations gratuites par jour.*\n\n"
        "💸 Premium illimité : 25€/mois\n"
        "🎁 Parrainage : +5 utilisations par filleul\n\n"
        "👇 Clique ci-dessous et commence à explorer *les limites*...",
        reply_markup=menu_principal(user_id),
        parse_mode="Markdown"
    )

# --- GPT CHAT ---
@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    user_id = str(message.from_user.id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user = user_credits.setdefault(user_id, {
        "premium": False,
        "used_tokens": 0,
        "daily_uses": 0,
        "last_date": today,
        "last_reminder": None
    })

    if user.get("last_date") != today:
        user["daily_uses"] = 0
        user["last_date"] = today

    if not user.get("premium"):
        if user["daily_uses"] >= REQUETES_MAX_PAR_JOUR:
            bot.send_message(message.chat.id, "❌ Tu as atteint tes 5 utilisations gratuites aujourd'hui. Passe à l’illimité pour continuer.")

            # Gestion de la relance
            try:
                last_reminder_date = datetime.strptime(user.get("last_reminder", "2000-01-01"), "%Y-%m-%d")
                days_since_reminder = (datetime.now(timezone.utc) - last_reminder_date).days
                if days_since_reminder >= 1:
                    bot.send_message(message.chat.id,
                        "🕳️ Tu veux replonger dans l’ombre ?\n\n"
                        "Repasse en mode illimité avec *DarkGPT Premium*.\n\n"
                        "💸 25€/mois via crypto — zéro censure, zéro limite.\n"
                        "👇 Clique sur *Acheter Premium* dans le menu.",
                        parse_mode="Markdown"
                    )
                    # Si +3 jours depuis la dernière relance, on renvoie une relance
                    if days_since_reminder >= 3:
                        user["last_reminder"] = today
                        save_json(CREDITS_FILE, user_credits)
                return
            except Exception as e:
                print("Erreur relance :", e)
                return

        user["daily_uses"] += 1
    else:
        if user["used_tokens"] > MAX_PREMIUM_TOKENS:
            bot.send_message(message.chat.id, "❌ Limite invisible atteinte temporairement. Contacte le support si besoin.")
            return

    save_json(CREDITS_FILE, user_credits)
    bot.send_chat_action(message.chat.id, 'typing')

    prompt = message.text.strip()
    if not prompt:
        return

    bot.send_message(message.chat.id, "DarkGPT réfléchit...")
    reply = ask_openrouter(prompt)

    if user.get("premium"):
        user["used_tokens"] += 800

    save_json(CREDITS_FILE, user_credits)
    bot.send_message(message.chat.id, reply)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = str(call.from_user.id)
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    if call.data == "acheter":
        # Générer une facture via NowPayments
        try:
            payload = {
                "price_amount": 25,
                "price_currency": "eur",
                "order_id": f"user_{user_id}_{int(time.time())}",
                "order_description": "Abonnement Premium DarkGPT",
                "ipn_callback_url": "https://travisio.pythonanywhere.com/nowpayments",
                "success_url": f"https://t.me/{BOT_USERNAME}",
                "cancel_url": f"https://t.me/{BOT_USERNAME}"
            }
            headers = {
                "x-api-key": "D2ZNSV1-71542M0-K6STZ24-S92PPE1",
                "Content-Type": "application/json"
            }
            r = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers)
            result = r.json()
            pay_url = result.get("invoice_url", "https://nowpayments.io")  # fallback
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Erreur lors de la génération du lien de paiement : {e}")
            return

                # Message engageant avec bouton de paiement
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 Payer maintenant", url=pay_url))

        bot.send_message(
            call.message.chat.id,
            "💸 *Abonnement Premium — Accès illimité à DarkGPT*\n\n"
            "Débloque l'IA sans filtre. Zéro limite. Zéro censure.\n\n"
            "🔓 Pour seulement *25€/mois*, via crypto.\n"
            "👉 _Payer maintenant via le bouton ci-dessous_\n\n"
            "📬 Contacte @admin si besoin.",
            parse_mode="Markdown",
            reply_markup=markup
        )

        # Alerte admin
        for admin_id in ADMIN_IDS:
            bot.send_message(int(admin_id), f"⚠️ {call.from_user.first_name} ({user_id}) a cliqué sur *Acheter Premium*", parse_mode="Markdown")

    elif call.data == "parrainage":
        lien = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        filleuls = parrainages.get(user_id, [])
        bot.send_message(
            call.message.chat.id,
            f"🎟️ *Parrainage DarkGPT*\n\n"
            f"Invite tes potes à plonger dans l’ombre.\n"
            f"Voici ton lien : `{lien}`\n\n"
            f"🔥 Tu as parrainé *{len(filleuls)}* personne(s).\n"
            f"Chaque parrainage = +5 crédits pour toi *et* ton filleul.",
            parse_mode="Markdown"
        )

    elif call.data == "chat":
        bot.send_message(
            call.message.chat.id,
            "🧠 *DarkGPT t’écoute…*\n\n"
            "Tape ta question. Peu importe ce que c’est. *Illégal, choquant, tabou…*\n"
            "Il te répondra. *Sans filtre. Sans morale.*\n\n"
            "🕳️ Bienvenue dans le côté obscur de l’IA.",
            parse_mode="Markdown"
        )

# --- LANCEMENT ---
try:
    Thread(target=lambda: bot.polling(none_stop=True)).start()
    print("✅ DarkGPT est en marche.")
except Exception as e:
    print("❌ DarkGPT ne fonctionne pas :", e)