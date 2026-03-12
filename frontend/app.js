const HAPI_URL = 'http://127.0.0.1:8080/fhir';

// Elementos do DOM
const obsGrid = document.getElementById('obs-grid');
const obsCount = document.getElementById('obs-count');
const modal = document.getElementById('modal');
const fhirForm = document.getElementById('fhir-form');

// Carregar Dados (READ)
async function fetchObservations() {
    try {
        const response = await fetch(`${HAPI_URL}/Observation?_sort=-_lastUpdated&_count=50`);
        const data = await response.json();
        
        renderObservations(data.entry || []);
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
        obsGrid.innerHTML = '<div class="empty-state">Erro ao conectar com o servidor FHIR. Verifique se o HAPI está rodando em :8080.</div>';
    }
}

function renderObservations(entries) {
    obsGrid.innerHTML = '';
    obsCount.innerText = entries.length;

    if (entries.length === 0) {
        obsGrid.innerHTML = '<div class="empty-state">Nenhum exame encontrado no servidor.</div>';
        return;
    }

    entries.forEach(entry => {
        const obs = entry.resource;
        const patientName = obs.subject?.display || 'Paciente Desconhecido';
        const patientCpf = obs.subject?.identifier?.value || 'N/A';
        const desc = obs.code?.text || obs.code?.coding?.[0]?.display || 'Exame Sem Nome';
        const value = obs.valueQuantity?.value || '0';
        const unit = obs.valueQuantity?.unit || '';
        const id = obs.id;
        const date = obs.issued ? new Date(obs.issued).toLocaleDateString('pt-BR') : 'Data N/A';

        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="card-header">
                <span class="badge badge-id">#${id}</span>
                <span class="badge badge-status">Final</span>
            </div>
            <div class="card-title">${desc}</div>
            <div class="card-sub">
                <i class="fa-solid fa-user" style="font-size: 0.8rem; color: var(--primary);"></i> ${patientName} <br>
                <span style="font-size: 0.75rem;">CPF: ${patientCpf} | Emissão: ${date}</span>
            </div>
            <div class="card-value">${value} <span style="font-size: 1rem; color: var(--text-dim);">${unit}</span></div>
            <div class="card-actions">
                <button class="btn-icon btn-edit" onclick="editObservation('${id}')" title="Editar">
                    <i class="fa-solid fa-pen-to-square"></i>
                </button>
                <button class="btn-icon btn-delete" onclick="deleteObservation('${id}')" title="Excluir">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;
        obsGrid.appendChild(card);
    });
}

// Criar ou Atualizar (CREATE / UPDATE)
fhirForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('edit-id').value;
    const cpf = document.getElementById('patient-cpf').value;
    const desc = document.getElementById('obs-desc').value;
    const value = document.getElementById('obs-value').value;
    const unit = document.getElementById('obs-unit').value;
    const loinc = document.getElementById('obs-loinc').value;

    const observation = {
        resourceType: "Observation",
        status: "final",
        code: {
            coding: [{ system: "http://loinc.org", code: loinc, display: desc }],
            text: desc
        },
        subject: {
            identifier: { system: "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf", value: cpf }
        },
        issued: new Date().toISOString(),
        valueQuantity: {
            value: parseFloat(value),
            unit: unit,
            system: "http://unitsofmeasure.org",
            code: unit
        }
    };

    if (id) observation.id = id;

    const method = id ? 'PUT' : 'POST';
    const url = id ? `${HAPI_URL}/Observation/${id}` : `${HAPI_URL}/Observation`;

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/fhir+json' },
            body: JSON.stringify(observation)
        });

        if (response.ok) {
            closeModal();
            fetchObservations();
        } else {
            alert('Erro ao salvar no servidor FHIR.');
        }
    } catch (error) {
        console.error('Erro:', error);
    }
});

// Excluir (DELETE)
async function deleteObservation(id) {
    if (!confirm(`Deseja realmente excluir a Observação #${id}?`)) return;

    try {
        const response = await fetch(`${HAPI_URL}/Observation/${id}`, { method: 'DELETE' });
        if (response.ok) {
            fetchObservations();
        } else {
            alert('Erro ao excluir registro.');
        }
    } catch (error) {
        console.error('Erro:', error);
    }
}

// Funções de Interface
function openModal() {
    document.getElementById('modal-title').innerText = 'Cadastrar Exame';
    document.getElementById('edit-id').value = '';
    fhirForm.reset();
    modal.style.display = 'block';
}

function closeModal() {
    modal.style.display = 'none';
}

async function editObservation(id) {
    try {
        const response = await fetch(`${HAPI_URL}/Observation/${id}`);
        const obs = await response.json();

        document.getElementById('modal-title').innerText = 'Editar Exame';
        document.getElementById('edit-id').value = id;
        document.getElementById('patient-cpf').value = obs.subject?.identifier?.value || '';
        document.getElementById('obs-desc').value = obs.code?.text || '';
        document.getElementById('obs-value').value = obs.valueQuantity?.value || '';
        document.getElementById('obs-unit').value = obs.valueQuantity?.unit || '';
        document.getElementById('obs-loinc').value = obs.code?.coding?.[0]?.code || '';

        modal.style.display = 'block';
    } catch (error) {
        console.error('Erro ao buscar detalhe:', error);
    }
}

// Fechar modal ao clicar fora
window.onclick = function(event) {
    if (event.target == modal) closeModal();
}

// Iniciar
fetchObservations();
