import os
import wave
import pyaudio
from django.http import JsonResponse
from django.views import View
from pydub import AudioSegment
from groq import Groq

# Inicializa o cliente da API GROQ
client = Groq(api_key='your_api_key_here')

# Caminho do diretório onde os arquivos temporários serão salvos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Parâmetros de gravação
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
OUTPUT_OGG = os.path.join(AUDIO_DIR, "audio.ogg")

class RecordView(View):
    def post(self, request):
        self.frames, self.audio, self.stream = self.start_recording()
        return JsonResponse({"message": "Recording started."})

    def start_recording(self):
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = []
        return frames, audio, stream

class StopRecordingView(View):
    def post(self, request):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        # Salva o áudio em um arquivo OGG
        with wave.open(os.path.join(AUDIO_DIR, "audio.wav"), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(self.frames))

        # Converte para OGG
        audio = AudioSegment.from_wav(os.path.join(AUDIO_DIR, "audio.wav"))
        audio.export(OUTPUT_OGG, format="ogg")

        return JsonResponse({"message": "Recording stopped.", "file_path": OUTPUT_OGG})

class TranscribeView(View):
    def post(self, request):
        file_path = OUTPUT_OGG

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
