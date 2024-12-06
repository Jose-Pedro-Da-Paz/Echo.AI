document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('infinite-editor');
    const saveButton = document.getElementById('save-button');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    if (!csrfToken) {
        console.error("CSRF token não encontrado.");
        alert("Erro ao carregar a página. Tente novamente.");
        return;
    }

    // Função para carregar as transcrições concatenadas
    async function loadTranscriptions(folderId) {
        try {
            const response = await fetch(`/transcription/editor/${folderId}/concatenated/`);
            if (response.ok) {
                const data = await response.json();
                editor.value = data.text; // Preenche o editor com o texto concatenado
            } else {
                throw new Error("Falha ao carregar as transcrições.");
            }
        } catch (error) {
            console.error("Erro ao carregar as transcrições:", error);
            alert("Erro ao carregar as transcrições.");
        }
    }

    // Função para salvar o conteúdo editado
    saveButton.addEventListener('click', async () => {
        try {
            const folderId = window.location.pathname.split("/").slice(-2, -1)[0]; // Obtém o folder_id da URL
            const response = await fetch('/transcription/save-concatenated/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    folder_id: folderId,
                    text: editor.value
                })
            });

            if (response.ok) {
                alert('Transcrições salvas com sucesso!');
            } else {
                const errorData = await response.json();
                alert(`Erro ao salvar: ${errorData.error || "Desconhecido"}`);
            }
        } catch (error) {
            console.error('Erro ao salvar:', error);
            alert('Erro ao salvar as transcrições.');
        }
    });

    // Carrega as transcrições ao iniciar a página
    const folderId = window.location.pathname.split("/").slice(-2, -1)[0];
    loadTranscriptions(folderId);
});
