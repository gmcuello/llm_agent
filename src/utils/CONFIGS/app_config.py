"""
Configuraciones para la sala de control (Frontend de Integridad)
"""

import os
import sys
import logging
from configparser import ConfigParser, ExtendedInterpolation

logger = logging.getLogger()

if os.path.isfile(os.getcwd() + '/APP.ini') is not True:
    logger.error('No se encontró el archivo de configuración APP.ini en el directorio raiz')
    sys.exit()
else:
    environ_dict = dict(os.environ)
    if not 'ANROOT' in environ_dict:
        environ_dict['ANROOT'] = os.getcwd()
    config = ConfigParser(defaults=environ_dict, allow_no_value=False, interpolation=ExtendedInterpolation())
    config.read(os.getcwd() + '/APP.ini', encoding='utf-8')

# =============================================================================
# PATHS Y LOGS
# =============================================================================
ROOT = config.get(section='LOCAL_PATH', option='ROOT', fallback='')
PATH_DESTINATION = config.get(section='LOCAL_PATH', option='PATH_DESTINATION', fallback='')
PATH_LOG = config.get(section='LOG', option='PATH_LOG', fallback='')
NAME_LOG = config.get(section='LOG', option='NAME_LOG', fallback='')
FILE_LOG = config.get('LOG', 'FILE_LOG', fallback='logfile.log')
BACKUP_COUNT = config.getint('LOG', 'BACKUP_COUNT', fallback=5)

# =============================================================================
# PARAMETROS DEL PROYECTO
# =============================================================================
PROJECT_NAME = config.get(section='PROJECT', option='PROJECT_NAME', fallback='IIS')
DEBUG = config.get(section='PROJECT', option='DEBUG', fallback=False)
SCT_KEY = config.get(section='PROJECT', option='SCT_KEY', fallback='')
CSV_SEPARATOR = config.get(section='PROJECT', option='CSV_SEPARATOR', fallback=';')

# =============================================================================
# API REST (Backend / Gateway)
# =============================================================================
API_SERVER = config.get(section='API_REST', option='API_SERVER', fallback='')
API_PORT = config.get(section='API_REST', option='API_PORT', fallback='')
API_PREFIX = config.get(section='API_REST', option='API_PREFIX', fallback='')
API_DIAGNOSTICS_URL = config.get(section='API_REST', option='API_DIAGNOSTICS_URL', fallback='')
API_NOTES_URL = config.get(section='API_REST', option='API_NOTES_URL', fallback='')
API_GRAPH_URL = config.get(section='API_REST', option='API_GRAPH_URL', fallback='')