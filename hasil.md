# Analisis Pola Penyebaran Narasi Politik pada Aplikasi X

Dokumen ini menyajikan hasil analisis pola penyebaran narasi politik di platform X (Twitter) pada dataset percakapan Pilpres 2024. Fokus utama analisis ini adalah membaca **pola hubungan antarakun** berdasarkan kemiripan narasi dan kedekatan waktu unggahan—bukan untuk memberi label identitas tertentu kepada akun, seperti bot, buzzer, atau afiliasi politik.

Istilah **koordinasi** dalam laporan ini merujuk pada pola graf: sekelompok akun terhubung karena mengunggah teks yang mirip dalam rentang waktu berdekatan, atau karena me-retweet dari sumber yang sama. Analisis ini membaca pola perilaku di data, **bukan** motif atau identitas asli pemilik akun.

Seluruh angka dan interpretasi dalam dokumen ini berasal dari output proyek yang sudah tersedia, terutama:

- `cleaned_data.csv`
- `data_audit.csv`
- `relation.csv`
- `relation_evidence.csv`
- `cluster_density_report.csv`
- `visualisasi_finale.html`

---

## 1. Gambaran Sumber Data

Data berasal dari tiga file JSON yang masing-masing mewakili satu query kandidat:

| File | Label Query |
|---|---|
| `data-twit-anies.json` | `anies` |
| `data-twit-ganjar.json` | `ganjar` |
| `data-twit-prabowo.json` | `prabowo` |

Perlu dicatat bahwa pipeline tidak melakukan crawling secara langsung. Script hanya membaca file JSON yang sudah tersedia di folder data. Oleh karena itu, hasil analisis ini berlaku untuk dataset tersebut, bukan untuk keseluruhan percakapan politik di platform X.

---

## 2. Ringkasan Dataset

Dataset berisi **1.002 tweet** dari **584 akun unik**, seluruhnya dalam rentang waktu sekitar **21 menit** (2024-01-04, pukul 17:59–18:21 UTC).

| Metrik | Nilai |
|---|---:|
| Total tweet | 1.002 |
| Akun unik | 584 |
| Waktu awal | 2024-01-04 17:59:59 UTC |
| Waktu akhir | 2024-01-04 18:21:20 UTC |
| Jumlah retweet | 563 |
| Rasio retweet | 56,2% |
| Reply / mention | 661 |

Secara jumlah, setiap query menyumbang 334 tweet. Namun, komposisi retweet antarquery tidak seimbang:

| Query | Tweet | Akun Unik | Retweet | Reply/Mention |
|---|---:|---:|---:|---:|
| `anies` | 334 | 187 | 302 | 325 |
| `ganjar` | 334 | 255 | 34 | 54 |
| `prabowo` | 334 | 199 | 227 | 282 |

Query `anies` dan `prabowo` didominasi retweet, sementara query `ganjar` jauh lebih banyak berisi tweet non-retweet. Perbedaan ini penting karena retweet secara alami menghasilkan teks yang identik—sehingga jika dicampur dengan analisis kemiripan narasi, kluster bisa terlihat sangat kuat padahal penyebab utamanya hanya karena banyak akun me-retweet unggahan yang sama. Itulah alasan proyek ini memisahkan kedua jenis hubungan tersebut.

---

## 3. Cara Data Disiapkan

Pipeline membaca semua file dengan pola `data-twit-*.json`, lalu menggabungkan tweet dari ketiga file dan mengurutkannya berdasarkan waktu unggah (`date_created`). Pengurutan ini penting karena analisis tidak hanya melihat kemiripan teks, tetapi juga memperhitungkan kedekatan waktu antarunggahan.

Teks tweet kemudian dibersihkan menjadi dua versi:

| Kolom | Fungsi |
|---|---|
| `cleaned_content` | Digunakan untuk menghitung kemiripan semantik (embedding) |
| `topic_content` | Digunakan untuk mengekstrak kata kunci dan topik kluster |

`cleaned_content` menghapus marker `RT`, pola reply seperti `[RE username]`, URL, dan spasi berlebih, agar model embedding lebih fokus pada isi narasi. `topic_content` dibersihkan lebih ketat lagi: mention dihapus, karakter non-alfanumerik dibuang, dan token pendek dihilangkan, sehingga URL dan mention tidak mendominasi hasil kata kunci.

---

## 4. Pengukuran Kemiripan dan Kedekatan Waktu

Untuk mengukur kemiripan isi narasi, proyek ini menggunakan model embedding multilingual:

```
symanto/sn-xlm-roberta-base-snli-mnli-anli-xnli
```

Setiap `cleaned_content` diubah menjadi representasi vektor. Kemiripan antartweet dihitung menggunakan *cosine similarity*, yang disimpan sebagai `s_text`. Nilai mendekati 1,0 menunjukkan narasi yang sangat mirip secara semantik.

Selain kemiripan teks, selisih waktu unggah juga diperhitungkan:

```
s_time = exp(−0.001155 × delta_t)
```

Semakin kecil jeda waktu (`delta_t` dalam detik), semakin tinggi skor waktu (`s_time`). Bobot akhir setiap hubungan (edge) dihitung sebagai rata-rata tertimbang dari kedua skor:

```
weight = 0.5 × s_text + 0.5 × s_time
```

Artinya, setiap hubungan antarakun mencerminkan dua dimensi sekaligus: **seberapa mirip narasinya** dan **seberapa dekat kemunculannya**.

---

## 5. Dua Jenis Hubungan Antarakun

Graf dalam analisis ini memiliki dua jenis edge:

**Edge semantic** terbentuk jika dua tweet bukan retweet, memiliki kemiripan teks minimal 0,65, dan diunggah dalam selisih waktu maksimal 1.800 detik (30 menit). Jenis edge ini mencerminkan kemiripan narasi yang ditulis oleh akun sendiri, bukan hasil retweet.

**Edge retweet** terbentuk jika dua tweet sama-sama merupakan retweet dari sumber yang sama, dalam rentang waktu maksimal 1.800 detik. Jenis edge ini mencerminkan pola berbagi konten (shared retweet), bukan kesamaan narasi asli.

Pemisahan ini membuat interpretasi lebih aman. Kluster yang kuat karena retweet tidak bisa langsung disamakan dengan kluster yang kuat karena narasi non-retweet yang mirip.

---

## 6. Ringkasan Hubungan yang Terdeteksi

Dari `relation.csv`, terdapat **2.357 hubungan teragregasi** yang berasal dari **2.816 bukti mentah**:

| Tipe Edge | Jumlah |
|---|---:|
| Edge semantic | 1.929 (81,8%) |
| Edge retweet | 422 (17,9%) |
| Edge campuran (semantic + retweet) | 6 (0,3%) |

Mayoritas hubungan yang terbentuk adalah hubungan semantic, bukan retweet. Ini menunjukkan bahwa banyak pasangan akun terhubung karena kemiripan narasi non-retweet, bukan semata karena membagikan konten yang sama.

Secara keseluruhan, hubungan yang terdeteksi memiliki bobot cukup tinggi:

| Metrik | Rata-rata | Median | Min | Max |
|---|---:|---:|---:|---:|
| `Weight` | 0,8903 | 0,8914 | 0,4982 | 1,0000 |
| `Avg_Text_Similarity` | 0,8495 | 0,8526 | 0,6502 | 1,0000 |
| `Avg_Time_Score` | 0,9312 | 0,9862 | 0,2863 | 1,0000 |
| `Min_Time_Delta_Seconds` | 68,42 | 12,00 | 0 | 1.083 |

Nilai median jeda waktu minimum sebesar **12 detik** merupakan temuan yang menonjol. Artinya, setidaknya separuh dari pasangan akun yang terhubung mengunggah narasi serupa dalam waktu kurang dari 15 detik satu sama lain.

---

## 7. Deteksi Komunitas: 41 Kluster Teridentifikasi

Graf umum (mencakup edge semantic, retweet, dan campuran) dianalisis menggunakan algoritma Louvain dengan parameter berikut:

```
LOUVAIN_RESOLUTION = 2.0
RANDOM_SEED = 42
```

Hasilnya, terdeteksi **41 kluster** dengan distribusi status sebagai berikut:

| Status | Jumlah Kluster |
|---|---:|
| Koordinasi kuat | 18 |
| Perlu investigasi lebih lanjut | 4 |
| Indikasi lemah (kluster kecil / bukti minim) | 18 |
| Pola rendah / cenderung organik | 1 |

Status kluster ditentukan berdasarkan **skor koordinasi**, yaitu:

```
Coordination_Score = density × log₂(size + 1)
```

Formula ini menggabungkan dua dimensi: **kepadatan hubungan internal** (density) dan **ukuran kluster** (size). Kluster kecil bisa memiliki density 1,0, tetapi skornya tetap terbatas oleh ukurannya. Sebaliknya, kluster besar akan mendapat skor tinggi hanya jika hubungan internalnya juga padat.

---

## 8. Kluster Teratas pada Graf Umum

Berikut beberapa kluster dengan skor koordinasi tertinggi:

| Cluster | Akun | Density | Evidence | RT Edge | Semantic Edge | Skor | Fokus Narasi |
|---:|---:|---:|---:|---:|---:|---:|---|
| 5 | 41 | 0,865 | 709 | 0 | 709 | 4,662 | Koperasi, perbankan, UMKM, kredit |
| 11 | 18 | 0,954 | 146 | 0 | 146 | 4,054 | Kesehatan mental, puskesmas |
| 6 | 13 | 1,000 | 78 | 0 | 78 | 3,807 | Nelayan, kredit macet |
| 1 | 11 | 1,000 | 186 | 55 | 6 | 3,585 | Deklarasi pemuda, Prabowo-Gibran |
| 12 | 27 | 0,684 | 240 | 0 | 240 | 3,287 | Count down, Februari |
| 9 | 8 | 1,000 | 28 | 0 | 28 | 3,170 | Norma, lembaga, direspons |
| 20 | 6 | 1,000 | 15 | 15 | 0 | 2,807 | Shared RT: `tomlembong` |
| 15 | 6 | 1,000 | 15 | 15 | 0 | 2,807 | Shared RT: `dapitnih` |

Kluster 5, 11, 6, 12, dan 9 sepenuhnya didominasi edge semantic—artinya, hubungan antarakunnya terbentuk bukan karena retweet, melainkan karena kemiripan narasi yang ditulis sendiri. Kluster 20 dan 15, sebaliknya, sepenuhnya berbasis shared retweet, sehingga harus dibaca sebagai pola amplifikasi konten dari sumber tunggal.

---

## 9. Contoh Kluster Shared Retweet: Deklarasi Pemuda Prabowo-Gibran

Sebagai ilustrasi kluster berbasis retweet, kluster 1 pada graf umum menjadi contoh yang informatif:

| Metrik | Nilai |
|---|---|
| Jumlah akun | 11 |
| Density | 1,000 |
| Evidence | 186 |
| RT edge | 55 |
| Semantic edge | 6 |
| Sumber RT dominan | `AzzrielAzaryahu` |
| Fokus narasi | Deklarasi dukungan pemuda Kabupaten Serang untuk Prabowo-Gibran |
| Keyword | pemuda, kabupaten, deklarasi, serang |

Kekuatan kluster ini sebagian besar berasal dari shared retweet. Interpretasi yang tepat adalah: sekelompok akun yang me-retweet unggahan yang sama dalam waktu berdekatan—bukan akun-akun yang secara mandiri menulis narasi orisinal yang serupa.

---

## 10. Dashboard Non-Retweet: Analisis Koordinasi Narasi yang Lebih Bersih

Untuk memisahkan koordinasi narasi dari pengaruh retweet, proyek ini membangun dashboard khusus (`visualisasi_non_rt_light.html`) yang hanya menggunakan **edge semantic non-retweet**. Jika sebuah kluster muncul di dashboard ini, hubungan antarakunnya terbentuk dari kemiripan teks yang ditulis sendiri dan kedekatan waktu—bukan karena akun-akun tersebut me-retweet sumber yang sama.

Dashboard Non-RT menggunakan filter backbone yang lebih ketat:

| Parameter | Nilai |
|---|---:|
| Minimum rata-rata similarity | 0,75 |
| Maksimum jeda waktu minimum | 300 detik |
| Resolusi Louvain | 6,5 |

Hasil setelah backbone:

| Metrik | Nilai |
|---|---:|
| Edge semantic awal | 1.935 |
| Edge setelah backbone | 1.259 |
| Edge visual internal kluster | 391 |
| Node tampil | 148 |
| Kluster tampil | 23 |
| RT edge dalam kluster | 0 |
| Node dengan status retweet | 0 |

Dashboard ini menjadi basis paling bersih untuk mendiskusikan koordinasi narasi non-retweet.

---

## 11. Daftar Kluster pada Dashboard Non-Retweet

Berikut seluruh kluster yang terdeteksi pada dashboard Non-RT:

| Cluster | Akun | Density | Skor | Avg Similarity | Median Jeda | Status | Fokus Narasi |
|---:|---:|---:|---:|---:|---|---|---|
| 26 | 13 | 1,000 | 3,807 | 1,000 | 6 detik | Koordinasi Kuat | Ganjar-Mahfud: nelayan, kredit macet |
| 25 | 8 | 1,000 | 3,170 | 1,000 | 9 detik | Koordinasi Kuat | Ganjar-Mahfud: legislasi, kekerasan seksual |
| 35 | 7 | 1,000 | 3,000 | 1,000 | 1 detik | Koordinasi Kuat | Ganjar-Mahfud: penyuluhan, desa |
| 63 | 17 | 0,691 | 2,882 | 0,915 | 4 detik | Koordinasi Kuat | Ganjar-Mahfud: kesehatan mental, puskesmas |
| 17 | 5 | 1,000 | 2,585 | 1,000 | 13 detik | Koordinasi Kuat | Ganjar-Mahfud: kepentingan rakyat, kebebasan berpendapat |
| 29 | 5 | 1,000 | 2,585 | 1,000 | 11 detik | Koordinasi Kuat | Ganjar-Mahfud: kredit perbankan, koperasi |
| 34 | 5 | 1,000 | 2,585 | 1,000 | 17 detik | Koordinasi Kuat | Ganjar-Mahfud: kredit perbankan, UMKM |
| 69 | 5 | 1,000 | 2,585 | 1,000 | 14 detik | Koordinasi Kuat | Ganjar-Mahfud: hari susah, bahagia |
| 73 | 7 | 0,429 | 1,286 | 0,802 | 2,3 menit | Perlu Investigasi | Ganjar-Mahfud: ganjarmahfud, mahfudlebihbaik |
| 72 | 16 | 0,300 | 1,226 | 0,808 | 46 detik | Perlu Investigasi | Ganjar-Mahfud: ganjarmahfud, mahfudlebihbaik |
| 1 | 19 | 0,228 | 0,986 | 0,795 | 1,1 menit | Perlu Investigasi | Ganjar-Mahfud: ganjarmahfud, mahfudlebihbaik |
| 2 | 4 | 1,000 | 2,322 | 1,000 | 12 detik | Indikasi Lemah | Ganjar-Mahfud: menu, restoran |
| 23 | 4 | 1,000 | 2,322 | 1,000 | 6 detik | Indikasi Lemah | Ganjar-Mahfud: jabatan, dedikasi |
| 24 | 4 | 1,000 | 2,322 | 1,000 | 0 detik | Indikasi Lemah | Prabowo-Gibran: pemuda, deklarasi |
| 59 | 4 | 1,000 | 2,322 | 1,000 | 7 detik | Indikasi Lemah | Ganjar-Mahfud: democratic, indonesian |
| 30 | 3 | 1,000 | 2,000 | 1,000 | 11 detik | Indikasi Lemah | Ganjar-Mahfud: democracy, people |
| 36 | 3 | 1,000 | 2,000 | 1,000 | 5 detik | Indikasi Lemah | Ganjar-Mahfud: ganjartindakannyata |
| 44 | 3 | 1,000 | 2,000 | 1,000 | 4 detik | Indikasi Lemah | Ganjar-Mahfud: pemilihan |
| 57 | 3 | 1,000 | 2,000 | 1,000 | 6 detik | Indikasi Lemah | Ganjar-Mahfud: presidential election |
| 62 | 3 | 1,000 | 2,000 | 0,969 | 5 detik | Indikasi Lemah | Ganjar-Mahfud: kontrak, kerja |
| 0 | 3 | 0,667 | 1,333 | 0,838 | 2,8 menit | Indikasi Lemah | Prabowo-Gibran: Demokrat, AHY |
| 76 | 3 | 0,667 | 1,333 | 0,812 | 58 detik | Indikasi Lemah | Ganjar-Mahfud: terima kasih |
| 75 | 4 | 0,500 | 1,161 | 0,827 | 2,3 menit | Indikasi Lemah | Ganjar-Mahfud: keluarga, anak |

**Pola yang paling menonjol:** dari 23 kluster pada dashboard Non-RT, mayoritas besar membahas narasi yang berkaitan dengan Ganjar-Mahfud. Banyak kluster di antaranya mencatat similarity sempurna (1,000) dengan median jeda hanya beberapa detik—menunjukkan bahwa sejumlah akun mengunggah narasi yang sama atau sangat mirip secara hampir bersamaan, tanpa melalui mekanisme retweet.

Perlu dicatat bahwa beberapa kluster berukuran kecil (3–5 akun). Meskipun kuat secara struktur internal, hasil dari kluster kecil tidak dapat digeneralisasi terlalu luas.

---

## 12. Analisis Kluster Non-Retweet Terkuat

### 12.1 Kluster 26: Narasi Nelayan dan Kredit Macet

Kluster ini adalah yang paling kuat di dashboard Non-RT, dengan 13 akun yang seluruhnya saling terhubung satu sama lain (density = 1,000).

| Metrik | Nilai |
|---|---:|
| Akun | 13 |
| Density | 1,000 |
| Skor koordinasi | 3,807 |
| Evidence | 78 |
| Avg similarity | 1,000 |
| Median jeda | 6 detik |

Contoh narasi yang muncul: *"Nelayan tak bisa sendiri melawan kredit macet..."*

Beberapa pasangan akun mengunggah teks dengan kemiripan sempurna (1,000) pada detik yang sama:

| Pasangan Akun | Similarity | Jeda |
|---|---:|---:|
| `3zvaec23mmg78p3` — `lis_dua23640` | 1,000 | 0 detik |
| `9r28488u96dhe41` — `BaisCharpe69286` | 1,000 | 0 detik |
| `ow1b0v562dkee04` — `anoodyhh123` | 1,000 | 0 detik |

**Interpretasi:** Terdapat pola penyebaran narasi non-retweet yang sangat seragam pada topik nelayan dan kredit macet, dalam rentang waktu yang sangat singkat. Narasi ini secara konsisten menyertakan framing yang mengaitkan isu dengan Ganjar-Mahfud.

---

### 12.2 Kluster 25: Narasi Legislasi dan Kekerasan Seksual

| Metrik | Nilai |
|---|---:|
| Akun | 8 |
| Density | 1,000 |
| Skor koordinasi | 3,170 |
| Evidence | 28 |
| Avg similarity | 1,000 |
| Median jeda | 9 detik |

Narasi yang muncul membahas legislasi, kekerasan seksual, dan peran lembaga pendidikan, dengan penyebutan Ganjar-Mahfud. Beberapa pasangan akun mengunggah teks identik dalam selisih 0–1 detik.

**Interpretasi:** Terdapat pola penyebaran narasi non-retweet yang sangat seragam pada topik legislasi dan kekerasan seksual dalam waktu sangat berdekatan.

---

### 12.3 Kluster 35: Narasi Penyuluhan dan Desa

| Metrik | Nilai |
|---|---:|
| Akun | 7 |
| Density | 1,000 |
| Skor koordinasi | 3,000 |
| Evidence | 21 |
| Avg similarity | 1,000 |
| Median jeda | **1 detik** |

Contoh narasi: *"Ganjar Pranowo Mahfud MD menyoroti pentingnya penyuluhan di desa..."*

Median jeda 1 detik pada kluster ini adalah angka yang sangat kecil. Tujuh akun yang berbeda mengunggah teks identik dengan jeda rata-rata hanya satu detik—menunjukkan tingkat sinkronisasi yang sangat tinggi.

**Interpretasi:** Terdapat pola penyebaran narasi yang sangat seragam dan hampir simultan pada topik penyuluhan desa.

---

### 12.4 Kluster 63: Narasi Kesehatan Mental dan Puskesmas

Kluster ini memiliki profil yang sedikit berbeda: lebih besar, density tidak sempurna, dan variasi teks yang lebih luas.

| Metrik | Nilai |
|---|---:|
| Akun | 17 |
| Density | 0,691 |
| Skor koordinasi | 2,882 |
| Evidence | 94 |
| Avg similarity | 0,915 |
| Median jeda | 4 detik |

Narasi berpusat pada tema kesehatan mental dan penempatan psikolog di puskesmas. Meskipun tidak semua teks identik, rata-rata similarity 0,915 menunjukkan bahwa inti narasi tetap sangat dekat. Kluster ini adalah yang terbesar di dashboard Non-RT (17 akun) dan juga memiliki jumlah evidence terbanyak (94 pasang bukti).

**Interpretasi:** Terdapat pola penyebaran narasi non-retweet yang kuat pada topik kesehatan mental, dengan kombinasi teks sangat mirip dan waktu unggah yang sangat berdekatan.

---

### 12.5 Kluster 29 dan 34: Narasi Kredit Perbankan untuk Koperasi dan UMKM

Dua kluster ini sama-sama membahas program kredit perbankan, dengan narasi yang sedikit berbeda satu sama lain.

**Kluster 29** — keyword: koperasi, kredit, kesejahteraan. Akun-akunnya: `gmonoona137`, `gmonoona82`, `gmonoona61`, `gmonoona138`, `gmonoona75`. Contoh narasi:

> *"Terimakasih. Program Capres Ganjar Pranowo dan Cawapres Mahfud MD persembahkan 35% kredit perbankan..."*

**Kluster 34** — keyword: UMKM, perbankan, tancap gas. Akun-akunnya: `gmonoona140`, `gmonoona143`, `Gmonoona163`, `Gmonoona160`, `gmonoona145`. Contoh narasi:

> *"Wow, luar biasa. Program Capres Ganjar Pranowo dan Cawapres Mahfud MD tancap gas, 35% kredit perbankan..."*

Dua hal menarik dari kedua kluster ini. Pertama, **pola nama akun**: seluruh akun menggunakan format `gmonoona + angka`, yang merupakan pola penamaan yang sangat seragam dan tidak lazim secara organik. Kedua, seluruh edge yang terbentuk adalah edge semantic—artinya, ini bukan retweet, melainkan tweet yang ditulis sebagai unggahan mandiri dengan isi yang sangat mirip.

**Interpretasi:** Terdapat pola penyebaran narasi non-retweet yang sangat seragam pada topik kredit perbankan untuk koperasi dan UMKM, dari akun-akun dengan pola penamaan yang serupa.

---

## 13. Perbedaan Pola Antarkuery

Salah satu temuan menarik dalam dataset ini adalah **perbedaan komposisi aktivitas** antarquery yang cukup mencolok:

| Query | Retweet | Koneksi Semantic (Non-RT) | Karakteristik Dominan |
|---|---:|---:|---|
| `anies` | 302 (dominan) | sangat sedikit | Amplifikasi via retweet dari sumber tunggal |
| `prabowo` | 227 | ~150 | Campuran retweet dan narasi non-RT |
| `ganjar` | 34 (sangat sedikit) | **~2.042** (dominan) | Narasi non-retweet yang sangat seragam |

Query `ganjar` menunjukkan pola yang paling berbeda: jumlah retweet sangat rendah, tetapi koneksi semantic sangat banyak—rasionya mencapai sekitar 60 banding 1. Ini bukan berarti query `ganjar` "lebih mencurigakan" dari yang lain; ini mencerminkan **gaya penyebaran yang berbeda** dalam dataset. Bisa jadi karena kelompok pendukung Ganjar lebih menghindari retweet langsung dan memilih mengunggah variasi teks, bisa juga karena faktor lain yang tidak dapat diverifikasi dari data ini saja.

Yang perlu ditekankan: **perbedaan gaya ini tidak menunjukkan identitas atau motif pelaku**—hanya menunjukkan pola perilaku yang teramati di data.

---

## 14. Mengapa Akun Dapat Masuk ke Dalam Kluster?

Satu akun tidak masuk kluster hanya karena menyebutkan nama kandidat tertentu. Akun masuk kluster karena memiliki hubungan matematis dengan akun lain berdasarkan:

1. **Kemiripan teks** (cosine similarity ≥ 0,65 untuk edge semantic)
2. **Kedekatan waktu** (jeda ≤ 1.800 detik)
3. **Status tweet** (bukan retweet, untuk dashboard Non-RT)
4. **Lolos filter backbone** (similarity rata-rata ≥ 0,75 dan jeda minimum ≤ 300 detik)

Dasar pengelompokan adalah **hubungan matematis antara isi teks dan waktu unggah**, bukan label politik atau identitas akun.

---

## 15. Profil Akun: Karakteristik Demografis dalam Dataset

Selain pola relasi antarakun, data yang tersedia juga memuat atribut akun seperti jumlah pengikut (*followers*), jumlah akun yang diikuti (*friends*), jumlah total tweet yang pernah diunggah (*statuses*), dan tanggal pembuatan akun. Analisis terhadap atribut-atribut ini menghasilkan beberapa temuan yang relevan.

### 15.1 Distribusi Jumlah Pengikut

Dari 584 akun unik dalam dataset, distribusi jumlah pengikut sangat tidak merata:

| Kategori | Jumlah Akun | Persentase |
|---|---:|---:|
| Followers = 0 (tidak punya pengikut sama sekali) | 139 | 23,8% |
| Followers ≤ 5 | 213 | 36,5% |
| Followers ≤ 50 | 349 | 59,8% |
| Followers > 1.000 | 61 | 10,4% |

Nilai **median followers seluruh dataset hanya 24**, jauh di bawah nilai rata-rata (35.744) yang terdistorsi oleh sejumlah kecil akun dengan pengikut sangat banyak—seperti `tvOneNews` (9,8 juta), `VIVAcoid` (4,7 juta), dan `CNNIndonesia` (4 juta). Kehadiran akun-akun media besar ini bersama dengan ratusan akun berpengaruh sangat rendah menghasilkan distribusi yang sangat miring ke kanan (*heavily right-skewed*).

Jika dilihat per query kandidat, perbedaan profil pengikut terlihat jelas:

| Query | Median Followers | Keterangan |
|---|---:|---|
| `anies` | 140 | Relatif lebih tinggi |
| `prabowo` | 77 | Menengah; ada akun media besar |
| `ganjar` | **0** | Mayoritas akun tanpa pengikut |

Query `ganjar` memiliki median followers **nol**—artinya lebih dari separuh akun yang muncul pada query ini tidak memiliki pengikut sama sekali. Ini konsisten dengan temuan sebelumnya bahwa koneksi semantic (non-retweet) paling banyak terbentuk pada query `ganjar`, karena akun dengan profil sangat minim cenderung tidak memiliki jejaring organik yang terbentuk secara alami.

Perlu ditekankan bahwa jumlah followers rendah tidak serta-merta menunjukkan akun tidak otentik. Ada banyak pengguna aktif yang memang memilih untuk tidak membangun audiens. Namun, ketika dikombinasikan dengan pola unggahan yang sangat seragam dalam waktu sangat singkat, profil followers rendah ini menjadi konteks yang relevan.

### 15.2 Akun dengan Koneksi Terbanyak di Graf

Akun-akun yang paling banyak terhubung di dalam graf (degree tertinggi) umumnya juga memiliki profil pengikut yang sangat rendah:

| Akun | Degree (koneksi) | Followers | Total Statuses |
|---|---:|---:|---:|
| `AsdasdasOpopop` | 54 | 0 | 3.125 |
| `manilyn37` | 54 | 0 | 3.155 |
| `Fatien_Epiey` | 54 | 0 | 3.186 |
| `RusherALanuzga1` | 47 | 1 | 2.801 |
| `AlbiPutz75864` | 47 | 1 | 2.228 |
| `JZariell` | 47 | 0 | 3.250 |
| `saudiboi28` | 47 | 0 | 3.256 |
| `Gmonoona167` | 42 | 0 | 2.125 |

Akun-akun ini memiliki ribuan total status (riwayat unggahan lama), tetapi hampir tanpa pengikut—sebuah kombinasi yang tidak lazim untuk akun yang memang digunakan secara aktif dalam percakapan sosial organik. Pola ini layak dicatat sebagai temuan deskriptif, meskipun penjelasan di baliknya membutuhkan verifikasi lebih lanjut.

### 15.3 Distribusi Tahun Pembuatan Akun

Sebaran tahun pembuatan akun menunjukkan adanya konsentrasi akun yang relatif baru:

| Periode | Jumlah Akun | Persentase |
|---|---:|---:|
| Sebelum 2020 | 280 | 47,9% |
| 2020–2021 | 78 | 13,4% |
| **2022–2023** | **210** | **36,0%** |

Sekitar **36% akun dalam dataset dibuat dalam dua tahun terakhir sebelum Pilpres 2024**. Akun-akun yang dibuat pada 2022–2023 memiliki median followers hanya **8**, dibandingkan median **44** untuk akun yang dibuat sebelum 2022. Selain itu, median total statuses akun baru (1.417) lebih rendah dari akun lama (3.074), yang masuk akal mengingat waktu akun berdiri lebih singkat.

Temuan ini tidak berarti akun baru secara otomatis tidak otentik—banyak pengguna yang memang baru bergabung menjelang Pilpres karena tertarik isu politik. Namun, kombinasi antara akun baru, followers sangat sedikit, dan pola unggahan yang sangat seragam merupakan konteks yang perlu diperhatikan dalam analisis lanjutan.

---

## 16. Pola Temporal: Distribusi Aktivitas Posting

Seluruh 1.002 tweet dalam dataset berada dalam rentang waktu sekitar 21 menit. Distribusi aktivitas per menit menunjukkan pola yang tidak merata:

| Waktu (UTC) | Jumlah Tweet | Proporsi |
|---|---:|---:|
| 17:59 | 1 | 0,1% |
| 18:00 | 78 | 7,8% |
| 18:01 | 87 | 8,7% |
| 18:02 | 96 | 9,6% |
| **18:03** | **221** | **22,1%** |
| 18:04 | 70 | 7,0% |
| 18:05 | 58 | 5,8% |
| 18:06 | 46 | 4,6% |
| 18:07 | 37 | 3,7% |
| 18:08 | 47 | 4,7% |
| 18:09 | 57 | 5,7% |
| 18:10–18:21 | 204 | 20,4% |

Temuan yang paling menonjol adalah **lonjakan aktivitas pada pukul 18:03 UTC**, di mana 221 tweet—setara 22,1% dari seluruh dataset—diunggah dalam satu menit. Ini adalah 2,3 kali lipat volume menit sebelumnya (96 tweet), dan langsung diikuti penurunan tajam ke 70 tweet pada menit berikutnya.

Pola ini—lonjakan mendadak lalu turun cepat—berbeda dari pola pertumbuhan organik yang biasanya meningkat secara bertahap. Dalam literatur analisis media sosial, pola seperti ini sering dikaitkan dengan unggahan terjadwal atau koordinasi yang terpusat pada satu titik waktu tertentu. Namun, tanpa data lebih lanjut tentang komposisi tweet pada menit tersebut, interpretasi ini tetap bersifat deskriptif.

Perlu dicatat bahwa lonjakan ini kemungkinan berhubungan dengan waktu di mana pipeline crawling mengambil data—sehingga konsentrasi tweet pada 18:03 bisa jadi juga mencerminkan batas snapshot pengambilan data, bukan semata perilaku posting pengguna.

---

## 17. Akun yang Aktif di Lebih dari Satu Query Kandidat

Dari 584 akun unik, sebagian besar (532 akun, 91,1%) hanya muncul pada satu query kandidat. Namun, **52 akun (8,9%) muncul pada dua query atau lebih**, dan 5 di antaranya muncul pada ketiga query sekaligus (`anies`, `ganjar`, `prabowo`):

| Akun | Query yang Diikuti | Tipe Tweet |
|---|---|---|
| `HalimWajib98317` | anies, ganjar, prabowo | Retweet di semua query |
| `kufar14` | anies, ganjar, prabowo | Retweet di semua query |
| `lilymrpng` | anies, ganjar, prabowo | Retweet di semua query |
| `rahmatknt270201` | anies, ganjar, prabowo | Retweet di semua query |
| `wongkalibanteng` | anies, ganjar, prabowo | Retweet di semua query |

Seluruh akun yang muncul di ketiga query melakukan **retweet** di semua kubu—bukan menulis narasi orisinal. Ini bisa berarti beberapa hal: akun tersebut memang mengikuti percakapan dari semua kandidat, atau akun tersebut aktif me-retweet konten dari berbagai sumber tanpa afiliasi tunggal.

Satu perbedaan menarik terlihat pada perbandingan profil followers:

| Kelompok | Median Followers |
|---|---:|
| Akun yang hanya muncul di 1 query | 17 |
| Akun yang muncul di 2+ query | 112 |

Akun lintas query memiliki median followers **6,6 kali lebih tinggi** dibanding akun yang hanya aktif pada satu kubu. Ini mengindikasikan bahwa akun lintas query cenderung memiliki jaringan sosial yang lebih luas dan mungkin lebih aktif secara umum—bukan akun dengan profil minim yang hanya muncul untuk satu narasi tertentu.

Temuan ini menambahkan nuansa pada gambaran keseluruhan: tidak semua aktivitas di dataset dapat langsung dikaitkan dengan satu kubu politik tertentu. Sebagian akun bergerak lintas kubu, dan pola ini layak diperhatikan dalam analisis yang lebih dalam.

---

## 18. Interpretasi Umum Hasil

Berdasarkan seluruh analisis yang telah dilakukan—mulai dari struktur graf, pola kluster, profil akun, distribusi temporal, hingga akun lintas query—beberapa poin utama dapat ditarik:

**1. Proporsi retweet yang tinggi membutuhkan pemisahan yang cermat.**
Dataset secara keseluruhan memiliki rasio retweet 56,2%. Pemisahan retweet dari koordinasi semantic menjadi langkah penting agar hasil tidak terdistorsi oleh konten yang secara otomatis identik. Dashboard Non-RT menyediakan pandangan yang lebih bersih untuk keperluan ini.

**2. Koordinasi narasi non-retweet paling menonjol pada query Ganjar-Mahfud.**
Setelah retweet dipisahkan, pola semantic coordination yang paling kuat secara konsisten muncul pada topik-topik yang berkaitan dengan Ganjar-Mahfud—meliputi nelayan dan kredit macet, legislasi dan kekerasan seksual, penyuluhan desa, kesehatan mental dan puskesmas, serta kredit perbankan untuk koperasi dan UMKM.

**3. Banyak kluster menunjukkan kemiripan teks yang sangat tinggi dalam waktu sangat singkat.**
Kluster dengan similarity 1,000 dan median jeda beberapa detik menunjukkan bahwa sejumlah akun mengunggah narasi yang sama atau hampir identik dalam waktu yang hampir bersamaan. Pola seperti ini sulit dijelaskan sebagai kebetulan, meskipun penjelasan pastinya tetap di luar jangkauan analisis ini.

**4. Profil akun yang terlibat cenderung memiliki pengikut sangat sedikit.**
Akun-akun dengan koneksi terbanyak di graf umumnya memiliki 0–1 followers. Query `ganjar`—yang paling banyak menghasilkan koneksi semantic—memiliki median followers nol. Pola ini relevan sebagai konteks, meski tidak dapat dijadikan bukti tunggal tentang sifat akun.

**5. Ada lonjakan temporal yang mencolok pada menit 18:03 UTC.**
Sebesar 22,1% dari seluruh tweet dalam dataset diunggah dalam satu menit, dengan volume 2,3 kali lipat menit sebelumnya. Pola ini berbeda dari pertumbuhan organik yang gradual, meskipun interpretasinya membutuhkan kehati-hatian mengingat keterbatasan data.

**6. Keterbatasan interpretasi harus diperhatikan.**
Dataset ini hanya mencakup 1.002 tweet dalam rentang 21 menit—sampel yang sangat terbatas. Analisis ini tidak dapat membuktikan motif, identitas asli, afiliasi organisasi, atau apakah akun dioperasikan secara manual atau otomatis. Temuan paling tepat dipahami sebagai **indikasi awal berbasis data**, bukan sebagai kesimpulan final mengenai identitas atau niat pelaku.

---

## 19. Kesimpulan

Secara metodologis, analisis ini memiliki beberapa kekuatan: retweet dipisahkan dari koordinasi semantic, setiap hubungan menyimpan bukti dan jenis relasi, kluster diberi label fokus narasi berdasarkan kata kunci, dan dashboard Non-RT menyediakan pandangan yang lebih bersih dari bias retweet. Analisis tambahan terhadap profil akun, distribusi temporal, dan akun lintas query memberikan lapisan konteks yang memperkaya pembacaan hasil.

Kesimpulan utama dari dataset ini dapat dirangkum sebagai berikut:

> Pada dataset yang dianalisis, pola koordinasi narasi yang paling menonjol ditemukan pada konten non-retweet yang berkaitan dengan Ganjar-Mahfud, terutama pada topik nelayan/kredit macet, legislasi/kekerasan seksual, penyuluhan desa, kesehatan mental/puskesmas, dan kredit perbankan untuk koperasi/UMKM. Pola tersebut ditandai dengan banyak akun mengunggah teks yang sama atau sangat mirip dalam selisih waktu yang sangat singkat, dengan profil pengikut yang sangat rendah dan sebagian besar berasal dari akun yang dibuat dalam dua tahun terakhir sebelum Pilpres.

Kesimpulan ini memiliki batas yang jelas. Dataset berukuran terbatas, rentang waktunya sangat pendek, dan analisis ini hanya membaca pola koordinasi di tingkat graf—bukan motif, identitas asli, atau struktur organisasi di balik akun. Temuan ini paling tepat digunakan sebagai titik awal investigasi berbasis data, yang idealnya dilengkapi dengan data yang lebih besar, rentang waktu yang lebih panjang, dan metode verifikasi tambahan.
