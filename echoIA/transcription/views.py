import os
import wave
import pyaudio
from django.http import JsonResponse
from django.views import View
from pydub import AudioSegment
from groq import Groq
from django.shortcuts import render
import threading
import time
from .models import Transcription
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Inicializa o cliente da API GROQ
client = Groq(api_key='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')

# Caminho do diretório onde os arquivos temporários serão salvos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Parâmetros de gravação
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
OUTPUT_WAV = os.path.join(AUDIO_DIR, "audio.wav")  # Salvar em WAV

# Variável de controle para a gravação
is_recording = False
frames = []
audio = None
stream = None

class RecordView(View):
    def post(self, request):
        global is_recording, frames, audio, stream

        # Inicializa PyAudio e os parâmetros de gravação
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, 
                            channels=CHANNELS, 
                            rate=RATE, input=True, 
                            frames_per_buffer=CHUNK)
        frames = []  # Limpa os frames

        is_recording = True  # Inicia a gravação

        # Thread para capturar o áudio continuamente
        def record_audio():
            while is_recording:
                data = stream.read(CHUNK)
                frames.append(data)

        # Inicia a thread de gravação
        threading.Thread(target=record_audio).start()

        return JsonResponse({"message": "Recording started."})

class StopRecordingView(View):
    def post(self, request):
        global is_recording, audio, stream

        # Sinaliza o fim da gravação
        is_recording = False

        # Para e fecha o stream
        if stream is not None:
            stream.stop_stream()
            stream.close()
        if audio is not None:
            audio.terminate()

        # Salva os dados gravados em um arquivo WAV
        with wave.open(OUTPUT_WAV, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

        return JsonResponse({"message": "Recording stopped and saved."})

@method_decorator(login_required, name='dispatch')
class TranscribeView(View):
    def post(self, request):
        file_path = OUTPUT_WAV

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return JsonResponse({"error": "Audio file not found."}, status=404)

        max_retries = 5
        attempt = 0
        success = False
        response_data = {}

        while attempt < max_retries and not success:
            try:
                with open(file_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=file,
                        model="whisper-large-v3-turbo",
                        prompt="""Você é um sistema de transcrição de áudio em Português. 
                        Será focado principalmente para transcrever áudios 
                        de professores de Universidade. Esteja habituado a lidar com palavras
                        em Português e Inglês, principalmente.
                        Transcreva exatamente o que você escuta.""",
                        response_format="verbose_json",
                    )

                if hasattr(transcription, 'text'):
                    # Salvar transcrição no banco de dados
                    Transcription.objects.create(
                        user=request.user,
                        text=transcription.text
                    )
                    response_data = {"transcription": transcription.text}
                    success = True
                else:
                    response_data = {"error": "Transcription not available."}
                    break

            except Exception as e:
                attempt += 1
                response_data = {
                    "status": "Retrying upload due to network error",
                    "attempt": attempt
                }
                print(f"Upload failed on attempt {attempt}. Retrying in 2 seconds...")
                time.sleep(2)

        if not success:
            response_data = {"error": "Upload failed after multiple attempts."}

        return JsonResponse(response_data)

def index(request):
    # Consulta as transcrições do usuário
    if request.user.is_authenticated:
        user_transcriptions = Transcription.objects.filter(user=request.user).order_by('-created_at')
        latest_transcription = user_transcriptions.first() if user_transcriptions.exists() else None
    else:
        user_transcriptions = []
        latest_transcription = None  # Se o usuário não está autenticado, o histórico estará vazio
    
    # Renderiza a interface com o novo layout
    return render(request, 'transcription/index.html', {
        'user_transcriptions': user_transcriptions,
        'latest_transcription': latest_transcription,
        'upload_status': "Carregando..."  # Status inicial
    })
