import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = PROJECT_ROOT / "Resource" / "LASmajor_requirement"
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
    degree_code: str | None
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
        if document_type not in {"program", "program_redirect"}:
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
            content_markdown = markdown_path.read_bytes().decode("utf-8")
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
        if not re.search(r"Catalog year(?:\*\*)?:\s*(?:\*\*)?" + re.escape(display_year), content_markdown):
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

        source_line = next((line for line in content_markdown.splitlines()
                            if "Official source" in line), "")
        urls = re.findall(r"https?://[^\s)>]+", source_line)
        if not urls or source_url != urls[0]:
            raise ValueError(f"{file_name} source_url must match first Official source URL")
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
            degree_code=_optional_string(
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
    if {d.file_name for d in documents} != {p.name for p in resource_dir.glob("*.md")}:
        raise ValueError("manifest must include every Markdown file exactly once")
    return documents


def _validate_documents(documents: list[GraduationRequirementDocument]) -> None:
    document_keys = [document.document_key for document in documents]
    if len(document_keys) != len(set(document_keys)):
        raise ValueError("manifest contains duplicate document_key values")
    if len(documents) != 61 or not EXPECTED_DOCUMENT_KEYS <= set(document_keys):
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
        if document.institution_code != "UIUC" or document.catalog_year != "2026-2027":
            raise ValueError("unexpected institution or catalog year")
        if document.file_name == "biology_2026_2027.md" and (
            document.document_key != "UIUC-BIOLOGY-REDIRECT-2026-2027"
            or document.document_type != "program_redirect" or document.degree_code is not None
        ):
            raise ValueError("invalid Biology redirect metadata")
        if document.document_type == "program_redirect":
            if document.document_key != "UIUC-BIOLOGY-REDIRECT-2026-2027" or document.degree_code is not None:
                raise ValueError("invalid Biology redirect metadata")
        elif document.degree_code not in {"BALAS", "BSLAS", "BS", "BALAS_OR_BSLAS"}:
            raise ValueError("invalid degree_code")
        if (document.degree_code == "BALAS_OR_BSLAS") != (document.file_name == "individual_plans_of_study_balas_or_bslas_2026_2027.md"):
            raise ValueError("invalid Individual Plans degree_code")


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


def run_upload(documents: list[GraduationRequirementDocument]) -> dict[str, Any]:
    # Requirements must commit with courses and instructor statistics.
    from Supabase.import_las_resources import run_upload as upload_las
    return upload_las(documents=documents)


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
