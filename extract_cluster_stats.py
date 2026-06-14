import os
import math
import numpy as np
import pandas as pd
from generate_final_dashboard import aggregate_non_rt_edges, row_to_edge, build_communities, load_inputs

def status_info(size, density, evidence):
    score = density * math.log2(size + 1)
    if size < 5 or evidence < 5:
        return {"status": "Indikasi Lemah", "rank": 1, "score": score}
    if score >= 1.5:
        return {"status": "Koordinasi Kuat", "rank": 3, "score": score}
    if score >= 0.8:
        return {"status": "Perlu Investigasi", "rank": 2, "score": score}
    return {"status": "Rendah", "rank": 0, "score": score}

def main():
    folder_path = "data/DE-sample-X-capres2024/DE-sample-X-capres2024"
    df, relation_df, evidence_df = load_inputs(folder_path)
    
    df["author_followers"] = pd.to_numeric(df["author_followers"], errors="coerce").fillna(0)

    # Calculate account age in days
    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce", utc=True)
    df["author_created_at"] = pd.to_datetime(df["author_created_at"], errors="coerce", utc=True)
    df["account_age_days"] = (df["date_created"] - df["author_created_at"]).dt.total_seconds() / (24 * 3600)
    df["account_age_days"] = df["account_age_days"].fillna(0)
    
    # 1. Generate ALL non-rt edges (unfiltered)
    non_rt_df = aggregate_non_rt_edges(evidence_df)
    non_rt_edges = [row_to_edge(row, "non_rt") for _, row in non_rt_df.iterrows()]
    
    # 2. Build communities on unfiltered edges
    community_map = build_communities(non_rt_edges, resolution=6.5)
    
    # 3. Filter edges like JS does (minSim=0.75, maxDelta=300)
    filtered_edges = [
        e for e in non_rt_edges 
        if e["avg_similarity"] >= 0.75 and e["min_delta"] <= 300
    ]
    
    # 4. Group into clusters
    groups = {}
    for edge in filtered_edges:
        src = edge["source"]
        tgt = edge["target"]
        src_comm = int(community_map.get(src, -1))
        tgt_comm = int(community_map.get(tgt, -1))
        
        for node, cid in [(src, src_comm), (tgt, tgt_comm)]:
            if cid not in groups:
                groups[cid] = {"id": cid, "nodes": set(), "edges": []}
            groups[cid]["nodes"].add(node)
            
        if src_comm == tgt_comm:
            groups[src_comm]["edges"].append(edge)
            
    # 5. Compute stats and sort
    clusters = []
    for cid, group in groups.items():
        size = len(group["nodes"])
        if cid < 0 or size < 3 or len(group["edges"]) == 0:
            continue
            
        possible = size * (size - 1) / 2
        density = len(group["edges"]) / possible if possible > 0 else 0
        evidence = sum(e["edge_count"] for e in group["edges"])
        avg_sim = sum(e["avg_similarity"] for e in group["edges"]) / len(group["edges"])
        
        status = status_info(size, density, evidence)
        
        clusters.append({
            "id": cid,
            "size": size,
            "density": density,
            "evidence": evidence,
            "edgeCount": len(group["edges"]),
            "score": status["score"],
            "rank": status["rank"],
            "status": status["status"],
            "avgSim": avg_sim,
            "medianDelta": np.median([e["min_delta"] for e in group["edges"]]),
            "nodes": group["nodes"]
        })
        
    # Sort like JS: b.rank - a.rank || b.evidence - a.evidence || b.score - a.score
    clusters.sort(key=lambda x: (x["rank"], x["evidence"], x["score"]), reverse=True)
    
    # Generate MD
    md_content = "# Detail Statistik Cluster 0, 1, dan 2 (Non-RT)\n\n"
    md_content += "Berikut adalah statistik detail untuk 3 kluster teratas pada mode **Tanpa RT** (Sesuai dengan urutan dan filter backbone di Dashboard).\n\n"
    
    for idx, c in enumerate(clusters[:3]):
        nodes_in_cluster = list(c["nodes"])
        
        # Followers and Account Age
        users_df = df[df["name"].astype(str).isin(nodes_in_cluster)].drop_duplicates(subset=["name"])
        followers = users_df["author_followers"].values
        account_ages = users_df["account_age_days"].values

        avg_followers = np.mean(followers) if len(followers) > 0 else 0
        median_followers = np.median(followers) if len(followers) > 0 else 0
        
        avg_age_days = np.mean(account_ages) if len(account_ages) > 0 else 0
        median_age_days = np.median(account_ages) if len(account_ages) > 0 else 0

        # Tweets
        tweets_df = df[df["name"].astype(str).isin(nodes_in_cluster)].drop_duplicates(subset=["content"]).head(5)
        
        md_content += f"## Cluster {idx} (ID Asli Python: {c['id']})\n\n"
        md_content += f"### Statistik Dasar\n"
        md_content += f"- **Status**: {c['status']}\n"
        md_content += f"- **Jumlah Akun**: {c['size']}\n"
        md_content += f"- **Jumlah Edge (Bukti)**: {c['edgeCount']} ({c['evidence']} raw evidence)\n"
        md_content += f"- **Kepadatan (Density)**: {c['density']:.4f}\n"
        md_content += f"- **Rata-rata Kemiripan Teks**: {(c['avgSim'] * 100):.2f}%\n"
        md_content += f"- **Median Jeda Waktu Minimum**: {c['medianDelta']:.1f} detik\n"
        md_content += f"- **Rata-rata Followers**: {avg_followers:.2f}\n"
        md_content += f"- **Median Followers**: {median_followers:.2f}\n"
        md_content += f"- **Rata-rata Umur Akun**: {avg_age_days:.1f} hari\n"
        md_content += f"- **Median Umur Akun**: {median_age_days:.1f} hari\n\n"
        
        md_content += f"### Contoh Tweet\n"
        for i, (_, row) in enumerate(tweets_df.iterrows()):
            md_content += f"{i+1}. **@{row['name']}**: > {row['content']}\n\n"
            
            
        md_content += "---\n\n"
        
    with open("cluster_stats.md", "w") as f:
        f.write(md_content)
        
if __name__ == "__main__":
    main()
