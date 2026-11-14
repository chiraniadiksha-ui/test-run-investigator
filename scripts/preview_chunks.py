"""Preview chunking; add --extract to run model observation extraction."""
import argparse
from time import perf_counter

from transformers import AutoTokenizer
from investigate import read_run_log, prepare_log_entries, chunk_log, extract_chunk_observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='RUN-CHUNK-DEMO')
    parser.add_argument('--extract', action='store_true')
    args = parser.parse_args()
    log_text = read_run_log(args.run_id)
    tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen3-4B')
    start = perf_counter()
    entries = prepare_log_entries(log_text)
    chunks = chunk_log(log_text, tokenizer)
    print(f'Original lines: {len(log_text.splitlines())}')
    print(f'Prepared entries: {len(entries)}')
    print(f'Total chunks: {len(chunks)}')
    print(f'Preparation and chunking: {perf_counter() - start:.3f}s')
    for number, chunk in enumerate(chunks, 1):
        print(f"Chunk {number}: original lines {chunk['start_line']}-{chunk['end_line']}, "
              f"{chunk['token_count']} tokens")
    if args.extract:
        start = perf_counter()
        for number, chunk in enumerate(chunks, 1):
            print(f"Observations for chunk {number}/{len(chunks)}:")
            print(extract_chunk_observations(chunk))
        print(f'Model loading and extraction: {perf_counter() - start:.3f}s')


if __name__ == '__main__':
    main()
