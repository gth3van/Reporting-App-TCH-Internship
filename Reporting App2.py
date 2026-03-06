import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from sqlalchemy import text, create_engine
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import tempfile
import numpy as np
from PIL import Image
import base64

# ==========================================
# ⚙️ KONFIGURASI DATABASE (ANTI-ERROR EXE)
# ==========================================
# Kita pakai create_engine langsung, BUKAN st.connection
# Ini lebih stabil buat EXE karena tidak butuh file secrets.toml
DB_URL = "postgresql://neondb_owner:npg_UHxb1dXrS9lM@ep-wispy-bonus-a1gcdzgu-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Buat Engine Global
try:
    engine = create_engine(DB_URL)
    # Test koneksi sesaat
    with engine.connect() as conn:
        pass
except Exception as e:
    st.error(f"❌ Gagal Konek Database: {e}")

BOT_TOKEN = "8433442999:AAGjTv0iZEm_xtvlQTUBT11PUyxUYMtGxFQ"
CHAT_ID = "-1003692690153"
PASSWORD_ADMIN = "admin123"

# --- HELPER TELEGRAM ---
def kirim_notifikasi_telegram(pesan):
    try:
        if "GANTI" in BOT_TOKEN: return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.get(url, params=params)
        return True
    except: return False

# --- HELPER DATABASE (PENGGANTI ST.CONNECTION) ---
# 1. Fungsi Baca Data (SELECT)
def run_query_select(query_str, params=None):
    try:
        with engine.connect() as conn:
            # Gunakan pandas read_sql yang lebih robust
            return pd.read_sql(text(query_str), conn, params=params)
    except Exception as e:
        return pd.DataFrame() # Return kosong jika error

# 2. Fungsi Tulis Data (INSERT/UPDATE/DELETE)
def run_query_execute(query_str, params=None):
    try:
        with engine.connect() as conn:
            conn.execute(text(query_str), params)
            conn.commit()
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- FUNGSI PDF ---
def create_pdf(ticket_data, image_file, user_sig, tech_sig, catatan_teknisi):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, "BERITA ACARA PERBAIKAN ALAT MEDIS", ln=True, align='C')
    pdf.set_font("Times", 'I', 10)
    pdf.cell(0, 10, "RS CINTA KASIH TZU CHI - DEPARTEMEN ATEM", ln=True, align='C')
    pdf.line(10, 30, 200, 30); pdf.ln(10)
    
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
    
    if pdf.get_y() > 200: pdf.add_page()
    y_start = pdf.get_y()
    
    pdf.set_xy(10, y_start)
    pdf.set_font("Times", '', 10); pdf.cell(80, 5, "Dikerjakan Oleh,", ln=True, align='C')
    if tech_sig is not None:
        img_data = tech_sig.astype(np.uint8); im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            im.save(tmp.name); pdf.image(tmp.name, x=30, y=y_start+5, w=40)
    pdf.set_xy(10, y_start+35); pdf.set_font("Times", 'B', 10); pdf.cell(80, 5, f"({ticket_data['Teknisi']})", ln=True, align='C')

    pdf.set_xy(110, y_start)
    pdf.set_font("Times", '', 10); pdf.cell(80, 5, "Mengetahui / User,", ln=True, align='C')
    if user_sig is not None:
        img_data = user_sig.astype(np.uint8); im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            im.save(tmp.name); pdf.image(tmp.name, x=130, y=y_start+5, w=40)
    pdf.set_xy(110, y_start+35); pdf.set_font("Times", 'B', 10); pdf.cell(80, 5, f"({ticket_data['Pelapor']})", ln=True, align='C')

    if image_file:
        pdf.add_page(); pdf.set_font("Times", 'B', 14); pdf.cell(0, 10, "LAMPIRAN DOKUMENTASI", ln=True, align='C')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_file.getvalue()); pdf.image(tmp.name, x=15, y=30, w=180)

    return pdf.output(dest="S").encode("latin1")

# --- SETTING PAGE ---
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

# Initial DB Check
run_query_execute("""
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
""")

# --- LOAD DATA (DENGAN CACHE) ---
@st.cache_data(ttl=5)
def load_data_ringan():
    # Ambil semua kecuali PDF biar cepat
    return run_query_select('SELECT "ID Tiket", "Waktu Lapor", "Pelapor", "Ruangan", "Nama Alat", "Nomor Serial", "Keluhan", "Prioritas", "Status", "Teknisi", "Catatan" FROM laporan;')

def get_pdf_by_id(ticket_id):
    df = run_query_select('SELECT "PDF_File" FROM laporan WHERE "ID Tiket" = :id', {"id": ticket_id})
    if not df.empty:
        return df.iloc[0]["PDF_File"]
    return None

def save_new_ticket(data_dict):
    # Simpan Tiket Baru
    df = pd.DataFrame([data_dict])
    df.to_sql('laporan', engine, if_exists='append', index=False)
    load_data_ringan.clear() # Reset cache

def update_ticket_status(ticket_id, status, teknisi=None, catatan=None, pdf_b64=None):
    # Update Status
    sql = 'UPDATE laporan SET "Status" = :s'
    params = {"s": status, "id": ticket_id}
    
    if teknisi:
        sql += ', "Teknisi" = :t'
        params["t"] = teknisi
    if catatan:
        sql += ', "Catatan" = :c'
        params["c"] = catatan
    if pdf_b64:
        sql += ', "PDF_File" = :p'
        params["p"] = pdf_b64
        
    sql += ' WHERE "ID Tiket" = :id'
    run_query_execute(sql, params)
    load_data_ringan.clear()

# ==========================================
# 🏥 NAVIGASI
# ==========================================
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Menu", ["📝 Buat Laporan", "🔍 Cek Status & Download", "🔧 Dashboard Teknisi", "🔐 Admin"])

# --- MENU 1: LAPOR ---
if menu == "📝 Buat Laporan":
    darurat = st.sidebar.toggle("🚨 MODE DARURAT")
    if darurat:
        st.markdown('<div class="emergency-box">🚨 FORMULIR DARURAT 🚨</div>', unsafe_allow_html=True)
        with st.form("f1"):
            loc = st.selectbox("LOKASI:", ["ICU","IGD","OT","NICU","Rawat Inap","Radiologi","Hemodialisa"])
            if st.form_submit_button("🚨 PANGGIL TEKNISI"):
                df_all = run_query_select('SELECT "ID Tiket" FROM laporan')
                new_id = f"URGENT-{len(df_all)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                save_new_ticket({
                    "ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": "DARURAT", "Ruangan": loc, 
                    "Nama Alat": "DARURAT", "Nomor Serial": "-", "Keluhan": "DARURAT", 
                    "Prioritas": "EMERGENCY", "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None
                })
                kirim_notifikasi_telegram(f"🚨 *SOS!* {loc}\nID: {new_id}")
                st.error(f"Sinyal Terkirim ke {loc}!")
    else:
        st.title("📝 Lapor Kerusakan")
        with st.form("f2"):
            c1, c2 = st.columns(2)
            with c1: pelapor = st.text_input("Nama Pelapor"); loc = st.selectbox("Lokasi", ["ICU","IGD","OT","Rawat Inap","Poli","Radiologi"])
            with c2: alat = st.text_input("Nama Alat"); sn = st.text_input("SN Alat"); prio = st.selectbox("Prioritas", ["🟢 Normal", "🟡 High (Urgent)"])
            kel = st.text_area("Keluhan / Kronologi")
            
            if st.form_submit_button("Kirim Laporan"):
                if not pelapor or not alat:
                    st.error("⚠️ Nama Pelapor dan Nama Alat WAJIB diisi!")
                else:
                    df_all = run_query_select('SELECT "ID Tiket" FROM laporan')
                    new_id = f"TC-{len(df_all)+1:03d}"
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    save_new_ticket({
                        "ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": pelapor, "Ruangan": loc, 
                        "Nama Alat": alat, "Nomor Serial": sn if sn else "-", "Keluhan": kel, 
                        "Prioritas": prio, "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None
                    })
                    
                    kirim_notifikasi_telegram(f"📝 *Tiket:* {new_id}\n📍 {loc} - {alat} {sn}\n⚠️ {prio}\n *Keluhan: * {kel}")
                    st.success(f"Terkirim! ID: {new_id}")

# --- MENU 2: STATUS ---
elif menu == "🔍 Cek Status & Download":
    st.title("🔍 Status Laporan")
    if st.button("Refresh"): st.rerun()
    
    df = load_data_ringan()
    if not df.empty:
        df['sort_val'] = df['Status'].apply(lambda x: 1 if x == 'DONE' else 0)
        df = df.sort_values(by=['sort_val', 'Waktu Lapor'], ascending=[True, False])
        
        tiket_selesai = df[df['Status']=='DONE']['ID Tiket'].tolist()
        pilih_id = st.selectbox("Unduh Berita Acara (PDF):", ["-"] + tiket_selesai)
        
        if pilih_id != "-":
            pdf_b64 = get_pdf_by_id(pilih_id)
            if pdf_b64:
                try:
                    pdf_bytes = base64.b64decode(pdf_b64)
                    st.download_button("⬇️ DOWNLOAD PDF", pdf_bytes, f"BA_{pilih_id}.pdf", "application/pdf", type="primary")
                except: st.error("File rusak.")
            else: st.warning("PDF belum tersedia.")

        st.divider()
        for i, r in df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([1,3,2])
                with c1: 
                    if r['Prioritas']=='EMERGENCY': st.error("SOS")
                    elif r['Prioritas']=='🟡 High (Urgent)': st.warning("🟡 HIGH")
                    else: st.info("🟢 NORMAL")
                with c2: 
                    st.write(f"**{r['Ruangan']}** - {r['Nama Alat']}")
                    st.caption(f"{r['ID Tiket']} | {r['Pelapor']}")
                    if r['Status'] == 'PENDING': st.warning(f"⚠️ PENDING: {r['Catatan']}")
                with c3: 
                    if r['Status']=='OPEN': st.write("⏳ Menunggu Teknisi")
                    elif r['Status']=='ON PROGRESS': st.markdown(f'<div class="status-otw">🏃 {r["Teknisi"]} Menuju Lokasi</div>', unsafe_allow_html=True)
                    elif r['Status']=='PENDING': st.markdown(f'<div class="status-pending">⏳ PENDING</div>', unsafe_allow_html=True)
                    elif r['Status']=='DONE': st.success("✅ SELESAI")
    else:
        st.info("Belum ada data.")

# --- MENU 3: TEKNISI ---
elif menu == "🔧 Dashboard Teknisi":
    st.title("🔧 Dashboard ATEM")
    if st.button("🔄 Refresh Data"): st.rerun()
    
    df = load_data_ringan()
    if not df.empty:
        st.subheader("📥 Tiket Masuk")
        open_t = df[df['Status']=='OPEN']
        if open_t.empty: st.info("Tidak ada tiket baru.")
        else:
            for i, r in open_t.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3,1])
                    with c1:
                        st.write(f"**{r['ID Tiket']}** - {r['Ruangan']}")
                        st.caption(f"{r['Nama Alat']} | {r['Keluhan']}")
                    with c2:
                        tek = st.selectbox("Nama Anda", ["Budi","Andi","Siti"], key=f"s{r['ID Tiket']}")
                        if st.button("AMBIL", key=f"b{r['ID Tiket']}", type="primary"):
                            update_ticket_status(r['ID Tiket'], 'ON PROGRESS', teknisi=tek)
                            kirim_notifikasi_telegram(f"✅ {r['ID Tiket']} diambil {tek}")
                            st.rerun()

        st.markdown("---")
        st.subheader("🛠 Sedang Dikerjakan")
        prog_t = df[df['Status']=='ON PROGRESS']
        if prog_t.empty: st.caption("Kosong.")
        else:
            for i, r in prog_t.iterrows():
                with st.container(border=True):
                    st.info(f"🔧 {r['ID Tiket']} - {r['Nama Alat']}")
                    cat = st.text_area(f"Laporan Pengerjaan", key=f"c{r['ID Tiket']}")
                    cam = st.camera_input("Foto Bukti", key=f"f{r['ID Tiket']}")
                    
                    st.write("Tanda Tangan:")
                    c1, c2 = st.columns(2)
                    with c1: st.caption("Teknisi"); ttd_tek = st_canvas(fill_color="rgba(255,165,0,0.3)",stroke_width=2, stroke_color="#000000",background_color="#FFFFFF", height=100, width=200, key=f"tk_{r['ID Tiket']}")
                    with c2: st.caption("User"); ttd_user = st_canvas(fill_color="rgba(255,165,0,0.3)",stroke_width=2, stroke_color="#000000",background_color="#FFFFFF", height=100, width=200, key=f"us_{r['ID Tiket']}")

                    ac1, ac2 = st.columns(2)
                    with ac1:
                        if st.button("✅ SELESAI", key=f"d{r['ID Tiket']}", type="primary"):
                            if ttd_tek.image_data is None or ttd_user.image_data is None:
                                st.error("TTD Wajib!")
                            else:
                                pdf_bytes = create_pdf(r, cam, ttd_user.image_data, ttd_tek.image_data, cat)
                                pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                                update_ticket_status(r['ID Tiket'], 'DONE', catatan=cat, pdf_b64=pdf_b64)
                                kirim_notifikasi_telegram(f"🎉 {r['ID Tiket']} SELESAI.")
                                st.success("Tersimpan!"); st.rerun()
                    with ac2:
                        if st.button("⏳ TUNDA", key=f"p{r['ID Tiket']}"):
                             update_ticket_status(r['ID Tiket'], 'PENDING', catatan=cat)
                             st.rerun()

        st.markdown("---")
        st.subheader("⏳ Menunggu Vendor")
        pend_t = df[df['Status']=='PENDING']
        if pend_t.empty: st.caption("Kosong.")
        else:
            for i, r in pend_t.iterrows():
                with st.container(border=True):
                    st.warning(f"{r['ID Tiket']} - {r['Catatan']}")
                    if st.button("▶️ LANJUT", key=f"r{r['ID Tiket']}"):
                        update_ticket_status(r['ID Tiket'], 'ON PROGRESS')
                        st.rerun()

# --- MENU 4: ADMIN ---
elif menu == "🔐 Admin":
    st.title("Admin")
    if st.text_input("Password", type="password") == PASSWORD_ADMIN:
        df = load_data_ringan()
        st.dataframe(df)
        
        to_del = st.multiselect("Hapus ID:", df['ID Tiket'].tolist())
        if st.button("HAPUS DATA"):
            if to_del:
                # Perbaikan Logika Hapus untuk SQLAlchemy
                # Kita ubah list jadi tuple agar bisa pakai IN
                t_ids = tuple(to_del)
                if len(t_ids) == 1:
                    run_query_execute('DELETE FROM laporan WHERE "ID Tiket" = :id', {"id": t_ids[0]})
                else:
                    run_query_execute('DELETE FROM laporan WHERE "ID Tiket" IN :ids', {"ids": t_ids})
                
                load_data_ringan.clear()
                st.success("Terhapus!"); st.rerun()
        
        if st.button("RESET TOTAL"):
            run_query_execute("DROP TABLE IF EXISTS laporan")
            st.error("Reset Berhasil!"); st.rerun()
