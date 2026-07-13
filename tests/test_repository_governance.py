import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")


class RepositoryGovernanceTest(unittest.TestCase):
    def test_checked_in_markdown_is_not_empty(self):
        documents = [ROOT / "README.md", ROOT / "AGENTS.md"]
        documents.extend((ROOT / "docs").rglob("*.md"))
        documents.extend((ROOT / ".agents" / "skills").rglob("*.md"))
        for document in documents:
            with self.subTest(path=str(document.relative_to(ROOT))):
                self.assertTrue(document.read_text(encoding="utf-8").strip())

    def test_canonical_entrypoints_are_present_and_nonempty(self):
        paths = [
            "README.md",
            "AGENTS.md",
            "docs/architecture/HARNESS_V1.md",
            "docs/integrations/HUNYUAN.md",
            "docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md",
            "docs/knowledge/AR_PRODUCTION_CASEBOOK.md",
            "docs/knowledge/LEGACY_SKILL_MIGRATION.md",
            ".github/workflows/harness-v1.yml",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), relative)
                self.assertTrue(path.read_text(encoding="utf-8").strip(), relative)

    def test_entrypoint_relative_links_resolve(self):
        for relative in ("README.md", "AGENTS.md"):
            document = ROOT / relative
            for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
                target = target.strip().strip("<>")
                if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                path_part = target.split("#", 1)[0]
                with self.subTest(document=relative, target=target):
                    self.assertTrue((document.parent / path_part).resolve().exists())

    def test_skill_metadata_is_complete(self):
        skills_root = ROOT / ".agents" / "skills"
        skills = sorted(path for path in skills_root.iterdir() if path.is_dir())
        self.assertTrue(skills)
        for skill in skills:
            with self.subTest(skill=skill.name):
                skill_md = skill / "SKILL.md"
                metadata = skill / "agents" / "openai.yaml"
                self.assertTrue(skill_md.is_file())
                self.assertTrue(metadata.is_file())
                text = skill_md.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                frontmatter = text.split("---", 2)[1]
                match = re.search(r"^name:\s*([^\s]+)\s*$", frontmatter, re.MULTILINE)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), skill.name)
                self.assertRegex(frontmatter, r"(?m)^description:\s*\S")
                interface = metadata.read_text(encoding="utf-8")
                self.assertIn("default_prompt:", interface)
                self.assertIn("$" + skill.name, interface)


if __name__ == "__main__":
    unittest.main()
