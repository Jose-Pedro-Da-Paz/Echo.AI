import os
import wave
import pyaudio
from django.http import JsonResponse
from django.views import View
from pydub import AudioSegment
from groq import Groq
from django.shortcuts import render

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

class RecordView(View):
    def post(self, request):
        # Inicializa PyAudio
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        # Salva os frames em uma lista durante a gravação
        frames = []

        # Grava por um tempo fixo, por exemplo, 5 segundos
        for _ in range(0, int(RATE / CHUNK * 5)):
            data = stream.read(CHUNK)
            frames.append(data)

        # Para o stream e fecha
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # Salva os dados gravados em um arquivo WAV
        with wave.open(OUTPUT_WAV, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

        return JsonResponse({"message": "Recording completed."})

class StopRecordingView(View):
    def post(self, request):
        # Como não há stream na sessão, não precisamos fazer nada aqui.
        return JsonResponse({"message": "No active recording to stop."})

class TranscribeView(View):
    def post(self, request):
        file_path = OUTPUT_WAV  # Use o arquivo WAV para a transcrição

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return JsonResponse({"error": "Audio file not found."}, status=404)

        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=file,
                model="whisper-large-v3",
                prompt="Você é um sistema de transcrição de áudio em Português. Será focado principalmente para transcrever áudios de professores de Universidade.",
                response_format="verbose_json",
            )

        if hasattr(transcription, 'text'):
            return JsonResponse({"transcription": transcription.text})
        else:
            return JsonResponse({"error": "Transcription not available."}, status=500)

def index(request):
    return render(request, 'transcription/index.html')

