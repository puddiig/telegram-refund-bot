import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from datetime import datetime
from flask import Flask
from threading import Thread
import asyncio

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# Token dan Spreadsheet
BOT_TOKEN = '7596288746:AAFOAXx2OOKvXgE8PzcfjgaqdTJ_lAiJDFo'
SPREADSHEET_ID = '1tdPwCEKg_QqApq6nlyG5VjKqmJ8VKWOeH0rEfVoN7fg'
ADMIN_ID = 8005266733  # Telegram Admin

# Setup Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name('olaa-refund-f5d486f2dc3a.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# Setup Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Server Flask is Running!"

# State conversation
(NAMA, EMAIL, PASSWORD, HARGA, TANGGAL_BELI, TANGGAL_BACKFREE, DURASI_HARI, KLAIM, E_WALLET, NO_EWALLET, KONFIRMASI, LANJUT) = range(12)

user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Masukkan nama Anda:")
    return NAMA

async def nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id] = {"nama": update.message.text}
    await update.message.reply_text("Masukkan email Anda:")
    return EMAIL

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id]["email"] = update.message.text
    await update.message.reply_text("Masukkan password Anda:")
    return PASSWORD

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id]["password"] = update.message.text
    await update.message.reply_text("Masukkan harga akun:")
    return HARGA

async def harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Harga harus berupa angka.")
        return HARGA

    harga = int(text)
    if harga not in [12000, 15000, 18000]:
        await update.message.reply_text("Harga tidak valid. Harap pilih 12000, 15000, atau 18000.")
        return HARGA

    user_data_store[update.effective_chat.id]["harga"] = harga
    await update.message.reply_text("Masukkan tanggal beli (format: DD-MM-YYYY):")
    return TANGGAL_BELI

async def tanggal_beli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id]["tanggal_beli"] = update.message.text
    await update.message.reply_text("Masukkan tanggal backfree (format: DD-MM-YYYY):")
    return TANGGAL_BACKFREE

async def tanggal_backfree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tgl_beli = datetime.strptime(user_data_store[update.effective_chat.id]["tanggal_beli"], "%d-%m-%Y")
        tgl_refund = datetime.strptime(update.message.text, "%d-%m-%Y")
        if tgl_refund < tgl_beli:
            await update.message.reply_text("Tanggal backfree tidak boleh lebih awal dari tanggal beli. Silakan masukkan ulang.")
            return TANGGAL_BACKFREE
        user_data_store[update.effective_chat.id]["tanggal_backfree"] = update.message.text
    except ValueError:
        await update.message.reply_text("Format tanggal salah. Harap gunakan format DD-MM-YYYY.")
        return TANGGAL_BACKFREE

    await update.message.reply_text("Masukkan durasi akun (dalam hari):")
    return DURASI_HARI

async def durasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        durasi_input = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Durasi harus berupa angka.")
        return DURASI_HARI

    harga = user_data_store[update.effective_chat.id]["harga"]
    if (harga == 12000 and durasi_input != 30) or (harga == 15000 and durasi_input != 60) or (harga == 18000 and durasi_input != 90):
        await update.message.reply_text(f"Durasi harus sesuai dengan harga {harga}.")
        return DURASI_HARI

    user_data_store[update.effective_chat.id]["durasi_hari"] = durasi_input
    await update.message.reply_text("Masukkan jumlah klaim garansi:")
    return KLAIM

async def klaim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Jumlah klaim harus berupa angka.")
        return KLAIM

    user_data_store[update.effective_chat.id]["klaim"] = int(text)
    keyboard = [["DANA", "OVO", "GoPay", "ShopeePay"]]
    await update.message.reply_text("Pilih e-wallet untuk refund:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return E_WALLET

async def ewallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pilihan = ["DANA", "OVO", "GoPay", "ShopeePay"]
    text = update.message.text
    if text not in pilihan:
        await update.message.reply_text("Silakan pilih e-wallet yang tersedia.")
        return E_WALLET

    user_data_store[update.effective_chat.id]["e_wallet"] = text
    await update.message.reply_text("Masukkan nomor e-wallet:")
    return NO_EWALLET

async def no_ewallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    no = update.message.text
    if not no.isdigit() or not no.startswith("08"):
        await update.message.reply_text("Nomor e-wallet harus berupa angka dan dimulai dengan '08'.")
        return NO_EWALLET

    user_data_store[update.effective_chat.id]["no_ewallet"] = no
    data = user_data_store[update.effective_chat.id]

    ringkasan = f"""
Konfirmasi Data Refund:
Nama: {data["nama"]}
Email: {data["email"]}
Password: {data["password"]}
Harga: {data["harga"]}
Tanggal Beli: {data["tanggal_beli"]}
Tanggal Backfree: {data["tanggal_backfree"]}
Durasi: {data["durasi_hari"]} hari
Klaim: {data["klaim"]}
E-Wallet: {data["e_wallet"]}
No E-Wallet: {data["no_ewallet"]}

Ketik 'ya' untuk lanjut atau 'tidak' untuk membatalkan.
"""
    await update.message.reply_text(ringkasan)
    return KONFIRMASI

async def konfirmasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "ya":
        await update.message.reply_text("Dibatalkan.")
        return ConversationHandler.END

    data = user_data_store[update.effective_chat.id]
    tgl_beli = datetime.strptime(data["tanggal_beli"], "%d-%m-%Y")
    tgl_refund = datetime.strptime(data["tanggal_backfree"], "%d-%m-%Y")
    pakai = (tgl_refund - tgl_beli).days
    sisa = max(0, data["durasi_hari"] - pakai)

    if pakai < 7:
        pengali = 0.8
    elif data["klaim"] == 0:
        pengali = 0.7
    elif 1 <= data["klaim"] <= 2:
        pengali = 0.6
    elif data["klaim"] == 3:
        pengali = 0.5
    else:
        pengali = 0.4

    refund = round(data["harga"] * sisa / data["durasi_hari"] * pengali)

    try:
        sheet.append_row([
            data["nama"], data["email"], data["password"],
            data["tanggal_beli"], data["tanggal_backfree"],
            data["durasi_hari"], sisa, pengali, refund,
            data["e_wallet"], data["no_ewallet"],
            datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        ])
    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan saat menyimpan data: {e}")
        return ConversationHandler.END

    notif = f"""
REFUND BARU DITERIMA:
Nama: {data["nama"]}
Email: {data["email"]}
Refund: Rp {refund}
E-Wallet: {data["e_wallet"]} - {data["no_ewallet"]}
"""
    await context.bot.send_message(chat_id=ADMIN_ID, text=notif)

    await update.message.reply_text(f"Pengajuan refund Anda telah diproses. Total refund: Rp {refund}")
    keyboard = [["ya", "tidak"]]
    await update.message.reply_text("Apakah Anda ingin mengajukan refund lain?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return LANJUT

async def lanjut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "ya":
        await update.message.reply_text("Masukkan nama Anda:")
        return NAMA
    else:
        await update.message.reply_text("Terima kasih sudah mengajukan refund, harap menunggu sampai dana masuk ke rekeningmu ya!")
        return ConversationHandler.END

def run_telegram_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, nama)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
            HARGA: [MessageHandler(filters.TEXT & ~filters.COMMAND, harga)],
            TANGGAL_BELI: [MessageHandler(filters.TEXT & ~filters.COMMAND, tanggal_beli)],
            TANGGAL_BACKFREE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tanggal_backfree)],
            DURASI_HARI: [MessageHandler(filters.TEXT & ~filters.COMMAND, durasi)],
            KLAIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, klaim)],
            E_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, ewallet)],
            NO_EWALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, no_ewallet)],
            KONFIRMASI: [MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi)],
            LANJUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, lanjut)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app_bot.add_handler(conv_handler)
    asyncio.run(app_bot.run_polling())

if __name__ == '__main__':
    Thread(target=run_telegram_bot).start()
    app.run(host='0.0.0.0', port=2597)
