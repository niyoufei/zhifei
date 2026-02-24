from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SUPPORTED_EXTENSIONS = {".json", ".md", ".markdown", ".xml", ".csv"}
DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_DB_PATH = Path("backend/data/autoplan/v2/knowledge_graph.sqlite3")


@dataclass
class ParsedNode:
    uid: str
    title: str
    body: str
    tags: List[str]
    keywords: List[str]
    payload_json: str


def _sha256_bytes(content: bytes) -> str:
    h = hashlib.sha256()
    h.update(content)
    return h.hexdigest()


def _normalize_term(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _tokenize(text: str) -> List[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_\-/]{1,}|\d+(?:\.\d+)?", text or "")
    out: List[str] = []
    seen = set()
    for part in parts:
        term = _normalize_term(part)
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _ensure_ascii_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return json.dumps({"error": "payload_not_serializable"}, ensure_ascii=False)


def _flatten_scalars(obj: Any, *, max_items: int = 180) -> List[str]:
    lines: List[str] = []

    def walk(node: Any, path: str) -> None:
        if len(lines) >= max_items:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if len(lines) >= max_items:
                    return
                next_path = f"{path}.{key}" if path else str(key)
                if isinstance(value, (dict, list)):
                    walk(value, next_path)
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{next_path}: {text}")
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if len(lines) >= max_items:
                    return
                next_path = f"{path}[{idx}]" if path else f"[{idx}]"
                if isinstance(value, (dict, list)):
                    walk(value, next_path)
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{next_path}: {text}")
        else:
            text = str(node).strip()
            if text:
                lines.append(f"{path}: {text}" if path else text)

    walk(obj, "")
    return lines


def _extract_terms(raw: Any) -> List[str]:
    out: List[str] = []
    if isinstance(raw, str):
        out.extend(_tokenize(raw))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.extend(_tokenize(item))
            elif item is not None:
                out.extend(_tokenize(str(item)))
    elif isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, (str, list)):
                out.extend(_extract_terms(value))
    elif raw is not None:
        out.extend(_tokenize(str(raw)))

    uniq: List[str] = []
    seen = set()
    for term in out:
        if term in seen:
            continue
        seen.add(term)
        uniq.append(term)
    return uniq[:40]


def _safe_title(source_name: str, payload: Dict[str, Any], fallback: str) -> str:
    candidates = [
        payload.get("title"),
        payload.get("name"),
        payload.get("node_id"),
        payload.get("id"),
        payload.get("domain"),
        payload.get("category"),
        fallback,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            return text[:120]
    return source_name


def _parse_markdown(path: Path) -> List[ParsedNode]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    nodes: List[ParsedNode] = []

    current_title = path.stem
    current_lines: List[str] = []

    def flush() -> None:
        if not current_lines:
            return
        body = "\n".join(current_lines).strip()
        if len(body) < 20:
            return
        uid = hashlib.sha1(f"{path}::{current_title}".encode("utf-8")).hexdigest()[:20]
        tokens = _tokenize(f"{current_title} {body}")
        nodes.append(
            ParsedNode(
                uid=uid,
                title=current_title,
                body=body[:6000],
                tags=_extract_terms(path.stem),
                keywords=tokens[:24],
                payload_json=_ensure_ascii_json({"type": "markdown", "title": current_title}),
            )
        )

    for line in lines:
        if line.lstrip().startswith("#"):
            flush()
            current_title = re.sub(r"^#+\s*", "", line).strip() or path.stem
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    if not nodes and text.strip():
        tokens = _tokenize(text)
        uid = hashlib.sha1(f"{path}::fallback".encode("utf-8")).hexdigest()[:20]
        nodes.append(
            ParsedNode(
                uid=uid,
                title=path.stem,
                body=text[:6000],
                tags=_extract_terms(path.stem),
                keywords=tokens[:24],
                payload_json=_ensure_ascii_json({"type": "markdown"}),
            )
        )

    return nodes


def _parse_csv(path: Path) -> List[ParsedNode]:
    nodes: List[ParsedNode] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            clean = {k: v for k, v in row.items() if v not in (None, "")}
            if not clean:
                continue
            title = _safe_title(path.stem, clean, f"row_{idx}")
            body = "\n".join(f"{k}: {v}" for k, v in clean.items())
            uid = hashlib.sha1(f"{path}::{idx}".encode("utf-8")).hexdigest()[:20]
            terms = _extract_terms(clean)
            nodes.append(
                ParsedNode(
                    uid=uid,
                    title=title,
                    body=body[:6000],
                    tags=_extract_terms([path.stem, "csv"]),
                    keywords=terms[:24],
                    payload_json=_ensure_ascii_json(clean),
                )
            )
    return nodes


def _parse_xml(path: Path) -> List[ParsedNode]:
    nodes: List[ParsedNode] = []
    root = ET.parse(path).getroot()

    def walk(elem: ET.Element, x_path: str) -> None:
        text_parts: List[str] = []
        if elem.attrib:
            for key, value in elem.attrib.items():
                if value is not None:
                    text_parts.append(f"@{key}: {value}")
        if elem.text and elem.text.strip():
            text_parts.append(elem.text.strip())
        for child in elem:
            if child.text and child.text.strip():
                text_parts.append(f"{child.tag}: {child.text.strip()}")

        body = "\n".join(text_parts).strip()
        if len(body) >= 20:
            uid = hashlib.sha1(f"{path}::{x_path}".encode("utf-8")).hexdigest()[:20]
            title = elem.attrib.get("name") or elem.attrib.get("id") or elem.tag
            terms = _tokenize(f"{title} {body} {' '.join(elem.attrib.keys())}")
            nodes.append(
                ParsedNode(
                    uid=uid,
                    title=str(title)[:120],
                    body=body[:6000],
                    tags=_extract_terms([path.stem, elem.tag]),
                    keywords=terms[:24],
                    payload_json=_ensure_ascii_json({"tag": elem.tag, "path": x_path, "attrs": elem.attrib}),
                )
            )

        for idx, child in enumerate(elem):
            walk(child, f"{x_path}/{child.tag}[{idx}]")

    walk(root, f"/{root.tag}")
    return nodes


def _parse_json(path: Path) -> List[ParsedNode]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes: List[ParsedNode] = []

    def walk(node: Any, pointer: str, inherited_tags: List[str], inherited_keywords: List[str]) -> None:
        local_tags = list(inherited_tags)
        local_keywords = list(inherited_keywords)

        if isinstance(node, dict):
            for tag_key in ("domain", "category", "type", "scene", "qt_tag", "tags", "labels"):
                if tag_key in node:
                    local_tags.extend(_extract_terms(node.get(tag_key)))
            for kw_key in ("keywords", "keyword", "trigger_keywords", "name", "title"):
                if kw_key in node:
                    local_keywords.extend(_extract_terms(node.get(kw_key)))

            has_identity = any(k in node for k in ("node_id", "name", "title", "id"))
            if has_identity:
                body_lines = _flatten_scalars(node, max_items=120)
                body = "\n".join(body_lines).strip()
                if len(body) >= 30:
                    node_id = str(node.get("node_id") or node.get("id") or pointer)
                    title = _safe_title(path.stem, node, pointer)
                    uid = hashlib.sha1(f"{path}::{node_id}".encode("utf-8")).hexdigest()[:20]
                    terms = _tokenize(f"{title} {body}")
                    merged_keywords = local_keywords + terms
                    merged_tags = local_tags + _extract_terms(path.stem)
                    nodes.append(
                        ParsedNode(
                            uid=uid,
                            title=title,
                            body=body[:12000],
                            tags=_dedupe_terms(merged_tags)[:24],
                            keywords=_dedupe_terms(merged_keywords)[:32],
                            payload_json=_ensure_ascii_json({"pointer": pointer, "node_id": node_id, "title": title}),
                        )
                    )

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, f"{pointer}.{key}", local_tags, local_keywords)

        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if isinstance(value, (dict, list)):
                    walk(value, f"{pointer}[{idx}]", local_tags, local_keywords)

    walk(raw, "$", _extract_terms(path.stem), [])

    if not nodes:
        body = "\n".join(_flatten_scalars(raw, max_items=160)).strip()
        if body:
            uid = hashlib.sha1(f"{path}::root".encode("utf-8")).hexdigest()[:20]
            nodes.append(
                ParsedNode(
                    uid=uid,
                    title=path.stem,
                    body=body[:12000],
                    tags=_extract_terms(path.stem),
                    keywords=_tokenize(body)[:32],
                    payload_json=_ensure_ascii_json({"pointer": "$"}),
                )
            )

    return nodes


def _dedupe_terms(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        term = _normalize_term(value)
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


class KnowledgeGraphIndex:
    """SQLite-backed unified knowledge graph index with keyword/tag retrieval API."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    ext TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    imported_at INTEGER NOT NULL,
                    node_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    node_uid TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, node_uid)
                );

                CREATE TABLE IF NOT EXISTS node_tags (
                    node_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    UNIQUE(node_id, tag),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS node_keywords (
                    node_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    UNIQUE(node_id, keyword),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_document_id ON nodes(document_id);
                CREATE INDEX IF NOT EXISTS idx_node_tags_tag ON node_tags(tag);
                CREATE INDEX IF NOT EXISTS idx_node_keywords_keyword ON node_keywords(keyword);
                """
            )

            try:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        node_uid,
                        title,
                        body,
                        tags,
                        keywords
                    );
                    """
                )
            except sqlite3.OperationalError as exc:
                raise RuntimeError(
                    "sqlite build does not support FTS5; cannot provide millisecond indexed retrieval"
                ) from exc

    def _clear_document_rows(self, conn: sqlite3.Connection, document_id: int) -> None:
        rows = conn.execute("SELECT id FROM nodes WHERE document_id = ?", (document_id,)).fetchall()
        node_ids = [int(r[0]) for r in rows]
        if node_ids:
            marks = ",".join("?" for _ in node_ids)
            conn.execute(f"DELETE FROM node_tags WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM node_keywords WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM nodes_fts WHERE rowid IN ({marks})", node_ids)
        conn.execute("DELETE FROM nodes WHERE document_id = ?", (document_id,))

    def _parse_file(self, path: Path) -> List[ParsedNode]:
        ext = path.suffix.lower()
        if ext == ".json":
            return _parse_json(path)
        if ext in {".md", ".markdown"}:
            return _parse_markdown(path)
        if ext == ".xml":
            return _parse_xml(path)
        if ext == ".csv":
            return _parse_csv(path)
        return []

    def ingest_directory(
        self,
        root_dir: Path | str = DEFAULT_KG_ROOT,
        *,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        root = Path(root_dir)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"knowledge graph root not found: {root}")

        start = time.perf_counter()
        parsed_files = 0
        skipped_files = 0
        total_nodes = 0

        files = [
            p
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        with self._connect() as conn:
            for path in files:
                data = path.read_bytes()
                sha = _sha256_bytes(data)
                rec = conn.execute(
                    "SELECT id, sha256 FROM documents WHERE source_path = ?",
                    (str(path),),
                ).fetchone()
                if rec and (str(rec["sha256"]) == sha) and not force_reindex:
                    skipped_files += 1
                    continue

                if rec:
                    doc_id = int(rec["id"])
                    self._clear_document_rows(conn, doc_id)
                else:
                    conn.execute(
                        """
                        INSERT INTO documents(source_path, file_name, ext, sha256, imported_at, node_count)
                        VALUES(?, ?, ?, ?, ?, 0)
                        """,
                        (str(path), path.name, path.suffix.lower(), sha, int(time.time())),
                    )
                    doc_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

                nodes = self._parse_file(path)
                inserted = 0
                for node in nodes:
                    cursor = conn.execute(
                        """
                        INSERT OR REPLACE INTO nodes(document_id, node_uid, title, body, payload_json)
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (doc_id, node.uid, node.title, node.body, node.payload_json),
                    )
                    node_id = int(cursor.lastrowid)
                    if node_id <= 0:
                        row = conn.execute(
                            "SELECT id FROM nodes WHERE document_id = ? AND node_uid = ?",
                            (doc_id, node.uid),
                        ).fetchone()
                        if not row:
                            continue
                        node_id = int(row["id"])

                    tags = _dedupe_terms(node.tags)
                    keywords = _dedupe_terms(node.keywords)
                    for tag in tags:
                        conn.execute(
                            "INSERT OR IGNORE INTO node_tags(node_id, tag) VALUES(?, ?)",
                            (node_id, tag),
                        )
                    for keyword in keywords:
                        conn.execute(
                            "INSERT OR IGNORE INTO node_keywords(node_id, keyword) VALUES(?, ?)",
                            (node_id, keyword),
                        )
                    conn.execute(
                        "INSERT OR REPLACE INTO nodes_fts(rowid, node_uid, title, body, tags, keywords) VALUES(?, ?, ?, ?, ?, ?)",
                        (node_id, node.uid, node.title, node.body, " ".join(tags), " ".join(keywords)),
                    )
                    inserted += 1

                conn.execute(
                    """
                    UPDATE documents
                    SET sha256 = ?, imported_at = ?, node_count = ?
                    WHERE id = ?
                    """,
                    (sha, int(time.time()), inserted, doc_id),
                )

                parsed_files += 1
                total_nodes += inserted

            conn.commit()

        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": True,
            "root": str(root),
            "db_path": str(self.db_path),
            "files_total": len(files),
            "files_parsed": parsed_files,
            "files_skipped": skipped_files,
            "nodes_indexed": total_nodes,
            "duration_ms": duration_ms,
        }

    def _candidate_ids_by_terms(
        self,
        conn: sqlite3.Connection,
        *,
        tags: List[str],
        keywords: List[str],
    ) -> Optional[set[int]]:
        candidate: Optional[set[int]] = None

        if tags:
            marks = ",".join("?" for _ in tags)
            rows = conn.execute(
                f"SELECT DISTINCT node_id FROM node_tags WHERE tag IN ({marks})",
                tuple(tags),
            ).fetchall()
            tag_ids = {int(r[0]) for r in rows}
            candidate = tag_ids if candidate is None else candidate.intersection(tag_ids)

        if keywords:
            marks = ",".join("?" for _ in keywords)
            rows = conn.execute(
                f"SELECT DISTINCT node_id FROM node_keywords WHERE keyword IN ({marks})",
                tuple(keywords),
            ).fetchall()
            kw_ids = {int(r[0]) for r in rows}
            candidate = kw_ids if candidate is None else candidate.intersection(kw_ids)

        return candidate

    def _fts_rank_map(
        self,
        conn: sqlite3.Connection,
        query: str,
        *,
        limit: int,
    ) -> Dict[int, float]:
        tokens = _tokenize(query)
        if not tokens:
            return {}
        # OR query keeps recall high, then we refine by exact tags/keywords scores.
        fts_query = " OR ".join(tokens[:16])
        rows = conn.execute(
            """
            SELECT rowid, bm25(nodes_fts) AS rank
            FROM nodes_fts
            WHERE nodes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, int(limit)),
        ).fetchall()
        return {int(r[0]): float(r[1]) for r in rows}

    def search(
        self,
        *,
        query: str = "",
        tags: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        top_k: int = 12,
    ) -> Dict[str, Any]:
        top_k = max(1, min(int(top_k or 12), 100))
        norm_tags = _dedupe_terms(tags or [])
        norm_keywords = _dedupe_terms(keywords or [])

        with self._connect() as conn:
            candidates = self._candidate_ids_by_terms(conn, tags=norm_tags, keywords=norm_keywords)
            rank_map = self._fts_rank_map(conn, query, limit=max(120, top_k * 6)) if query.strip() else {}

            if candidates is not None and rank_map:
                target_ids = candidates.intersection(set(rank_map.keys()))
                if not target_ids and candidates:
                    target_ids = candidates
            elif candidates is not None:
                target_ids = candidates
            elif rank_map:
                target_ids = set(rank_map.keys())
            else:
                target_ids = set()

            where_sql = ""
            params: List[Any] = []
            if target_ids:
                marks = ",".join("?" for _ in target_ids)
                where_sql = f"WHERE n.id IN ({marks})"
                params.extend(sorted(target_ids))

            rows = conn.execute(
                f"""
                SELECT
                    n.id,
                    n.node_uid,
                    n.title,
                    n.body,
                    n.payload_json,
                    d.file_name,
                    d.source_path,
                    COALESCE(GROUP_CONCAT(DISTINCT t.tag), '') AS tags_csv,
                    COALESCE(GROUP_CONCAT(DISTINCT k.keyword), '') AS keywords_csv
                FROM nodes n
                JOIN documents d ON d.id = n.document_id
                LEFT JOIN node_tags t ON t.node_id = n.id
                LEFT JOIN node_keywords k ON k.node_id = n.id
                {where_sql}
                GROUP BY n.id
                ORDER BY n.id DESC
                LIMIT ?
                """,
                tuple(params + [max(top_k * 12, 200)]),
            ).fetchall()

        query_tokens = _tokenize(query)
        results: List[Dict[str, Any]] = []
        for row in rows:
            body = str(row["body"] or "")
            title = str(row["title"] or "")
            tags_row = [t for t in str(row["tags_csv"] or "").split(",") if t]
            keywords_row = [k for k in str(row["keywords_csv"] or "").split(",") if k]

            score = 0.0
            for tag in norm_tags:
                if tag in tags_row:
                    score += 10.0
            for keyword in norm_keywords:
                if keyword in keywords_row:
                    score += 8.0
                elif keyword in _normalize_term(title) or keyword in _normalize_term(body):
                    score += 5.0
            if query_tokens:
                merged = f"{title}\n{body}".lower()
                score += sum(1.5 for token in query_tokens if token in merged)
            row_id = int(row["id"])
            if row_id in rank_map:
                # bm25 lower is better, convert to positive score bonus.
                score += max(0.0, 20.0 - min(20.0, abs(rank_map[row_id]) * 4.0))

            if norm_tags or norm_keywords or query_tokens:
                if score <= 0:
                    continue

            snippet = body[:260]
            results.append(
                {
                    "node_id": row["node_uid"],
                    "title": title,
                    "snippet": snippet,
                    "tags": tags_row[:12],
                    "keywords": keywords_row[:18],
                    "source_file": row["file_name"],
                    "source_path": row["source_path"],
                    "score": round(score, 4),
                    "payload": json.loads(row["payload_json"]),
                }
            )

        results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return {
            "ok": True,
            "query": query,
            "tags": norm_tags,
            "keywords": norm_keywords,
            "total": len(results),
            "results": results[:top_k],
            "db_path": str(self.db_path),
        }


def ingest_knowledge_graph(
    root_dir: Path | str = DEFAULT_KG_ROOT,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
    force_reindex: bool = False,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.ingest_directory(root_dir=root_dir, force_reindex=force_reindex)


def search_graph_index(
    *,
    query: str = "",
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    top_k: int = 12,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.search(query=query, tags=tags, keywords=keywords, top_k=top_k)
