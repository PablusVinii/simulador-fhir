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

if __name__ == '__main__':
    # Inicio do processo
    df = extrair_resultados()
    
    # Tratamento basico de CPFs e interpretacao
    # remove pontos e tracos do cpf
    df['cpf_clean'] = df['cpf_paciente'].str.replace(r'\D','',regex=True).str.zfill(11)
    df['interpretacao_fhir'] = df['interpretacao'].map(INTERPRETACAO).fillna('N')

    lista_resultados = []
    for _, row in df.iterrows():
        try:
            obs = build_obs(row)
            
            # Post para o servidor
            resp = requests.post(
                f'{URL_SERVIDOR}/Observation',
                json=obs,
                headers={'Content-Type': 'application/fhir+json'}
            )
            
            res = {
                'status': resp.status_code,
                'id': resp.json().get('id',''),
                'cpf': row['cpf_clean'],
                'exame': row['descricao']
            }
            
            if resp.status_code != 201:
                print(f"[Aviso] Problema com {row['nome']}: {resp.text[:100]}")
            
            lista_resultados.append(res)
            
            status_msg = 'OK' if resp.status_code == 201 else 'ERRO'
            print(f"  [{status_msg}] {row['nome']} - {row['descricao']} -> {resp.status_code}")
            
        except Exception as e:
            print(f"Erro ao processar linha: {e}")

    # Salva o log em csv
    pd.DataFrame(lista_resultados).to_csv('resultado_pipeline.csv', index=False)
    print('\nRelatorio gerado com sucesso.')