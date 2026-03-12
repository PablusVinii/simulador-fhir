import sqlite3

conn = sqlite3.connect('hospital_ses.db')
cur = conn.cursor()

cur.executescript('''
CREATE TABLE IF NOT EXISTS pacientes (
    id          INTEGER PRIMARY KEY,
    cpf         TEXT NOT NULL,
    nome        TEXT NOT NULL,
    nascimento  TEXT NOT NULL,
    sexo        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resultados_exame (
    id              INTEGER PRIMARY KEY,
    cpf_paciente    TEXT NOT NULL,
    codigo_exame    TEXT NOT NULL,
    descricao       TEXT NOT NULL,
    resultado       REAL NOT NULL,
    unidade         TEXT NOT NULL,
    ref_min         REAL,
    ref_max         REAL,
    interpretacao   TEXT,
    metodo          TEXT,
    data_coleta     TEXT NOT NULL,
    data_emissao    TEXT NOT NULL,
    cnes_lab        TEXT NOT NULL,
    cpf_responsavel TEXT NOT NULL,
    conselho        TEXT NOT NULL,
    loinc           TEXT
);
''')

pacientes = [
    ('07123456789', 'Maria Aparecida da Silva', '1985-03-22', 'female'),
    ('98765432100', 'João Carlos Pereira',      '1972-11-08', 'male'),
    ('11122233344', 'Ana Beatriz Souza',         '1995-07-14', 'female'),
]
cur.executemany(
    'INSERT INTO pacientes (cpf,nome,nascimento,sexo) VALUES (?,?,?,?)',
    pacientes
)

resultados = [
    ('07123456789','HB','Hemoglobina',
     7.4,'g/dL',12.0,16.0,'BAIXO',
     'Automatizado - Cell-Dyn Ruby',
     '2026-03-01T08:00:00-03:00','2026-03-01T14:30:00-03:00',
     '2337991','12345678900','71','718-7'),

    ('07123456789','GLI','Glicemia em jejum',
     95.0,'mg/dL',70.0,99.0,'NORMAL',
     'Enzimático colorimétrico',
     '2026-03-01T08:00:00-03:00','2026-03-01T14:30:00-03:00',
     '2337991','12345678900','71','2339-0'),

    ('98765432100','HB','Hemoglobina',
     16.2,'g/dL',13.5,17.5,'NORMAL',
     'Automatizado - Cell-Dyn Ruby',
     '2026-03-02T09:00:00-03:00','2026-03-02T15:00:00-03:00',
     '2337991','00011111100','15','718-7'),

    ('11122233344','GLI','Glicemia em jejum',
     28.0,'mg/dL',70.0,99.0,'CRITICO BAIXO',
     'Enzimático colorimétrico',
     '2026-03-03T07:30:00-03:00','2026-03-03T11:00:00-03:00',
     '2337991','00011111100','15','2339-0'),
]
cur.executemany('''
    INSERT INTO resultados_exame
    (cpf_paciente,codigo_exame,descricao,resultado,unidade,
     ref_min,ref_max,interpretacao,metodo,data_coleta,
     data_emissao,cnes_lab,cpf_responsavel,conselho,loinc)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
''', resultados)

conn.commit()
conn.close()
print('Banco hospital_ses.db inicializado.')