import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Tzu Chi MedFix", page_icon="🏥", layout="wide")

# --- STYLE CSS & AUDIO ---
st.markdown("""
<style>
    .stButton>button { width: 100%; height: 3em; font-weight: bold; }
    .emergency-box {
        background-color: #ff4b4b; color: white; padding: 15px;
        border-radius: 10px; text-align: center; font-size: 20px; font-weight: 900;
        animation: blinker 1s linear infinite;
    }
    .status-otw {
        background-color: #ffd700; color: black; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;
    }
    @keyframes blinker { 50% { opacity: 0.8; } }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
file_db = 'database_laporan.xlsx'

# Cek kolom database, pastikan Nomor Serial ada
if not os.path.exists(file_db):
    df_init = pd.DataFrame(columns=[
        "ID Tiket", "Waktu Lapor", "Pelapor", "Ruangan", 
        "Nama Alat", "Nomor Serial", "Keluhan", "Prioritas", "Status", "Teknisi", "Catatan"
    ])
    df_init.to_excel(file_db, index=False)

# --- FUNGSI LOAD & SAVE ---
def load_data():
    return pd.read_excel(file_db)

def save_data(df):
    df.to_excel(file_db, index=False)

# --- SIDEBAR (MENU) ---
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Pilih Menu:", ["📝 Buat Laporan", "🔍 Cek Status Laporan", "🔧 Dashboard Teknisi"])

# ================= MENU 1: USER PELAPOR (BUAT) =================
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
                    "Nomor Serial": "-", # Emergency tidak perlu isi serial
                    "Keluhan": "DARURAT",
                    "Prioritas": "EMERGENCY", "Status": "OPEN", "Teknisi": "-", "Catatan": "-"
                }])
                save_data(pd.concat([df, new_data], ignore_index=True))
                st.error(f"🚨 SINYAL TERKIRIM! Mohon tunggu di {ruangan}.")
    else:
        st.title("📝 Lapor Kerusakan Rutin")
        with st.form("form_laporan"):
            col1, col2 = st.columns(2)
            with col1:
                pelapor = st.text_input("Nama Pelapor")
                ruangan = st.selectbox("Lokasi", ["ICU", "IGD", "OK", "Rawat Inap", "Poli", "Radiologi"])
            with col2:
                nama_alat = st.text_input("Nama Alat")
                # --- UPDATE: Input Nomor Serial ---
                no_serial = st.text_input("Nomor Serial / SN Alat")
                prioritas = st.selectbox("Prioritas", ["Normal", "High (Urgent)"])
            
            keluhan = st.text_area("Keluhan")
            
            if st.form_submit_button("Kirim Laporan"):
                df = load_data()
                new_id = f"TC-{len(df)+1:03d}"
                waktu = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # Simpan data termasuk Nomor Serial
                new_data = pd.DataFrame([{
                    "ID Tiket": new_id, "Waktu Lapor": waktu, "Pelapor": pelapor,
                    "Ruangan": ruangan, "Nama Alat": nama_alat, 
                    "Nomor Serial": no_serial if no_serial else "-", 
                    "Keluhan": keluhan,
                    "Prioritas": prioritas, "Status": "OPEN", "Teknisi": "-", "Catatan": "-"
                }])
                save_data(pd.concat([df, new_data], ignore_index=True))
                st.success(f"✅ Laporan Terkirim! ID: {new_id}")

# ================= MENU 2: USER PELAPOR (CEK STATUS) =================
elif menu == "🔍 Cek Status Laporan":
    st.title("🔍 Cek Status Laporan")
    st.info("Lihat apakah teknisi sudah merespon panggilan Anda.")
    
    df = load_data()
    df_aktif = df[df['Status'] != 'DONE'].sort_values(by='Waktu Lapor', ascending=False)
    
    for index, row in df_aktif.iterrows():
        with st.container(border=True):
            cols = st.columns([1, 3, 2])
            with cols[0]:
                st.write(f"**{row['ID Tiket']}**")
                if row['Prioritas'] == 'EMERGENCY':
                    st.error("DARURAT")
            
            with cols[1]:
                # Tampilkan Serial Number di sini juga
                sn_text = f"(SN: {row['Nomor Serial']})" if row['Nomor Serial'] != "-" else ""
                st.write(f"📍 **{row['Ruangan']}** - {row['Nama Alat']} {sn_text}")
                st.caption(f"Pelapor: {row['Pelapor']} | {row['Waktu Lapor']}")
            
            with cols[2]:
                if row['Status'] == 'OPEN':
                    st.warning("⏳ Menunggu Teknisi")
                elif row['Status'] == 'ON PROGRESS':
                    st.markdown(f'<div class="status-otw">🏃 {row["Teknisi"]} SEDANG MENUJU LOKASI</div>', unsafe_allow_html=True)

# ================= MENU 3: TEKNISI (AUTO REFRESH & BUNYI) =================
elif menu == "🔧 Dashboard Teknisi":
    st.title("🔧 Dashboard ATEM")
    
    if st.button("🔄 Refresh Data (Cek Tiket Baru)"):
        st.rerun()

    df = load_data()
    
    # Notifikasi Bunyi
    ada_darurat = not df[(df['Prioritas'] == 'EMERGENCY') & (df['Status'] == 'OPEN')].empty
    if ada_darurat:
        st.markdown("""
            <audio autoplay loop>
                <source src="https://www.soundjay.com/buttons/sounds/beep-07.mp3" type="audio/mpeg">
            </audio>
            <div class="emergency-box">🚨 ADA PANGGILAN DARURAT BARU! CEK BAWAH! 🚨</div>
        """, unsafe_allow_html=True)
    
    # --- TIKET MASUK ---
    st.subheader("📥 Tiket Masuk (Belum Diambil)")
    tiket_open = df[df['Status'] == 'OPEN'].sort_values(by='Prioritas')
    
    if tiket_open.empty:
        st.info("Belum ada tiket baru.")
    else:
        for index, row in tiket_open.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 2])
                with c1:
                    if row['Prioritas'] == 'EMERGENCY':
                        st.error(f"🚨 {row['Ruangan']} (DARURAT)")
                    else:
                        st.write(f"📍 **{row['Ruangan']}**")
                    
                    # Tampilkan SN di Dashboard Teknisi
                    sn_display = f"SN: {row['Nomor Serial']}" if row['Nomor Serial'] != "-" else ""
                    st.write(f"🛠 **{row['Nama Alat']}**")
                    if sn_display:
                        st.caption(f"🆔 {sn_display}")
                        
                    st.write(f"📝 {row['Keluhan']}")
                
                with c2:
                    st.write(f"🕒 {row['Waktu Lapor']}")
                    st.write(f"👤 {row['Pelapor']}")
                
                with c3:
                    st.write("Ambil Pekerjaan Ini:")
                    nama_teknisi = st.selectbox(f"Siapa yang berangkat? ({row['ID Tiket']})", 
                                                ["Budi", "Andi", "Siti", "Magang"], 
                                                key=f"sel_{row['ID Tiket']}")
                    
                    if st.button(f"🏃 SAYA BERANGKAT ({row['ID Tiket']})", key=f"btn_{row['ID Tiket']}", type="primary"):
                        df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'ON PROGRESS'
                        df.loc[df['ID Tiket'] == row['ID Tiket'], 'Teknisi'] = nama_teknisi
                        save_data(df)
                        st.success(f"Selamat bekerja {nama_teknisi}!")
                        st.rerun()

    st.markdown("---")
    
    # --- SEDANG DIKERJAKAN ---
    st.subheader("🛠 Sedang Dikerjakan")
    tiket_progress = df[df['Status'] == 'ON PROGRESS']
    
    for index, row in tiket_progress.iterrows():
         with st.container(border=True):
            cols = st.columns([4, 2])
            with cols[0]:
                sn_info = f"(SN: {row['Nomor Serial']})" if row['Nomor Serial'] != "-" else ""
                st.write(f"**{row['ID Tiket']}** - {row['Ruangan']}")
                st.write(f"🛠 {row['Nama Alat']} {sn_info}")
                st.info(f"Dihandle oleh: **{row['Teknisi']}**")
            with cols[1]:
                if st.button("✅ SELESAI", key=f"done_{row['ID Tiket']}"):
                    df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'DONE'
                    save_data(df)
                    st.success("Pekerjaan Selesai!")
                    st.rerun()


    # Download #
    st.markdown("---")
    st.subheader("📂 Manajemen Data")
    
    # Tombol Download
    with open(file_db, "rb") as f:
        st.download_button(
            label="📥 Download Database Excel",
            data=f,
            file_name="backup_laporan_tzuchi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )