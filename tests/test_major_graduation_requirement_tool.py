import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.tools import ToolException
from pydantic import ValidationError

from tools.degree_programs_tool import find_degree_programs
from tools.major_graduation_requirement_tool import major_graduation_requirement


@pytest.fixture
def documents():
    root = Path(__file__).resolve().parents[1] / "Resource/LASmajor_requirement"
    records = json.loads((root / "manifest.json").read_text())["documents"]
    return [{**r, "content_markdown": (root / r['file_name']).read_bytes().decode()} for r in records]


class Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, fields):
        self.fields = fields.split(',')
        return self

    def eq(self, column, value):
        self.rows = [r for r in self.rows if r[column] == value]
        return self

    def order(self, column):
        self.rows = sorted(self.rows, key=lambda r: r[column])
        return self

    def range(self, start, end):
        self.rows = self.rows[start:end + 1]
        return self

    def execute(self):
        return SimpleNamespace(data=[{k: r[k] for k in self.fields} for r in self.rows])


@pytest.fixture
def database(documents):
    client = SimpleNamespace(table=lambda _: Query(documents))
    with patch('tools.major_graduation_requirement_tool.create_supabase_client', return_value=client), \
         patch('tools.degree_programs_tool.create_supabase_client', return_value=client):
        yield documents


def test_all_61_programs_return_exact_markdown(database):
    for document in database:
        for field in ['document_key', 'program_code', 'program_name']:
            assert major_graduation_requirement.invoke({'major': document[field]}) == document['content_markdown']


@pytest.mark.parametrize('major,key', [('math', 'UIUC-MATH-BSLAS-2026-2027'), ('stats', 'UIUC-STAT-BSLAS-2026-2027')])
def test_legacy_aliases(database, major, key):
    expected = next(d['content_markdown'] for d in database if d['document_key'] == key)
    assert major_graduation_requirement.invoke({'major': major}) == expected


def test_economics_discovery_keeps_three_programs_distinct(database):
    matches = find_degree_programs.invoke({'query': 'economics'})
    assert len(matches) == 3
    assert {m['degree_code'] for m in matches} == {'BALAS', 'BSLAS'}
    assert all({'document_key', 'program_name', 'program_code', 'document_type', 'catalog_year'} <= set(m) for m in matches)
    expected = next(d for d in database if d['document_key'] == 'UIUC-ECONOMICS-BALAS-2026-2027')
    assert major_graduation_requirement.invoke({'major': 'Economics'}) == expected['content_markdown']


def test_biology_returns_redirect(database):
    found = find_degree_programs.invoke({'query': 'Biology'})
    assert len(found) > 1
    redirect = next(d for d in database if d['document_type'] == 'program_redirect')
    assert major_graduation_requirement.invoke({'major': 'Biology'}) == redirect['content_markdown']
    assert redirect['degree_code'] is None


def test_unavailable_concentration_is_not_replaced_by_general_major(database):
    with pytest.raises(ToolException, match='concentration'):
        major_graduation_requirement.invoke({'major': 'Mathematics - Applied Mathematics'})


def test_ambiguous_name_returns_candidates(database):
    # These are distinct stored programs; neither is the program named Computer Science.
    with pytest.raises(ToolException) as error:
        major_graduation_requirement.invoke({'major': 'Computer Science'})
    result = json.loads(str(error.value))
    assert result['error'] == 'ambiguous_program'
    assert len(result['candidates']) > 1


def test_unknown_program_and_empty_content_are_recoverable(database):
    assert find_degree_programs.invoke({'query': 'Underwater Basketweaving'}) == []
    with pytest.raises(ToolException, match='program_not_found'):
        major_graduation_requirement.invoke({'major': 'Underwater Basketweaving'})
    database[0]['content_markdown'] = ''
    with pytest.raises(ToolException, match='No stored requirement Markdown'):
        major_graduation_requirement.invoke({'major': database[0]['document_key']})


@pytest.mark.parametrize('value', ['', '   '])
def test_blank_input_fails_validation(value):
    with pytest.raises(ValidationError):
        major_graduation_requirement.invoke({'major': value})
    with pytest.raises(ValidationError):
        find_degree_programs.invoke({'query': value})


def test_service_failure_is_not_reported_as_missing_program():
    with patch('tools.major_graduation_requirement_tool.create_supabase_client', side_effect=RuntimeError('service unavailable')):
        with pytest.raises(RuntimeError, match='service unavailable'):
            major_graduation_requirement.invoke({'major': 'Economics'})


def test_catalog_and_advising_register_discovery():
    from nodes.catalog_lookup import CATALOG_TOOLS
    from nodes.advising import ADVISING_TOOLS
    assert ADVISING_TOOLS is CATALOG_TOOLS
    assert {
        'major_graduation_requirement',
        'general_education_graduation_requirement',
        'find_degree_programs',
    } <= {t.name for t in CATALOG_TOOLS}


def test_prompts_distinguish_requirement_tool_scope():
    prompt_root = Path(__file__).resolve().parents[1] / 'prompt'
    for prompt_name in ['catalog_lookup_prompt.txt', 'advising_prompt.txt']:
        prompt = (prompt_root / prompt_name).read_text(encoding='utf-8')
        assert 'major_graduation_requirement' in prompt
        assert 'general_education_graduation_requirement' in prompt
        assert 'explicitly scoped to one requirement type' in prompt
        assert 'use both requirement tools' in prompt

    router_prompt = (prompt_root / 'router_prompt.txt').read_text(encoding='utf-8')
    assert 'major or general education graduation' in router_prompt
    assert 'major_graduation_requirement' not in router_prompt
    assert 'general_education_graduation_requirement' not in router_prompt
