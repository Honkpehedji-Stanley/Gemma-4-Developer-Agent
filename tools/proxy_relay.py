#!/usr/bin/env python3
"""Relais local OpenAI-compatible vers le Kaggle Model Proxy, pour générer des trajectoires « professeur ».

Le proxy renvoie parfois `message: null` (réponse vide), ce qui fait planter litellm et déclenche des tentatives
en cascade. Le relais réessaie ces réponses vides, ajoute la clé (lue dans l'environnement, jamais en argument)
et réécrit le nom du modèle. Écoute sur 127.0.0.1 uniquement.

Usage : set -a; . ~/.config/gemma4-agent/proxy.env; set +a
        tools/proxy_relay.py --model openai/gpt-oss-120b --port 8765
Puis : tools/eval_local.py --api-base http://127.0.0.1:8765/v1 --api-key x --served-model teacher
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = os.environ['MODEL_PROXY_URL'].rstrip('/') + '/openapi/chat/completions'
KEY = os.environ['MODEL_PROXY_API_KEY']
ENV_FILE = Path.home() / '.config' / 'gemma4-agent' / 'proxy.env'
KEY_LOCK = threading.Lock()


def refresh_key(stale: str) -> None:
    """La clé du proxy expire au bout de 2 h : on en redemande une (une seule fois pour tous les fils)."""
    global KEY
    with KEY_LOCK:
        if KEY != stale:
            return  # un autre fil l'a déjà renouvelée
        subprocess.run(['uvx', '--with', 'six', 'kaggle', 'benchmarks', 'auth', '-y', '--env-file', str(ENV_FILE)],
                       capture_output=True, timeout=120)
        os.chmod(ENV_FILE, 0o600)
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith('MODEL_PROXY_API_KEY='):
                KEY = line.split('=', 1)[1].strip()
STATS = {'requests': 0, 'empty_retries': 0, 'errors': 0}


class Relay(BaseHTTPRequestHandler):
    model = ''
    log_file = None

    def log_message(self, *a):  # silence du journal HTTP par défaut
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        body['model'] = self.model
        # Le proxy renvoie surtout des réponses vides avec les longues docstrings d'outils et les paramètres vLLM.
        body.pop('chat_template_kwargs', None)
        for t in body.get('tools') or []:
            fn = t.get('function', {})
            fn['description'] = (fn.get('description') or '').strip().split('\n')[0]
        if os.environ.get('RELAY_DUMP'):
            Path(os.environ['RELAY_DUMP']).write_text(json.dumps(body, indent=1, ensure_ascii=False))
        STATS['requests'] += 1
        data, status = None, 502
        for attempt in range(25):
            key = KEY
            req = urllib.request.Request(UPSTREAM, data=json.dumps(body).encode(),
                                         headers={'Authorization': 'Bearer ' + key,
                                                  'Content-Type': 'application/json'})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    data, status = json.load(r), 200
            except urllib.error.HTTPError as e:
                data, status = {'error': {'message': e.read().decode()[:500]}}, e.code
            except Exception as e:  # noqa: BLE001
                data, status = {'error': {'message': str(e)[:500]}}, 502
            ok = status == 200 and data.get('choices') and data['choices'][0].get('message') is not None
            print(json.dumps({'t': round(time.time() - t0, 1), 'status': status, 'ok': bool(ok),
                              'usage': (data or {}).get('usage', {}).get('total_tokens')}), file=self.log_file,
                  flush=True)
            if ok:
                break
            if status == 200:
                STATS['empty_retries'] += 1
            elif status == 401:
                refresh_key(key)
                continue
            elif status in (400, 403):
                break
            time.sleep(min(1 + attempt, 5))
        if status != 200:
            STATS['errors'] += 1
        out = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='openai/gpt-oss-120b')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--log', default='logs/proxy_relay.jsonl')
    args = ap.parse_args()
    Relay.model = args.model
    Relay.log_file = open(args.log, 'a')
    srv = ThreadingHTTPServer(('127.0.0.1', args.port), Relay)
    print(f'relais sur 127.0.0.1:{args.port} -> {args.model}', file=sys.stderr, flush=True)
    srv.serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
