"""Mesure le hit rate documentaire sur le jeu fourni par le guide."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from tools import DocSearchTool, load_corpus, load_embedder

JEU_EVAL = [
    ("Combien de jours pour retourner un article ?", "02_politique_retours.md"),
    ("Comment est défini le chiffre d'affaires ?", "01_glossaire_kpi.md"),
    ("Quels sont les critères pour devenir VIP ?", "03_segmentation_clients.md"),
    ("Quelles colonnes contient la table lignes_commande ?", "04_dictionnaire_donnees.md"),
    ("À partir de quel montant la livraison est-elle gratuite ?", "05_livraison.md"),
    ("Peut-on afficher l'email d'un client dans un rapport ?", "06_regles_reporting.md"),
    ("Qu'est-ce qu'un client actif ?", "01_glossaire_kpi.md"),
    ("Les produits de beauté peuvent-ils être retournés ?", "02_politique_retours.md"),
]


def main():
    search = DocSearchTool(load_corpus(config.DOCS_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP),
                           load_embedder(config.EMBEDDING_MODEL), config.TOP_K)
    for k in (1, 3):
        hits = sum(any(chunk.source == expected for _, chunk in search.search(question, k=k))
                   for question, expected in JEU_EVAL)
        print(f"Hit rate @{k}: {hits}/{len(JEU_EVAL)} = {100 * hits / len(JEU_EVAL):.1f}%")


if __name__ == "__main__":
    main()
