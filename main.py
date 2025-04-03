import requests
import time
import re
import random

# Configurações do qBittorrent
QB_URL = "http://127.0.0.1:8080"
QB_USERNAME = "admin"
QB_PASSWORD = "2atgv4pn"

FILMES_ALEATORIOS = [
    "Deadpool e Wolverine",
    "Oppenheimer",
    "Duna 2",
    "John Wick 4",
    "Avatar 2",
    "Batman: O Cavaleiro das Trevas",
    "Interestelar",
    "Matrix",
    "Coringa",
    "Vingadores: Ultimato"
]

# Variável para armazenar o nome do torrent baixado
torrent_baixado = None

def login_qbittorrent():
    """Faz login na API do qBittorrent e retorna a sessão autenticada"""
    session = requests.Session()
    data = {"username": QB_USERNAME, "password": QB_PASSWORD}
    
    res = session.post(f"{QB_URL}/api/v2/auth/login", data=data)
    if res.text != "Ok.":
        print(f"❌ Erro ao conectar ao qBittorrent! Resposta: {res.text}")
        return None

    print("✅ Conectado ao qBittorrent!")
    return session

def verificar_qualidade(file_name, qualidade):
    """Verifica se o nome do torrent contém a qualidade desejada"""
    if not qualidade:
        return True  # Se não especificou qualidade, qualquer uma serve
    qualidade_regex = re.compile(re.escape(qualidade), re.IGNORECASE)
    return bool(qualidade_regex.search(file_name))

def verificar_tipo_audio(file_name, tipo_audio):
    """Verifica se o nome do torrent contém o tipo de áudio desejado"""
    if not tipo_audio:
        return True  # Se não especificou tipo de áudio, qualquer um serve
    tipo_audio_regex = re.compile(re.escape(tipo_audio), re.IGNORECASE)
    return bool(tipo_audio_regex.search(file_name))

def verificar_ano(file_name, ano):
    """Verifica se o nome do torrent contém o ano desejado"""
    if not ano:
        return True  # Se não especificou ano, qualquer um serve
    ano_regex = re.compile(rf"\b{ano}\b")
    return bool(ano_regex.search(file_name))

def buscar_filme(session, filme, qualidade, tipo_audio, ano):
    """Busca um filme no qBittorrent e retorna uma lista de torrents"""
    print(f"🔍 Buscando: {filme}...")
    time.sleep(5)

    data = {"pattern": filme, "plugins": "all", "category": "movies"}

    try:
        res = session.post(f"{QB_URL}/api/v2/search/start", data=data)
        if res.status_code != 200:
            print(f"❌ Erro ao iniciar busca! Resposta: {res.text}")
            return None

        search_id = res.json().get("id")
        if not search_id:
            print("❌ Erro: Não foi possível recuperar o ID da busca.")
            return None

        print(f"🔧 ID da busca: {search_id}")
        time.sleep(10)

        res = session.get(f"{QB_URL}/api/v2/search/results?id={search_id}")
        results = res.json().get("results", [])

        if not results:
            print(f"❌ Nenhum torrent encontrado para: {filme}")
            return None

        print(f"🔍 {len(results)} torrents encontrados!")

        # Filtrar torrents por qualidade, tipo de áudio e ano
        filtered_results = [
            torrent for torrent in results
            if verificar_qualidade(torrent.get('fileName', ''), qualidade) and
               verificar_tipo_audio(torrent.get('fileName', ''), tipo_audio) and
               verificar_ano(torrent.get('fileName', ''), ano)
        ]

        if not filtered_results:
            print("❌ Nenhum torrent corresponde aos critérios.")
            return None

        return filtered_results

    except Exception as e:
        print(f"❌ Erro ao processar a resposta: {e}")
        return None

def adicionar_torrent(session, magnet_link):
    """Adiciona o torrent ao qBittorrent e retorna o hash"""
    try:
        add_data = {"urls": magnet_link}
        res = session.post(f"{QB_URL}/api/v2/torrents/add", data=add_data)

        if res.status_code == 200:
            print("✅ Torrent adicionado com sucesso!")
            time.sleep(3)
            return obter_ultimo_torrent(session)
        else:
            print(f"❌ Erro ao adicionar o torrent. Código: {res.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Erro ao adicionar o torrent: {e}")
        return None

def obter_ultimo_torrent(session):
    """Obtém o último torrent adicionado e retorna seu hash"""
    res = session.get(f"{QB_URL}/api/v2/torrents/info")
    if res.status_code == 200:
        torrents = res.json()
        if torrents:
            return torrents[-1]  # Retorna o último torrent, com todos os dados (incluindo o nome)
    return None

def verificar_status_torrent(session, torrent_hash):
    """Verifica o status do torrent e mostra progresso"""
    while True:
        res = session.get(f"{QB_URL}/api/v2/torrents/properties?hash={torrent_hash}")
        
        if res.status_code == 200:
            try:
                data = res.json()
                if "progress" in data and "state" in data:
                    progress = round(data["progress"] * 100, 2)
                    state = data["state"]
                    print(f"📥 Download: {progress}% - Estado: {state}")

                    if state == "downloading":
                        time.sleep(5)
                        continue
                    elif state in ["pausedDL", "stalledDL"]:
                        return False  
                    elif state == "error":
                        return False  
                    elif state == "uploading" or progress == 100:
                        print("✅ Download concluído!")
                        return True
                else:
                    print(f"⚠️ Resposta inesperada da API: {data}")
                    return False  # Retorna falso se os dados forem inválidos
            except Exception as e:
                print(f"❌ Erro ao processar os dados do torrent: {e}")
                return False

        print(f"❌ Erro ao consultar status do torrent. Código: {res.status_code}")
        return False

def processar_torrents(session, torrents, filme):
    """Baixa o primeiro torrent disponível e para imediatamente após encontrar um válido"""
    if not torrents:
        print("❌ Nenhum torrent disponível para download.")
        return

    for torrent in torrents:
        magnet_link = torrent.get("fileUrl")
        nome_torrent = torrent.get("fileName")
        if not magnet_link:
            print(f"⚠️ Magnet link inválido para o torrent: {nome_torrent}, tentando próximo...")
            continue

        torrent_hash = adicionar_torrent(session, magnet_link)
        if torrent_hash:
            print(f"✅ Torrent {nome_torrent} adicionado com sucesso! Aguardando progresso...")
            if verificar_status_torrent(session, torrent_hash):
                print(f"✅ Torrent {nome_torrent} está baixando. Nenhum outro será adicionado.")
                global torrent_baixado
                torrent_baixado = nome_torrent  # Armazena o nome do torrent que foi baixado com sucesso
                return  # Para imediatamente após encontrar um válido
            else:
                print(f"✅ Torrent {nome_torrent} Baixando!!\n")
                return  # Se travar, para sem tentar outros

    print("❌ Nenhum torrent válido encontrado.")

def main():
    """Gerencia o login, busca e download dos torrents"""
    session = login_qbittorrent()
    if not session:
        return

    filme = random.choice(FILMES_ALEATORIOS)
    print(f"🎬 Filme selecionado: {filme}")
    qualidade = "1080p"
    print(f"🎥 Qualidade: {qualidade}")
    tipo_audio = input("🎤 Tipo de áudio (dublado, legendado, dual audio) ou deixe em branco para qualquer: ").strip()
    ano = input("📅 Digite o ano do filme (opcional) ou pressione Enter para qualquer: ").strip()

    torrents = buscar_filme(session, filme, qualidade, tipo_audio, ano)

    if torrents:
        processar_torrents(session, torrents, filme)

if __name__ == "__main__":
    main()
