import platform
import re
import time
import requests
import zipfile
import shutil
import os
import sys
from http.client import IncompleteRead

from colorama import Fore, Style

v = '1.0.3.2'


class Configurate:
    def __init__(self):
        self.config_file_path = os.path.join(sys.prefix,
                                             '.m3u8_analyzer_config') if self.is_virtualenv() else '.m3u8_analyzer_config'
        self.BIN_DIR = 'ffmpeg-binaries'
        self.config = self.load_config(self.config_file_path)
        self.OS_SYSTEM = self.config.get('OS_SYSTEM', os.name)
        self.VERSION = self.config.get('VERSION', v)
        self.FFMPEG_URL = self.config.get('FFMPEG_URL')
        self.FFMPEG_BINARY = self.config.get('FFMPEG_BINARY')
        self.INSTALL_DIR = self.config.get('INSTALL_DIR')
        self.STATUS = self.config.get('STATUS')
        self.VENV_PATH = self.config.get('VENV_PATH', os.path.dirname(self.config_file_path))

        if not self.INSTALL_DIR:
            self.INSTALL_DIR = os.path.join(sys.prefix, self.BIN_DIR) if self.is_virtualenv() else os.path.join(
                os.getcwd(), self.BIN_DIR)
            self.config['INSTALL_DIR'] = self.INSTALL_DIR
            self.save_config(self.config_file_path, self.config)

        if not os.path.exists(self.config_file_path):
            self.configure()
        self.create_file()

    def loader(self):
        """Carrega a configuração do arquivo e retorna um dicionário."""
        return self.load_config(self.config_file_path)

    # Função para ler variáveis de configuração de um arquivo .config
    def load_config(self, file_path):
        config = {}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):  # Ignorar linhas em branco e comentários
                        key, value = line.strip().split('=', 1)
                        config[key.strip()] = value.strip()
        return config

    # Função para criar/atualizar o arquivo .config
    def save_config(self, file_path, config):
        with open(file_path, 'w') as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")

    def check_files(self, path):
        """Verifica"""
        binary_path = os.path.join(self.VENV_PATH)
        if binary_path:
            return True
        return None

    # Função para obter entradas do usuário e atualizar o arquivo de configuração
    def configure(self):
        config = {
            'OS_SYSTEM': os.name,
            'VERSION': self.VERSION
        }
        if os.name == 'nt':
            config[
                'FFMPEG_URL'] = ('https://raw.githubusercontent.com/PauloCesar-dev404/binarios/main/ffmpeg2024-07-15'
                                 '-git-350146a1ea-essentials_build.zip')
            config['FFMPEG_BINARY'] = 'ffmpeg.exe'
        elif os.name == 'posix':
            config[
                'FFMPEG_URL'] = 'https://raw.githubusercontent.com/PauloCesar-dev404/binarios/main/ffmpeg_linux.zip'
            config['FFMPEG_BINARY'] = 'ffmpeg'
        config['STATUS'] = 'TRUE'
        config['VENV_PATH'] = os.path.dirname(self.config_file_path)
        config['INSTALL_DIR'] = self.INSTALL_DIR
        self.save_config(self.config_file_path, config)

    # Função para detectar se estamos em um ambiente virtual
    def is_virtualenv(self):
        return (
                hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )

    # Função para baixar o arquivo
    def download_file(self, url: str, local_filename: str):
        """Baixa um arquivo do URL para o caminho local especificado."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_length = int(response.headers.get('content-length', 0))

            with open(local_filename, 'wb') as f:
                start_time = time.time()
                downloaded = 0

                for data in response.iter_content(chunk_size=4096):
                    downloaded += len(data)
                    f.write(data)

                    elapsed_time = time.time() - start_time
                    elapsed_time = max(elapsed_time, 0.001)  # Prevenir divisão por zero
                    speed_kbps = (downloaded / 1024) / elapsed_time
                    percent_done = (downloaded / total_length) * 100

                    sys.stdout.write(
                        f"\r{Fore.LIGHTCYAN_EX}Baixando Binários do ffmpeg: {Style.RESET_ALL}{Fore.LIGHTGREEN_EX}"
                        f"{percent_done:.2f}%{Style.RESET_ALL} | {Fore.LIGHTCYAN_EX}Velocidade:{Style.RESET_ALL}"
                        f"{Fore.LIGHTGREEN_EX} {speed_kbps:.2f} KB/s{Style.RESET_ALL} | "
                        f"{Fore.LIGHTCYAN_EX}Tempo decorrido:{Style.RESET_ALL} {Fore.LIGHTGREEN_EX}{int(elapsed_time)}s"
                        f"{Style.RESET_ALL}")
                    sys.stdout.flush()
                sys.stdout.write("\nDownload completo.\n")
                sys.stdout.flush()
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"Erro ao baixar o arquivo: {e}\n")
            raise
        except IOError as e:
            if isinstance(e, IncompleteRead):
                sys.stderr.write("Erro de conexão: Leitura incompleta\n")
            else:
                sys.stderr.write(f"Ocorreu um erro de I/O: {str(e)}\n")
            raise

    # Função para extrair o arquivo ZIP
    def extract_zip(self, zip_path: str, extract_to: str):
        """Descompacta o arquivo ZIP no diretório especificado."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

        except zipfile.BadZipFile as e:
            sys.stderr.write(f"Erro ao descompactar o arquivo: {e}\n")
            raise
        finally:
            os.remove(zip_path)

    # Função para remover o arquivo
    def remove_file(self, file_path: str):
        """Remove o arquivo especificado."""
        # Remover o diretório temporário
        if os.path.exists(file_path):
            try:
                sys.stdout.flush()  # Certificar-se de que toda a saída foi impressa antes de remover o diretório
                shutil.rmtree(file_path, ignore_errors=True)
            except PermissionError as e:
                print(f"Permissão negada ao tentar remover o diretório {file_path}: {e}")
            except OSError as e:
                print(f"Erro ao remover o diretório {file_path}: {e}")
            except Exception as e:
                print(f"Erro inesperado ao remover o diretório {file_path}: {e}")

    # Função para instalar os binários
    def install_bins(self):
        """Instala o ffmpeg baixando e descompactando o binário apropriado."""
        self.configure()
        zip_path = os.path.join(self.INSTALL_DIR, "ffmpeg.zip")
        # Criar o diretório de destino se não existir
        os.makedirs(self.INSTALL_DIR, exist_ok=True)
        # Baixar o arquivo ZIP
        self.download_file(self.FFMPEG_URL, zip_path)
        # Descompactar o arquivo ZIP
        self.extract_zip(zip_path, self.INSTALL_DIR)
        # Remover o arquivo ZIP
        self.remove_file(zip_path)

    # Função para desinstalar os binários
    def uninstall_bins(self):
        """Remove os binários do ffmpeg instalados no ambiente virtual com força bruta."""
        dt = self.loader()
        install_dir = dt.get('INSTALL_DIR')

        if install_dir and os.path.exists(install_dir):
            try:
                # Tenta remover o diretório e seu conteúdo
                shutil.rmtree(install_dir, ignore_errors=True)

                # Verifica se o diretório foi removido
                if not os.path.exists(install_dir):
                    print(f"ffmpeg desinstalado com sucesso do diretório: {install_dir}")
                else:
                    print(f"Falha ao remover o diretório: {install_dir}")

            except Exception as e:
                sys.stderr.write(f"Erro ao remover o diretório ffmpeg-binaries: {e}\n")
                raise
        else:
            print("ffmpeg já está desinstalado ou nunca foi instalado.")

    def run(self):
        try:
            self.configure()
            ffmpeg_binary_path = os.path.join(self.INSTALL_DIR, self.FFMPEG_BINARY)
            if not os.path.exists(ffmpeg_binary_path):
                self.configure()
                self.install_bins()
            else:
                self.configure()
        except TypeError:
            self.configure()
        except FileNotFoundError:
            self.configure()
        except Exception as e:
            raise DeprecationWarning(
                f"este erro deve ser contatado ao desenvolvedor!juntamente com 'nome do ambiente virtual e qual o "
                f"tipo' , ' seu sistema' e 'versão do python' '{e}'")

    def __get_pip_path(self,venv_path):
        pyvenv_cfg_path = os.path.join(venv_path, 'pyvenv.cfg')
        if not os.path.isfile(pyvenv_cfg_path):
            raise FileNotFoundError(f"{pyvenv_cfg_path} não encontrado")
        with open(pyvenv_cfg_path, 'r') as file:
            lines = file.readlines()
        for line in lines:
            if line.startswith('home'):
                home_path = line.split('=')[1].strip()
                pip_path = os.path.join(home_path, 'Scripts',
                                        'pip.exe') if platform.system() == "Windows" else os.path.join(home_path, 'bin',
                                                                                                       'pip')
                return pip_path

        raise ValueError("Não foi possível encontrar o caminho do pip no arquivo pyvenv.cfg")

    def create_file(self):
        """Cria o arquivo de desinstalação apropriado com base no sistema operacional."""
        base_path = self.VENV_PATH
        pip_path = self.__get_pip_path(base_path)
        os_name = platform.system()

        if os_name == "Windows":
            bat_content = fr"""@echo off
    chcp 65001 >nul
    SET "INSTALL_DIR={base_path}\\ffmpeg-binaries"
    SET "FILE={base_path}\\.m3u8_analyzer_config"

    :: Remover o diretório de instalação do ffmpeg
    IF EXIST "%INSTALL_DIR%" (
        RMDIR /S /Q "%INSTALL_DIR%" 2>nul
    )

    :: Remover o arquivo de configuração
    IF EXIST "%FILE%" (
        DEL /Q "%FILE%" 2>nul
    )

    :: Executar o comando pip uninstall m3u8-analyzer no ambiente virtual
    "{pip_path}" uninstall m3u8-analyzer

    :: Criar um script temporário para remover o próprio script
    SET "TEMP_SCRIPT=%TEMP%\\remove_self.bat"
    (
        ECHO @echo off
        ECHO :loop
        ECHO DEL "%~f0" ^>nul 2^>^&1
        ECHO IF EXIST "%~f0" GOTO loop
        ECHO DEL "%TEMP_SCRIPT%" ^>nul 2^>^&1
        ECHO EXIT /b 0
    ) > "%TEMP_SCRIPT%" 2>nul

    :: Executa o script temporário sem esperar
    START "" /B "%TEMP_SCRIPT%" 2>nul
    EXIT
    """

            bat_file_path = os.path.join(base_path, 'Scripts', 'm3u8_analyzer_uninstall.bat')

            try:
                bat_dir_path = os.path.dirname(bat_file_path)
                if not os.path.exists(bat_dir_path):
                    os.makedirs(bat_dir_path)

                with open(bat_file_path, 'w', encoding='utf-8') as bat_file:
                    bat_file.write(bat_content)

            except Exception as e:
                print(f"Erro ao criar o script de remoção do ffmpeg: {e}")

        elif os_name == "Linux":
            sh_content = fr"""#!/bin/bash

    # Definir as variáveis
    INSTALL_DIR="{base_path}/ffmpeg-binaries"
    FILE="{base_path}/.m3u8_analyzer_config"
    # Remover o diretório de instalação do ffmpeg
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR" 2>/dev/null
    fi

    # Remover o arquivo de configuração
    if [ -f "$FILE" ]; then
        rm "$FILE" 2>/dev/null
    fi


    # Executar o comando pip uninstall m3u8-analyzer no ambiente virtual
    "{pip_path}" uninstall m3u8-analyzer

    # Remover o próprio script
    SELF="$0"
    if [ -f "$SELF" ]; then
        rm "$SELF" 2>/dev/null
    fi
    """

            sh_file_path = os.path.join(base_path, 'bin', 'm3u8_analyzer_uninstall.sh')

            try:
                sh_dir_path = os.path.dirname(sh_file_path)
                if not os.path.exists(sh_dir_path):
                    os.makedirs(sh_dir_path)

                with open(sh_file_path, 'w', encoding='utf-8') as sh_file:
                    sh_file.write(sh_content)

                os.chmod(sh_file_path, 0o755)

            except Exception as e:
                print(f"Erro ao criar o script de remoção do ffmpeg: {e}")

        else:
            print("Sistema operacional não suportado. Nenhum script criado.")


def g():
    configurate = Configurate()
    configurate.run()
    configurate = Configurate()
    load = configurate.loader()
    return load


if __name__ == '__main__':
    raise RuntimeError("erro de execução!")
