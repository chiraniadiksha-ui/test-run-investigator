"""Regression checks for evidence-preserving log compression."""
import unittest
from investigate import prepare_log_entries, chunk_log, read_run_log


def event(n, message, level='DEBUG', component='traffic', run='RUN-1042'):
    return f'2026-10-28 10:00:00.000 {level} run_id={run} component={component} {message}'


def heartbeat(n, state='running'):
    return event(n, f'Heartbeat sequence={n} traffic_state={state} measurement_state=collecting')


class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(text)


class CompressionTests(unittest.TestCase):
    def test_sequence_compaction_and_state_boundary(self):
        log = '\n'.join([heartbeat(i) for i in range(3)] + [heartbeat(3, 'stopped')])
        entries = prepare_log_entries(log)
        self.assertEqual([(e['start_line'], e['end_line']) for e in entries], [(1, 3), (4, 4)])
        self.assertIn('sequence=0', entries[0]['text'])
        self.assertIn('sequence=2', entries[0]['text'])
        self.assertIn('traffic_state=stopped', entries[1]['text'])

    def test_changing_measurements_and_unknown_messages_are_preserved(self):
        for level in ('DEBUG', 'WARNING', 'ERROR'):
            log = '\n'.join(event(i, f'Measured throughput={i} sequence={i}', level) for i in range(4))
            self.assertEqual(len(prepare_log_entries(log)), 4)
        log = '\n'.join(event(i, f'Unknown progress sequence={i}') for i in range(4))
        self.assertEqual(len(prepare_log_entries(log)), 4)

    def test_run_boundaries_and_traceback(self):
        log = '\n'.join([heartbeat(0), heartbeat(1), event(2, 'Heartbeat sequence=2 traffic_state=running measurement_state=collecting', run='RUN-2'), 'Traceback:', 'AssertionError: failed'])
        self.assertEqual(len(prepare_log_entries(log)), 5)

    def test_demo_coverage_and_evidence(self):
        log = read_run_log('RUN-CHUNK-DEMO')
        entries = prepare_log_entries(log)
        covered = [i for e in entries for i in range(e['start_line'], e['end_line'] + 1)]
        self.assertEqual(covered, list(range(1, len(log.splitlines()) + 1)))
        self.assertLess(len(entries), 60)
        text = '\n'.join(e['text'] for e in entries)
        for evidence in ('configured_rate_limit_mbps=50', 'minimum_throughput_mbps=100', 'Measured throughput: 42 Mbps', 'AssertionError:', 'Final status: FAILED'):
            self.assertIn(evidence, text)
        self.assertTrue(any(e['start_line'] == 510 and e['end_line'] == 609 for e in entries))

    def test_chunk_limits_coverage_and_invalid_inputs(self):
        tokenizer = CharacterTokenizer()
        log = '\n'.join('line ' + str(i) for i in range(40))
        chunks = chunk_log(log, tokenizer, max_tokens=60, overlap_lines=2)
        self.assertTrue(all(c['token_count'] <= 60 for c in chunks))
        self.assertEqual({i for c in chunks for i in range(c['start_line'], c['end_line']+1)}, set(range(1,41)))
        for text, limit in (('',60), ('long entry',2), ('log',0)):
            with self.assertRaises(ValueError):
                chunk_log(text, tokenizer, max_tokens=limit)


if __name__ == '__main__':
    unittest.main()
