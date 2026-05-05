import json
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
model_file = script_dir / 'models' / 'UG' / 'ugofficial.vtube.json'

with open(model_file, encoding='utf-8') as f:
    data = json.load(f)

print('=== VTube Studio 模型配置 ===')
print('All keys:', list(data.keys()))
print()

for key, value in data.items():
    if isinstance(value, dict):
        print(f'{key}: (dict, {len(value)} items)')
        for k2, v2 in list(value.items())[:5]:
            print(f'  {k2}: {v2}')
    elif isinstance(value, list):
        print(f'{key}: (list, {len(value)} items)')
        if value:
            print(f'  first: {str(value[0])[:100]}')
    else:
        print(f'{key}: {value}')
