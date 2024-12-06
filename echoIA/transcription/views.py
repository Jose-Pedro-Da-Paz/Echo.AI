import os
import wave
import pyaudio
from django.http import JsonResponse
from django.views import View
from pydub import AudioSegment
from groq import Groq
from django.shortcuts import render, get_object_or_404
import threading
import time
from .models import Transcription, Folder
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.models import User
from .models import Transcription
import logging

#configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level = logging.INFO)

# Inicializa o cliente da API GROQ
client_groq = Groq(api_key='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')

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
recording_event = threading.Event()
frames = []
audio = None
stream = None

class BaseAuthenticatedView(LoginRequiredMixin, View): 
    
    pass

@method_decorator(csrf_exempt, name='dispatch')
class RecordView(View):
    def post(self, request):
        global frames, audio, stream
        user = request.user
        print(f"RecordView chamada por {user.username}")

        # Verifica se a gravação já está em andamento
        if recording_event.is_set():
            return JsonResponse({"error": "Gravação já está em andamento."}, status=400)

        try:
            # Inicializa PyAudio e os parâmetros de gravação
            audio = pyaudio.PyAudio()
            stream = audio.open(format=FORMAT, 
                                channels=CHANNELS, 
                                rate=RATE, 
                                input=True, 
                                frames_per_buffer=CHUNK)
            frames = []  # Limpa os frames

            # Marca a gravação como ativa
            recording_event.set()

            # Thread para capturar o áudio continuamente
            def record_audio():
                print("Thread de gravação iniciada.")
                while recording_event.is_set():
                    try:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        frames.append(data)
                    except Exception as e:
                        print(f"Erro durante a gravação: {e}")
                        break

            # Inicia a thread de gravação
            threading.Thread(target=record_audio, daemon=True).start()

            print("Gravação iniciada.")
            return JsonResponse({"message": "Gravação iniciada com sucesso."})
        except Exception as e:
            print(f"Erro ao iniciar a gravação: {e}")
            return JsonResponse({"error": "Erro ao iniciar a gravação."}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class StopRecordingView(BaseAuthenticatedView):
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        global audio, stream
        logger.info(f"StopRecordingView chamada por {request.user.username}")

        # Verifica se há uma gravação em andamento
        if not recording_event.is_set():
            logger.warning("Tentativa de parar gravação sem gravação ativa.")
            return JsonResponse({"error": "Nenhuma gravação em andamento."}, status=400)

        try:
            # Interrompe o evento de gravação
            recording_event.clear()

            # Finaliza o fluxo e o recurso de áudio
            if stream:
                stream.stop_stream()
                stream.close()
                logger.debug("Stream de áudio fechado.")
            if audio:
                audio.terminate()
                logger.debug("Áudio encerrado.")

            # Salva o arquivo de áudio gravado
            with wave.open(OUTPUT_WAV, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                logger.info(f"Arquivo de áudio salvo em: {OUTPUT_WAV}")

            return JsonResponse({"message": "Gravação interrompida e salva com sucesso."})
        except Exception as e:
            # Log detalhado em caso de erro
            logger.error(f"Erro ao interromper gravação: {e}", exc_info=True)
            return JsonResponse({"error": "Erro ao parar a gravação."}, status=500)
        finally:
            # Limpeza de recursos e reseta os frames para a próxima gravação
            frames.clear()
            logger.debug("Frames de áudio resetados.")


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class TranscribeView(View):
    def post(self, request):
        # Verifica se o conteúdo é JSON
        if request.content_type != 'application/json':
            return JsonResponse({"error": "Content-Type must be application/json."}, status=400)

        # Parse dos dados da requisição
        data = json.loads(request.body)
        file_path = OUTPUT_WAV  # Caminho do arquivo de áudio

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return JsonResponse({"error": "Audio file not found."}, status=404)

        max_retries = 5
        attempt = 0
        success = False
        response_data = {}

        # Processo de transcrição
        while attempt < max_retries and not success:
            try:
                with open(file_path, "rb") as file:
                    transcription = client_groq.audio.transcriptions.create(
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
                    # Chama o Groq para formatar a transcrição
                    formatted_text = self.format_transcription_with_groq(transcription.text)

                    # Retorna a transcrição formatada ao cliente
                    response_data = {"transcription": formatted_text}
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

    def format_transcription_with_groq(self, transcription_text):
        """
        Envia a transcrição para o modelo Groq para formatação e enriquecimento.
        """
        prompt = (
            "Você é um sistema inteligente especializado em processar transcrições e anotações de aulas. "
            "Sua função principal é formatar o texto recebido de maneira clara, organizada e profissional, "
            "tornando-o fácil de ler e adequado para estudo ou consulta futura. "
            "Formate o seguinte texto:"
            f"\n\n{transcription_text}\n\n"
            "Adicione parágrafos, subtítulos e listas onde for apropriado. Se adicionar conteúdo, marque-o como '(Informação adicionada pela IA)'."
        )

        # Chamada à API do Groq para processar a transcrição
        completion = client_groq.chat.completions.create(
            model="llama3-groq-70b-8192-tool-use-preview",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=1024,
            top_p=0.65,
            stream=True,
            stop=None,
        )

        # Agrega o resultado do modelo
        formatted_text = ""
        for chunk in completion:
            formatted_text += chunk.choices[0].delta.content or ""

        return formatted_text

    
class SaveTranscriptionView(View):
    def post(self, request):
        # Verifica se o conteúdo é JSON
        if request.content_type != 'application/json':
            return JsonResponse({"error": "Content-Type must be application/json."}, status=400)

        data = json.loads(request.body)
        folder_id = data.get('folder_id')  # ID da pasta
        transcription_text = data.get('transcription')  # Texto da transcrição

        if not folder_id or not transcription_text:
            return JsonResponse({"error": "Folder ID and transcription text are required."}, status=400)

        try:
            # Salvar a transcrição no banco de dados
            Transcription.objects.create(
                user=request.user,
                text=transcription_text,
                folder_id=folder_id  # Associar à pasta selecionada
            )

            return JsonResponse({"message": "Transcription saved successfully."})
        except Exception as e:
            print(f"Erro ao salvar transcrição: {e}")
            return JsonResponse({"error": "Failed to save transcription."}, status=500)


class TranscriptionListView(View):
    def get(self, request, folder_id):
        transcriptions = Transcription.objects.filter(folder_id=folder_id)
        data = [{"id": t.id, "text": t.text} for t in transcriptions]
        return JsonResponse(data, safe=False)

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

@csrf_exempt
@login_required
def folder_list(request):
    user = request.user
    print(f"folder_list chamada por {user.username}")
    folders = Folder.objects.filter(user=user).values('id', 'name')
    return JsonResponse(list(folders), safe=False)

@csrf_exempt
@login_required
def create_folder(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            folder_name = data.get('name')
            user = request.user
            if not folder_name:
                print("Nome da pasta não fornecido.")
                return JsonResponse({"error": "Nome da pasta não fornecido."}, status=400)
            Folder.objects.create(name=folder_name, user=user)
            print(f"Pasta '{folder_name}' criada para o usuário {user.username}.")
            return JsonResponse({"message": "Folder created successfully."})
        except json.JSONDecodeError:
            print("Erro ao decodificar JSON.")
            return JsonResponse({"error": "Invalid JSON."}, status=400)
        except Exception as e:
            print(f"Erro ao criar pasta: {e}")
            return JsonResponse({"error": "Internal server error."}, status=500)
    print("Requisição inválida para create_folder.")
    return JsonResponse({"error": "Invalid request method."}, status=400)

@csrf_exempt
@login_required
def transcriptions_in_folder(request, folder_id):
    if request.method == "GET":
        try:
            folder = Folder.objects.get(id=folder_id, user=request.user)
            transcriptions = folder.transcriptions.all().values('id', 'text', 'created_at')
            print(f"Transcrições carregadas para a pasta '{folder.name}'.")
            return JsonResponse(list(transcriptions), safe=False)
        except Folder.DoesNotExist:
            print("Pasta não encontrada.")
            return JsonResponse({"error": "Folder not found."}, status=404)
    print("Requisição inválida para transcriptions_in_folder.")
    return JsonResponse({"error": "Invalid request method."}, status=400)

@login_required
def editor_view(request, folder_id):
    # Obtém a pasta selecionada
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    # Obtém todas as transcrições associadas à pasta
    transcriptions = Transcription.objects.filter(folder=folder).order_by('created_at')

    return render(request, 'transcription/editor.html', {
        'folder': folder,
        'transcriptions': transcriptions
    })

@csrf_exempt
@login_required
def save_updates_view(request):
    """
    View para salvar as atualizações feitas nas transcrições.
    Recebe uma lista de atualizações no formato JSON e as salva no banco de dados.
    """
    if request.method == 'POST':
        try:
            # Parse do corpo da requisição para JSON
            data = json.loads(request.body)
            updates = data.get('updates', [])

            if not updates:
                return JsonResponse({"error": "Nenhuma atualização enviada."}, status=400)

            # Itera sobre as atualizações e salva cada transcrição
            for update in updates:
                transcription_id = update.get('id')
                updated_text = update.get('text')

                if not transcription_id or updated_text is None:
                    return JsonResponse({"error": "ID ou texto da transcrição ausente."}, status=400)

                try:
                    # Atualiza a transcrição correspondente
                    transcription = Transcription.objects.get(id=transcription_id, user=request.user)
                    transcription.text = updated_text
                    transcription.save()
                except Transcription.DoesNotExist:
                    return JsonResponse({"error": f"Transcrição com ID {transcription_id} não encontrada."}, status=404)

            return JsonResponse({"message": "Transcrições salvas com sucesso."})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON inválido."}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"Erro inesperado: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Método não permitido."}, status=405)
    
from django.http import JsonResponse

@login_required
def get_concatenated_transcriptions(request, folder_id):
    """
    Retorna todas as transcrições da pasta concatenadas como uma única string.
    """
    try:
        folder = Folder.objects.get(id=folder_id, user=request.user)
        transcriptions = Transcription.objects.filter(folder=folder).order_by('created_at')
        concatenated_text = "\n\n".join([t.text for t in transcriptions])  # Junta as transcrições com espaços entre elas
        return JsonResponse({"text": concatenated_text})
    except Folder.DoesNotExist:
        return JsonResponse({"error": "Pasta não encontrada."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def save_concatenated_transcriptions(request):
    """
    Salva todas as transcrições de uma pasta como um texto único concatenado.
    Divide o texto em transcrições individuais e atualiza o banco de dados.
    """
    if request.method == 'POST':
        try:
            # Processa o corpo da requisição
            data = json.loads(request.body)
            folder_id = data.get('folder_id')  # ID da pasta onde as transcrições serão salvas
            concatenated_text = data.get('text')  # Texto completo concatenado do editor

            # Valida os dados recebidos
            if not folder_id or concatenated_text is None:
                return JsonResponse({"error": "Folder ID e texto concatenado são obrigatórios."}, status=400)

            # Obtém a pasta correspondente
            folder = Folder.objects.get(id=folder_id, user=request.user)

            # Divide o texto em transcrições individuais (separadas por duas linhas)
            transcription_texts = concatenated_text.split("\n\n")

            # Remove todas as transcrições existentes da pasta
            Transcription.objects.filter(folder=folder).delete()

            # Cria novas transcrições com base no texto concatenado
            for text in transcription_texts:
                Transcription.objects.create(
                    user=request.user,
                    folder=folder,
                    text=text.strip()  # Remove espaços desnecessários
                )

            return JsonResponse({"message": "Transcrições salvas com sucesso."})
        except Folder.DoesNotExist:
            return JsonResponse({"error": "Pasta não encontrada."}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"Erro ao salvar transcrições: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Método não permitido."}, status=405)
