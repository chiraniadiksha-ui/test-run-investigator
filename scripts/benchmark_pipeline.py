"""Benchmark the real investigation pipeline and save evidence for manual review."""
import argparse
import contextlib
from datetime import datetime
from functools import wraps
import hashlib
import json
from pathlib import Path
from time import perf_counter
import traceback
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='RUN-1042')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'evaluation_results' / ('benchmark_' + datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y%m%d_%H%M%S'))
    output.mkdir(parents=True)
    started = perf_counter()
    metrics = {'run_id': args.run_id, 'stages': [], 'status': 'running', 'scope': 'Direct pipeline; excludes API upload, queue wait and report download. Nested stage timings overlap.'}
    print(f'Artifacts: {output}', flush=True)

    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2) if not isinstance(value, str) else value, encoding='utf-8')

    def timed(name, function):
        @wraps(function)
        def call(*a, **kw):
            start = perf_counter()
            print(f'Starting {name}', flush=True)
            try:
                with (output / 'execution.txt').open('a') as log, contextlib.redirect_stdout(log):
                    result = function(*a, **kw)
                if name == 'chunking':
                    save('chunks.json', result)
                    metrics['chunk_count'] = len(result)
                    metrics['chunk_tokens'] = sum(c['token_count'] for c in result)
                elif name in ('chunk_observation', 'model_generation'):
                    count = sum(s['stage'] == name for s in metrics['stages']) + 1
                    save(f'{name}_{count}.txt', result)
                elif name in ('tool_discovery', 'configuration', 'retrieval'):
                    save(f'{name}.json', result)
                return result
            finally:
                elapsed = perf_counter() - start
                metrics['stages'].append({'stage': name, 'seconds': elapsed})
                save('metrics.json', metrics)
                print(f'Finished {name}: {elapsed:.2f}s', flush=True)
        return call

    try:
        start = perf_counter()
        import investigate as inv
        metrics['stages'].append({'stage': 'imports', 'seconds': perf_counter() - start})
        for name, label in [('chunk_log','chunking'), ('extract_chunk_observations','chunk_observation'), ('ask_model','model_generation'), ('discover_tools_via_mcp','tool_discovery'), ('get_run_config_via_mcp','configuration')]:
            setattr(inv, name, timed(label, getattr(inv, name)))
        log = timed('read_log', inv.read_run_log)(args.run_id)
        save('input.log', log)
        metrics['input_sha256'] = hashlib.sha256(log.encode()).hexdigest()
        metrics['input_lines'] = len(log.splitlines())
        tokenizer, model, embedding_model, device = timed('model_loading', inv.get_models)()
        metrics['device'] = device
        observations = timed('observation_extraction', inv.extract_log_observations)(log, tokenizer)
        save('observations.txt', observations)
        guides = timed('retrieval', inv.retrieve_guides)(observations, embedding_model, top_k=1)
        report = timed('investigation', inv.generate_investigation)(run_id=args.run_id, log_text=observations, retrieved_guides=guides)
        save('report.md', report)
        if report.startswith('Investigation stopped:'):
            raise RuntimeError(report)
        metrics['status'] = 'completed'
    except Exception as error:
        metrics['status'] = 'failed'
        metrics['error'] = str(error)
        save('error.txt', traceback.format_exc())
        print(f'FAILED: {error}', flush=True)
    finally:
        metrics['total_seconds'] = perf_counter() - started
        save('metrics.json', metrics)
        print(f"{metrics['status']}: total {metrics['total_seconds']:.2f}s; {output}", flush=True)
    if metrics['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
