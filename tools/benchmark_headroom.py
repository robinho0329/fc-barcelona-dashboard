"""Offline input compression experiment; not an account-usage measurement."""
import json
from pathlib import Path
from headroom import compress
import tiktoken

root = Path(__file__).resolve().parents[1]
enc = tiktoken.get_encoding('o200k_base')
cases = {
    'handoff': (root / 'HANDOFF.md').read_text(encoding='utf-8'),
    'source': (root / 'views/coverage.py').read_text(encoding='utf-8'),
    'synthetic_log': '\n'.join(f'INFO request {i} status=200 completed successfully' for i in range(1000)) + '\nFATAL sentinel: manager total mismatch 1265 vs 1264',
}
for name, content in cases.items():
    messages = [
        {'role':'user','content':'Inspect this tool output. Preserve errors and exact numbers.'},
        {'role':'assistant','content':None,'tool_calls':[{'id':'read1','type':'function','function':{'name':'read_file','arguments':'{}'}}]},
        {'role':'tool','tool_call_id':'read1','content':content},
        {'role':'user','content':'Report issues.'},
    ]
    result = compress(messages, model='gpt-4o')
    out = '\n'.join(str(m.get('content') or '') for m in result.messages if m.get('role')=='tool')
    print(json.dumps({'case':name,'before':result.tokens_before,'after':result.tokens_after,
        'saved_percent':round(result.compression_ratio*100,1),
        'sentinel_preserved': 'FATAL sentinel: manager total mismatch 1265 vs 1264' in out if name=='synthetic_log' else None,
        'unchanged':out==content}, ensure_ascii=False))
full = len(enc.encode(cases['handoff']))
brief = len(enc.encode((root/'docs/CURRENT.md').read_text(encoding='utf-8')))
print(json.dumps({'case':'targeted_context_not_equivalent_content','full':full,'brief':brief,'saved_percent':round((1-brief/full)*100,1)}))
