import io
import json
import unittest
from contextlib import redirect_stdout

from blender_harness.cli import build_parser, run


class TripoCliTest(unittest.TestCase):
    def test_capabilities_needs_no_credentials(self):
        args = build_parser().parse_args(["tripo", "capabilities"])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run(args), 0)
        value = json.loads(output.getvalue())
        self.assertEqual(value["provider"], "tripo")
        self.assertFalse(value["provider_done_is_asset_approval"])
        enabled = [item["operation"] for item in value["operations"] if item["submit_enabled"]]
        self.assertEqual(enabled, ["geometry.multiview"])

    def test_reconcile_parser_requires_reason(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["tripo", "reconcile", "a" * 24])


if __name__ == "__main__":
    unittest.main()
