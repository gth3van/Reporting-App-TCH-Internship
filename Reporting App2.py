import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from sqlalchemy import text # Library SQL
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import tempfile
import numpy as np
from PIL import Image

# ==========================================
# ⚙️ KONFIGURASI TELEGRAM & ADMIN
# ==========================================
BOT_TOKEN = "8433442999:AAGjTv0iZEm_xtvlQTUBT11PUyxUYMtGxFQ"
CHAT_ID = "-1003692690153"
PASSWORD_ADMIN = "admin123"

# --- FUNGSI KIRIM PESAN ---
def kirim_notifikasi_telegram(pesan):
    try:
        if "GANTI" in BOT_TOKEN: return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.get(url, params=params)
        return True
    except: return False

# --- FUNGSI PDF ---
def create_pdf(ticket_data, image_file, signature_img, catatan_teknisi):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BERITA ACARA PERBAIKAN ALAT MEDIS", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, "RS CINTA KASIH TZU CHI - DEPARTEMEN ATEM", ln=True, align='C')
    pdf.line(10, 30, 200, 30); pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    fields = [
        f"No. Tiket: {ticket_data['ID Tiket']}",
        f"Tanggal: {ticket_data['Waktu Lapor']}",
        f"Ruangan: {ticket_data['Ruangan']}",
        f"Pelapor: {ticket_data['Pelapor']}"
    ]
    for f in fields: pdf.cell(0, 8, f, ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "DETAIL KERUSAKAN", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, f"Alat: {ticket_data['Nama Alat']} ({ticket_data['Nomor Serial']})\nKeluhan: {ticket_data['Keluhan']}")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "TINDAKAN TEKNISI", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, f"Teknisi: {ticket_data['Teknisi']}\nSolusi: {catatan_teknisi}")
    pdf.ln(5)
    
    if image_file:
        pdf.add_page(); pdf.cell(0, 10, "FOTO BUKTI", ln=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_file.getvalue())
            pdf.image(tmp.name, x=10, y=30, w=100)
            
    if signature_img is not None:
        pdf.ln(10); pdf.cell(0, 10, "Tanda Tangan User:", ln=True)
        img_data = signature_img.astype(np.uint8)
        im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
            im.save(tmp_sig.name)
            pdf.image(tmp_sig.name, w=50)

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
# 🚀 KONEKSI DATABASE POSTGRESQL (NEON)
# ==========================================
# Koneksi tipe SQL (bukan GSheets lagi)
conn = st.connection("postgresql", type="sql")

def init_db():
    # Fungsi ini untuk membuat Tabel otomatis jika belum ada di Neon
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
                "Catatan" TEXT
            );
        """))
        s.commit()

# Panggil fungsi init sekali di awal
init_db()

def load_data():
    # Ambil semua data dari SQL. ttl=0 aman di SQL karena servernya kuat.
    try:
        df = conn.query('SELECT * FROM laporan;', ttl=0)
        return df
    except:
        return pd.DataFrame(columns=["ID Tiket","Waktu Lapor","Pelapor","Ruangan","Nama Alat","Nomor Serial","Keluhan","Prioritas","Status","Teknisi","Catatan"])

def save_data(df):
    # Simpan data ke SQL dengan cara "Timpa Tabel Lama" (Simplest way for intern project)
    # if_exists='replace' artinya tabel lama dihapus, diganti data baru dari 'df'
    df.to_sql('laporan', conn.engine, if_exists='replace', index=False)

# --- SIDEBAR ---
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Menu", ["📝 Buat Laporan", "🔍 Cek Status", "🔧 Dashboard Teknisi", "🔐 Admin"])

# ================= MENU 1: LAPOR =================
if menu == "📝 Buat Laporan":
    darurat = st.sidebar.toggle("🚨 MODE DARURAT")
    if darurat:
        st.markdown('<div class="emergency-box">🚨 FORMULIR DARURAT 🚨</div>', unsafe_allow_html=True)
        with st.form("f1"):
            loc = st.selectbox("LOKASI:", ["ICU","IGD","OK","NICU","Rawat Inap","Radiologi","Hemodialisa"])
            if st.form_submit_button("🚨 PANGGIL TEKNISI"):
                df = load_data()
                new_id = f"URGENT-{len(df)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = {"ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": "DARURAT", "Ruangan": loc, "Nama Alat": "DARURAT", "Nomor Serial": "-", "Keluhan": "DARURAT", "Prioritas": "EMERGENCY", "Status": "OPEN", "Teknisi": "-", "Catatan": "-"}
                # Cara nambah data di Pandas:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                kirim_notifikasi_telegram(f"🚨 *SOS!* {loc}\nID: {new_id}")
                st.error(f"Sinyal Terkirim ke {loc}!")
    else:
        st.title("📝 Lapor Rutin")
        with st.form("f2"):
            c1, c2 = st.columns(2)
            with c1: pelapor = st.text_input("Nama"); loc = st.selectbox("Lokasi", ["ICU","IGD","OK","Rawat Inap","Poli","Radiologi"])
            with c2: alat = st.text_input("Alat"); sn = st.text_input("SN"); prio = st.selectbox("Prio", ["Normal", "High (Urgent)"])
            kel = st.text_area("Keluhan")
            if st.form_submit_button("Kirim"):
                df = load_data()
                new_id = f"TC-{len(df)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = {"ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": pelapor, "Ruangan": loc, "Nama Alat": alat, "Nomor Serial": sn if sn else "-", "Keluhan": kel, "Prioritas": prio, "Status": "OPEN", "Teknisi": "-", "Catatan": "-"}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                kirim_notifikasi_telegram(f"📝 *Tiket:* {new_id}\n📍 {loc} - {alat}\n⚠️ {prio}")
                st.success(f"Terkirim! ID: {new_id}")

# ================= MENU 2: STATUS =================
elif menu == "🔍 Cek Status":
    st.title("🔍 Status Laporan")
    if st.button("Refresh"): st.rerun()
    df = load_data()
    if not df.empty:
        df = df[df['Status'] != 'DONE'].sort_values(by='Waktu Lapor', ascending=False)
        for i, r in df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([1,3,2])
                with c1: 
                    if r['Prioritas']=='EMERGENCY': st.error("SOS")
                    elif r['Prioritas']=='High (Urgent)': st.warning("HIGH")
                    else: st.info("NOR")
                with c2: st.write(f"**{r['Ruangan']}** - {r['Nama Alat']}"); st.caption(f"{r['ID Tiket']} | {r['Pelapor']}")
                with c3: 
                    if r['Status']=='OPEN': st.write("⏳ Menunggu")
                    elif r['Status']=='ON PROGRESS': st.markdown(f'<div class="status-otw">🏃 {r["Teknisi"]} OTW</div>', unsafe_allow_html=True)
                    elif r['Status']=='PENDING': st.markdown(f'<div class="status-pending">⏳ PENDING</div>', unsafe_allow_html=True)

# ================= MENU 3: TEKNISI =================
elif menu == "🔧 Dashboard Teknisi":
    st.title("🔧 Dashboard ATEM")
    if st.button("🔄 Refresh Data"): st.rerun()
    df = load_data()
    if not df.empty:
        # TIKET MASUK
        st.subheader("📥 Tiket Masuk")
        prio_map = {"EMERGENCY":0, "High (Urgent)":1, "Normal":2}
        df['sort'] = df['Prioritas'].map(prio_map)
        open_t = df[df['Status']=='OPEN'].sort_values('sort')
        
        if open_t.empty: st.info("Tidak ada tiket baru.")
        else:
            for i, r in open_t.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2,3,2])
                    with c1:
                        if r['Prioritas']=='EMERGENCY': st.error(f"🚨 {r['Ruangan']}")
                        elif r['Prioritas']=='High (Urgent)': st.warning(f"⚡ {r['Ruangan']}")
                        else: st.info(f"🟢 {r['Ruangan']}")
                        st.caption(r['Nama Alat'])
                    with c2: st.write(r['Keluhan']); st.caption(f"Pelapor: {r['Pelapor']}")
                    with c3:
                        tek = st.selectbox("Teknisi", ["Budi","Andi","Siti"], key=f"s{r['ID Tiket']}")
                        if st.button("AMBIL", key=f"b{r['ID Tiket']}", type="primary"):
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='ON PROGRESS'
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Teknisi']=tek
                            save_data(df)
                            kirim_notifikasi_telegram(f"✅ {r['ID Tiket']} diambil {tek}")
                            st.rerun()
        
        st.markdown("---")
        # SEDANG DIKERJAKAN
        st.subheader("🛠 Sedang Dikerjakan")
        prog_t = df[df['Status']=='ON PROGRESS']
        for i, r in prog_t.iterrows():
            with st.container(border=True):
                st.info(f"🔧 {r['ID Tiket']} - {r['Nama Alat']} ({r['Ruangan']})")
                cat = st.text_area(f"Laporan ({r['ID Tiket']})", key=f"c{r['ID Tiket']}")
                c1, c2 = st.columns(2)
                with c1: cam = st.camera_input("Foto", key=f"f{r['ID Tiket']}")
                with c2: st.write("TTD User:"); ttd = st_canvas(height=100, width=200, key=f"t{r['ID Tiket']}")
                
                if st.button("✅ SELESAI", key=f"d{r['ID Tiket']}", type="primary"):
                    if ttd.image_data is None: st.error("Butuh TTD!")
                    else:
                        df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='DONE'
                        df.loc[df['ID Tiket']==r['ID Tiket'], 'Catatan']=cat
                        save_data(df)
                        pdf = create_pdf(r, cam, ttd.image_data, cat)
                        kirim_notifikasi_telegram(f"🎉 {r['ID Tiket']} SELESAI.")
                        st.download_button("📥 Unduh Berita Acara", pdf, f"BA_{r['ID Tiket']}.pdf")
                        st.success("Selesai!")

# ================= MENU 4: ADMIN =================
elif menu == "🔐 Admin":
    st.title("Admin SQL Database")
    if st.text_input("Password", type="password") == PASSWORD_ADMIN:
        df = load_data()
        st.dataframe(df)
        
        st.write("---")
        st.subheader("🗑️ Hapus Data")
        to_del = st.selectbox("Pilih ID", ["-"] + df['ID Tiket'].tolist())
        if st.button("Hapus Permanen"):
            if to_del != "-":
                df = df[df['ID Tiket'] != to_del]
                save_data(df)
                st.success("Terhapus!")
                st.rerun()
        
        st.write("---")
        st.subheader("📥 Export Excel")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Semua Data (CSV)", csv, "Backup_ATEM.csv", "text/csv")
