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
# ⚙️ KONFIGURASI UMUM
# ==========================================
BOT_TOKEN = "8433442999:AAGjTv0iZEm_xtvlQTUBT11PUyxUYMtGxFQ"
CHAT_ID = "-1003692690153"
PASSWORD_ADMIN = "admin123"

def kirim_notifikasi_telegram(pesan):
    try:
        if "GANTI" in BOT_TOKEN: return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.get(url, params=params)
        return True
    except: return False

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

# --- OPTIMISASI 1: LOAD HANYA DATA RINGAN (TANPA PDF) ---
@st.cache_data(ttl=10)
def load_data_ringan():
    try:
        # KITA EXCLUDE KOLOM "PDF_File" AGAR RINGAN & CEPAT
        query = 'SELECT "ID Tiket", "Waktu Lapor", "Pelapor", "Ruangan", "Nama Alat", "Nomor Serial", "Keluhan", "Prioritas", "Status", "Teknisi", "Catatan" FROM laporan;'
        df = conn.query(query, ttl=0)
        return df
    except Exception as e:
        # Return struktur kosong jika error
        return pd.DataFrame(columns=["ID Tiket","Waktu Lapor","Pelapor","Ruangan","Nama Alat","Nomor Serial","Keluhan","Prioritas","Status","Teknisi","Catatan"])

# --- OPTIMISASI 2: AMBIL PDF HANYA JIKA DIMINTA ---
def get_pdf_by_id(ticket_id):
    try:
        query = text('SELECT "PDF_File" FROM laporan WHERE "ID Tiket" = :id')
        result = conn.query(query, params={"id": ticket_id}, ttl=0)
        if not result.empty:
            return result.iloc[0]["PDF_File"]
    except: return None
    return None

def save_data(df_row, is_new=False):
    """
    Menyimpan data. Jika is_new=True, insert baru.
    Jika tidak, update data yang ada.
    """
    try:
        if is_new:
            # Simpan baris baru ke SQL
            df_row.to_sql('laporan', conn.engine, if_exists='append', index=False)
        else:
            # UPDATE manual pake SQL agar tidak menimpa seluruh tabel (LEBIH CEPAT)
            # Catatan: Karena kita pakai replace di versi sebelumnya, kita pakai replace lagi biar konsisten & mudah
            # TAPI idealnya pakai UPDATE WHERE ID=...
            # Untuk sekarang kita pakai replace total tapi ambil data ringan dulu
            
            # Cara lama (Replace All) masih oke untuk data < 1000 baris asalkan loadnya ringan
            # Tapi kita harus ambil FULL data dulu termasuk PDF kalau mau replace all.
            # Jadi kita pakai teknik 'UPDATE' sederhana via Pandas Replace All (kurang efisien tapi paling aman buat struktur ini)
            pass 
            
    except Exception as e:
        st.error(f"Save Error: {e}")

# Agar tidak pusing mengubah logika Save Data yang sudah kamu buat,
# Kita tetap pakai logika 'Load All -> Edit -> Save All' tapi 
# Kita pastikan fungsi 'save_full_dataframe' bekerja benar.

def save_full_dataframe(df):
    try:
        df.to_sql('laporan', conn.engine, if_exists='replace', index=False)
        load_data_ringan.clear() 
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")

# ==========================================
# 🏥 NAVIGASI
# ==========================================
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Menu", ["📝 Buat Laporan", "🔍 Cek Status & Download", "🔧 Dashboard Teknisi", "🔐 Admin"])

# --- MENU 1 ---
if menu == "📝 Buat Laporan":
    darurat = st.sidebar.toggle("🚨 MODE DARURAT")
    if darurat:
        st.markdown('<div class="emergency-box">🚨 FORMULIR DARURAT 🚨</div>', unsafe_allow_html=True)
        with st.form("f1"):
            loc = st.selectbox("LOKASI:", ["ICU","IGD","OT","NICU","Rawat Inap","Radiologi","Hemodialisa"])
            if st.form_submit_button("🚨 PANGGIL TEKNISI"):
                # Load Full Data sebentar untuk dapat ID & Append
                df = conn.query('SELECT * FROM laporan;', ttl=0) 
                new_id = f"URGENT-{len(df)+1:03d}"
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_row = pd.DataFrame([{
                    "ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": "DARURAT", "Ruangan": loc, 
                    "Nama Alat": "DARURAT", "Nomor Serial": "-", "Keluhan": "DARURAT", 
                    "Prioritas": "EMERGENCY", "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None
                }])
                new_row.to_sql('laporan', conn.engine, if_exists='append', index=False)
                load_data_ringan.clear()
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
                    # Teknik INSERT (Append) jauh lebih cepat daripada Replace All
                    df_count = load_data_ringan() # Cuma buat hitung ID
                    new_id = f"TC-{len(df_count)+1:03d}"
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    new_row = pd.DataFrame([{
                        "ID Tiket": new_id, "Waktu Lapor": now, "Pelapor": pelapor, "Ruangan": loc, 
                        "Nama Alat": alat, "Nomor Serial": sn if sn else "-", "Keluhan": kel, 
                        "Prioritas": prio, "Status": "OPEN", "Teknisi": "-", "Catatan": "-", "PDF_File": None
                    }])
                    
                    # Simpan HANYA baris baru (Append) -> SANGAT CEPAT
                    new_row.to_sql('laporan', conn.engine, if_exists='append', index=False)
                    load_data_ringan.clear()
                    
                    kirim_notifikasi_telegram(f"📝 *Tiket:* {new_id}\n📍 {loc} - {alat} {sn}\n⚠️ {prio}\n *Keluhan: * {kel}")
                    st.success(f"Terkirim! ID: {new_id}")

# --- MENU 2: STATUS (OPTIMISASI BESAR) ---
elif menu == "🔍 Cek Status & Download":
    st.title("🔍 Status Laporan")
    if st.button("Refresh"): st.rerun()
    
    # 1. Load Data Ringan (Tanpa PDF) -> CEPAT
    df = load_data_ringan()
    
    if not df.empty:
        # Sortir
        df['sort_val'] = df['Status'].apply(lambda x: 1 if x == 'DONE' else 0)
        df = df.sort_values(by=['sort_val', 'Waktu Lapor'], ascending=[True, False])
        
        # 2. Fitur Download Terpisah (Biar gak berat load semua PDF)
        st.info("💡 Untuk mengunduh Berita Acara, pilih tiket di bawah ini:")
        tiket_selesai = df[df['Status']=='DONE']['ID Tiket'].tolist()
        
        col_dl1, col_dl2 = st.columns([3, 1])
        with col_dl1:
            pilih_id = st.selectbox("Pilih ID Tiket Selesai:", ["-"] + tiket_selesai)
        with col_dl2:
            st.write("") # Spacer
            st.write("") 
            if pilih_id != "-":
                # 3. Ambil PDF Cuma Kalau Diminta -> EFISIEN
                pdf_b64 = get_pdf_by_id(pilih_id)
                if pdf_b64 and pd.notna(pdf_b64):
                    try:
                        pdf_bytes = base64.b64decode(pdf_b64)
                        st.download_button("⬇️ DOWNLOAD PDF", pdf_bytes, f"BA_{pilih_id}.pdf", "application/pdf", type="primary")
                    except: st.error("File rusak.")
                else:
                    st.warning("PDF belum tersedia.")

        st.divider()
        st.write("### Daftar Tiket")

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
    
    # Load Full Data is needed here for updating logic safely with replace strategy
    # Or we can optimize by loading full ONLY when saving.
    # Let's keep it simple: Load full data here because technician needs to edit
    try:
        df = conn.query('SELECT * FROM laporan;', ttl=0)
        if 'PDF_File' not in df.columns: df['PDF_File'] = None
    except: df = pd.DataFrame()
    
    if not df.empty:
        st.subheader("📥 Tiket Masuk")
        prio_map = {"EMERGENCY":0, "🟡 High (Urgent)":1, "🟢 Normal":2}
        df['sort'] = df['Prioritas'].map(prio_map)
        open_t = df[df['Status']=='OPEN'].sort_values('sort')
        
        if open_t.empty: st.info("Tidak ada tiket baru.")
        else:
            for i, r in open_t.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2,3,2])
                    with c1:
                        if r['Prioritas']=='EMERGENCY': st.error(f"🚨 {r['Ruangan']}")
                        elif r['Prioritas']=='🟡 High (Urgent)': st.warning(f"🟡 {r['Ruangan']}")
                        else: st.info(f"🟢 {r['Ruangan']}")
                        st.caption(r['Nama Alat'])
                    with c2: st.write(f"📝 {r['Keluhan']}"); st.caption(r['Pelapor'])
                    with c3:
                        tek = st.selectbox("Teknisi", ["Budi","Andi","Siti"], key=f"s{r['ID Tiket']}")
                        if st.button("AMBIL TUGAS", key=f"b{r['ID Tiket']}", type="primary"):
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='ON PROGRESS'
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Teknisi']=tek
                            save_full_dataframe(df)
                            kirim_notifikasi_telegram(f"✅ {r['ID Tiket']} diambil {tek}")
                            st.rerun()

        st.markdown("---")
        st.subheader("🛠 Sedang Dikerjakan")
        prog_t = df[df['Status']=='ON PROGRESS']
        
        if prog_t.empty: st.caption("Tidak ada pekerjaan aktif.")
        else:
            for i, r in prog_t.iterrows():
                with st.container(border=True):
                    st.info(f"🔧 PENGERJAAN: {r['ID Tiket']} - {r['Nama Alat']}")
                    cat = st.text_area(f"Laporan / Alasan Pending (WAJIB DIISI)", key=f"c{r['ID Tiket']}")
                    cam = st.camera_input("Foto Bukti", key=f"f{r['ID Tiket']}")
                    
                    st.write("✍️ **Tanda Tangan:**")
                    c1, c2 = st.columns(2)
                    with c1: st.caption("Teknisi"); ttd_tek = st_canvas(fill_color="rgba(255,165,0,0.3)",background_color="#FFFFFF", stroke_width=2, stroke_color="#000", height=150, width=250, key=f"tk_{r['ID Tiket']}")
                    with c2: st.caption("User"); ttd_user = st_canvas(fill_color="rgba(255,165,0,0.3)",background_color="#FFFFFF", stroke_width=2, stroke_color="#000", height=150, width=250, key=f"us_{r['ID Tiket']}")

                    ac1, ac2 = st.columns(2)
                    with ac1:
                        if st.button("✅ SELESAI & SIMPAN", key=f"d{r['ID Tiket']}", type="primary"):
                            if ttd_tek.image_data is None or ttd_user.image_data is None:
                                st.error("TTD Wajib diisi keduanya!")
                            else:
                                df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='DONE'
                                df.loc[df['ID Tiket']==r['ID Tiket'], 'Catatan']=cat
                                pdf_bytes = create_pdf(r, cam, ttd_user.image_data, ttd_tek.image_data, cat)
                                pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                                df.loc[df['ID Tiket']==r['ID Tiket'], 'PDF_File']=pdf_b64
                                save_full_dataframe(df)
                                kirim_notifikasi_telegram(f"🎉 Tiket {r['ID Tiket']} SELESAI.")
                                st.success("Tersimpan!"); st.rerun()

                    with ac2:
                        if st.button("⏳ TUNDA (VENDOR)", key=f"p{r['ID Tiket']}"):
                            if not cat: st.error("⚠️ Tulis alasan di kotak Laporan!")
                            else:
                                df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='PENDING'
                                df.loc[df['ID Tiket']==r['ID Tiket'], 'Catatan']=cat
                                save_full_dataframe(df)
                                kirim_notifikasi_telegram(f"⚠️ PENDING: {r['ID Tiket']} ({cat})")
                                st.rerun()

        st.markdown("---")
        st.subheader("⏳ Menunggu Vendor")
        pend_t = df[df['Status']=='PENDING']
        if pend_t.empty: st.caption("Kosong.")
        else:
            for i, r in pend_t.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3,1])
                    with c1: st.write(f"**{r['ID Tiket']}** - {r['Nama Alat']}"); st.warning(f"Alasan: {r['Catatan']}")
                    with c2: 
                        if st.button("▶️ LANJUT", key=f"r{r['ID Tiket']}"):
                            df.loc[df['ID Tiket']==r['ID Tiket'], 'Status']='ON PROGRESS'
                            save_full_dataframe(df)
                            st.rerun()

# --- MENU 4: ADMIN ---
elif menu == "🔐 Admin":
    st.title("Admin SQL Database")
    if st.text_input("Password", type="password") == PASSWORD_ADMIN:
        df = load_data_ringan() # Load ringan aja buat lihat
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🗑️ Hapus Data")
        to_del = st.multiselect("Pilih ID:", df['ID Tiket'].tolist())
        if st.button(f"Hapus {len(to_del)} Data", type="primary"):
            if to_del:
                # Untuk delete kita butuh full access atau execute SQL delete directly
                # Paling aman dan cepat: SQL Delete
                id_tuple = tuple(to_del)
                if len(id_tuple) == 1:
                    # Kalau cuma 1, tuple butuh koma: ('ID',)
                    query_del = text('DELETE FROM laporan WHERE "ID Tiket" = :id')
                    with conn.session as s:
                        s.execute(query_del, {"id": to_del[0]})
                        s.commit()
                else:
                    query_del = text('DELETE FROM laporan WHERE "ID Tiket" IN :ids')
                    with conn.session as s:
                        s.execute(query_del, {"ids": id_tuple})
                        s.commit()
                
                load_data_ringan.clear()
                st.success("Terhapus!"); st.rerun()
        
        st.divider()
        if st.button("🔥 RESET DATABASE TOTAL"):
            try:
                with conn.session as s:
                    s.execute(text("DROP TABLE IF EXISTS laporan;"))
                    s.commit()
                init_db(); load_data_ringan.clear()
                st.error("Database Bersih!"); st.rerun()
            except Exception as e: st.error(e)





