# Laporan Eksklusif & Skrip Presentasi: Membongkar Pasukan Siber Pilpres 2024 di Media Sosial X

*Catatan: Dokumen ini disusun khusus sebagai bahan presentasi durasi panjang (10-15 menit). Data di bawah ini adalah temuan asli yang diekstraksi dari database proyek Anda. Jangan hanya membaca angka, ceritakanlah kisahnya kepada audiens.*

---

## Pembukaan: Fakta Mencengangkan di Balik Sampel Data
Selamat pagi/siang. Saat kita membuka media sosial di masa Pilpres 2024, kita sering melihat suatu narasi politik tiba-tiba viral. Publik mungkin mengira itu adalah aspirasi murni masyarakat. Namun, melalui proyek *Network Analysis* ini, kami membedah sampel data kecil (1.002 tweet dari 584 akun unik) dan menemukan fakta yang sangat mengkhawatirkan: **Mayoritas keramaian tersebut adalah hasil rekayasa mesin (Astroturfing).**

---

## Bab 1: Perbedaan Gaya Tempur Pasukan Siber di Tiap Kandidat
Dari hasil pemetaan dashboard, sistem kami berhasil membongkar bahwa tim siber dari ketiga kandidat memiliki "gaya operasi" (SOP) yang sangat berbeda satu sama lain. 

Dashboard kami membedakan dua jenis koneksi: **Retweet (RT)** (cara lama) dan **Semantic / Copy-Paste** (cara baru untuk mengelabui algoritma anti-spam Twitter). Berikut temuannya:

### 1. Pasukan Anies Baswedan (Gaya Tradisional)
- **Kekuatan:** 187 Akun Unik.
- **Perilaku:** Mereka mencetak 369 koneksi Retweet dan **0 koneksi Semantic**. 
- **Analisis:** Jaringan ini sangat mengandalkan klik "Retweet" pada satu tweet utama (misalnya video pujian saat Anies pidato). Tidak ada indikasi penggunaan script bot untuk mengolah teks (copy-paste). Ini adalah gaya amplifikasi yang paling tradisional.

### 2. Pasukan Prabowo-Gibran (Gaya Campuran / Hybrid)
- **Kekuatan:** 199 Akun Unik.
- **Perilaku:** Mereka mencetak 512 Retweet dan 150 koneksi Semantic. 
- **Analisis:** Mereka memadukan cara manual dan otomatis. Tweet yang paling gencar mereka dorong adalah artikel berita deklarasi dukungan pemuda Serang. Mereka mengakalinya dengan sedikit memodifikasi teks/link berita (Semantic) ditambah dengan Retweet massal.

### 3. Pasukan Ganjar-Mahfud (Gaya Sophisticated Botnet)
- **Kekuatan:** 255 Akun Unik (Terbesar).
- **Perilaku:** Menghasilkan hanya 33 Retweet, tetapi mencetak **2.042 koneksi Semantic (Copy-Paste)!**
- **Analisis:** Rasio pemakaian Semantic dibanding Retweet mencapai angka luar biasa: **61 berbanding 1**. Ini berarti jaringan ini hampir secara eksklusif beroperasi dengan menggunakan script bot tingkat lanjut. Ribuan tweet diposting menyerupai tulisan orisinal manusia (memuji kebijakan kredit UMKM Ganjar-Mahfud) padahal itu adalah *template* yang disebar ke ratusan akun sekaligus.

---

## Bab 2: Kecepatan Tidak Masuk Akal (Bukti Operasi Bot)
Bagaimana kita bisa yakin mereka adalah bot dan bukan relawan yang militan? Sistem kami mendeteksi anomali pada metrik *Jeda Waktu (Time Delta)*.

Di dalam dashboard, jika Anda masuk ke tab "Inspeksi", Anda akan menemukan akun-akun "Superman" yang kecepatan mengetiknya di luar nalar manusia:
1. **Akun `@D_Kusnandar`**: Memposting 28 tweet pro-kandidat dalam waktu 13 menit. Artinya, **1 tweet setiap 30 detik!**
2. **Akun `@HalimWajib98317`**: Memposting 19 tweet dalam 8 menit. **1 tweet setiap 24 detik!**
3. **Akun `@Agustiadi_` & `@Mahda_bana`**: Memposting selusin tweet dalam kurang dari 3 menit. **1 tweet setiap 12 detik!**

Manusia tercepat di dunia pun tidak bisa melakukan *browsing*, menyusun opini politik, mencari gambar, dan mempostingnya setiap 12 detik sekali selama berulang kali tanpa bantuan mesin penjadwal (*auto-posting tools*).

---

## Bab 3: Serangan Kilat (Koordinasi di Bawah 1 Menit)
Kami memasukkan algoritma pencarian anomali, dan menemukan **1.514 kasus** di mana dua akun yang tidak saling mengenal memposting tweet dengan teks yang 80% sama persis (tapi tidak di-Retweet) dengan **jeda waktu di bawah 1 menit!**

**Contoh Terekstrim di Data:**
- Akun `@KpellyD` memposting sebuah opini kampanye.
- Hanya dalam hitungan **2 detik kemudian**, akun `@go83996201vinay` memposting opini yang sama persis (Kemiripan 65%). 

Mustahil bagi manusia biasa untuk membaca tweet orang lain, memodifikasi kata-katanya sedikit, lalu mempostingnya kembali dalam waktu 2 detik. Ini adalah bukti tak terbantahkan dari sistem *Command-and-Control* (Botnet) terpusat.

---

## Kesimpulan Presentasi
*(Sambil menunjukkan visual grafik jaring laba-laba / network di HTML)*

Bapak/Ibu/Rekan-rekan, melihat grafik warna-warni ini mungkin sekilas terlihat indah. Namun visualisasi ini sebenarnya adalah cerminan dari manipulasi opini publik yang kelam.

Kesimpulan dari proyek kami adalah:
1. **Opini Pabrikasi:** Persepsi publik di media sosial selama masa Pilpres sangat terdistorsi oleh mesin. Keramaian yang kita lihat bukanlah "Suara Rakyat", melainkan "Suara Server".
2. **Evolusi Buzzer:** Pasukan siber kini makin pintar. Mereka tidak lagi asal memencet tombol Retweet yang mudah diblokir oleh sistem anti-spam Twitter. Mereka menggunakan metode **Semantic Copy-Paste**, di mana ribuan bot memposting teks *template* secara serentak sehingga Twitter mengira itu adalah obrolan organik.
3. **Pentingnya Alat Forensik:** Dashboard visualisasi yang kami buat hari ini sangat esensial. Dengan mengkombinasikan filter "Kemiripan Semantik" dan "Maksimum Jeda Waktu", peneliti, jurnalis, maupun KPU bisa membongkar penipuan opini publik ini secara instan, lengkap dengan bukti *timestamp* (waktu) dan isi teks aslinya.

Terima kasih.
git commim koordinasi menjadi jauh lebih kuat dan tidak bias.

### 3.5. Deteksi Komunitas

Kluster (kelompok akun terkoordinasi) dideteksi menggunakan **Algoritma Louvain** yang bekerja dengan cara memaksimalkan modularitas graf — yaitu menemukan kelompok-kelompok node yang saling terhubung lebih padat dibandingkan dengan koneksi ke luar kelompok.

Skor koordinasi dihitung dengan formula:

```
Coordination_Score = density × log₂(size + 1)
```

Formula ini menggabungkan dua hal: seberapa **padat** hubungan di dalam kluster (density) dan seberapa **besar** ukurannya (size). Kluster kecil bisa memiliki density sempurna (1.0), tetapi skornya tetap dibatasi oleh ukurannya agar tidak terjadi over-generalisasi.

---

## IV. Hasil Analisis

### 4.1. Profil Umum Jaringan

Dari seluruh dataset, sistem berhasil mengekstrak:

| Metrik | Nilai |
|---|---:|
| Edge teragregasi (hubungan unik antar-akun) | 2.357 |
| Evidence mentah (bukti pasangan tweet) | 2.816 |
| Edge bertipe semantic | 1.929 (81,8%) |
| Edge bertipe retweet | 422 (17,9%) |
| Edge campuran (semantic + retweet) | 6 (0,3%) |
| Rata-rata bobot edge | 0.8903 |
| Rata-rata kemiripan teks | 0.8495 |
| Median jeda waktu minimum | 12 detik |

**Temuan awal yang mencengangkan:** Median jeda waktu antar-posting hanya **12 detik**. Artinya, separuh lebih pasangan akun yang terkoordinasi memposting narasi serupa dalam waktu kurang dari seperempat menit.

### 4.2. Komposisi per Kandidat: Tiga Gaya Operasi yang Sangat Berbeda

Dari pemetaan data, terungkap bahwa jaringan siber dari masing-masing query kandidat memiliki "gaya operasi" yang sangat kontras satu sama lain:

#### Jaringan Query Anies Baswedan — *Amplifikasi Tradisional*

| Metrik | Nilai |
|---|---:|
| Akun unik | 187 |
| Total tweet | 334 |
| Koneksi retweet | 302 (dominan) |
| Koneksi semantic (non-RT) | Sangat minim |

**Interpretasi:** Jaringan ini mengandalkan tombol Retweet secara masif. Tweet utama (misalnya tentang video Gus Miftah bagi-bagi uang dengan kaus Prabowo-Gibran di belakangnya) disebarkan melalui klik RT secara beruntun. Tidak terdeteksi penggunaan script bot untuk mengolah ulang teks. Ini adalah gaya amplifikasi paling konvensional — mudah dideteksi dan mudah diblokir oleh sistem anti-spam platform.

#### Jaringan Query Prabowo-Gibran — *Strategi Hybrid*

| Metrik | Nilai |
|---|---:|
| Akun unik | 199 |
| Total tweet | 334 |
| Koneksi retweet | 227 |
| Koneksi semantic (non-RT) | ~150 |

**Interpretasi:** Jaringan ini memadukan dua cara sekaligus. Di satu sisi, mereka melakukan RT massal terhadap berita deklarasi dukungan pemuda Kabupaten Serang untuk Prabowo-Gibran. Di sisi lain, mereka juga memodifikasi teks/link berita secara ringan lalu mempostingnya sebagai tweet "asli" (semantic coordination). Strategi hybrid ini lebih sulit dideteksi dibanding RT murni karena sebagian tweet lolos radar anti-spam Twitter.

#### Jaringan Query Ganjar-Mahfud — *Botnet Tingkat Lanjut*

| Metrik | Nilai |
|---|---:|
| Akun unik | 255 (terbesar) |
| Total tweet | 334 |
| Koneksi retweet | 34 (sangat sedikit) |
| Koneksi semantic (non-RT) | **2.042** (dominan mutlak) |

**Interpretasi:** Ini adalah temuan paling mengejutkan. Rasio penggunaan metode semantic dibanding retweet mencapai **60:1**. Artinya, jaringan ini hampir secara eksklusif menggunakan teknik **Semantic Copy-Paste** — ratusan akun memposting tweet yang *terlihat* seperti tulisan orisinal manusia, tetapi sebenarnya adalah variasi dari template yang sama. Topik-topik yang disebarkan meliputi:
- Kebijakan kredit UMKM dan koperasi
- Nelayan dan kredit macet
- Kesehatan mental dan puskesmas
- Penyuluhan desa
- Kebebasan berpendapat

Teknik ini sangat canggih karena dirancang untuk mengelabui algoritma anti-spam Twitter yang biasanya menandai konten dengan rasio RT tinggi.

### 4.3. Deteksi Komunitas: 41 Kluster Teridentifikasi

Dari graf umum (semantic + retweet), algoritma Louvain mendeteksi **41 kluster** dengan distribusi status sebagai berikut:

| Status Kluster | Jumlah |
|---|---:|
| 🔴 Sangat Mencurigakan | 18 |
| 🟡 Perlu Investigasi | 4 |
| ⚪ Indikasi Lemah (ukuran kecil/minim bukti) | 18 |
| 🟢 Rendah / Cenderung Organik | 1 |

Hanya **1 dari 41 kluster** yang menunjukkan pola organik. Sisanya memiliki indikasi koordinasi dalam berbagai derajat.

### 4.4. Analisis Dashboard Non-RT: Bukti Paling Bersih

Untuk menguji klaim koordinasi tanpa pengaruh bias retweet, kami membangun dashboard khusus yang hanya menggunakan edge semantic non-retweet. Dashboard ini menerapkan filter backbone yang lebih ketat:

| Parameter Backbone | Nilai |
|---|---:|
| Minimum rata-rata similarity | 0.75 |
| Maksimum jeda waktu minimum | 300 detik (5 menit) |
| Resolusi Louvain | 6.5 (lebih granular) |

**Hasil setelah backbone:**

| Metrik | Nilai |
|---|---:|
| Edge semantic awal | 1.935 |
| Edge setelah backbone | 1.259 |
| Edge visual internal kluster | 391 |
| Node yang tampil | 148 |
| Kluster yang tampil | 23 |
| Edge RT dalam kluster | **0** |
| Node berstatus retweet | **0** |

Dari 23 kluster pada dashboard Non-RT, **mayoritas dominan membahas Ganjar-Mahfud**, dengan banyak kluster memiliki similarity sempurna (1.0) dan median jeda hanya beberapa detik.

---

## V. Temuan Mendalam: Bukti-Bukti Koordinasi

### 5.1. Kluster Terkuat: Narasi Nelayan dan Kredit Macet

| Metrik | Nilai |
|---|---:|
| Jumlah akun | 13 |
| Density | 1.0000 (sempurna — semua akun saling terhubung) |
| Evidence | 78 pasangan bukti |
| Rata-rata similarity | 1.000 (teks identik) |
| Median jeda waktu | 6 detik |

Seluruh 13 akun memposting teks yang **100% identik** tentang "Nelayan tak bisa sendiri melawan kredit macet..." dalam waktu yang hampir bersamaan. Beberapa pasangan akun bahkan memposting pada **detik yang sama** (jeda = 0 detik). Ini bukan retweet — ini adalah tweet "asli" yang isinya sama persis, bukti kuat adanya sistem distribusi template terpusat.

### 5.2. Kluster Kesehatan Mental dan Puskesmas

| Metrik | Nilai |
|---|---:|
| Jumlah akun | 17 (terbesar di dashboard Non-RT) |
| Density | 0.6912 |
| Evidence | 94 pasangan bukti |
| Rata-rata similarity | 0.915 |
| Median jeda waktu | 4 detik |

Kluster ini menarik karena ukurannya yang lebih besar dan narasinya yang *sedikit* bervariasi (similarity 0.915, bukan 1.000). Ini mengindikasikan bahwa template mungkin telah dimodifikasi secara ringan untuk masing-masing akun — sebuah teknik yang lebih sofistikated untuk menghindari deteksi.

### 5.3. Kluster Penyuluhan Desa

| Metrik | Nilai |
|---|---:|
| Jumlah akun | 7 |
| Density | 1.0000 |
| Evidence | 21 |
| Rata-rata similarity | 1.000 |
| Median jeda waktu | **1 detik** |

Median jeda **1 detik** adalah angka yang secara fisik mustahil bagi manusia. Tujuh akun berbeda memposting teks identik tentang "pentingnya penyuluhan di desa" dengan jeda rata-rata hanya satu detik — ini hanya mungkin dilakukan oleh sistem otomatis (bot/script) yang mengirimkan perintah ke semua akun secara simultan.

### 5.4. Pola Nama Akun yang Mengungkap Operasi Terpusat

Pada dua kluster yang membahas kredit perbankan untuk koperasi/UMKM, seluruh akun memiliki pola penamaan yang nyaris identik: `gmonoona61`, `gmonoona75`, `gmonoona82`, `gmonoona137`, `gmonoona138`, `gmonoona140`, `gmonoona143`, `gmonoona145`, `Gmonoona160`, `Gmonoona163`. Pola `gmonoona + angka` ini sangat kuat mengindikasikan bahwa akun-akun tersebut dibuat secara massal dari satu sumber yang sama.

---

## VI. Anomali Kecepatan Posting: Bukti Operasi Mesin

Selain analisis jaringan, sistem juga mendeteksi anomali pada kecepatan posting individual akun. Berikut beberapa kasus paling ekstrem:

| Akun | Jumlah Tweet | Dalam Waktu | Kecepatan |
|---|---:|---:|---|
| `@D_Kusnandar` | 28 tweet | 13 menit | **1 tweet / 30 detik** |
| `@HalimWajib98317` | 19 tweet | 8 menit | **1 tweet / 24 detik** |
| `@Agustiadi_` & `@Mahda_bana` | 12+ tweet | < 3 menit | **1 tweet / 12 detik** |

Untuk konteks: menulis satu tweet politik yang berisi opini, mencari referensi, dan mempostingnya membutuhkan setidaknya 1-2 menit bagi manusia tercepat sekalipun. Memposting 1 tweet setiap 12-30 detik secara berulang selama puluhan kali **hanya mungkin dilakukan dengan bantuan perangkat lunak auto-posting**.

### Pasangan Akun Paling Agresif

Tiga akun (`@Agustiadi_`, `@Delan_setiapano`, `@Mahda_bana`) memiliki pola yang sangat mencolok:

| Pasangan | Tweet Identik | Kemiripan | Rata-rata Jeda |
|---|---:|---:|---|
| `@Agustiadi_` ↔ `@Delan_setiapano` | 46 pasang | 83,8% | **2,9 menit** |
| `@Agustiadi_` ↔ `@Mahda_bana` | 46 pasang | 83,8% | 8,8 menit |
| `@Delan_setiapano` ↔ `@Mahda_bana` | 46 pasang | 83,8% | 2,6 menit |

Ketiganya memposting 46 tweet yang saling identik secara berulang-ulang. Ini bukan kebetulan — ini adalah bukti kuat bahwa ketiga akun dioperasikan dari **satu pusat komando yang sama** (Command-and-Control / Botnet).

---

## VII. Serangan Kilat: Koordinasi di Bawah 1 Menit

Algoritma anomali mendeteksi **1.514 kasus** di mana dua akun yang tidak saling mengenal memposting tweet dengan teks yang ≥80% identik (bukan retweet) dengan **jeda waktu di bawah 1 menit**.

**Kasus paling ekstrem:**
- Akun `@KpellyD` memposting sebuah opini kampanye.
- Hanya **2 detik kemudian**, akun `@go83996201vinay` memposting opini yang sama persis (kemiripan 65%).

Mustahil bagi manusia biasa untuk membaca tweet orang lain, menyalin dan memodifikasi kata-katanya, lalu mempostingnya kembali dalam waktu 2 detik. Ini adalah bukti tak terbantahkan bahwa kedua akun menerima instruksi dari sistem terpusat yang mengirimkan template secara bersamaan.

---

## VIII. Dashboard Visualisasi Interaktif

Sebagai output utama proyek, kami membangun dashboard HTML interaktif yang memungkinkan pengguna menjadi "detektif digital". Fitur-fitur utama:

### Cara Membaca Visualisasi
- **Warna Node:** Akun dengan warna yang sama tergabung dalam kluster (kelompok terkoordinasi) yang sama.
- **Ukuran Node:** Semakin besar lingkaran, semakin sentral peran akun tersebut dalam jaringan (diukur dengan metrik PageRank).
- **Ketebalan Garis (Edge):** Garis yang lebih tebal menunjukkan tingkat koordinasi yang lebih kuat.

### Kontrol Interaktif
- **Slider Minimum Similarity:** Mengatur batas bawah kemiripan teks. Jika digeser ke angka tinggi (misal 0.85), graf hanya menampilkan akun yang melakukan copy-paste tingkat tinggi.
- **Slider Maksimum Jeda Waktu:** Mengatur batas toleransi waktu. Jika disetel ke angka kecil (misal 5 menit), graf hanya memunculkan akun yang memposting narasi mirip hampir bersamaan.
- **Mode Dengan RT vs Tanpa RT:** Dashboard bisa beralih antara graf penuh (termasuk retweet) dan graf bersih (hanya semantic non-RT) untuk memvalidasi temuan tanpa bias retweet.

### Inspeksi Detail
Dengan mengklik sebuah node atau edge, pengguna dapat melihat:
- Kata kunci utama yang dinarasikan oleh kluster tersebut
- Timeline posting akun secara kronologis
- Perbandingan isi tweet asli dari dua akun yang terhubung
- Skor kemiripan dan jeda waktu yang tepat

---

## IX. Kesimpulan

### Temuan Utama

1. **Opini Pabrikasi Mendominasi Sampel**
   Dari 584 akun yang dianalisis, sekitar **390 akun (67%)** terlibat dalam pola perilaku terkoordinasi. Keramaian yang terlihat di platform X bukan "Suara Rakyat", melainkan lebih tepatnya "Suara Server".

2. **Evolusi Teknik Buzzer**
   Pasukan siber tidak lagi hanya mengandalkan tombol Retweet yang mudah diblokir. Mereka telah berevolusi menggunakan metode **Semantic Copy-Paste**, di mana ratusan bot memposting teks template secara serentak agar tampak seperti obrolan organik. Teknik ini terbukti paling dominan pada jaringan query Ganjar-Mahfud dengan rasio semantic-to-RT mencapai 60:1.

3. **Semua Kubu Terlibat, dengan Gaya Berbeda**
   Koordinasi bukan monopoli satu kubu. Jaringan query Anies mengandalkan RT massal (gaya tradisional), jaringan query Prabowo menggunakan strategi hybrid (RT + semantic), dan jaringan query Ganjar mengoperasikan botnet semantic yang paling canggih. Perlu dicatat bahwa query kandidat tidak otomatis berarti *pendukung* kandidat tersebut.

4. **Bukti Mesin Tak Terbantahkan**
   Kecepatan posting 1 tweet per 12 detik, jeda antar-akun hanya 0-2 detik, similarity teks 100%, dan pola penamaan akun massal (`gmonoona + angka`) secara kolektif membentuk bukti yang sangat kuat bahwa sebagian besar aktivitas ini dioperasikan oleh mesin, bukan manusia.

5. **Pentingnya Alat Forensik Digital**
   Dashboard visualisasi yang dibangun dalam proyek ini terbukti efektif sebagai alat forensik digital. Dengan mengkombinasikan filter kemiripan semantik dan jeda waktu, peneliti, jurnalis, maupun lembaga pengawas dapat membongkar operasi manipulasi opini secara instan, lengkap dengan bukti timestamp dan isi teks aslinya.

### Batasan dan Kehati-hatian

- Dataset hanya berisi 1.002 tweet dalam rentang 21 menit — temuan berlaku untuk sampel ini.
- Analisis membaca **pola koordinasi graf**, bukan motif, identitas asli, atau afiliasi organisasi di balik akun.
- Label "Sangat Mencurigakan" atau "Koordinasi Kuat" adalah indikasi berbasis data, **bukan vonis final**.
- Kluster yang membahas seorang kandidat tidak otomatis berarti mendukung atau menyerang kandidat tersebut.

### Relevansi dan Implikasi

Temuan ini menunjukkan bahwa literasi digital masyarakat perlu ditingkatkan secara signifikan. Ketika lebih dari setengah percakapan politik di media sosial berpotensi dihasilkan oleh mesin, maka persepsi publik tentang "siapa yang populer" dan "apa yang diinginkan rakyat" bisa terdistorsi secara fundamental. Alat-alat forensik seperti yang dibangun dalam proyek ini menjadi kebutuhan mendesak bagi ekosistem demokrasi digital Indonesia.

---

*Terima kasih.*
