"""Validate the frozen corpus, including materialized LFS objects, offline."""
import hashlib
import json
from pathlib import Path
import unittest

from evaluate import evaluate

ROOT = Path(__file__).resolve().parent


class CorpusIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
        cls.truth = [json.loads(line) for line in
                     (ROOT / 'ground_truth/expected.jsonl').read_text(encoding='utf-8').splitlines()]

    def test_manifest_and_materialized_files(self):
        self.assertEqual(len(self.manifest), 84)
        ids = [row['id'] for row in self.manifest]
        self.assertEqual(len(set(ids)), 84)
        self.assertEqual(set(ids), {row['id'] for row in self.truth})
        for row in self.manifest:
            path = (ROOT / row['path']).resolve()
            self.assertTrue(path.is_relative_to((ROOT / 'inputs').resolve()))
            contents = path.read_bytes()
            self.assertTrue(contents.startswith(b'%PDF-'), f"Run git lfs pull: {path}")
            self.assertEqual(hashlib.sha256(contents).hexdigest(), row['sha256'])
        manifests = {row['id']: row for row in self.manifest}
        for row in self.truth:
            for key, value in manifests[row['id']].items():
                self.assertEqual(value, row[key], (row['id'], key))

    def test_group_and_family_separation(self):
        groups = {}
        for row in self.truth:
            groups.setdefault(row['group_id'], set()).add(row['split'])
        self.assertEqual(len(groups), 60)
        self.assertTrue(all(len(splits) == 1 for splits in groups.values()))
        training = {r['family'] for r in self.truth if r['split'] == 'setup'}
        unseen = {r['family'] for r in self.truth if r['split'] == 'unseen_layout'}
        self.assertTrue(training.isdisjoint(unseen))
        self.assertEqual({s: sum(r['split'] == s for r in self.truth)
                          for s in ('setup', 'known_layout', 'unseen_layout')},
                         {'setup': 24, 'known_layout': 18, 'unseen_layout': 42})

    def test_field_presence_and_coordinates(self):
        for row in self.truth:
            self.assertEqual(len(row['fields']), 9)
            for field in row['fields'].values():
                present = field['status'] == 'present'
                self.assertEqual(field['value'] is not None, present)
                self.assertEqual(bool(field['locators']), present)
                for location in field['locators']:
                    self.assertLess(location['page'], row['pages'])
                    self.assertGreaterEqual(location['page'], 0)
                    x0, y0, x1, y1 = location['bbox']
                    self.assertTrue(0 <= x0 < x1 <= 595.276)
                    self.assertTrue(0 <= y0 < y1 <= 841.890)

    def test_evaluation_oracle_and_missing_answers(self):
        fields = list(self.truth[0]['fields'])
        oracle = [{'id': r['id'], 'fields': {k: f['value'] for k, f in r['fields'].items()}}
                  for r in self.truth]
        score = evaluate(self.truth, oracle, fields)['summary']['all']
        self.assertEqual(score['correct'], 756)
        self.assertEqual(score['complete_documents'], 84)
        self.assertEqual(evaluate(self.truth, [], fields)['summary']['all']['correct'], 0)


if __name__ == '__main__':
    unittest.main()
