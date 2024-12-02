// Leia o CSRF token da meta tag
let csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
let recordingInProgress = false; // Variável para controlar o estado da gravação

// Função para iniciar a gravação
async function startRecording() {
    try {
        const response = await fetch('/transcription/start-recording/', { 
            method: 'POST', 
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            }
        });
        
        if (response.ok) {
            recordingInProgress = true;
            document.getElementById("stop-recording").disabled = false;
            console.log("Gravação iniciada.");
        } else {
            const errorData = await response.json();
            console.error("Erro ao iniciar a gravação:", errorData);
            alert(`Erro ao iniciar a gravação: ${errorData.error || "Desconhecido"}`);
        }
    } catch (error) {
        console.error("Erro ao iniciar a gravação:", error);
        alert("Erro ao iniciar a gravação. Verifique o console para mais detalhes.");
    }
}

// Função para parar a gravação
async function stopRecording() {
    if (!recordingInProgress) return;

    try {
        const response = await fetch('/transcription/stop-recording/', { 
            method: 'POST', 
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            }
        });

        if (response.ok) {
            recordingInProgress = false;
            document.getElementById("transcribe").disabled = false;
            document.getElementById("stop-recording").disabled = true;
            document.getElementById("start-recording").disabled = false;
            console.log("Gravação parada.");
        } else {
            const errorData = await response.json();
            console.error("Erro ao parar a gravação:", errorData);
            alert(`Erro ao parar a gravação: ${errorData.error || "Desconhecido"}`);
        }
    } catch (error) {
        console.error("Erro ao parar a gravação:", error);
        alert("Erro ao parar a gravação. Verifique o console para mais detalhes.");
    }
}

//evento se salvar alterações via Botão Salvar
document.getElementById("save-transcription").onclick = async () => {
    const folderSelect = document.getElementById("folder-select");
    const selectedFolderId = folderSelect.value.trim(); // Obtenha o valor do campo de seleção
    const transcriptionText = document.getElementById("transcription-text").innerText;

    if (selectedFolderId && transcriptionText) {
        try {
            const response = await fetch('/transcription/save-transcription/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ folder_id: selectedFolderId, transcription: transcriptionText })
            });
            
            console.log({
                folder_id: selectedFolderId,
                transcription: transcriptionText
            });
            
            if (response.ok) {
                const data = await response.json();
                alert("Transcrição salva com sucesso!");
                console.log(data.message);
            } else {
                const errorData = await response.json();
                alert(`Erro ao salvar transcrição: ${errorData.error || "Desconhecido"}`);
            }
        } catch (error) {
            console.error("Erro ao salvar transcrição:", error);
            alert("Erro ao salvar transcrição. Verifique o console para mais detalhes.");
        }
    } else {
        alert("Selecione uma pasta e/ou garanta que há uma transcrição para salvar.");
    }
};

// Evento de clique para iniciar a gravação
document.getElementById("start-recording").onclick = async () => {
    if (!recordingInProgress) {
        await startRecording();
        document.getElementById("start-recording").disabled = true;
    }
};

// Evento de clique para parar a gravação
document.getElementById("stop-recording").onclick = async () => {
    await stopRecording();
};

// Evento de clique para transcrever o áudio
document.getElementById("transcribe").onclick = async () => {
    document.getElementById("upload-status").innerText = "Enviando arquivo para transcrição, aguarde...";
    let uploadSuccess = false;
    let attempts = 0;
    const maxAttempts = 5;

    // Obter o ID da pasta selecionada
    const folderSelect = document.getElementById("folder-select");
    const selectedFolderId = folderSelect.value;

    while (!uploadSuccess && attempts < maxAttempts) {
        try {
            const response = await fetch('/transcription/transcribe/', { 
                method: 'POST', 
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ folder_id: selectedFolderId }) // Passar o ID da pasta aqui
            });

            if (response.ok) {
                const data = await response.json();
                document.getElementById("transcription-text").innerText = data.transcription || data.error;
                uploadSuccess = true;
                document.getElementById("upload-status").innerText = "";
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || "Falha no upload");
            }
        } catch (error) {
            attempts++;
            document.getElementById("upload-status").innerText = `Tentando novamente... (${attempts}/${maxAttempts})`;
            console.log("Erro ao transcrever:", error);
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
    }

    if (!uploadSuccess) {
        document.getElementById("upload-status").innerText = "Falha no upload após várias tentativas. Verifique a conexão.";
    }
};

// Função para carregar transcrições de uma pasta específica
async function loadTranscriptions(folderId) {
    try {
        document.getElementById("transcription-text").innerText = "Carregando transcrições...";

        const response = await fetch(`/transcription/folders/${folderId}/transcriptions/`);
        if (!response.ok) {
            // Verifique se o status é 404
            if (response.status === 404) {
                throw new Error("A pasta não contém transcrições ou não foi encontrada.");
            } else {
                throw new Error("Falha ao carregar transcrições.");
            }
        }

        const transcriptions = await response.json();
        console.log("Transcrições carregadas:", transcriptions);

        const transcriptionContainer = document.getElementById("transcription-text");
        transcriptionContainer.innerHTML = '';

        if (transcriptions.length > 0) {
            transcriptions.forEach(transcription => {
                const transcriptionItem = document.createElement("div");
                transcriptionItem.classList.add("transcription-item");
                transcriptionItem.textContent = transcription.text; // Supondo que 'text' é o campo que contém a transcrição
                transcriptionContainer.appendChild(transcriptionItem);
            });
        } else {
            transcriptionContainer.innerText = "Nenhuma transcrição encontrada.";
        }
    } catch (error) {
        console.error("Erro ao carregar transcrições:", error);
        document.getElementById("transcription-text").innerText = error.message; // Mensagem amigável
    }
}

// Carrega as pastas do usuário ao carregar a página
window.onload = async () => {
    await loadFolders();
};

async function loadFolders() {
    try {
        const response = await fetch('/transcription/folders/');
        if (response.ok) {
            const folders = await response.json();
            const folderList = document.getElementById("folder-list");
            const folderSelect = document.getElementById("folder-select");

            if (folderList && folderSelect) {
                folderList.innerHTML = ''; // Limpa a lista de pastas existentes
                folderSelect.innerHTML = ''; // Limpa as opções existentes

                folders.forEach(folder => {
                    // Adiciona pastas na barra lateral
                    const listItem = document.createElement("li");
                    listItem.textContent = folder.name;
                    listItem.onclick = () => loadTranscriptions(folder.id); // Chama a função para carregar as transcrições da pasta
                    folderList.appendChild(listItem);

                    // Adiciona pastas na lista suspensa de seleção
                    const option = document.createElement("option");
                    option.value = folder.id;
                    option.textContent = folder.name;
                    folderSelect.appendChild(option);
                });

                // Adiciona botão de salvar transcrição
                const saveButton = document.createElement("button");
                saveButton.textContent = "Salvar Transcrição";
                saveButton.onclick = async () => {
                    const selectedFolderId = folderSelect.value; // Obtém a pasta selecionada
                    const transcriptionText = document.getElementById("transcription-text").innerText;

                    if (selectedFolderId && transcriptionText) {
                        try {
                            const saveResponse = await fetch('/transcription/save-transcription/', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': csrftoken
                                },
                                body: JSON.stringify({ folder_id: selectedFolderId, text: transcriptionText })
                            });

                            if (saveResponse.ok) {
                                const data = await saveResponse.json();
                                alert("Transcrição salva com sucesso!");
                                console.log(data.message);
                            } else {
                                const errorData = await saveResponse.json();
                                alert(`Erro ao salvar transcrição: ${errorData.error || "Desconhecido"}`);
                            }
                        } catch (error) {
                            console.error("Erro ao salvar transcrição:", error);
                            alert("Erro ao salvar transcrição. Verifique o console para mais detalhes.");
                        }
                    } else {
                        alert("Selecione uma pasta e/ou garanta que há uma transcrição para salvar.");
                    }
                };

                folderList.appendChild(saveButton);
            } else {
                console.error("Elementos folderList ou folderSelect não encontrados.");
            }
        } else {
            const errorData = await response.json();
            console.error("Erro ao carregar as pastas:", errorData);
        }
    } catch (error) {
        console.error("Erro ao carregar as pastas:", error);
    }
}

// Função para salvar a transcrição em uma pasta selecionada
async function saveTranscription() {
    const folderSelect = document.getElementById("folder-select");
    const selectedFolderId = folderSelect.value;
    const transcriptionText = document.getElementById("transcription-text").innerText;

    if (selectedFolderId && transcriptionText) {
        try {
            const response = await fetch('/transcription/save-transcription/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ folder_id: selectedFolderId, text: transcriptionText })
            });

            if (response.ok) {
                alert("Transcrição salva com sucesso!");
            } else {
                const errorData = await response.json();
                alert(`Erro ao salvar transcrição: ${errorData.error || "Desconhecido"}`);
            }
        } catch (error) {
            console.error("Erro ao salvar transcrição:", error);
        }
    } else {
        alert("Selecione uma pasta válida e/ou garanta que há uma transcrição para salvar.");
    }
}

// Função para criar uma nova pasta
async function createFolder() {
    const folderName = prompt("Nome da nova pasta:");
    if (folderName) {
        try {
            const response = await fetch('/transcription/create-folder/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ name: folderName })
            });

            if (response.ok) {
                const data = await response.json();
                console.log(data.message);
                await loadFolders();  // Atualiza a lista de pastas
            } else {
                const errorData = await response.json();
                console.error("Erro ao criar pasta:", errorData);
                alert(`Erro ao criar pasta: ${errorData.error || "Desconhecido"}`);
            }
        } catch (error) {
            console.error("Erro ao criar pasta:", error);
            alert("Erro ao criar pasta. Verifique o console para mais detalhes.");
        }
    }
}
