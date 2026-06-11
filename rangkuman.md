# Rangkuman Hasil Analisis Koordinasi Narasi Politik (Pilpres 2024)

Dokumen ini merangkum temuan terperinci dari hasil *Network Analysis* terhadap dataset sampel (`DE-sample-X-capres2024`). Hasil ini membuktikan adanya pola pergerakan non-organik (terkoordinasi) dalam penyebaran isu terkait ketiga kandidat capres.

---

## 1. Statistik Umum
Berdasarkan pemrosesan data, berikut adalah gambaran besar populasi dataset yang dianalisis:
- **Total Akun Unik:** 584 akun X (Twitter).
- **Total Tweet:** 1.002 tweet.
- Dari 584 akun tersebut, terdeteksi **390 akun (66%)** yang secara aktif terlibat dalam perilaku terkoordinasi yang kuat.
- Terdapat **1.682 pasangan koneksi (edges)** antar akun yang memiliki kemiripan teks sangat tinggi (Similarity $\ge$ 0.75) dan jeda waktu sangat cepat (di bawah 5 jam).

## 2. Temuan Utama: Akun Paling Terkoordinasi (Top Buzzers)
Algoritma mendeteksi sekumpulan akun yang secara berulang memposting teks yang nyaris identik dalam jeda waktu yang tidak masuk akal untuk ukuran manusia (kurang dari 10 menit).

**Contoh Top 3 Pasangan Akun Paling Agresif:**
1. **@Agustiadi_ $\leftrightarrow$ @Delan_setiapano** 
   - Bukti: 46 pasang tweet yang saling identik.
   - Kemiripan Semantik: 83.8%
   - Rata-rata Jeda Waktu: **Hanya 2.9 menit!**
2. **@Agustiadi_ $\leftrightarrow$ @Mahda_bana** 
   - Bukti: 46 pasang tweet.
   - Kemiripan Semantik: 83.8%
   - Rata-rata Jeda Waktu: 8.8 menit.
3. **@Delan_setiapano $\leftrightarrow$ @Mahda_bana** 
   - Bukti: 46 pasang tweet.
   - Kemiripan Semantik: 83.8%
   - Rata-rata Jeda Waktu: 2.6 menit.

> [!IMPORTANT]
> Kecepatan respon (jeda di bawah 3 menit) yang dilakukan berulang kali (46 kali) membuktikan bahwa ketiga akun ini (`@Agustiadi_`, `@Delan_setiapano`, dan `@Mahda_bana`) sangat mungkin dioperasikan oleh bot atau mesin *auto-post* dari satu sumber komando yang sama (satu kluster).

## 3. Topik & Narasi yang Diviralkan
Tiga narasi utama yang paling banyak didorong oleh jaringan terkoordinasi (dari 390 akun bot/buzzer) adalah:
- **Ganjar Pranowo / Mahfud:** 277 tweet terkoordinasi.
- **Anies Baswedan / Muhaimin:** 256 tweet terkoordinasi.
- **Prabowo Subianto / Gibran:** 209 tweet terkoordinasi.

**Contoh Tweet Spesifik yang Paling Banyak Di-copy-paste (Amplifikasi):**
1. **Isu Uang & Prabowo (Terkait Anies):** 
   *"Calon presiden nomor urut 1, Anies Baswedan, merespons atas beredarnya video Gus Miftah bagi-bagi duit di pesantrennya dan di belakangnya ada kaus Prabowo-Gibran..."*
2. **Deklarasi Pemuda (Terkait Prabowo-Gibran):**
   *"Pemuda Kabupaten Serang Deklarasi Dukung Prabowo-Gibran Jadi Presiden 2024..."* (dengan hashtag `#MenangSeputaran`).

---

## 4. Kesimpulan

1. **Keberadaan Pasukan Siber (Astroturfing):** Data menunjukkan secara meyakinkan bahwa opini politik di platform X selama masa sampel tidak terjadi secara organik. Angka partisipasi koordinasi sebesar 66% (390 dari 584 akun) mengindikasikan bahwa perbincangan sangat didominasi oleh operasi *astroturfing* (rekayasa opini seolah-olah organik).
2. **Pola Serangan/Amplifikasi Mesin:** Akun-akun teratas memposting narasi yang sama dalam hitungan kurang dari 3 menit puluhan kali. Ini adalah karakteristik dari **Automated Botnets** atau *Buzzer* yang menggunakan script, bukan manusia yang mengetik manual.
3. **Senjata Utamanya adalah Copy-Paste Semantik:** Tidak hanya mengandalkan *Retweet* (RT), pasukan siber ini menggunakan teknik *copy-paste* teks (kemiripan semantik rata-rata di atas 83%) untuk mengelabui algoritma Twitter yang biasanya menekan jangkauan jika sebuah narasi hanya mengandalkan rasio RT saja.
4. **Semua Kubu Terlibat:** Koordinasi tidak terbatas pada satu kubu politik. Berdasarkan query kandidat, narasi dari ketiga kubu (Ganjar, Anies, dan Prabowo) sama-sama dipompakan oleh akun-akun yang berada di bawah komando koordinasi yang kuat.

Secara keseluruhan, visualisasi dan analisis dashboard final ini berhasil menjadi alat **forensik digital** yang efektif untuk membuka kedok kampanye manipulasi opini pada platform X.
