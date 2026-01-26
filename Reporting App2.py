import streamlit as st
import pandas as pd
import os
import requests # Library untuk kirim ke Telegram
from datetime import datetime

# ==========================================
# ⚙️ KONFIGURASI TELEGRAM (WAJIB DIISI!)
# ==========================================
# Masukkan Token & ID yang sudah kamu dapatkan sebelumnya
BOT_TOKEN = "8433442999:AAGjTv0iZEm_xtvlQTUBT11PUyxUYMtGxFQ" 
CHAT_ID = "-1003692690153"
# ==========================================

# --- FUNGSI KIRIM PESAN ---
def kirim_notifikasi_telegram(pesan):
    try:
        if "GANTI" in BOT_TOKEN or "GANTI" in CHAT_ID:
            st.error("⚠️ TOKEN/CHAT ID BELUM DIISI DI KODINGAN!")
            return False

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return True
        else:
            st.error(f"❌ Gagal Kirim! Telegram bilang: {response.text}")
            return False
            
    except Exception as e:
        st.error(f"Error Koneksi: {e}")
        return False

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Tzu Chi MedFix", page_icon="🏥", layout="wide")

# --- STYLE CSS ---
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
    .status-pending {
        background-color: #6c757d; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;
    }
    @keyframes blinker { 50% { opacity: 0.8; } }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
file_db = 'database_laporan.xlsx'

def load_data():
    if os.path.exists(file_db):
        return pd.read_excel(file_db)
    else:
        return pd.DataFrame(columns=[
            "ID Tiket", "Waktu Lapor", "Pelapor", "Ruangan", 
            "Nama Alat", "Nomor Serial", "Keluhan", "Prioritas", "Status", "Teknisi", "Catatan"
        ])

def save_data(df):
    df.to_excel(file_db, index=False)

# --- SIDEBAR (MENU) ---
st.sidebar.title("🏥 Navigasi")
menu = st.sidebar.radio("Pilih Menu:", ["📝 Buat Laporan", "🔍 Cek Status Laporan", "🔧 Dashboard Teknisi"])

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
                    # TAMPILKAN CATATAN TEKNISI JIKA ADA
                    if row['Catatan'] != "-" and pd.notna(row['Catatan']):
                        st.info(f"📝 **Catatan Teknisi:** {row['Catatan']}")
                with cols[2]:
                    if row['Status'] == 'OPEN': st.write("⏳ Menunggu Teknisi")
                    elif row['Status'] == 'ON PROGRESS': st.markdown(f'<div class="status-otw">🏃 {row["Teknisi"]} OTW</div>', unsafe_allow_html=True)
                    elif row['Status'] == 'PENDING': 
                        st.markdown(f'<div class="status-pending">⏳ MENUNGGU VENDOR</div>', unsafe_allow_html=True)
                        st.caption(f"Pending oleh: {row['Teknisi']}")
    else:
        st.write("Belum ada data.")

# ================= MENU 3: TEKNISI =================
elif menu == "🔧 Dashboard Teknisi":
    st.title("🔧 Dashboard ATEM")
    if st.button("🔄 Refresh Data"): st.rerun()

    df = load_data()
    if not df.empty:
        # --- 1. TIKET MASUK ---
        st.subheader("📥 Tiket Masuk")
        prio_order = {"EMERGENCY": 0, "High (Urgent)": 1, "Normal": 2}
        df['prio_sort'] = df['Prioritas'].map(prio_order)
        tiket_open = df[df['Status'] == 'OPEN'].sort_values(by=['prio_sort', 'Waktu Lapor'])
        
        if tiket_open.empty:
            st.info("Aman terkendali.")
        else:
            for index, row in tiket_open.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 2])
                    with c1:
                        if row['Prioritas'] == 'EMERGENCY': st.error(f"🚨 {row['Ruangan']}")
                        elif row['Prioritas'] == 'High (Urgent)': st.warning(f"⚡ {row['Ruangan']}")
                        else: st.info(f"🟢 {row['Ruangan']}")
                        st.write(f"🛠 **{row['Nama Alat']}**")
                        st.write(f"📝 {row['Keluhan']}")
                    with c2:
                        st.write(f"🕒 {row['Waktu Lapor']}")
                        st.write(f"👤 {row['Pelapor']}")
                    with c3:
                        nama = st.selectbox(f"Teknisi:", ["Budi", "Andi", "Siti", "Magang"], key=f"s{row['ID Tiket']}")
                        if st.button(f"AMBIL TUGAS", key=f"b{row['ID Tiket']}", type="primary"):
                            df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'ON PROGRESS'
                            df.loc[df['ID Tiket'] == row['ID Tiket'], 'Teknisi'] = nama
                            save_data(df)
                            kirim_notifikasi_telegram(f"✅ Tiket `{row['ID Tiket']}` diambil oleh **{nama}**.")
                            st.rerun()

        st.markdown("---")
        
        # --- 2. SEDANG DIKERJAKAN ---
        st.subheader("🛠 Sedang Dikerjakan")
        tiket_progress = df[df['Status'] == 'ON PROGRESS']
        
        if tiket_progress.empty:
            st.caption("Tidak ada pekerjaan aktif.")
        else:
            for index, row in tiket_progress.iterrows():
                 with st.container(border=True):
                    cols = st.columns([3, 2])
                    with cols[0]:
                        sn_info = f"(SN: {row['Nomor Serial']})" if row['Nomor Serial'] != "-" else ""
                        st.write(f"**{row['ID Tiket']}** - {row['Ruangan']}") 
                        st.write(f"🛠 {row['Nama Alat']} {sn_info}")
                        st.info(f"Oleh: **{row['Teknisi']}**")
                    with cols[1]:
                        # --- INPUT CATATAN ---
                        # Teknisi bisa mengetik catatan di sini
                        catatan_baru = st.text_input(f"📝 Catatan / Tindakan ({row['ID Tiket']}):", key=f"note_{row['ID Tiket']}")
                        
                        # TOMBOL SELESAI
                        if st.button("✅ SELESAI", key=f"d{row['ID Tiket']}", type="primary"):
                            df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'DONE'
                            # Simpan catatan jika ada isi
                            if catatan_baru:
                                df.loc[df['ID Tiket'] == row['ID Tiket'], 'Catatan'] = catatan_baru
                            
                            save_data(df)
                            # Kirim Telegram dengan catatan
                            msg = f"🎉 Tiket `{row['ID Tiket']}` SELESAI diperbaiki oleh {row['Teknisi']}."
                            if catatan_baru:
                                msg += f"\n\n📝 *Tindakan:* {catatan_baru}"
                            kirim_notifikasi_telegram(msg)
                            st.rerun()
                        
                        # TOMBOL PENDING
                        if st.button("⏳ PENDING (VENDOR/SPAREPART)", key=f"p{row['ID Tiket']}"):
                            df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'PENDING'
                            if catatan_baru:
                                df.loc[df['ID Tiket'] == row['ID Tiket'], 'Catatan'] = catatan_baru
                            
                            save_data(df)
                            msg = f"⚠️ Tiket `{row['ID Tiket']}` DIPENDING oleh {row['Teknisi']}."
                            if catatan_baru:
                                msg += f"\n\n📝 *Alasan:* {catatan_baru}"
                            else:
                                msg += "\n(Menunggu Vendor/Sparepart)"
                            kirim_notifikasi_telegram(msg)
                            st.rerun()

        st.markdown("---")

        # --- 3. DAFTAR PENDING ---
        st.subheader("⏳ Ditunda / Menunggu Vendor")
        tiket_pending = df[df['Status'] == 'PENDING']

        if tiket_pending.empty:
            st.caption("Tidak ada tiket yang dipending.")
        else:
             for index, row in tiket_pending.iterrows():
                 with st.container(border=True):
                    cols = st.columns([3, 2])
                    with cols[0]:
                        st.markdown(f"**{row['ID Tiket']}** - {row['Ruangan']} (PENDING)")
                        st.write(f"🛠 {row['Nama Alat']}")
                        if row['Catatan'] != "-" and pd.notna(row['Catatan']):
                             st.warning(f"📝 Catatan: {row['Catatan']}")
                        st.caption(f"Teknisi Terakhir: {row['Teknisi']}")
                    with cols[1]:
                        if st.button("▶️ LANJUT KERJAKAN", key=f"res{row['ID Tiket']}"):
                            df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'ON PROGRESS'
                            save_data(df)
                            kirim_notifikasi_telegram(f"▶️ Tiket `{row['ID Tiket']}` DILANJUTKAN kembali oleh {row['Teknisi']}.")
                            st.rerun()
                            
                        if st.button("✅ SELESAI DARI VENDOR", key=f"vend{row['ID Tiket']}"):
                            df.loc[df['ID Tiket'] == row['ID Tiket'], 'Status'] = 'DONE'
                            save_data(df)
                            kirim_notifikasi_telegram(f"🎉 Tiket `{row['ID Tiket']}` SELESAI (Setelah dari Vendor).")
                            st.rerun()

        st.markdown("---")
        if os.path.exists(file_db):
            with open(file_db, "rb") as f:
                st.download_button("📥 Download Excel", f, "laporan_atem.xlsx")
