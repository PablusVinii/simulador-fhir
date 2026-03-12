import sqlite3, json, uuid, requests
import pandas as pd

# Dicionarios de auxilio para o padrao FHIR
INTERPRETACAO = {
    'N':'N','NORMAL':'N','Normal':'N',
    'H':'H','HIGH':'H','ALTO':'H',
    'L':'L','LOW':'L','BAIXO':'L',
    'HH':'HH','CRITICO ALTO':'HH','PANICO ALTO':'HH',
    'LL':'LL','CRITICO BAIXO':'LL','PANICO BAIXO':'LL',
}

CONSELHOS = {
    '71': {'code':'71', 'display':'Conselho Regional de Medicina'},
    '15': {'code':'15', 'display':'Conselho Regional de Biomedicina'},
    '69': {'code':'69', 'display':'Conselho Regional de Farmácia'},
}

URL_SERVIDOR = 'http://localhost:8080/fhir'

def extrair_resultados():
    conn = sqlite3.connect('hospital_ses.db')
    df = pd.read_sql('''
        SELECT r.*, p.nome, p.nascimento, p.sexo
        FROM resultados_exame r
        JOIN pacientes p ON p.cpf = r.cpf_paciente
        WHERE r.processado = 0
    ''', conn)
    conn.close()
    print(f'Extraidos {len(df)} registros')
    return df

def build_obs(row):
    # Pega o conselho ou usa CRM como padrao
    c = CONSELHOS.get(str(row['conselho']), CONSELHOS['71'])
    return {
        'resourceType': 'Observation',
        'id': str(uuid.uuid4()),
        'status': 'final',
        'contained': [{
            'resourceType': 'Specimen',
            'id': 'amostra',
            'type': {'coding': [{
                'system': 'http://terminology.hl7.org/CodeSystem/v2-0487',
                'code': 'BLD',
                'display': 'Whole blood'
            }]},
            'subject': {'identifier': {
                'system': 'http://meu-sistema-hospitalar.com/paciente',
                'value': row['cpf_clean']
            }},
            'collection': {'collectedDateTime': row['data_coleta']}
        }],
        'category': [{'coding': [{
            'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
            'code': 'laboratory'
        }]}],
        'code': {'coding': [{
            'system': 'http://loinc.org',
            'code': row['loinc'],
            'display': row['descricao']
        }], 'text': row['descricao']},
        'subject': {'identifier': {
            'system': 'http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf',
            'value': row['cpf_clean']
        }},
        'issued': row['data_emissao'],
        'performer': [
            {
                'id': 'estabelecimentoPrincipal',
                'identifier': {
                    'system': 'http://cnes.datasus.gov.br',
                    'value': row['cnes_lab']
                }
            },
            {
                'id': 'responsavelTecnico',
                'identifier': {
                    'system': 'http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf',
                    'value': row['cpf_responsavel']
                }
            },
            {
                'id': 'responsavelResultado',
                'identifier': {
                    'system': 'http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf',
                    'value': row['cpf_responsavel']
                }
            }
        ],
        'valueQuantity': {
            'value': float(row['resultado']),
            'unit':  row['unidade'],
            'system': 'http://unitsofmeasure.org',
            'code':   row['unidade']
        },
        'method': {'text': row['metodo']},
        'specimen': {'reference': '#amostra'},
        'interpretation': [{'coding': [{
            'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation',
            'code':  row['interpretacao_fhir'],
        }]}],
        'referenceRange': [{
           'low':  {'value': float(row['ref_min']), 'unit': row['unidade'],
                     'system': 'http://unitsofmeasure.org', 'code': row['unidade']},
            'high': {'value': float(row['ref_max']), 'unit': row['unidade'],
                     'system': 'http://unitsofmeasure.org', 'code': row['unidade']},
        }]
    }

def gerar_bundle_transacao(lista_obs):
    """
    Transforma uma lista de Observations em um único Bundle de Transação.
    """
    entradas = []
    for obs in lista_obs:
        entradas.append({
            'resource': obs,
            'request': {
                'method': 'POST',
                'url': 'Observation'
            }
        })
    
    return {
        'resourceType': 'Bundle',
        'type': 'transaction',
        'entry': entradas
    }

if __name__ == '__main__':
    # Inicio do processo
    df = extrair_resultados()
    
    # Tratamento basico
    df['cpf_clean'] = df['cpf_paciente'].str.replace(r'\D','',regex=True).str.zfill(11)
    df['interpretacao_fhir'] = df['interpretacao'].map(INTERPRETACAO).fillna('N')

    # Passo 1: Gerar todos os recursos localmente primeiro
    lista_obs_local = []
    for _, row in df.iterrows():
        try:
            obs = build_obs(row)
            lista_obs_local.append(obs)
        except Exception as e:
            print(f"Erro ao converter linha: {e}")

    # Passo 2: Se houver dados, envia tudo em um unico Bundle
    if lista_obs_local:
        print(f"\nPreparando bundle com {len(lista_obs_local)} recursos...")
        bundle = gerar_bundle_transacao(lista_obs_local)
        
        try:
            resp = requests.post(
                URL_SERVIDOR,  # Nota: Para Bundles, enviamos para a URL base /fhir
                json=bundle,
                headers={'Content-Type': 'application/fhir+json'}
            )
            
            if resp.status_code == 200:
                print("OK - Bundle de transacao processado com sucesso!")
                
                # Passo 3: Marcar registros como processados no banco original
                # Usamos os IDs internos que vieram do banco (row['id'])
                ids_processados = [row['id'] for _, row in df.iterrows()]
                
                if ids_processados:
                    conn = sqlite3.connect('hospital_ses.db')
                    cur = conn.cursor()
                    # Atualiza para 1 onde o ID está na lista de enviados
                    placeholder = ','.join(['?'] * len(ids_processados))
                    cur.execute(f'UPDATE resultados_exame SET processado = 1 WHERE id IN ({placeholder})', ids_processados)
                    conn.commit()
                    conn.close()
                    print(f"✅ {len(ids_processados)} registros marcados como processados no banco local.")

                # O servidor HAPI retorna um Bundle de resposta com os IDs gerados
                for i, entry in enumerate(resp.json().get('entry', [])):
                    status = entry.get('response', {}).get('status')
                    location = entry.get('response', {}).get('location', 'N/A')
                    print(f"  [Item {i}] Status: {status} -> {location}")
            else:
                print(f"ERRO - Falha no Bundle: {resp.status_code}")
                print(resp.text[:500])
                
        except Exception as e:
            print(f"Erro na comunicacao: {e}")

    print('\nProcesso finalizado.')