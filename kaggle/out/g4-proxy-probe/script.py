# Sonde du Kaggle Model Proxy : modèles disponibles et appel d'outil. N'affiche jamais la clé.
import os, json, urllib.request
names = sorted(k for k in os.environ if 'PROXY' in k or 'MODEL' in k or 'BENCH' in k)
print('variables présentes :', names)
url = os.environ.get('MODEL_PROXY_URL', '').rstrip('/')
key = os.environ.get('MODEL_PROXY_API_KEY', '')
print('url définie :', bool(url), '| clé définie :', bool(key), '| url :', url)
for k in names:
    v = os.environ[k]
    if 'KEY' not in k and 'TOKEN' not in k and 'SECRET' not in k:
        print(f'  {k} = {v[:200]}')
def call(path, body=None):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())
for base in ('/openapi', ''):
    try:
        m = call(base + '/models')
        ids = [x.get('id') for x in m.get('data', [])]
        print(base or '/', 'modèles :', ids)
        g = [i for i in ids if 'gemma' in (i or '').lower()]
        if g:
            target = next((i for i in g if '31b' in i), g[0])
            r = call(base + '/chat/completions', {'model': target, 'max_tokens': 200,
                'messages': [{'role': 'user', 'content': 'List files in /workspace using the tool.'}],
                'tools': [{'type': 'function', 'function': {'name': 'run_command', 'description': 'Run a shell command',
                           'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}}}]})
            print('appel outil', target, ':', json.dumps(r.get('choices', [{}])[0].get('message'))[:500], r.get('usage'))
        break
    except Exception as e:
        print(base or '/', 'échec :', repr(e)[:300])
