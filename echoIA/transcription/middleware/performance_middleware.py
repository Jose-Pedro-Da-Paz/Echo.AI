import time
import psutil
import os

class PerformanceMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.process = psutil.Process(os.getpid())  # Identifica o processo do servidor Django

    def __call__(self, request):
        # Marca o início da medição
        start_time = time.time()

        # Processa a requisição e obtém a resposta
        response = self.get_response(request)

        # Marca o fim da medição
        end_time = time.time()

        # Obtém o uso de CPU e memória
        cpu_usage = self.process.cpu_percent(interval=0.1)
        memory_usage = self.process.memory_info().rss / (1024 ** 2)  # Em MB

        # Loga os resultados no console (ou pode ser enviado para logs)
        print(
            f"Requisição: {request.path}, "
            f"CPU: {cpu_usage}%, "
            f"Memória: {memory_usage:.2f} MB, "
            f"Tempo: {end_time - start_time:.4f}s"
        )

        return response

