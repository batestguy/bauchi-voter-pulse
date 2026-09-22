import json
from collections import Counter

humans = [json.loads(l) for l in open('data/pilot/pilot_500.jsonl', encoding='utf-8')]
jevs = [json.loads(l) for l in open('data/pilot/jev_out.jsonl', encoding='utf-8')]

print('MENTIONS misses (human -> jev-no-mention means jev yes=False):')
for h, j in zip(humans, jevs):
    a = j['answers']
    if int(a['mentions_candidate']['yes']) != h['human_mentions_candidate']:
        print(' ', h['raw_id'], '|', h['text'], '| human=', h['human_mentions_candidate'],
              'noul=', round(a['mentions_candidate']['noul'], 2))
print('SENT misses:')
for h, j in zip(humans, jevs):
    a = j['answers']
    if a['sentiment']['choice'] != h['human_sentiment']:
        print(' ', h['raw_id'], '|', h['human_language'], '|', h['text'][:90],
              '| human=', h['human_sentiment'], 'jev=', a['sentiment']['choice'],
              round(a['sentiment']['confidence'], 2))
print('LANG misses:')
print(Counter((h['human_language'], j['answers']['language']['choice'])
              for h, j in zip(humans, jevs)
              if j['answers']['language']['choice'] != h['human_language']))
