# Hasil Analisis Koordinasi Narasi Politik di Twitter/X

Dokumen ini merangkum hasil analisis koordinasi narasi politik di Twitter/X pada dataset capres 2024. Fokus utama analisis ini bukan untuk memberi label bahwa sebuah akun adalah bot, buzzer, atau pendukung kandidat tertentu, melainkan untuk membaca pola hubungan antarakun dari sisi kemiripan narasi dan kedekatan waktu unggahan.

Dengan kata lain, istilah **koordinasi** dalam laporan ini harus dipahami sebagai pola graf: beberapa akun terhubung karena mengunggah teks yang mirip, dalam waktu yang berdekatan, atau karena melakukan retweet dari sumber yang sama. Analisis ini membaca pola perilaku di data, bukan motif asli pemilik akun.

Angka dan interpretasi dalam dokumen ini berasal dari output proyek yang sudah tersedia, terutama:

- `cleaned_data.csv`
- `data_audit.csv`
- `relation.csv`
- `relation_evidence.csv`
- `cluster_density_report.csv`
- `visualisasi_st.html`
- `visualisasi_non_rt_light.html`

## 1. Gambaran Sumber Data

Data yang dianalisis berada di folder:

```text
data/DE-sample-X-capres2024/DE-sample-X-capres2024/
```

Ada tiga file JSON utama yang dipakai. Masing-masing file mewakili query terhadap salah satu kandidat.

| File | Label Query |
|---|---|
| `data-twit-anies.json` | `anies` |
| `data-twit-ganjar.json` | `ganjar` |
| `data-twit-prabowo.json` | `prabowo` |

Perlu dicatat bahwa pipeline tidak melakukan crawling Twitter/X secara langsung saat script dijalankan. Script hanya membaca file JSON yang sudah tersedia di folder data. Jadi, hasil analisis ini berlaku untuk dataset tersebut, bukan untuk keseluruhan percakapan politik di Twitter/X.

## 2. Ringkasan Dataset

Dataset berisi **1002 tweet** dari **584 akun unik**. Semua tweet berada dalam rentang waktu yang cukup pendek, yaitu dari **2024-01-04 17:59:59 UTC** sampai **2024-01-04 18:21:20 UTC**. Artinya, seluruh data yang dianalisis hanya mencakup sekitar 21 menit percakapan.

| Metrik | Nilai |
|---|---:|
| Total baris tweet | 1002 |
| Akun unik | 584 |
| Rentang waktu awal | 2024-01-04 17:59:59 UTC |
| Rentang waktu akhir | 2024-01-04 18:21:20 UTC |
| Retweet rows | 563 |
| Rasio retweet | 0.5619 |
| Reply/mention rows | 661 |
| Empty cleaned content | 0 |
| Bahasa | 1002 baris `id` |
| Tipe | 1002 baris `twit` |

Secara jumlah baris, dataset terlihat seimbang karena setiap query kandidat memiliki 334 tweet. Namun, ketika dilihat lebih dalam, komposisi retweet-nya tidak seimbang. Query `anies` dan `prabowo` didominasi retweet, sedangkan query `ganjar` jauh lebih banyak berisi tweet non-retweet.

| Query | Jumlah Tweet | Akun Unik | Retweet | Reply/Mention |
|---|---:|---:|---:|---:|
| `anies` | 334 | 187 | 302 | 325 |
| `ganjar` | 334 | 255 | 34 | 54 |
| `prabowo` | 334 | 199 | 227 | 282 |

Perbedaan ini penting karena retweet secara alami membuat banyak teks menjadi sama atau sangat mirip. Jika retweet dicampur begitu saja dengan analisis kemiripan narasi, kluster bisa terlihat sangat kuat padahal penyebab utamanya hanya karena banyak akun me-retweet unggahan yang sama. Karena itu, proyek ini memisahkan hubungan berbasis retweet dari hubungan berbasis kemiripan narasi non-retweet.

## 3. Cara Data Dibaca dan Disiapkan

Pipeline membaca file dengan pola:

```text
data-twit-*.json
```

Dari setiap file, script mempertahankan beberapa kolom penting seperti nama akun, isi tweet, waktu unggah, ID tweet, penulis, metadata JSON, jumlah retweet, informasi reply, tipe, dan bahasa. Selain itu, script juga menambahkan dua informasi baru: `query_candidate`, yaitu label kandidat yang diambil dari nama file, serta `source_file`, yaitu nama file asal tweet.

Setelah semua data digabung, tweet diurutkan berdasarkan `date_created`. Pengurutan ini penting karena analisis tidak hanya melihat kemiripan teks, tetapi juga memperhitungkan seberapa dekat waktu antarunggahan.

## 4. Preprocessing Teks

Sebelum dihitung kemiripannya, teks tweet dibersihkan terlebih dahulu. Proses ini menghasilkan dua versi teks: `cleaned_content` dan `topic_content`.

| Kolom | Fungsi |
|---|---|
| `cleaned_content` | Teks untuk embedding dan similarity |
| `topic_content` | Teks untuk TF-IDF keyword/topik |

`cleaned_content` dipakai untuk menghitung kemiripan semantik. Pada tahap ini, script menghapus marker `RT`, pola reply seperti `[RE username]`, URL, dan spasi berlebih. Tujuannya agar model embedding lebih fokus pada isi narasi, bukan pada format teknis tweet.

Sementara itu, `topic_content` dipakai untuk membaca kata kunci atau topik kluster. Versi ini lebih dibersihkan lagi: mention dihapus, tanda `#` dihilangkan tetapi kata hashtag tetap dipertahankan, karakter non-alfanumerik dibuang, dan token yang terlalu pendek dihapus.

Dengan pembersihan seperti ini, URL dan mention tidak mendominasi hasil keyword. Retweet juga tidak dianggap berbeda hanya karena memiliki marker `RT`. Hasil akhirnya adalah teks yang lebih representatif untuk membaca isi narasi.

## 5. Pemisahan Retweet dari Narasi Non-RT

Salah satu bagian paling penting dalam analisis ini adalah deteksi retweet. Retweet dideteksi dari beberapa sumber: metadata `contentJson.rt_status`, kolom `rt_source`, `rt_source_id`, marker teks `[RE username]` sebagai fallback, dan teks yang diawali `RT`.

Dari proses ini, script menghasilkan kolom seperti:

- `is_retweet`
- `rt_source`
- `rt_source_id`
- `is_reply_or_mention`

Pemisahan ini krusial. Dua akun yang me-retweet sumber yang sama memang dapat terlihat sangat mirip, tetapi kemiripan itu berbeda maknanya dari dua akun yang menulis tweet non-retweet dengan narasi yang sama atau hampir sama. Karena itu, analisis membedakan **shared-retweet** dari **semantic coordination non-RT**.

## 6. Embedding, Similarity, dan Kedekatan Waktu

Untuk mengukur kemiripan isi tweet, proyek ini menggunakan model embedding:

```text
symanto/sn-xlm-roberta-base-snli-mnli-anli-xnli
```

Setiap `cleaned_content` diubah menjadi vektor embedding. Setelah itu, kemiripan antartweet dihitung menggunakan cosine similarity. Dalam output, nilai ini disebut `s_text`. Nilai yang mendekati 1 menunjukkan teks yang sangat mirip secara semantik. Jika nilainya 1, biasanya teks tersebut identik atau hampir identik.

Selain teks, waktu unggah juga dihitung. Untuk setiap pasangan tweet, script menghitung selisih waktu absolut dalam detik:

```text
delta_t = selisih waktu absolut dalam detik
s_time = exp(-LAMBDA * delta_t)
```

Konfigurasi yang dipakai adalah:

```text
LAMBDA = 0.001155
```

Semakin kecil `delta_t`, semakin tinggi `s_time`. Jika dua tweet muncul pada detik yang sama, skor waktunya sangat tinggi. Jika jedanya hanya beberapa detik, hubungan waktunya masih kuat. Jika jedanya mendekati 30 menit, pasangan itu masih bisa lolos batas waktu, tetapi skor waktunya menurun.

Bobot akhir edge dihitung dengan formula:

```text
weight = (ALPHA * s_text) + ((1 - ALPHA) * s_time)
```

Dengan konfigurasi:

```text
ALPHA = 0.5
```

Artinya, bobot edge menyeimbangkan dua hal: seberapa mirip narasinya dan seberapa dekat waktu kemunculannya.

## 7. Jenis Hubungan Antarakun

Dalam graf, ada dua jenis edge utama.

Pertama, **edge semantic**. Edge ini terbentuk jika dua tweet bukan retweet, memiliki kemiripan teks minimal `0.65`, dan muncul dalam jarak waktu maksimal `1800 detik`. Karena `INCLUDE_RETWEETS_IN_SEMANTIC = False`, retweet tidak ikut membentuk edge semantic. Jadi, edge jenis ini menunjukkan kemiripan narasi non-retweet.

Kedua, **edge retweet**. Edge ini terbentuk jika dua tweet sama-sama retweet, memiliki sumber retweet yang sama, dan muncul dalam rentang waktu maksimal `1800 detik`. Jika `rt_source_id` kosong, script memakai `rt_source` sebagai fallback. Edge ini menunjukkan pola shared-retweet, bukan kesamaan narasi asli yang ditulis akun.

Pembedaan ini membuat interpretasi menjadi lebih aman. Kluster yang kuat karena retweet tidak dibaca sama dengan kluster yang kuat karena tweet non-RT yang mirip.

## 8. Ringkasan Edge yang Terbentuk

Dari `relation.csv`, terdapat **2357 edge teragregasi** yang berasal dari **2816 evidence mentah**. Mayoritas edge adalah edge semantic.

| Metrik | Nilai |
|---|---:|
| Edge teragregasi | 2357 |
| Evidence mentah | 2816 |
| Edge semantic | 1929 |
| Edge retweet | 422 |
| Edge campuran semantic + retweet | 6 |

Jika dilihat dari `relation_evidence.csv`, evidence semantic berjumlah 2192, sedangkan evidence retweet berjumlah 624.

| Tipe Evidence | Jumlah |
|---|---:|
| `semantic` | 2192 |
| `retweet` | 624 |

Secara umum, edge yang terbentuk memiliki bobot cukup tinggi. Rata-rata `Weight` adalah 0.8903 dan median 0.8914. Rata-rata similarity teks juga tinggi, yaitu 0.8495. Median jeda minimum hanya 12 detik, menunjukkan banyak pasangan tweet muncul dalam waktu yang sangat dekat.

| Metrik | Rata-rata | Median | Min | Max |
|---|---:|---:|---:|---:|
| `Weight` | 0.8903 | 0.8914 | 0.4982 | 1.0000 |
| `Edge_Count` | 1.1947 | 1.0000 | 1 | 46 |
| `Avg_Text_Similarity` | 0.8495 | 0.8526 | 0.6502 | 1.0000 |
| `Avg_Time_Score` | 0.9312 | 0.9862 | 0.2863 | 1.0000 |
| `Min_Time_Delta_Seconds` | 68.42 | 12.00 | 0 | 1083 |

Namun, mayoritas edge hanya memiliki `Edge_Count = 1`. Karena itu, dashboard Non-RT memakai backbone tambahan agar visualisasi tidak terlalu melebar akibat edge yang lemah atau terlalu banyak.

## 9. Graf Umum dan Deteksi Komunitas

Graf umum dibangun dari `relation.csv`, sehingga memuat edge semantic, edge retweet, dan edge campuran. Community detection dilakukan menggunakan Louvain dengan konfigurasi:

```text
LOUVAIN_RESOLUTION = 2.0
RANDOM_SEED = 42
```

Dari `cluster_density_report.csv`, terdeteksi **41 kluster**. Status kluster ditentukan dari struktur graf, bukan dari identitas akun.

| Status | Jumlah Kluster |
|---|---:|
| Sangat mencurigakan | 18 |
| Perlu investigasi | 4 |
| Indikasi lemah (kluster kecil/minim bukti) | 18 |
| Rendah / cenderung organik | 1 |

Skor koordinasi dihitung dengan formula:

```text
Coordination_Score = density * log2(size + 1)
```

Formula ini menggabungkan dua hal: seberapa padat hubungan dalam kluster dan seberapa besar ukuran klusternya. Kluster kecil bisa memiliki density 1.0, tetapi skornya tetap dibatasi oleh ukurannya. Sebaliknya, kluster besar akan lebih kuat jika hubungan internalnya juga padat.

## 10. Kluster Teratas pada Graf Umum

Berikut beberapa kluster teratas dari `cluster_density_report.csv`.

| Cluster | Akun | Density | Evidence | RT Edge | Semantic Edge | Skor | Status | Topik |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 5 | 41 | 0.86463 | 709 | 0 | 709 | 4.66238 | Sangat mencurigakan | koperasi, perbankan, UMKM, kredit |
| 11 | 18 | 0.95425 | 146 | 0 | 146 | 4.05358 | Sangat mencurigakan | kesehatan, mental, puskesmas |
| 6 | 13 | 1.00000 | 78 | 0 | 78 | 3.80735 | Sangat mencurigakan | nelayan, beban, kredit macet |
| 1 | 11 | 1.00000 | 186 | 55 | 6 | 3.58496 | Sangat mencurigakan | deklarasi pemuda, Prabowo-Gibran |
| 12 | 27 | 0.68376 | 240 | 0 | 240 | 3.28708 | Sangat mencurigakan | count down, Februari |
| 9 | 8 | 1.00000 | 28 | 0 | 28 | 3.16993 | Sangat mencurigakan | kekerasan seksual, norma |
| 20 | 6 | 1.00000 | 15 | 15 | 0 | 2.80735 | Sangat mencurigakan | sumber RT `tomlembong` |
| 15 | 6 | 1.00000 | 15 | 15 | 0 | 2.80735 | Sangat mencurigakan | sumber RT `dapitnih` |

Dari tabel ini terlihat bahwa beberapa kluster kuat, seperti cluster 5, 11, 6, 12, dan 9, didominasi oleh edge semantic. Artinya, hubungan antarakunnya terutama terbentuk karena kemiripan narasi non-retweet.

Sebaliknya, cluster 1, 20, dan 15 mengandung retweet edge yang kuat. Kluster seperti ini tetap penting, tetapi harus dibaca sebagai pola shared-retweet. Klaim yang aman bukan bahwa akun-akun tersebut menulis narasi asli yang sama, melainkan bahwa mereka me-retweet sumber yang sama dalam waktu berdekatan.

## 11. Contoh Kluster Shared-Retweet

Salah satu contoh kluster retweet pada dashboard umum adalah kluster yang membahas deklarasi dukungan Prabowo-Gibran.

| Metrik | Nilai |
|---|---|
| Cluster | 2 pada dashboard umum |
| Jumlah akun | 11 |
| Density | 1.0 |
| Evidence | 186 |
| RT edge | 55 |
| Semantic edge | 6 |
| Sumber RT dominan | `AzzrielAzaryahu` |
| Fokus narasi | Dominan membahas Prabowo-Gibran |
| Keyword | menangseputaran, pemuda, kabupaten, deklarasi, serang |

Beberapa akun sentral yang muncul antara lain:

| Akun | Tipe Tweet di Card | Rasio RT | Contoh Narasi |
|---|---|---:|---|
| `ChairudinN6548` | Retweet | 0.75 | "Pemuda Kabupaten Serang Deklarasi Dukung Prabowo-Gibran..." |
| `doddy_h4312` | Retweet | 0.75 | "Pemuda Kabupaten Serang Deklarasi Dukung Prabowo-Gibran..." |
| `Herlina_Muachhh` | Retweet | 0.75 | "Pemuda Kabupaten Serang Deklarasi Dukung Prabowo-Gibran..." |
| `SahrulAmzi` | Retweet | 1.00 | "Pemuda Kabupaten Serang Deklarasi Dukung Prabowo-Gibran..." |
| `mehuli_ginting` | Retweet | 1.00 | "Pemuda Kabupaten Serang Deklarasi Dukung Prabowo-Gibran..." |

Kluster ini kuat secara graf, tetapi sebagian besar kekuatannya berasal dari retweet. Karena itu, interpretasi yang tepat adalah: terdapat pola shared-retweet berdekatan waktu pada narasi deklarasi dukungan Prabowo-Gibran. Kluster ini tidak boleh langsung disamakan dengan koordinasi narasi non-RT.

## 12. Dashboard Non-RT sebagai Analisis yang Lebih Bersih

Untuk membaca koordinasi narasi yang tidak didorong oleh retweet, proyek ini membuat dashboard khusus:

```text
visualisasi_non_rt_light.html
```

Dashboard ini hanya memakai evidence dengan:

```text
edge_type = semantic
```

Dengan kata lain, retweet tidak dipakai untuk membentuk kluster. Jika suatu kluster muncul di dashboard ini, maka hubungan antarakunnya muncul karena kemiripan teks non-retweet dan kedekatan waktu, bukan karena akun-akun tersebut me-retweet sumber yang sama.

Backbone Non-RT memakai konfigurasi berikut:

| Parameter | Nilai |
|---|---:|
| Minimum average similarity | 0.75 |
| Maksimum minimum time delta | 300 detik |
| Louvain resolution | 6.5 |

Hasilnya:

| Metrik | Nilai |
|---|---:|
| Edge semantic awal | 1935 |
| Edge setelah backbone | 1259 |
| Edge visual internal kluster | 391 |
| Node tampil | 148 |
| Kluster tampil | 23 |
| Total RT edge | 0 |
| Node `is_retweet=true` | 0 |

Dashboard Non-RT menjadi basis paling bersih untuk membahas koordinasi narasi non-retweet. Alasan sebuah kluster terbentuk dapat dibaca dari kombinasi similarity teks, kedekatan waktu, density, dan contoh pasangan edge.

## 13. Daftar Kluster pada Dashboard Non-RT

Cluster ID pada tabel ini berasal dari `visualisasi_non_rt_light.html`. ID ini tidak harus sama dengan ID pada `cluster_density_report.csv`, karena dashboard Non-RT memakai backbone dan resolusi Louvain yang berbeda.

| Cluster | Akun | Density | Skor | Evidence | Avg Similarity | Median Jeda | Status | Fokus Narasi | Keyword |
|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 26 | 13 | 1.0000 | 3.8074 | 78 | 1.000 | 6 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | beban, ringankan, macet, melawan, sendiri |
| 25 | 8 | 1.0000 | 3.1699 | 28 | 1.000 | 9 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | lembaga, seksual, direspons, dihindari, kekerasan |
| 35 | 7 | 1.0000 | 3.0000 | 21 | 1.000 | 1 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | pentingnya, penyuluhan, desa |
| 63 | 17 | 0.6912 | 2.8822 | 94 | 0.915 | 4 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | mental, kesehatan, dampak |
| 17 | 5 | 1.0000 | 2.5850 | 10 | 1.000 | 13 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | kepentingan, kebebasan, berpendapat |
| 29 | 5 | 1.0000 | 2.5850 | 10 | 1.000 | 11 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | cawapres, kesejahteraan, kredit |
| 34 | 5 | 1.0000 | 2.5850 | 10 | 1.000 | 17 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | tancap, gas, perbankan |
| 69 | 5 | 1.0000 | 2.5850 | 10 | 1.000 | 14 detik | Koordinasi Kuat | Dominan membahas Ganjar-Mahfud | hari susah, bahagia |
| 73 | 7 | 0.4286 | 1.2857 | 12 | 0.802 | 2.3 menit | Perlu Investigasi | Dominan membahas Ganjar-Mahfud | ganjarmahfud, mahfudlebihbaik |
| 72 | 16 | 0.3000 | 1.2262 | 43 | 0.808 | 46 detik | Perlu Investigasi | Dominan membahas Ganjar-Mahfud | ganjarmahfud, mahfudlebihbaik |
| 1 | 19 | 0.2281 | 0.9857 | 60 | 0.795 | 1.1 menit | Perlu Investigasi | Dominan membahas Ganjar-Mahfud | ganjarmahfud, mahfudlebihbaik |
| 2 | 4 | 1.0000 | 2.3219 | 6 | 1.000 | 12 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | menu, restoran |
| 23 | 4 | 1.0000 | 2.3219 | 6 | 1.000 | 6 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | jabatan, negeri, dedikasi |
| 24 | 4 | 1.0000 | 2.3219 | 6 | 1.000 | 0 detik | Indikasi Lemah | Dominan membahas Prabowo-Gibran | pemuda, dukung, deklarasi |
| 59 | 4 | 1.0000 | 2.3219 | 6 | 1.000 | 7 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | democratic, indonesian |
| 30 | 3 | 1.0000 | 2.0000 | 3 | 1.000 | 11 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | democracy, people |
| 36 | 3 | 1.0000 | 2.0000 | 3 | 1.000 | 5 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | ganjartindakannyata |
| 44 | 3 | 1.0000 | 2.0000 | 3 | 1.000 | 4 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | pemilihan |
| 57 | 3 | 1.0000 | 2.0000 | 3 | 1.000 | 6 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | presidential election |
| 62 | 3 | 1.0000 | 2.0000 | 3 | 0.969 | 5 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | kontrak, kerja |
| 0 | 3 | 0.6667 | 1.3333 | 92 | 0.838 | 2.8 menit | Indikasi Lemah | Dominan membahas Prabowo-Gibran | Demokrat, AHY, Prabowo |
| 76 | 3 | 0.6667 | 1.3333 | 2 | 0.812 | 58 detik | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | terima kasih |
| 75 | 4 | 0.5000 | 1.1610 | 3 | 0.827 | 2.3 menit | Indikasi Lemah | Dominan membahas Ganjar-Mahfud | keluarga, anak |

Dari tabel ini, pola yang paling menonjol adalah dominasi kluster Non-RT yang membahas Ganjar-Mahfud. Banyak di antaranya memiliki similarity 1.0 dan median jeda hanya beberapa detik. Ini menunjukkan bahwa sejumlah akun mengunggah narasi yang sama atau sangat mirip dalam waktu yang sangat dekat.

Namun, ukuran kluster tetap perlu diperhatikan. Beberapa kluster memang sangat padat, tetapi hanya berisi 3 sampai 5 akun. Kluster seperti ini kuat secara pola internal, tetapi tidak boleh digeneralisasi terlalu luas.

## 14. Interpretasi Detail Kluster Non-RT Terkuat

Bagian ini membahas beberapa kluster paling kuat pada dashboard Non-RT. Karena retweet sudah dikeluarkan dari pembentukan kluster, bukti yang dibahas di sini adalah bukti semantic non-RT.

### 14.1 Cluster 26: Narasi Nelayan dan Kredit Macet

Cluster 26 berisi 13 akun dengan density 1.0000, skor 3.8074, dan 78 evidence semantic. Rata-rata similarity-nya 1.000, dengan median jeda hanya 6 detik.

| Metrik | Nilai |
|---|---:|
| Akun | 13 |
| Density | 1.0000 |
| Skor | 3.8074 |
| Evidence | 78 |
| Semantic edge | 78 |
| Avg similarity | 1.000 |
| Median jeda | 6 detik |
| Status | Koordinasi Kuat |

Beberapa akun sentral dalam kluster ini adalah `ow1b0v562dkee04`, `anoodyhh123`, `3zvaec23mmg78p3`, `lis_dua23640`, dan `9r28488u96dhe41`. Contoh narasinya berbunyi: "Nelayan tak bisa sendiri melawan kredit macet..."

Bukti pasangan menunjukkan beberapa akun mengunggah teks dengan similarity 1.000 pada detik yang sama.

| Pasangan Akun | Similarity | Jeda | Bukti |
|---|---:|---:|---:|
| `3zvaec23mmg78p3` - `lis_dua23640` | 1.000 | 0 detik | 1 |
| `9r28488u96dhe41` - `BaisCharpe69286` | 1.000 | 0 detik | 1 |
| `ow1b0v562dkee04` - `anoodyhh123` | 1.000 | 0 detik | 1 |

Kluster ini menjadi kuat karena semua akun saling terhubung, teksnya identik atau hampir identik, dan waktu unggahnya sangat dekat. Karena ini dashboard Non-RT, kesamaan tersebut bukan berasal dari retweet sumber yang sama.

Interpretasi aman: terdapat pola penyebaran narasi non-retweet yang sangat seragam tentang nelayan, kredit macet, dan Ganjar-Mahfud dalam waktu sangat dekat.

### 14.2 Cluster 25: Narasi Kekerasan Seksual dan Lembaga Pendidikan

Cluster 25 berisi 8 akun dengan density 1.0000, skor 3.1699, dan 28 evidence. Rata-rata similarity-nya 1.000, dengan median jeda 9 detik.

| Metrik | Nilai |
|---|---:|
| Akun | 8 |
| Density | 1.0000 |
| Skor | 3.1699 |
| Evidence | 28 |
| Avg similarity | 1.000 |
| Median jeda | 9 detik |
| Status | Koordinasi Kuat |

Akun yang muncul antara lain `DavidCo04395172`, `LoganWalke93437`, `NicholasRo77225`, `DylanYoung42780`, dan `EdwardBroo52343`. Contoh narasinya membahas legislasi, kekerasan seksual, lembaga pendidikan, dan penyebutan Ganjar-Mahfud.

| Pasangan Akun | Similarity | Jeda | Bukti |
|---|---:|---:|---:|
| `EdwardBroo52343` - `PeterCa03670533` | 1.000 | 0 detik | 1 |
| `DavidCo04395172` - `LoganWalke93437` | 1.000 | 0 detik | 1 |
| `DylanYoung42780` - `NicholasRo77225` | 1.000 | 1 detik | 1 |

Pola utamanya jelas: teks sangat identik, waktu unggah sangat dekat, dan hubungan antarakun sangat padat. Interpretasi aman: ada penyebaran teks non-RT yang sangat seragam pada topik legislasi dan kekerasan seksual, dengan fokus penyebutan Ganjar-Mahfud.

### 14.3 Cluster 35: Narasi Penyuluhan dan Desa

Cluster 35 berisi 7 akun dengan density 1.0000, skor 3.0000, dan 21 evidence. Rata-rata similarity-nya 1.000, dengan median jeda hanya 1 detik.

| Metrik | Nilai |
|---|---:|
| Akun | 7 |
| Density | 1.0000 |
| Skor | 3.0000 |
| Evidence | 21 |
| Avg similarity | 1.000 |
| Median jeda | 1 detik |
| Status | Koordinasi Kuat |

Akun yang muncul antara lain `kyton83321444`, `mbsqt84444943`, `hcybl92984327`, `nozit66263479`, dan `jttts84589488`. Contoh narasinya adalah: "Ganjar Pranowo Mahfud MD menyoroti pentingnya penyuluhan..."

| Pasangan Akun | Similarity | Jeda | Bukti |
|---|---:|---:|---:|
| `kyton83321444` - `mbsqt84444943` | 1.000 | 0 detik | 1 |
| `nozit66263479` - `hcybl92984327` | 1.000 | 0 detik | 1 |
| `nozit66263479` - `jttts84589488` | 1.000 | 0 detik | 1 |

Kluster ini sangat kuat karena teksnya identik, jeda waktunya hampir bersamaan, dan semua akun saling terhubung. Interpretasi aman: terdapat penyebaran narasi non-RT yang sangat seragam tentang penyuluhan dan desa, dengan fokus penyebutan Ganjar-Mahfud.

### 14.4 Cluster 63: Narasi Kesehatan Mental dan Puskesmas

Cluster 63 sedikit berbeda dari tiga kluster sebelumnya. Kluster ini lebih besar, berisi 17 akun, dengan density 0.6912, skor 2.8822, dan 94 evidence. Rata-rata similarity-nya 0.915, dengan median jeda 4 detik.

| Metrik | Nilai |
|---|---:|
| Akun | 17 |
| Density | 0.6912 |
| Skor | 2.8822 |
| Evidence | 94 |
| Avg similarity | 0.915 |
| Median jeda | 4 detik |
| Status | Koordinasi Kuat |

Akun sentral yang muncul antara lain `mitchell_j70489`, `bawerman68390`, `EBarringto16155`, `chandter4855`, dan `dwptr27963469`. Narasinya berkaitan dengan kesehatan mental dan penempatan psikolog di puskesmas.

| Pasangan Akun | Similarity | Jeda | Bukti |
|---|---:|---:|---:|
| `mitchell_j70489` - `bawerman68390` | 1.000 | 3 detik | 1 |
| `chandter4855` - `EBarringto16155` | 1.000 | 3 detik | 1 |
| `bawerman68390` - `EBarringto16155` | 1.000 | 5 detik | 1 |

Tidak semua teks dalam kluster ini benar-benar identik, tetapi rata-rata similarity 0.915 menunjukkan bahwa inti narasinya sangat dekat. Ukurannya juga lebih besar dibanding beberapa kluster lain, dan median jedanya hanya 4 detik. Interpretasi aman: ini adalah kluster non-RT yang kuat tentang kesehatan mental dan penempatan psikolog di puskesmas, dengan kombinasi teks sangat mirip dan waktu unggah yang sangat berdekatan.

### 14.5 Cluster 17: Narasi Kebebasan Berpendapat

Cluster 17 berisi 5 akun dengan density 1.0000, skor 2.5850, dan 10 evidence. Rata-rata similarity-nya 1.000, dengan median jeda 13 detik.

| Metrik | Nilai |
|---|---:|
| Akun | 5 |
| Density | 1.0000 |
| Skor | 2.5850 |
| Evidence | 10 |
| Avg similarity | 1.000 |
| Median jeda | 13 detik |
| Status | Koordinasi Kuat |

Akun yang muncul antara lain `pywih49433791`, `akodc32817493`, `wcqdi86596419`, `vftza83414785`, dan `uoudw11445115`. Contoh narasinya membahas pemimpin, kepentingan rakyat, dan kebebasan berpendapat.

| Pasangan Akun | Similarity | Jeda | Bukti |
|---|---:|---:|---:|
| `wcqdi86596419` - `akodc32817493` | 1.000 | 0 detik | 1 |
| `wcqdi86596419` - `pywih49433791` | 1.000 | 3 detik | 1 |
| `pywih49433791` - `akodc32817493` | 1.000 | 3 detik | 1 |

Kluster ini kecil, tetapi sangat padat. Interpretasi aman: terdapat pola teks non-RT yang identik atau hampir identik tentang kepentingan rakyat dan kebebasan berpendapat.

### 14.6 Cluster 29 dan 34: Narasi Kredit Perbankan untuk Koperasi/UMKM

Cluster 29 dan 34 sama-sama membahas program kredit perbankan untuk koperasi atau UMKM. Keduanya berisi 5 akun, memiliki density 1.0000, evidence 10, average similarity 1.000, dan median jeda yang sangat pendek.

Cluster 29 memiliki median jeda 11 detik dengan keyword `cawapres`, `kesejahteraan`, dan `kredit`. Akun-akunnya adalah `gmonoona137`, `gmonoona82`, `gmonoona61`, `gmonoona138`, dan `gmonoona75`. Contoh narasinya:

```text
Terimakasih. Program Capres Ganjar Pranowo dan Cawapres Mahfud MD persembahkan 35% kredit perbankan...
```

Cluster 34 memiliki median jeda 17 detik dengan keyword `tancap`, `gas`, dan `perbankan`. Akun-akunnya adalah `gmonoona140`, `gmonoona143`, `Gmonoona163`, `Gmonoona160`, dan `gmonoona145`. Contoh narasinya:

```text
Wow, luar biasa. Program Capres Ganjar Pranowo dan Cawapres Mahfud MD tancap gas, 35% kredit perbankan...
```

Kedua kluster ini menarik karena akun-akunnya memiliki pola nama yang mirip, yaitu `gmonoona...`, dan rasio RT pada card Non-RT bernilai 0.00. Artinya, kluster terbentuk dari tweet non-retweet yang sangat mirip, bukan dari retweet. Interpretasi aman: ada pola penyebaran narasi non-RT yang sangat seragam pada topik kredit perbankan, koperasi, dan UMKM.

## 15. Mengapa Akun Bisa Masuk ke Dalam Kluster?

Satu akun tidak masuk kluster hanya karena menyebut nama kandidat tertentu. Akun masuk ke kluster karena memiliki edge dengan akun lain. Edge itu terbentuk ketika teksnya mirip secara embedding, waktu unggahnya dekat, akunnya berbeda, dan untuk dashboard Non-RT, tweet tersebut bukan retweet.

Untuk dashboard Non-RT, edge juga harus lolos backbone similarity dan waktu. Jadi, dasar pengelompokan bukan label politik akun, melainkan hubungan matematis antara isi teks dan waktu unggah.

Beberapa contoh penyebab kluster terbentuk:

| Kluster | Penyebab Utama |
|---|---|
| 26 | Teks nelayan/kredit macet identik, jeda median 6 detik |
| 25 | Teks legislasi/kekerasan seksual identik, jeda median 9 detik |
| 35 | Teks penyuluhan/desa identik, jeda median 1 detik |
| 63 | Narasi kesehatan mental sangat mirip, jeda median 4 detik |
| 17 | Teks kepentingan rakyat/kebebasan berpendapat identik, jeda median 13 detik |

Dengan cara baca seperti ini, analisis menjadi lebih hati-hati. Yang dibuktikan bukan "akun ini pendukung kandidat tertentu", melainkan "akun-akun ini memiliki pola unggahan yang sangat mirip dan muncul dalam waktu yang sangat dekat".

## 16. Interpretasi Umum Hasil

Temuan utama dari analisis ini adalah bahwa dataset memiliki proporsi retweet yang tinggi, terutama pada query `anies` dan `prabowo`. Karena itu, pemisahan retweet dari semantic coordination menjadi langkah penting agar hasil tidak bias oleh konten RT yang otomatis sama.

Setelah retweet dipisahkan, masih terlihat banyak pola semantic coordination non-RT. Pada dashboard Non-RT, pola paling kuat dalam dataset ini dominan membahas Ganjar-Mahfud. Beberapa topik yang menonjol adalah nelayan dan kredit macet, legislasi dan kekerasan seksual, penyuluhan desa, kesehatan mental dan puskesmas, serta kredit perbankan untuk koperasi/UMKM.

Banyak kluster kuat memiliki similarity 1.0 dan median jeda hanya beberapa detik. Ini menunjukkan adanya unggahan dengan teks yang sama atau sangat mirip dalam waktu yang hampir bersamaan. Namun, beberapa kluster berukuran kecil, sehingga walaupun kuat secara struktur internal, hasilnya tetap harus dibaca secara proporsional.

Interpretasi yang aman adalah bahwa terdapat indikasi koordinasi narasi pada beberapa kelompok akun. Indikasi paling kuat terlihat ketika teks sangat mirip atau identik dan muncul hampir bersamaan. Dashboard Non-RT memperkuat pembacaan ini karena menunjukkan bahwa pola tersebut tidak hanya berasal dari retweet.

Namun, ada beberapa hal yang tidak boleh disimpulkan dari data ini saja. Analisis ini tidak bisa membuktikan bahwa akun pasti bot, buzzer bayaran, atau pendukung resmi kandidat tertentu. Analisis ini juga tidak bisa dipakai untuk menyimpulkan opini publik secara keseluruhan, karena dataset hanya berisi 1002 tweet dalam rentang waktu sekitar 21 menit.

## 17. Kesimpulan

Secara metodologis, proyek ini sudah lebih kuat karena retweet dipisahkan dari semantic coordination, setiap edge menyimpan bukti dan jenis relasi, kluster diberi label fokus narasi, dan dashboard Non-RT menampilkan alasan kluster melalui similarity, waktu, density, serta contoh pasangan akun.

Kesimpulan utama dari dataset ini adalah sebagai berikut:

> Pada dataset yang dianalisis, pola koordinasi paling jelas muncul pada narasi non-retweet yang membahas Ganjar-Mahfud, terutama pada topik nelayan/kredit macet, legislasi/kekerasan seksual, penyuluhan/desa, kesehatan mental/puskesmas, dan kredit perbankan untuk koperasi/UMKM. Pola tersebut kuat karena banyak akun memposting teks yang sama atau sangat mirip dalam jeda waktu sangat pendek.

Kesimpulan ini tetap memiliki batas. Dataset berukuran terbatas, rentang waktunya pendek, dan analisis ini membaca pola koordinasi graf, bukan motif, identitas asli, atau hubungan organisasi di balik akun. Karena itu, hasil paling tepat digunakan sebagai indikasi awal yang berbasis data, bukan sebagai vonis final terhadap akun atau kelompok tertentu.
