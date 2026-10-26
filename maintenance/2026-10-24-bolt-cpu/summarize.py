"""Summarize saved measurements without running another inference."""
import csv
import json
from pathlib import Path
import statistics

OUT = Path(__file__).resolve().parent


def main():
    results = []
    conversations = []
    for mode in ('baseline', 'dflash'):
        path = OUT / f'{mode}-t16.json'
        if not path.exists():
            continue
        report = json.loads(path.read_text(encoding='utf-8'))
        for count in sorted({row['actual_input_tokens'] for row in report['rows']}):
            rows = [row for row in report['rows'] if row['actual_input_tokens'] == count]
            results.append({'mode': mode, 'input_tokens': count, 'repeats': len(rows),
                'prefill_seconds': statistics.mean(row['timings']['prompt_ms'] / 1000 for row in rows),
                'prefill_tokens_per_second': statistics.mean(row['timings']['prompt_per_second'] for row in rows),
                'first_content_seconds': statistics.mean(row['first_content_seconds'] for row in rows),
                'generation_tokens_per_second': statistics.mean(row['timings']['predicted_per_second'] for row in rows),
                'total_seconds_128_output': statistics.mean(row['wall_seconds'] for row in rows),
                'max_working_set_gib': max(row['memory']['working_set_gib'] for row in rows if row.get('memory')),
                'all_prompts_fully_evaluated': all(row['timings']['prompt_n'] == count and row['timings']['cache_n'] == 0 for row in rows),
                'all_outputs_128_tokens': all(row['timings']['predicted_n'] == 128 for row in rows)})
        for row in report.get('conversation', []):
            conversations.append({'mode': mode, 'prompt': row['prompt'], 'answer': row['text'],
                                  'first_content_seconds': row['first_content_seconds'],
                                  'first_sentence_seconds': row['first_sentence_seconds'],
                                  'total_seconds': row['wall_seconds'], 'timings': row['timings']})
    summary = {'results': results, 'conversation': conversations,
               'limits': 'Two repeats per fixed prompt; warm model, prompt cache disabled; CPU only, 16 threads; short conversations tested once per mode. No microphone, ASR or TTS.'}
    (OUT / 'results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if results:
        with (OUT / 'results.csv').open('w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
