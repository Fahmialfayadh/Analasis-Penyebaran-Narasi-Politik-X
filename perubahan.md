# Perubahan Algoritma dan Konfigurasi

Dokumen ini merangkum perubahan yang memengaruhi hasil analisis, bukan perubahan kosmetik kecil.

## 1. Pemrosesan Metadata Tweet

Pipeline sekarang tidak hanya membaca `name`, `content`, dan `date_created`, tetapi juga metadata tambahan:

- `id`
- `author`
- `contentJson`
- `num_retweets`
- `in_reply_to_screen_name`
- `type`
- `lang`
- `query_candidate`
- `source_file`
- `rt_source`
- `rt_source_id`
- `is_retweet`
- `is_reply_or_mention`

Dampak ke analisis:

- Retweet bisa dibedakan dari tweet asli.
- Reply/mention bisa diberi konteks terpisah.
- Sumber retweet bisa dilacak.
- Dataset bisa diaudit sebelum masuk analisis graf.

Output audit ditambahkan:

- `data_audit.csv`

## 2. Pembersihan Teks Dipisah Berdasarkan Tujuan

Sebelumnya teks cenderung dipakai langsung untuk semua kebutuhan. Sekarang ada dua versi teks:

- `cleaned_content`: untuk embedding dan similarity.
- `topic_content`: untuk ekstraksi keyword/topik kluster.

Perubahan penting:

- Marker `RT` dibersihkan dari teks analisis.
- Pola reply seperti `[RE ...]` dibersihkan.
- Kata teknis seperti `rt`, `retweet`, `tweet`, URL, dan noise umum tidak ikut mendominasi keyword.

Dampak ke analisis:

- Kemiripan narasi tidak bias karena format retweet.
- Keyword kluster lebih menggambarkan topik, bukan artefak Twitter/X.

## 3. Retweet Tidak Lagi Disamakan dengan Tweet Non-RT

Ini perubahan algoritma paling penting.

Retweet sekarang diperlakukan sebagai jenis edge berbeda:

- `edge_type = retweet`
- `edge_type = semantic`

### Edge Retweet

Dua akun dianggap punya edge retweet jika:

- keduanya adalah retweet;
- punya `rt_source_id` yang sama;
- jika `rt_source_id` kosong, fallback ke `rt_source` yang sama;
- selisih waktu <= `THRESHOLD_RETWEET_TIME`.

### Edge Semantic

Dua akun dianggap punya edge semantic jika:

- bukan retweet, karena `INCLUDE_RETWEETS_IN_SEMANTIC = False`;
- kemiripan teks >= `THRESHOLD_TEXT`;
- selisih waktu <= `THRESHOLD_TIME`.

Dampak ke analisis:

- Akun tidak masuk kluster semantic hanya karena me-retweet konten yang sama.
- Retweet tetap bisa dianalisis, tetapi tidak dicampur dengan koordinasi narasi non-RT.
- Komposisi edge bisa dibaca: berapa RT dan berapa semantic.

## 4. Konfigurasi Utama Pipeline

Konfigurasi utama di `FP_Tegraf.py`:

| Parameter | Nilai | Fungsi |
|---|---:|---|
| `MODEL_NAME` | `symanto/sn-xlm-roberta-base-snli-mnli-anli-xnli` | Model embedding kalimat |
| `MAX_ROWS` | `None` | Memakai seluruh data, bukan sample kecil |
| `ALPHA` | `0.5` | Bobot seimbang antara similarity teks dan kedekatan waktu |
| `LAMBDA` | `0.001155` | Kontrol peluruhan skor waktu |
| `THRESHOLD_TEXT` | `0.65` | Minimum similarity teks untuk edge semantic |
| `THRESHOLD_TIME` | `1800` detik | Batas waktu semantic, 30 menit |
| `THRESHOLD_RETWEET_TIME` | `1800` detik | Batas waktu shared-retweet, 30 menit |
| `INCLUDE_RETWEETS_IN_SEMANTIC` | `False` | RT tidak ikut edge semantic |
| `LOUVAIN_RESOLUTION` | `2.0` | Resolusi community detection pipeline utama |
| `RANDOM_SEED` | `42` | Reproducibility |
| `MIN_SUSPICIOUS_CLUSTER_SIZE` | `5` | Minimum akun untuk status kuat |
| `MIN_SUSPICIOUS_EDGE_EVIDENCE` | `5` | Minimum bukti pasangan untuk status kuat |
| `RUN_SENSITIVITY` | `False` | Sensitivity tidak dijalankan default |

Formula bobot edge:

```text
s_time = exp(-LAMBDA * delta_t)
weight = (ALPHA * s_text) + ((1 - ALPHA) * s_time)
```

Artinya:

- `s_text` menjawab: narasinya mirip atau tidak.
- `s_time` menjawab: munculnya berdekatan waktu atau tidak.
- `weight` adalah gabungan keduanya.

## 5. Output Edge Dibuat Lebih Transparan

Output `relation.csv` sekarang menyimpan informasi agregat:

- `Weight`
- `Max_Weight`
- `Edge_Count`
- `Avg_Text_Similarity`
- `Avg_Time_Score`
- `Min_Time_Delta_Seconds`
- `Edge_Types`
- `Dominant_RT_Source`
- `Query_Context`
- `Example_Tweet_1`
- `Example_Tweet_2`

Output tambahan:

- `relation_evidence.csv`

Isi `relation_evidence.csv` adalah bukti edge mentah sebelum agregasi.

Dampak ke analisis:

- Bisa dicek kenapa dua akun dianggap berhubungan.
- Bisa dibedakan apakah hubungan karena retweet atau karena narasi mirip.
- Bisa dilihat contoh tweet pembentuk edge.

## 6. Status Kluster Tidak Lagi Disebut Langsung sebagai Buzzer

Label status dibuat lebih hati-hati:

- `Koordinasi Kuat`
- `Perlu Investigasi`
- `Indikasi Lemah`
- `Rendah`

Skor koordinasi:

```text
buzzer_score = density * log2(size + 1)
```

Syarat status mempertimbangkan:

- jumlah akun;
- density kluster;
- jumlah bukti pasangan edge.

Dampak ke analisis:

- Tidak langsung menuduh akun sebagai buzzer.
- Istilah lebih cocok untuk analisis akademik: indikasi koordinasi, bukan vonis.

## 7. Pelabelan Kluster Diubah dari "Pendukung" menjadi Fokus Narasi

Label seperti `Pendukung Prabowo` atau `Pendukung Ganjar` dihindari.

Label sekarang berbasis objek pembahasan:

- `Dominan membahas Anies-Muhaimin`
- `Dominan membahas Prabowo-Gibran`
- `Dominan membahas Ganjar-Mahfud`
- `Lintas kandidat / perbandingan`
- `Tanpa kandidat dominan`

Dampak ke analisis:

- Menyebut kandidat tidak otomatis dianggap mendukung kandidat tersebut.
- Label kluster lebih aman secara interpretasi.
- Dashboard tidak overgeneralized.

## 8. Dashboard Non-RT Dibuat Terpisah

File baru:

- `visualisasi_non_rt_light.html`

Dashboard ini tidak memakai `relation.csv` langsung, tetapi membangun ulang edge dari:

- `relation_evidence.csv`
- hanya `edge_type = semantic`

Dampak:

- Kluster di versi ini tidak bisa terbentuk hanya karena shared-retweet.
- Retweet tidak menjadi dasar pembentukan kluster.
- Rasio RT akun tetap ditampilkan hanya sebagai konteks perilaku.

## 9. Backbone Non-RT untuk Mengurangi Kluster yang Melebar

Masalah sebelumnya:

- Semua edge semantic yang lolos threshold awal divisualkan.
- Banyak edge hanya punya 1 bukti.
- Edge tunggal bisa menjadi jembatan antar sub-narasi.
- Akibatnya graf terlihat seperti satu kluster besar.

Konfigurasi backbone Non-RT di `generate_dashboard.py`:

| Parameter | Nilai | Fungsi |
|---|---:|---|
| `NON_RT_MIN_AVG_SIMILARITY` | `0.75` | Minimum rata-rata similarity edge untuk visual Non-RT |
| `NON_RT_MAX_MIN_DELTA_SECONDS` | `300` detik | Minimum jeda tercepat harus <= 5 menit |
| `NON_RT_LOUVAIN_RESOLUTION` | `6.5` | Community detection lebih granular untuk dashboard Non-RT |

Dampak:

- Edge lemah tidak lagi menjadi jembatan visual.
- Kluster Non-RT lebih terpisah.
- Graf lebih mudah dibaca.

Hasil setelah backbone:

- Edge semantic awal: `1935`
- Edge semantic yang dipakai backbone: `1259`
- Edge visual internal kluster: `391`
- Total kluster: `23`
- Node tampil: `148`
- Total edge RT dalam kluster Non-RT: `0`
- Node `is_retweet=true` di versi Non-RT: `0`

## 10. Alasan Masuk Kluster Ditambahkan

Dashboard Non-RT sekarang menampilkan alasan kenapa akun masuk satu kluster.

Metrik yang ditampilkan:

- rata-rata kemiripan teks;
- median jeda waktu;
- jumlah edge dengan teks sangat mirip;
- jumlah edge dengan jeda <= 1 menit;
- contoh pasangan akun pembentuk edge;
- similarity pasangan;
- jeda waktu pasangan;
- contoh tweet pasangan.

Dampak:

- Bisa dibaca apakah kluster terbentuk terutama karena narasi mirip, waktu berdekatan, atau kombinasi keduanya.
- Analisis tidak lagi terasa seperti black box.

## 11. Warna Visual Non-RT Diubah

Sebelumnya warna node mengikuti fokus kandidat.

Masalah:

- Banyak kluster yang sama-sama membahas Ganjar-Mahfud terlihat sebagai satu massa merah.
- Secara visual jadi tampak seperti satu kluster besar, padahal komunitasnya berbeda.

Perubahan:

- Pada dashboard Non-RT, warna node membedakan kluster visual.
- Fokus narasi tetap ditampilkan di badge dan panel detail.

Dampak:

- Kluster lebih mudah dibedakan.
- Label fokus narasi tetap tidak berubah menjadi klaim dukungan.

## 12. File Output Penting

File analisis utama:

- `cleaned_data.csv`
- `data_audit.csv`
- `relation.csv`
- `relation_evidence.csv`
- `cluster_density_report.csv`

File visualisasi:

- `visualisasi_st.html`: versi umum, memuat edge semantic dan retweet yang sudah dipisahkan.
- `visualisasi_non_rt_light.html`: versi Non-RT, hanya memakai backbone semantic non-retweet.

## Ringkasan Dampak

Perubahan paling berpengaruh terhadap hasil analisis:

1. Retweet dipisahkan dari semantic coordination.
2. RT tidak ikut edge semantic.
3. Edge menyimpan bukti dan tipe relasi.
4. Label kluster tidak lagi mengklaim dukungan politik.
5. Dashboard Non-RT memakai backbone agar kluster tidak melebar karena edge lemah.
6. Detail kluster sekarang menjelaskan alasan: teks, waktu, dan contoh pasangan bukti.

