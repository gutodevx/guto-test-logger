#!/usr/bin/env python3
"""GUTO Test Logger v0.3 - processa exportacao JSON do Hermes Desktop, sem acessar Hermes."""
import argparse, collections, datetime, hashlib, json, pathlib, re, sys


def utc_stamp(v):
    if v is None: return None
    try: return datetime.datetime.fromtimestamp(float(v), tz=datetime.timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError): return None

def main():
    ap=argparse.ArgumentParser(description='Extrai um teste de JSON Desktop ou JSONL CLI do Hermes.')
    ap.add_argument('--input', required=True, help='Export JSON Desktop ou JSONL CLI')
    ap.add_argument('--output', required=True, help='Pasta de saida isolada')
    ap.add_argument('--test', required=True, help='Codigo do teste, ex.: B3-T01')
    ap.add_argument('--session-id', help='ID exato da sessao; obrigatorio se houver varias no JSONL')
    ap.add_argument('--message-id', help='ID exato do prompt do usuario no export')
    ap.add_argument('--force', action='store_true', help='Permitir criar nova versao quando mesmo teste ja existe (sem substituir)')
    args=ap.parse_args()
    src=pathlib.Path(args.input).resolve(strict=True)
    suffix=src.suffix.lower()
    if not src.is_file() or suffix not in ('.json','.jsonl'):
        raise ValueError('Entrada deve ser JSON ou JSONL.')
    raw=src.read_bytes()
    decoded=raw.decode('utf-8-sig')
    sessions=([json.loads(line) for line in decoded.splitlines() if line.strip()]
              if suffix=='.jsonl' else [json.loads(decoded)])
    if not sessions or not all(isinstance(s,dict) for s in sessions):
        raise ValueError('Exportacao deve conter objetos de sessao.')
    def identity(s):
        sid=s.get('session_id')
        rid=s.get('id')
        if sid is not None and rid is not None and str(sid)!=str(rid):
            raise ValueError('IDs conflitantes na raiz da sessao.')
        return sid if sid is not None else rid
    candidates=[s for s in sessions if args.session_id is None or str(identity(s))==args.session_id]
    if len(candidates)!=1:
        raise ValueError('Selecao de sessao ambigua ou ausente; informe --session-id exato.')
    data=candidates[0]
    session_id=identity(data)
    if session_id is None:
        raise ValueError('ID da sessao ausente.')
    all_msgs=data.get('messages')
    if not isinstance(all_msgs,list) or not all_msgs or not all(isinstance(m,dict) for m in all_msgs):
        raise ValueError('messages deve ser lista nao vazia de objetos.')
    for m in all_msgs:
        if m.get('session_id') is not None and str(m['session_id'])!=str(session_id):
            raise ValueError('Mensagem pertence a outra sessao.')
        for flag in ('active','compacted'):
            if flag in m and (type(m[flag]) not in (int,bool) or m[flag] not in (0,1)):
                raise ValueError(f'Flag {flag} invalida.')
            if suffix=='.jsonl' and flag not in m:
                raise ValueError(f'Flag {flag} ausente no JSONL; revisar formato.')
    msgs=[m for m in all_msgs if m.get('active',True)]
    excluded_inactive=len(all_msgs)-len(msgs)
    test=args.test.upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{1,39}',test):
        raise ValueError('Codigo de teste invalido.')
    if not all(isinstance(m,dict) for m in msgs):
        raise ValueError('messages deve conter objetos.')
    user_idxs=[i for i,m in enumerate(msgs) if m.get('role')=='user']
    if args.message_id is not None:
        selected=[i for i in user_idxs if str(msgs[i].get('id'))==args.message_id]
        selection_method='explicit_message_id'
    else:
        pattern=re.compile(r'(?<![\w-])'+re.escape(test)+r'(?![\w-])',re.I)
        selected=[i for i in user_idxs if isinstance(msgs[i].get('content'),str)
                  and pattern.search(msgs[i]['content'])]
        selection_method='exact_test_label'
    if len(selected)!=1:
        raise ValueError(f'Selecao encontrou {len(selected)} prompts. Informe --message-id com um ID unico de mensagem do usuario; nenhuma evidencia foi criada.')
    start=selected[0]
    end=next((i for i in user_idxs if i>start),len(msgs))
    segment=msgs[start:end]
    if any(m.get('compacted',False) for m in segment):
        raise ValueError('Trecho selecionado contem mensagens compactadas; revisar linhagem antes de extrair.')
    if not all(isinstance(m.get('content'),(str,type(None))) for m in segment):
        raise ValueError('Conteudo estruturado nao suportado neste trecho.')
    finals=[m for m in segment if m.get('role')=='assistant' and m.get('content') and m.get('finish_reason')=='stop' and not m.get('tool_calls')]
    if any(m.get('role')=='assistant' and m.get('content') and m.get('finish_reason') not in ('stop','tool_calls') for m in segment):
        raise ValueError('Resposta com termino ausente ou nao concluido; revisar export.')
    if not finals: raise ValueError('Nao existe resposta final do agente apos o prompt selecionado.')
    tools=[]
    for m in segment:
        if m.get('role')=='assistant':
            for t in m.get('tool_calls') or []:
                f=t.get('function') or {}
                arguments=f.get('arguments')
                try:arguments=json.loads(arguments) if isinstance(arguments,str) else arguments
                except json.JSONDecodeError:pass
                tools.append({'id':t.get('id'),'name':f.get('name'),'arguments':arguments,'timestamp_utc':utc_stamp(m.get('timestamp'))})
    result_rows=[m for m in segment if m.get('role')=='tool']
    call_ids=[t['id'] for t in tools]
    result_ids=[m.get('tool_call_id') for m in result_rows]
    if any(not isinstance(x,str) or not x for x in call_ids+result_ids):
        raise ValueError('ID de ferramenta ausente ou invalido.')
    if len(set(call_ids))!=len(call_ids) or len(set(result_ids))!=len(result_ids):
        raise ValueError('IDs de ferramenta duplicados; revisar trecho.')
    if set(call_ids)!=set(result_ids):
        raise ValueError('Chamadas e resultados nao correspondem integralmente.')
    outputs={m['tool_call_id']:m for m in result_rows}
    for t in tools:
        m=outputs.get(t['id'])
        if m: t['result']=m.get('content'); t['result_timestamp_utc']=utc_stamp(m.get('timestamp'))
    counts=collections.Counter(t.get('name') or 'unknown' for t in tools)
    parsed_paths=[]
    for t in tools:
        if t.get('name')=='read_file':
            p=(t.get('arguments') or {}).get('path') if isinstance(t.get('arguments'),dict) else None
            if p: parsed_paths.append(p)
    outroot=pathlib.Path(args.output).resolve()
    if src.parent==outroot: raise ValueError('A pasta de saida deve ser separada da exportacao original.')
    outroot.mkdir(parents=True,exist_ok=True)
    target=outroot/test
    if target.exists():
        if not args.force: raise FileExistsError(f'{target} ja existe; nenhum arquivo sera substituido. Use --force para criar outra versao sem substituir a anterior.')
        i=2
        while (outroot/f'{test}-V{i:02d}').exists():i+=1
        target=outroot/f'{test}-V{i:02d}'
    target.mkdir()
    (target/'INCOMPLETO.txt').write_text('Gravacao em andamento. Nao utilizar como evidencia completa.',encoding='utf-8')
    pfx=test
    try:
        (target/f'{pfx}-PROMPT.md').write_text(f'# {test} — Prompt original\n\n'+(segment[0].get('content') or '')+'\n',encoding='utf-8')
        (target/f'{pfx}-RESPOSTA.md').write_text(f'# {test} — Resposta do Hermes\n\n'+ '\n\n'.join(str(m['content']) for m in finals)+'\n',encoding='utf-8')
        (target/f'{pfx}-FERRAMENTAS.json').write_text(json.dumps(tools,ensure_ascii=False,indent=2),encoding='utf-8')
        meta={'logger_version':'0.3','selection_method':selection_method,'run_directory':target.name,'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'test_id':test,'session_id':session_id,'source_format':suffix[1:],'source_session_count':len(sessions),'source_message_count':len(all_msgs),'excluded_inactive_count':excluded_inactive,'message_policy':'active messages only; reject compacted selected segment; missing flags allowed only for desktop JSON','session_title':data.get('title'),
              'exported_at':data.get('exported_at'),'source_file':src.name,'source_sha256':hashlib.sha256(raw).hexdigest(),
              'user_message_id':segment[0].get('id'),'assistant_message_ids':[m.get('id') for m in finals],
              'start_utc':utc_stamp(segment[0].get('timestamp')),'end_utc':utc_stamp(finals[-1].get('timestamp')),
              'tool_call_count':len(tools),'tool_counts':dict(counts),'read_file_paths':list(dict.fromkeys(parsed_paths)),
              'model':None,'model_note':'Nao informado em campo estruturado desta exportacao; nao inferido.',
              'review_status':'pendente','assessment_score':None,
              'notice':'Arquivos de exportacao podem conter dados sensiveis; revisar antes de compartilhar.'}
        (target/f'{pfx}-METADADOS.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        (target/f'{pfx}-AVALIACAO.md').write_text(f'# {test} — Avaliacao pendente\n\n- Status: **Aguardando revisao humana**\n- Pontuacao: **nao atribuida**\n- Observacoes: \n\n> Nota: exportar a conversa nao comprova a veracidade das respostas; comparar com os documentos originais.\n',encoding='utf-8')
        (target/f'{pfx}-ORIGEM-SHA256.txt').write_text(f'SHA256  {hashlib.sha256(raw).hexdigest()}  {src.name}\n',encoding='utf-8')
        (target/f'{pfx}-ORIGEM{suffix}').write_bytes(raw)
        (target/'INCOMPLETO.txt').unlink()
    except Exception:
        print(f'Execucao incompleta, nao utilizar: {target}',file=sys.stderr)
        raise
    print(f'OK: {target}')
    print(f'Teste: {test} | ferramentas: {len(tools)} | read_file: {counts.get("read_file",0)}')
    print('Arquivos criados: 7. Copia integral da origem preservada com SHA256.')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('ERRO:',e,file=sys.stderr)
        sys.exit(1)
