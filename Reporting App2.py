import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import base64
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
        if "GANTI" in BOT_TOKEN or "GANTI" in CHAT_ID:
            return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.get(url, params=params)
        return True
    except Exception:
        return False

# --- FUNGSI BIKIN PDF (BERITA ACARA) ---
def create_pdf(ticket_data, image_file, signature_img, catatan_teknisi):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Header
    pdf.cell(0, 10, "BERITA ACARA PERBAIKAN ALAT MEDIS", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, "RS CINTA KASIH TZU CHI - DEPARTEMEN ATEM", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    # Info Tiket
    pdf.set_font("Arial", '', 12)
    pdf.cell(50, 10, f"No. Tiket: {ticket_data['ID Tiket']}", ln=True)
    pdf.cell(50, 10, f"Tanggal Lapor: {ticket_data['Waktu Lapor']}", ln=True)
    pdf.cell(50, 10, f"Ruangan: {ticket_data['Ruangan']}", ln=True)
    pdf.cell(50, 10, f"Pelapor: {ticket_data['Pelapor']}", ln=True)
    pdf.ln(5)
    
    # Info Alat
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "DETAIL ALAT & KERUSAKAN", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, f"Nama Alat: {ticket_data['Nama Alat']}")
    pdf.multi_cell(0, 8, f"No. Serial: {ticket_data['Nomor Serial']}")
    pdf.multi_cell(0, 8, f"Keluhan Awal: {ticket_data['Keluhan']}")
    pdf.ln(5)
    
    # Tindakan
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "TINDAKAN TEKNISI", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, f"Teknisi: {ticket_data['Teknisi']}")
    pdf.multi_cell(0, 8, f"Solusi/Catatan: {catatan_teknisi}")
    pdf.ln(5)
    
    # FOTO BUKTI (Jika Ada)
    if image_file is not None:
        pdf.add_page()
        pdf.cell(0, 10, "DOKUMENTASI / FOTO", ln=True)
        # Simpan sementara agar bisa dibaca FPDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_file.getvalue())
            pdf.image(tmp.name, x=10, y=30, w=100)
    
    # TANDA TANGAN (Jika Ada)
    if signature_img is not None:
        pdf.ln(10)
        pdf.cell(0, 10, "Tanda Tangan User / Pelapor:", ln=True)
        # Convert numpy array from canvas to image file temporary
        img_data = signature_img.astype(np.uint8)
        im = Image.fromarray(img_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
            im.save(tmp_sig.name)
            pdf.image(tmp_sig.name, w=50)

    # Output string
    return pdf.output(dest="S").encode("latin1")


# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Tzu Chi MedFix", page_icon="🏥", layout="wide")

# --- STYLE CSS ---
st.markdown("""
<style>
    .stButton>button { width: 100%; height: 3em; font-weight: bold; }
    .emergency-box { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: 900; animation: blinker 1s linear infinite; }
    .status-otw { background-color: #ffd700; color: black; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    .status-pending { background-color: #6c757d; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0.8; } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🌐 FUNGSI GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.astype(str)
        df = df.replace("nan", "-")
        return df
    except Exception as e:
        st.error(f"Gagal koneksi ke Google Sheets: {e}")
        return pd.DataFrame()

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")

# --- SIDEBAR (MENU) ---
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Pilih Menu:", ["📝 Buat Laporan", "🔍 Cek Status Laporan", "🔧 Dashboard Teknisi", "🔐 Admin Database"])

# ================= MENU 1: USER PELAPOR =================
if menu == "📝 Buat Laporan":
    mode_darurat = st.sidebar.toggle("🚨 MODE DARURAT", value=False)
    
    if mode_darurat:
        st.markdown('<div class="emergency-box">🚨 FORMULIR GAWAT DARURAT 🚨</div>', unsafe_allow_html=True)
        with st.form("form_darurat"):
            ruangan = st.selectbox("LOKASI KEJADIAN:", ["ICU", "IGD", "OK", "NICU", "Rawat Inap", "Radiologi", "Hemodialisa"])
            submit = st.form_submit_button("🚨 PANGGIL TEKNISI SEKARANG", type="primary")
            
            if submit and ruangan:
                df = load_data()
                new_id = f"URGENT-{len(df)+1:03d}"
                waktu = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_data = pd.DataFrame([{
                    "ID Tiket": new_id, "Waktu Lapor": waktu, "Pelapor": "STAFF (DARURAT)",
                    "Ruangan": ruangan, "Nama Alat": "❗ CEK LOKASI", 
                    "Nomor Serial": "-", "Keluhan": "DARURAT",
                    "Prioritas": "EMERGENCY", "Status": "OPEN", "Teknisi": "-", "Catatan": "-"
                }])
                save_data(pd.concat([df, new_data], ignore_index=True))
                
                pesan = f"🚨 *SOS! DARURAT MEDIS!* 🚨\n\n📍 Lokasi: *{ruangan}*\n⚠️ Status: *EMERGENCY*\n🕒 Waktu: {waktu}\n\n_Mohon teknisi segera meluncur!_"
                kirim_notifikasi_telegram(pesan)
                st.error(f"🚨 SINYAL TERKIRIM KE HP TEKNISI! Mohon tunggu di {ruangan}.")
    else:
        st.title("📝 Lapor Kerusakan Rutin")
        with st.form("form_laporan"):
            col1, col2 = st.columns(2)
            with col1:
                pelapor = st.text_input("Nama Pelapor")
                ruangan = st.selectbox("Lokasi", ["ICU", "IGD", "OK", "Rawat Inap", "Poli", "Radiologi"])
            with col2:
                nama_alat = st.text_input("Nama Alat")
                no_serial = st.text_input("Nomor Serial / SN Alat")
                prioritas = st.selectbox("Prioritas", ["Normal", "High (Urgent)"])
            keluhan = st.text_area("Keluhan")
            
            if st.form_submit_button("Kirim Laporan"):
                if pelapor and nama_alat:
                    df = load_data()
                    new_id = f"TC-{len(df)+1:03d}"
                    waktu = datetime.now().strftime("%Y-%m-%d %H:%M")
                    new_data = pd.DataFrame([{
                        "ID Tiket": new_id, "Waktu Lapor": waktu, "Pelapor": pelapor,
                        "Ruangan": ruangan, "Nama Alat": nama_alat, 
                        "Nomor Serial": no_serial if no_serial else "-", 
                        "Keluhan": keluhan, "Prioritas": prioritas, 
                        "Status": "OPEN", "Teknisi": "-", "Catatan": "-"
                    }])
                    save_data(pd.concat([df, new_data], ignore_index=True))
                    
                    icon = "⚡" if prioritas == "High (Urgent)" else "📝"
                    sn_info = f"(SN: {no_serial})" if no_serial else ""
                    pesan = f"{icon} *Tiket Baru Masuk* {icon}\n\n🆔 ID: `{new_id}`\n📍 Lokasi: *{ruangan}*\n🛠 Alat: {nama_alat} {sn_info}\n👤 Pelapor: {pelapor}\n⚠️ Prioritas: {prioritas}\n📝 Keluhan: {keluhan}\n\n_Silakan cek dashboard._"
                    kirim_notifikasi_telegram(pesan)
                    st.success(f"✅ Laporan Terkirim! ID: {new_id}")
                else:
                    st.error("Mohon lengkapi data.")

# ================= MENU 2: STATUS =================
elif menu == "🔍 Cek Status Laporan":
    st.title("🔍 Cek Status Laporan")
    if st.button("🔄 Refresh Status"): st.rerun()
    
    df = load_data()
    if not df.empty:
        df_aktif = df[df['Status'] != 'DONE'].sort_values(by='Waktu Lapor', ascending=False)
        for index, row in df_aktif.iterrows():
            with st.container(border=True):
                cols = st.columns([1, 3, 2])
                with cols[0]:
                    st.write(f"**{row['ID Tiket']}**")
                    if row['Prioritas'] == 'EMERGENCY': st.error("DARURAT")
                    elif row['Prioritas'] == 'High (Urgent)': st.warning("HIGH")
                    else: st.info("NORMAL")
                with cols[1]:
                    sn_text = f"(SN: {row['Nomor Serial']})" if row['Nomor Serial'] != "-" else ""
                    st.write(f"📍 **{row['Ruangan']}** - {row['Nama Alat']} {sn_text}")
                    st.caption(f"Pelapor: {row['Pelapor']}")
                with cols[2]:
                    if row['Status'] == 'OPEN': st.write("⏳ Menunggu Teknisi")
                    elif row['Status'] == 'ON PROGRESS': st.markdown(f'<div class="status-otw">🏃 {row["Teknisi"]} OTW</div>', unsafe_allow_html=True)
                    elif row['Status'] == 'PENDING': 
                        st.markdown(f'<div class="status-pending">⏳ MENUNGGU VENDOR</div>', unsafe_allow_html=True)
    else:
        st.write("Belum ada data.")

# ================= MENU 3: TEKNISI (FULL COLOR & PDF) =================
elif menu == "🔧 Dashboard Teknisi":
    st.title("🔧 Dashboard ATEM")
    if st.button("🔄 Refresh"): st.rerun()
    df = load_data()
    
    if not df.empty:
        # --- 1. TIKET MASUK (WARNA-WARNI) ---
        st.subheader("📥 Tiket Masuk")
        
        # Sortir: Emergency paling atas
        prio_order = {"EMERGENCY": 0, "High (Urgent)": 1, "Normal": 2}
        df['prio_sort'] = df['Prioritas'].map(prio_order).fillna(3)
        tiket_open = df[df['Status'] == 'OPEN'].sort_values(by=['prio_sort', 'Waktu Lapor'])
        
        if tiket_open.empty:
            st.info("Tidak ada tiket baru. Aman!")
        else:
            for i, row in tiket_open.iterrows():
                # --- LOGIKA WARNA DI SINI ---
                with st.container(border=True):
                    # Kita pakai kolom layout
                    col_alert, col_info, col_action = st.columns([2, 3, 2])
                    
                    with col_alert:
                        # Tampilkan Kotak Berwarna Sesuai Prioritas
                        if row['Prioritas'] == 'EMERGENCY':
                            st.error(f"🚨 {row['Ruangan']} (DARURAT!)")
                        elif row['Prioritas'] == 'High (Urgent)':
                            st.warning(f"⚡ {row['Ruangan']} (URGENT)")
                        else:
                            st.info(f"🟢 {row['Ruangan']} (NORMAL)")
                        
                        st.write(f"🛠 **{row['Nama Alat']}**")
                        st.caption(f"ID: {row['ID Tiket']}")

                    with col_info:
                        st.write(f"📝 **Keluhan:** {row['Keluhan']}")
                        st.write(f"👤 Pelapor: {row['Pelapor']}")
                        st.write(f"🕒 Waktu: {row['Waktu Lapor']}")

                    with col_action:
                        st.write("---")
                        nama = st.selectbox("Teknisi:", ["Budi", "Andi", "Siti"], key=f"s{row['ID Tiket']}")
                        if st.button("🏃 AMBIL TUGAS", key=f"b{row['ID Tiket']}", type="primary"):
                            df.loc[df['ID Tiket']==row['ID Tiket'], 'Status']='ON PROGRESS'
                            df.loc[df['ID Tiket']==row['ID Tiket'], 'Teknisi']=nama
                            save_data(df)
                            kirim_notifikasi_telegram(f"✅ {row['ID Tiket']} diambil oleh {nama}")
                            st.rerun()

        st.markdown("---")
        
        # --- 2. SEDANG DIKERJAKAN (HEADER BERWARNA) ---
        st.subheader("🛠 Sedang Dikerjakan")
        tiket_prog = df[df['Status'] == 'ON PROGRESS']
        
        if tiket_prog.empty:
            st.caption("Belum ada pekerjaan yang diambil.")
        else:
            for i, row in tiket_prog.iterrows():
                with st.container(border=True):
                    # Header berwarna juga saat dikerjakan biar sadar urgensinya
                    if row['Prioritas'] == 'EMERGENCY':
                        st.error(f"🔧 PENGERJAAN: {row['Nama Alat']} - {row['Ruangan']} (DARURAT)")
                    elif row['Prioritas'] == 'High (Urgent)':
                        st.warning(f"🔧 PENGERJAAN: {row['Nama Alat']} - {row['Ruangan']} (HIGH)")
                    else:
                        st.info(f"🔧 PENGERJAAN: {row['Nama Alat']} - {row['Ruangan']}")
                    
                    # Form Penyelesaian
                    catatan = st.text_area(f"Laporan Pengerjaan ({row['ID Tiket']}):", key=f"cat_{row['ID Tiket']}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("📸 **Foto Bukti (Opsional):**")
                        foto = st.camera_input("Ambil Foto", key=f"cam_{row['ID Tiket']}")
                        if not foto:
                            foto = st.file_uploader("Atau Upload Foto", type=['jpg','png'], key=f"up_{row['ID Tiket']}")
                    
                    with c2:
                        st.write("✍️ **Tanda Tangan User (Wajib):**")
                        ttd = st_canvas(
                            fill_color="rgba(255, 165, 0, 0.3)",
                            stroke_width=2,
                            stroke_color="#000000",
                            background_color="#eeeeee",
                            height=150,
                            width=300,
                            drawing_mode="freedraw",
                            key=f"canvas_{row['ID Tiket']}"
                        )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("✅ SIMPAN & BUAT BERITA ACARA", key=f"done_{row['ID Tiket']}", type="primary"):
                            if ttd.image_data is None:
                                st.error("Mohon minta tanda tangan user dulu!")
                            else:
                                df.loc[df['ID Tiket']==row['ID Tiket'], 'Status']='DONE'
                                df.loc[df['ID Tiket']==row['ID Tiket'], 'Catatan']=catatan
                                save_data(df)
                                pdf_bytes = create_pdf(row, foto, ttd.image_data, catatan)
                                kirim_notifikasi_telegram(f"🎉 Tiket {row['ID Tiket']} SELESAI. Berita Acara telah dibuat.")
                                st.success("Pekerjaan Selesai! Silakan download Berita Acara di bawah.")
                                st.download_button(
                                    label="📄 DOWNLOAD PDF BERITA ACARA",
                                    data=pdf_bytes,
                                    file_name=f"Berita_Acara_{row['ID Tiket']}.pdf",
                                    mime='application/pdf'
                                )

# ================= MENU 4: ADMIN DATABASE & REKAP =================
elif menu == "🔐 Admin Database":
    st.title("🔐 Admin & Rekap Data")
    password = st.text_input("🔑 Masukkan Password Admin:", type="password")
    
    if password == PASSWORD_ADMIN:
        st.success("✅ Akses Diterima")
        
        # LINK KE GOOGLE SHEET ASLI (Opsional, isi jika mau)
        link_sheet = "https://docs.google.com/spreadsheets" 
        st.link_button("📂 Buka File Google Sheets Asli", link_sheet)
        
        df = load_data()
        
        tab1, tab2 = st.tabs(["🗑️ Manajemen Data", "📅 Rekap & Export Excel"])
        
        with tab1:
            st.subheader("📂 Semua Data Laporan (Real-time)")
            st.dataframe(df)
            st.warning("⚠️ Hati-hati! Data yang dihapus tidak bisa kembali.")
            list_id = df['ID Tiket'].tolist()
            pilih_id = st.selectbox("Pilih ID Tiket untuk dihapus:", ["-"] + list_id)
            if st.button("🗑️ HAPUS PERMANEN", type="primary"):
                if pilih_id != "-":
                    df_baru = df[df['ID Tiket'] != pilih_id]
                    save_data(df_baru)
                    st.success(f"✅ Data {pilih_id} berhasil dihapus dari Google Sheets!")
                    st.rerun()

        with tab2:
            st.subheader("📅 Download Laporan per Periode")
            col_date1, col_date2 = st.columns(2)
            with col_date1: tgl_mulai = st.date_input("Dari Tanggal:")
            with col_date2: tgl_akhir = st.date_input("Sampai Tanggal:")
            
            if st.button("🔍 Tampilkan Data"):
                try:
                    df_filter = df.copy()
                    df_filter['Tanggal_Saja'] = pd.to_datetime(df_filter['Waktu Lapor']).dt.date
                    mask = (df_filter['Tanggal_Saja'] >= tgl_mulai) & (df_filter['Tanggal_Saja'] <= tgl_akhir)
                    df_hasil = df_filter.loc[mask].drop(columns=['Tanggal_Saja'])
                    
                    if not df_hasil.empty:
                        st.success(f"Ditemukan {len(df_hasil)} laporan.")
                        st.dataframe(df_hasil)
                        csv = df_hasil.to_csv(index=False).encode('utf-8')
                        st.download_button(label="📥 DOWNLOAD REKAP (CSV)", data=csv, file_name=f"Rekap_{tgl_mulai}_sd_{tgl_akhir}.csv", mime='text/csv')
                    else:
                        st.warning("Tidak ada data.")
                except Exception as e:
                    st.error(f"Error tanggal: {e}")

    elif password:
        st.error("❌ Password Salah!")
