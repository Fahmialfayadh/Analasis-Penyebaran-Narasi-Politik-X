import pandas as pd
from pyvis.network import Network
import os

def generate_rt_only_html():
    folder_path = "data/DE-sample-X-capres2024/DE-sample-X-capres2024"
    evidence_path = os.path.join(folder_path, "relation_evidence.csv")

    print(f"Membaca data dari {evidence_path}...")
    evidence_df = pd.read_csv(evidence_path)

    # Filter khusus retweet
    print("Memfilter edge khusus Retweet...")
    rt_df = evidence_df[evidence_df["edge_type"].fillna("").astype(str).str.lower().eq("retweet")].copy()

    # Agregasi edge (hitung jumlah RT antar akun)
    edges_df = rt_df.groupby(["Source", "Target"]).size().reset_index(name="Weight")
    
    print(f"Ditemukan {len(edges_df)} edge retweet unik dari {len(rt_df)} bukti mentah.")

    # Inisialisasi PyVis Network (full screen, latar putih)
    net = Network(height="100vh", width="100%", bgcolor="#ffffff", font_color="black")

    # Tambahkan nodes
    nodes = set(edges_df["Source"]).union(set(edges_df["Target"]))
    for node in nodes:
        net.add_node(node, label=str(node), title=str(node), color="#d97706", size=15)

    # Tambahkan edges
    for _, row in edges_df.iterrows():
        net.add_edge(row["Source"], row["Target"], value=row["Weight"], color="#d97706")

    # Konfigurasi physics agar grafis menyebar bagus seperti sarang laba-laba
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "edges": {
        "smooth": {
          "type": "continuous"
        }
      }
    }
    """)

    output_path = os.path.join(folder_path, "visualisasi_rt_only.html")
    net.write_html(output_path)
    print(f"Sukses! File HTML disimpan di: {output_path}")

if __name__ == "__main__":
    generate_rt_only_html()
