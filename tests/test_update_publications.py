import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("updater", ROOT / "scripts" / "update_publications.py")
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


class UpdaterTests(unittest.TestCase):
    def test_known_orcid_checksum(self):
        self.assertTrue(updater.valid_orcid("0000-0001-7962-7487"))
        self.assertFalse(updater.valid_orcid("0000-0001-7962-7488"))

    def test_deduplicate_shared_publication(self):
        records = [
            {"title": "A Paper", "year": 2026, "doi": "10.1/example", "quantact_members": ["A"], "orcid_ids": ["id-a"]},
            {"title": "A Paper", "year": 2026, "doi": "10.1/example", "quantact_members": ["B"], "orcid_ids": ["id-b"]},
        ]
        merged = updater.merge_publications(records)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["quantact_members"], ["A", "B"])

    def test_parse_orcid_work_group(self):
        group = {
            "external-ids": {
                "external-id": [{"external-id-type": "doi", "external-id-value": "10.1234/ABC"}]
            },
            "work-summary": [{
                "title": {"title": {"value": "Example title"}},
                "journal-title": {"value": "Example Journal"},
                "publication-date": {"year": {"value": "2025"}},
                "type": "journal-article",
            }],
        }
        result = updater.parse_orcid_work_group(group, "Member", "0000-0001-7962-7487")
        self.assertEqual(result["doi"], "10.1234/abc")
        self.assertEqual(result["journal"], "Example Journal")
        self.assertEqual(result["quantact_members"], ["Member"])
        self.assertEqual(result["source"], "ORCID public record")

    def test_crossref_requires_exact_orcid_on_work(self):
        item = {
            "title": ["Exact ORCID paper"],
            "author": [{"given": "Member", "family": "Name", "ORCID": "https://orcid.org/0000-0001-7962-7487"}],
            "DOI": "10.1234/example",
            "issued": {"date-parts": [[2025]]},
        }
        accepted = updater.parse_crossref_item(item, "Member Name", "0000-0001-7962-7487")
        rejected = updater.parse_crossref_item(item, "Other Member", "0000-0002-7141-1048")
        wrong_name = updater.parse_crossref_item(item, "Different Person", "0000-0001-7962-7487")
        self.assertIsNotNone(accepted)
        self.assertIsNone(rejected)
        self.assertIsNone(wrong_name)

    def test_orcid_record_name_must_match_member(self):
        record = {
            "person": {
                "name": {
                    "given-names": {"value": "Alexandre"},
                    "family-name": {"value": "Roch"},
                    "credit-name": None,
                },
                "other-names": {"other-name": []},
            }
        }
        updater.validate_orcid_record_identity(record, "Alexandre F. Roch", "0000-0002-8206-0765")
        with self.assertRaises(updater.IdentityMismatchError):
            updater.validate_orcid_record_identity(record, "Someone Else", "0000-0002-8206-0765")

    def test_publication_scope_starts_in_2000(self):
        publications = [
            {"title": "Included boundary", "year": 2000},
            {"title": "Included recent", "year": 2026},
            {"title": "Excluded old", "year": 1999},
            {"title": "Excluded undated", "year": None},
        ]
        self.assertEqual(
            [publication["title"] for publication in updater.filter_publications(publications)],
            ["Included boundary", "Included recent"],
        )

    def test_site_data_bundle(self):
        member_doc = {"members": [{"name": "Member", "institution": "University", "orcid": None}]}
        publication_doc = {
            "generated_at": "2026-08-20T00:00:00Z",
            "publications": [{"title": "A Paper", "year": 2025}],
        }
        text = updater.site_data_text(member_doc, publication_doc)
        prefix = "var QUANTACT_SITE_DATA="
        self.assertTrue(text.startswith(prefix))
        payload = json.loads(text.removeprefix(prefix).removesuffix(";\n"))
        self.assertEqual(payload["members"], member_doc["members"])
        self.assertEqual(payload["publications"], [])
        self.assertEqual(payload["minimum_publication_year"], 2000)
        self.assertEqual(payload["generated_at"], publication_doc["generated_at"])
        publications = updater.browser_publications(publication_doc)
        chunk = updater.site_publication_chunk_text(publications)
        chunk_prefix = "QUANTACT_SITE_DATA.publications.push(..."
        self.assertTrue(chunk.startswith(chunk_prefix))
        self.assertEqual(json.loads(chunk.removeprefix(chunk_prefix).removesuffix(");\n")), publication_doc["publications"])


if __name__ == "__main__":
    unittest.main()
