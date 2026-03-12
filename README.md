# Trajetória: Implementação do Simulador de Integração FHIR

Este documento detalha o processo passo a passo para configurar um ambiente local de interoperabilidade em saúde, desde a subida do servidor FHIR até a execução da pipeline de dados.

## 1. Configuração do Servidor FHIR Local

Para que o projeto tenha onde salvar os dados, é necessário um servidor que suporte o padrão HL7 FHIR. A forma mais rápida e comum é utilizar o **HAPI FHIR Starter**.

### Pré-requisitos
*   Docker instalado (recomendado) ou ambiente Java (JDK 11+).

### Passo a passo (via Docker)
1.  Abra o terminal e execute o comando para subir o container do servidor:
    ```bash
    docker run -d -p 8080:8080 --name hapi-fhir hapiproject/hapi-fhir-jpaserver-starter
    ```
2.  Aguarde alguns minutos para a inicialização.
3.  Acesse `http://localhost:8080/fhir` no navegador. Se a página do HAPI carregar, o servidor está pronto para receber requisições.

---

## 2. Preparação do Ambiente Python

O projeto utiliza Python para orquestrar a extração e transformação dos dados.

1.  **Criação do Ambiente Virtual**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # No Windows: .venv\Scripts\activate
    ```
2.  **Instalação das Bibliotecas**:
    ```bash
    pip install pandas requests
    ```

---

## 3. Preparação do "Legado" (Banco de Dados)

Antes de integrar, precisamos dos dados brutos. O arquivo `setup_banco.py` simula o banco de dados de um hospital real.

1.  Execute o script para criar o banco de dados SQLite local:
    ```bash
    python setup_banco.py
    ```
2.  Isso criará o arquivo `hospital_ses.db` com tabelas de pacientes e resultados de exames laboratoriais pré-configurados.

---

## 4. Execução da Pipeline de Integração

Com o banco local pronto e o servidor HAPI rodando, executamos o processo de ETL (Extração, Transformação e Carga).

1.  Execute o script principal:
    ```bash
    python pipeline_rel.py
    ```
2.  **O que acontece durante a execução**:
    *   **Extração**: O script lê os dados do SQLite e junta as informações de paciente com seus exames.
    *   **Transformação**: O script converte CPFs, limpa strings e mapeia os resultados para o formato JSON FHIR (Recurso `Observation`).
    *   **Carga**: Cada exame é enviado via POST para `http://localhost:8080/fhir/Observation`.

---

## 5. Verificação dos Resultados

Existem duas formas de validar se a trajetória foi concluída com sucesso:

1.  **Relatório CSV**: O arquivo `resultado_pipeline.csv` será gerado na pasta do projeto, mostrando o status HTTP de cada envio (Status 201 significa "Criado com Sucesso").
2.  **Consulta no Servidor**:
    *   Vá ao navegador em `http://localhost:8080/fhir/Observation`.
    *   Você verá a lista de recursos que o seu script acabou de injetar no servidor.

---

## Glossário de Tecnologias Utilizadas
*   **FHIR**: Padrão internacional para troca de dados de saúde.
*   **HAPI FHIR**: Servidor open-source de referência para implementação do padrão.
*   **LOINC**: Sistema de codificação para exames laboratoriais.
*   **SQLite**: Banco de dados leve usado para simular o sistema hospitalar legado.
*   **Python + Pandas**: Ferramentas para manipulação e limpeza de dados em larga escala.
