"""Check failure handling and overlap merging without running a model."""
import json
import unittest
from unittest.mock import patch
from investigate import extract_log_observations


class ObservationTests(unittest.TestCase):
    chunks = [dict(start_line=1, end_line=3), dict(start_line=2, end_line=5)]

    def extract(self, responses):
        with patch('investigate.chunk_log', return_value=self.chunks), patch(
                'investigate.extract_chunk_observations', side_effect=responses):
            return extract_log_observations('log', None)

    def test_overlap_deduplication_and_markdown(self):
        response = json.dumps({'observations': [dict(description='failure', start_line=2, end_line=3)]})
        result = self.extract([response, '```json\n' + response + '\n```'])
        self.assertEqual(result.count('[2-3] failure'), 1)

    def test_invalid_model_responses(self):
        invalid = ['bad JSON', '[]', '{"observations": {}}', '{"observations": [null]}']
        for item in [dict(description='', start_line=1, end_line=1),
                     dict(description='x', start_line=True, end_line=2),
                     dict(description='x', start_line=0, end_line=2),
                     dict(description='x', start_line=1, end_line=4),
                     dict(description='x', start_line=3, end_line=2)]:
            invalid.append(json.dumps({'observations': [item]}))
        for response in invalid:
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.extract([response])

    def test_empty_evidence_fails(self):
        with self.assertRaisesRegex(ValueError, 'No relevant observations'):
            self.extract(['{"observations": []}'] * 2)

    def test_one_empty_chunk_does_not_drop_other_evidence(self):
        response = json.dumps({'observations': [dict(description='failure', start_line=5, end_line=5)]})
        self.assertIn('[5-5] failure', self.extract(['{"observations": []}', response]))
