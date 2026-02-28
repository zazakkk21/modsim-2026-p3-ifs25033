import streamlit as st
import simpy
import random
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# ==========================
# KONFIGURASI
# ==========================
TOTAL_MEJA = 60
MAHASISWA_PER_MEJA = 3
TOTAL_OMPRENG = TOTAL_MEJA * MAHASISWA_PER_MEJA

START_TIME = datetime(2024, 1, 1, 7, 0)
random.seed(42)
np.random.seed(42)

# ==========================
# MODEL SIMULASI
# ==========================
class SimulasiPiket:
    def __init__(self):
        self.env = simpy.Environment()

        # 7 Petugas sesuai soal
        self.petugas_lauk = simpy.Resource(self.env, capacity=3)
        self.petugas_angkut = simpy.Resource(self.env, capacity=2)
        self.petugas_nasi = simpy.Resource(self.env, capacity=2)

        self.antrian_angkut = simpy.Store(self.env)
        self.data = []

    def waktu_real(self, waktu_sim):
        return START_TIME + timedelta(minutes=waktu_sim)

    # ==========================
    # PROSES ISI LAUK
    # ==========================
    def proses_lauk(self, id_ompreng, meja):
        with self.petugas_lauk.request() as req:
            yield req
            yield self.env.timeout(random.uniform(0.5, 1))  # 30–60 detik

        yield self.antrian_angkut.put((id_ompreng, meja))

    # ==========================
    # PROSES ANGKUT (4–7)
    # ==========================
    def proses_angkut(self):
        while True:
            if len(self.antrian_angkut.items) >= 4:

                jumlah_batch = random.randint(4, 7)
                batch_size = min(jumlah_batch, len(self.antrian_angkut.items))

                with self.petugas_angkut.request() as req:
                    yield req
                    yield self.env.timeout(random.uniform(0.33, 1))  # 20–60 detik

                for _ in range(batch_size):
                    id_ompreng, meja = yield self.antrian_angkut.get()
                    self.env.process(self.proses_nasi(id_ompreng, meja))
            else:
                yield self.env.timeout(0.1)

    # ==========================
    # PROSES NASI
    # ==========================
    def proses_nasi(self, id_ompreng, meja):
        with self.petugas_nasi.request() as req:
            yield req
            yield self.env.timeout(random.uniform(0.5, 1))  # 30–60 detik

        selesai = self.env.now
        self.data.append({
            "ID_Ompreng": id_ompreng,
            "Meja": meja,
            "Waktu_Selesai (Menit)": selesai,
            "Jam_Selesai": self.waktu_real(selesai)
        })

    # ==========================
    # JALANKAN SIMULASI
    # ==========================
    def run(self):
        for i in range(TOTAL_OMPRENG):
            meja = i // MAHASISWA_PER_MEJA + 1
            self.env.process(self.proses_lauk(i, meja))

        self.env.process(self.proses_angkut())
        self.env.run()

        return pd.DataFrame(self.data)

# ==========================
# DASHBOARD STREAMLIT
# ==========================
def main():
    st.set_page_config(page_title="Simulasi Piket IT Del", layout="wide", page_icon="🍽️")

    st.markdown("<h1 style='text-align:center;'>🍱 Simulasi Piket Kantin IT Del</h1>", unsafe_allow_html=True)

    if st.button("🚀 Jalankan Simulasi"):

        with st.spinner("Menjalankan simulasi produksi ompreng..."):
            simulasi = SimulasiPiket()
            df = simulasi.run()

        # ==========================
        # METRIK UTAMA
        # ==========================
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Ompreng", TOTAL_OMPRENG)
        col2.metric("Total Meja", TOTAL_MEJA)
        col3.metric("Jumlah Petugas", "7 Orang")
        col4.metric("Selesai Pada", df["Jam_Selesai"].max().strftime("%H:%M"))

        st.divider()

        # ==========================
        # GRAFIK
        # ==========================
        tab1, tab2 = st.tabs(["📊 Distribusi Waktu", "📈 Penyelesaian per Meja"])

        with tab1:
            fig1 = px.histogram(
                df,
                x="Waktu_Selesai (Menit)",
                nbins=20,
                title="Distribusi Waktu Penyelesaian Ompreng",
                labels={"Waktu_Selesai (Menit)": "Menit"}
            )
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            meja_group = df.groupby("Meja")["Waktu_Selesai (Menit)"].max().reset_index()

            fig2 = px.line(
                meja_group,
                x="Meja",
                y="Waktu_Selesai (Menit)",
                title="Waktu Penyelesaian Maksimum per Meja",
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("📄 Data Detail")
        st.dataframe(df, use_container_width=True)

    else:
        st.info("Klik tombol untuk menjalankan simulasi sistem piket sesuai studi kasus.")
        st.image("https://img.freepik.com/free-vector/data-report-concept-illustration_114360-883.jpg", width=400)

if __name__ == "__main__":
    main()
