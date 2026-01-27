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
import base64 # 👈 NEW: For saving PDF to Database

# ==========================================
# ⚙️ TELEGRAM & ADMIN CONFIGURATION
# ==========================================
BOT_TOKEN = "8433442999:AAGjTv0iZEm_xtvlQTUBT11PUyxUYMtGxFQ"
CHAT_ID = "-1003692690153"
PASSWORD_ADMIN = "admin123"

# --- SEND MESSAGE FUNCTION ---
def kirim_notifikasi_telegram(pesan):
    try:
        if "GANTI" in BOT_TOKEN: return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.get(url, params=params)
        return True
    except: return False

# --- PDF GENERATION FUNCTION (2 SIGNATURES) ---
def create_pdf(ticket_data, image_file, user_sig, tech_sig, catatan_teknisi):
    pdf = FPDF()
    pdf.add_page()
    
    # --- HEADER ---
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, "BERITA ACARA PERBAIKAN ALAT MEDIS", ln=True, align='C')
    
    pdf.set_font("Times", 'I', 10)
    pdf.cell(0, 10, "RS CINTA KASIH TZU CHI - DEPARTEMEN ATEM", ln=True, align='C')
    pdf.line(10, 30, 200, 30); pdf.ln(10)
    
    # --- REPORT CONTENT ---
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
    
    # --- SIGNATURE AREA (SIDE BY SIDE) ---
    if pdf.get_y() > 200: pdf.add_page()
    
    y_start = pdf.get_y()
    
    # 1. LEFT: TECHNICIAN
    pdf.set_xy(10, y_start)
    pdf.set_font("Times", '', 10)
    pdf.cell(80, 5, "Dikerjakan Oleh / Teknisi,", ln=True, align='C')
    
    if tech_sig is not None:
        img_data = tech_sig.astype(np.uint8)
        im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_t:
            im.save(tmp_t.name)
            pdf.image(tmp_t.name, x=30, y=y_start+5, w=40)
            
    pdf.set_xy(10, y_start+35)
    pdf.set_font("Times", 'B', 10)
    pdf.cell(80, 5, f"({ticket_data['Teknisi']})", ln=True, align='C')

    # 2. RIGHT: USER
    pdf.set_xy(110, y_start)
    pdf.set_font("Times", '', 10)
    pdf.cell(80, 5, "Mengetahui / User,", ln=True, align='C')
    
    if user_sig is not None:
        img_data = user_sig.astype(np.uint8)
        im = Image.fromarray(img_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_u:
            im.save(tmp_u.name)
            pdf.image(tmp_u.name, x=130, y=y_start+5, w=40)
            
    pdf.set_xy(110, y_start+35)
    pdf.set_font("Times", 'B', 10)
    pdf.cell(80, 5, f"({ticket_data['Pelapor']})", ln=True, align='C')

    # --- PHOTO ATTACHMENT ---
    if image_file:
        pdf.add_page()
        pdf.set_font("Times", 'B', 14)
        pdf.cell(0, 10, "LAMPIRAN DOKUMENTASI", ln=True, align='C')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_file.getvalue())
            pdf.image(tmp.name, x=15, y=30, w=180)

    return pdf.output(dest="S").encode("latin1")

# --- PAGE CONFIG ---
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
# 🚀 POSTGRESQL DATABASE CONNECTION (NEON)
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
                "PDF_File" TEXT  -- New column for storing PDF
            );
        """))
        s.commit()

init_db()

# --- OPTIMIZED LOAD & SAVE FUNCTIONS ---

@st.cache_data(ttl=10)
def load_data():
    try:
        df = conn.query('SELECT * FROM laporan;')
        # Check if PDF_File column exists, if not, handle it gracefully
        if 'PDF_File' not in df.columns:
             df['PDF_File'] = None
        return df
    except Exception as e:
        return pd.DataFrame(columns=[
            "ID Tiket","Waktu Lapor","Pelapor","Ruangan","Nama Alat",
            "Nomor Serial","Keluhan","Prioritas","Status","Teknisi","Catatan","PDF_File"
        ])

def save_data(df):
    try:
        df.to_sql('laporan', conn.engine, if_exists='replace', index=False)
        # 👈 CRITICAL: Clear cache so new data appears immediately
        load_data.clear() 
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")
        
# --- SIDEBAR ---
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Menu", ["📝 Buat Laporan", "🔍 Cek Status Laporan", "🔧 Dashboard Teknisi", "🔐 Admin"])

# ================= MENU 1: LAPOR =================
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
        st.title("📝 Laporan Kerusakan")
        with st.form("f2"):
            c1, c2 = st.columns(2)
            with c1: pelapor = st.text_input("Nama Pelapor"); loc = st.selectbox("Lokasi", ["ICU","IGD","OT","Rawat Inap","Poli","Radiologi"])
            with c2: alat = st.text_input("Nama Alat"); sn = st.text_input("Serial Number"); prio = st.selectbox("Priority", ["Normal", "High (Urgent)"])
            kel = st.text_area("Kronologi/Keluhan")
            if st.form_submit_button("Kirim Laporan"):
                df = load_data()
                new_id = f"TC-{len(df)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = {"ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": pelapor, "Ruangan": loc, "Nama Alat": alat, "Nomor Serial": sn if sn else "-", "Keluhan": kel, "Prioritas": prio, "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                kirim_notifikasi_telegram(f"📝 *Tiket:* {new_id}\n📍 {loc} - {alat}\n⚠️ {prio}\n *Keluhan/Kronologi: * {kel}")
                st.success(f"Terkirim! ID: {new_id}")

# ================= MENU 2: STATUS & DOWNLOAD PDF =================
elif menu == "🔍 Cek Status Laporan":
    st.title("🔍 Status Laporan")
    if st.button("Refresh"): st.rerun()
    df = load_data()
    if not df.empty:
        df = df[df['Status'] != 'DONE'].sort_values(by='Waktu Lapor', ascending=False)
        # Show DONE tickets separately if you want, or just filter out DONE
        # Here we show active tickets, maybe you want to see DONE tickets to download PDF?
        # Let's show ALL tickets but sort Active first
        
        # Sort: Active first, then Done
        df['sort_val'] = df['Status'].apply(lambda x: 1 if x == 'DONE' else 0)
        df = df.sort_values(by=['sort_val', 'Waktu Lapor'], ascending=[True, False])
        
        for i, r in df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([1,3,2])
                with c1: 
                    if r['Prioritas']=='EMERGENCY': st.error("🚨 SOS")
                    elif r['Prioritas']=='High (Urgent)': st.warning("⚡ HIGH")
                    else: st.info("🟢 NORMAL")
                with c2: 
                    st.write(f"**{r['Ruangan']}** - {r['Nama Alat']}")
                    st.caption(f"{r['ID Tiket']} | {r['Pelapor']}")
                with c3: 
                    if r['Status']=='OPEN': st.write("⏳ Menunggu Teknisi")
                    elif r['Status']=='ON PROGRESS': st.markdown(f'<div class="status-otw">🏃 {r["Teknisi"]} OTW</div>', unsafe_allow_html=True)
                    elif r['Status']=='PENDING': st.markdown(f'<div class="status-pending">⏳ PENDING</div>', unsafe_allow_html=True)
                    elif r['Status']=='DONE':
                        st.success("✅ SELESAI")
                        # DOWNLOAD BUTTON FOR PDF
                        if r['PDF_File'] and r['PDF_File'] != "None" and pd.notna(r['PDF_File']):
                            try:
                                b64_pdf = r['PDF_File']
                                pdf_bytes = base64.b64decode(b64_pdf)
                                st.download_button("📄 Unduh BA", pdf_bytes, f"BA_{r['ID Tiket']}.pdf", "application/pdf", key=f"dl_{r['ID Tiket']}")
                            except:
                                st.caption("PDF Error")

# ================= MENU 3: TEKNISI =================
elif menu == "🔧 Dashboard Teknisi":
    st.title("🔧 Dashboard ATEM")
    if st.button("🔄 Refresh Data"): st.rerun()
    
    df = load_data()
    if not df.empty:
        # -------------------------------------------
        # PART 1: INCOMING TICKETS (Pick up button only)
        # -------------------------------------------
        st.subheader("📥 Tiket Masuk")
        prio_map = {"EMERGENCY":0, "High (Urgent)":1, "Normal":2}
        df['sort'] = df['Prioritas'].map(prio_map)
        open_t = df[df['Status']=='OPEN'].sort_values('sort')
        
        if open_t.empty: 
            st.info("Tidak ada tiket baru.")
        else:
            for i, r in open_t.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2,3,2])
                    
                    with c1: # Priority & Location
                        if r['Prioritas']=='EMERGENCY': st.error(f"🚨 {r['Ruangan']}")
                        elif r['Prioritas']=='High (Urgent)': st.warning(f"⚡ {r['Ruangan']}")
                        else: st.info(f"🟢 {r['Ruangan']}")
                        st.caption(f"Alat: {r['Nama Alat']}")
                    
                    with c2: # Complaints
                        st.write(f"📝 **Keluhan:** {r['Keluhan']}")
                        st.caption(f"Pelapor: {r['Pelapor']}")
                    
                    with c3: # Pickup Action
                        tek = st.selectbox("Pilih Teknisi", ["Budi","Andi","Siti"], key=f"s{r['ID Tiket']}")
                        if st.button("AMBIL TUGAS", key=f"b{r['ID Tiket']}", type="primary"):
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='ON PROGRESS'
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Teknisi']=tek
                            save_data(df)
                            kirim_notifikasi_telegram(f"✅ Tiket {r['ID Tiket']} diambil oleh {tek}")
                            st.rerun()

        st.markdown("---")
        
        # -------------------------------------------
        # PART 2: IN PROGRESS (With Signatures & PDF Save)
        # -------------------------------------------
        st.subheader("🛠 Sedang Dikerjakan")
        prog_t = df[df['Status']=='ON PROGRESS']
        
        if prog_t.empty:
            st.caption("Belum ada pekerjaan yang diambil.")
        else:
            for i, r in prog_t.iterrows():
                with st.container(border=True):
                    # Colored Header
                    if r['Prioritas']=='EMERGENCY': st.error(f"🔧 PENGERJAAN: {r['ID Tiket']} - {r['Nama Alat']} (SOS)")
                    elif r['Prioritas']=='High (Urgent)': st.warning(f"🔧 PENGERJAAN: {r['ID Tiket']} - {r['Nama Alat']} (HIGH)")
                    else: st.info(f"🔧 PENGERJAAN: {r['ID Tiket']} - {r['Nama Alat']}")
                    
                    # Form Input
                    cat = st.text_area(f"Laporan Pengerjaan ({r['ID Tiket']})", key=f"c{r['ID Tiket']}")
                    cam = st.camera_input("Foto Bukti (Opsional)", key=f"f{r['ID Tiket']}")
                    
                    st.write("---")
                    st.write("✍️ **Tanda Tangan Digital:**")
                    
                    # 2 Columns for Signatures
                    col_ttd1, col_ttd2 = st.columns(2)
                    
                    with col_ttd1:
                        st.caption(f"Teknisi: {r['Teknisi']}")
                        ttd_tek = st_canvas(
                            fill_color="rgba(255, 165, 0, 0.3)",
                            stroke_width=2, stroke_color="#000000",
                            background_color="#FFFFFF",
                            height=150, width=250,
                            drawing_mode="freedraw",
                            key=f"ttd_tek_{r['ID Tiket']}"
                        )
                        
                    with col_ttd2:
                        st.caption(f"User: {r['Pelapor']}")
                        ttd_user = st_canvas(
                            fill_color="rgba(255, 165, 0, 0.3)",
                            stroke_width=2, stroke_color="#000000",
                            background_color="#FFFFFF",
                            height=150, width=250,
                            drawing_mode="freedraw",
                            key=f"ttd_user_{r['ID Tiket']}"
                        )

                    # Finish Button
                    if st.button("✅ SIMPAN & BUAT BERITA ACARA", key=f"d{r['ID Tiket']}", type="primary"):
                        if ttd_tek.image_data is None or ttd_user.image_data is None:
                            st.error("⚠️ Harap lengkapi kedua Tanda Tangan (Teknisi & User)!")
                        else:
                            # 1. Generate PDF First
                            pdf_bytes = create_pdf(r, cam, ttd_user.image_data, ttd_tek.image_data, cat)
                            
                            # 2. Convert PDF to Base64 (Text) for Database
                            pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                            
                            # 3. Update DataFrame
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='DONE'
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Catatan']=cat
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'PDF_File']=pdf_b64
                            
                            # 4. Save to DB (And Clear Cache)
                            save_data(df)
                            
                            # 5. Notify & Provide Download
                            kirim_notifikasi_telegram(f"🎉 Tiket {r['ID Tiket']} SELESAI ({r['Teknisi']}).")
                            st.success("Berita Acara Tersimpan di Database!")
                            st.download_button("📥 Unduh PDF Resmi", pdf_bytes, f"BA_{r['ID Tiket']}.pdf", "application/pdf")
                            
                            # 6. Refresh to remove finished task
                            st.rerun()

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
