import os
import re
import json
import math
import pandas as pd
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer

NON_RT_MIN_AVG_SIMILARITY = 0.75
NON_RT_MAX_MIN_DELTA_SECONDS = 300
NON_RT_LOUVAIN_RESOLUTION = 6.5

CLUSTER_PALETTE = [
    "#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2",
    "#be123c", "#4f46e5", "#65a30d", "#c2410c", "#0f766e", "#9333ea",
]

def most_common_nonempty(values):
    cleaned = []
    for value in values:
        if pd.isna(value):
            continue
        value = str(value).strip()
        if value:
            cleaned.append(value)
    if not cleaned:
        return ""
    return pd.Series(cleaned).value_counts().idxmax()

def clean_keyword(word):
    if len(word) <= 2:
        return False
    if re.match(r'^[a-z0-9]{16,}$', word) and not re.search(
        r'anies|prabowo|ganjar|mahfud|gibran|muhaimin|amin', word.lower()
    ):
        return False
    if re.match(r'^\d+$', word):
        return False
    cleaned = re.sub(r'[^a-zA-Z]', '', word)
    if len(cleaned) <= 2:
        return False
    return cleaned.lower()

def is_truthy(value):
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return value != 0
    return bool(value)

def classify_tweet(row):
    if is_truthy(row.get('is_retweet', False)):
        return "Retweet"
    if is_truthy(row.get('is_reply_or_mention', False)):
        return "Reply/Mention"
    return "Tweet Asli"

def join_unique(values, limit=3):
    seen = []
    for value in values:
        if pd.isna(value):
            continue
        for part in str(value).split("|"):
            cleaned = re.sub(r'\s+', ' ', part).strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
            if len(seen) >= limit:
                return " | ".join(seen)
    return " | ".join(seen)

def edge_pair_id(source, target):
    return "||".join(sorted([str(source), str(target)]))

def cluster_visual_color(cluster_id):
    return CLUSTER_PALETTE[int(cluster_id) % len(CLUSTER_PALETTE)]

def number_or_none(value):
    numeric = pd.to_numeric(value, errors='coerce')
    if pd.isna(numeric):
        return None
    return float(numeric)

def compact_seconds(seconds):
    if seconds is None or pd.isna(seconds):
        return "N/A"
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "N/A"
    if seconds < 60:
        return f"{seconds:.0f} detik"
    return f"{seconds / 60:.1f} menit"

def aggregate_semantic_edges_from_evidence(evidence_path):
    evidence_df = pd.read_csv(evidence_path)
    evidence_df['edge_type'] = evidence_df['edge_type'].fillna('').astype(str).str.lower()
    semantic_df = evidence_df[evidence_df['edge_type'].eq('semantic')].copy()

    expected_columns = [
        'Source', 'Target', 'Weight', 'Max_Weight', 'Edge_Count',
        'Avg_Text_Similarity', 'Avg_Time_Score', 'Min_Time_Delta_Seconds',
        'Edge_Types', 'Dominant_RT_Source', 'Query_Context',
        'Example_Tweet_1', 'Example_Tweet_2'
    ]
    if semantic_df.empty:
        return pd.DataFrame(columns=expected_columns), semantic_df

    for col in ['Weight', 's_text', 's_time', 'delta_t_seconds']:
        semantic_df[col] = pd.to_numeric(semantic_df[col], errors='coerce')

    edges_df = (
        semantic_df.groupby(['Source', 'Target'])
        .agg(
            Weight=('Weight', 'mean'),
            Max_Weight=('Weight', 'max'),
            Edge_Count=('Weight', 'size'),
            Avg_Text_Similarity=('s_text', 'mean'),
            Avg_Time_Score=('s_time', 'mean'),
            Min_Time_Delta_Seconds=('delta_t_seconds', 'min'),
            Edge_Types=('edge_type', join_unique),
            Dominant_RT_Source=('rt_source', most_common_nonempty),
            Query_Context=('query_i', lambda values: join_unique(values, limit=4)),
            Example_Tweet_1=('tweet_i', lambda values: join_unique(values, limit=2)),
            Example_Tweet_2=('tweet_j', lambda values: join_unique(values, limit=2)),
        )
        .reset_index()
    )
    edges_df['Edge_Types'] = 'semantic'
    edges_df['Dominant_RT_Source'] = ''
    edges_df = edges_df.sort_values(
        by=['Edge_Count', 'Weight'], ascending=[False, False]
    ).reset_index(drop=True)
    return edges_df, semantic_df

def build_node_example_map(evidence_df):
    example_map = {}
    if evidence_df.empty:
        return example_map

    ranked = evidence_df.copy()
    ranked['Weight'] = pd.to_numeric(ranked['Weight'], errors='coerce').fillna(0)
    ranked = ranked.sort_values('Weight', ascending=False)
    for _, row in ranked.iterrows():
        for node_col, tweet_col in [('Source', 'tweet_i'), ('Target', 'tweet_j')]:
            node = str(row.get(node_col, '')).strip()
            tweet = str(row.get(tweet_col, '')).strip()
            if node and tweet and tweet.lower() != 'nan' and node not in example_map:
                example_map[node] = re.sub(r'\s+', ' ', tweet)
    return example_map

def detect_narrative_focus(text_corpus):
    """Melabeli objek narasi, bukan sikap dukungan/oposisi."""
    text = text_corpus.lower()
    patterns = {
        "anies": r"\b(anies|baswedan|muhaimin|cak\s*imin|aminajadulu)\b",
        "prabowo": r"\b(prabowo|gibran|prabowogibran|gemoy)\b",
        "ganjar": r"\b(ganjar|mahfud|pranowo|ganjarmahfud|mahfudlebihbaik3|l3bihbaik)\b",
    }
    counts = {key: len(re.findall(pattern, text)) for key, pattern in patterns.items()}
    total = sum(counts.values())

    colors = {
        "anies": "#5aa7c8",
        "prabowo": "#d79a57",
        "ganjar": "#cf7373",
        "mixed": "#9b8bd3",
        "general": "#8a94a6",
    }
    names = {
        "anies": "Dominan membahas Anies-Muhaimin",
        "prabowo": "Dominan membahas Prabowo-Gibran",
        "ganjar": "Dominan membahas Ganjar-Mahfud",
    }

    if total == 0:
        return "Tanpa kandidat dominan", colors["general"], counts, 0.0

    top_key, top_count = max(counts.items(), key=lambda item: item[1])
    top_share = top_count / total
    if top_count >= 2 and top_share >= 0.6:
        return names[top_key], colors[top_key], counts, top_share

    return "Lintas kandidat / perbandingan", colors["mixed"], counts, top_share

def generate_dashboard(folder_path, non_rt_only=False, output_filename=None):
    mode_name = "Non-RT Light" if non_rt_only else "Laporan Koordinasi"
    print(f"Membuat Dashboard Analitis Graf-Sentris ({mode_name})...")
    cleaned_path = os.path.join(folder_path, "cleaned_data.csv")
    relation_path = os.path.join(folder_path, "relation.csv")
    evidence_path = os.path.join(folder_path, "relation_evidence.csv")
    
    df = pd.read_csv(cleaned_path)
    semantic_evidence_df = pd.DataFrame()
    if non_rt_only and os.path.exists(evidence_path):
        edges_df, semantic_evidence_df = aggregate_semantic_edges_from_evidence(evidence_path)
        print(f"Mode Non-RT: memakai {len(edges_df)} edge pasangan semantik dari {len(semantic_evidence_df)} bukti non-retweet.")
    else:
        edges_df = pd.read_csv(relation_path)
    
    df['content'] = df['content'].fillna('')
    df['cleaned_content'] = df['cleaned_content'].fillna('')
    if 'topic_content' not in df.columns:
        df['topic_content'] = df['cleaned_content']
    df['topic_content'] = df['topic_content'].fillna('')
    if 'is_retweet' not in df.columns:
        df['is_retweet'] = df['content'].str.match(r'^RT\b', case=False)
    if 'is_reply_or_mention' not in df.columns:
        reply_source = (
            df['in_reply_to_screen_name']
            if 'in_reply_to_screen_name' in df.columns
            else pd.Series('', index=df.index)
        )
        df['is_reply_or_mention'] = (
            reply_source.fillna('').astype(str).str.strip().ne('')
            | df['content'].str.match(r'^@\w+')
        )
    if 'rt_source' not in df.columns:
        df['rt_source'] = ''
    if 'rt_source_id' not in df.columns:
        df['rt_source_id'] = ''
    df['is_retweet'] = df['is_retweet'].apply(is_truthy)
    df['is_reply_or_mention'] = df['is_reply_or_mention'].apply(is_truthy)
    if 'query_candidate' not in df.columns:
        df['query_candidate'] = 'unknown'
    if 'Edge_Count' not in edges_df.columns:
        edges_df['Edge_Count'] = 1
    if 'Edge_Types' not in edges_df.columns:
        edges_df['Edge_Types'] = 'semantic'
    if 'Dominant_RT_Source' not in edges_df.columns:
        edges_df['Dominant_RT_Source'] = ''
    if 'Min_Time_Delta_Seconds' not in edges_df.columns:
        edges_df['Min_Time_Delta_Seconds'] = ''
    edges_df['Dominant_RT_Source'] = edges_df['Dominant_RT_Source'].fillna('')
    edges_df['Edge_Types'] = edges_df['Edge_Types'].fillna('semantic')
    if non_rt_only:
        for col in ['Avg_Text_Similarity', 'Min_Time_Delta_Seconds', 'Weight']:
            edges_df[col] = pd.to_numeric(edges_df[col], errors='coerce')
        before_backbone_edges = len(edges_df)
        edges_df = edges_df[edges_df['Edge_Types'].astype(str).str.contains('semantic', case=False, na=False)].copy()
        edges_df = edges_df[
            (edges_df['Avg_Text_Similarity'] >= NON_RT_MIN_AVG_SIMILARITY)
            & (edges_df['Min_Time_Delta_Seconds'] <= NON_RT_MAX_MIN_DELTA_SECONDS)
        ].copy()
        edges_df['Edge_Types'] = 'semantic'
        edges_df['Dominant_RT_Source'] = ''
        kept_pairs = {
            edge_pair_id(row.Source, row.Target)
            for row in edges_df[['Source', 'Target']].itertuples(index=False)
        }
        if not semantic_evidence_df.empty:
            semantic_evidence_df = semantic_evidence_df[
                semantic_evidence_df.apply(
                    lambda row: edge_pair_id(row['Source'], row['Target']) in kept_pairs,
                    axis=1
                )
            ].copy()
        print(
            "Backbone Non-RT: "
            f"{len(edges_df)} dari {before_backbone_edges} edge dipakai "
            f"(avg similarity >= {NON_RT_MIN_AVG_SIMILARITY}, "
            f"min jeda <= {NON_RT_MAX_MIN_DELTA_SECONDS} detik)."
        )
    
    G = nx.from_pandas_edgelist(edges_df, source='Source', target='Target', edge_attr=True)
    
    analysis_df = df[~df['is_retweet']].copy() if non_rt_only else df.copy()
    latest_source_df = analysis_df if non_rt_only else df
    latest_df = latest_source_df.sort_values('date_created').drop_duplicates(subset=['name'], keep='last')
    latest_df = latest_df.copy()
    latest_df['tweet_type'] = latest_df.apply(classify_tweet, axis=1)
    latest_df['rt_source'] = latest_df['rt_source'].fillna('')
    latest_df['rt_source_id'] = latest_df['rt_source_id'].fillna('')
    latest_by_name = latest_df.set_index('name')
    tweet_mapping = latest_df.set_index('name')['cleaned_content'].to_dict()
    semantic_example_map = build_node_example_map(semantic_evidence_df) if non_rt_only else {}
    if semantic_example_map:
        tweet_mapping.update(semantic_example_map)
    nx.set_node_attributes(G, tweet_mapping, 'last_tweet')
    account_stats = df.groupby('name').agg(
        tweet_count=('content', 'size'),
        rt_count=('is_retweet', 'sum'),
        query_context=('query_candidate', lambda x: ' | '.join(sorted(set(x))))
    )
    account_stats['rt_ratio'] = account_stats['rt_count'] / account_stats['tweet_count']
    for attr in ['tweet_count', 'rt_count', 'query_context', 'rt_ratio']:
        nx.set_node_attributes(G, account_stats[attr].to_dict(), attr)
    
    pagerank_scores = nx.pagerank(G, weight='Weight')
    nx.set_node_attributes(G, pagerank_scores, 'pagerank')
    
    louvain_resolution = NON_RT_LOUVAIN_RESOLUTION if non_rt_only else 3.5
    communities = nx.community.louvain_communities(
        G, weight='Weight', resolution=louvain_resolution, seed=42
    )
    community_dict = {}
    for cluster_id, group_nodes in enumerate(communities):
        for node in group_nodes:
            community_dict[node] = cluster_id
    nx.set_node_attributes(G, community_dict, 'community')
    
    custom_stopwords = [
        'rt', 're', 'retweet', 'twit', 'tweet', 'https', 'http', 'com', 'amp',
        'yang', 'di', 'dan', 'itu', 'ini', 'untuk', 'dengan', 'ada', 'seperti',
        'dari', 'ke', 'akan', 'bisa', 'ya', 'ga', 'gak', 'aja', 'kalo', 'kalau',
        'oleh', 'hanya', 'atau', 'pada', 'juga', 'sudah', 'telah', 'saya', 'kami',
        'mereka', 'dia', 'adalah', 'bahwa', 'tidak', 'bukan', 'tapi', 'namun',
        'yg', 'utk', 'jd', 'bgt', 'dgn', 'lalu', 'maka', 'karena', 'bila', 'jika',
        'ga', 'gak', 'gue', 'gw', 'lu', 'lo', 'nya', 'nih', 'sih', 'dong',
        'pak', 'bapak', 'mas', 'bang', 'bung', 'ibu', 'dok', 'prof', 'www', 'tco',
        'pic', 'twitter', 'xcom', 'and', 'the', 'to', 'of', 'in', 'for', 'is',
        'are', 'you', 'your'
    ]
    
    cluster_docs = {}
    cluster_nodes = {}
    for node, cid in community_dict.items():
        if cid not in cluster_docs:
            cluster_docs[cid] = []
            cluster_nodes[cid] = []
        cluster_nodes[cid].append(node)
        user_tweets = analysis_df[analysis_df['name'] == node]['topic_content'].values
        if len(user_tweets) > 0:
            cluster_docs[cid].append(" ".join(user_tweets))
            
    sorted_cids = sorted(list(cluster_docs.keys()))
    cluster_corpus = [" ".join(cluster_docs[cid]) for cid in sorted_cids]
    
    tfidf_labels = {}
    if cluster_corpus:
        vectorizer = TfidfVectorizer(
            max_df=0.85,
            min_df=1,
            stop_words=custom_stopwords,
            token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z0-9_]{2,}\b'
        )
        try:
            tfidf_matrix = vectorizer.fit_transform(cluster_corpus)
            feature_names = vectorizer.get_feature_names_out()
            for i, cid in enumerate(sorted_cids):
                row = tfidf_matrix.getrow(i).toarray()[0]
                top_indices = np.argsort(row)[::-1]
                valid_keywords = []
                for idx in top_indices:
                    word = feature_names[idx]
                    cleaned_word = clean_keyword(word)
                    if cleaned_word and cleaned_word not in custom_stopwords:
                        valid_keywords.append(cleaned_word)
                    if len(valid_keywords) >= 5:
                        break
                tfidf_labels[cid] = ", ".join(valid_keywords) if valid_keywords else "N/A"
        except Exception as e:
            print(f"TF-IDF Error: {e}")
            for cid in sorted_cids:
                tfidf_labels[cid] = "N/A"
                
    cluster_analysis_dict = {}
    cluster_top_node = {}
    
    for cid in sorted_cids:
        nodes = cluster_nodes[cid]
        size = len(nodes)
        if size < 3:
            continue
        subgraph = G.subgraph(nodes)
        density = nx.density(subgraph)
        total_pair_matches = sum(int(data.get('Edge_Count', 1)) for _, _, data in subgraph.edges(data=True))
        edge_type_values = [str(data.get('Edge_Types', '')) for _, _, data in subgraph.edges(data=True)]
        retweet_edges = sum('retweet' in value for value in edge_type_values)
        semantic_edges = sum('semantic' in value for value in edge_type_values)
        edge_records = [data for _, _, data in subgraph.edges(data=True)]
        text_similarity_values = [
            number_or_none(data.get('Avg_Text_Similarity')) for data in edge_records
        ]
        text_similarity_values = [value for value in text_similarity_values if value is not None]
        delta_values = [
            number_or_none(data.get('Min_Time_Delta_Seconds')) for data in edge_records
        ]
        delta_values = [value for value in delta_values if value is not None]
        avg_text_similarity = float(np.mean(text_similarity_values)) if text_similarity_values else 0.0
        median_time_delta = float(np.median(delta_values)) if delta_values else 0.0
        min_time_delta = float(np.min(delta_values)) if delta_values else 0.0
        strong_text_edges = sum(value >= 0.85 for value in text_similarity_values)
        close_time_edges = sum(value <= 60 for value in delta_values)
        avg_pair_evidence = total_pair_matches / semantic_edges if semantic_edges else 0.0
        if avg_text_similarity >= 0.85 and median_time_delta <= 60:
            reason_summary = "Kluster ini terbentuk karena narasi antar-akun sangat mirip dan muncul dalam waktu sangat berdekatan."
        elif avg_text_similarity >= 0.85:
            reason_summary = "Kluster ini terutama kuat karena kemiripan narasi; kedekatan waktu menjadi bukti pendukung."
        elif median_time_delta <= 60:
            reason_summary = "Kluster ini terutama kuat karena narasi yang mirip muncul hampir bersamaan."
        elif non_rt_only:
            reason_summary = "Kluster ini terbentuk dari kombinasi kemiripan narasi dan kedekatan waktu, bukan dari retweet."
        else:
            reason_summary = "Kluster ini terbentuk dari kombinasi kemiripan narasi, kedekatan waktu, dan komposisi edge yang terlihat pada metrik."

        evidence_pairs = []
        ranked_edges = sorted(
            subgraph.edges(data=True),
            key=lambda item: (
                int(item[2].get('Edge_Count', 1)),
                float(item[2].get('Avg_Text_Similarity', 0) or 0),
                float(item[2].get('Weight', 0) or 0),
            ),
            reverse=True,
        )
        for u, v, data in ranked_edges[:3]:
            evidence_pairs.append({
                "source": u,
                "target": v,
                "evidence_count": int(data.get('Edge_Count', 1)),
                "avg_similarity": round(float(data.get('Avg_Text_Similarity', 0) or 0), 3),
                "min_delta_seconds": round(float(data.get('Min_Time_Delta_Seconds', 0) or 0), 1),
                "min_delta_label": compact_seconds(data.get('Min_Time_Delta_Seconds')),
                "tweet_1": re.sub(r'\s+', ' ', str(data.get('Example_Tweet_1', ''))).strip(),
                "tweet_2": re.sub(r'\s+', ' ', str(data.get('Example_Tweet_2', ''))).strip(),
            })
        dominant_rt_source = most_common_nonempty(
            [data.get('Dominant_RT_Source') for _, _, data in subgraph.edges(data=True)]
        )
        cluster_pageranks = {n: pagerank_scores[n] for n in nodes}
        top_nodes = sorted(cluster_pageranks.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if top_nodes:
            cluster_top_node[cid] = top_nodes[0][0]
            
        cluster_tweets = []
        if non_rt_only and not semantic_evidence_df.empty:
            semantic_cluster_rows = semantic_evidence_df[
                semantic_evidence_df['Source'].isin(nodes)
                & semantic_evidence_df['Target'].isin(nodes)
            ].copy()
            semantic_cluster_rows['Weight'] = pd.to_numeric(
                semantic_cluster_rows['Weight'], errors='coerce'
            ).fillna(0)
            for _, row in semantic_cluster_rows.sort_values('Weight', ascending=False).head(40).iterrows():
                for col in ['tweet_i', 'tweet_j']:
                    t = row.get(col, '')
                    if isinstance(t, str) and len(t.strip()) > 10:
                        cluster_tweets.append(t.strip())
        else:
            for n in nodes:
                user_tweets = analysis_df[analysis_df['name'] == n]['cleaned_content'].values
                for t in user_tweets:
                    if isinstance(t, str) and len(t.strip()) > 10:
                        cluster_tweets.append(t.strip())
        unique_tweets = list(dict.fromkeys(cluster_tweets))
        unique_tweets.sort(key=len, reverse=True)
        sample_tweets_list = [re.sub(r'\s+', ' ', t).strip() for t in unique_tweets[:3]]
        
        top_accounts_detail = []
        for node, pr_val in top_nodes:
            node_tweets = analysis_df[analysis_df['name'] == node]['cleaned_content'].values
            last_t = semantic_example_map.get(node) if non_rt_only else None
            if not last_t:
                last_t = node_tweets[0].strip() if len(node_tweets) > 0 else "Tidak ada tweet"
            last_t = re.sub(r'\s+', ' ', last_t)
            latest_meta = latest_by_name.loc[node] if node in latest_by_name.index else None
            top_accounts_detail.append({
                "username": node,
                "pagerank": round(pr_val, 6),
                "tweet": last_t,
                "tweet_type": "Non-RT (bukti semantik)" if non_rt_only else latest_meta.get('tweet_type', 'Tidak diketahui') if latest_meta is not None else "Tidak diketahui",
                "rt_source": "" if non_rt_only else latest_meta.get('rt_source', '') if latest_meta is not None else "",
                "rt_ratio": round(float(G.nodes[node].get('rt_ratio', 0)), 4)
            })
            
        cluster_all_text = " ".join(cluster_docs[cid])
        narrative_focus, focus_color, focus_counts, focus_confidence = detect_narrative_focus(cluster_all_text)
        buzzer_score = density * np.log2(size + 1)
        
        if size < 5 or total_pair_matches < 5:
            status = "Indikasi Lemah"
        elif buzzer_score >= 1.5:
            status = "Koordinasi Kuat"
        elif buzzer_score >= 0.8:
            status = "Perlu Investigasi"
        else:
            status = "Rendah"
            
        kws = tfidf_labels.get(cid, "N/A")
        keyword_list = [k.strip() for k in kws.split(",") if k.strip() != "N/A"]
        
        if non_rt_only:
            evidence_note = f"{total_pair_matches} bukti pasangan semantik non-RT; edge RT dikeluarkan dari pembentukan kluster"
        else:
            evidence_note = f"{total_pair_matches} bukti pasangan, {retweet_edges} edge RT, {semantic_edges} edge semantik"
        if dominant_rt_source and not non_rt_only:
            evidence_note += f", sumber RT dominan @{dominant_rt_source}"
        
        if non_rt_only:
            focus_note = "Label fokus narasi tetap objek pembahasan, bukan dukungan politik; RT hanya dipakai sebagai konteks rasio akun."
        else:
            focus_note = "Label fokus narasi dibuat dari frekuensi penyebutan kandidat, bukan analisis sentimen atau dukungan politik."
        if keyword_list and narrative_focus != "Tanpa kandidat dominan":
            narasi = f"{narrative_focus}. Topik utama: {', '.join(keyword_list[:3])}. Bukti ringkas: {evidence_note}. {focus_note}"
        elif keyword_list:
            narasi = f"Kluster tanpa kandidat dominan dengan fokus topik: {', '.join(keyword_list[:3])}. Bukti ringkas: {evidence_note}. {focus_note}"
        else:
            narasi = f"Kluster diskusi umum. Bukti ringkas: {evidence_note}. {focus_note}"
            
        cluster_analysis_dict[cid] = {
            "cluster_id": cid,
            "size": size,
            "density": round(density, 4),
            "buzzer_score": round(buzzer_score, 4),
            "total_pair_matches": int(total_pair_matches),
            "retweet_edges": int(retweet_edges),
            "semantic_edges": int(semantic_edges),
            "dominant_rt_source": dominant_rt_source,
            "affiliation": narrative_focus,
            "affiliation_color": focus_color,
            "affiliation_emoji": "",
            "narrative_focus": narrative_focus,
            "focus_color": focus_color,
            "cluster_color": cluster_visual_color(cid) if non_rt_only else focus_color,
            "focus_counts": focus_counts,
            "focus_confidence": round(float(focus_confidence), 4),
            "reason_summary": reason_summary,
            "avg_text_similarity": round(avg_text_similarity, 3),
            "median_time_delta_seconds": round(median_time_delta, 1),
            "median_time_delta_label": compact_seconds(median_time_delta),
            "min_time_delta_seconds": round(min_time_delta, 1),
            "min_time_delta_label": compact_seconds(min_time_delta),
            "strong_text_edges": int(strong_text_edges),
            "close_time_edges": int(close_time_edges),
            "avg_pair_evidence": round(avg_pair_evidence, 2),
            "backbone_note": (
                f"Backbone: similarity >= {NON_RT_MIN_AVG_SIMILARITY}, "
                f"jeda tercepat <= {compact_seconds(NON_RT_MAX_MIN_DELTA_SECONDS)}"
            ) if non_rt_only else "",
            "evidence_pairs": evidence_pairs,
            "status": status,
            "status_emoji": "",
            "keywords": kws,
            "keyword_list": keyword_list,
            "narasi": narasi,
            "top_accounts": top_accounts_detail,
            "sample_tweets": sample_tweets_list
        }
        
    nodes_json = []
    edges_json = []
    rendered_nodes = set()
    
    for node in G.nodes():
        cid = community_dict.get(node)
        if cid in cluster_analysis_dict:
            c = cluster_analysis_dict[cid]
            pr = pagerank_scores.get(node, 0)
            
            is_top = (cluster_top_node.get(cid) == node)
            
            # Map node size proportionally [12px to 38px] so they look good even when zoomed out
            size_val = int(12 + math.log(pr * 2000 + 1) * 5.0) if pr > 0 else 12
            
            hover_title = (
                f"<b>Akun:</b> @{node}<br>"
                f"<b>Kluster:</b> #{cid}<br>"
                f"<b>PageRank:</b> {pr:.6f}<br>"
                f"<b>Jenis tweet:</b> {'Non-RT (bukti semantik)' if non_rt_only else latest_by_name.loc[node].get('tweet_type', 'Tidak diketahui') if node in latest_by_name.index else 'Tidak diketahui'}<br>"
                f"<b>Rasio RT akun:</b> {G.nodes[node].get('rt_ratio', 0):.2f}"
            )
            latest_meta = latest_by_name.loc[node] if node in latest_by_name.index else None
            
            nodes_json.append({
                "id": node,
                "label": "", # Default blank labels for clean visualization
                "size": size_val,
                "color": c.get('cluster_color', c['affiliation_color']),
                "community": int(cid),
                "title": hover_title,
                "is_top": is_top,
                "tweet": tweet_mapping.get(node, "Tidak ada tweet"),
                "pagerank": round(pr, 6),
                "rt_ratio": round(float(G.nodes[node].get('rt_ratio', 0)), 4),
                "tweet_type": "Non-RT (bukti semantik)" if non_rt_only else latest_meta.get('tweet_type', 'Tidak diketahui') if latest_meta is not None else "Tidak diketahui",
                "rt_source": "" if non_rt_only else latest_meta.get('rt_source', '') if latest_meta is not None else "",
                "rt_source_id": "" if non_rt_only else latest_meta.get('rt_source_id', '') if latest_meta is not None else "",
                "is_retweet": False if non_rt_only else bool(is_truthy(latest_meta.get('is_retweet', False))) if latest_meta is not None else False,
                "is_reply_or_mention": bool(is_truthy(latest_meta.get('is_reply_or_mention', False))) if latest_meta is not None else False
            })
            rendered_nodes.add(node)
            
    for u, v, data in G.edges(data=True):
        if u in rendered_nodes and v in rendered_nodes:
            u_cid = community_dict.get(u)
            v_cid = community_dict.get(v)
            if non_rt_only and u_cid != v_cid:
                continue
            w = data.get('Weight', 0.1)
            edge_count = int(data.get('Edge_Count', 1))
            # Crisp and highly visible edges
            if non_rt_only:
                edge_title = (
                    f"Jenis: Semantik Non-RT<br>"
                    f"Bukti pasangan: {edge_count}<br>"
                    f"Min jeda: {data.get('Min_Time_Delta_Seconds', 'N/A')} detik"
                )
                edge_color = cluster_analysis_dict.get(u_cid, {}).get('cluster_color', '#94a3b8')
                edge_opacity = float(0.16 + float(w) * 0.22)
                edge_scale_cap = 2.2
            else:
                edge_title = (
                    f"Jenis: {data.get('Edge_Types', 'N/A')}<br>"
                    f"Bukti pasangan: {edge_count}<br>"
                    f"Min jeda: {data.get('Min_Time_Delta_Seconds', 'N/A')} detik<br>"
                    f"Sumber RT: {data.get('Dominant_RT_Source', '-') or '-'}"
                )
                edge_color = "#64748b"
                edge_opacity = float(0.28 + float(w) * 0.35)
                edge_scale_cap = 3
            edges_json.append({
                "from": u,
                "to": v,
                "value": float(w) * max(1, min(edge_scale_cap, math.log2(edge_count + 1))),
                "title": edge_title,
                "color": {"color": edge_color, "opacity": edge_opacity}
            })
            
    stats = {
        "total_nodes": len(rendered_nodes),
        "total_edges": len(edges_json),
        "total_clusters": len(cluster_analysis_dict),
        "suspicious_clusters": sum(
            1 for c in cluster_analysis_dict.values()
            if c['status'] == "Koordinasi Kuat"
        )
    }

    if non_rt_only:
        page_title = "Analisis Koordinasi Narasi Politik - Non-RT"
        header_badge = "Mode Non-RT"
        header_note = "Backbone narasi non-retweet"
        mode_note = (
            "Mode ini hanya membentuk edge dari tweet non-RT yang mirip secara semantik "
            f"dan muncul berdekatan waktunya. Backbone visual memakai similarity >= {NON_RT_MIN_AVG_SIMILARITY} "
            f"dan jeda tercepat <= {compact_seconds(NON_RT_MAX_MIN_DELTA_SECONDS)}. "
            "Retweet tidak dipakai untuk membuat kluster; rasio RT akun tetap ditampilkan sebagai konteks perilaku."
        )
        edge_stat_label = "Hubungan Narasi Non-RT"
        body_class = "light-mode"
        node_label_color = "#334155"
        legend_title = "Warna Kluster"
        legend_clusters = sorted(
            cluster_analysis_dict.values(),
            key=lambda c: c['buzzer_score'],
            reverse=True
        )[:6]
        legend_items = "\n".join(
            f'<div class="legend-item"><span class="legend-dot" style="background-color: {c["cluster_color"]};"></span>Kluster #{c["cluster_id"]}</div>'
            for c in legend_clusters
        )
        legend_note = "Warna node membedakan kluster visual; fokus narasi tetap dibaca dari badge dan panel kanan."
    else:
        page_title = "Analisis Koordinasi Narasi Politik"
        header_badge = "Laporan Koordinasi"
        header_note = "Visualisasi Kluster Twitter/X"
        mode_note = (
            "Graf ini membaca koordinasi dari kemiripan narasi, kedekatan waktu, dan relasi "
            "retweet yang sudah dipisahkan pada komposisi edge."
        )
        edge_stat_label = "Hubungan Interaksi"
        body_class = ""
        node_label_color = "#e2e8f0"
        legend_title = "Fokus Narasi"
        legend_items = """
                <div class="legend-item"><span class="legend-dot" style="background-color: #5aa7c8;"></span>Membahas Anies-Muhaimin</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: #d79a57;"></span>Membahas Prabowo-Gibran</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: #cf7373;"></span>Membahas Ganjar-Mahfud</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: #9b8bd3;"></span>Lintas kandidat</div>
                <div class="legend-item"><span class="legend-dot" style="background-color: #8a94a6;"></span>Tanpa kandidat dominan</div>
        """
        legend_note = "Warna menunjukkan objek pembahasan, bukan dukungan atau oposisi."
    
    html_template = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>/*HTML_TITLE*/</title>
    
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
    
    <style>
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #0f172a;
            color: #e2e8f0;
            margin: 0;
            overflow: hidden;
            height: 100vh;
        }
        
        #app-layout {
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100vw;
        }
        
        #header-bar {
            height: 60px;
            background-color: #1e293b;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            z-index: 100;
        }
        
        #main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        #visualizer-area {
            flex: 1;
            position: relative;
            background-color: #0f172a;
        }
        
        #network-canvas {
            width: 100%;
            height: 100%;
        }
        
        #analysis-panel {
            width: 500px;
            background-color: #1e293b;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .hud-panel {
            position: absolute;
            background: rgba(30, 41, 59, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 12px 16px;
            z-index: 50;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        #hud-legend {
            bottom: 24px;
            left: 24px;
        }
        
        .hud-title {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            margin-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 4px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 6px;
            font-size: 0.8rem;
            color: #cbd5e1;
        }
        
        .legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .nav-pills {
            background-color: #0f172a;
            padding: 4px;
            border-radius: 8px;
            margin: 16px 20px 12px 20px;
        }
        
        .nav-pills .nav-link {
            color: #94a3b8;
            background: none;
            border: none;
            font-weight: 600;
            font-size: 0.85rem;
            padding: 8px 12px;
            border-radius: 6px;
            transition: all 0.2s;
            flex: 1;
            text-align: center;
        }
        
        .nav-pills .nav-link.active {
            color: #ffffff;
            background-color: #334155;
        }
        
        .tab-content {
            flex: 1;
            overflow-y: auto;
            padding: 0 20px 20px 20px;
        }
        
        .tab-content::-webkit-scrollbar {
            width: 6px;
        }
        .tab-content::-webkit-scrollbar-track {
            background: transparent;
        }
        .tab-content::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }
        
        .table-dark-custom {
            font-size: 0.85rem;
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .table-dark-custom th {
            color: #94a3b8;
            font-weight: 600;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            padding: 8px 6px;
            text-align: left;
        }
        .table-dark-custom td {
            padding: 8px 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            cursor: pointer;
            transition: background 0.15s;
            color: #cbd5e1;
        }
        .table-dark-custom tr:hover td {
            background-color: rgba(255, 255, 255, 0.04);
            color: #ffffff;
        }
        
        .info-list {
            background-color: #0f172a;
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.85rem;
        }
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            color: #94a3b8;
            font-weight: 500;
        }
        
        .info-value {
            font-weight: 600;
            color: #ffffff;
        }
        
        .keyword-badge {
            background-color: rgba(255, 255, 255, 0.05);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            display: inline-block;
            margin: 2px;
        }
        
        blockquote.tweet-quote {
            border-left: 4px solid #475569;
            background: #0f172a;
            padding: 12px 14px;
            font-size: 0.85rem;
            border-radius: 0 6px 6px 0;
            margin-bottom: 12px;
            color: #cbd5e1;
            line-height: 1.45;
        }
        
        .top-account-item {
            background-color: #0f172a;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 8px;
        }
        
        .top-account-user {
            color: #38bdf8;
            font-weight: 600;
            font-size: 0.85rem;
        }

        .insight-note {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 12px 14px;
            color: #cbd5e1;
            font-size: 0.82rem;
            line-height: 1.55;
            margin-bottom: 16px;
        }

        .reason-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-bottom: 12px;
        }

        .reason-metric {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.03);
        }

        .reason-label {
            color: #94a3b8;
            font-size: 0.72rem;
            margin-bottom: 3px;
        }

        .reason-value {
            color: #ffffff;
            font-size: 0.95rem;
            font-weight: 700;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }

        .evidence-pair {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-left-width: 3px;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.03);
        }

        .evidence-meta {
            color: #94a3b8;
            font-size: 0.72rem;
            margin-top: 4px;
        }

        body.light-mode {
            background-color: #f6f8fb;
            color: #0f172a;
        }

        body.light-mode #header-bar,
        body.light-mode #analysis-panel {
            background-color: #ffffff;
            border-color: #e2e8f0;
        }

        body.light-mode #visualizer-area {
            background: linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
        }

        body.light-mode .hud-panel,
        body.light-mode .info-list,
        body.light-mode .top-account-item,
        body.light-mode blockquote.tweet-quote {
            background: rgba(255, 255, 255, 0.94);
            border-color: #dde6f0;
            color: #334155;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
        }

        body.light-mode .nav-pills {
            background-color: #eef2f7;
        }

        body.light-mode .nav-pills .nav-link {
            color: #64748b;
        }

        body.light-mode .nav-pills .nav-link.active {
            color: #0f172a;
            background-color: #ffffff;
            box-shadow: 0 1px 8px rgba(15, 23, 42, 0.08);
        }

        body.light-mode .hud-title,
        body.light-mode .info-label,
        body.light-mode .table-dark-custom th {
            color: #64748b;
            border-color: #e2e8f0;
        }

        body.light-mode .legend-item,
        body.light-mode .table-dark-custom td,
        body.light-mode #detail-narrative {
            color: #334155 !important;
        }

        body.light-mode .table-dark-custom th,
        body.light-mode .table-dark-custom td,
        body.light-mode .info-row {
            border-color: #e2e8f0;
        }

        body.light-mode .table-dark-custom tr:hover td {
            background-color: #f1f5f9;
            color: #0f172a;
        }

        body.light-mode .info-value,
        body.light-mode .text-white {
            color: #0f172a !important;
        }

        body.light-mode .text-muted {
            color: #64748b !important;
        }

        body.light-mode .keyword-badge {
            background-color: #ffffff;
            color: #334155;
            border-color: #cbd5e1;
        }

        body.light-mode .insight-note {
            background: #f8fafc;
            border-color: #dbe4ee;
            color: #334155;
        }

        body.light-mode .reason-metric,
        body.light-mode .evidence-pair {
            background: #ffffff;
            border-color: #dbe4ee;
        }

        body.light-mode .reason-label,
        body.light-mode .evidence-meta {
            color: #64748b;
        }

        body.light-mode .reason-value {
            color: #0f172a;
        }

        body.light-mode .badge.bg-secondary {
            background-color: #e2e8f0 !important;
            color: #334155 !important;
        }

        body.light-mode #selected-account-card {
            background: #f8fafc !important;
            border-color: #dbe4ee !important;
        }

        body.light-mode #node-tweet {
            background: #ffffff !important;
            color: #334155 !important;
        }
    </style>
</head>
<body class="/*BODY_CLASS*/">

<div id="app-layout">
    <!-- Header -->
    <div id="header-bar">
        <div class="d-flex align-items-center">
            <h5 class="fw-bold m-0 text-white" style="letter-spacing: -0.2px;">/*HEADER_TITLE*/</h5>
            <span class="badge bg-secondary ms-3" style="font-size: 0.7rem; font-weight:600;">/*HEADER_BADGE*/</span>
        </div>
        <div class="text-muted small" style="font-size: 0.8rem;">/*HEADER_NOTE*/</div>
    </div>
    
    <!-- Main Content -->
    <div id="main-content">
        
        <!-- Graph Area -->
        <div id="visualizer-area">
            <div id="network-canvas"></div>
            
            <!-- HUD: Legend -->
            <div id="hud-legend" class="hud-panel">
                <div class="hud-title">/*LEGEND_TITLE*/</div>
                /*LEGEND_ITEMS*/
                <div class="text-muted" style="font-size: 0.68rem; line-height:1.35; max-width: 210px;">/*LEGEND_NOTE*/</div>
            </div>
        </div>
        
        <!-- Right Analysis Panel -->
        <div id="analysis-panel">
            <div class="nav nav-pills" id="panelTabs" role="tablist">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button" role="tab" aria-controls="overview" aria-selected="true">Ikhtisar</button>
                <button class="nav-link" id="detail-tab" data-bs-toggle="tab" data-bs-target="#detail" type="button" role="tab" aria-controls="detail" aria-selected="false">Analisis Detil</button>
                <button class="nav-link" id="all-tab" data-bs-toggle="tab" data-bs-target="#all-clusters" type="button" role="tab" aria-controls="all-clusters" aria-selected="false">Kluster</button>
            </div>
            
            <div class="tab-content" id="panelTabContent">
                <!-- TAB 1: OVERVIEW -->
                <div class="tab-pane fade show active" id="overview" role="tabpanel" aria-labelledby="overview-tab">
                    <div class="insight-note">/*MODE_NOTE*/</div>
                    <div class="info-list">
                        <div class="info-row">
                            <span class="info-label">Total Akun Terdeteksi</span>
                            <span class="info-value" id="stat-nodes">0</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">/*EDGE_STAT_LABEL*/</span>
                            <span class="info-value" id="stat-edges">0</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Jumlah Kelompok</span>
                            <span class="info-value" id="stat-clusters">0</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Kluster Koordinasi Kuat</span>
                            <span class="info-value text-danger" id="stat-buzzers">0</span>
                        </div>
                    </div>
                    
                    <h6 class="hud-title mt-4">Peringkat Koordinasi Kluster</h6>
                    <table class="table-dark-custom">
                        <thead>
                            <tr>
                                <th>Kluster</th>
                                <th>Ukuran (Akun)</th>
                                <th>Skor</th>
                                <th>Fokus Narasi</th>
                            </tr>
                        </thead>
                        <tbody id="overview-table-body">
                            <!-- Injected by JS -->
                        </tbody>
                    </table>
                </div>
                
                <!-- TAB 2: DETAIL KLUSTER -->
                <div class="tab-pane fade" id="detail" role="tabpanel" aria-labelledby="detail-tab">
                    <div id="detail-empty-state">
                        <div class="text-center text-muted my-5">
                            <p class="mb-0">Pilih salah satu node pada graf atau pilih kluster pada tabel untuk menampilkan analisis kelompok.</p>
                        </div>
                    </div>
                    <div id="detail-content" style="display: none;">
                        
                        <!-- CARD 1: AKUN TERPILIH (Dinamis jika node graf di-klik) -->
                        <div id="selected-account-card" class="mb-4" style="display: none; background: rgba(56, 189, 248, 0.05); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 8px; padding: 14px 16px;">
                            <h6 class="hud-title text-info mb-2" id="account-card-title" style="border-bottom: 1px solid rgba(56, 189, 248, 0.15); padding-bottom: 4px;">Akun Terpilih</h6>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="fw-bold text-white" id="node-username">@username</span>
                                <span class="text-muted small" id="node-pagerank">PR: 0.000000</span>
                            </div>
                            <div class="d-flex flex-wrap gap-2 mb-2">
                                <span class="keyword-badge" id="node-tweet-type">Jenis tweet</span>
                                <span class="keyword-badge" id="node-rt-source" style="display:none;">Sumber RT</span>
                                <span class="keyword-badge" id="node-rt-ratio">Rasio RT akun: 0.00</span>
                            </div>
                            <blockquote class="tweet-quote mb-0" id="node-tweet" style="border-left-color: #38bdf8; background: #0f172a; margin-top: 6px;">
                                "Tweet..."
                            </blockquote>
                        </div>
                        
                        <!-- CARD 2: DETAIL METRIK KLUSTER -->
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-white m-0" id="detail-title">Kluster #0</h5>
                            <span id="detail-affiliation-badge" class="badge bg-secondary">Fokus Narasi</span>
                        </div>
                        
                        <div class="info-list">
                            <div class="info-row">
                                <span class="info-label">Skor Koordinasi</span>
                                <span class="info-value text-danger font-monospace" id="detail-score">0</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Kepadatan (Density)</span>
                                <span class="info-value font-monospace" id="detail-density">0</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Jumlah Akun</span>
                                <span class="info-value font-monospace" id="detail-size">0</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Status Koordinasi</span>
                                <span class="info-value" id="detail-status">Organik</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Bukti Pasangan</span>
                                <span class="info-value font-monospace" id="detail-evidence">0</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Komposisi Edge</span>
                                <span class="info-value font-monospace" id="detail-edge-mix">0 RT / 0 Semantik</span>
                            </div>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="hud-title">Alasan Masuk Kluster</h6>
                            <div class="insight-note mb-2" id="detail-reason-summary"></div>
                            <div class="reason-grid">
                                <div class="reason-metric">
                                    <div class="reason-label">Rata-rata Kemiripan Teks</div>
                                    <div class="reason-value" id="detail-avg-sim">0.000</div>
                                </div>
                                <div class="reason-metric">
                                    <div class="reason-label">Median Jeda Waktu</div>
                                    <div class="reason-value" id="detail-median-delta">0 detik</div>
                                </div>
                                <div class="reason-metric">
                                    <div class="reason-label">Edge Teks Sangat Mirip</div>
                                    <div class="reason-value" id="detail-strong-text">0</div>
                                </div>
                                <div class="reason-metric">
                                    <div class="reason-label">Edge <= 1 Menit</div>
                                    <div class="reason-value" id="detail-close-time">0</div>
                                </div>
                            </div>
                            <div class="text-muted small mb-2" id="detail-backbone-note"></div>
                            <div id="detail-evidence-pairs"></div>
                        </div>

                        <div class="mb-4">
                            <h6 class="hud-title">Topik Pembicaraan (Keywords)</h6>
                            <div id="detail-keywords"></div>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="hud-title">Deskripsi Analisis Narasi</h6>
                            <p class="small" id="detail-narrative" style="line-height: 1.6; color: #cbd5e1;"></p>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="hud-title">Sampel Narasi Utama</h6>
                            <div id="detail-tweets"></div>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="hud-title">Akun Sentral (PageRank)</h6>
                            <div id="detail-accounts">
                                <!-- Injected by JS -->
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- TAB 3: SEMUA KLUSTER -->
                <div class="tab-pane fade" id="all-clusters" role="tabpanel" aria-labelledby="all-tab">
                    <h6 class="hud-title">Semua Kluster Terdeteksi</h6>
                    <div id="all-clusters-list" class="d-flex flex-column gap-2">
                        <!-- Injected by JS -->
                    </div>
                </div>
            </div>
        </div>
        
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const clusterMetadata = /*CLUSTER_METADATA_JSON*/;
    const nonRtMode = /*NON_RT_MODE*/;
    
    // Payload nodes & edges
    const nodes = new vis.DataSet(/*NODES_JSON*/);
    const edges = new vis.DataSet(/*EDGES_JSON*/);
    
    const container = document.getElementById('network-canvas');
    const data = { nodes: nodes, edges: edges };
    const options = {
        nodes: {
            shape: 'dot',
            font: {
                size: 11,
                face: 'Plus Jakarta Sans',
                color: '/*NODE_LABEL_COLOR*/'
            },
            borderWidth: 0,
            borderWidthSelected: 2
        },
        edges: {
            width: 1.2,
            smooth: {
                type: 'continuous'
            }
        },
        physics: {
            enabled: true,
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {
                gravitationalConstant: -180,
                centralGravity: 0.015,
                springLength: 160,
                springConstant: 0.08,
                damping: 0.4,
                avoidOverlap: 1.0
            },
            stabilization: { 
                iterations: 400,
                fit: true
            }
        }
    };
    
    const network = new vis.Network(container, data, options);
    
    // Freeze physics once stabilization is complete
    network.on("stabilizationIterationsDone", () => {
        network.setOptions({ physics: false });
        console.log("Physics frozen.");
    });
    
    // Node selection labels
    let selectedNodeId = null;
    
    network.on("selectNode", function (params) {
        const nodeId = params.nodes[0];
        
        // Restore label of previously selected node
        if (selectedNodeId && selectedNodeId !== nodeId) {
            const oldNode = nodes.get(selectedNodeId);
            if (oldNode) {
                nodes.update({ id: selectedNodeId, label: "" });
            }
        }
        
        selectedNodeId = nodeId;
        
        // Show username label on the selected node
        nodes.update({ id: nodeId, label: "@" + nodeId });
        
        const nodeData = nodes.get(nodeId);
        if (nodeData && nodeData.community !== undefined) {
            showClusterDetail(nodeData.community, nodeData);
            const triggerEl = document.querySelector('#detail-tab');
            bootstrap.Tab.getInstance(triggerEl).show();
        }
    });
    
    network.on("deselectNode", function (params) {
        if (selectedNodeId) {
            const oldNode = nodes.get(selectedNodeId);
            if (oldNode) {
                nodes.update({ id: selectedNodeId, label: "" });
            }
            selectedNodeId = null;
        }
    });
    
    function focusCluster(clusterId) {
        const clusterNodeIds = [];
        nodes.forEach(n => {
            if (n.community === clusterId) {
                clusterNodeIds.push(n.id);
            }
        });
        
        if (clusterNodeIds.length > 0) {
            network.fit({
                nodes: clusterNodeIds,
                animation: {
                    duration: 800,
                    easingFunction: "easeInOutQuad"
                }
            });
        }
        
        showClusterDetail(clusterId, null);
        
        const triggerEl = document.querySelector('#detail-tab');
        bootstrap.Tab.getInstance(triggerEl).show();
    }
    
    function selectNodeByName(username) {
        network.selectNodes([username]);
        const position = network.getPositions([username])[username];
        if (position) {
            network.moveTo({
                position: position,
                scale: 1.2,
                animation: {
                    duration: 500,
                    easingFunction: "easeInOutQuad"
                }
            });
        }
        const nodeData = nodes.get(username);
        if (nodeData) {
            if (selectedNodeId && selectedNodeId !== username) {
                const oldNode = nodes.get(selectedNodeId);
                if (oldNode) {
                    nodes.update({ id: selectedNodeId, label: "" });
                }
            }
            selectedNodeId = username;
            nodes.update({ id: username, label: "@" + username });
            showClusterDetail(nodeData.community, nodeData);
        }
    }

    function renderAccountTweetMeta(account) {
        const tweetTypeEl = document.getElementById('node-tweet-type');
        const rtSourceEl = document.getElementById('node-rt-source');
        const rtRatioEl = document.getElementById('node-rt-ratio');

        const tweetType = account.tweet_type || 'Tidak diketahui';
        tweetTypeEl.innerText = 'Jenis: ' + tweetType;

        const rtSource = account.rt_source || '';
        if (tweetType === 'Retweet' && rtSource) {
            rtSourceEl.style.display = 'inline-block';
            rtSourceEl.innerText = 'Sumber RT: @' + rtSource;
        } else {
            rtSourceEl.style.display = 'none';
            rtSourceEl.innerText = '';
        }

        const ratio = Number(account.rt_ratio || 0);
        rtRatioEl.innerText = 'Rasio RT akun: ' + ratio.toFixed(2);
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }
    
    function showClusterDetail(cid, nodeData) {
        const meta = clusterMetadata[cid];
        if (!meta) return;
        const visualColor = meta.cluster_color || meta.affiliation_color;
        
        document.getElementById('detail-empty-state').style.display = 'none';
        document.getElementById('detail-content').style.display = 'block';
        
        // Handle specific account details card
        const accCard = document.getElementById('selected-account-card');
        const accCardTitle = document.getElementById('account-card-title');
        
        if (nodeData) {
            accCard.style.display = 'block';
            accCard.style.borderColor = visualColor + "33";
            accCard.style.backgroundColor = visualColor + "11";
            accCardTitle.style.borderBottomColor = visualColor + "33";
            accCardTitle.style.color = visualColor;
            
            document.getElementById('node-username').innerText = "@" + nodeData.id;
            document.getElementById('node-username').style.color = visualColor;
            document.getElementById('node-pagerank').innerText = "PR Score: " + nodeData.pagerank;
            renderAccountTweetMeta(nodeData);
            
            const nodeTweet = document.getElementById('node-tweet');
            nodeTweet.style.borderLeftColor = visualColor;
            nodeTweet.innerText = `"${nodeData.tweet || 'Tidak ada tweet'}"`;
        } else {
            // Default to top influencer when no specific node is selected (e.g., clicked from cluster list)
            const topInf = meta.top_accounts[0];
            if (topInf) {
                accCard.style.display = 'block';
                accCard.style.borderColor = visualColor + "33";
                accCard.style.backgroundColor = visualColor + "11";
                accCardTitle.style.borderBottomColor = visualColor + "33";
                accCardTitle.style.color = visualColor;
                
                document.getElementById('node-username').innerText = "@" + topInf.username + " (Akun Sentral)";
                document.getElementById('node-username').style.color = visualColor;
                document.getElementById('node-pagerank').innerText = "PR Score: " + topInf.pagerank;
                renderAccountTweetMeta(topInf);
                
                const nodeTweet = document.getElementById('node-tweet');
                nodeTweet.style.borderLeftColor = visualColor;
                nodeTweet.innerText = `"${topInf.tweet}"`;
            } else {
                accCard.style.display = 'none';
            }
        }
        
        // Populate cluster metadata
        document.getElementById('detail-title').innerText = "Kluster #" + cid;
        
        const badge = document.getElementById('detail-affiliation-badge');
        badge.innerText = meta.narrative_focus || meta.affiliation;
        badge.style.backgroundColor = meta.affiliation_color;
        badge.style.color = "#0f172a";
        
        document.getElementById('detail-score').innerText = meta.buzzer_score;
        document.getElementById('detail-density').innerText = meta.density;
        document.getElementById('detail-size').innerText = meta.size;
        document.getElementById('detail-evidence').innerText = meta.total_pair_matches;
        document.getElementById('detail-edge-mix').innerText = nonRtMode
            ? `0 RT / ${meta.semantic_edges} Semantik Non-RT`
            : `${meta.retweet_edges} RT / ${meta.semantic_edges} Semantik`;
        
        const statusEl = document.getElementById('detail-status');
        statusEl.innerText = meta.status;
        if (meta.status === "Koordinasi Kuat") {
            statusEl.className = 'info-value text-danger';
        } else if (meta.status === "Perlu Investigasi") {
            statusEl.className = 'info-value text-warning';
        } else if (meta.status === "Indikasi Lemah") {
            statusEl.className = 'info-value text-muted';
        } else {
            statusEl.className = 'info-value text-success';
        }

        document.getElementById('detail-reason-summary').innerText = meta.reason_summary || '-';
        document.getElementById('detail-avg-sim').innerText = Number(meta.avg_text_similarity || 0).toFixed(3);
        document.getElementById('detail-median-delta').innerText = meta.median_time_delta_label || '-';
        document.getElementById('detail-strong-text').innerText = `${meta.strong_text_edges || 0} edge`;
        document.getElementById('detail-close-time').innerText = `${meta.close_time_edges || 0} edge`;
        document.getElementById('detail-backbone-note').innerText = meta.backbone_note || '';

        const evidencePairsContainer = document.getElementById('detail-evidence-pairs');
        evidencePairsContainer.innerHTML = '';
        if (meta.evidence_pairs && meta.evidence_pairs.length > 0) {
            meta.evidence_pairs.forEach(pair => {
                const div = document.createElement('div');
                div.className = 'evidence-pair';
                div.style.borderLeftColor = meta.cluster_color || meta.affiliation_color;
                div.innerHTML = `
                    <div class="fw-bold small">@${escapeHtml(pair.source)} - @${escapeHtml(pair.target)}</div>
                    <div class="evidence-meta">Similarity ${Number(pair.avg_similarity || 0).toFixed(3)} · jeda min ${escapeHtml(pair.min_delta_label || '-')} · ${pair.evidence_count || 0} bukti pasangan</div>
                    <div class="text-muted small mt-2" style="line-height:1.45;">"${escapeHtml(pair.tweet_1 || '')}"</div>
                    <div class="text-muted small mt-1" style="line-height:1.45;">"${escapeHtml(pair.tweet_2 || '')}"</div>
                `;
                evidencePairsContainer.appendChild(div);
            });
        } else {
            evidencePairsContainer.innerText = 'Tidak ada contoh pasangan edge.';
        }
        
        const kwContainer = document.getElementById('detail-keywords');
        kwContainer.innerHTML = '';
        if (meta.keyword_list && meta.keyword_list.length > 0) {
            meta.keyword_list.forEach(kw => {
                const span = document.createElement('span');
                span.className = 'keyword-badge';
                span.innerText = kw;
                kwContainer.appendChild(span);
            });
        } else {
            kwContainer.innerText = 'N/A';
        }
        
        document.getElementById('detail-narrative').innerText = meta.narasi;
        
        const tweetContainer = document.getElementById('detail-tweets');
        tweetContainer.innerHTML = '';
        if (meta.sample_tweets && meta.sample_tweets.length > 0) {
            meta.sample_tweets.forEach(tweet => {
                const bq = document.createElement('blockquote');
                bq.className = 'tweet-quote';
                bq.style.borderLeftColor = visualColor;
                bq.innerText = `"${tweet}"`;
                tweetContainer.appendChild(bq);
            });
        } else {
            tweetContainer.innerText = 'Tidak ada sampel tweet.';
        }
        
        const accContainer = document.getElementById('detail-accounts');
        accContainer.innerHTML = '';
        if (meta.top_accounts && meta.top_accounts.length > 0) {
            meta.top_accounts.forEach(acc => {
                const div = document.createElement('div');
                div.className = 'top-account-item';
                div.innerHTML = `
                    <div class="d-flex justify-content-between font-weight-bold mb-1">
                        <span class="top-account-user" style="cursor:pointer;" onclick="selectNodeByName('${acc.username}')">@${acc.username}</span>
                        <span class="text-muted small">PR Score: ${acc.pagerank}</span>
                    </div>
                    <div class="text-muted small" style="line-height:1.4;">"${acc.tweet}"</div>
                `;
                accContainer.appendChild(div);
            });
        }
    }
    
    window.addEventListener('load', () => {
        function statusRank(status) {
            if (status === "Koordinasi Kuat") return 3;
            if (status === "Perlu Investigasi") return 2;
            if (status === "Indikasi Lemah") return 1;
            return 0;
        }
        const sortedClusters = Object.values(clusterMetadata).sort((a, b) => {
            return statusRank(b.status) - statusRank(a.status)
                || b.total_pair_matches - a.total_pair_matches
                || b.buzzer_score - a.buzzer_score;
        });
        
        const tbody = document.getElementById('overview-table-body');
        tbody.innerHTML = '';
        
        const allList = document.getElementById('all-clusters-list');
        allList.innerHTML = '';
        
        sortedClusters.forEach(c => {
            const visualColor = c.cluster_color || c.affiliation_color;
            const tr = document.createElement('tr');
            tr.onclick = () => focusCluster(c.cluster_id);
            tr.innerHTML = `
                <td class="fw-bold">#${c.cluster_id}</td>
                <td>${c.size}</td>
                <td><span class="fw-bold">${c.buzzer_score}</span></td>
                <td><span class="badge" style="background-color: ${c.affiliation_color}; color:#0f172a; font-size: 0.7rem;">${c.narrative_focus || c.affiliation}</span></td>
            `;
            tbody.appendChild(tr);
            
            const card = document.createElement('div');
            card.className = 'p-3 rounded mb-2 border-0';
            card.style.backgroundColor = nonRtMode ? '#ffffff' : 'rgba(255, 255, 255, 0.02)';
            card.style.border = nonRtMode ? '1px solid #e2e8f0' : '0';
            card.style.borderLeft = `3px solid ${visualColor}`;
            card.style.cursor = 'pointer';
            card.onclick = () => focusCluster(c.cluster_id);
            
            card.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-bold text-white small">Kluster #${c.cluster_id}</span>
                    <span class="text-muted" style="font-size: 0.75rem;">Skor: <span class="fw-bold text-white">${c.buzzer_score}</span></span>
                </div>
                <div class="small mb-2" style="color: ${c.affiliation_color}; font-size: 0.75rem; font-weight:600;">${c.narrative_focus || c.affiliation}</div>
                <div class="text-muted mb-1" style="font-size: 0.72rem;">${c.status} · ${c.total_pair_matches} bukti · ${nonRtMode ? `0 RT / ${c.semantic_edges} semantik non-RT` : `${c.retweet_edges} RT / ${c.semantic_edges} semantik`}</div>
                <div class="text-muted" style="font-size: 0.75rem;">${c.keywords}</div>
            `;
            allList.appendChild(card);
        });
        
        const tabTriggerList = [].slice.call(document.querySelectorAll('#panelTabs button'))
        tabTriggerList.forEach(function (tabTriggerEl) {
            new bootstrap.Tab(tabTriggerEl)
        });
        
        document.getElementById('stat-nodes').innerText = "/*STAT_NODES*/";
        document.getElementById('stat-edges').innerText = "/*STAT_EDGES*/";
        document.getElementById('stat-clusters').innerText = "/*STAT_CLUSTERS*/";
        document.getElementById('stat-buzzers').innerText = "/*STAT_BUZZERS*/";
    });
</script>

</body>
</html>
"""

    html_template = html_template.replace("/*HTML_TITLE*/", page_title)
    html_template = html_template.replace("/*HEADER_TITLE*/", page_title)
    html_template = html_template.replace("/*HEADER_BADGE*/", header_badge)
    html_template = html_template.replace("/*HEADER_NOTE*/", header_note)
    html_template = html_template.replace("/*MODE_NOTE*/", mode_note)
    html_template = html_template.replace("/*EDGE_STAT_LABEL*/", edge_stat_label)
    html_template = html_template.replace("/*BODY_CLASS*/", body_class)
    html_template = html_template.replace("/*NODE_LABEL_COLOR*/", node_label_color)
    html_template = html_template.replace("/*NON_RT_MODE*/", "true" if non_rt_only else "false")
    html_template = html_template.replace("/*LEGEND_TITLE*/", legend_title)
    html_template = html_template.replace("/*LEGEND_ITEMS*/", legend_items)
    html_template = html_template.replace("/*LEGEND_NOTE*/", legend_note)
    html_template = html_template.replace("/*CLUSTER_METADATA_JSON*/", json.dumps(cluster_analysis_dict))
    html_template = html_template.replace("/*NODES_JSON*/", json.dumps(nodes_json))
    html_template = html_template.replace("/*EDGES_JSON*/", json.dumps(edges_json))
    html_template = html_template.replace("/*STAT_NODES*/", str(stats['total_nodes']))
    html_template = html_template.replace("/*STAT_EDGES*/", str(stats['total_edges']))
    html_template = html_template.replace("/*STAT_CLUSTERS*/", str(stats['total_clusters']))
    html_template = html_template.replace("/*STAT_BUZZERS*/", str(stats['suspicious_clusters']))

    if output_filename is None:
        output_filename = "visualisasi_non_rt_light.html" if non_rt_only else "visualisasi_st.html"
    output_path = os.path.join(folder_path, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Dashboard Analitis Sukses Terbentuk: {output_path}")

if __name__ == "__main__":
    folder = "/home/data/kuliah/rka/tegrf/finalproject/data/DE-sample-X-capres2024/DE-sample-X-capres2024"
    generate_dashboard(folder)
