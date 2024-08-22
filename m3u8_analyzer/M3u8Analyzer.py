import re
import shutil
import site
import time
import uuid
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import subprocess
import os
import sys
import requests

__author__ = 'PauloCesar0073-dev404'
__version__ = '1.0.0.0'
__ossystem = os.name

ffmpeg_bin = os.path.join(site.getsitepackages()[0], 'Lib', 'site-packages', 'm3u8_analyzer', 'bin')


class M3u8Analyzer:
    def __init__(self):
        """
        Classe para análise e manipulação de streams M3U8.
        Fornece métodos para obter o conteúdo de URLs M3U8, identificar o tipo de conteúdo,
        extrair informações de playlists, e suporte a decriptografia AES128 de segmentos.
        """
        pass

    @staticmethod
    def get_m3u8(url_m3u8: str, headers: dict = None, save_in_file=None):
        """
        Obtém o conteúdo de um arquivo M3U8 a partir de uma URL HLS.

        :param url_m3u8: A URL do arquivo M3U8.
        :param headers: Cabeçalhos HTTP opcionais para a requisição.
        :param save_in_file: Se fornecido, salva a playlist em um arquivo .m3u8.
        :return: O conteúdo do arquivo M3U8 como uma string, ou None se a requisição falhar.
        :raises ValueError: Se a URL não for válida ou se os headers não forem um dicionário.
        """
        if headers:
            if not isinstance(headers, dict):
                raise ValueError("headers deve ser um dicionário válido!")
        if not (url_m3u8.startswith('https://') or url_m3u8.startswith('http://')):
            raise ValueError("A URL é inválida!")
        if not (url_m3u8.endswith(".m3u8") or url_m3u8.endswith(".m3u8?")):
            if not headers:
                raise ValueError("Esta URL requer autenticação! Passe os headers autenticados no parâmetro headers")
        try:
            r = requests.get(url_m3u8, timeout=20, headers=headers, stream=True)
            if r.status_code == 200:
                if save_in_file:
                    local = os.getcwd()
                    aleator_code = uuid.uuid4()
                    with open(fr"{local}\{save_in_file}.m3u8", 'a', encoding='utf-8') as e:
                        e.write(r.text)
                return r.text
            else:
                return None
        except ConnectionError:
            raise ConnectionError("Erro de conexão: Não foi possível se conectar ao servidor.")
        except TimeoutError:
            raise TimeoutError("Erro de tempo esgotado: A conexão com o servidor demorou muito para responder.")
        except requests.exceptions.HTTPError as http_err:
            raise ValueError(f"Erro HTTP: O servidor retornou um erro HTTP {http_err.response.status_code}.")
        except requests.exceptions.RequestException as req_err:
            raise ValueError(f"Erro de requisição: {req_err}")
        except Exception as e:
            raise ValueError(f"Erro inesperado: {e}")

    @staticmethod
    def get_high_resolution(m3u8_content: str):
        """
        Obtém a maior resolução disponível em um arquivo M3U8 e o URL correspondente.

        :param m3u8_content: O conteúdo do arquivo M3U8.
        :return: Uma tupla contendo a maior resolução e o URL correspondente.
        """
        resolutions = re.findall(r'RESOLUTION=(\d+x\d+)', m3u8_content)
        max_resolution = max(resolutions, key=lambda res: int(res.split('x')[0]) * int(res.split('x')[1]))
        url = re.search(rf'#EXT-X-STREAM-INF:[^\n]*RESOLUTION={max_resolution}[^\n]*\n([^\n]+)', m3u8_content).group(1)
        if not url:
            return max_resolution, None
        if not max_resolution:
            return None, url
        else:
            return max_resolution, url

    @staticmethod
    def get_type_m3u8_content(m3u8_content: str) -> str:
        """
        Determina o tipo de conteúdo de um arquivo M3U8 (Master ou Segmentos).

        :param m3u8_content: URL ou conteúdo do arquivo M3U8.
        :return: O tipo de conteúdo ('Master', 'Master encrypted', 'Segments', 'Segments encrypted', 'Segments Master' ou 'Desconhecido').
        """
        try:
            conteudo = m3u8_content
            if '#EXT-X-STREAM-INF' in conteudo:
                if '#EXT-X-KEY' in conteudo:
                    return 'Master encrypted'
                else:
                    return 'Master'
            elif '#EXTINF' in conteudo:
                if '#EXT-X-KEY' in conteudo:
                    return 'Segments encrypted'
                else:
                    # Verifica se URLs dos segmentos possuem a extensão .ts ,.m4s
                    segment_urls = re.findall(r'#EXTINF:[0-9.]+,\n([^\n]+)', conteudo)
                    if all(url.endswith('.ts') for url in segment_urls):
                        return 'Segments .ts'
                    elif all(url.endswith('.m4s') for url in segment_urls):
                        return 'Segments .m4s'
                    else:
                        return 'Segments Master'
            else:
                return 'Desconhecido'
        except Exception as e:
            return f'Erro ao processar o conteúdo: {e}'

    @staticmethod
    def get_player_playlist(m3u8_url: str) -> str:
        """
        Obtém o caminho do diretório base do arquivo M3U8, excluindo o nome do arquivo.

        :param m3u8_url: URL completa do arquivo M3U8.
        :return: Caminho do diretório onde o arquivo M3U8 está localizado.
        """
        if m3u8_url.endswith('/'):
            m3u8_url = m3u8_url[:-1]
        partes = m3u8_url.split('/')
        for i, parte in enumerate(partes):
            if '.m3u8' in parte:
                return '/'.join(partes[:i]) + "/"
        return ''

    @staticmethod
    def get_audio_playlist(m3u8_content: str):
        """
        Extrai o URL da playlist de áudio de um conteúdo M3U8.

        :param m3u8_content: Conteúdo da playlist M3U8 como string.
        :return: URL da playlist de áudio ou None se não encontrado.
        """
        match = re.search(r'#EXT-X-MEDIA:.*URI="([^"]+)"(?:.*,IV=(0x[0-9A-Fa-f]+))?', m3u8_content)
        if match:
            return match.group(1)
        return None

    @classmethod
    class EncryptSuport:
        """
        Classe interna para suporte a operações de criptografia relacionadas a M3U8.
        Fornece métodos para obter a URL da chave de criptografia e o IV associado.
        """

        @staticmethod
        def get_url_key_m3u8(m3u8_content: str, player: str, headers=None):
            """
            Extrai a URL da chave de criptografia AES-128 e o IV de um conteúdo M3U8.

            :param m3u8_content: String contendo o conteúdo do arquivo M3U8.
            :param player: URL base para formar o URL completo da chave, se necessário.
            :param headers: Cabeçalhos HTTP opcionais para a requisição da chave.
            :return: Um dicionário contendo a chave em hexadecimal e o IV (se disponível).
            """
            pattern = r'#EXT-X-KEY:.*URI="([^"]+)"(?:.*,IV=(0x[0-9A-Fa-f]+))?'
            match = re.search(pattern, m3u8_content)
            data = {}
            if match:
                url_key = f"{player}{match.group(1)}"
                iv_hex = match.group(2)
                headers_get_keys = headers or {}
                resp = requests.get(url_key, headers=headers_get_keys)
                resp.raise_for_status()
                key_bytes = resp.content
                key_hex = key_bytes.hex()
                data['key'] = key_hex
                data['iv'] = iv_hex
                return data
            else:
                return None

    @classmethod
    class M3u8AnalyzerDownloader:
        @staticmethod
        def downloader_and_remuxer_segments(url_playlist: str, output: str, key_hex: str = None,
                                            iv_hex: str = None,
                                            player: str = None, headers: dict = None, segmentsType: str = None):
            """
            Baixa os segmentos de uma playlist M3U8 e os combina em um arquivo de vídeo.

            :param url_playlist: URL da playlist de segmentos.
            :param output: Caminho de saída para o vídeo final (dir/nome.mp4).
            :param key_hex: Chave de descriptografia em formato hexadecimal (opcional).
            :param iv_hex: IV (vetor de inicialização) em formato hexadecimal (opcional).
            :param player: URL base para os segmentos, se necessário.
            :param headers: Cabeçalhos HTTP adicionais para as requisições.
            :return: None
            """
            if not (url_playlist.startswith('http://') or url_playlist.startswith('https://')):
                raise ValueError("A URL é inválida!")
            resposta = requests.get(url_playlist, headers=headers)
            resposta.raise_for_status()
            playlist = resposta.text
            urls_segmentos = [linha for linha in playlist.splitlines() if linha and not linha.startswith('#')]

            temp_dir = 'TEMPs'
            os.makedirs(temp_dir, exist_ok=True)
            arquivos_temporarios = []
            extens = '.ts'
            try:
                for i, url_segmento in enumerate(urls_segmentos):

                    if segmentsType:
                        if '.m4s' in segmentsType:
                            extens = '.m4s'
                    arquivo_temporario = fr'{temp_dir}\seg_{i}{extens}'
                    arquivos_temporarios.append(arquivo_temporario)
                    if not url_segmento.startswith("https://"):
                        if player:
                            url_segmento = f"{player}{url_segmento}"
                        else:
                            raise ValueError("Não há URL base para os segmentos.")
                    sys.stdout.write(f"\rBaixando Segmentos [{i + 1}/{len(urls_segmentos)}]")
                    sys.stdout.flush()
                    if key_hex and iv_hex:
                        key = bytes.fromhex(key_hex)
                        iv = bytes.fromhex(iv_hex)
                        M3u8Analyzer.M3u8AnalyzerDownloader.__baixar_segmento(url_segmento, arquivo_temporario, key, iv,
                                                                              headers)
                    else:
                        M3u8Analyzer.M3u8AnalyzerDownloader.__baixar_segmento(url_segmento, arquivo_temporario,
                                                                              headers=headers)

                # Concatena os segmentos em um arquivo de vídeo final
                M3u8Analyzer.M3u8AnalyzerDownloader.__ffmpeg_concatener(output=output, extension=extens)

            except OSError as e:
                raise ValueError(f"O vídeo parece não ser válido: {e}")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"\nErro de conexão: {e}")
            finally:
                # Remover arquivos temporários
                for arquivo in arquivos_temporarios:
                    if os.path.isfile(arquivo):
                        try:
                            os.remove(arquivo)
                        except OSError as e:
                            print(f"Erro ao remover o arquivo {arquivo}: {e}")
                # Remover diretório temporário
                if os.path.isdir(temp_dir):
                    try:
                        os.rmdir(temp_dir)
                    except OSError as e:
                        print(f"Erro ao remover o diretório {temp_dir}: {e}")

        @staticmethod
        def __baixar_segmento(url_segmento: str, path: str, key: bytes = None, iv: bytes = None,
                              headers: dict = None):
            """
            Baixa um segmento de vídeo e, se necessário, o descriptografa.

            :param url_segmento: URL do segmento.
            :param path: Caminho de saída para salvar o segmento.
            :param key: Chave de descriptografia em bytes (opcional).
            :param iv: IV (vetor de inicialização) em bytes (opcional).
            :param headers: Cabeçalhos HTTP adicionais para a requisição (opcional).
            :return: None
            """
            resposta = requests.get(url_segmento, headers=headers, stream=True)
            resposta.raise_for_status()
            total_bytes = 0
            chunk_size = 1024  # Definir o tamanho do chunk (1 KB)
            with open(path, 'wb') as arquivo_segmento:
                for chunk in resposta.iter_content(chunk_size=chunk_size):
                    if chunk:
                        arquivo_segmento.write(chunk)
                        total_bytes += len(chunk)

            # Descriptografar se necessário
            if key and iv:
                with open(path, 'rb') as arquivo_segmento:
                    segmento_bytes = arquivo_segmento.read()
                backend = default_backend()
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
                decryptor = cipher.decryptor()
                unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
                decrypted_segment = decryptor.update(segmento_bytes) + decryptor.finalize()
                segment = unpadder.update(decrypted_segment) + unpadder.finalize()

                with open(path, 'wb') as arquivo_segmento:
                    arquivo_segmento.write(segment)
            # Adicionar uma nova linha após o fim do download
            sys.stdout.write("\r")

        @staticmethod
        def __clear_line():
            """
            Limpa a linha atual no terminal usando códigos de escape ANSI.
            :return: None
            """
            sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
            sys.stdout.flush()

        @staticmethod
        def __filter_ffmpeg_output(line, index):
            """
            Filtra e imprime apenas as linhas que contêm a palavra 'Opening' na saída do ffmpeg.
            :param line: Linha de saída do ffmpeg.
            :param index: Índice de progresso.
            :return: None
            """
            lines = line.decode('utf-8').strip()
            # Verifica se a linha contém a palavra 'Opening'
            if re.search(r'Opening', lines):
                M3u8Analyzer.M3u8AnalyzerDownloader.__clear_line()  # Limpa a linha anterior
                sys.stdout.write(f'Obtendo segmentos [{index}]')
                sys.stdout.flush()
                time.sleep(0.2)
                return True  # Indica que o índice deve ser incrementado

            return False  # Indica que o índice não deve ser incrementado

        @staticmethod
        def __ffmpeg_concatener(output: str, extension: str):
            """
            Concatena os segmentos de vídeo em um arquivo de vídeo usando FFmpeg.
            :param output: Caminho de saída para o vídeo final (dir/nome.mp4).
            :return: None
            """
            # Defina o nome do arquivo de lista
            arquivo_lista = 'lista.txt'

            def extrair_numero(nome_arquivo):
                match = re.search(r'(\d+)', nome_arquivo)
                return int(match.group(1)) if match else float('inf')

            # Defina o diretório onde estão os arquivos .ts
            diretorio_ts = 'TEMPs'
            # Abre o arquivo lista.txt para escrita
            with open(arquivo_lista, 'w') as f:
                # Lista todos os arquivos no diretório e filtra apenas os arquivos .ts
                arquivos_ts = [arquivo for arquivo in os.listdir(diretorio_ts) if arquivo.endswith(f'{extension}')]
                # Ordena os arquivos com base no número extraído
                arquivos_ts.sort(key=extrair_numero)
                # Escreve cada arquivo no lista.txt
                for arquivo in arquivos_ts:
                    caminho_absoluto = os.path.join(diretorio_ts, arquivo)
                    f.write(f"file '{caminho_absoluto}'\n")
            ffmpeg_exe = 'ffmpeg' if os.name == 'posix' else 'ffmpeg.exe'
            cmd = [
                fr'{ffmpeg_bin}',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', arquivo_lista,
                '-c', 'copy',
                f'{output}'
            ]
            # Executa o comando ffmpeg
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            index = 0
            while True:
                output = process.stdout.readline()
                # print(output.decode('utf-8').strip())
                if process.poll() is not None and output == b'':
                    break
                if output:
                    if M3u8Analyzer.M3u8AnalyzerDownloader.__filter_ffmpeg_output(output, index):
                        index += 1  # Incrementa o índice apenas se a linha corresponder ao filtro
            M3u8Analyzer.M3u8AnalyzerDownloader.__clear_line()

            sys.stdout.write('\nProcesso finalizado!\n')
            sys.stdout.flush()

        @staticmethod
        def ffmpeg(input_url: str, output: str, type_playlist: str, resolution: str = None):
            """
            Baixa um vídeo usando FFmpeg.
            :param type_playlist: tipo da playlist 'audio' ,'video'
            :param input_url: URL da playlist m3u8.
            :param resolution: Define qual resolução você deseja baixar: 'medium', 'lower', 'high'.
            :param output: Caminho de saída para o vídeo final (dir/nome.mp4).
            :return: None
            """

            i = 0

            ffmpeg_exe = 'ffmpeg' if os.name == 'posix' else 'ffmpeg.exe'
            resolution_map = {}
            # Mapeando as opções de resolução para filtros de FFmpeg
            if not isinstance(type_playlist, str):
                raise SyntaxError(f"o parâmetro 'type_playlist' é necessário!")
            if not 'videos' or not 'audio' in type_playlist:
                raise ValueError(" e necessário especificar qual tipo de playlis, 'audio','video'")
            if type_playlist == 'video':
                resolution_map = {
                    'lower': 'v:0',
                    'medium': 'v:1',
                    'high': 'v:2'
                }
            if type_playlist == 'audio':
                resolution_map = {
                    'lower': 'a:0',
                    'medium': 'a:1',
                    'high': 'a:2'
                }
            # Seleciona a opção correta de mapeamento de vídeo
            if resolution:
                video_map = resolution_map.get(resolution,
                                               'v:2')  # 'high' é o padrão se a resolução não for reconhecida
                cmd = [
                    fr'{ffmpeg_bin}',
                    '-y',
                    '-i', input_url,
                    '-map', video_map,
                    '-c', 'copy',
                    f'{output}'
                ]
            else:
                cmd = [
                    fr'{ffmpeg_bin}',
                    '-y',
                    '-i', input_url,
                    '-c', 'copy',
                    f'{output}'
                ]

            # Executa o comando ffmpeg
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            index = 0
            while True:
                output = process.stdout.readline()
                # print(output.decode('utf-8').strip())
                if process.poll() is not None and output == b'':
                    break
                if output:
                    if M3u8Analyzer.M3u8AnalyzerDownloader.__filter_ffmpeg_output(output, index):
                        index += 1  # Incrementa o índice apenas se a linha corresponder ao filtro
            M3u8Analyzer.M3u8AnalyzerDownloader.__clear_line()

            sys.stdout.write('\nProcesso finalizado!\n')
            sys.stdout.flush()

        @staticmethod
        def remuxer_audio_and_video(audioPath: str, videoPath: str, outputPath: str):
            """
            Remuxer áudio e vídeo com FFmpeg.
            :param audioPath: Caminho para o arquivo de áudio.
            :param videoPath: Caminho para o arquivo de vídeo.
            :param outputPath: Caminho de saída para o arquivo remuxado (dir/nome.mp4).
            :return: None
            """
            if not os.path.exists(audioPath) or not os.path.exists(videoPath):
                raise ValueError("os paths não estão sendo possível de encontrar...")
            cmd = [
                ffmpeg_bin,
                '-y',  # Sobrescrever o arquivo de saída se já existir
                '-i', audioPath,  # Caminho do arquivo de áudio
                '-i', videoPath,  # Caminho do arquivo de vídeo
                '-c', 'copy',  # Copia os streams de áudio e vídeo sem recodificação
                '-map', '0:a',  # Mapeia o áudio da primeira entrada (0) - arquivo de áudio
                '-map', '1:v',  # Mapeia o vídeo da segunda entrada (1) - arquivo de vídeo
                outputPath
            ]

            # Executa o comando ffmpeg
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # Envia a saída em tempo real para o cliente
            for line in iter(process.stdout.readline, b''):
                try:
                    # Tente decodificar os bytes como UTF-8
                    decoded_line = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    # Em caso de erro de decodificação, você pode ignorar a linha ou tratar de outra forma
                    continue
                print(decoded_line)
                try:
                    os.remove(audioPath)
                    os.remove(videoPath)
                except Exception:
                    pass
            print('Remuxing concluído!')
