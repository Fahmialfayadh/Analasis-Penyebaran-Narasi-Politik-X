# Presentasi Final Project: Analisis Koordinasi Narasi Politik di Media Sosial X (Pilpres 2024)

Presentasi ini dirancang sebagai panduan alur (script) untuk mempresentasikan dashboard visualisasi jaringan. Anda bisa menggunakan poin-poin ini sebagai teks slide PowerPoint dan panduan berbicara Anda.

---

## Slide 1: Judul & Latar Belakang
**Visual di layar:** Tampilan awal dashboard (Ikhtisar / Overview)

**Poin Bicara:**
- **Latar Belakang:** Pada masa Pilpres 2024, media sosial dipenuhi oleh berbagai narasi politik. Seringkali, sebuah opini yang terlihat masif bukan berasal dari audiens organik, melainkan hasil koordinasi kelompok tertentu (seperti *buzzer* atau tim kampanye).
- **Tujuan Project:** Proyek ini bertujuan untuk mendeteksi, memetakan, dan menganalisis secara otomatis kelompok-kelompok akun yang saling berkoordinasi dalam menyebarkan narasi politik di platform X (Twitter).
- **Pendekatan:** Menggunakan *Network Analysis* (Analisis Jaringan) untuk melihat siapa terhubung dengan siapa berdasarkan kemiripan isi tweet dan waktu posting.

---

## Slide 2: Kamus Istilah (Key Concepts)
**Visual di layar:** Teks definisi (bisa dibuat bullet points yang rapi)

**Poin Bicara:**
Sebelum kita masuk ke visualisasi, ada beberapa istilah teknis penting yang akan sering kita gunakan:

- **Node (Simpul):** Lingkaran-lingkaran yang ada di dalam graf. Satu node merepresentasikan **satu akun X (Twitter)**.
- **Edge (Sisi / Garis Koneksi):** Garis yang menghubungkan dua node. Jika dua akun memiliki garis penghubung, artinya mereka memiliki aktivitas yang saling terkait (berkoordinasi).
- **Kemiripan Semantik (Semantic Similarity):** Skor yang mengukur seberapa mirip isi dan makna dari dua tweet yang berbeda.
- **Jeda Waktu (Time Delta):** Selisih waktu (dalam menit) antara akun A memposting tweet dan akun B memposting tweet yang mirip. Jeda waktu yang sangat sempit mengindikasikan koordinasi yang terencana.
- **Kluster (Komunitas):** Sekumpulan node yang saling terhubung erat dan memiliki warna yang sama. Ini merepresentasikan satu "pasukan" atau kelompok yang bergerak bersamaan.

---

## Slide 3: Membaca Visualisasi Graf (Visual Cues)
**Visual di layar:** Zoom ke salah satu kluster di graf, tunjukkan node besar dan kecil, serta garis edge.

**Poin Bicara:**
Bagaimana cara kita membaca peta jaringan yang kompleks ini?

1. **Warna Node:** Akun-akun dengan warna yang sama berarti mereka tergabung dalam satu kluster (kelompok) yang sama. Mereka menyebarkan narasi yang identik secara terkoordinasi.
2. **Ukuran Node:** Semakin besar lingkaran (node) sebuah akun, semakin sentral peran akun tersebut. Artinya akun ini memiliki banyak koneksi (edge) dengan akun lain di kelompoknya.
3. **Ketebalan Garis (Edge):** Garis yang lebih tebal menunjukkan tingkat koordinasi yang lebih kuat, baik itu karena sering melakukan Retweet atau memiliki banyak postingan dengan kemiripan semantik tinggi.

---

## Slide 4: Filter dan Sensitivitas (Kontrol Dashboard)
**Visual di layar:** Tunjukkan panel kontrol di sebelah kiri atas (Filter Sensitivitas).

**Poin Bicara:**
Dashboard ini interaktif. Kita bisa mengatur parameter untuk mencari anomali data secara spesifik:
- **Minimum Similarity:** Menentukan batas bawah kemiripan. Jika kita geser ke angka tinggi (misal 0.85), graf hanya akan menampilkan akun-akun yang melakukan *copy-paste* atau memposting kalimat yang nyaris identik.
- **Maksimum Jeda Waktu:** Mengatur batas toleransi waktu. Jika kita setel ke angka kecil (misal 5 menit), graf hanya akan memunculkan akun-akun yang memposting topik mirip dalam waktu kurang dari 5 menit berurutan. Ini adalah indikator terkuat dari orkestrasi otomatis (bot/buzzer).
- **Ukuran Node (Fitur Baru):** Karena beberapa akun sangat dominan sehingga bulatannya menutupi garis koneksi, kita menyediakan slider ini. Mengecilkan ukuran node memungkinkan kita melihat struktur jaring laba-laba (edge) di balik node besar tersebut.

---

## Slide 5: Investigasi Mendalam (Deep Dive Analysis)
**Visual di layar:** Klik sebuah node besar, lalu tunjukkan tab "Inspeksi".

**Poin Bicara:**
Sistem ini tidak hanya memberikan peta *helicopter view*, tapi juga memungkinkan kita menjadi detektif digital.
- Jika kita menemukan satu kluster mencurigakan, kita bisa mengklik salah satu akun utamanya.
- Pada panel **Inspeksi**, kita bisa melihat bukti konkrit: 
  - Apa *keyword* (kata kunci) yang mereka narasikan.
  - Rekam jejak **waktu tweet** secara berurutan (Timeline tweet). Dari waktu ini kita tahu persis siapa penyebar pertama dan siapa yang mengekor (mengamplifikasi).
  - Jika kita klik garis (edge) di antara dua akun, sistem akan memunculkan secara transparan perbandingan isi tweet asli dari kedua akun tersebut untuk membuktikan tingkat kemiripan semantiknya.

---

## Slide 6: Kesimpulan & Temuan
**Visual di layar:** Tampilan tabel kluster (Tab Kluster) yang menunjukkan status "Koordinasi Kuat" vs "Tersebar".

**Poin Bicara:**
- **Validasi Bukti:** Dengan melacak jejak semantik dan jeda waktu, sistem berhasil membedakan mana topik yang viral secara organik (jeda waktu acak, kemiripan redaksional rendah) dan mana yang diviralkan secara terkoordinasi/pabrikasi (jeda waktu rapat, redaksional identik).
- **Manfaat Alat Ini:** Visualisasi ini sangat berguna untuk jurnalis, peneliti, atau analis politik dalam membongkar operasi *astroturfing* (kampanye buatan yang seolah-olah aspirasi publik asli) di media sosial secara akurat dan berbasis data (*evidence-based*).

---

> [!TIP]
> **Saran Saat Presentasi:**
> - Jangan terlalu lama di definisi, usahakan langsung demo dashboard-nya (kalau memungkinkan presentasi sambil buka web HTML-nya).
> - Saat menjelaskan Slide 3, langsung praktikkan menggeser slider **"Ukuran node"** ke kiri agar audiens paham masalah node besar yang menutupi garis.
> - Saat Slide 5, klik dua kali (klik Node, lalu klik Edge) untuk mendemonstrasikan tab "Inspeksi" dan memperlihatkan betapa lengkapnya data *timestamp* dan *tweet text* yang ditangkap sistem.
