import simpy
import random
import pandas as pd
from datetime import datetime, timedelta

# ==========================
# KONFIGURASI
# ==========================
TOTAL_MEJA = 60
MAHASISWA_PER_MEJA = 3
TOTAL_OMPRENG = TOTAL_MEJA * MAHASISWA_PER_MEJA

START_TIME = datetime(2024, 1, 1, 7, 0)

random.seed(42)

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
    # PROSES OMPreng
    # ==========================
    def proses_ompreng(self, id_ompreng):
        waktu_mulai = self.env.now

        # 1️⃣ Isi Lauk (30–60 detik)
        with self.petugas_lauk.request() as req:
            yield req
            waktu_lauk = random.uniform(0.5, 1)  # menit
            yield self.env.timeout(waktu_lauk)

        # Masuk antrian angkut
        yield self.antrian_angkut.put(id_ompreng)

    # ==========================
    # PROSES ANGKUT (Batch 4–7)
    # ==========================
    def proses_angkut(self):
        while True:
            if len(self.antrian_angkut.items) >= 4:
                jumlah = random.randint(4, 7)
                batch = min(jumlah, len(self.antrian_angkut.items))

                with self.petugas_angkut.request() as req:
                    yield req
                    waktu_angkut = random.uniform(0.33, 1)  # 20–60 detik
                    yield self.env.timeout(waktu_angkut)

                for _ in range(batch):
                    ompreng = yield self.antrian_angkut.get()
                    self.env.process(self.proses_nasi(ompreng))
            else:
                yield self.env.timeout(0.1)

    # ==========================
    # PROSES NASI
    # ==========================
    def proses_nasi(self, id_ompreng):
        with self.petugas_nasi.request() as req:
            yield req
            waktu_nasi = random.uniform(0.5, 1)
            yield self.env.timeout(waktu_nasi)

        selesai = self.env.now
        self.data.append({
            "ID_Ompreng": id_ompreng,
            "Waktu_Selesai (Menit)": selesai,
            "Jam_Selesai": self.waktu_real(selesai)
        })

    # ==========================
    # JALANKAN SIMULASI
    # ==========================
    def run(self):
        # Buat semua ompreng langsung (tidak pakai kedatangan acak)
        for i in range(TOTAL_OMPRENG):
            self.env.process(self.proses_ompreng(i))

        # Jalankan proses angkut paralel
        self.env.process(self.proses_angkut())

        self.env.run()

        return pd.DataFrame(self.data)


# ==========================
# MAIN
# ==========================
simulasi = SimulasiPiket()
hasil = simulasi.run()

print("Total Ompreng:", len(hasil))
print("Selesai pada:", hasil["Jam_Selesai"].max())
