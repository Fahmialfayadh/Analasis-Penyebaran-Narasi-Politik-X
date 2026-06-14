"""Fungsi fundamental teori graf yang dipakai pada proyek.


Definisi model:
- Node: akun X/Twitter.
- Edge: hubungan koordinasi antara dua akun.
- Weight: kekuatan hubungan, dihitung dari kemiripan teks dan kedekatan waktu.

=============================================================================
ALUR PEMBUATAN GRAF (urutan pemanggilan fungsi)
=============================================================================

LANGKAH 1 — Hitung bobot setiap hubungan (edge)
    calculate_edge_weight()
    time_decay_score()
    → Mengubah pasangan tweet menjadi angka bobot (0–1).

LANGKAH 2 — Bangun objek graf dari file hasil pipeline
    build_graph_from_relation_csv()   ← pintu masuk: baca CSV dulu
        └─ build_weighted_coordination_graph()  ← inti: buat nx.Graph
    → Setiap baris di relation.csv menjadi satu edge dalam graf.

LANGKAH 3 — Tambahkan informasi akun ke setiap node
    add_account_node_attributes()
    → Misal: jumlah tweet, rasio retweet, query kandidat.

LANGKAH 4 — Ukur sentralitas akun di dalam jaringan
    compute_pagerank()
    → Akun yang banyak terhubung dengan akun penting mendapat skor tinggi.

LANGKAH 5 — Deteksi kluster / komunitas akun
    detect_louvain_communities()
    → Algoritma Louvain mengelompokkan akun yang saling terhubung rapat.

LANGKAH 6 — Beri skor dan label interpretasi tiap kluster
    cluster_density_score()
    cluster_status()
    calculate_cluster_density_report()
    → Menghasilkan cluster_density_report.csv yang berisi ringkasan tiap kluster.

=============================================================================
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Hashable

import networkx as nx
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Konstanta default
# Nilai-nilai ini bisa di-override saat memanggil fungsi,
# tapi defaultnya sudah dikalibrasi untuk dataset capres 2024.
# ---------------------------------------------------------------------------

DEFAULT_ALPHA = 0.5          # porsi kemiripan teks vs. kedekatan waktu (50:50)
DEFAULT_LAMBDA = 0.001155    # laju peluruhan skor waktu; ~600 detik → skor ~0.5 
DEFAULT_LOUVAIN_RESOLUTION = 2.0  # makin tinggi → kluster makin kecil & granular
DEFAULT_RANDOM_SEED = 42     # seed untuk hasil Louvain yang reproducible


# ===========================================================================
# LANGKAH 1 — Fungsi-fungsi perhitungan bobot edge
# ===========================================================================

def pair_key(account_a: Hashable, account_b: Hashable) -> tuple[str, str]:
    """Mengunci pasangan akun agar edge A→B dan B→A dianggap edge yang sama.

    Graf ini tidak berarah (undirected), jadi (A, B) == (B, A).
    Fungsi ini mengembalikan tuple terurut secara leksikografis
    sehingga pasangan yang sama selalu punya kunci yang sama.
    """
    return tuple(sorted((str(account_a), str(account_b))))


def time_decay_score(
    delta_t_seconds: float,
    lambda_value: float = DEFAULT_LAMBDA,
) -> float:
    """[LANGKAH 1a] Mengubah selisih waktu posting menjadi skor kedekatan (0–1).

    Rumus:
        s_time = exp(−lambda × delta_t)

    Intuisi:
    - Jika dua tweet diposting pada detik yang sama  → s_time ≈ 1.0 (sangat dekat)
    - Jika jedanya 10 menit (600 detik)              → s_time ≈ 0.5
    - Jika jedanya 30 menit (1800 detik)             → s_time ≈ 0.13 (jauh)

    Semakin kecil delta_t, skor makin dekat ke 1. Semakin jauh waktunya,
    skor turun mendekati 0.
    """
    if pd.isna(delta_t_seconds):
        return 0.0

    delta_t = max(float(delta_t_seconds), 0.0)
    return float(math.exp(-float(lambda_value) * delta_t))


def calculate_edge_weight(
    s_text: float,
    delta_t_seconds: float,
    alpha: float = DEFAULT_ALPHA,
    lambda_value: float = DEFAULT_LAMBDA,
) -> tuple[float, float]:
    """[LANGKAH 1b] Menghitung bobot akhir satu edge (hubungan antar dua akun).

    Bobot ini menggabungkan DUA dimensi:
        1. Seberapa MIRIP isi narasinya?  → s_text  (cosine similarity embedding)
        2. Seberapa DEKAT waktu postingnya? → s_time (time decay score)

    Rumus:
        w_ij = alpha × s_text + (1 − alpha) × s_time

    Dengan alpha = 0.5, kedua dimensi berkontribusi sama besar (50:50).

    Catatan khusus untuk shared-retweet:
        Pipeline memakai s_text = 1.0 karena kedua akun membagikan
        sumber retweet yang sama, sehingga teks dianggap identik.

    Return:
        (weight, s_time) — keduanya float dalam rentang [0, 1].
    """
    text_score = float(s_text)
    alpha_value = float(alpha)
    s_time = time_decay_score(delta_t_seconds, lambda_value=lambda_value)
    weight = (alpha_value * text_score) + ((1.0 - alpha_value) * s_time)
    return float(weight), float(s_time)


# ---------------------------------------------------------------------------
# Helper internal — konversi aman agar tidak crash saat data kotor
# ---------------------------------------------------------------------------

def _safe_float(value: object, default: float = 0.0) -> float:
    """Konversi ke float; kembalikan `default` jika gagal atau NaN."""
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def _safe_int(value: object, default: int = 1) -> int:
    """Konversi ke int; kembalikan `default` jika gagal atau NaN."""
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return int(parsed)


# ===========================================================================
# LANGKAH 2 — Membangun objek graf dari data edge
# ===========================================================================

def build_weighted_coordination_graph(
    edges_df: pd.DataFrame,
    source_col: str = "Source",
    target_col: str = "Target",
    weight_col: str = "Weight",
) -> nx.Graph:
    """[LANGKAH 2 — INTI] Membentuk objek nx.Graph dari DataFrame edge.

    Ini adalah fungsi INTI pembuatan graf. Input utamanya adalah DataFrame
    yang berisi daftar pasangan akun beserta bobot hubungannya
    (biasanya berasal dari relation.csv).

    Setiap baris DataFrame → satu edge di graf:

        G = (V, E)
        V (node) = akun-akun yang muncul sebagai Source atau Target
        E (edge) = pasangan akun yang punya bukti koordinasi
        Weight   = bobot kekuatan relasi (gabungan s_text dan s_time)

    Selain Weight, semua kolom lain di baris tersebut juga ikut disimpan
    sebagai atribut edge (misalnya Edge_Count, Edge_Types, Avg_Text_Similarity).
    Atribut ini akan terpakai saat menghitung laporan kluster di Langkah 6.

    Catatan: edge dengan source == target (self-loop) dilewati.
    """
    # Pastikan kolom wajib ada sebelum mulai memproses
    required_columns = {source_col, target_col, weight_col}
    missing = required_columns.difference(edges_df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ada: {sorted(missing)}")

    graph = nx.Graph()

    for _, row in edges_df.iterrows():
        source = str(row[source_col])
        target = str(row[target_col])

        # Lewati self-loop (akun terhubung ke dirinya sendiri — tidak relevan)
        if source == target:
            continue

        # Bawa semua kolom dari baris ini sebagai atribut edge
        edge_data = row.to_dict()

        # Pastikan tipe data Weight dan Edge_Count sudah benar
        edge_data[weight_col] = _safe_float(row[weight_col])
        if "Edge_Count" in edge_data:
            edge_data["Edge_Count"] = _safe_int(edge_data["Edge_Count"])

        # Tambahkan edge ke graf beserta semua atributnya
        graph.add_edge(source, target, **edge_data)

    return graph


def build_graph_from_relation_csv(
    relation_csv_path: str | Path,
    source_col: str = "Source",
    target_col: str = "Target",
    weight_col: str = "Weight",
) -> nx.Graph:
    """[LANGKAH 2 — PINTU MASUK] Baca relation.csv lalu bangun graf.

    Ini adalah versi praktis dari build_weighted_coordination_graph().
    Perbedaannya hanya di input:
    - Fungsi ini menerima PATH file CSV.
    - build_weighted_coordination_graph() menerima DataFrame yang sudah di-load.

    Gunakan fungsi ini jika kamu belum punya DataFrame dan ingin langsung
    membaca dari file relation.csv hasil pipeline.

    Alur internal:
        1. pd.read_csv(path)  →  DataFrame
        2. build_weighted_coordination_graph(df)  →  nx.Graph
    """
    edges_df = pd.read_csv(relation_csv_path)
    return build_weighted_coordination_graph(
        edges_df,
        source_col=source_col,
        target_col=target_col,
        weight_col=weight_col,
    )


# ===========================================================================
# LANGKAH 3 — Menambahkan informasi akun ke setiap node
# ===========================================================================

def add_account_node_attributes(
    graph: nx.Graph,
    tweets_df: pd.DataFrame,
    account_col: str = "name",
) -> nx.Graph:
    """[LANGKAH 3] Menambahkan atribut akun ke node graf.

    Setelah graf dibangun dari edge, node-node di dalamnya baru berisi
    nama akun (string) tanpa informasi tambahan. Fungsi ini mengisi
    setiap node dengan data dari tabel tweet, seperti:
    - tweet_count    : total tweet yang diunggah akun ini dalam dataset
    - retweet_count  : berapa banyak di antaranya adalah retweet
    - retweet_ratio  : proporsi retweet (0.0 = tidak ada RT, 1.0 = semua RT)
    - last_tweet     : konten tweet terakhir
    - candidate_queries : query kandidat mana saja yang menyertakan akun ini

    Atribut ini dipakai oleh dashboard visualisasi untuk menampilkan
    informasi detail saat pengguna mengklik sebuah node.
    """
    if account_col not in tweets_df.columns:
        raise ValueError(f"Kolom akun tidak ada: {account_col}")

    df = tweets_df.copy()

    # Ambil tweet terakhir tiap akun (sebagai representasi konten terbaru)
    if "date_created" in df.columns:
        df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
        latest_rows = (
            df.sort_values("date_created")
            .drop_duplicates(subset=[account_col], keep="last")
            .set_index(account_col)
        )
    else:
        latest_rows = df.drop_duplicates(subset=[account_col], keep="last").set_index(
            account_col
        )

    # Pasang atribut dari baris tweet terakhir ke setiap node
    optional_latest_attrs = {
        "content": "last_tweet",
        "cleaned_content": "cleaned_tweet",
        "query_candidate": "last_query",
    }
    for column, attr_name in optional_latest_attrs.items():
        if column in latest_rows.columns:
            nx.set_node_attributes(graph, latest_rows[column].to_dict(), attr_name)

    # Hitung statistik agregat per akun (jumlah tweet, rasio RT, dll.)
    aggregations = {}
    if "content" in df.columns:
        aggregations["tweet_count"] = ("content", "size")
    else:
        aggregations["tweet_count"] = (account_col, "size")

    if "is_retweet" in df.columns:
        aggregations["retweet_count"] = ("is_retweet", "sum")

    if "query_candidate" in df.columns:
        aggregations["candidate_queries"] = (
            "query_candidate",
            lambda values: " | ".join(sorted({str(v) for v in values if pd.notna(v)})),
        )

    account_summary = df.groupby(account_col).agg(**aggregations)
    if "retweet_count" in account_summary.columns:
        account_summary["retweet_ratio"] = (
            account_summary["retweet_count"] / account_summary["tweet_count"]
        )

    # Pasang semua statistik ke node graf
    for column in account_summary.columns:
        nx.set_node_attributes(graph, account_summary[column].to_dict(), column)

    return graph


# ===========================================================================
# LANGKAH 4 — Mengukur sentralitas akun (PageRank)
# ===========================================================================

def compute_pagerank(graph: nx.Graph, weight_col: str = "Weight") -> dict[str, float]:
    """[LANGKAH 4] Mengukur sentralitas akun di graf memakai PageRank berbobot.

    PageRank mengukur seberapa 'penting' atau 'sentral' sebuah akun
    dalam jaringan. Akun yang terhubung dengan banyak akun lain yang
    juga punya banyak koneksi akan mendapat skor PageRank yang tinggi.

    Pada dashboard visualisasi, skor PageRank diterjemahkan menjadi
    ukuran lingkaran node — node besar = akun yang lebih sentral di jaringan.

    Skor PageRank disimpan langsung sebagai atribut 'pagerank' di tiap node.
    """
    if graph.number_of_nodes() == 0:
        return {}

    scores = nx.pagerank(graph, weight=weight_col)
    nx.set_node_attributes(graph, scores, "pagerank")
    return dict(scores)


# ===========================================================================
# LANGKAH 5 — Mendeteksi kluster / komunitas akun
# ===========================================================================

def detect_louvain_communities(
    graph: nx.Graph,
    weight_col: str = "Weight",
    resolution: float = DEFAULT_LOUVAIN_RESOLUTION,
    seed: int = DEFAULT_RANDOM_SEED,
) -> dict[str, int]:
    """[LANGKAH 5] Mendeteksi kluster akun memakai algoritma Louvain.

    Louvain adalah algoritma deteksi komunitas yang bekerja dengan cara
    memaksimalkan 'modularitas' — yaitu mencari kelompok node yang
    saling terhubung lebih padat dibandingkan dengan koneksi ke luar kelompok.

    Parameter `resolution` mengontrol granularitas kluster:
    - Nilai lebih tinggi → kluster lebih kecil dan lebih banyak.
    - Nilai lebih rendah → kluster lebih besar dan lebih sedikit.

    Hasil: setiap node mendapat atribut 'community' berupa ID kluster (integer).
    Node-node dengan ID kluster yang sama akan ditampilkan dengan warna yang
    sama di dashboard visualisasi.
    """
    if graph.number_of_nodes() == 0:
        return {}

    communities = nx.community.louvain_communities(
        graph,
        weight=weight_col,
        resolution=resolution,
        seed=seed,
    )

    # Ubah format dari list-of-sets menjadi dict {node: cluster_id}
    community_by_node = {}
    for cluster_id, nodes in enumerate(communities):
        for node in nodes:
            community_by_node[str(node)] = cluster_id

    # Simpan ID kluster sebagai atribut di setiap node
    nx.set_node_attributes(graph, community_by_node, "community")
    return community_by_node


# ===========================================================================
# LANGKAH 6 — Memberi skor dan label interpretasi tiap kluster
# ===========================================================================

def cluster_density_score(size: int, density: float) -> float:
    """[LANGKAH 6a] Menghitung skor koordinasi satu kluster.

    Rumus:
        Coordination_Score = density × log₂(size + 1)

    Mengapa dikali log₂(size + 1)?
    - Density saja tidak cukup: kluster 3 akun dengan density 1.0 sangat berbeda
      bobotnya dari kluster 30 akun dengan density 1.0.
    - log₂(size + 1) memberi 'penghargaan' pada kluster yang besar,
      tapi dengan kenaikan yang melambat (logaritmik) agar kluster besar
      tidak mendominasi secara berlebihan.

    Contoh:
        Kluster 3 akun, density 1.0  → skor = 1.0 × log₂(4) = 2.00
        Kluster 13 akun, density 1.0 → skor = 1.0 × log₂(14) ≈ 3.81
        Kluster 41 akun, density 0.86 → skor = 0.86 × log₂(42) ≈ 4.62
    """
    return float(density) * float(np.log2(int(size) + 1))


def cluster_status(
    size: int,
    density: float,
    total_pair_matches: int,
    min_size: int = 5,
    min_matches: int = 5,
) -> tuple[float, str]:
    """[LANGKAH 6b] Memberi label interpretasi awal terhadap kluster koordinasi.

    Label didasarkan pada skor koordinasi (Langkah 6a) dan ukuran minimum:

    - Kluster dengan < 5 akun ATAU < 5 bukti pasangan:
        → "Indikasi lemah (kluster kecil/minim bukti)"
          (terlalu kecil untuk ditafsirkan dengan percaya diri)

    - Kluster dengan skor ≥ 1.5:
        → "Sangat mencurigakan"

    - Kluster dengan skor ≥ 0.8:
        → "Perlu investigasi"

    - Selain itu:
        → "Rendah / cenderung organik"

    Label ini BUKAN vonis — hanya indikasi awal berbasis struktur graf.
    """
    score = cluster_density_score(size=size, density=density)

    if size < min_size or total_pair_matches < min_matches:
        return score, "Indikasi lemah (kluster kecil/minim bukti)"
    if score >= 1.5:
        return score, "Sangat mencurigakan"
    if score >= 0.8:
        return score, "Perlu investigasi"
    return score, "Rendah / cenderung organik"


def _dominant_nonempty(values: list[object]) -> str:
    """Helper: kembalikan nilai yang paling sering muncul (non-kosong)."""
    cleaned = [str(value) for value in values if pd.notna(value) and str(value).strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def calculate_cluster_density_report(
    graph: nx.Graph,
    cluster_labels: dict[int, str] | None = None,
    min_size: int = 5,
    min_matches: int = 5,
) -> pd.DataFrame:
    """[LANGKAH 6c] Menghasilkan laporan ringkasan semua kluster dalam graf.

    Fungsi ini membutuhkan graf yang sudah memiliki atribut 'community'
    di setiap node (hasil dari detect_louvain_communities di Langkah 5).

    Untuk setiap kluster, fungsi ini menghitung:
    - Size_Jumlah_Akun      : berapa akun dalam kluster
    - Density               : proporsi edge yang ada vs. kemungkinan maksimum
                              (1.0 = semua akun saling terhubung satu sama lain)
    - Total_Evidence_Matches: total pasangan tweet yang menjadi bukti
    - Avg_Weight            : rata-rata bobot edge dalam kluster
    - Retweet_Edges         : jumlah edge berbasis shared-retweet
    - Semantic_Edges        : jumlah edge berbasis kemiripan narasi non-RT
    - Coordination_Score    : skor akhir (density × log₂(size+1))
    - Status                : label interpretasi ("Sangat mencurigakan", dll.)
    - Topik_Utama           : label topik yang bisa diisi manual

    Output disimpan ke cluster_density_report.csv dan ditampilkan di dashboard.
    """
    cluster_labels = cluster_labels or {}

    # Ambil mapping node → ID kluster dari atribut graf
    node_communities = nx.get_node_attributes(graph, "community")
    if not node_communities:
        raise ValueError(
            "Graf belum punya atribut 'community'. Jalankan detect_louvain_communities dulu."
        )

    # Kelompokkan node berdasarkan ID kluster
    clusters: dict[int, list[str]] = {}
    for node, cluster_id in node_communities.items():
        clusters.setdefault(int(cluster_id), []).append(str(node))

    rows = []
    for cluster_id, nodes in clusters.items():
        # Buat subgraf hanya dari node-node dalam kluster ini
        subgraph = graph.subgraph(nodes)

        # Kluster dengan satu node saja dilewati (tidak relevan)
        if subgraph.number_of_nodes() <= 1:
            continue

        size = subgraph.number_of_nodes()
        density = nx.density(subgraph)

        # Kumpulkan data dari semua edge dalam subgraf
        edge_payloads = [data for _, _, data in subgraph.edges(data=True)]
        total_pair_matches = sum(
            _safe_int(data.get("Edge_Count", 1)) for data in edge_payloads
        )
        edge_types = [str(data.get("Edge_Types", "")) for data in edge_payloads]
        weights = [_safe_float(data.get("Weight", 0.0)) for data in edge_payloads]

        # Hitung skor dan tentukan label status kluster
        score, status = cluster_status(
            size=size,
            density=density,
            total_pair_matches=total_pair_matches,
            min_size=min_size,
            min_matches=min_matches,
        )

        rows.append(
            {
                "Cluster_ID": cluster_id,
                "Size_Jumlah_Akun": size,
                "Density": round(float(density), 5),
                "Edge_Count": subgraph.number_of_edges(),
                "Total_Evidence_Matches": total_pair_matches,
                "Avg_Weight": round(float(np.mean(weights)), 5) if weights else 0.0,
                "Retweet_Edges": sum("retweet" in value for value in edge_types),
                "Semantic_Edges": sum("semantic" in value for value in edge_types),
                "Dominant_RT_Source": _dominant_nonempty(
                    [data.get("Dominant_RT_Source") for data in edge_payloads]
                ),
                "Coordination_Score": round(float(score), 5),
                "Status": status,
                "Topik_Utama": cluster_labels.get(cluster_id, "Topik tidak terdefinisi"),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Cluster_ID",
                "Size_Jumlah_Akun",
                "Density",
                "Edge_Count",
                "Total_Evidence_Matches",
                "Avg_Weight",
                "Retweet_Edges",
                "Semantic_Edges",
                "Dominant_RT_Source",
                "Coordination_Score",
                "Status",
                "Topik_Utama",
            ]
        )

    # Urutkan dari kluster paling kuat ke paling lemah
    report_df = pd.DataFrame(rows)
    status_rank = {
        "Sangat mencurigakan": 3,
        "Perlu investigasi": 2,
        "Indikasi lemah (kluster kecil/minim bukti)": 1,
        "Rendah / cenderung organik": 0,
    }
    return (
        report_df.assign(_Status_Rank=report_df["Status"].map(status_rank).fillna(0))
        .sort_values(
            by=["_Status_Rank", "Coordination_Score", "Total_Evidence_Matches"],
            ascending=[False, False, False],
        )
        .drop(columns=["_Status_Rank"])
        .reset_index(drop=True)
    )
