import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from sqlalchemy import text
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import tempfile
import numpy as np
from PIL import Image
import base64

# ==========================================
# ⚙️ KONFIGURASI TELEGRAM & ADMIN
# ==========================================
BOT_TOKEN = "8433442999:AAGjTv0iZEm_xtvlQTUBT11PUyxUYMtGxFQ"
CHAT_ID = "-1003692690153"
PASSWORD_ADMIN = "admin123"

# --- FUNGSI KIRIM NOTIFIKASI ---
def kirim_notifikasi_telegram(pesan):
    try:
        if "GANTI" in BOT_TOKEN: return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.get(url, params=params)
        return True
    except: return False

# --- FUNGSI MEMBUAT PDF ---
def create_pdf(ticket_data, image_file, user_sig, tech_sig, catatan_teknisi):
    pdf = FPDF()
    pdf.add_page()
    
    # Header PDF
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, "BERITA ACARA PERBAIKAN ALAT MEDIS", ln=True, align='C')
    pdf.set_font("Times", 'I', 10)
    pdf.cell(0, 10, "RS CINTA KASIH TZU CHI - DEPARTEMEN ATEM", ln=True, align='C')
    pdf.line(10, 30, 200, 30); pdf.ln(10)
    
    # Isi Laporan
    pdf.set_font("Times", '', 12)
    fields = [
        f"No. Tiket: {ticket_data['ID Tiket']}",
        f"Tanggal: {ticket_data['Waktu Lapor']}",
        f"Ruangan: {ticket_data['Ruangan']}",
        f"Pelapor: {ticket_data['Pelapor']}"
    ]
    for f in fields: pdf.cell(0, 8, f, ln=True)
    pdf.ln(5)
    
    pdf.set_font("Times", 'B', 12); pdf.cell(0, 10, "DETAIL KERUSAKAN", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 8, f"Alat: {ticket_data['Nama Alat']} ({ticket_data['Nomor Serial']})\nKeluhan: {ticket_data['Keluhan']}")
    pdf.ln(5)
    
    pdf.set_font("Times", 'B', 12); pdf.cell(0, 10, "TINDAKAN TEKNISI", ln=True)
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 8, f"Teknisi: {ticket_data['Teknisi']}\nSolusi: {catatan_teknisi}")
    pdf.ln(10)
    
    # Area Tanda Tangan
    if pdf.get_y() > 200: pdf.add_page()
    y_start = pdf.get_y()
    
    # TTD Teknisi (Kiri)
    pdf.set_xy(10, y_start)
    pdf.set_font("Times", '', 10); pdf.cell(80, 5, "Dikerjakan Oleh,", ln=True, align='C')
    if tech_sig is not None:
        img_data = tech_sig.astype(np.uint8); im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            im.save(tmp.name); pdf.image(tmp.name, x=30, y=y_start+5, w=40)
    pdf.set_xy(10, y_start+35); pdf.set_font("Times", 'B', 10); pdf.cell(80, 5, f"({ticket_data['Teknisi']})", ln=True, align='C')

    # TTD User (Kanan)
    pdf.set_xy(110, y_start)
    pdf.set_font("Times", '', 10); pdf.cell(80, 5, "Mengetahui / User,", ln=True, align='C')
    if user_sig is not None:
        img_data = user_sig.astype(np.uint8); im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            im.save(tmp.name); pdf.image(tmp.name, x=130, y=y_start+5, w=40)
    pdf.set_xy(110, y_start+35); pdf.set_font("Times", 'B', 10); pdf.cell(80, 5, f"({ticket_data['Pelapor']})", ln=True, align='C')

    # Lampiran Foto
    if image_file:
        pdf.add_page(); pdf.set_font("Times", 'B', 14); pdf.cell(0, 10, "LAMPIRAN DOKUMENTASI", ln=True, align='C')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_file.getvalue()); pdf.image(tmp.name, x=15, y=30, w=180)

    return pdf.output(dest="S").encode("latin1")

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Tzu Chi MedFix", page_icon="🏥", layout="wide")
st.markdown("""
<style>
    .stButton>button { width: 100%; height: 3em; font-weight: bold; }
    .emergency-box { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 10px; text-align: center; animation: blinker 1s infinite; }
    .status-otw { background-color: #ffd700; color: black; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    .status-pending { background-color: #6c757d; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0.8; } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🚀 KONEKSI DATABASE NEON
# ==========================================
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS laporan (
                "ID Tiket" TEXT,
                "Waktu Lapor" TEXT,
                "Pelapor" TEXT,
                "Ruangan" TEXT,
                "Nama Alat" TEXT,
                "Nomor Serial" TEXT,
                "Keluhan" TEXT,
                "Prioritas" TEXT,
                "Status" TEXT,
                "Teknisi" TEXT,
                "Catatan" TEXT,
                "PDF_File" TEXT
            );
        """))
        s.commit()

init_db()

# --- FUNGSI LOAD & SAVE (DIPERBAIKI) ---

@st.cache_data(ttl=10)
def load_data():
    try:
        # ttl=0 MEMAKSA AMBIL DATA BARU (Agar update real-time)
        df = conn.query('SELECT * FROM laporan;', ttl=0)
        if 'PDF_File' not in df.columns: df['PDF_File'] = None
        return df
    except Exception as e:
        return pd.DataFrame(columns=["ID Tiket","Waktu Lapor","Pelapor","Ruangan","Nama Alat","Nomor Serial","Keluhan","Prioritas","Status","Teknisi","Catatan","PDF_File"])

# PERBAIKAN: Fungsi save_data ditaruh di level paling luar agar dikenali
def save_data(df):
    try:
        df.to_sql('laporan', conn.engine, if_exists='replace', index=False)
        load_data.clear() # Hapus cache agar data di layar langsung berubah
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")

# ==========================================
# 🏥 MENU NAVIGASI UTAMA
# ==========================================
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Menu", ["📝 Buat Laporan", "🔍 Cek Status Laporan", "🔧 Dashboard Teknisi", "🔐 Admin"])

# --- MENU 1: BUAT LAPORAN ---
if menu == "📝 Buat Laporan":
    darurat = st.sidebar.toggle("🚨 MODE DARURAT")
    if darurat:
        st.markdown('<div class="emergency-box">🚨 FORMULIR DARURAT 🚨</div>', unsafe_allow_html=True)
        with st.form("f1"):
            loc = st.selectbox("LOKASI:", ["ICU","IGD","OT","NICU","Rawat Inap","Radiologi","Hemodialisa"])
            if st.form_submit_button("🚨 PANGGIL TEKNISI"):
                df = load_data()
                new_id = f"URGENT-{len(df)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = {"ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": "DARURAT", "Ruangan": loc, "Nama Alat": "DARURAT", "Nomor Serial": "-", "Keluhan": "DARURAT", "Prioritas": "EMERGENCY", "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                kirim_notifikasi_telegram(f"🚨 *SOS!* {loc}\nID: {new_id}")
                st.error(f"Sinyal Terkirim ke {loc}!")
    else:
        st.title("📝 Lapor Kerusakan")
        with st.form("f2"):
            c1, c2 = st.columns(2)
            with c1: pelapor = st.text_input("Nama Pelapor"); loc = st.selectbox("Lokasi", ["ICU","IGD","OT","Rawat Inap","Poli","Radiologi"])
            with c2: alat = st.text_input("Nama Alat"); sn = st.text_input("SN Alat"); prio = st.selectbox("Prioritas", ["Normal", "High (Urgent)"])
            kel = st.text_area("Keluhan / Kronologi")
            if st.form_submit_button("Kirim Laporan"):
                df = load_data()
                new_id = f"TC-{len(df)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = {"ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": pelapor, "Ruangan": loc, "Nama Alat": alat, "Nomor Serial": sn if sn else "-", "Keluhan": kel, "Prioritas": prio, "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                kirim_notifikasi_telegram(f"📝 *Tiket:* {new_id}\n📍 {loc} - {alat}\n⚠️ {prio}\n *Keluhan: * {kel}")
                st.success(f"Terkirim! ID: {new_id}")

# --- MENU 2: CEK STATUS & DOWNLOAD ---
elif menu == "🔍 Cek Status Laporan":
    st.title("🔍 Status Laporan")
    if st.button("Refresh"): st.rerun()
    df = load_data()
    
    if not df.empty:
