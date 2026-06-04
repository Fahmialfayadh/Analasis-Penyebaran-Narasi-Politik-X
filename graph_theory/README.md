# Fungsi Teori Graf

Folder ini memisahkan fungsi fundamental teori graf dari pipeline utama.
Tujuannya supaya implementasi graf mudah ditunjukkan saat presentasi.

## Representasi Graf

- Node: akun X/Twitter.
- Edge: hubungan koordinasi antar-akun.
- Weight: bobot kekuatan hubungan.
- Graf: undirected weighted graph memakai NetworkX.

## Rumus Bobot Edge

```text
s_time = exp(-lambda * delta_t)
w_ij   = alpha * s_text + (1 - alpha) * s_time
```

Keterangan:

- `s_text`: kemiripan teks, dari cosine similarity embedding.
- `delta_t`: selisih waktu posting dalam detik.
- `s_time`: skor kedekatan waktu.
- `alpha`: porsi pengaruh kemiripan teks.
- Untuk shared-retweet, `s_text = 1.0` karena dua akun membagikan sumber retweet yang sama.

## Fungsi Utama

- `calculate_edge_weight`: deklarasi bobot edge.
- `build_weighted_coordination_graph`: membentuk graf berbobot dari `relation.csv`.
- `add_account_node_attributes`: menempelkan atribut akun ke node.
- `compute_pagerank`: menghitung sentralitas akun.
- `detect_louvain_communities`: mendeteksi cluster/komunitas.
- `calculate_cluster_density_report`: menghitung density dan skor koordinasi cluster.

Pipeline utama tetap ada di `FP_Tegraf.py`. File ini adalah versi modular dan eksplisit dari bagian teori graf yang dipakai di sana.
