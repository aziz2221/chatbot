"""Outils sécurisés SQL et recherche documentaire pour DataPilot."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b", re.IGNORECASE)


class SQLValidationError(ValueError):
    """Requête refusée avant exécution."""


def validate_sql(sql: str) -> str:
    cleaned = str(sql or "").strip()
    cleaned = re.sub(r"^```(?:sql)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.rstrip().rstrip(";").strip()
    if not cleaned:
        raise SQLValidationError("requête vide")
    if ";" in cleaned:
        raise SQLValidationError("une seule instruction SQL est autorisée")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, flags=re.IGNORECASE):
        raise SQLValidationError("seules les requêtes SELECT ou WITH sont autorisées")
    if FORBIDDEN.search(cleaned):
        raise SQLValidationError("mot-clé SQL interdit")
    return cleaned


def format_results(columns: list[str], rows: list[tuple], truncated: bool = False) -> str:
    if not rows:
        return "0 ligne(s) : aucun résultat."
    def cell(value):
        if value is None:
            return "NULL"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = [f"{len(rows)} ligne(s) :", "| " + " | ".join(columns) + " |",
             "|" + "|".join("---" for _ in columns) + "|"]
    lines.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    if truncated:
        lines.append(f"Résultat tronqué à {len(rows)} lignes.")
    return "\n".join(lines)


class SQLTool:
    name = "query_database"
    description = "Exécute UNE requête SQL SELECT (SQLite) sur la base e-commerce."

    def __init__(self, db_path, max_rows: int = 50) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.is_file():
            raise FileNotFoundError(f"Base introuvable : {self.db_path}. Lancez data/create_db.py.")
        self.max_rows = max_rows

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
        return conn

    def run(self, sql: str, params=()) -> str:
        try:
            query = validate_sql(sql)
        except SQLValidationError as exc:
            return f"ERREUR : requête refusée — {exc}"
        try:
            with self._connect() as conn:
                cursor = conn.execute(query, tuple(params))
                columns = [d[0] for d in cursor.description or []]
                rows = cursor.fetchmany(self.max_rows + 1)
            truncated = len(rows) > self.max_rows
            return format_results(columns, rows[:self.max_rows], truncated)
        except sqlite3.Error as exc:
            return f"ERREUR SQL : {exc}. Corrigez la requête et réessayez."

    def get_schema(self) -> str:
        with self._connect() as conn:
            rows = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name").fetchall()
        return "\n\n".join(row[0] for row in rows)


@dataclass
class Chunk:
    text: str
    source: str
    section: str


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap doit être positif et strictement inférieur à chunk_size")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        limit = min(start + chunk_size, len(text))
        end = limit
        if limit < len(text):
            space = text.rfind(" ", start, limit + 1)
            if space > start:
                end = space
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        # Repartir au début d'un mot entier pour conserver des morceaux lisibles.
        next_space = text.find(" ", next_start)
        start = next_space + 1 if next_space >= 0 else next_start
    return chunks


def chunk_markdown(text: str, source: str, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source
    chunks = []
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for index, part in enumerate(parts):
        if index == 0:
            section, content = "Introduction", part
        else:
            section, _, content = part.partition("\n")
            section = section.strip()
        content = content.strip()
        if not content or (index == 0 and not re.sub(r"^#.*(?:\n|$)", "", content).strip()):
            continue
        for piece in chunk_text(content, chunk_size, overlap):
            chunks.append(Chunk(f"[{title} — {section}] {piece}", source, section))
    return chunks


def load_corpus(docs_dir, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    files = sorted(Path(docs_dir).glob("*.md"))
    if not files:
        raise FileNotFoundError(f"Aucun document Markdown dans {docs_dir}")
    return [chunk for path in files for chunk in chunk_markdown(path.read_text(encoding="utf-8"), path.name, chunk_size, overlap)]


class DocSearchTool:
    name = "search_docs"
    description = "Recherche dans la documentation métier (KPI, retours, segmentation, données, livraison, reporting)."

    def __init__(self, chunks: list[Chunk], embedder, top_k: int = 3) -> None:
        import faiss
        self.chunks, self.embedder, self.top_k = chunks, embedder, top_k
        vectors = self._embed([c.text for c in chunks])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        if len(vectors):
            self.index.add(vectors)

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = self.embedder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vectors, dtype="float32")

    def search(self, query: str, k: int | None = None) -> list[tuple[float, Chunk]]:
        if not self.chunks:
            return []
        count = min(self.top_k if k is None else max(0, k), len(self.chunks))
        if count == 0:
            return []
        scores, ids = self.index.search(self._embed([query]), count)
        return [(float(score), self.chunks[int(idx)]) for score, idx in zip(scores[0], ids[0]) if idx >= 0]

    def run(self, query: str) -> str:
        results = self.search(query)
        if not results:
            return "Aucun passage pertinent trouvé dans la documentation."
        return "\n\n".join(f"[Passage {i} — source : {chunk.source}, section « {chunk.section} », score {score:.2f}]\n{chunk.text}" for i, (score, chunk) in enumerate(results, 1))


def load_embedder(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)
