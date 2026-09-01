import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from Supabase.import_stat_resources import create_supabase_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = PROJECT_ROOT / "Resource" / "graduation_requirements"
MANIFEST_PATH = RESOURCE_DIR / "manifest.json"
TABLE_NAME = "graduation_requirement_documents"
EXPECTED_DOCUMENT_KEYS = {
    "UIUC-MATH-BSLAS-2026-2027",
    "UIUC-STAT-BSLAS-2026-2027",
}
MANIFEST_FIELDS = {
    "document_key",
    "document_type",
    "institution_code",
    "degree_code",
    "program_code",
    "program_name",
    "catalog_year",
    "parent_document_key",
    "source_url",
    "file_name",
}


@dataclass(frozen=True)
class GraduationRequirementDocument:
    document_key: str
    document_type: str
    institution_code: str
    degree_code: str
    program_code: str | None
    program_name: str | None
    catalog_year: str
    parent_document_key: str | None
    source_url: str
    file_name: str
    content_markdown: str

    def database_row(self) -> dict[str, Any]:
        return {
            "document_key": self.document_key,
            "document_type": self.document_type,
            "institution_code": self.institution_code,
            "degree_code": self.degree_code,
            "program_code": self.program_code,
            "program_name": self.program_name,
            "catalog_year": self.catalog_year,
            "parent_document_key": self.parent_document_key,
            "source_url": self.source_url,
            "content_markdown": self.content_markdown,
        }


def _required_string(value: Any, *, field: str, row_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"manifest document {row_number} has invalid {field}: {value!r}"
        )
    return value.strip()


def _optional_string(value: Any, *, field: str, row_number: int) -> str | None:
    if value is None:
        return None
    return _required_string(value, field=field, row_number=row_number)


def _read_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"manifest does not exist: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict) or set(payload) != {"documents"}:
        raise ValueError("manifest root must contain only a documents array")
    documents = payload["documents"]
    if not isinstance(documents, list) or not documents:
        raise ValueError("manifest documents must be a non-empty array")
    if not all(isinstance(document, dict) for document in documents):
        raise ValueError("every manifest document must be an object")
    return documents


def load_requirement_documents(
    manifest_path: Path = MANIFEST_PATH,
) -> list[GraduationRequirementDocument]:
    raw_documents = _read_manifest(manifest_path)
    resource_dir = manifest_path.parent
    documents: list[GraduationRequirementDocument] = []

    for row_number, raw in enumerate(raw_documents, start=1):
        fields = set(raw)
        if fields != MANIFEST_FIELDS:
            missing = sorted(MANIFEST_FIELDS - fields)
            unexpected = sorted(fields - MANIFEST_FIELDS)
            raise ValueError(
                f"manifest document {row_number} fields do not match; "
                f"missing={missing}, unexpected={unexpected}"
            )

        document_type = _required_string(
            raw["document_type"], field="document_type", row_number=row_number
        )
        if document_type != "program":
            raise ValueError(
                f"manifest document {row_number} has invalid document_type: "
                f"{document_type!r}"
            )

        file_name = _required_string(
            raw["file_name"], field="file_name", row_number=row_number
        )
        if Path(file_name).name != file_name or not file_name.endswith(".md"):
            raise ValueError(
                f"manifest document {row_number} has unsafe Markdown file_name: "
                f"{file_name!r}"
            )
        markdown_path = resource_dir / file_name
        try:
            content_markdown = markdown_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError(f"Markdown file does not exist: {markdown_path}") from exc
        if not content_markdown.strip():
            raise ValueError(f"Markdown file is empty: {markdown_path}")
        if not content_markdown.startswith("# "):
            raise ValueError(f"Markdown file must start with an H1: {markdown_path}")

        catalog_year = _required_string(
            raw["catalog_year"], field="catalog_year", row_number=row_number
        )
        display_year = catalog_year.replace("-", "–")
        if f"**Catalog year:** {display_year}" not in content_markdown:
            raise ValueError(
                f"{file_name} does not declare Catalog year {display_year}"
            )

        source_url = _required_string(
            raw["source_url"], field="source_url", row_number=row_number
        )
        if not source_url.startswith("https://catalog.illinois.edu/"):
            raise ValueError(
                f"manifest document {row_number} source_url is not an official "
                "catalog URL"
            )

        document = GraduationRequirementDocument(
            document_key=_required_string(
                raw["document_key"], field="document_key", row_number=row_number
            ),
            document_type=document_type,
            institution_code=_required_string(
                raw["institution_code"],
                field="institution_code",
                row_number=row_number,
            ),
            degree_code=_required_string(
                raw["degree_code"], field="degree_code", row_number=row_number
            ),
            program_code=_optional_string(
                raw["program_code"], field="program_code", row_number=row_number
            ),
            program_name=_optional_string(
                raw["program_name"], field="program_name", row_number=row_number
            ),
            catalog_year=catalog_year,
            parent_document_key=_optional_string(
                raw["parent_document_key"],
                field="parent_document_key",
                row_number=row_number,
            ),
            source_url=source_url,
            file_name=file_name,
            content_markdown=content_markdown,
        )
        documents.append(document)

    _validate_documents(documents)
    return documents


def _validate_documents(documents: list[GraduationRequirementDocument]) -> None:
    document_keys = [document.document_key for document in documents]
    if len(document_keys) != len(set(document_keys)):
        raise ValueError("manifest contains duplicate document_key values")
    if set(document_keys) != EXPECTED_DOCUMENT_KEYS:
        raise ValueError(
            "manifest document keys do not match the expected snapshot: "
            f"{sorted(document_keys)}"
        )

    file_names = [document.file_name for document in documents]
    if len(file_names) != len(set(file_names)):
        raise ValueError("manifest contains duplicate Markdown file names")

    for document in documents:
        if not document.program_code or not document.program_name:
            raise ValueError(
                f"program document {document.document_key} is missing program metadata"
            )
        if document.parent_document_key is not None:
            raise ValueError(
                f"program document {document.document_key} must not have a parent"
            )
        if "General Education" in document.content_markdown:
            raise ValueError(
                f"program document {document.document_key} contains "
                "General Education content"
            )


def validation_summary(
    documents: list[GraduationRequirementDocument],
) -> dict[str, Any]:
    return {
        "documents": len(documents),
        "shared_documents": sum(
            document.document_type == "shared" for document in documents
        ),
        "program_documents": sum(
            document.document_type == "program" for document in documents
        ),
        "document_keys": sorted(document.document_key for document in documents),
    }


def upload_documents(
    documents: list[GraduationRequirementDocument],
    *,
    supabase_client: Any,
) -> dict[str, Any]:
    program_rows = [document.database_row() for document in documents]
    supabase_client.table(TABLE_NAME).upsert(
        program_rows, on_conflict="document_key"
    ).execute()

    document_keys = [document.document_key for document in documents]
    stored_rows = (
        supabase_client.table(TABLE_NAME)
        .select("document_key,content_markdown")
        .in_("document_key", document_keys)
        .execute()
        .data
        or []
    )
    if len(stored_rows) != len(documents):
        raise RuntimeError(
            f"expected {len(documents)} stored documents, found {len(stored_rows)}"
        )
    stored_by_key = {row["document_key"]: row for row in stored_rows}
    if set(stored_by_key) != set(document_keys):
        raise RuntimeError("Supabase returned unexpected graduation requirement keys")
    for document in documents:
        stored_content = stored_by_key[document.document_key].get("content_markdown")
        if stored_content != document.content_markdown:
            raise RuntimeError(
                f"stored Markdown does not match {document.document_key}"
            )

    return {
        "documents": len(stored_rows),
        "document_keys": sorted(stored_by_key),
        "content_verified": True,
    }


def run_upload(
    documents: list[GraduationRequirementDocument],
) -> dict[str, Any]:
    return upload_documents(
        documents,
        supabase_client=create_supabase_client(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and import UIUC graduation requirement Markdown."
    )
    parser.add_argument("command", choices=("validate", "upload"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    documents = load_requirement_documents()
    if args.command == "validate":
        result = validation_summary(documents)
    else:
        result = run_upload(documents)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
