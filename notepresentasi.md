# Catatan Presentasi: Penjelasan Rumus Matematis

Jika dosen/penguji bertanya asal-usul rumus yang digunakan pada *Slide Pengukuran Kemiripan & Waktu*, berikut adalah argumen akademis yang bisa digunakan:

## 1. Asal Rumus Kemiripan Teks ($S_{\text{text}}$)
**Rumus:** $S_{\text{text}} = \cos(\mathbf{e}_1, \mathbf{e}_2)$
* **Darimana:** Ini adalah rumus baku **Cosine Similarity** dari *Vector Space Model* (diperkenalkan pertama kali oleh Gerard Salton tahun 1970-an untuk *Information Retrieval*). Ini adalah standar industri mutlak dalam AI/NLP modern.
* **Cara Menjawab:** "Teks bahasa alami diubah oleh model AI menjadi vektor angka (*embedding*). Rumus *Cosine Similarity* ini tidak mengukur 'jarak', tapi mengukur 'sudut' antar dua vektor tersebut. Ini dipakai karena paling efektif mendeteksi kemiripan *makna (semantik)* meskipun panjang-pendek karakternya berbeda."

## 2. Asal Angka $0.001155$ di Rumus Waktu ($S_{\text{time}}$)
**Rumus:** $S_{\text{time}} = \exp(-0.001155 \Delta t)$
* **Darimana:** Ini diadopsi dari **Hukum Peluruhan Radioaktif di Fisika (Exponential Decay Law)**, yang banyak dipakai di sistem rekomendasi komputer sebagai *time-decay function*.
* **Cara Menjawab:** "Kami menggunakan model peluruhan eksponensial karena relevansi informasi menurun secara drastis seiring waktu (tidak menurun secara linear). Angka unik **$0.001155$** bukanlah angka acak, melainkan konstanta laju peluruhan ($\lambda$) yang diturunkan secara matematis. Kami menetapkan **waktu paruh (half-life) sebesar 10 menit (600 detik)**. Karena rumusnya adalah $\lambda = \ln(2) \div 600$, hasil pembagian tersebut adalah tepat $0.001155$. Artinya, setiap 10 menit, kecurigaan koordinasi waktunya berkurang persis setengahnya."

## 3. Asal Rumus Bobot 50-50 ($Weight$)
**Rumus:** $\text{weight} = 0.5 S_{\text{text}} + 0.5 S_{\text{time}}$
* **Darimana:** Ini adalah metode **Linear Combination / Multi-Criteria Decision Analysis** sederhana. Kedua variabel bisa digabung langsung karena sudah sama-sama dinormalisasi pada skala rasio 0 sampai 1.
* **Cara Menjawab:** "Kami menggabungkan kedua skor dengan metode penjumlahan terbobot (*weighted sum*). Bobot 0.5 (atau 50:50) dipakai sebagai **heuristic (asumsi dasar) yang adil** dalam mendeteksi operasi astroturfing. Asumsinya: untuk membuktikan ada manipulasi perbincangan, *kemiripan isi pesan* memiliki derajat pembuktian yang sama krusialnya dengan *keserempakan waktu posting*."

---
**Tips Ekstra:**
*Kalau ditanya: "Kenapa nggak pakai korelasi biasa atau regresi linear?"*
*Jawab:* "Karena tujuan penelitian ini bukan mencari hubungan sebab-akibat (kausalitas) antar variabel, melainkan mencari nilai **kekuatan koneksi (edge weight)** untuk membentuk graf (*Network Analysis*)."
