#!/usr/bin/env python3
"""Exporta uma sessao Hermes e processa um teste com Logger 0.3."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile', required=True)
    ap.add_argument('--session-id', required=True)
    ap.add_argument('--test', required=True)
    ap.add_argument('--message-id')
    ap.add_argument('--output', required=True, help='Raiz dos registros; cada chamada cria subpasta exclusiva')
    args = ap.parse_args()
    test = args.test.upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{1,39}', test):
        raise ValueError('Codigo de teste invalido.')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.profile) or not re.fullmatch(r'[A-Za-z0-9_-]+', args.session_id):
        raise ValueError('Perfil ou ID de sessao invalido.')
    logger = Path(__file__).with_name('guto_logger.py')
    if not logger.is_file():
        raise FileNotFoundError('guto_logger.py deve estar ao lado do registrador.')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run = Path(args.output).resolve() / f'{test}-{stamp}-{uuid.uuid4().hex[:12]}'
    run.mkdir(parents=True, exist_ok=False)
    marker = run / 'INCOMPLETO.txt'
    marker.write_text('Registro em andamento ou interrompido. Nao considerar concluido.', encoding='utf-8')
    source = run / 'export.jsonl'
    export_cmd = ['hermes', '-p', args.profile, 'sessions', 'export', str(source), '--format', 'jsonl', '--session-id', args.session_id]
    result = subprocess.run(export_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (run / 'export-stdout.txt').write_text(result.stdout, encoding='utf-8')
    (run / 'export-stderr.txt').write_text(result.stderr, encoding='utf-8')
    if result.returncode != 0:
        raise RuntimeError(f'Exportacao falhou: codigo {result.returncode}. Diagnostico em {run}')
    raw = source.read_bytes()
    sessions = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    if len(sessions) != 1 or not isinstance(sessions[0], dict):
        raise ValueError('Export deve conter exatamente uma sessao.')
    data = sessions[0]
    if str(data.get('id')) != args.session_id:
        raise ValueError('ID exportado diverge do ID solicitado; utilize o ID completo.')
    if data.get('profile_name') != args.profile:
        raise ValueError('Perfil exportado ausente ou divergente; revisar export antes de processar.')
    logger_cmd = [sys.executable, str(logger), '--input', str(source), '--output', str(run / 'EVIDENCIAS'), '--test', test, '--session-id', args.session_id]
    if args.message_id:
        logger_cmd += ['--message-id', args.message_id]
    result = subprocess.run(logger_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (run / 'logger-stdout.txt').write_text(result.stdout, encoding='utf-8')
    (run / 'logger-stderr.txt').write_text(result.stderr, encoding='utf-8')
    if result.returncode != 0:
        raise RuntimeError(f'Logger falhou: codigo {result.returncode}. Diagnostico em {run}')
    evidence = run / 'EVIDENCIAS' / test
    meta = json.loads((evidence / f'{test}-METADADOS.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(raw).hexdigest()
    copy_digest = hashlib.sha256((evidence / f'{test}-ORIGEM.jsonl').read_bytes()).hexdigest()
    checks = (meta.get('logger_version') == '0.3', meta.get('session_id') == args.session_id,
              meta.get('test_id') == test, meta.get('source_format') == 'jsonl',
              meta.get('source_sha256') == digest == copy_digest,
              len(list(evidence.iterdir())) == 7, not (evidence / 'INCOMPLETO.txt').exists())
    if args.message_id:
        checks += (str(meta.get('user_message_id')) == args.message_id,)
    if not all(checks):
        raise ValueError('Conferencia final falhou; manter registro como incompleto.')
    receipt = dict(registrar_version='0.1', logger_version='0.3', status='concluido', profile=args.profile,
                   session_id=args.session_id, test_id=test, user_message_id=meta['user_message_id'],
                   assistant_message_ids=meta['assistant_message_ids'], source_sha256=digest,
                   evidence_directory=str(evidence), export_command=export_cmd, logger_command=logger_cmd,
                   export_returncode=0, logger_returncode=0, tool_counts=meta['tool_counts'],
                   redaction='none; integral local export', assessment_status='pendente',
                   logger_code_sha256=hashlib.sha256(logger.read_bytes()).hexdigest())
    (run / 'REGISTRO.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    marker.unlink()
    print(f'REGISTRO CONCLUIDO: {run}')
    print(f'Teste: {test} | prompt: {meta["user_message_id"]} | ferramentas: {meta["tool_call_count"]}')
    print('Exportacao e extracao verificadas; avaliacao humana pendente.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
