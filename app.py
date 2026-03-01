import streamlit as st
import simpy
import random
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# =========================
# PARAMETER SISTEM
# =========================
TOTAL_MEJA = 60
MAHASISWA_PER_MEJA = 3
TOTAL_OMPRENG = TOTAL_MEJA * MAHASISWA_PER_MEJA

WAKTU_LAUK = (0.5, 1)       # 30–60 detik
WAKTU_ANGKUT = (0.33, 1)    # 20–60 detik
WAKTU_NASI = (0.5, 1)

START_TIME = datetime(2024, 1, 1, 7, 0)

# =========================
# MODEL SIMULASI
# =========================
class SistemPiket:
    def __init__(self, env):
        self.env = env

        # 7 Petugas
        self.petugas_lauk = simpy.Resource(env, capacity=3)
        self.petugas_angkut = simpy.Resource(env, capacity=2)
        self.petugas_nasi = simpy.Resource(env, capacity=2)

        self.antrian_angkut = simpy.Store(env)
        self.hasil = []

    def waktu_real(self, menit):
        return START_TIME + timedelta(minutes=menit)

    def isi_lauk(self, id_ompreng, meja):
        with self.petugas_lauk.request() as req:
            yield req
            yield self.env.timeout(random.uniform(*WAKTU_LAUK))

        yield self.antrian_angkut.put((id_ompreng, meja))

    def proses_angkut(self):
        while len(self.hasil) < TOTAL_OMPRENG:

            if len(self.antrian_angkut.items) >= 4:
                batch = random.randint(4, 7)
                batch_size = min(batch, len(self.antrian_angkut.items))

                with self.petugas_angkut.request() as req:
                    yield req
                    yield self.env.timeout(random.uniform(*WAKTU_ANGKUT))

                for _ in range(batch_size):
                    id_ompreng, meja = yield self.antrian_angkut.get()
                    self.env.process(self.isi_nasi(id_ompreng, meja))
            else:
                yield self.env.timeout(0.1)

    def isi_nasi(self, id_ompreng, meja):
        with self.petugas_nasi.request() as req:
            yield req
            yield self.env.timeout(random.uniform(*WAKTU_NASI))

        selesai = self.env.now
        self.hasil.append({
            "ID_Ompreng": id_ompreng,
            "Meja": meja,
            "Selesai (Menit)": selesai,
            "Jam_Selesai": self.waktu_real(selesai)
        })

# =========================
# FUNGSI JALANKAN SIMULASI
# =========================
def run_simulation():
    random.seed(42)

    env = simpy.Environment()
    sistem = SistemPiket(env)

    for i in range(TOTAL_OMPRENG):
        meja = i // MAHASISWA_PER_MEJA + 1
        env.process(sistem.isi_lauk(i, meja))

    env.process(sistem.proses_angkut())
    env.run()

    return pd.DataFrame(sistem.hasil)

# =========================
# STREAMLIT APP
# =========================
def main():
    st.set_page_config(page_title="Simulasi Piket IT Del", layout="wide")

    st.title("🍱 Simulasi Sistem Piket IT Del")
    st.write("Simulasi Discrete Event berdasarkan studi kasus 60 meja dan 7 petugas.")

    if st.button("🚀 Jalankan Simulasi"):

        with st.spinner("Simulasi sedang berjalan..."):
            df = run_simulation()

        # =========================
        # METRIK
        # =========================
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Ompreng", TOTAL_OMPRENG)
        col2.metric("Total Meja", TOTAL_MEJA)
        col3.metric("Jumlah Petugas", "7 Orang")
        col4.metric("Selesai Pada", df["Jam_Selesai"].max().strftime("%H:%M"))

        st.divider()

        # =========================
        # GRAFIK 1 - Distribusi Waktu
        # =========================
        fig1 = px.histogram(
            df,
            x="Selesai (Menit)",
            nbins=20,
            title="Distribusi Waktu Penyelesaian"
        )
        st.plotly_chart(fig1, use_container_width=True)

        # =========================
        # GRAFIK 2 - Waktu Maks per Meja
        # =========================
        meja_df = df.groupby("Meja")["Selesai (Menit)"].max().reset_index()

        fig2 = px.line(
            meja_df,
            x="Meja",
            y="Selesai (Menit)",
            markers=True,
            title="Waktu Penyelesaian Maksimum per Meja"
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        st.subheader("📄 Data Detail")
        st.dataframe(df, use_container_width=True)

    else:
        st.info("Klik tombol untuk menjalankan simulasi.")

if __name__ == "__main__":
    main()
