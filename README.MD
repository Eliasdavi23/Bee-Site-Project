python main.py #Sobe direto captando o IP da rede local automaticamente (ex: http://192.168.0.11:8000)
python -m uvicorn main:app --host 192.168.0.11 --port 8000 --reload #Host fixo no IP atual da rede local
python -m uvicorn main:app --reload #Comando para testes locais (127.0.0.1)
