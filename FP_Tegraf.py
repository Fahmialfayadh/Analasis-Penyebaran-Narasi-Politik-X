import glob
import json
import os
import re
from collections import Counter

import networkx as nx
import numpy as np
import pandas as pd
from pyvis.network import Network
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer

# Configuration
main_folder_path = "/data/DE-sample-X-capres2024/DE-sample-X-capres2024"


# =====================================================================
# UTILITAS DATA
# =====================================================================
def parse_json_field(value):
    """Mengubah field JSON string dari dataset menjadi dictionary Python."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def get_candidate_from_filename(path):
    """Mengambil label query kandidat dari nama file data-twit-*.json."""
    filename = os.path.basename(path)
    match = re.search(r"data-twit-(.+)\.json$", filename)
    return match.group(1).lower() if match else "unknown"


def normalize_spaces(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def short_text(text, limit=180):
    text = normalize_spaces(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# [REFERENSI PPT: SLIDE 3 - PERSIAPAN DATA]
# cleaned_content: membersihkan spasi, RT, URL untuk pengukuran kesamaan semantik.
def clean_text_for_embedding(text):
    """Membersihkan teks untuk embedding tanpa menghapus substansi narasi."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"^rt\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[RE\s+[^\]]+\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# [REFERENSI PPT: SLIDE 3 - PERSIAPAN DATA]
# topic_content: pembersihan lebih ketat untuk ekstraksi kata kunci/topik TF-IDF.
def clean_text_for_topic(text):
    """Versi lebih bersih untuk TF-IDF agar keyword tidak didominasi URL/mention."""
    text = clean_text_for_embedding(text).lower()
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#", " ", text)
    text = re.sub(r"[^0-9a-zA-Z_]+", " ", text)
    text = re.sub(r"\b\w{1,2}\b", " ", text)
    return normalize_spaces(text)


def clean_keyword(word):
    if not isinstance(word, str):
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", word.lower())
    if len(cleaned) <= 2:
        return None
    if cleaned.isdigit():
        return None
    if re.match(r"^[a-z0-9]{16,}$", cleaned) and not re.search(
        r"anies|prabowo|ganjar|mahfud|gibran|muhaimin|amin", cleaned
    ):
        return None
    return cleaned


# =====================================================================
# MODUL 1: DATA INGESTION, CLEANING, DAN AUDIT
# =====================================================================
# [REFERENSI PPT: SLIDE 1 - SUMBER DATA]
# Fungsi ini memuat sample data tweet yang difilter khusus keyword ganjar, prabowo, anies.
def load_and_combine_json(main_folder, file_pattern="data-twit-*.json", max_rows=None):
    """Membaca file JSON paslon, menjaga metadata penting, lalu menggabungkannya."""
    print("Membaca data tweet mentah...")

    search_path = os.path.join(main_folder, file_pattern)
    file_paths = sorted(glob.glob(search_path))

    if not file_paths:
        raise FileNotFoundError(
            f"Tidak ditemukan file dengan pola '{search_path}' di {main_folder}."
        )

    important_columns = [
        "name",
        "content",
        "date_created",
        "id",
        "author",
        "contentJson",
        "num_retweets",
        "in_reply_to_screen_name",
        "type",
        "lang",
    ]

    all_dfs = []
    for path in file_paths:
        print(f"-> Memuat {path}")
        temp_df = pd.read_json(path)
        for col in important_columns:
            if col not in temp_df.columns:
                temp_df[col] = np.nan
        temp_df = temp_df[important_columns].copy()
        temp_df["query_candidate"] = get_candidate_from_filename(path)
        temp_df["source_file"] = os.path.basename(path)
        all_dfs.append(temp_df)

    df = pd.concat(all_dfs, ignore_index=True)
    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    df = df.sort_values("date_created").reset_index(drop=True)

    if max_rows is not None:
        df = df.head(max_rows).copy()
        print(f"Data dibatasi ke {len(df)} baris pertama secara kronologis.")

    print(f"Total data sukses dimuat: {len(df)} baris.\n")
    return df


# [REFERENSI PPT: SLIDE 3 - PERSIAPAN DATA]
# Tahapan penyiapan teks dan metadata (cleaned_content & topic_content) mengurangi bias platform.
def preprocess_tweets(df):
    """Membersihkan teks dan mengekstrak metadata RT yang mengubah makna analisis."""
    print("Melakukan preprocessing teks dan ekstraksi metadata RT...")
    df = df.copy()

    parsed_content = df["contentJson"].apply(parse_json_field)
    parsed_author = df["author"].apply(parse_json_field)

    rt_sources = []
    rt_source_ids = []
    author_followers = []
    author_friends = []
    author_statuses = []
    author_created_at = []

    for idx, content_json in parsed_content.items():
        rt_status = content_json.get("rt_status", {})
        if isinstance(rt_status, dict):
            rt_sources.append(rt_status.get("screen_name"))
            rt_source_ids.append(rt_status.get("id"))
        else:
            rt_sources.append(None)
            rt_source_ids.append(None)

        author_json = parsed_author.loc[idx]
        if not author_json:
            author_json = content_json.get("user", {})
        author_followers.append(author_json.get("flw_cnt"))
        author_friends.append(author_json.get("frn_cnt"))
        author_statuses.append(author_json.get("sts_cnt"))
        author_created_at.append(author_json.get("created_at"))

    df["rt_source"] = rt_sources
    df["rt_source_id"] = rt_source_ids

    # Fallback untuk dataset yang menyimpan asal RT sebagai teks "[RE username]".
    fallback_rt_source = df["content"].fillna("").str.extract(
        r"\[RE\s+([^\]]+)\]", flags=re.IGNORECASE
    )[0]
    df["rt_source"] = df["rt_source"].fillna(fallback_rt_source)

    df["is_retweet"] = (
        df["content"].fillna("").str.match(r"^RT\b", case=False)
        | df["rt_source"].notna()
        | df["rt_source_id"].notna()
    )
    df["is_reply_or_mention"] = (
        df["in_reply_to_screen_name"].fillna("").astype(str).str.strip().ne("")
        | df["content"].fillna("").str.match(r"^@\w+")
    )

    df["cleaned_content"] = df["content"].apply(clean_text_for_embedding)
    df["topic_content"] = df["content"].apply(clean_text_for_topic)
    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    df["author_followers"] = pd.to_numeric(author_followers, errors="coerce")
    df["author_friends"] = pd.to_numeric(author_friends, errors="coerce")
    df["author_statuses"] = pd.to_numeric(author_statuses, errors="coerce")
    df["author_created_at"] = pd.to_datetime(author_created_at, errors="coerce")

    return df


# [REFERENSI PPT: SLIDE 2 - RINGKASAN DATASET]
# Menghitung statistik ringkasan: Total tweet, Akun unik, Rasio RT, dll.
def audit_dataset(df, output_filename=None):
    """Mencetak dan menyimpan audit singkat agar batas klaim analisis jelas."""
    print("\n=== AUDIT DATA ===")
    total_rows = len(df)
    unique_accounts = df["name"].nunique()
    min_date = df["date_created"].min()
    max_date = df["date_created"].max()
    retweet_count = int(df["is_retweet"].sum())
    reply_count = int(df["is_reply_or_mention"].sum())
    empty_cleaned = int(df["cleaned_content"].fillna("").str.strip().eq("").sum())

    metrics = [
        ("total_rows", total_rows),
        ("unique_accounts", unique_accounts),
        ("date_min", min_date),
        ("date_max", max_date),
        ("retweet_rows", retweet_count),
        ("retweet_ratio", round(retweet_count / total_rows, 4) if total_rows else 0),
        ("reply_or_mention_rows", reply_count),
        ("empty_cleaned_content", empty_cleaned),
    ]

    for key, value in metrics:
        print(f"{key}: {value}")

    print("\nJumlah data per query kandidat:")
    print(df["query_candidate"].value_counts().to_string())

    top_rt_sources = df["rt_source"].dropna().value_counts().head(10)
    if not top_rt_sources.empty:
        print("\nTop 10 sumber RT:")
        print(top_rt_sources.to_string())

    if output_filename:
        audit_rows = [{"Metric": key, "Value": value} for key, value in metrics]
        audit_df = pd.DataFrame(audit_rows)
        audit_df.to_csv(output_filename, index=False)
        print(f"[SUKSES] Audit data disimpan di: {output_filename}")


# =====================================================================
# MODUL 2: AI SEMANTIC EMBEDDING
# =====================================================================
# [REFERENSI PPT: SLIDE 4 - PENGUKURAN KEMIRIPAN & WAKTU]
# Proses Embed: Mengubah teks menjadi representasi vektor numerik.
def generate_embeddings(sentences, model_name):
    """Mengubah teks menjadi vektor embedding menggunakan pre-trained model AI."""
    print(f"Memuat Model AI: {model_name}")
    model = SentenceTransformer(model_name)

    print("Mengonversi teks ke vektor semantik (Embedding)...")
    embeddings = model.encode(
        sentences, convert_to_tensor=True, show_progress_bar=True
    )
    return embeddings


# =====================================================================
# MODUL 3: JARINGAN KOORDINASI & FILTER (CORE LOGIC)
# =====================================================================
def pair_key(account_a, account_b):
    return tuple(sorted([str(account_a), str(account_b)]))


# [REFERENSI PPT: SLIDE 4 - PENGUKURAN KEMIRIPAN & WAKTU]
# Implementasi formula s_time = exp(-0.001155 * delta_t) dan gabungan (weight = 0.5 s_text + 0.5 s_time)
def calculate_edge_weight(s_text, delta_t, config):
    s_time = np.exp(-config["LAMBDA"] * delta_t)
    weight = (config["ALPHA"] * s_text) + ((1 - config["ALPHA"]) * s_time)
    return weight, s_time


# [REFERENSI PPT: SLIDE 5 - KRITERIA PEMBENTUKAN EDGE]
# Menerapkan 3 filter ketat: Unggahan Mandiri (Non-RT), Kemiripan Makna (s_text >= 0.65), Keserempakan Waktu (<= 30 menit).
def extract_coordination_edges(df, embeddings, config):
    """Mengekstrak edge koordinasi berbasis semantic match dan shared-retweet."""
    print("\nMengekstrak jaringan koordinasi...")
    n = len(df)
    edges_list = []
    cosine_scores = util.cos_sim(embeddings, embeddings)

    include_rt_in_semantic = config.get("INCLUDE_RETWEETS_IN_SEMANTIC", False)
    text_threshold = config["THRESHOLD_TEXT"]
    text_time_threshold = config["THRESHOLD_TIME"]
    rt_time_threshold = config.get("THRESHOLD_RETWEET_TIME", text_time_threshold)

    for i in range(n):
        row_i = df.iloc[i]
        for j in range(i + 1, n):
            row_j = df.iloc[j]
            if row_i["name"] == row_j["name"]:
                continue

            if pd.isna(row_i["date_created"]) or pd.isna(row_j["date_created"]):
                continue

            delta_t = abs((row_i["date_created"] - row_j["date_created"]).total_seconds())
            source, target = pair_key(row_i["name"], row_j["name"])

            rt_id_i = row_i.get("rt_source_id")
            rt_id_j = row_j.get("rt_source_id")
            rt_source_i = row_i.get("rt_source")
            rt_source_j = row_j.get("rt_source")
            same_rt_id = (
                bool(row_i.get("is_retweet"))
                and bool(row_j.get("is_retweet"))
                and pd.notna(rt_id_i)
                and pd.notna(rt_id_j)
                and rt_id_i == rt_id_j
            )
            same_rt_source_fallback = (
                bool(row_i.get("is_retweet"))
                and bool(row_j.get("is_retweet"))
                and (pd.isna(rt_id_i) or pd.isna(rt_id_j))
                and pd.notna(rt_source_i)
                and pd.notna(rt_source_j)
                and rt_source_i == rt_source_j
            )

            if (same_rt_id or same_rt_source_fallback) and delta_t <= rt_time_threshold:
                weight, s_time = calculate_edge_weight(1.0, delta_t, config)
                edges_list.append(
                    {
                        "Source": source,
                        "Target": target,
                        "Weight": weight,
                        "s_text": 1.0,
                        "s_time": s_time,
                        "w_ij": weight,
                        "delta_t_seconds": delta_t,
                        "edge_type": "retweet",
                        "rt_source": row_i.get("rt_source"),
                        "rt_source_id": row_i.get("rt_source_id"),
                        "tweet_i": short_text(row_i.get("cleaned_content", "")),
                        "tweet_j": short_text(row_j.get("cleaned_content", "")),
                        "query_i": row_i.get("query_candidate", "unknown"),
                        "query_j": row_j.get("query_candidate", "unknown"),
                    }
                )
                continue

            if not include_rt_in_semantic and (
                bool(row_i.get("is_retweet")) or bool(row_j.get("is_retweet"))
            ):
                continue

            if delta_t > text_time_threshold:
                continue

            s_text = cosine_scores[i][j].item()
            if s_text < text_threshold:
                continue

            weight, s_time = calculate_edge_weight(s_text, delta_t, config)
            edges_list.append(
                {
                    "Source": source,
                    "Target": target,
                    "Weight": weight,
                    "s_text": s_text,
                    "s_time": s_time,
                    "w_ij": weight,
                    "delta_t_seconds": delta_t,
                    "edge_type": "semantic",
                    "rt_source": "",
                    "rt_source_id": "",
                    "tweet_i": short_text(row_i.get("cleaned_content", "")),
                    "tweet_j": short_text(row_j.get("cleaned_content", "")),
                    "query_i": row_i.get("query_candidate", "unknown"),
                    "query_j": row_j.get("query_candidate", "unknown"),
                }
            )

    return edges_list


# =====================================================================
# MODUL 4: AGREGASI JARINGAN & OUTPUT CSV
# =====================================================================
def most_common_nonempty(values):
    values = [str(v) for v in values if pd.notna(v) and str(v).strip()]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def join_unique(values, limit=6):
    cleaned = []
    for value in values:
        if pd.isna(value):
            continue
        value = str(value).strip()
        if value and value not in cleaned:
            cleaned.append(value)
        if len(cleaned) >= limit:
            break
    return " | ".join(cleaned)


# [REFERENSI PPT: SLIDE 6 - RINGKASAN HUBUNGAN YANG TERDETEKSI]
# Menggabungkan bukti mentah menjadi aggregated edges dan mendeteksi proporsi Semantic, Retweet, dan Campuran.
def export_network_to_csv(edges_list, output_filename="political_edges.csv"):
    """Mengagregasi edge ganda sambil menyimpan bukti relasi koordinasi."""
    if not edges_list:
        print(
            "\n[Hasil] Tidak ditemukan pola koordinasi dengan konfigurasi threshold saat ini."
        )
        return None

    edges_df = pd.DataFrame(edges_list)
    evidence_filename = output_filename.replace(".csv", "_evidence.csv")
    edges_df.to_csv(evidence_filename, index=False)

    final_edges = (
        edges_df.groupby(["Source", "Target"])
        .agg(
            Weight=("Weight", "mean"),
            Max_Weight=("Weight", "max"),
            Edge_Count=("Weight", "size"),
            Avg_Text_Similarity=("s_text", "mean"),
            Avg_Time_Score=("s_time", "mean"),
            Min_Time_Delta_Seconds=("delta_t_seconds", "min"),
            Edge_Types=("edge_type", join_unique),
            Dominant_RT_Source=("rt_source", most_common_nonempty),
            Query_Context=("query_i", lambda values: join_unique(values, limit=4)),
            Example_Tweet_1=("tweet_i", lambda values: join_unique(values, limit=2)),
            Example_Tweet_2=("tweet_j", lambda values: join_unique(values, limit=2)),
        )
        .reset_index()
    )

    final_edges = final_edges.sort_values(
        by=["Edge_Count", "Weight"], ascending=[False, False]
    ).reset_index(drop=True)

    final_edges.to_csv(output_filename, index=False)
    print(
        f"\n[Sukses] Berhasil mengekstrak {len(final_edges)} edges koordinasi teragregasi."
    )
    print(f"File edge utama disimpan dengan nama: '{output_filename}'")
    print(f"File bukti edge detail disimpan dengan nama: '{evidence_filename}'")
    print(final_edges.head())
    return final_edges


# =====================================================================
# MODUL 5: ANALISIS TEORI GRAF (NETWORKX)
# =====================================================================
# [REFERENSI PPT: SLIDE 7 - DETEKSI KOMUNITAS (CLUSTERING)]
# Menjalankan algoritma Louvain untuk menemukan kluster dari graf yang terbentuk.
def analyze_coordination_graph(csv_path, df, config=None):
    print("Memuat file jaringan koordinasi...")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"File tidak ditemukan di: {csv_path}. Jalankan skrip AI terlebih dahulu."
        )

    edges_df = pd.read_csv(csv_path)

    print("Membangun struktur matematika graf...")
    G = nx.from_pandas_edgelist(
        edges_df,
        source="Source",
        target="Target",
        edge_attr=True,
    )

    print("Memetakan atribut akun ke setiap node...")
    latest_tweets = (
        df.sort_values("date_created")
        .drop_duplicates(subset=["name"], keep="last")
        .set_index("name")
    )
    nx.set_node_attributes(G, latest_tweets["content"].to_dict(), "last_tweet")
    nx.set_node_attributes(G, latest_tweets["cleaned_content"].to_dict(), "cleaned_tweet")
    nx.set_node_attributes(G, latest_tweets["query_candidate"].to_dict(), "last_query")

    account_summary = df.groupby("name").agg(
        tweet_count=("content", "size"),
        retweet_count=("is_retweet", "sum"),
        candidate_queries=("query_candidate", lambda x: " | ".join(sorted(set(x)))),
    )
    account_summary["retweet_ratio"] = (
        account_summary["retweet_count"] / account_summary["tweet_count"]
    )
    for attr in ["tweet_count", "retweet_count", "candidate_queries", "retweet_ratio"]:
        nx.set_node_attributes(G, account_summary[attr].to_dict(), attr)

    print("Menghitung metrik PageRank sebagai akun paling sentral di graf...")
    pagerank_scores = nx.pagerank(G, weight="Weight")
    nx.set_node_attributes(G, pagerank_scores, "pagerank")

    print("Menjalankan algoritma deteksi komunitas (Louvain)...")
    resolution = config.get("LOUVAIN_RESOLUTION", 2.0) if config else 2.0
    seed = config.get("RANDOM_SEED", 42) if config else 42
    communities = nx.community.louvain_communities(
        G, weight="Weight", resolution=resolution, seed=seed
    )

    community_dict = {}
    for cluster_id, group_nodes in enumerate(communities):
        for node in group_nodes:
            community_dict[node] = cluster_id

    nx.set_node_attributes(G, community_dict, "community")
    print(f"Sukses mengidentifikasi {len(communities)} kelompok koordinasi politik.\n")

    return G


# =====================================================================
# Pelabelan topik
# =====================================================================
def extract_cluster_topics(df, G, top_n=3):
    print("Mengekstrak kata kunci utama untuk setiap kluster...")
    custom_stopwords = [
        "rt", "re", "retweet", "twit", "tweet", "https", "http", "www", "com", "co",
        "amp", "tco", "pic", "twitter", "xcom",
        "yang", "dan", "itu", "ini", "untuk", "dengan", "ada", "seperti", "dari",
        "akan", "bisa", "atau", "pada", "juga", "sudah", "telah", "karena",
        "saya", "kami", "mereka", "dia", "adalah", "bahwa", "tidak", "bukan",
        "tapi", "namun", "yg", "utk", "jd", "bgt", "dgn", "aja", "kalo", "kalau",
        "ga", "gak", "gue", "gw", "lu", "lo", "nya", "nih", "sih", "dong",
        "pak", "bapak", "mas", "bang", "bung", "ibu", "dok", "prof",
        "and", "the", "to", "of", "in", "for", "is", "are", "you", "your",
    ]
    node_communities = nx.get_node_attributes(G, "community")

    cluster_documents = {}
    for node_id, community_id in node_communities.items():
        user_tweets = df[df["name"] == node_id]["topic_content"].dropna().values
        if len(user_tweets) > 0:
            text_combined = " ".join(user_tweets)
            cluster_documents.setdefault(community_id, []).append(text_combined)

    cluster_ids = sorted(cluster_documents.keys())
    cluster_corpus = [" ".join(cluster_documents[cid]) for cid in cluster_ids]

    if not cluster_corpus:
        print("[Peringatan] Tidak ada teks yang dapat diekstrak untuk TF-IDF.")
        return {}

    vectorizer = TfidfVectorizer(
        max_df=0.85,
        min_df=1,
        stop_words=custom_stopwords,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9_]{2,}\b",
    )
    tfidf_matrix = vectorizer.fit_transform(cluster_corpus)
    feature_names = np.array(vectorizer.get_feature_names_out())

    cluster_labels = {}
    for i, cid in enumerate(cluster_ids):
        row = tfidf_matrix.getrow(i).toarray()[0]
        top_indices = np.argsort(row)[::-1]
        top_keywords = []
        for idx in top_indices:
            keyword = clean_keyword(feature_names[idx])
            if keyword and keyword not in custom_stopwords and keyword not in top_keywords:
                top_keywords.append(keyword)
            if len(top_keywords) >= top_n:
                break

        cluster_labels[cid] = ", ".join(top_keywords) if top_keywords else "N/A"
        print(f"-> Kluster {cid} membahas seputar: [{cluster_labels[cid]}]")

    return cluster_labels


# =====================================================================
# MODUL 6: VISUALISASI JARINGAN & EKSPOR HTML (PYVIS)
# =====================================================================
def generate_and_save_html(G, cluster_labels, output_html_path):
    print("Mempersiapkan mesin visualisasi jaringan...")

    net = Network(
        notebook=False,
        bgcolor="#1a1a1a",
        font_color="white",
        height="750px",
        width="100%",
    )

    net.from_nx(G)

    print("Menyesuaikan ukuran lingkaran dan warna berdasarkan metrik...")
    for node in net.nodes:
        pagerank = node.get("pagerank", 0)
        node["size"] = pagerank * 1500 + 10
        node["group"] = node.get("community", 0)

        cid = node.get("community", 0)
        topik_kluster = cluster_labels.get(cid, "Tidak ada data")
        if "color" in node:
            del node["color"]

        tweet_teks = G.nodes[node["id"]].get("last_tweet", "Teks tweet tidak tersedia")
        if len(str(tweet_teks)) > 80:
            tweet_teks = str(tweet_teks)[:80] + "..."

        node["title"] = (
            f"Akun: {node['id']}<br>"
            f"<b>Kluster: {cid}</b><br>"
            f"<b>Topik Utama (TF-IDF): [{topik_kluster}]</b><br>"
            f"PageRank: {pagerank:.5f}<br>"
            f"Rasio RT akun: {G.nodes[node['id']].get('retweet_ratio', 0):.2f}<br>"
            f"Tweet Terakhir: '{tweet_teks}'"
        )

    for edge in net.edges:
        data = G.get_edge_data(edge["from"], edge["to"], default={})
        edge["title"] = (
            f"Jenis edge: {data.get('Edge_Types', 'N/A')}<br>"
            f"Jumlah bukti: {data.get('Edge_Count', 1)}<br>"
            f"Min jeda waktu: {data.get('Min_Time_Delta_Seconds', 'N/A')} detik"
        )

    net.toggle_physics(True)
    net.write_html(output_html_path)
    print(f"[SUKSES] File visualisasi graf berhasil disimpan di: {output_html_path}")


# =====================================================================
# MODUL 7: ANALISIS KEPADATAN UNTUK INDIKASI KOORDINASI
# =====================================================================
def get_cluster_status(size, density, total_pair_matches, config):
    min_size = config.get("MIN_SUSPICIOUS_CLUSTER_SIZE", 5)
    min_matches = config.get("MIN_SUSPICIOUS_EDGE_EVIDENCE", 5)
    score = density * np.log2(size + 1)

    if size < min_size or total_pair_matches < min_matches:
        return score, "Indikasi lemah (kluster kecil/minim bukti)"
    if score >= 1.5:
        return score, "Sangat mencurigakan"
    if score >= 0.8:
        return score, "Perlu investigasi"
    return score, "Rendah / cenderung organik"


# [REFERENSI PPT: SLIDE 8 & SLIDE DETAIL - KLUSTER UNGGULAN & INTERPRETASI]
# Menghitung Metrik Kluster: Jumlah Akun (Size), Kepadatan (Density), Edge (Bukti), dan memberi status koordinasi.
def calculate_and_export_cluster_density(G, cluster_labels, output_filename, config=None):
    print("Menghitung metrik kepadatan dan bukti koordinasi kluster...")
    config = config or {}

    node_communities = nx.get_node_attributes(G, "community")
    clusters = {}
    for node, cid in node_communities.items():
        clusters.setdefault(cid, []).append(node)

    density_data = []

    for cid, nodes in clusters.items():
        subgraph = G.subgraph(nodes)
        if subgraph.number_of_nodes() <= 1:
            continue

        c_density = nx.density(subgraph)
        c_size = subgraph.number_of_nodes()
        c_topic = cluster_labels.get(cid, "Topik tidak terdefinisi")
        total_pair_matches = sum(
            int(data.get("Edge_Count", 1)) for _, _, data in subgraph.edges(data=True)
        )
        edge_type_values = [
            str(data.get("Edge_Types", "")) for _, _, data in subgraph.edges(data=True)
        ]
        retweet_edges = sum("retweet" in value for value in edge_type_values)
        semantic_edges = sum("semantic" in value for value in edge_type_values)
        dominant_rt_sources = [
            data.get("Dominant_RT_Source")
            for _, _, data in subgraph.edges(data=True)
            if data.get("Dominant_RT_Source")
        ]
        dominant_rt_source = most_common_nonempty(dominant_rt_sources)
        avg_weight = np.mean(
            [float(data.get("Weight", 0)) for _, _, data in subgraph.edges(data=True)]
        )
        score, status = get_cluster_status(
            c_size, c_density, total_pair_matches, config
        )

        density_data.append(
            {
                "Cluster_ID": cid,
                "Size_Jumlah_Akun": c_size,
                "Density": round(c_density, 5),
                "Edge_Count": subgraph.number_of_edges(),
                "Total_Evidence_Matches": total_pair_matches,
                "Avg_Weight": round(float(avg_weight), 5),
                "Retweet_Edges": retweet_edges,
                "Semantic_Edges": semantic_edges,
                "Dominant_RT_Source": dominant_rt_source,
                "Coordination_Score": round(float(score), 5),
                "Status": status,
                "Topik_Utama": c_topic,
            }
        )

    if not density_data:
        print("[Peringatan] Tidak ada data kluster yang valid untuk dihitung.")
        return None

    density_df = pd.DataFrame(density_data)
    status_rank = {
        "Sangat mencurigakan": 3,
        "Perlu investigasi": 2,
        "Indikasi lemah (kluster kecil/minim bukti)": 1,
        "Rendah / cenderung organik": 0,
    }
    density_df["_Status_Rank"] = density_df["Status"].map(status_rank).fillna(0)
    density_df = density_df.sort_values(
        by=["_Status_Rank", "Coordination_Score", "Total_Evidence_Matches"],
        ascending=[False, False, False],
    ).drop(columns=["_Status_Rank"]).reset_index(drop=True)

    density_df.to_csv(output_filename, index=False)
    print(f"[SUKSES] Laporan kluster berhasil disimpan di: {output_filename}")

    return density_df


def export_threshold_sensitivity(df, embeddings, config, output_filename):
    """Opsional: ringkasan sensitivitas threshold agar klaim tidak rapuh."""
    if not config.get("RUN_SENSITIVITY", False):
        return None

    print("Menjalankan sensitivity check ringan...")
    original_text = config["THRESHOLD_TEXT"]
    original_time = config["THRESHOLD_TIME"]
    rows = []

    for text_threshold in config.get("SENSITIVITY_TEXT_THRESHOLDS", [0.65, 0.75, 0.85]):
        for time_threshold in config.get("SENSITIVITY_TIME_WINDOWS", [600, 1800, 3600]):
            temp_config = config.copy()
            temp_config["THRESHOLD_TEXT"] = text_threshold
            temp_config["THRESHOLD_TIME"] = time_threshold
            temp_edges = extract_coordination_edges(df, embeddings, temp_config)
            temp_df = pd.DataFrame(temp_edges)
            if temp_df.empty:
                rows.append(
                    {
                        "Threshold_Text": text_threshold,
                        "Threshold_Time_Seconds": time_threshold,
                        "Aggregated_Edges": 0,
                        "Accounts_In_Graph": 0,
                        "Raw_Evidence_Matches": 0,
                    }
                )
                continue
            accounts = set(temp_df["Source"]) | set(temp_df["Target"])
            rows.append(
                {
                    "Threshold_Text": text_threshold,
                    "Threshold_Time_Seconds": time_threshold,
                    "Aggregated_Edges": temp_df.groupby(["Source", "Target"]).ngroups,
                    "Accounts_In_Graph": len(accounts),
                    "Raw_Evidence_Matches": len(temp_df),
                }
            )

    config["THRESHOLD_TEXT"] = original_text
    config["THRESHOLD_TIME"] = original_time
    sensitivity_df = pd.DataFrame(rows)
    sensitivity_df.to_csv(output_filename, index=False)
    print(f"[SUKSES] Sensitivity check disimpan di: {output_filename}")
    return sensitivity_df


if __name__ == "__main__":
    CONFIG = {
        "MODEL_NAME": "symanto/sn-xlm-roberta-base-snli-mnli-anli-xnli",
        "MAX_ROWS": None,
        "ALPHA": 0.5,
        "LAMBDA": 0.001155,
        "THRESHOLD_TEXT": 0.65,
        "THRESHOLD_TIME": 1800,
        "THRESHOLD_RETWEET_TIME": 1800,
        "INCLUDE_RETWEETS_IN_SEMANTIC": False,
        "LOUVAIN_RESOLUTION": 2.0,
        "RANDOM_SEED": 42,
        "MIN_SUSPICIOUS_CLUSTER_SIZE": 5,
        "MIN_SUSPICIOUS_EDGE_EVIDENCE": 5,
        "RUN_SENSITIVITY": False,
    }

    try:
        raw_data = load_and_combine_json(
            main_folder=main_folder_path,
            file_pattern="data-twit-*.json",
            max_rows=CONFIG["MAX_ROWS"],
        )
        cleaned_data = preprocess_tweets(raw_data)
        audit_dataset(
            cleaned_data,
            output_filename=os.path.join(main_folder_path, "data_audit.csv"),
        )
        print(cleaned_data.head())
        print(cleaned_data.info())
        cleaned_data.to_csv(os.path.join(main_folder_path, "cleaned_data.csv"), index=False)

        tweet_embeddings = generate_embeddings(
            sentences=cleaned_data["cleaned_content"].tolist(),
            model_name=CONFIG["MODEL_NAME"],
        )

        export_threshold_sensitivity(
            df=cleaned_data,
            embeddings=tweet_embeddings,
            config=CONFIG,
            output_filename=os.path.join(main_folder_path, "threshold_sensitivity.csv"),
        )

        extracted_edges = extract_coordination_edges(
            df=cleaned_data, embeddings=tweet_embeddings, config=CONFIG
        )

        output_file = os.path.join(main_folder_path, "relation.csv")
        export_network_to_csv(
            edges_list=extracted_edges,
            output_filename=output_file,
        )

        graph_obj = analyze_coordination_graph(
            csv_path=output_file,
            df=cleaned_data,
            config=CONFIG,
        )

        labels_topik = extract_cluster_topics(df=cleaned_data, G=graph_obj, top_n=5)

        html_output = os.path.join(main_folder_path, "visualisasi_st.html")
        generate_and_save_html(
            G=graph_obj,
            cluster_labels=labels_topik,
            output_html_path=html_output,
        )

        print(f"\n--> SELESAI. File visualisasi interaktif telah disimpan di: {html_output}")

        density_csv_path = os.path.join(main_folder_path, "cluster_density_report.csv")
        df_density = calculate_and_export_cluster_density(
            G=graph_obj,
            cluster_labels=labels_topik,
            output_filename=density_csv_path,
            config=CONFIG,
        )

        if df_density is not None:
            print("\n=== TOP 10 KLUSTER DENGAN INDIKASI KOORDINASI TERKUAT ===")
            print(df_density.head(10))

        try:
            from generate_dashboard import generate_dashboard

            generate_dashboard(main_folder_path)
        except Exception as dash_err:
            print(f"\n[Peringatan] Gagal membuat dashboard analitis: {str(dash_err)}")

    except Exception as e:
        print(f"\n[Eror Sistem] Terjadi kegagalan proses: {str(e)}")
