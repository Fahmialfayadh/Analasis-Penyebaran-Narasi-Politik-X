import json
import math
import os
import re
from collections import Counter

import networkx as nx
import numpy as np
import pandas as pd


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(
    PROJECT_DIR,
    "data",
    "DE-sample-X-capres2024",
    "DE-sample-X-capres2024",
)
OUTPUT_FILENAME = "visualisasi_finale.html"

WITH_RT_DEFAULTS = {
    "min_similarity": 0.65,
    "max_delta": 1800,
    "resolution": 2.0,
}
NON_RT_DEFAULTS = {
    "min_similarity": 0.75,
    "max_delta": 300,
    "resolution": 6.5,
}

PALETTE = [
    "#2563eb",
    "#dc2626",
    "#059669",
    "#7c3aed",
    "#d97706",
    "#0891b2",
    "#be123c",
    "#4f46e5",
    "#65a30d",
    "#c2410c",
    "#0f766e",
    "#9333ea",
    "#0284c7",
    "#b91c1c",
    "#16a34a",
    "#a21caf",
]

STOPWORDS = {
    "rt",
    "re",
    "retweet",
    "twit",
    "tweet",
    "https",
    "http",
    "www",
    "com",
    "co",
    "amp",
    "tco",
    "pic",
    "twitter",
    "xcom",
    "yang",
    "dan",
    "itu",
    "ini",
    "untuk",
    "dengan",
    "ada",
    "seperti",
    "dari",
    "akan",
    "bisa",
    "atau",
    "pada",
    "juga",
    "sudah",
    "telah",
    "karena",
    "saya",
    "kami",
    "mereka",
    "dia",
    "adalah",
    "bahwa",
    "tidak",
    "bukan",
    "tapi",
    "namun",
    "yg",
    "utk",
    "jd",
    "bgt",
    "dgn",
    "aja",
    "kalo",
    "kalau",
    "ga",
    "gak",
    "gue",
    "gw",
    "lu",
    "lo",
    "nya",
    "nih",
    "sih",
    "dong",
    "pak",
    "bapak",
    "mas",
    "bang",
    "bung",
    "ibu",
    "dok",
    "prof",
    "and",
    "the",
    "to",
    "of",
    "in",
    "for",
    "is",
    "are",
    "you",
    "your",
}


def truthy(value):
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def short_text(value, limit=220):
    text = clean_text(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def safe_float(value, default=0.0):
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return default
    return float(numeric)


def safe_int(value, default=0):
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return default
    return int(numeric)


def join_unique(values, limit=4):
    seen = []
    for value in values:
        if pd.isna(value):
            continue
        for part in str(value).split("|"):
            cleaned = clean_text(part)
            if cleaned and cleaned.lower() != "nan" and cleaned not in seen:
                seen.append(cleaned)
            if len(seen) >= limit:
                return " | ".join(seen)
    return " | ".join(seen)


def edge_pair_id(source, target):
    return "||".join(sorted([str(source), str(target)]))


def keyword_terms(text, limit=12):
    tokens = re.findall(r"(?u)\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", str(text).lower())
    cleaned = []
    for token in tokens:
        token = re.sub(r"[^a-zA-Z0-9_]", "", token)
        if token in STOPWORDS or len(token) <= 2:
            continue
        if token.isdigit():
            continue
        if re.match(r"^[a-z0-9]{16,}$", token) and not re.search(
            r"anies|prabowo|ganjar|mahfud|gibran|muhaimin|amin", token
        ):
            continue
        cleaned.append(token)
    return [word for word, _ in Counter(cleaned).most_common(limit)]


def focus_counts(text):
    text = str(text).lower()
    patterns = {
        "anies": r"\b(anies|baswedan|muhaimin|cak\s*imin|aminajadulu)\b",
        "prabowo": r"\b(prabowo|gibran|prabowogibran|gemoy)\b",
        "ganjar": r"\b(ganjar|mahfud|pranowo|ganjarmahfud|mahfudlebihbaik3|l3bihbaik)\b",
    }
    return {key: len(re.findall(pattern, text)) for key, pattern in patterns.items()}


def load_inputs(folder_path):
    cleaned_path = os.path.join(folder_path, "cleaned_data.csv")
    relation_path = os.path.join(folder_path, "relation.csv")
    evidence_path = os.path.join(folder_path, "relation_evidence.csv")

    for path in [cleaned_path, relation_path, evidence_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File tidak ditemukan: {path}")

    df = pd.read_csv(cleaned_path)
    relation_df = pd.read_csv(relation_path)
    evidence_df = pd.read_csv(evidence_path)
    return df, relation_df, evidence_df


def build_summary(df, relation_df, evidence_df):
    df = df.copy()
    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    df["is_retweet"] = df.get("is_retweet", False)
    df["is_retweet"] = df["is_retweet"].apply(truthy)
    df["is_reply_or_mention"] = df.get("is_reply_or_mention", False)
    df["is_reply_or_mention"] = df["is_reply_or_mention"].apply(truthy)

    date_min = df["date_created"].min()
    date_max = df["date_created"].max()
    duration_minutes = 0.0
    if pd.notna(date_min) and pd.notna(date_max):
        duration_minutes = (date_max - date_min).total_seconds() / 60

    per_query = []
    if "query_candidate" in df.columns:
        query_group = df.groupby("query_candidate").agg(
            rows=("content", "size"),
            accounts=("name", "nunique"),
            retweets=("is_retweet", "sum"),
            replies=("is_reply_or_mention", "sum"),
        )
        for query, row in query_group.sort_index().iterrows():
            per_query.append(
                {
                    "query": str(query),
                    "rows": int(row["rows"]),
                    "accounts": int(row["accounts"]),
                    "retweets": int(row["retweets"]),
                    "replies": int(row["replies"]),
                }
            )

    edge_type_counts = relation_df["Edge_Types"].fillna("N/A").value_counts().to_dict()
    evidence_counts = evidence_df["edge_type"].fillna("N/A").value_counts().to_dict()

    return {
        "total_rows": int(len(df)),
        "unique_accounts": int(df["name"].nunique()),
        "duration_minutes": round(float(duration_minutes), 2),
        "date_min": str(date_min) if pd.notna(date_min) else "N/A",
        "date_max": str(date_max) if pd.notna(date_max) else "N/A",
        "retweet_rows": int(df["is_retweet"].sum()),
        "retweet_ratio": round(float(df["is_retweet"].mean()), 4) if len(df) else 0,
        "reply_rows": int(df["is_reply_or_mention"].sum()),
        "per_query": per_query,
        "edge_type_counts": {str(k): int(v) for k, v in edge_type_counts.items()},
        "evidence_counts": {str(k): int(v) for k, v in evidence_counts.items()},
    }


def build_nodes(df):
    df = df.copy()
    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    df["content"] = df.get("content", "").fillna("")
    df["cleaned_content"] = df.get("cleaned_content", df["content"]).fillna("")
    df["topic_content"] = df.get("topic_content", df["cleaned_content"]).fillna("")
    df["is_retweet"] = df.get("is_retweet", False)
    df["is_retweet"] = df["is_retweet"].apply(truthy)
    df["query_candidate"] = df.get("query_candidate", "unknown").fillna("unknown")

    latest = (
        df.sort_values("date_created")
        .drop_duplicates(subset=["name"], keep="last")
        .set_index("name")
    )
    grouped = df.groupby("name")

    nodes = {}
    for name, group in grouped:
        query_counts = {
            str(key): int(value)
            for key, value in group["query_candidate"].value_counts().to_dict().items()
        }
        all_text = " ".join(group["content"].fillna("").astype(str).tolist())
        topic_text = " ".join(group["topic_content"].fillna("").astype(str).tolist())
        latest_row = latest.loc[name]
        nodes[str(name)] = {
            "id": str(name),
            "tweet_count": int(len(group)),
            "rt_count": int(group["is_retweet"].sum()),
            "rt_ratio": round(float(group["is_retweet"].mean()), 4) if len(group) else 0,
            "query_counts": query_counts,
            "query_context": " | ".join(sorted(query_counts.keys())),
            "focus_counts": focus_counts(all_text),
            "keywords": keyword_terms(topic_text, limit=12),
            "last_tweet": short_text(
                latest_row.get("cleaned_content") or latest_row.get("content"), limit=260
            ),
            "tweet_dates": [
                d.strftime("%Y-%m-%d %H:%M")
                for d in sorted(group["date_created"].dropna())[-5:]
            ],
            "first_tweet_time": (
                group["date_created"].min().strftime("%Y-%m-%d %H:%M")
                if pd.notna(group["date_created"].min()) else "N/A"
            ),
            "last_tweet_time": (
                group["date_created"].max().strftime("%Y-%m-%d %H:%M")
                if pd.notna(group["date_created"].max()) else "N/A"
            ),
        }
    return nodes


def normalize_edge_kind(edge_types):
    value = str(edge_types).lower()
    has_semantic = "semantic" in value
    has_retweet = "retweet" in value
    if has_semantic and has_retweet:
        return "mixed"
    if has_retweet:
        return "retweet"
    return "semantic"


def row_to_edge(row, mode):
    edge_types = row.get("Edge_Types", "semantic")
    source = str(row.get("Source"))
    target = str(row.get("Target"))
    kind = normalize_edge_kind(edge_types)
    avg_similarity = safe_float(row.get("Avg_Text_Similarity"), 1.0 if kind == "retweet" else 0.0)
    min_delta = safe_float(row.get("Min_Time_Delta_Seconds"), 0.0)
    edge_count = safe_int(row.get("Edge_Count"), 1)
    return {
        "id": f"{mode}:{edge_pair_id(source, target)}",
        "source": source,
        "target": target,
        "weight": round(safe_float(row.get("Weight"), 0.0), 6),
        "max_weight": round(safe_float(row.get("Max_Weight"), safe_float(row.get("Weight"), 0.0)), 6),
        "edge_count": edge_count,
        "avg_similarity": round(avg_similarity, 6),
        "avg_time_score": round(safe_float(row.get("Avg_Time_Score"), 0.0), 6),
        "min_delta": round(min_delta, 2),
        "edge_types": str(edge_types),
        "kind": kind,
        "dominant_rt_source": clean_text(row.get("Dominant_RT_Source", "")),
        "query_context": clean_text(row.get("Query_Context", "")),
        "tweet_1": short_text(row.get("Example_Tweet_1", ""), limit=260),
        "tweet_2": short_text(row.get("Example_Tweet_2", ""), limit=260),
    }


def aggregate_non_rt_edges(evidence_df):
    semantic_df = evidence_df[evidence_df["edge_type"].fillna("").astype(str).str.lower().eq("semantic")].copy()
    if semantic_df.empty:
        return pd.DataFrame(
            columns=[
                "Source",
                "Target",
                "Weight",
                "Max_Weight",
                "Edge_Count",
                "Avg_Text_Similarity",
                "Avg_Time_Score",
                "Min_Time_Delta_Seconds",
                "Edge_Types",
                "Dominant_RT_Source",
                "Query_Context",
                "Example_Tweet_1",
                "Example_Tweet_2",
            ]
        )

    for col in ["Weight", "s_text", "s_time", "delta_t_seconds"]:
        semantic_df[col] = pd.to_numeric(semantic_df[col], errors="coerce")

    semantic_df["query_context_joined"] = (
        semantic_df.get("query_i", "").fillna("").astype(str)
        + " | "
        + semantic_df.get("query_j", "").fillna("").astype(str)
    )

    edges_df = (
        semantic_df.groupby(["Source", "Target"])
        .agg(
            Weight=("Weight", "mean"),
            Max_Weight=("Weight", "max"),
            Edge_Count=("Weight", "size"),
            Avg_Text_Similarity=("s_text", "mean"),
            Avg_Time_Score=("s_time", "mean"),
            Min_Time_Delta_Seconds=("delta_t_seconds", "min"),
            Query_Context=("query_context_joined", lambda values: join_unique(values, limit=4)),
            Example_Tweet_1=("tweet_i", lambda values: join_unique(values, limit=2)),
            Example_Tweet_2=("tweet_j", lambda values: join_unique(values, limit=2)),
        )
        .reset_index()
    )
    edges_df["Edge_Types"] = "semantic"
    edges_df["Dominant_RT_Source"] = ""
    return edges_df.sort_values(["Edge_Count", "Weight"], ascending=[False, False]).reset_index(drop=True)


def build_communities(edge_rows, resolution):
    if not edge_rows:
        return {}
    edges_df = pd.DataFrame(
        [
            {
                "Source": edge["source"],
                "Target": edge["target"],
                "Weight": edge["weight"],
            }
            for edge in edge_rows
        ]
    )
    graph = nx.from_pandas_edgelist(edges_df, "Source", "Target", edge_attr=True)
    if graph.number_of_edges() == 0:
        return {}
    communities = nx.community.louvain_communities(
        graph,
        weight="Weight",
        resolution=resolution,
        seed=42,
    )
    ordered = sorted(communities, key=lambda group: (-len(group), sorted(group)[0]))
    community_map = {}
    for index, group in enumerate(ordered):
        for node in group:
            community_map[str(node)] = index
    return community_map


def build_layout_positions(edge_rows, community_map):
    """Create deterministic cluster-aware coordinates so filtering does not reshuffle nodes."""
    if not edge_rows:
        return {}

    graph = nx.Graph()
    for edge in edge_rows:
        graph.add_edge(edge["source"], edge["target"], Weight=edge.get("weight", 1.0))

    if graph.number_of_nodes() == 0:
        return {}

    groups = {}
    for node in graph.nodes():
        cid = int(community_map.get(str(node), -1))
        groups.setdefault(cid, []).append(str(node))

    sorted_groups = sorted(
        groups.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    cols = max(1, math.ceil(math.sqrt(len(sorted_groups) * 1.2)))
    rows = max(1, math.ceil(len(sorted_groups) / cols))
    spacing_x = 500
    spacing_y = 390

    layout = {}
    for index, (cid, nodes) in enumerate(sorted_groups):
        col = index % cols
        row = index // cols
        center_x = (col - (cols - 1) / 2) * spacing_x
        center_y = (row - (rows - 1) / 2) * spacing_y
        size = len(nodes)
        radius = max(68, min(220, 34 * math.sqrt(size)))

        if size == 1:
            layout[nodes[0]] = {"x": round(center_x, 2), "y": round(center_y, 2)}
            continue

        subgraph = graph.subgraph(nodes)
        if size <= 4 or subgraph.number_of_edges() == 0:
            local_positions = {
                node: np.array(
                    [
                        math.cos((2 * math.pi * i) / size),
                        math.sin((2 * math.pi * i) / size),
                    ]
                )
                for i, node in enumerate(sorted(nodes))
            }
        else:
            local_positions = nx.spring_layout(
                subgraph,
                weight="Weight",
                seed=42 + max(cid, 0),
                iterations=160,
            )

        xs = np.array([pos[0] for pos in local_positions.values()], dtype=float)
        ys = np.array([pos[1] for pos in local_positions.values()], dtype=float)
        x_mid = float((xs.min() + xs.max()) / 2)
        y_mid = float((ys.min() + ys.max()) / 2)
        span = float(max(xs.max() - xs.min(), ys.max() - ys.min(), 1e-9))

        for node, pos in local_positions.items():
            layout[str(node)] = {
                "x": round(center_x + ((float(pos[0]) - x_mid) / span) * radius * 2, 2),
                "y": round(center_y + ((float(pos[1]) - y_mid) / span) * radius * 2, 2),
            }

    return layout


def build_mode_payload(relation_df, evidence_df):
    with_rt_edges = [row_to_edge(row, "with_rt") for _, row in relation_df.iterrows()]

    non_rt_df = aggregate_non_rt_edges(evidence_df)
    non_rt_edges = [row_to_edge(row, "non_rt") for _, row in non_rt_df.iterrows()]

    with_rt_communities = build_communities(with_rt_edges, WITH_RT_DEFAULTS["resolution"])
    non_rt_communities = build_communities(non_rt_edges, NON_RT_DEFAULTS["resolution"])
    with_rt_positions = build_layout_positions(with_rt_edges, with_rt_communities)
    non_rt_positions = build_layout_positions(non_rt_edges, non_rt_communities)

    return {
        "with_rt": {
            "label": "Dengan RT",
            "description": "Semantic + shared-retweet",
            "defaults": WITH_RT_DEFAULTS,
            "edges": with_rt_edges,
            "communities": with_rt_communities,
            "positions": with_rt_positions,
        },
        "non_rt": {
            "label": "Tanpa RT",
            "description": "Semantic non-retweet",
            "defaults": NON_RT_DEFAULTS,
            "edges": non_rt_edges,
            "communities": non_rt_communities,
            "positions": non_rt_positions,
        },
    }


def sensitivity_reference(evidence_df):
    semantic = evidence_df[evidence_df["edge_type"].fillna("").astype(str).str.lower().eq("semantic")].copy()
    semantic["s_text"] = pd.to_numeric(semantic.get("s_text"), errors="coerce")
    semantic["delta_t_seconds"] = pd.to_numeric(semantic.get("delta_t_seconds"), errors="coerce")

    thresholds = []
    for value in [0.65, 0.75, 0.85, 0.95, 1.0]:
        thresholds.append({"label": f">= {value:.2f}", "count": int((semantic["s_text"] >= value).sum())})

    windows = []
    for seconds in [60, 300, 600, 1800]:
        windows.append({"label": f"<= {seconds}s", "count": int((semantic["delta_t_seconds"] <= seconds).sum())})

    return {"similarity": thresholds, "time": windows}


def js_json(data):
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_html(payload):
    data_json = js_json(payload)
    palette_json = js_json(PALETTE)
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Finale Analisis Koordinasi Narasi Politik</title>
    <link rel="icon" href="data:,">
    <link rel="stylesheet" href="../../../lib/vis-9.1.2/vis-network.css">
    <script src="../../../lib/vis-9.1.2/vis-network.min.js"></script>
    <style>
        :root {{
            --bg: #f6f8fb;
            --panel: #ffffff;
            --panel-soft: #eef3f8;
            --ink: #111827;
            --muted: #64748b;
            --line: #dbe4ee;
            --accent: #2563eb;
            --semantic: #0891b2;
            --retweet: #d97706;
            --mixed: #7c3aed;
            --good: #059669;
            --warn: #d97706;
            --strong: #dc2626;
            --shadow: 0 16px 36px rgba(15, 23, 42, 0.10);
        }}

        * {{ box-sizing: border-box; }}

        body {{
            margin: 0;
            min-height: 100vh;
            background: var(--bg);
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            letter-spacing: 0;
        }}

        button, input {{
            font: inherit;
        }}

        #app {{
            display: grid;
            grid-template-rows: auto auto 1fr;
            height: 100vh;
            min-height: 720px;
        }}

        .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
            padding: 16px 22px;
            background: var(--panel);
            border-bottom: 1px solid var(--line);
        }}

        .brand-title {{
            margin: 0;
            font-size: 1.08rem;
            line-height: 1.25;
            font-weight: 750;
        }}

        .brand-subtitle {{
            margin-top: 3px;
            color: var(--muted);
            font-size: 0.82rem;
        }}

        .mode-switch {{
            display: inline-flex;
            background: var(--panel-soft);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 3px;
        }}

        .mode-btn {{
            border: 0;
            background: transparent;
            color: var(--muted);
            border-radius: 6px;
            padding: 8px 13px;
            font-weight: 700;
            cursor: pointer;
        }}

        .mode-btn.active {{
            background: var(--panel);
            color: var(--ink);
            box-shadow: 0 1px 8px rgba(15, 23, 42, 0.08);
        }}

        .summary-strip {{
            display: grid;
            grid-template-columns: repeat(8, minmax(0, 1fr));
            gap: 1px;
            background: var(--line);
            border-bottom: 1px solid var(--line);
        }}

        .summary-cell {{
            background: var(--panel);
            padding: 12px 16px;
            min-width: 0;
        }}

        .summary-label {{
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .summary-value {{
            margin-top: 3px;
            font-size: 1.08rem;
            font-weight: 780;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .workspace {{
            display: grid;
            grid-template-columns: minmax(420px, 1fr) 430px;
            min-height: 0;
        }}

        .graph-wrap {{
            position: relative;
            min-height: 0;
            background: linear-gradient(180deg, #f8fafc 0%, #edf3f8 100%);
        }}

        #network {{
            width: 100%;
            height: 100%;
        }}

        .control-panel {{
            position: absolute;
            top: 18px;
            left: 18px;
            width: min(560px, calc(100% - 36px));
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 13px 14px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(10px);
        }}

        .control-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }}

        .range-label {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
        }}

        .range-value {{
            color: var(--ink);
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }}

        input[type="range"] {{
            width: 100%;
            accent-color: var(--accent);
            margin-top: 8px;
        }}

        .mini-note {{
            margin-top: 10px;
            color: var(--muted);
            font-size: 0.76rem;
            line-height: 1.45;
        }}

        .legend {{
            position: absolute;
            left: 18px;
            bottom: 18px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px 12px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
        }}

        .legend-item {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 700;
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 999px;
        }}

        .side {{
            min-height: 0;
            background: var(--panel);
            border-left: 1px solid var(--line);
            display: grid;
            grid-template-rows: auto auto 1fr;
            overflow: hidden;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1px;
            background: var(--line);
            border-bottom: 1px solid var(--line);
        }}

        .stat {{
            background: var(--panel);
            padding: 13px 16px;
        }}

        .stat-label {{
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 750;
        }}

        .stat-value {{
            margin-top: 3px;
            font-size: 1.16rem;
            font-weight: 800;
        }}

        .tabs {{
            display: flex;
            gap: 6px;
            padding: 12px 14px 10px;
            border-bottom: 1px solid var(--line);
        }}

        .tab-btn {{
            flex: 1;
            border: 1px solid var(--line);
            border-radius: 7px;
            background: var(--panel-soft);
            color: var(--muted);
            padding: 8px 10px;
            font-weight: 750;
            cursor: pointer;
        }}

        .tab-btn.active {{
            background: var(--ink);
            color: white;
            border-color: var(--ink);
        }}

        .panel-scroll {{
            min-height: 0;
            overflow-y: auto;
            padding: 14px;
        }}

        .cluster-list {{
            display: grid;
            gap: 8px;
        }}

        .cluster-row {{
            border: 1px solid var(--line);
            border-left-width: 4px;
            border-radius: 8px;
            padding: 11px 12px;
            background: var(--panel);
            cursor: pointer;
        }}

        .cluster-row.active {{
            outline: 2px solid rgba(37, 99, 235, 0.22);
            border-color: #bfdbfe;
            background: #f8fbff;
        }}

        .row-top {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            align-items: center;
        }}

        .cluster-name {{
            font-weight: 800;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 3px 8px;
            background: var(--panel-soft);
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 800;
        }}

        .badge.strong {{ color: #991b1b; background: #fee2e2; }}
        .badge.warn {{ color: #92400e; background: #fef3c7; }}
        .badge.ok {{ color: #065f46; background: #d1fae5; }}

        .row-meta {{
            margin-top: 7px;
            color: var(--muted);
            font-size: 0.76rem;
            line-height: 1.45;
        }}

        .detail-title {{
            margin: 0 0 8px;
            font-size: 1.02rem;
        }}

        .detail-sub {{
            color: var(--muted);
            font-size: 0.82rem;
            line-height: 1.5;
            margin-bottom: 12px;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin: 12px 0;
        }}

        .metric {{
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px 11px;
            background: #fbfdff;
        }}

        .metric-label {{
            color: var(--muted);
            font-size: 0.70rem;
            font-weight: 750;
        }}

        .metric-value {{
            margin-top: 3px;
            font-size: 0.96rem;
            font-weight: 800;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }}

        .chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 8px 0 14px;
        }}

        .chip {{
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 4px 8px;
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 750;
            background: var(--panel);
        }}

        .evidence {{
            border: 1px solid var(--line);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            padding: 10px 11px;
            margin-bottom: 8px;
            background: #fbfdff;
        }}

        .evidence-pair {{
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 5px;
        }}

        .evidence-text {{
            color: #334155;
            font-size: 0.76rem;
            line-height: 1.45;
            margin-top: 6px;
        }}

        .empty {{
            color: var(--muted);
            border: 1px dashed var(--line);
            border-radius: 8px;
            padding: 18px;
            text-align: center;
            font-size: 0.85rem;
        }}

        .table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
        }}

        .table th, .table td {{
            border-bottom: 1px solid var(--line);
            padding: 8px 6px;
            text-align: left;
        }}

        .table th {{
            color: var(--muted);
            font-weight: 800;
        }}

        .bar-row {{
            display: grid;
            grid-template-columns: 66px 1fr 46px;
            gap: 8px;
            align-items: center;
            margin: 8px 0;
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 750;
        }}

        .bar-track {{
            height: 8px;
            background: var(--panel-soft);
            border-radius: 999px;
            overflow: hidden;
        }}

        .bar-fill {{
            height: 100%;
            background: var(--accent);
        }}

        @media (max-width: 980px) {{
            #app {{
                height: auto;
                min-height: 100vh;
            }}

            .summary-strip {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .workspace {{
                grid-template-columns: 1fr;
            }}

            .graph-wrap {{
                height: 68vh;
                min-height: 560px;
            }}

            .side {{
                border-left: 0;
                border-top: 1px solid var(--line);
            }}
        }}
    </style>
</head>
<body>
    <div id="app">
        <header class="topbar">
            <div>
                <h1 class="brand-title">Finale Analisis Koordinasi Narasi Politik</h1>
                <div class="brand-subtitle">Graf interaktif dari output CSV project, dengan mode RT dan Non-RT.</div>
            </div>
            <div class="mode-switch" aria-label="Mode analisis">
                <button class="mode-btn active" id="mode-with-rt" type="button">Dengan RT</button>
                <button class="mode-btn" id="mode-non-rt" type="button">Tanpa RT</button>
            </div>
        </header>

        <section class="summary-strip">
            <div class="summary-cell"><div class="summary-label">Tweet</div><div class="summary-value" id="sum-tweets">0</div></div>
            <div class="summary-cell"><div class="summary-label">Akun Unik</div><div class="summary-value" id="sum-accounts">0</div></div>
            <div class="summary-cell"><div class="summary-label">Rentang</div><div class="summary-value" id="sum-duration">0 menit</div></div>
            <div class="summary-cell"><div class="summary-label">Rasio RT</div><div class="summary-value" id="sum-rt">0%</div></div>
            <div class="summary-cell"><div class="summary-label">Edge Semantic</div><div class="summary-value" id="sum-semantic">0</div></div>
            <div class="summary-cell"><div class="summary-label">Edge RT</div><div class="summary-value" id="sum-retweet">0</div></div>
            <div class="summary-cell"><div class="summary-label">Evidence Semantic</div><div class="summary-value" id="sum-ev-semantic">0</div></div>
            <div class="summary-cell"><div class="summary-label">Evidence RT</div><div class="summary-value" id="sum-ev-rt">0</div></div>
        </section>

        <main class="workspace">
            <section class="graph-wrap">
                <div id="network"></div>
                <div class="control-panel">
                    <div class="control-grid">
                        <label>
                            <div class="range-label">
                                <span>Minimum similarity</span>
                                <span class="range-value" id="sim-value">0.75</span>
                            </div>
                            <input id="sim-slider" type="range" min="0.65" max="1" step="0.01" value="0.75">
                        </label>
                        <label>
                            <div class="range-label">
                                <span>Maks. jeda waktu</span>
                                <span class="range-value" id="time-value">300 detik</span>
                            </div>
                            <input id="time-slider" type="range" min="0" max="1800" step="30" value="300">
                        </label>
                    </div>
                    <div class="mini-note" id="mode-note"></div>
                </div>
                <div class="legend">
                    <div class="legend-item"><span class="legend-dot" style="background: var(--semantic);"></span>Semantic</div>
                    <div class="legend-item"><span class="legend-dot" style="background: var(--retweet);"></span>Retweet</div>
                    <div class="legend-item"><span class="legend-dot" style="background: var(--mixed);"></span>Mixed</div>
                    <div class="legend-item"><span class="legend-dot" style="background: #94a3b8;"></span>Lintas kluster</div>
                </div>
            </section>

            <aside class="side">
                <div class="stats-grid">
                    <div class="stat"><div class="stat-label">Node Tampil</div><div class="stat-value" id="stat-nodes">0</div></div>
                    <div class="stat"><div class="stat-label">Edge Tampil</div><div class="stat-value" id="stat-edges">0</div></div>
                    <div class="stat"><div class="stat-label">Kluster Tampil</div><div class="stat-value" id="stat-clusters">0</div></div>
                    <div class="stat"><div class="stat-label">Koordinasi Kuat</div><div class="stat-value" id="stat-strong">0</div></div>
                </div>
                <nav class="tabs">
                    <button class="tab-btn active" data-tab="clusters" type="button">Kluster</button>
                    <button class="tab-btn" data-tab="detail" type="button">Detail</button>
                    <button class="tab-btn" data-tab="data" type="button">Data</button>
                </nav>
                <div class="panel-scroll" id="tab-clusters"><div class="cluster-list" id="cluster-list"></div></div>
                <div class="panel-scroll" id="tab-detail" hidden><div id="detail-panel"></div></div>
                <div class="panel-scroll" id="tab-data" hidden>
                    <h2 class="detail-title">Ringkasan Data</h2>
                    <div class="detail-sub" id="data-window"></div>
                    <table class="table" id="query-table"></table>
                    <h2 class="detail-title" style="margin-top: 18px;">Referensi Sensitivitas</h2>
                    <div id="sensitivity-bars"></div>
                </div>
            </aside>
        </main>
    </div>

    <script>
        const DATA = {data_json};
        const PALETTE = {palette_json};

        const state = {{
            mode: "with_rt",
            minSim: DATA.modes.with_rt.defaults.min_similarity,
            maxDelta: DATA.modes.with_rt.defaults.max_delta,
            selectedCommunity: null,
            activeTab: "clusters"
        }};

        let network = null;
        let latestClusters = [];
        let latestNodeIds = new Set();
        let latestEdges = [];

        const els = {{
            simSlider: document.getElementById("sim-slider"),
            timeSlider: document.getElementById("time-slider"),
            simValue: document.getElementById("sim-value"),
            timeValue: document.getElementById("time-value"),
            modeNote: document.getElementById("mode-note"),
            clusterList: document.getElementById("cluster-list"),
            detailPanel: document.getElementById("detail-panel")
        }};

        function fmtNumber(value) {{
            return Number(value || 0).toLocaleString("id-ID");
        }}

        function fmtPct(value) {{
            return `${{(Number(value || 0) * 100).toFixed(1)}}%`;
        }}

        function fmtDelta(seconds) {{
            const value = Number(seconds || 0);
            if (value < 60) return `${{Math.round(value)}} detik`;
            return `${{(value / 60).toFixed(1)}} menit`;
        }}

        function median(values) {{
            if (!values.length) return 0;
            const sorted = values.slice().sort((a, b) => a - b);
            const mid = Math.floor(sorted.length / 2);
            if (sorted.length % 2) return sorted[mid];
            return (sorted[mid - 1] + sorted[mid]) / 2;
        }}

        function statusFor(size, density, evidence) {{
            const score = density * Math.log2(size + 1);
            if (size < 5 || evidence < 5) return {{ label: "Indikasi Lemah", rank: 1, score }};
            if (score >= 1.5) return {{ label: "Koordinasi Kuat", rank: 3, score }};
            if (score >= 0.8) return {{ label: "Perlu Investigasi", rank: 2, score }};
            return {{ label: "Rendah", rank: 0, score }};
        }}

        function focusLabel(counts) {{
            const labels = {{
                anies: "Dominan membahas Anies-Muhaimin",
                prabowo: "Dominan membahas Prabowo-Gibran",
                ganjar: "Dominan membahas Ganjar-Mahfud"
            }};
            const entries = Object.entries(counts);
            const total = entries.reduce((sum, [, value]) => sum + value, 0);
            if (!total) return "Tanpa kandidat dominan";
            entries.sort((a, b) => b[1] - a[1]);
            const [topKey, topValue] = entries[0];
            if (topValue >= 2 && topValue / total >= 0.6) return labels[topKey];
            return "Lintas kandidat / perbandingan";
        }}

        function communityOf(nodeId) {{
            const map = DATA.modes[state.mode].communities || {{}};
            return Object.prototype.hasOwnProperty.call(map, nodeId) ? map[nodeId] : -1;
        }}

        function communityColor(communityId) {{
            if (communityId < 0) return "#94a3b8";
            return PALETTE[communityId % PALETTE.length];
        }}

        function filteredEdges() {{
            return DATA.modes[state.mode].edges.filter(edge => {{
                return edge.avg_similarity >= state.minSim && edge.min_delta <= state.maxDelta;
            }});
        }}

        function computeClusters(edges) {{
            const byCommunity = new Map();
            const visibleNodes = new Set();
            const crossEdges = [];

            for (const edge of edges) {{
                visibleNodes.add(edge.source);
                visibleNodes.add(edge.target);
                const sc = communityOf(edge.source);
                const tc = communityOf(edge.target);
                for (const [nodeId, cid] of [[edge.source, sc], [edge.target, tc]]) {{
                    if (!byCommunity.has(cid)) {{
                        byCommunity.set(cid, {{ id: cid, nodes: new Set(), edges: [], cross: 0 }});
                    }}
                    byCommunity.get(cid).nodes.add(nodeId);
                }}
                if (sc === tc) {{
                    byCommunity.get(sc).edges.push(edge);
                }} else {{
                    crossEdges.push(edge);
                    if (byCommunity.has(sc)) byCommunity.get(sc).cross += 1;
                    if (byCommunity.has(tc)) byCommunity.get(tc).cross += 1;
                }}
            }}

            const clusters = [];
            for (const raw of byCommunity.values()) {{
                if (raw.id < 0 || raw.nodes.size < 2 || raw.edges.length === 0) continue;
                const size = raw.nodes.size;
                const possible = size * (size - 1) / 2;
                const density = possible ? raw.edges.length / possible : 0;
                const evidence = raw.edges.reduce((sum, edge) => sum + edge.edge_count, 0);
                const avgSim = raw.edges.reduce((sum, edge) => sum + edge.avg_similarity, 0) / raw.edges.length;
                const avgWeight = raw.edges.reduce((sum, edge) => sum + edge.weight, 0) / raw.edges.length;
                const deltas = raw.edges.map(edge => edge.min_delta);
                const rtEdges = raw.edges.filter(edge => edge.kind === "retweet").length;
                const semanticEdges = raw.edges.filter(edge => edge.kind === "semantic").length;
                const mixedEdges = raw.edges.filter(edge => edge.kind === "mixed").length;
                const status = statusFor(size, density, evidence);
                const focusCounts = {{ anies: 0, prabowo: 0, ganjar: 0 }};
                const keywordCounter = new Map();
                const topAccounts = [];

                for (const nodeId of raw.nodes) {{
                    const node = DATA.nodes[nodeId];
                    if (!node) continue;
                    for (const key of Object.keys(focusCounts)) {{
                        focusCounts[key] += Number(node.focus_counts?.[key] || 0);
                    }}
                    for (const keyword of node.keywords || []) {{
                        keywordCounter.set(keyword, (keywordCounter.get(keyword) || 0) + 1);
                    }}
                    topAccounts.push(node);
                }}

                const keywords = Array.from(keywordCounter.entries())
                    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
                    .slice(0, 6)
                    .map(([keyword]) => keyword);

                const rankedEdges = raw.edges.slice().sort((a, b) => {{
                    return b.edge_count - a.edge_count || b.avg_similarity - a.avg_similarity || b.weight - a.weight;
                }});

                topAccounts.sort((a, b) => b.tweet_count - a.tweet_count || b.rt_ratio - a.rt_ratio);

                clusters.push({{
                    id: raw.id,
                    color: communityColor(raw.id),
                    size,
                    density,
                    evidence,
                    edgeCount: raw.edges.length,
                    avgSim,
                    avgWeight,
                    medianDelta: median(deltas),
                    rtEdges,
                    semanticEdges,
                    mixedEdges,
                    crossEdges: raw.cross,
                    status: status.label,
                    rank: status.rank,
                    score: status.score,
                    focus: focusLabel(focusCounts),
                    keywords,
                    nodes: Array.from(raw.nodes),
                    examples: rankedEdges.slice(0, 3),
                    topAccounts: topAccounts.slice(0, 5)
                }});
            }}

            clusters.sort((a, b) => b.rank - a.rank || b.score - a.score || b.evidence - a.evidence);
            return {{ clusters, visibleNodes, crossEdges }};
        }}

        function renderGraph(edges, visibleNodes) {{
            const degree = new Map();
            for (const edge of edges) {{
                degree.set(edge.source, (degree.get(edge.source) || 0) + edge.edge_count);
                degree.set(edge.target, (degree.get(edge.target) || 0) + edge.edge_count);
            }}

            const nodes = Array.from(visibleNodes).map(nodeId => {{
                const node = DATA.nodes[nodeId] || {{ id: nodeId }};
                const community = communityOf(nodeId);
                const color = communityColor(community);
                const active = state.selectedCommunity === null || community === state.selectedCommunity;
                const strength = degree.get(nodeId) || 1;
                return {{
                    id: nodeId,
                    label: active && state.selectedCommunity !== null ? `@${{nodeId}}` : "",
                    title: `<b>@${{nodeId}}</b><br>Tweet: ${{node.tweet_count || 0}}<br>Rasio RT: ${{((node.rt_ratio || 0) * 100).toFixed(1)}}%<br>Query: ${{node.query_context || "-"}}<br><br>${{node.last_tweet || ""}}`,
                    size: Math.min(34, 10 + Math.log2(strength + 1) * 4),
                    color: {{
                        background: color,
                        border: active ? "#0f172a" : color,
                        highlight: {{ background: color, border: "#0f172a" }}
                    }},
                    font: {{ size: 12, color: "#0f172a", face: "Inter, sans-serif" }},
                    borderWidth: active ? 2 : 1,
                    opacity: active ? 1 : 0.22,
                    community
                }};
            }});

            const edgeColor = edge => {{
                if (communityOf(edge.source) !== communityOf(edge.target)) return "#94a3b8";
                if (edge.kind === "retweet") return "#d97706";
                if (edge.kind === "mixed") return "#7c3aed";
                return "#0891b2";
            }};

            const visEdges = edges.map(edge => {{
                const cross = communityOf(edge.source) !== communityOf(edge.target);
                return {{
                    id: edge.id,
                    from: edge.source,
                    to: edge.target,
                    value: Math.max(1, Math.min(5, Math.log2(edge.edge_count + 1) * Math.max(1, edge.weight))),
                    title: `<b>${{edge.edge_types}}</b><br>Bukti: ${{edge.edge_count}}<br>Similarity: ${{edge.avg_similarity.toFixed(3)}}<br>Jeda min: ${{fmtDelta(edge.min_delta)}}${{edge.dominant_rt_source ? `<br>Sumber RT: @${{edge.dominant_rt_source}}` : ""}}`,
                    color: {{ color: edgeColor(edge), opacity: cross ? 0.24 : 0.46 }},
                    dashes: cross,
                    smooth: {{ type: "continuous" }}
                }};
            }});

            const data = {{
                nodes: new vis.DataSet(nodes),
                edges: new vis.DataSet(visEdges)
            }};

            const options = {{
                autoResize: true,
                nodes: {{
                    shape: "dot",
                    scaling: {{ min: 8, max: 36 }}
                }},
                edges: {{
                    width: 1,
                    selectionWidth: 1.5
                }},
                physics: {{
                    enabled: true,
                    solver: "forceAtlas2Based",
                    forceAtlas2Based: {{
                        gravitationalConstant: -58,
                        centralGravity: 0.018,
                        springLength: 112,
                        springConstant: 0.08
                    }},
                    stabilization: {{ iterations: 130, fit: true }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 80,
                    hideEdgesOnDrag: true
                }}
            }};

            if (network) network.destroy();
            network = new vis.Network(document.getElementById("network"), data, options);
            network.on("click", params => {{
                if (params.nodes.length) {{
                    const nodeId = params.nodes[0];
                    const cid = communityOf(nodeId);
                    focusCommunity(cid, false);
                }}
            }});
        }}

        function badgeClass(status) {{
            if (status === "Koordinasi Kuat") return "badge strong";
            if (status === "Perlu Investigasi") return "badge warn";
            if (status === "Rendah") return "badge ok";
            return "badge";
        }}

        function renderClusterList(clusters) {{
            if (!clusters.length) {{
                els.clusterList.innerHTML = `<div class="empty">Tidak ada kluster yang lolos filter saat ini.</div>`;
                return;
            }}

            els.clusterList.innerHTML = clusters.map(cluster => `
                <article class="cluster-row ${{cluster.id === state.selectedCommunity ? "active" : ""}}" data-community="${{cluster.id}}" style="border-left-color: ${{cluster.color}}">
                    <div class="row-top">
                        <div class="cluster-name">Kluster #${{cluster.id}}</div>
                        <span class="${{badgeClass(cluster.status)}}">${{cluster.status}}</span>
                    </div>
                    <div class="row-meta">
                        ${{cluster.size}} akun · ${{cluster.edgeCount}} edge · ${{cluster.evidence}} bukti · skor ${{cluster.score.toFixed(3)}}<br>
                        ${{cluster.focus}}<br>
                        ${{cluster.keywords.length ? cluster.keywords.join(", ") : "keyword tidak dominan"}}
                    </div>
                </article>
            `).join("");

            document.querySelectorAll(".cluster-row").forEach(row => {{
                row.addEventListener("click", () => focusCommunity(Number(row.dataset.community), true));
            }});
        }}

        function renderDetail(cluster) {{
            if (!cluster) {{
                els.detailPanel.innerHTML = `<div class="empty">Pilih kluster untuk melihat detail.</div>`;
                return;
            }}

            const edgeBreakdown = state.mode === "non_rt"
                ? `${{cluster.semanticEdges}} semantic non-RT`
                : `${{cluster.semanticEdges}} semantic · ${{cluster.rtEdges}} RT · ${{cluster.mixedEdges}} mixed`;

            const evidenceHtml = cluster.examples.map(edge => `
                <div class="evidence">
                    <div class="evidence-pair">@${{edge.source}} - @${{edge.target}}</div>
                    <span class="badge">${{edge.edge_types}}</span>
                    <span class="badge">sim ${{edge.avg_similarity.toFixed(3)}}</span>
                    <span class="badge">${{fmtDelta(edge.min_delta)}}</span>
                    <span class="badge">${{edge.edge_count}} bukti</span>
                    <div class="evidence-text">${{edge.tweet_1 || "-"}}</div>
                    <div class="evidence-text">${{edge.tweet_2 || "-"}}</div>
                </div>
            `).join("");

            const accountsHtml = cluster.topAccounts.map(node => `
                <div class="evidence">
                    <div class="evidence-pair">@${{node.id}}</div>
                    <span class="badge">tweet ${{node.tweet_count}}</span>
                    <span class="badge">RT ${{fmtPct(node.rt_ratio)}}</span>
                    <div class="evidence-text">${{node.last_tweet || "-"}}</div>
                </div>
            `).join("");

            els.detailPanel.innerHTML = `
                <h2 class="detail-title">Kluster #${{cluster.id}}</h2>
                <div class="detail-sub">${{cluster.focus}}. ${{cluster.status}} berdasarkan density, ukuran kluster, dan jumlah bukti edge yang masih lolos filter.</div>
                <div class="chips">
                    ${{cluster.keywords.map(keyword => `<span class="chip">${{keyword}}</span>`).join("") || `<span class="chip">keyword tidak dominan</span>`}}
                </div>
                <div class="metric-grid">
                    <div class="metric"><div class="metric-label">Akun</div><div class="metric-value">${{cluster.size}}</div></div>
                    <div class="metric"><div class="metric-label">Density</div><div class="metric-value">${{cluster.density.toFixed(4)}}</div></div>
                    <div class="metric"><div class="metric-label">Skor</div><div class="metric-value">${{cluster.score.toFixed(4)}}</div></div>
                    <div class="metric"><div class="metric-label">Evidence</div><div class="metric-value">${{cluster.evidence}}</div></div>
                    <div class="metric"><div class="metric-label">Avg Similarity</div><div class="metric-value">${{cluster.avgSim.toFixed(3)}}</div></div>
                    <div class="metric"><div class="metric-label">Median Jeda</div><div class="metric-value">${{fmtDelta(cluster.medianDelta)}}</div></div>
                </div>
                <div class="detail-sub">${{edgeBreakdown}}. Edge lintas kluster yang masih terlihat: ${{cluster.crossEdges}}.</div>
                <h2 class="detail-title">Bukti Pasangan</h2>
                ${{evidenceHtml || `<div class="empty">Tidak ada contoh edge.</div>`}}
                <h2 class="detail-title" style="margin-top: 16px;">Akun Sentral Ringkas</h2>
                ${{accountsHtml || `<div class="empty">Tidak ada akun.</div>`}}
            `;
        }}

        function focusCommunity(communityId, switchTab) {{
            state.selectedCommunity = communityId;
            renderClusterList(latestClusters);
            renderDetail(latestClusters.find(cluster => cluster.id === communityId));
            renderGraph(latestEdges, latestNodeIds);
            if (network && communityId !== null) {{
                const cluster = latestClusters.find(item => item.id === communityId);
                if (cluster) {{
                    network.selectNodes(cluster.nodes);
                    network.fit({{ nodes: cluster.nodes, animation: {{ duration: 450, easingFunction: "easeInOutQuad" }} }});
                }}
            }}
            if (switchTab) activateTab("detail");
        }}

        function renderStats(clusters, nodeCount, edgeCount) {{
            document.getElementById("stat-nodes").textContent = fmtNumber(nodeCount);
            document.getElementById("stat-edges").textContent = fmtNumber(edgeCount);
            document.getElementById("stat-clusters").textContent = fmtNumber(clusters.length);
            document.getElementById("stat-strong").textContent = fmtNumber(clusters.filter(c => c.status === "Koordinasi Kuat").length);
        }}

        function renderModeNote() {{
            const mode = DATA.modes[state.mode];
            const base = state.mode === "with_rt"
                ? "Mode ini memakai edge semantic dan shared-retweet yang sudah dipisahkan tipe relasinya."
                : "Mode ini hanya memakai edge semantic dari tweet non-retweet.";
            els.modeNote.textContent = `${{base}} Filter aktif: similarity >= ${{state.minSim.toFixed(2)}} dan jeda <= ${{fmtDelta(state.maxDelta)}}.`;
        }}

        function render() {{
            els.simValue.textContent = state.minSim.toFixed(2);
            els.timeValue.textContent = fmtDelta(state.maxDelta);
            renderModeNote();

            latestEdges = filteredEdges();
            const computed = computeClusters(latestEdges);
            latestClusters = computed.clusters;
            latestNodeIds = computed.visibleNodes;

            if (state.selectedCommunity !== null && !latestClusters.some(c => c.id === state.selectedCommunity)) {{
                state.selectedCommunity = null;
            }}
            if (state.selectedCommunity === null && latestClusters.length) {{
                state.selectedCommunity = latestClusters[0].id;
            }}

            renderStats(latestClusters, latestNodeIds.size, latestEdges.length);
            renderClusterList(latestClusters);
            renderDetail(latestClusters.find(cluster => cluster.id === state.selectedCommunity));
            renderGraph(latestEdges, latestNodeIds);
        }}

        function setMode(mode) {{
            state.mode = mode;
            state.minSim = DATA.modes[mode].defaults.min_similarity;
            state.maxDelta = DATA.modes[mode].defaults.max_delta;
            state.selectedCommunity = null;
            els.simSlider.value = state.minSim;
            els.timeSlider.value = state.maxDelta;
            document.getElementById("mode-with-rt").classList.toggle("active", mode === "with_rt");
            document.getElementById("mode-non-rt").classList.toggle("active", mode === "non_rt");
            render();
        }}

        function activateTab(tab) {{
            state.activeTab = tab;
            document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.tab === tab));
            document.getElementById("tab-clusters").hidden = tab !== "clusters";
            document.getElementById("tab-detail").hidden = tab !== "detail";
            document.getElementById("tab-data").hidden = tab !== "data";
        }}

        function renderSummary() {{
            const s = DATA.summary;
            document.getElementById("sum-tweets").textContent = fmtNumber(s.total_rows);
            document.getElementById("sum-accounts").textContent = fmtNumber(s.unique_accounts);
            document.getElementById("sum-duration").textContent = `${{s.duration_minutes}} menit`;
            document.getElementById("sum-rt").textContent = fmtPct(s.retweet_ratio);
            document.getElementById("sum-semantic").textContent = fmtNumber(s.edge_type_counts.semantic || 0);
            document.getElementById("sum-retweet").textContent = fmtNumber(s.edge_type_counts.retweet || 0);
            document.getElementById("sum-ev-semantic").textContent = fmtNumber(s.evidence_counts.semantic || 0);
            document.getElementById("sum-ev-rt").textContent = fmtNumber(s.evidence_counts.retweet || 0);
            document.getElementById("data-window").textContent = `${{s.total_rows}} tweet dari ${{s.unique_accounts}} akun, rentang ${{s.date_min}} sampai ${{s.date_max}}.`;

            const rows = s.per_query.map(row => `
                <tr>
                    <td>${{row.query}}</td>
                    <td>${{fmtNumber(row.rows)}}</td>
                    <td>${{fmtNumber(row.accounts)}}</td>
                    <td>${{fmtNumber(row.retweets)}}</td>
                    <td>${{fmtNumber(row.replies)}}</td>
                </tr>
            `).join("");
            document.getElementById("query-table").innerHTML = `
                <thead><tr><th>Query</th><th>Tweet</th><th>Akun</th><th>RT</th><th>Reply</th></tr></thead>
                <tbody>${{rows}}</tbody>
            `;

            const maxSim = Math.max(...DATA.sensitivity_reference.similarity.map(item => item.count), 1);
            const maxTime = Math.max(...DATA.sensitivity_reference.time.map(item => item.count), 1);
            const simBars = DATA.sensitivity_reference.similarity.map(item => barRow(item, maxSim)).join("");
            const timeBars = DATA.sensitivity_reference.time.map(item => barRow(item, maxTime)).join("");
            document.getElementById("sensitivity-bars").innerHTML = `
                <div class="detail-sub">Jumlah evidence semantic yang lolos pada ambang tertentu.</div>
                ${{simBars}}
                <div style="height: 8px;"></div>
                ${{timeBars}}
            `;
        }}

        function barRow(item, maxValue) {{
            const width = Math.max(3, (item.count / maxValue) * 100);
            return `
                <div class="bar-row">
                    <div>${{item.label}}</div>
                    <div class="bar-track"><div class="bar-fill" style="width: ${{width}}%;"></div></div>
                    <div>${{fmtNumber(item.count)}}</div>
                </div>
            `;
        }}

        document.getElementById("mode-with-rt").addEventListener("click", () => setMode("with_rt"));
        document.getElementById("mode-non-rt").addEventListener("click", () => setMode("non_rt"));
        els.simSlider.addEventListener("input", event => {{
            state.minSim = Number(event.target.value);
            state.selectedCommunity = null;
            render();
        }});
        els.timeSlider.addEventListener("input", event => {{
            state.maxDelta = Number(event.target.value);
            state.selectedCommunity = null;
            render();
        }});
        document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => activateTab(btn.dataset.tab)));

        renderSummary();
        setMode("with_rt");
    </script>
</body>
</html>
"""


def render_html_v2(payload):
    html = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Finale Analisis Koordinasi Narasi Politik</title>
    <link rel="icon" href="data:,">
    <link rel="stylesheet" href="../../../lib/vis-9.1.2/vis-network.css">
    <script src="../../../lib/vis-9.1.2/vis-network.min.js"></script>
    <style>
        body {
            font-family: "Plus Jakarta Sans", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background-color: #f6f8fb;
            color: #0f172a;
            margin: 0;
            overflow: hidden;
            height: 100vh;
            letter-spacing: 0;
        }

        * {
            box-sizing: border-box;
        }

        button, input {
            font: inherit;
        }

        #app-layout {
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100vw;
        }

        #header-bar {
            height: 60px;
            background-color: #ffffff;
            border-bottom: 1px solid #e2e8f0;
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
            background: linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
        }

        #network-canvas {
            width: 100%;
            height: 100%;
        }

        #analysis-panel {
            width: 500px;
            background-color: #ffffff;
            border-left: 1px solid #e2e8f0;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .d-flex { display: flex; }
        .align-items-center { align-items: center; }
        .justify-content-between { justify-content: space-between; }
        .flex-wrap { flex-wrap: wrap; }
        .gap-2 { gap: 8px; }
        .m-0 { margin: 0; }
        .mb-0 { margin-bottom: 0; }
        .mb-1 { margin-bottom: 4px; }
        .mb-2 { margin-bottom: 8px; }
        .mb-3 { margin-bottom: 12px; }
        .mb-4 { margin-bottom: 16px; }
        .mt-4 { margin-top: 16px; }
        .ms-2 { margin-left: 8px; }
        .ms-3 { margin-left: 12px; }
        .my-5 { margin-top: 36px; margin-bottom: 36px; }
        .text-center { text-align: center; }
        .text-muted { color: #64748b !important; }
        .text-white { color: #0f172a !important; }
        .text-danger { color: #dc2626 !important; }
        .text-info { color: #0284c7 !important; }
        .small { font-size: 0.82rem; }
        .fw-bold { font-weight: 700; }

        .badge {
            display: inline-flex;
            align-items: center;
            background-color: #e2e8f0;
            color: #334155;
            border-radius: 999px;
            padding: 4px 8px;
            font-size: 0.72rem;
            font-weight: 700;
            line-height: 1;
        }

        .mode-switch {
            display: inline-flex;
            background: #eef2f7;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 4px;
        }

        .mode-button {
            border: 0;
            background: transparent;
            color: #64748b;
            border-radius: 6px;
            padding: 7px 12px;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
        }

        .mode-button.active {
            background: #ffffff;
            color: #0f172a;
            box-shadow: 0 1px 8px rgba(15, 23, 42, 0.08);
        }

        .hud-panel {
            position: absolute;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid #dde6f0;
            border-radius: 8px;
            padding: 12px 16px;
            z-index: 50;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
        }

        #hud-controls {
            top: 24px;
            left: 24px;
            width: 370px;
        }

        #hud-legend {
            bottom: 24px;
            left: 24px;
            max-width: 245px;
        }

        .hud-title {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 8px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 4px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 6px;
            font-size: 0.8rem;
            color: #334155;
        }

        .legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .slider-row {
            margin-bottom: 10px;
        }

        .slider-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .slider-value {
            color: #0f172a;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }

        input[type="range"] {
            width: 100%;
            accent-color: #2563eb;
        }

        .nav-pills {
            background-color: #eef2f7;
            padding: 4px;
            border-radius: 8px;
            margin: 16px 20px 12px 20px;
            display: flex;
        }

        .nav-pills .nav-link {
            color: #64748b;
            background: none;
            border: none;
            font-weight: 600;
            font-size: 0.85rem;
            padding: 8px 10px;
            border-radius: 6px;
            flex: 1;
            text-align: center;
            cursor: pointer;
        }

        .nav-pills .nav-link.active {
            color: #0f172a;
            background-color: #ffffff;
            box-shadow: 0 1px 8px rgba(15, 23, 42, 0.08);
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
            background: #cbd5e1;
            border-radius: 3px;
        }

        .tab-pane {
            display: none;
        }

        .tab-pane.active {
            display: block;
        }

        .table-dark-custom {
            font-size: 0.85rem;
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .table-dark-custom th {
            color: #64748b;
            font-weight: 600;
            border-bottom: 2px solid #e2e8f0;
            padding: 8px 6px;
            text-align: left;
        }

        .table-dark-custom td {
            padding: 8px 6px;
            border-bottom: 1px solid #e2e8f0;
            cursor: pointer;
            color: #334155;
            vertical-align: top;
        }

        .table-dark-custom tr:hover td {
            background-color: #f1f5f9;
            color: #0f172a;
        }

        .info-list {
            background-color: #f8fafc;
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 20px;
            border: 1px solid #dbe4ee;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
            font-size: 0.85rem;
        }

        .info-row:last-child {
            border-bottom: none;
        }

        .info-label {
            color: #64748b;
            font-weight: 500;
        }

        .info-value {
            font-weight: 600;
            color: #0f172a;
            text-align: right;
        }

        .keyword-badge {
            background-color: #ffffff;
            color: #334155;
            border: 1px solid #cbd5e1;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            display: inline-block;
            margin: 2px;
        }

        blockquote.tweet-quote {
            border-left: 4px solid #475569;
            background: #ffffff;
            padding: 12px 14px;
            font-size: 0.85rem;
            border-radius: 0 6px 6px 0;
            margin-bottom: 12px;
            color: #334155;
            line-height: 1.45;
        }

        .top-account-item {
            background-color: #f8fafc;
            border: 1px solid #dbe4ee;
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 8px;
        }

        .top-account-user {
            color: #0284c7;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
        }

        .insight-note {
            background: #f8fafc;
            border: 1px solid #dbe4ee;
            border-radius: 8px;
            padding: 12px 14px;
            color: #334155;
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
            border: 1px solid #dbe4ee;
            border-radius: 8px;
            padding: 10px 12px;
            background: #ffffff;
        }

        .reason-label {
            color: #64748b;
            font-size: 0.72rem;
            margin-bottom: 3px;
        }

        .reason-value {
            color: #0f172a;
            font-size: 0.95rem;
            font-weight: 700;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }

        .evidence-pair {
            border: 1px solid #dbe4ee;
            border-left-width: 3px;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: #ffffff;
        }

        .evidence-meta {
            color: #64748b;
            font-size: 0.72rem;
            margin-top: 4px;
        }

        .cluster-card {
            padding: 12px 14px;
            border-radius: 8px;
            margin-bottom: 8px;
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-left-width: 3px;
            cursor: pointer;
        }

        .cluster-card.active {
            background: #f8fafc;
            border-color: #bfdbfe;
        }

        .bar-row {
            display: grid;
            grid-template-columns: 74px 1fr 48px;
            gap: 8px;
            align-items: center;
            margin: 8px 0;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .bar-track {
            height: 8px;
            background: #e2e8f0;
            border-radius: 999px;
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            background: #2563eb;
        }

        .report-section {
            background: #f8fafc;
            border: 1px solid #dbe4ee;
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 12px;
        }

        .report-section-title {
            color: #64748b;
            font-size: 0.74rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }

        .report-text {
            color: #334155;
            font-size: 0.84rem;
            line-height: 1.55;
        }

        .report-list {
            display: grid;
            gap: 8px;
        }

        .report-item {
            border-left: 3px solid #2563eb;
            background: #ffffff;
            border-radius: 6px;
            padding: 9px 10px;
            color: #334155;
            font-size: 0.8rem;
            line-height: 1.45;
        }

        .tweet-time-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 0;
            font-size: 0.78rem;
            color: #334155;
            border-bottom: 1px solid #f1f5f9;
        }

        .tweet-time-item:last-child {
            border-bottom: none;
        }

        .tweet-time-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #94a3b8;
            flex-shrink: 0;
        }

        .inspeksi-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
        }

        .inspeksi-type-badge {
            background: #dbeafe;
            color: #1e40af;
            border-radius: 4px;
            padding: 2px 10px;
            font-size: 0.72rem;
            font-weight: 700;
        }

        .inspeksi-type-badge.edge-type {
            background: #fef3c7;
            color: #92400e;
        }

        .edge-conn-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 0;
            font-size: 0.78rem;
            color: #334155;
            border-bottom: 1px solid #f1f5f9;
            cursor: pointer;
        }

        .edge-conn-item:hover {
            color: #0f172a;
        }

        .edge-conn-item:last-child {
            border-bottom: none;
        }

        @media (max-width: 980px) {
            body {
                overflow: auto;
                height: auto;
            }

            #app-layout {
                height: auto;
                min-height: 100vh;
            }

            #header-bar {
                height: auto;
                min-height: 60px;
                gap: 12px;
                flex-wrap: wrap;
                padding: 12px 16px;
            }

            #main-content {
                flex-direction: column;
                overflow: visible;
            }

            #visualizer-area {
                min-height: 560px;
            }

            #analysis-panel {
                width: 100%;
                border-left: 0;
                border-top: 1px solid #e2e8f0;
            }

            #hud-controls {
                width: calc(100% - 48px);
            }
        }
    </style>
</head>
<body>
<div id="app-layout">
    <div id="header-bar">
        <div class="d-flex align-items-center">
            <h5 class="fw-bold m-0 text-white" style="font-size: 1rem;">Finale Analisis Koordinasi Narasi Politik</h5>
            <span class="badge ms-3" id="mode-badge">Pakai RT</span>
        </div>
        <div class="mode-switch">
            <button class="mode-button active" id="mode-with-rt" type="button">Pakai RT</button>
            <button class="mode-button" id="mode-non-rt" type="button">Tanpa RT</button>
        </div>
    </div>

    <div id="main-content">
        <div id="visualizer-area">
            <div id="network-canvas"></div>
            <div id="hud-controls" class="hud-panel">
                <div class="hud-title">Filter Sensitivitas</div>
                <div class="slider-row">
                    <div class="slider-label"><span>Minimum similarity</span><span class="slider-value" id="sim-value">0.75</span></div>
                    <input id="sim-slider" type="range" min="0.65" max="1" step="0.01" value="0.75">
                </div>
                <div class="slider-row">
                    <div class="slider-label"><span>Maksimum jeda waktu</span><span class="slider-value" id="time-value">5.0 menit</span></div>
                    <input id="time-slider" type="range" min="0" max="1800" step="30" value="300">
                </div>
                <div class="slider-row mb-0">
                    <div class="slider-label"><span>Ukuran node</span><span class="slider-value" id="size-value">1.0x</span></div>
                    <input id="size-slider" type="range" min="0.3" max="2.0" step="0.1" value="1.0">
                </div>
                <div class="text-muted small" id="filter-note" style="line-height: 1.4; margin-top: 8px;"></div>
            </div>
            <div id="hud-legend" class="hud-panel">
                <div class="hud-title">Warna Edge</div>
                <div class="legend-item"><span class="legend-dot" style="background-color:#0891b2;"></span>Semantic</div>
                <div class="legend-item"><span class="legend-dot" style="background-color:#d97706;"></span>Retweet</div>
                <div class="legend-item"><span class="legend-dot" style="background-color:#7c3aed;"></span>Campuran</div>
                <div class="text-muted" style="font-size: 0.68rem; line-height:1.35;">Warna node tetap membedakan kluster visual. Klik tidak menggerakkan kamera.</div>
            </div>
        </div>

        <div id="analysis-panel">
            <div class="nav nav-pills" id="panelTabs">
                <button class="nav-link active" data-tab="overview" type="button">Ikhtisar</button>
                <button class="nav-link" data-tab="report" type="button">Report</button>
                <button class="nav-link" data-tab="detail" type="button">Analisis Detil</button>
                <button class="nav-link" data-tab="inspeksi" type="button">Inspeksi</button>
                <button class="nav-link" data-tab="all-clusters" type="button">Kluster</button>
                <button class="nav-link" data-tab="data" type="button">Data</button>
            </div>

            <div class="tab-content">
                <div class="tab-pane active" id="overview">
                    <div class="insight-note" id="mode-note"></div>
                    <div class="info-list">
                        <div class="info-row"><span class="info-label">Total Akun Tampil</span><span class="info-value" id="stat-nodes">0</span></div>
                        <div class="info-row"><span class="info-label">Hubungan Tampil</span><span class="info-value" id="stat-edges">0</span></div>
                        <div class="info-row"><span class="info-label">Jumlah Kelompok</span><span class="info-value" id="stat-clusters">0</span></div>
                        <div class="info-row"><span class="info-label">Koordinasi Kuat</span><span class="info-value text-danger" id="stat-strong">0</span></div>
                    </div>
                    <h6 class="hud-title mt-4">Peringkat Koordinasi Kluster</h6>
                    <table class="table-dark-custom">
                        <thead>
                            <tr>
                                <th>Kluster</th>
                                <th>Akun</th>
                                <th>Skor</th>
                                <th>Fokus Narasi</th>
                            </tr>
                        </thead>
                        <tbody id="overview-table-body"></tbody>
                    </table>
                </div>

                <div class="tab-pane" id="report">
                    <div class="report-section">
                        <div class="report-section-title">Rangkuman Overall</div>
                        <div class="report-text" id="report-overall"></div>
                    </div>
                    <div class="report-section">
                        <div class="report-section-title">Ciri Khas Kluster Kuat</div>
                        <div class="report-list" id="report-characteristics"></div>
                    </div>
                    <div class="report-section">
                        <div class="report-section-title">Komposisi Hubungan</div>
                        <div class="report-list" id="report-composition"></div>
                    </div>
                    <div class="report-section">
                        <div class="report-section-title">Jembatan Antar-Kluster</div>
                        <div class="report-list" id="report-bridges"></div>
                    </div>
                </div>

                <div class="tab-pane" id="detail">
                    <div id="detail-empty-state">
                        <div class="text-center text-muted my-5">
                            <p class="mb-0">Pilih node, baris tabel, atau kartu kluster untuk melihat detail.</p>
                        </div>
                    </div>
                    <div id="detail-content" style="display:none;">
                        <div id="selected-account-card" class="mb-4" style="display:none; background:#f8fafc; border:1px solid #dbe4ee; border-radius:8px; padding:14px 16px;">
                            <h6 class="hud-title text-info mb-2">Akun Terpilih</h6>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="fw-bold text-white" id="node-username">@username</span>
                                <span class="text-muted small" id="node-cluster">Kluster #0</span>
                            </div>
                            <div class="d-flex flex-wrap gap-2 mb-2">
                                <span class="keyword-badge" id="node-query">Query</span>
                                <span class="keyword-badge" id="node-rt-ratio">Rasio RT akun: 0.00</span>
                                <span class="keyword-badge" id="node-first-time" style="background:#f0fdf4;border-color:#86efac;">Pertama: -</span>
                                <span class="keyword-badge" id="node-last-time" style="background:#fef3c7;border-color:#fcd34d;">Terakhir: -</span>
                            </div>
                            <blockquote class="tweet-quote mb-0" id="node-tweet" style="border-left-color:#38bdf8;">Tweet...</blockquote>
                        </div>

                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-white m-0" id="detail-title" style="font-size:1rem;">Kluster #0</h5>
                            <span id="detail-status-badge" class="badge">Status</span>
                        </div>
                        <div class="insight-note" id="detail-narrative"></div>
                        <div class="reason-grid">
                            <div class="reason-metric"><div class="reason-label">Jumlah Akun</div><div class="reason-value" id="detail-size">0</div></div>
                            <div class="reason-metric"><div class="reason-label">Density</div><div class="reason-value" id="detail-density">0</div></div>
                            <div class="reason-metric"><div class="reason-label">Avg Similarity</div><div class="reason-value" id="detail-sim">0</div></div>
                            <div class="reason-metric"><div class="reason-label">Median Jeda</div><div class="reason-value" id="detail-delta">0</div></div>
                        </div>
                        <div class="mb-3" id="detail-keywords"></div>
                        <h6 class="hud-title mt-4">Bukti Pasangan Terkuat</h6>
                        <div id="detail-evidence"></div>
                        <h6 class="hud-title mt-4">Akun Utama</h6>
                        <div id="detail-accounts"></div>
                    </div>
                </div>

                <div class="tab-pane" id="all-clusters">
                    <div id="all-clusters-list"></div>
                </div>

                <div class="tab-pane" id="data">
                    <div class="insight-note" id="data-summary"></div>
                    <h6 class="hud-title">Komposisi Query</h6>
                    <table class="table-dark-custom">
                        <thead><tr><th>Query</th><th>Tweet</th><th>Akun</th><th>RT</th></tr></thead>
                        <tbody id="query-table-body"></tbody>
                    </table>
                    <h6 class="hud-title mt-4">Referensi Sensitivitas Evidence Semantic</h6>
                    <div id="sensitivity-bars"></div>
                </div>

                <div class="tab-pane" id="inspeksi">
                    <div id="inspeksi-empty" class="text-center text-muted my-5">
                        <p class="mb-0">Klik node atau edge di graf untuk melihat detail lengkap.</p>
                        <p class="small" style="margin-top:6px;">Tab ini menampilkan informasi lengkap termasuk waktu tweet, keyword, dan koneksi edge dari item yang dipilih.</p>
                    </div>
                    <div id="inspeksi-content" style="display:none;"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    const DATA = __DATA_JSON__;
    const PALETTE = __PALETTE_JSON__;

    const state = {
        mode: "with_rt",
        minSim: DATA.modes.with_rt.defaults.min_similarity,
        maxDelta: DATA.modes.with_rt.defaults.max_delta,
        selectedCluster: null,
        selectedNode: null,
        selectedEdge: null,
        nodeSizeMultiplier: 1.0
    };

    let network = null;
    let networkMode = null;
    let latestRawEdges = [];
    let latestClusters = [];
    let latestEdges = [];
    let latestNodes = new Set();

    function fmtNumber(value) {
        return Number(value || 0).toLocaleString("id-ID");
    }

    function fmtPct(value) {
        return `${(Number(value || 0) * 100).toFixed(1)}%`;
    }

    function fmtDelta(seconds) {
        const value = Number(seconds || 0);
        if (value < 60) return `${Math.round(value)} detik`;
        return `${(value / 60).toFixed(1)} menit`;
    }

    function median(values) {
        if (!values.length) return 0;
        const sorted = values.slice().sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    }

    function communityOf(nodeId) {
        const map = DATA.modes[state.mode].communities || {};
        return Object.prototype.hasOwnProperty.call(map, nodeId) ? map[nodeId] : -1;
    }

    function clusterColor(cid) {
        if (cid < 0) return "#8a94a6";
        return PALETTE[cid % PALETTE.length];
    }

    function stablePosition(nodeId) {
        return DATA.modes[state.mode].positions?.[nodeId] || { x: 0, y: 0 };
    }

    function statusInfo(size, density, evidence) {
        const score = density * Math.log2(size + 1);
        if (size < 5 || evidence < 5) return { status: "Indikasi Lemah", rank: 1, score };
        if (score >= 1.5) return { status: "Koordinasi Kuat", rank: 3, score };
        if (score >= 0.8) return { status: "Perlu Investigasi", rank: 2, score };
        return { status: "Rendah", rank: 0, score };
    }

    function focusLabel(counts) {
        const labels = {
            anies: "Dominan membahas Anies-Muhaimin",
            prabowo: "Dominan membahas Prabowo-Gibran",
            ganjar: "Dominan membahas Ganjar-Mahfud"
        };
        const entries = Object.entries(counts);
        const total = entries.reduce((sum, item) => sum + item[1], 0);
        if (!total) return "Tanpa kandidat dominan";
        entries.sort((a, b) => b[1] - a[1]);
        if (entries[0][1] >= 2 && entries[0][1] / total >= 0.6) return labels[entries[0][0]];
        return "Lintas kandidat / perbandingan";
    }

    function filteredEdges() {
        return DATA.modes[state.mode].edges.filter(edge => {
            return edge.avg_similarity >= state.minSim && edge.min_delta <= state.maxDelta;
        });
    }

    function computeClusters(edges) {
        const groups = new Map();
        const nodes = new Set();
        for (const edge of edges) {
            nodes.add(edge.source);
            nodes.add(edge.target);
            const sourceCommunity = communityOf(edge.source);
            const targetCommunity = communityOf(edge.target);
            for (const pair of [[edge.source, sourceCommunity], [edge.target, targetCommunity]]) {
                if (!groups.has(pair[1])) groups.set(pair[1], { id: pair[1], nodes: new Set(), edges: [], crossEdges: 0 });
                groups.get(pair[1]).nodes.add(pair[0]);
            }
            if (sourceCommunity === targetCommunity) {
                groups.get(sourceCommunity).edges.push(edge);
            } else {
                if (groups.has(sourceCommunity)) groups.get(sourceCommunity).crossEdges += 1;
                if (groups.has(targetCommunity)) groups.get(targetCommunity).crossEdges += 1;
            }
        }

        const clusters = [];
        for (const group of groups.values()) {
            if (group.id < 0 || group.nodes.size < 3 || group.edges.length === 0) continue;
            const size = group.nodes.size;
            const possibleEdges = size * (size - 1) / 2;
            const density = possibleEdges ? group.edges.length / possibleEdges : 0;
            const evidence = group.edges.reduce((sum, edge) => sum + edge.edge_count, 0);
            const avgSimilarity = group.edges.reduce((sum, edge) => sum + edge.avg_similarity, 0) / group.edges.length;
            const status = statusInfo(size, density, evidence);
            const focusCounts = { anies: 0, prabowo: 0, ganjar: 0 };
            const keywordCounts = new Map();
            const topAccounts = [];

            for (const nodeId of group.nodes) {
                const node = DATA.nodes[nodeId];
                if (!node) continue;
                for (const key of Object.keys(focusCounts)) focusCounts[key] += Number(node.focus_counts?.[key] || 0);
                for (const keyword of node.keywords || []) keywordCounts.set(keyword, (keywordCounts.get(keyword) || 0) + 1);
                topAccounts.push(node);
            }

            const keywords = Array.from(keywordCounts.entries())
                .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
                .slice(0, 5)
                .map(item => item[0]);
            const examples = group.edges.slice().sort((a, b) => {
                return b.edge_count - a.edge_count || b.avg_similarity - a.avg_similarity || b.weight - a.weight;
            }).slice(0, 3);

            topAccounts.sort((a, b) => b.tweet_count - a.tweet_count || b.rt_ratio - a.rt_ratio);
            clusters.push({
                id: group.id,
                size,
                density,
                evidence,
                edgeCount: group.edges.length,
                score: status.score,
                status: status.status,
                rank: status.rank,
                avgSimilarity,
                medianDelta: median(group.edges.map(edge => edge.min_delta)),
                semanticEdges: group.edges.filter(edge => edge.kind === "semantic").length,
                retweetEdges: group.edges.filter(edge => edge.kind === "retweet").length,
                mixedEdges: group.edges.filter(edge => edge.kind === "mixed").length,
                crossEdges: group.crossEdges,
                focus: focusLabel(focusCounts),
                keywords,
                examples,
                topAccounts: topAccounts.slice(0, 5),
                nodes: Array.from(group.nodes),
                color: clusterColor(group.id)
            });
        }

        clusters.sort((a, b) => b.rank - a.rank || b.evidence - a.evidence || b.score - a.score);
        const renderedNodes = new Set();
        clusters.forEach(cluster => cluster.nodes.forEach(nodeId => renderedNodes.add(nodeId)));
        return { clusters, nodes: renderedNodes };
    }

    function edgeColor(edge) {
        if (edge.kind === "retweet") return "#d97706";
        if (edge.kind === "mixed") return "#7c3aed";
        return "#0891b2";
    }

    function renderNetwork() {
        const degree = new Map();
        latestEdges.forEach(edge => {
            degree.set(edge.source, (degree.get(edge.source) || 0) + edge.edge_count);
            degree.set(edge.target, (degree.get(edge.target) || 0) + edge.edge_count);
        });

        const nodes = Array.from(latestNodes).map(nodeId => {
            const node = DATA.nodes[nodeId] || { id: nodeId };
            const cid = communityOf(nodeId);
            const baseSize = Math.min(32, 11 + Math.log2((degree.get(nodeId) || 1) + 1) * 3.2);
            const size = baseSize * state.nodeSizeMultiplier;
            const pos = stablePosition(nodeId);
            return {
                id: nodeId,
                label: "",
                x: pos.x,
                y: pos.y,
                fixed: { x: true, y: true },
                physics: false,
                size,
                color: clusterColor(cid),
                borderWidth: state.selectedNode === nodeId ? 3 : 1,
                title: `<b>@${nodeId}</b><br>Kluster: #${cid}<br>Tweet: ${node.tweet_count || 0}<br>Rasio RT: ${fmtPct(node.rt_ratio || 0)}<br>Query: ${node.query_context || "-"}<br>Waktu: ${node.first_tweet_time || "?"} → ${node.last_tweet_time || "?"}<br><br>${truncText(node.last_tweet, 100)}`
            };
        });

        const edges = latestEdges.map(edge => ({
            id: edge.id,
            from: edge.source,
            to: edge.target,
            value: Math.max(1, Math.min(3, Math.log2(edge.edge_count + 1))),
            width: Math.max(0.7, Math.min(2.4, Math.log2(edge.edge_count + 1) * 0.65)),
            color: { color: edgeColor(edge), opacity: 0.42 },
            title: `<b>${edge.edge_types}</b><br>Bukti: ${edge.edge_count}<br>Similarity: ${edge.avg_similarity.toFixed(3)}<br>Jeda min: ${fmtDelta(edge.min_delta)}${edge.dominant_rt_source ? `<br>Sumber RT: @${edge.dominant_rt_source}` : ""}`,
            smooth: { type: "continuous" }
        }));

        const keepView = network && networkMode === state.mode
            ? { position: network.getViewPosition(), scale: network.getScale() }
            : null;
        if (network) network.destroy();
        network = new vis.Network(
            document.getElementById("network-canvas"),
            { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
            {
                nodes: {
                    shape: "dot",
                    font: { color: "#334155", size: 12 },
                    scaling: { min: 8, max: 32 }
                },
                edges: {
                    width: 1,
                    selectionWidth: 1
                },
                layout: {
                    improvedLayout: false
                },
                physics: {
                    enabled: false
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 120,
                    hideEdgesOnDrag: true
                }
            }
        );
        networkMode = state.mode;
        if (keepView) {
            network.moveTo({ position: keepView.position, scale: keepView.scale });
        }

        network.on("click", params => {
            if (params.nodes.length) {
                const nodeId = params.nodes[0];
                state.selectedNode = nodeId;
                state.selectedEdge = null;
                state.selectedCluster = communityOf(nodeId);
                updateDetail();
                updateInspection();
                activateTab("inspeksi");
            } else if (params.edges.length) {
                const edgeId = params.edges[0];
                const edge = latestEdges.find(e => e.id === edgeId);
                if (edge) {
                    state.selectedEdge = edge;
                    updateInspection();
                    activateTab("inspeksi");
                }
            }
        });
    }

    function activeCluster() {
        if (state.selectedCluster === null && latestClusters.length) state.selectedCluster = latestClusters[0].id;
        return latestClusters.find(cluster => cluster.id === state.selectedCluster) || null;
    }

    function focusClusterViewport(cluster) {
        if (!network || !cluster || !cluster.nodes.length) return;
        const coords = cluster.nodes
            .map(nodeId => stablePosition(nodeId))
            .filter(pos => Number.isFinite(pos.x) && Number.isFinite(pos.y));
        if (!coords.length) return;

        const xs = coords.map(pos => pos.x);
        const ys = coords.map(pos => pos.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const center = {
            x: (minX + maxX) / 2,
            y: (minY + maxY) / 2
        };
        const width = Math.max(80, maxX - minX);
        const height = Math.max(80, maxY - minY);
        const canvas = document.getElementById("network-canvas").getBoundingClientRect();
        const scaleX = canvas.width / (width + 260);
        const scaleY = canvas.height / (height + 260);
        const scale = Math.max(0.28, Math.min(1.35, Math.min(scaleX, scaleY)));

        network.selectNodes(cluster.nodes);
        network.moveTo({
            position: center,
            scale
        });
    }

    function selectCluster(clusterId, openDetail) {
        state.selectedCluster = clusterId;
        state.selectedNode = null;
        const cluster = activeCluster();
        focusClusterViewport(cluster);
        renderTables();
        updateDetail();
        if (openDetail) activateTab("detail");
    }

    function statusBadgeClass(status) {
        if (status === "Koordinasi Kuat") return "badge text-danger";
        return "badge";
    }

    function renderTables() {
        const overviewBody = document.getElementById("overview-table-body");
        const clusterList = document.getElementById("all-clusters-list");
        overviewBody.innerHTML = "";
        clusterList.innerHTML = "";

        latestClusters.forEach(cluster => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="fw-bold">#${cluster.id}</td>
                <td>${cluster.size}</td>
                <td><span class="fw-bold">${cluster.score.toFixed(3)}</span></td>
                <td><span class="badge" style="background-color:${cluster.color}; color:#fff;">${cluster.focus}</span></td>
            `;
            tr.onclick = () => selectCluster(cluster.id, true);
            overviewBody.appendChild(tr);

            const card = document.createElement("div");
            card.className = `cluster-card ${state.selectedCluster === cluster.id ? "active" : ""}`;
            card.style.borderLeftColor = cluster.color;
            card.onclick = () => selectCluster(cluster.id, true);
            card.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-bold text-white small">Kluster #${cluster.id}</span>
                    <span class="text-muted small">Skor: <span class="fw-bold text-white">${cluster.score.toFixed(3)}</span></span>
                </div>
                <div class="small mb-2" style="color:${cluster.color}; font-weight:700;">${cluster.focus}</div>
                <div class="text-muted mb-1" style="font-size:0.72rem;">${cluster.status} · ${cluster.evidence} bukti · ${cluster.semanticEdges} semantic / ${cluster.retweetEdges} RT / ${cluster.mixedEdges} mixed</div>
                <div class="text-muted" style="font-size:0.75rem;">${cluster.keywords.join(", ") || "N/A"}</div>
            `;
            clusterList.appendChild(card);
        });
    }

    function updateDetail() {
        const cluster = activeCluster();
        const emptyState = document.getElementById("detail-empty-state");
        const content = document.getElementById("detail-content");
        if (!cluster) {
            emptyState.style.display = "block";
            content.style.display = "none";
            return;
        }

        emptyState.style.display = "none";
        content.style.display = "block";

        const node = state.selectedNode ? DATA.nodes[state.selectedNode] : null;
        const nodeCard = document.getElementById("selected-account-card");
        if (node) {
            nodeCard.style.display = "block";
            document.getElementById("node-username").innerText = `@${node.id}`;
            document.getElementById("node-cluster").innerText = `Kluster #${communityOf(node.id)}`;
            document.getElementById("node-query").innerText = `Query: ${node.query_context || "-"}`;
            document.getElementById("node-rt-ratio").innerText = `Rasio RT akun: ${Number(node.rt_ratio || 0).toFixed(2)}`;
            document.getElementById("node-first-time").innerText = `Pertama: ${node.first_tweet_time || "-"}`;
            document.getElementById("node-last-time").innerText = `Terakhir: ${node.last_tweet_time || "-"}`;
            document.getElementById("node-tweet").innerText = `"${truncText(node.last_tweet, 140) || "-"}"`;
        } else {
            nodeCard.style.display = "none";
        }

        document.getElementById("detail-title").innerText = `Kluster #${cluster.id}`;
        document.getElementById("detail-status-badge").innerText = cluster.status;
        document.getElementById("detail-status-badge").className = statusBadgeClass(cluster.status);
        document.getElementById("detail-narrative").innerText =
            `${cluster.focus}. Topik utama: ${cluster.keywords.slice(0, 3).join(", ") || "N/A"}. ` +
            `Bukti ringkas: ${cluster.evidence} bukti pasangan; ${cluster.semanticEdges} edge semantic, ${cluster.retweetEdges} edge RT, ${cluster.mixedEdges} edge campuran. ` +
            `Label fokus narasi adalah objek pembahasan, bukan klaim dukungan politik.`;
        document.getElementById("detail-size").innerText = cluster.size;
        document.getElementById("detail-density").innerText = cluster.density.toFixed(4);
        document.getElementById("detail-sim").innerText = cluster.avgSimilarity.toFixed(3);
        document.getElementById("detail-delta").innerText = fmtDelta(cluster.medianDelta);
        document.getElementById("detail-keywords").innerHTML =
            cluster.keywords.map(keyword => `<span class="keyword-badge">${keyword}</span>`).join("") || '<span class="keyword-badge">N/A</span>';

        const evidenceContainer = document.getElementById("detail-evidence");
        evidenceContainer.innerHTML = "";
        cluster.examples.forEach(edge => {
            const div = document.createElement("div");
            div.className = "evidence-pair";
            div.style.borderLeftColor = edgeColor(edge);
            div.innerHTML = `
                <div class="fw-bold small mb-1">@${edge.source} - @${edge.target}</div>
                <div class="evidence-meta">${edge.edge_types} · similarity ${edge.avg_similarity.toFixed(3)} · jeda ${fmtDelta(edge.min_delta)} · ${edge.edge_count} bukti</div>
                <blockquote class="tweet-quote mt-2" style="border-left-color:${edgeColor(edge)};">"${truncText(edge.tweet_1, 140)}"</blockquote>
                <blockquote class="tweet-quote mb-0" style="border-left-color:${edgeColor(edge)};">"${truncText(edge.tweet_2, 140)}"</blockquote>
            `;
            evidenceContainer.appendChild(div);
        });

        const accountContainer = document.getElementById("detail-accounts");
        accountContainer.innerHTML = "";
        cluster.topAccounts.forEach(account => {
            const div = document.createElement("div");
            div.className = "top-account-item";
            div.innerHTML = `
                <div class="d-flex justify-content-between mb-1">
                    <span class="top-account-user" data-node="${account.id}">@${account.id}</span>
                    <span class="text-muted small">RT: ${fmtPct(account.rt_ratio || 0)}</span>
                </div>
                <div class="text-muted" style="font-size:0.7rem; margin-bottom:4px; color:#64748b;">${account.first_tweet_time || ""} → ${account.last_tweet_time || ""}</div>
                <div class="text-muted small" style="line-height:1.4;">"${truncText(account.last_tweet, 120)}"</div>
            `;
            div.querySelector(".top-account-user").onclick = () => {
                state.selectedNode = account.id;
                if (network) network.selectNodes([account.id]);
                updateDetail();
            };
            accountContainer.appendChild(div);
        });
    }

    function truncText(text, limit) {
        if (!text || text.length <= limit) return text || "-";
        return text.substring(0, limit) + "…";
    }

    function updateInspection() {
        const container = document.getElementById("inspeksi-content");
        const empty = document.getElementById("inspeksi-empty");

        if (state.selectedEdge) {
            empty.style.display = "none";
            container.style.display = "block";
            const edge = state.selectedEdge;
            const nodeA = DATA.nodes[edge.source] || {};
            const nodeB = DATA.nodes[edge.target] || {};
            container.innerHTML = `
                <div class="inspeksi-header">
                    <h6 class="hud-title m-0">Edge</h6>
                    <span class="inspeksi-type-badge edge-type">${edge.edge_types}</span>
                </div>
                <div class="fw-bold mb-3" style="font-size:1.05rem;">@${edge.source} — @${edge.target}</div>
                <div class="info-list">
                    <div class="info-row"><span class="info-label">Tipe Edge</span><span class="info-value">${edge.edge_types}</span></div>
                    <div class="info-row"><span class="info-label">Similarity</span><span class="info-value">${edge.avg_similarity.toFixed(4)}</span></div>
                    <div class="info-row"><span class="info-label">Jeda Minimum</span><span class="info-value">${fmtDelta(edge.min_delta)}</span></div>
                    <div class="info-row"><span class="info-label">Jumlah Bukti</span><span class="info-value">${edge.edge_count}</span></div>
                    <div class="info-row"><span class="info-label">Weight</span><span class="info-value">${edge.weight.toFixed(4)}</span></div>
                    <div class="info-row"><span class="info-label">Max Weight</span><span class="info-value">${edge.max_weight.toFixed(4)}</span></div>
                    <div class="info-row"><span class="info-label">Avg Time Score</span><span class="info-value">${edge.avg_time_score.toFixed(4)}</span></div>
                    ${edge.dominant_rt_source ? `<div class="info-row"><span class="info-label">Sumber RT</span><span class="info-value">@${edge.dominant_rt_source}</span></div>` : ""}
                    ${edge.query_context ? `<div class="info-row"><span class="info-label">Query Context</span><span class="info-value">${edge.query_context}</span></div>` : ""}
                </div>
                <h6 class="hud-title mt-4">Waktu Tweet Masing-masing Akun</h6>
                <div class="info-list">
                    <div class="info-row"><span class="info-label">@${edge.source}</span><span class="info-value">${nodeA.first_tweet_time || "?"} → ${nodeA.last_tweet_time || "?"}</span></div>
                    <div class="info-row"><span class="info-label">@${edge.target}</span><span class="info-value">${nodeB.first_tweet_time || "?"} → ${nodeB.last_tweet_time || "?"}</span></div>
                </div>
                <h6 class="hud-title mt-4">Tweet @${edge.source} (Lengkap)</h6>
                <blockquote class="tweet-quote">"${edge.tweet_1 || "-"}"</blockquote>
                <h6 class="hud-title mt-4">Tweet @${edge.target} (Lengkap)</h6>
                <blockquote class="tweet-quote">"${edge.tweet_2 || "-"}"</blockquote>
            `;
        } else if (state.selectedNode) {
            empty.style.display = "none";
            container.style.display = "block";
            const node = DATA.nodes[state.selectedNode] || {};
            const cid = communityOf(state.selectedNode);
            const nodeEdges = latestEdges.filter(e => e.source === state.selectedNode || e.target === state.selectedNode);
            const keywordsHtml = (node.keywords || []).map(k => `<span class="keyword-badge">${k}</span>`).join("") || '<span class="keyword-badge">N/A</span>';
            const edgesHtml = nodeEdges.length ? nodeEdges.map(e => {
                const other = e.source === state.selectedNode ? e.target : e.source;
                return `<div class="edge-conn-item"><span class="tweet-time-dot" style="background:${edgeColor(e)};"></span>@${other} · ${e.edge_types} · sim ${e.avg_similarity.toFixed(3)} · ${fmtDelta(e.min_delta)}</div>`;
            }).join("") : '<div class="text-muted small">Tidak ada edge internal.</div>';
            const timesHtml = (node.tweet_dates || []).map(d => `<div class="tweet-time-item"><span class="tweet-time-dot"></span>${d}</div>`).join("") || '<div class="text-muted small">Tidak ada data waktu.</div>';

            container.innerHTML = `
                <div class="inspeksi-header">
                    <h6 class="hud-title m-0">Node</h6>
                    <span class="inspeksi-type-badge" style="background:${clusterColor(cid)};color:#fff;">Kluster #${cid}</span>
                </div>
                <div class="fw-bold mb-3" style="font-size:1.05rem;">@${node.id || state.selectedNode}</div>
                <div class="info-list">
                    <div class="info-row"><span class="info-label">Jumlah Tweet</span><span class="info-value">${node.tweet_count || 0}</span></div>
                    <div class="info-row"><span class="info-label">Rasio RT</span><span class="info-value">${fmtPct(node.rt_ratio || 0)}</span></div>
                    <div class="info-row"><span class="info-label">Query</span><span class="info-value">${node.query_context || "-"}</span></div>
                    <div class="info-row"><span class="info-label">Tweet Pertama</span><span class="info-value">${node.first_tweet_time || "N/A"}</span></div>
                    <div class="info-row"><span class="info-label">Tweet Terakhir</span><span class="info-value">${node.last_tweet_time || "N/A"}</span></div>
                    <div class="info-row"><span class="info-label">Edge Internal</span><span class="info-value">${nodeEdges.length}</span></div>
                </div>
                <h6 class="hud-title mt-4">Keyword</h6>
                <div class="d-flex flex-wrap gap-2 mb-3">${keywordsHtml}</div>
                <h6 class="hud-title mt-4">Tweet Terakhir (Lengkap)</h6>
                <blockquote class="tweet-quote">"${node.last_tweet || "-"}"</blockquote>
                <h6 class="hud-title mt-4">Riwayat Waktu Tweet (Maks 5)</h6>
                ${timesHtml}
                <h6 class="hud-title mt-4">Koneksi Edge (${nodeEdges.length})</h6>
                ${edgesHtml}
            `;
        } else {
            empty.style.display = "block";
            container.style.display = "none";
        }
    }

    function updateStats() {
        document.getElementById("stat-nodes").innerText = fmtNumber(latestNodes.size);
        document.getElementById("stat-edges").innerText = fmtNumber(latestEdges.length);
        document.getElementById("stat-clusters").innerText = fmtNumber(latestClusters.length);
        document.getElementById("stat-strong").innerText = fmtNumber(latestClusters.filter(cluster => cluster.status === "Koordinasi Kuat").length);
        document.getElementById("sim-value").innerText = state.minSim.toFixed(2);
        document.getElementById("time-value").innerText = fmtDelta(state.maxDelta);
        const modeText = state.mode === "with_rt" ? "Pakai RT" : "Tanpa RT";
        document.getElementById("mode-badge").innerText = modeText;
        document.getElementById("filter-note").innerText = `Mode ${modeText}; edge internal kluster tampil jika similarity >= ${state.minSim.toFixed(2)} dan jeda <= ${fmtDelta(state.maxDelta)}.`;
        document.getElementById("mode-note").innerText = state.mode === "with_rt"
            ? "Mode ini memakai edge semantic dan shared-retweet. Retweet tetap dibedakan dari semantic edge; graf menampilkan edge internal kluster agar visual tidak melebar."
            : "Mode ini hanya memakai edge semantic dari tweet non-retweet. Retweet tidak membentuk kluster; graf menampilkan backbone internal seperti dashboard Non-RT.";
    }

    function updateReport() {
        const overall = document.getElementById("report-overall");
        const characteristics = document.getElementById("report-characteristics");
        const composition = document.getElementById("report-composition");
        const bridges = document.getElementById("report-bridges");

        if (!latestClusters.length) {
            overall.innerText = "Tidak ada kluster yang lolos filter saat ini. Longgarkan similarity atau maksimum jeda waktu untuk melihat pola hubungan.";
            characteristics.innerHTML = '<div class="report-item">Tidak ada kluster yang bisa dirangkum.</div>';
            composition.innerHTML = '<div class="report-item">Tidak ada edge yang lolos filter.</div>';
            bridges.innerHTML = '<div class="report-item">Tidak ada hubungan antar-kluster yang lolos filter.</div>';
            return;
        }

        const strongClusters = latestClusters.filter(cluster => cluster.status === "Koordinasi Kuat");
        const avgClusterSize = latestClusters.reduce((sum, cluster) => sum + cluster.size, 0) / latestClusters.length;
        const avgDensity = latestClusters.reduce((sum, cluster) => sum + cluster.density, 0) / latestClusters.length;
        const internalEvidence = latestEdges.reduce((sum, edge) => sum + edge.edge_count, 0);
        const rawEvidence = latestRawEdges.reduce((sum, edge) => sum + edge.edge_count, 0);
        const avgSimilarity = latestEdges.length
            ? latestEdges.reduce((sum, edge) => sum + edge.avg_similarity, 0) / latestEdges.length
            : 0;
        const medianDelta = median(latestEdges.map(edge => edge.min_delta));
        const modeText = state.mode === "with_rt" ? "Pakai RT" : "Tanpa RT";

        const focusCounts = new Map();
        latestClusters.forEach(cluster => {
            focusCounts.set(cluster.focus, (focusCounts.get(cluster.focus) || 0) + 1);
        });
        const dominantFocus = Array.from(focusCounts.entries())
            .sort((a, b) => b[1] - a[1])[0]?.[0] || "N/A";

        overall.innerText =
            `Pada mode ${modeText}, filter saat ini menampilkan ${latestClusters.length} kluster dari ${latestNodes.size} akun. ` +
            `${strongClusters.length} kluster masuk kategori Koordinasi Kuat. Rata-rata ukuran kluster ${avgClusterSize.toFixed(1)} akun, ` +
            `rata-rata density ${avgDensity.toFixed(3)}, median jeda edge internal ${fmtDelta(medianDelta)}, dan rata-rata similarity internal ${avgSimilarity.toFixed(3)}. ` +
            `Fokus narasi yang paling sering muncul: ${dominantFocus}.`;

        characteristics.innerHTML = latestClusters.slice(0, 4).map(cluster => {
            const reason = cluster.avgSimilarity >= 0.9 && cluster.medianDelta <= 60
                ? "teks sangat mirip dan muncul hampir bersamaan"
                : cluster.avgSimilarity >= 0.9
                    ? "kemiripan narasi sangat tinggi"
                    : cluster.medianDelta <= 60
                        ? "kedekatan waktu sangat kuat"
                        : "gabungan kemiripan narasi dan kedekatan waktu";
            return `
                <div class="report-item" style="border-left-color:${cluster.color};">
                    <b>Kluster #${cluster.id}</b> (${cluster.size} akun, skor ${cluster.score.toFixed(3)}): ${reason}. 
                    Topik: ${cluster.keywords.slice(0, 3).join(", ") || "N/A"}.
                </div>
            `;
        }).join("");

        const kindCounts = { semantic: 0, retweet: 0, mixed: 0 };
        const kindEvidence = { semantic: 0, retweet: 0, mixed: 0 };
        latestRawEdges.forEach(edge => {
            const kind = kindCounts[edge.kind] === undefined ? "semantic" : edge.kind;
            kindCounts[kind] += 1;
            kindEvidence[kind] += edge.edge_count;
        });
        const highSimilarityEdges = latestRawEdges.filter(edge => edge.avg_similarity >= 0.85).length;
        const closeTimeEdges = latestRawEdges.filter(edge => edge.min_delta <= 60).length;
        composition.innerHTML = `
            <div class="report-item" style="border-left-color:#0891b2;">
                Semantic: ${fmtNumber(kindCounts.semantic)} edge (${fmtNumber(kindEvidence.semantic)} bukti).
            </div>
            <div class="report-item" style="border-left-color:#d97706;">
                Retweet: ${fmtNumber(kindCounts.retweet)} edge (${fmtNumber(kindEvidence.retweet)} bukti).
            </div>
            <div class="report-item" style="border-left-color:#7c3aed;">
                Campuran: ${fmtNumber(kindCounts.mixed)} edge (${fmtNumber(kindEvidence.mixed)} bukti).
            </div>
            <div class="report-item">
                ${fmtNumber(highSimilarityEdges)} edge punya similarity >= 0.85, dan ${fmtNumber(closeTimeEdges)} edge punya jeda <= 60 detik.
                Evidence internal yang divisualkan: ${fmtNumber(internalEvidence)} dari ${fmtNumber(rawEvidence)} evidence yang lolos filter.
            </div>
        `;

        const visibleClusterIds = new Set(latestClusters.map(cluster => cluster.id));
        const bridgeMap = new Map();
        latestRawEdges.forEach(edge => {
            const sourceCommunity = communityOf(edge.source);
            const targetCommunity = communityOf(edge.target);
            if (sourceCommunity === targetCommunity) return;
            if (!visibleClusterIds.has(sourceCommunity) || !visibleClusterIds.has(targetCommunity)) return;
            const ids = [sourceCommunity, targetCommunity].sort((a, b) => a - b);
            const key = `${ids[0]}-${ids[1]}`;
            if (!bridgeMap.has(key)) {
                bridgeMap.set(key, {
                    source: ids[0],
                    target: ids[1],
                    count: 0,
                    evidence: 0,
                    similarity: [],
                    delta: [],
                    kinds: new Map()
                });
            }
            const item = bridgeMap.get(key);
            item.count += 1;
            item.evidence += edge.edge_count;
            item.similarity.push(edge.avg_similarity);
            item.delta.push(edge.min_delta);
            item.kinds.set(edge.kind, (item.kinds.get(edge.kind) || 0) + 1);
        });

        const bridgeRows = Array.from(bridgeMap.values())
            .sort((a, b) => b.evidence - a.evidence || b.count - a.count)
            .slice(0, 5);
        bridges.innerHTML = bridgeRows.length
            ? bridgeRows.map(item => {
                const avgBridgeSim = item.similarity.reduce((sum, value) => sum + value, 0) / item.similarity.length;
                const kindText = Array.from(item.kinds.entries())
                    .sort((a, b) => b[1] - a[1])
                    .map(([kind, count]) => `${kind}: ${count}`)
                    .join(", ");
                return `
                    <div class="report-item">
                        <b>Kluster #${item.source} - #${item.target}</b>: ${item.count} edge lintas kluster, ${item.evidence} bukti,
                        avg similarity ${avgBridgeSim.toFixed(3)}, median jeda ${fmtDelta(median(item.delta))}. ${kindText}.
                    </div>
                `;
            }).join("")
            : '<div class="report-item">Tidak ada edge lintas-kluster yang cukup relevan pada filter ini. Ini berarti kluster yang tampil relatif terpisah.</div>';
    }

    function renderDataTab() {
        const summary = DATA.summary;
        document.getElementById("data-summary").innerText =
            `${summary.total_rows} tweet dari ${summary.unique_accounts} akun unik. Rentang data ${summary.duration_minutes} menit, dari ${summary.date_min} sampai ${summary.date_max}. Rasio retweet ${fmtPct(summary.retweet_ratio)}.`;

        const queryBody = document.getElementById("query-table-body");
        queryBody.innerHTML = "";
        summary.per_query.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${row.query}</td><td>${fmtNumber(row.rows)}</td><td>${fmtNumber(row.accounts)}</td><td>${fmtNumber(row.retweets)}</td>`;
            queryBody.appendChild(tr);
        });

        const bars = document.getElementById("sensitivity-bars");
        const maxSimilarity = Math.max(...DATA.sensitivity_reference.similarity.map(item => item.count), 1);
        const maxTime = Math.max(...DATA.sensitivity_reference.time.map(item => item.count), 1);
        bars.innerHTML = [
            ...DATA.sensitivity_reference.similarity.map(item => barRow(item, maxSimilarity)),
            '<div style="height:8px;"></div>',
            ...DATA.sensitivity_reference.time.map(item => barRow(item, maxTime))
        ].join("");
    }

    function barRow(item, maxValue) {
        const width = Math.max(3, item.count / maxValue * 100);
        return `
            <div class="bar-row">
                <div>${item.label}</div>
                <div class="bar-track"><div class="bar-fill" style="width:${width}%;"></div></div>
                <div>${fmtNumber(item.count)}</div>
            </div>
        `;
    }

    function render() {
        state.selectedEdge = null;
        const rawEdges = filteredEdges();
        latestRawEdges = rawEdges;
        const computed = computeClusters(rawEdges);
        latestClusters = computed.clusters;
        latestNodes = computed.nodes;
        latestEdges = rawEdges.filter(edge => {
            return latestNodes.has(edge.source)
                && latestNodes.has(edge.target)
                && communityOf(edge.source) === communityOf(edge.target);
        });

        if (state.selectedCluster !== null && !latestClusters.some(cluster => cluster.id === state.selectedCluster)) {
            state.selectedCluster = null;
            state.selectedNode = null;
        }
        if (state.selectedCluster === null && latestClusters.length) state.selectedCluster = latestClusters[0].id;

        updateStats();
        renderTables();
        updateDetail();
        updateReport();
        updateInspection();
        renderNetwork();
    }

    function setMode(mode) {
        state.mode = mode;
        state.minSim = DATA.modes[mode].defaults.min_similarity;
        state.maxDelta = DATA.modes[mode].defaults.max_delta;
        state.selectedCluster = null;
        state.selectedNode = null;
        state.selectedEdge = null;
        state.nodeSizeMultiplier = 1.0;
        document.getElementById("size-slider").value = 1.0;
        document.getElementById("size-value").innerText = "1.0x";
        document.getElementById("sim-slider").value = state.minSim;
        document.getElementById("time-slider").value = state.maxDelta;
        document.getElementById("mode-with-rt").classList.toggle("active", mode === "with_rt");
        document.getElementById("mode-non-rt").classList.toggle("active", mode === "non_rt");
        render();
    }

    function activateTab(tabId) {
        document.querySelectorAll(".nav-link").forEach(button => button.classList.toggle("active", button.dataset.tab === tabId));
        document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.toggle("active", pane.id === tabId));
    }

    document.getElementById("mode-with-rt").onclick = () => setMode("with_rt");
    document.getElementById("mode-non-rt").onclick = () => setMode("non_rt");
    document.getElementById("sim-slider").oninput = event => {
        state.minSim = Number(event.target.value);
        state.selectedCluster = null;
        state.selectedNode = null;
        render();
    };
    document.getElementById("time-slider").oninput = event => {
        state.maxDelta = Number(event.target.value);
        state.selectedCluster = null;
        state.selectedNode = null;
        render();
    };
    document.getElementById("size-slider").oninput = event => {
        state.nodeSizeMultiplier = Number(event.target.value);
        document.getElementById("size-value").innerText = state.nodeSizeMultiplier.toFixed(1) + "x";
        renderNetwork();
    };
    document.querySelectorAll(".nav-link").forEach(button => {
        button.onclick = () => activateTab(button.dataset.tab);
    });

    renderDataTab();
    setMode("with_rt");
</script>
</body>
</html>
"""
    return (
        html.replace("__DATA_JSON__", js_json(payload))
        .replace("__PALETTE_JSON__", js_json(PALETTE))
    )


def generate_final_dashboard(folder_path=DEFAULT_DATA_DIR, output_filename=OUTPUT_FILENAME):
    print("Membuat finale dashboard interaktif...")
    df, relation_df, evidence_df = load_inputs(folder_path)
    payload = {
        "summary": build_summary(df, relation_df, evidence_df),
        "nodes": build_nodes(df),
        "modes": build_mode_payload(relation_df, evidence_df),
        "sensitivity_reference": sensitivity_reference(evidence_df),
    }

    output_path = os.path.join(folder_path, output_filename)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(render_html_v2(payload))
    print(f"[SUKSES] Finale dashboard tersimpan di: {output_path}")
    return output_path


if __name__ == "__main__":
    data_dir = os.environ.get("TEGRAF_DATA_DIR", DEFAULT_DATA_DIR)
    generate_final_dashboard(data_dir)
