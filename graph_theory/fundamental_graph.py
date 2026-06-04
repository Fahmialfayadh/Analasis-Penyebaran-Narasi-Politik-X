"""Fungsi fundamental teori graf yang dipakai pada proyek.


Definisi model:
- Node: akun X/Twitter.
- Edge: hubungan koordinasi antara dua akun.
- Weight: kekuatan hubungan, dihitung dari kemiripan teks dan kedekatan waktu.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Hashable

import networkx as nx
import numpy as np
import pandas as pd


DEFAULT_ALPHA = 0.5
DEFAULT_LAMBDA = 0.001155
DEFAULT_LOUVAIN_RESOLUTION = 2.0
DEFAULT_RANDOM_SEED = 42


def pair_key(account_a: Hashable, account_b: Hashable) -> tuple[str, str]:
    """Mengunci pasangan akun agar edge A-B dan B-A dianggap edge yang sama."""
    return tuple(sorted((str(account_a), str(account_b))))


def time_decay_score(
    delta_t_seconds: float,
    lambda_value: float = DEFAULT_LAMBDA,
) -> float:
    """Mengubah selisih waktu menjadi skor kedekatan waktu.

    Rumus:
        s_time = exp(-lambda * delta_t)

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
    """Menghitung bobot edge koordinasi.

    Rumus:
        w_ij = alpha * s_text + (1 - alpha) * s_time

    Keterangan:
    - s_text: kemiripan isi tweet, cosine similarity embedding.
    - s_time: kedekatan waktu posting.
    - alpha: porsi pengaruh kemiripan teks terhadap bobot akhir.

    Untuk shared-retweet, pipeline memakai s_text = 1.0 karena kedua akun
    membagikan sumber retweet yang sama.
    """
    text_score = float(s_text)
    alpha_value = float(alpha)
    s_time = time_decay_score(delta_t_seconds, lambda_value=lambda_value)
    weight = (alpha_value * text_score) + ((1.0 - alpha_value) * s_time)
    return float(weight), float(s_time)


def _safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def _safe_int(value: object, default: int = 1) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return int(parsed)


def build_weighted_coordination_graph(
    edges_df: pd.DataFrame,
    source_col: str = "Source",
    target_col: str = "Target",
    weight_col: str = "Weight",
) -> nx.Graph:
    """Membentuk graf tak berarah berbobot dari tabel edge.

    Input utama fungsi ini adalah `relation.csv`, yaitu daftar pasangan akun
    yang sudah lolos filter koordinasi. Setiap baris menjadi satu edge:

        G = (V, E)
        V = akun
        E = pasangan akun yang punya bukti koordinasi
        Weight = bobot kekuatan relasi
    """
    required_columns = {source_col, target_col, weight_col}
    missing = required_columns.difference(edges_df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ada: {sorted(missing)}")

    graph = nx.Graph()
    for _, row in edges_df.iterrows():
        source = str(row[source_col])
        target = str(row[target_col])
        if source == target:
            continue

        edge_data = row.to_dict()
        edge_data[weight_col] = _safe_float(row[weight_col])
        if "Edge_Count" in edge_data:
            edge_data["Edge_Count"] = _safe_int(edge_data["Edge_Count"])

        graph.add_edge(source, target, **edge_data)

    return graph


def build_graph_from_relation_csv(
    relation_csv_path: str | Path,
    source_col: str = "Source",
    target_col: str = "Target",
    weight_col: str = "Weight",
) -> nx.Graph:
    """Membaca `relation.csv` lalu membentuk graf koordinasi berbobot."""
    edges_df = pd.read_csv(relation_csv_path)
    return build_weighted_coordination_graph(
        edges_df,
        source_col=source_col,
        target_col=target_col,
        weight_col=weight_col,
    )


def add_account_node_attributes(
    graph: nx.Graph,
    tweets_df: pd.DataFrame,
    account_col: str = "name",
) -> nx.Graph:
    """Menambahkan atribut akun ke node, misalnya jumlah tweet dan rasio retweet."""
    if account_col not in tweets_df.columns:
        raise ValueError(f"Kolom akun tidak ada: {account_col}")

    df = tweets_df.copy()

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

    optional_latest_attrs = {
        "content": "last_tweet",
        "cleaned_content": "cleaned_tweet",
        "query_candidate": "last_query",
    }
    for column, attr_name in optional_latest_attrs.items():
        if column in latest_rows.columns:
            nx.set_node_attributes(graph, latest_rows[column].to_dict(), attr_name)

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

    for column in account_summary.columns:
        nx.set_node_attributes(graph, account_summary[column].to_dict(), column)

    return graph


def compute_pagerank(graph: nx.Graph, weight_col: str = "Weight") -> dict[str, float]:
    """Mengukur sentralitas akun di graf memakai PageRank berbobot."""
    if graph.number_of_nodes() == 0:
        return {}

    scores = nx.pagerank(graph, weight=weight_col)
    nx.set_node_attributes(graph, scores, "pagerank")
    return dict(scores)


def detect_louvain_communities(
    graph: nx.Graph,
    weight_col: str = "Weight",
    resolution: float = DEFAULT_LOUVAIN_RESOLUTION,
    seed: int = DEFAULT_RANDOM_SEED,
) -> dict[str, int]:
    """Mendeteksi cluster/komunitas akun memakai algoritma Louvain."""
    if graph.number_of_nodes() == 0:
        return {}

    communities = nx.community.louvain_communities(
        graph,
        weight=weight_col,
        resolution=resolution,
        seed=seed,
    )

    community_by_node = {}
    for cluster_id, nodes in enumerate(communities):
        for node in nodes:
            community_by_node[str(node)] = cluster_id

    nx.set_node_attributes(graph, community_by_node, "community")
    return community_by_node


def cluster_density_score(size: int, density: float) -> float:
    """Skor sederhana untuk membaca seberapa padat relasi dalam satu cluster."""
    return float(density) * float(np.log2(int(size) + 1))


def cluster_status(
    size: int,
    density: float,
    total_pair_matches: int,
    min_size: int = 5,
    min_matches: int = 5,
) -> tuple[float, str]:
    """Memberi label interpretasi awal terhadap cluster koordinasi."""
    score = cluster_density_score(size=size, density=density)

    if size < min_size or total_pair_matches < min_matches:
        return score, "Indikasi lemah (kluster kecil/minim bukti)"
    if score >= 1.5:
        return score, "Sangat mencurigakan"
    if score >= 0.8:
        return score, "Perlu investigasi"
    return score, "Rendah / cenderung organik"


def _dominant_nonempty(values: list[object]) -> str:
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
    """Menghitung ringkasan cluster dari graf yang sudah punya atribut community."""
    cluster_labels = cluster_labels or {}
    node_communities = nx.get_node_attributes(graph, "community")
    if not node_communities:
        raise ValueError(
            "Graf belum punya atribut 'community'. Jalankan detect_louvain_communities dulu."
        )

    clusters: dict[int, list[str]] = {}
    for node, cluster_id in node_communities.items():
        clusters.setdefault(int(cluster_id), []).append(str(node))

    rows = []
    for cluster_id, nodes in clusters.items():
        subgraph = graph.subgraph(nodes)
        if subgraph.number_of_nodes() <= 1:
            continue

        size = subgraph.number_of_nodes()
        density = nx.density(subgraph)
        edge_payloads = [data for _, _, data in subgraph.edges(data=True)]
        total_pair_matches = sum(
            _safe_int(data.get("Edge_Count", 1)) for data in edge_payloads
        )
        edge_types = [str(data.get("Edge_Types", "")) for data in edge_payloads]
        weights = [_safe_float(data.get("Weight", 0.0)) for data in edge_payloads]
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
