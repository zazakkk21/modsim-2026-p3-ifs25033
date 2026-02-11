import streamlit as st
import simpy
import random
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass
import plotly.express as px
import plotly.graph_objects as go

# ============================
# KONFIGURASI SIMULASI
# ============================
@dataclass
class Config:
    NUM_MAHASISWA: int = 500
    NUM_OMPRENG: int = 180 
    NUM_STAFF_PER_KELOMPOK: int = 2
    NUM_KELOMPOK: int = 2
    MIN_SERVICE_TIME: float = 1.0
    MAX_SERVICE_TIME: float = 3.0
    MEAN_INTERARRIVAL: float = 120 / 500
    START_HOUR: int = 7
    START_MINUTE: int = 0
    RANDOM_SEED: int = 42

# ============================
# MODEL SIMULASI (LOGIKA TETAP)
# ============================
class KantinPrasmananDES:
    def __init__(self, config: Config):
        self.config = config
        self.env = simpy.Environment()
        self.petugas_lauk = simpy.Resource(self.env, capacity=3)
        self.petugas_angkut = simpy.Resource(self.env, capacity=2)
        self.petugas_nasi = simpy.Resource(self.env, capacity=2)
        self.antrian_angkut = simpy.Store(self.env)
        self.kelompok_staff = [simpy.Resource(self.env, capacity=config.NUM_STAFF_PER_KELOMPOK) for _ in range(config.NUM_KELOMPOK)]
        self.antrian = simpy.Store(self.env)
        self.statistics = {'mahasiswa_data': [], 'queue_lengths': []}
        self.start_time = datetime(2024, 1, 1, config.START_HOUR, config.START_MINUTE)
        random.seed(config.RANDOM_SEED)
        np.random.seed(config.RANDOM_SEED)

    def waktu_ke_jam(self, waktu_simulasi: float) -> datetime:
        return self.start_time + timedelta(minutes=waktu_simulasi)

    def proses_mahasiswa(self, mahasiswa_id):
        waktu_datang = self.env.now
        # Alur Lauk -> Angkut -> Nasi
        with self.petugas_lauk.request() as req:
            yield req
            yield self.env.timeout(random.uniform(0.5, 1))
        yield self.antrian_angkut.put(mahasiswa_id)
        if len(self.antrian_angkut.items) >= 4:
            with self.petugas_angkut.request() as req:
                yield req
                yield self.env.timeout(random.uniform(0.3, 0.8))
                for _ in range(min(5, len(self.antrian_angkut.items))): yield self.antrian_angkut.get()
        with self.petugas_nasi.request() as req:
            yield req
            yield self.env.timeout(random.uniform(0.5, 1))

        # Antrian Utama
        yield self.antrian.put(mahasiswa_id)
        self.statistics['queue_lengths'].append({'time': self.env.now, 'length': len(self.antrian.items)})
        
        kelompok_idx = np.argmin([k.count for k in self.kelompok_staff])
        waktu_mulai = self.env.now
        with self.kelompok_staff[kelompok_idx].request() as req:
            yield req
            svc = random.uniform(self.config.MIN_SERVICE_TIME, self.config.MAX_SERVICE_TIME)
            yield self.env.timeout(svc)
        
        yield self.antrian.get()
        self.statistics['mahasiswa_data'].append({
            'id': mahasiswa_id, 'datang': waktu_datang, 'mulai': waktu_mulai,
            'selesai': self.env.now, 'tunggu': waktu_mulai - waktu_datang,
            'layanan': svc, 'kelompok': kelompok_idx + 1
        })

    def proses_kedatangan(self):
        for i in range(self.config.NUM_MAHASISWA):
            self.env.process(self.proses_mahasiswa(i))
            yield self.env.timeout(random.expovariate(1.0 / self.config.MEAN_INTERARRIVAL))

    def run_simulation(self):
        self.env.process(self.proses_kedatangan())
        self.env.run()
        df = pd.DataFrame(self.statistics['mahasiswa_data'])
        df['jam_selesai'] = df['selesai'].apply(lambda x: self.waktu_ke_jam(x))
        return df

# ============================
# TAMPILAN DASHBOARD
# ============================
def main():
    st.set_page_config(page_title="Dashboard Kantin IT Del", layout="wide", page_icon="🍽️")

    # Styling Metrik
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 28px; color: #007BFF; }
        .main-header { font-size: 36px; font-weight: bold; color: #1E1E1E; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.image("https://www.del.ac.id/wp-content/uploads/2021/05/Logo-IT-Del.png", width=100)
        st.title("Settings")
        with st.expander("👥 Populasi & Staff", expanded=True):
            n_mhs = st.number_input("Jumlah Mahasiswa", 50, 1000, 500)
            n_kel = st.slider("Jumlah Kelompok Staff", 1, 5, 2)
            n_stf = st.slider("Staff per Kelompok", 1, 5, 2)
        with st.expander("⏱️ Waktu Layanan", expanded=False):
            min_s = st.slider("Min (menit)", 0.5, 3.0, 1.0)
            max_s = st.slider("Max (menit)", 3.1, 10.0, 5.0)
        run_btn = st.button("🚀 Jalankan Simulasi", use_container_width=True, type="primary")

    st.markdown('<div class="main-header">🍽️ Dashboard Simulasi Kantin IT Del</div>', unsafe_allow_html=True)

    if run_btn:
        config = Config(NUM_MAHASISWA=n_mhs, NUM_KELOMPOK=n_kel, NUM_STAFF_PER_KELOMPOK=n_stf, MIN_SERVICE_TIME=min_s, MAX_SERVICE_TIME=max_s)
        model = KantinPrasmananDES(config)
        
        with st.spinner("Mengkalkulasi aliran mahasiswa..."):
            df = model.run_simulation()

        # BARIS METRIK UTAMA
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rata-rata Tunggu", f"{df['tunggu'].mean():.2f} min", "⏱️")
        m2.metric("Selesai Simulasi", df['jam_selesai'].max().strftime('%H:%M'), "🏁")
        m3.metric("Maksimal Antrian", f"{int(pd.DataFrame(model.statistics['queue_lengths'])['length'].max())} org", "🧍")
        m4.metric("Total Terlayani", f"{len(df)} Mhs", "✅")

        st.divider()

        # TAB LAYOUT
        tab1, tab2, tab3 = st.tabs(["📊 Analisis Grafik", "📈 Tren Antrian", "📄 Data Mentah"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                fig1 = px.histogram(df, x='tunggu', nbins=20, title="Distribusi Waktu Tunggu", 
                                   color_discrete_sequence=['#636EFA'], labels={'tunggu':'Menit'})
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                # Beban Kerja per Kelompok
                util = df.groupby('kelompok').size().reset_index(name='jumlah')
                fig2 = px.pie(util, values='jumlah', names='kelompok', title="Distribusi Beban Kerja Staff",
                             hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            q_df = pd.DataFrame(model.statistics['queue_lengths'])
            fig3 = px.line(q_df, x='time', y='length', title="Dinamika Panjang Antrian Sepanjang Waktu",
                          line_shape='spline', render_mode='svg')
            fig3.update_traces(line_color='#EF553B')
            st.plotly_chart(fig3, use_container_width=True)

        with tab3:
            st.subheader("Detail Log Per Mahasiswa")
            st.dataframe(df.style.background_gradient(subset=['tunggu'], cmap='YlOrRd'), use_container_width=True)
            
    else:
        st.info("Silakan atur parameter di sebelah kiri dan klik tombol **Jalankan Simulasi** untuk melihat hasil.")
        st.image("https://img.freepik.com/free-vector/data-report-concept-illustration_114360-883.jpg", width=400)

if __name__ == "__main__":
    main()