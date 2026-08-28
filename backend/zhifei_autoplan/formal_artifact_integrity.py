from __future__ import annotations

"""Side-effect-free integrity checks for formal OOXML delivery artifacts.

The validator deliberately uses only the Python standard library.  In
particular, importing it cannot initialise a model provider, start a
subprocess, access the network, or write a receipt.  The package is parsed from
the same ``O_NOFOLLOW`` file descriptor whose identity and bytes are checked
against the caller's existing witness.
"""

import hashlib
import json
import os
import posixpath
import re
import stat
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any, BinaryIO, Literal
from xml.etree import ElementTree

ArtifactKind = Literal["docx", "xlsx"]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
_MAX_MEMBER_COUNT = 20_000
_MAX_UNCOMPRESSED_BYTES = 4 * 1024 * 1024 * 1024
_MAX_XML_PART_BYTES = 128 * 1024 * 1024

_CONTENT_TYPES_NS = (
    "http://schemas.openxmlformats.org/package/2006/content-types"
)
_PACKAGE_RELATIONSHIPS_NS = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
_OFFICE_RELATIONSHIPS_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
_WORDPROCESSING_NS = (
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
)
_SPREADSHEET_NS = (
    "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
)
_OFFICE_DOCUMENT_RELATIONSHIP = f"{_OFFICE_RELATIONSHIPS_NS}/officeDocument"
_WORKSHEET_RELATIONSHIP = f"{_OFFICE_RELATIONSHIPS_NS}/worksheet"
_DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document.main+xml"
)
_XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet.main+xml"
)
_WORKSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.worksheet+xml"
)


class FormalArtifactIntegrityError(RuntimeError):
    """Raised when a formal artifact cannot be trusted as the declared OOXML."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode),
        left.st_uid,
        left.st_dev,
        left.st_ino,
        left.st_size,
        left.st_mtime_ns,
        left.st_ctime_ns,
    ) == (
        stat.S_IFMT(right.st_mode),
        right.st_uid,
        right.st_dev,
        right.st_ino,
        right.st_size,
        right.st_mtime_ns,
        right.st_ctime_ns,
    )


def _hash_handle(handle: BinaryIO) -> str:
    handle.seek(0)
    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    handle.seek(0)
    return digest.hexdigest()


def _safe_package_name(raw_name: str, *, allow_directory: bool = True) -> str:
    name = str(raw_name or "")
    if not name or "\x00" in name or "\\" in name or ":" in name:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML包包含无效部件名称",
        )
    is_directory = name.endswith("/")
    if is_directory:
        if not allow_directory:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML关系不能指向目录",
            )
        name = name[:-1]
    decoded = urllib.parse.unquote(name)
    if (
        not name
        or name.startswith("/")
        or decoded.startswith("/")
        or "\\" in decoded
    ):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML包部件名称越出包根目录",
        )
    raw_parts = name.split("/")
    decoded_parts = decoded.split("/")
    if (
        any(part in {"", ".", ".."} for part in raw_parts)
        or any(part in {"", ".", ".."} for part in decoded_parts)
        or posixpath.normpath(name) != name
        or posixpath.normpath(decoded) != decoded
    ):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML包部件名称包含路径越界或歧义",
        )
    return name


def _content_type_part_name(raw_name: Any) -> str:
    value = str(raw_name or "")
    if not value.startswith("/") or value.startswith("//"):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML Content_Types部件名称无效",
        )
    return _safe_package_name(value[1:], allow_directory=False)


def _relationship_owner(rels_name: str) -> str:
    if rels_name == "_rels/.rels":
        return ""
    rels_dir = posixpath.dirname(rels_name)
    if posixpath.basename(rels_dir) != "_rels":
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML关系部件位置无效",
        )
    owner_name = posixpath.basename(rels_name)[: -len(".rels")]
    owner_dir = posixpath.dirname(rels_dir)
    owner = posixpath.join(owner_dir, owner_name)
    return _safe_package_name(owner, allow_directory=False)


def _relationship_target(owner_part: str, raw_target: Any) -> str:
    target = str(raw_target or "")
    if not target or "\x00" in target or "\\" in target:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML内部关系目标无效",
        )
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML内部关系目标不是包内部件",
        )
    decoded = urllib.parse.unquote(parsed.path)
    if decoded.startswith("/"):
        candidate = decoded[1:]
    else:
        candidate = posixpath.join(posixpath.dirname(owner_part), decoded)
    normalised = posixpath.normpath(candidate)
    if normalised in {"", ".", ".."} or normalised.startswith("../"):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML内部关系目标越出包根目录",
        )
    return _safe_package_name(normalised, allow_directory=False)


def _read_xml(
    archive: zipfile.ZipFile,
    name: str,
    *,
    info_by_name: dict[str, zipfile.ZipInfo],
) -> ElementTree.Element:
    info = info_by_name.get(name)
    if info is None or info.is_dir() or info.file_size > _MAX_XML_PART_BYTES:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML必需XML部件缺失或超过安全大小",
        )
    try:
        raw = archive.read(info)
        return ElementTree.fromstring(raw)
    except (KeyError, RuntimeError, ValueError, ElementTree.ParseError) as exc:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML包包含不可解析的XML部件",
        ) from exc


def _inspect_members(
    archive: zipfile.ZipFile,
) -> tuple[dict[str, zipfile.ZipInfo], int, str]:
    infos = archive.infolist()
    if not infos or len(infos) > _MAX_MEMBER_COUNT:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_LIMIT_EXCEEDED",
            "OOXML包部件数量为空或超过安全上限",
        )
    info_by_name: dict[str, zipfile.ZipInfo] = {}
    casefold_names: set[str] = set()
    total_uncompressed = 0
    manifest: list[dict[str, Any]] = []
    for info in infos:
        name = _safe_package_name(info.filename)
        folded = name.casefold()
        if name in info_by_name or folded in casefold_names:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML包包含重复或大小写歧义部件",
            )
        if info.flag_bits & 0x1:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML包不得包含加密部件",
            )
        unix_mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(unix_mode):
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML包不得包含符号链接部件",
            )
        if info.file_size < 0 or info.compress_size < 0:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML包部件大小无效",
            )
        total_uncompressed += info.file_size
        if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_LIMIT_EXCEEDED",
                "OOXML包解压规模超过安全上限",
            )
        info_by_name[name] = info
        casefold_names.add(folded)
        manifest.append(
            {
                "name": name,
                "crc32": f"{info.CRC:08x}",
                "compressed_size": info.compress_size,
                "size": info.file_size,
            }
        )
    return info_by_name, total_uncompressed, _canonical_digest(manifest)


def _content_types(
    archive: zipfile.ZipFile,
    *,
    info_by_name: dict[str, zipfile.ZipInfo],
) -> dict[str, str]:
    root = _read_xml(
        archive,
        "[Content_Types].xml",
        info_by_name=info_by_name,
    )
    if root.tag != f"{{{_CONTENT_TYPES_NS}}}Types":
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML Content_Types根节点无效",
        )
    overrides: dict[str, str] = {}
    for item in root.findall(f"{{{_CONTENT_TYPES_NS}}}Override"):
        name = _content_type_part_name(item.get("PartName"))
        content_type = str(item.get("ContentType") or "").strip()
        if not content_type or name in overrides:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML Content_Types包含缺失或重复声明",
            )
        overrides[name] = content_type
    return overrides


def _relationships(
    archive: zipfile.ZipFile,
    *,
    info_by_name: dict[str, zipfile.ZipInfo],
) -> tuple[dict[str, dict[str, dict[str, str]]], int]:
    relationship_sets: dict[str, dict[str, dict[str, str]]] = {}
    relationship_count = 0
    for rels_name in sorted(
        name for name in info_by_name if name.endswith(".rels")
    ):
        owner = _relationship_owner(rels_name)
        root = _read_xml(archive, rels_name, info_by_name=info_by_name)
        if root.tag != f"{{{_PACKAGE_RELATIONSHIPS_NS}}}Relationships":
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "OOXML关系部件根节点无效",
            )
        rows: dict[str, dict[str, str]] = {}
        for item in root.findall(
            f"{{{_PACKAGE_RELATIONSHIPS_NS}}}Relationship"
        ):
            relationship_id = str(item.get("Id") or "").strip()
            relationship_type = str(item.get("Type") or "").strip()
            raw_target = str(item.get("Target") or "").strip()
            target_mode = str(item.get("TargetMode") or "Internal").strip()
            if (
                not relationship_id
                or not relationship_type
                or not raw_target
                or relationship_id in rows
            ):
                raise FormalArtifactIntegrityError(
                    "FORMAL_ARTIFACT_OOXML_INVALID",
                    "OOXML关系身份缺失或重复",
                )
            if target_mode.casefold() == "external":
                target = raw_target
            else:
                target = _relationship_target(owner, raw_target)
                if target not in info_by_name or info_by_name[target].is_dir():
                    raise FormalArtifactIntegrityError(
                        "FORMAL_ARTIFACT_OOXML_INVALID",
                        "OOXML内部关系目标不存在",
                    )
            rows[relationship_id] = {
                "type": relationship_type,
                "target": target,
                "target_mode": target_mode,
            }
            relationship_count += 1
        relationship_sets[owner] = rows
    return relationship_sets, relationship_count


def _office_document_part(
    relationship_sets: dict[str, dict[str, dict[str, str]]],
) -> str:
    root_relationships = relationship_sets.get("")
    if root_relationships is None:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML包缺少根关系部件",
        )
    candidates = [
        row
        for row in root_relationships.values()
        if row.get("type") == _OFFICE_DOCUMENT_RELATIONSHIP
    ]
    if (
        len(candidates) != 1
        or candidates[0].get("target_mode", "").casefold() == "external"
    ):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "OOXML根officeDocument关系缺失或不唯一",
        )
    return candidates[0]["target"]


def _inspect_docx(
    archive: zipfile.ZipFile,
    *,
    info_by_name: dict[str, zipfile.ZipInfo],
    overrides: dict[str, str],
    relationship_sets: dict[str, dict[str, dict[str, str]]],
) -> dict[str, Any]:
    main_part = _office_document_part(relationship_sets)
    if main_part != "word/document.xml":
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_KIND_MISMATCH",
            "OOXML包不是DOCX主文档",
        )
    if overrides.get(main_part) != _DOCX_CONTENT_TYPE:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_KIND_MISMATCH",
            "OOXML主部件Content-Type不是DOCX",
        )
    document = _read_xml(archive, main_part, info_by_name=info_by_name)
    if (
        document.tag != f"{{{_WORDPROCESSING_NS}}}document"
        or document.find(f"{{{_WORDPROCESSING_NS}}}body") is None
    ):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "DOCX主文档缺少合法Word正文",
        )
    main_bytes = archive.read(info_by_name[main_part])
    return {
        "main_part": main_part,
        "main_content_type": _DOCX_CONTENT_TYPE,
        "main_part_sha256": hashlib.sha256(main_bytes).hexdigest(),
        "body_present": True,
    }


def _inspect_xlsx(
    archive: zipfile.ZipFile,
    *,
    info_by_name: dict[str, zipfile.ZipInfo],
    overrides: dict[str, str],
    relationship_sets: dict[str, dict[str, dict[str, str]]],
) -> dict[str, Any]:
    main_part = _office_document_part(relationship_sets)
    if main_part != "xl/workbook.xml":
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_KIND_MISMATCH",
            "OOXML包不是XLSX工作簿",
        )
    if overrides.get(main_part) != _XLSX_CONTENT_TYPE:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_KIND_MISMATCH",
            "OOXML主部件Content-Type不是XLSX",
        )
    workbook = _read_xml(archive, main_part, info_by_name=info_by_name)
    if workbook.tag != f"{{{_SPREADSHEET_NS}}}workbook":
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "XLSX工作簿根节点无效",
        )
    sheets_root = workbook.find(f"{{{_SPREADSHEET_NS}}}sheets")
    sheets = (
        list(sheets_root.findall(f"{{{_SPREADSHEET_NS}}}sheet"))
        if sheets_root is not None
        else []
    )
    if not sheets:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "XLSX工作簿没有工作表",
        )
    workbook_relationships = relationship_sets.get(main_part)
    if workbook_relationships is None:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "XLSX工作簿缺少关系部件",
        )
    relationship_ids: set[str] = set()
    sheet_names: set[str] = set()
    worksheet_parts: list[str] = []
    for sheet in sheets:
        name = str(sheet.get("name") or "").strip()
        relationship_id = str(
            sheet.get(f"{{{_OFFICE_RELATIONSHIPS_NS}}}id") or ""
        ).strip()
        relationship = workbook_relationships.get(relationship_id)
        if (
            not name
            or name.casefold() in sheet_names
            or not relationship_id
            or relationship_id in relationship_ids
            or relationship is None
            or relationship.get("type") != _WORKSHEET_RELATIONSHIP
            or relationship.get("target_mode", "").casefold() == "external"
        ):
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "XLSX工作表身份或关系无效",
            )
        target = relationship["target"]
        if overrides.get(target) != _WORKSHEET_CONTENT_TYPE:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "XLSX工作表Content-Type无效",
            )
        worksheet = _read_xml(archive, target, info_by_name=info_by_name)
        if worksheet.tag != f"{{{_SPREADSHEET_NS}}}worksheet":
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_OOXML_INVALID",
                "XLSX工作表XML根节点无效",
            )
        sheet_names.add(name.casefold())
        relationship_ids.add(relationship_id)
        worksheet_parts.append(target)
    main_bytes = archive.read(info_by_name[main_part])
    return {
        "main_part": main_part,
        "main_content_type": _XLSX_CONTENT_TYPE,
        "main_part_sha256": hashlib.sha256(main_bytes).hexdigest(),
        "sheet_count": len(sheets),
        "worksheet_parts_digest": _canonical_digest(sorted(worksheet_parts)),
    }


def _inspect_ooxml(handle: BinaryIO, *, artifact_kind: ArtifactKind) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(handle, mode="r") as archive:
            info_by_name, total_uncompressed, manifest_digest = _inspect_members(
                archive
            )
            bad_member = archive.testzip()
            if bad_member is not None:
                raise FormalArtifactIntegrityError(
                    "FORMAL_ARTIFACT_OOXML_INVALID",
                    "OOXML包包含CRC校验失败的部件",
                )
            xml_names = sorted(
                name
                for name, info in info_by_name.items()
                if not info.is_dir()
                and name.endswith((".xml", ".rels"))
            )
            for name in xml_names:
                _read_xml(archive, name, info_by_name=info_by_name)
            overrides = _content_types(archive, info_by_name=info_by_name)
            relationship_sets, relationship_count = _relationships(
                archive,
                info_by_name=info_by_name,
            )
            specific = (
                _inspect_docx(
                    archive,
                    info_by_name=info_by_name,
                    overrides=overrides,
                    relationship_sets=relationship_sets,
                )
                if artifact_kind == "docx"
                else _inspect_xlsx(
                    archive,
                    info_by_name=info_by_name,
                    overrides=overrides,
                    relationship_sets=relationship_sets,
                )
            )
            return {
                "package_member_count": len(info_by_name),
                "xml_part_count": len(xml_names),
                "relationship_count": relationship_count,
                "uncompressed_size": total_uncompressed,
                "package_manifest_digest": manifest_digest,
                **specific,
            }
    except FormalArtifactIntegrityError:
        raise
    except (
        OSError,
        RuntimeError,
        ValueError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ) as exc:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_OOXML_INVALID",
            "文件不是可验证的OOXML包",
        ) from exc


def validate_formal_ooxml_artifact(
    path: str | os.PathLike[str],
    *,
    artifact_kind: ArtifactKind,
    expected_size: int,
    expected_sha256: str,
) -> dict[str, Any]:
    """Validate one witnessed DOCX/XLSX and return a relocatable projection.

    ``expected_size`` and ``expected_sha256`` must come from the caller's
    independently captured artifact witness.  The returned projection contains
    no path, timestamps, inode values, or document text, so its digest remains
    stable when the same sealed artifact is moved as a unit.
    """

    kind = str(artifact_kind or "").strip().lower()
    digest = str(expected_sha256 or "").strip().lower()
    if kind not in {"docx", "xlsx"}:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_EXPECTATION_INVALID",
            "正式制品类型必须为docx或xlsx",
        )
    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or expected_size <= 0
        or expected_size > _MAX_ARCHIVE_BYTES
        or _SHA256_RE.fullmatch(digest) is None
    ):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_EXPECTATION_INVALID",
            "正式制品大小或SHA256见证无效",
        )
    try:
        candidate = Path(os.path.abspath(os.fspath(path)))
        path_before = candidate.lstat()
    except (OSError, TypeError, ValueError) as exc:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_UNTRUSTED",
            "正式制品路径无法安全解析",
        ) from exc
    if candidate.is_symlink() or not stat.S_ISREG(path_before.st_mode):
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_UNTRUSTED",
            "正式制品必须为非符号链接普通文件",
        )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except (OSError, ValueError) as exc:
        raise FormalArtifactIntegrityError(
            "FORMAL_ARTIFACT_UNTRUSTED",
            "正式制品无法通过可信文件描述符打开",
        ) from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or not _same_identity(path_before, before)
            or before.st_size != expected_size
        ):
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_UNTRUSTED",
                "正式制品身份、所有者或大小与见证不一致",
            )
        with os.fdopen(descriptor, mode="rb", closefd=False) as handle:
            initial_sha256 = _hash_handle(handle)
            if initial_sha256 != digest:
                raise FormalArtifactIntegrityError(
                    "FORMAL_ARTIFACT_HASH_MISMATCH",
                    "正式制品当前字节SHA256与见证不一致",
                )
            package_projection = _inspect_ooxml(
                handle,
                artifact_kind=kind,  # type: ignore[arg-type]
            )
            final_sha256 = _hash_handle(handle)
        after = os.fstat(descriptor)
        try:
            path_after = candidate.lstat()
        except OSError as exc:
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_CHANGED",
                "正式制品校验后无法复验路径身份",
            ) from exc
        if (
            final_sha256 != digest
            or not _same_identity(before, after)
            or not _same_identity(after, path_after)
            or candidate.is_symlink()
        ):
            raise FormalArtifactIntegrityError(
                "FORMAL_ARTIFACT_CHANGED",
                "正式制品在OOXML校验期间发生变化",
            )
    finally:
        os.close(descriptor)

    core = {
        "schema_version": "formal-ooxml-integrity-v1",
        "artifact_kind": kind,
        "size": expected_size,
        "sha256": digest,
        **package_projection,
    }
    return {**core, "projection_digest": _canonical_digest(core)}


__all__ = [
    "FormalArtifactIntegrityError",
    "validate_formal_ooxml_artifact",
]
