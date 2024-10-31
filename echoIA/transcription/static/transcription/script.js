const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
let recordingInProgress = false;

async function startRecording() {
    await fetch('/transcription/start-recording/', { 
        method: 'POST', 
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    });
    recordingInProgress = true;
    document.getElementById("stop-recording").disabled = false;
    console.log("Gravação iniciada.");
}

async function stopRecording() {
    if (!recordingInProgress) return;

    await fetch('/transcription/stop-recording/', { 
        method: 'POST', 
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    });
    recordingInProgress = false;
    document.getElementById("transcribe").disabled = false;
    console.log("Gravação parada.");
}

document.getElementById("start-recording").onclick = async () => {
    if (!recordingInProgress) {
        await startRecording();
        document.getElementById("start-recording").disabled = true;
    }
};

document.getElementById("stop-recording").onclick = async () => {
    await stopRecording();
    document.getElementById("stop-recording").disabled = true;
    document.getElementById("start-recording").disabled = false;
};

document.getElementById("transcribe").onclick = async () => {
    document.getElementById("upload-status").innerText = "Enviando arquivo para transcrição, aguarde...";

    let uploadSuccess = false;
    let attempts = 0;
    const maxAttempts = 5;

    while (!uploadSuccess && attempts < maxAttempts) {
        try {
            const response = await fetch('/transcription/transcribe/', { 
                method: 'POST', 
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                }
            });

            if (response.ok) {
                const data = await response.json();
                document.getElementById("transcription-text").innerText = data.transcription || data.error;
                uploadSuccess = true;
                document.getElementById("upload-status").innerText = "";
            } else {
                throw new Error("Falha no upload");
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
