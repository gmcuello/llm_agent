# -*- coding: utf-8 -*-
"""
Creation of logger object.

Classes:

    ContextFilter

Functions:

    getLogger
    ini_log



Created on Thu Jul  9 09:11:54 2020
@author: RY24108

REF: https://docs.python.org/3/howto/logging.html

"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import psutil

from utils.CONFIGS.app_config import NAME_LOG, PATH_LOG, FILE_LOG, BACKUP_COUNT

class ContextFilter(logging.Filter):
    """
    Filter which injects contextual information into the log: memory usage and cpu usage.

    """

    def filter(self, record):
        """
        Add to the log record memory usage and cpu usage.

        :param record: current record to modify
        :type record: log record
        :return: True when executed
        :rtype: bool

        """
        record.mem_usage = psutil.virtual_memory().percent
        record.cpu_usage = psutil.cpu_percent()
        return True


def getLogger(name):
    """
    Get logger name.

    :param name: name of the logger
    :type name: string
    :return: return logger object
    :rtype: object

    """
    ini_log(logger_name=NAME_LOG, logfile=FILE_LOG, path=PATH_LOG)
    return logging.getLogger(name)
    return logging.getLogger(name=name)

def ini_log(
        logger_name=NAME_LOG,
        path=PATH_LOG,
        logfile=FILE_LOG):
    """
    Initialize logger.

    :param logger_name: logger name, defaults to NAME_LOG
    :type logger_name: TYPE, optional
    :param path: path assigned to store logs, defaults to PATH_LOG
    :type path: string, optional
    :param logfile: name of log file, defaults to FILE_LOG
    :type logfile: string, optional
    :return: logger object
    :rtype: object

    """
    # prepara directorio si es que no existe
    if os.path.isdir(PATH_LOG) is False:
        # no existe directorio y lo crea
        os.makedirs(PATH_LOG)

    # crea el logger con un nombre
    logger = logging.getLogger(logger_name)
    

    f = ContextFilter()
    logger.addFilter(f)

    logger.handlers.clear()

    # set log level
    logger.setLevel(logging.DEBUG)

    # define handlers and set formatter
    cons_handler = logging.StreamHandler()
    file_handler = TimedRotatingFileHandler(
            path + '/' + logfile,
            when='d',
            interval=1,
            backupCount=BACKUP_COUNT)

    cons_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)
    FORMAT = "%(asctime)s [%(levelname)8s] [MEM %(mem_usage)s, CPU %(cpu_usage)s] [%(filename)s: %(lineno)s, %(funcName)s() ] %(message)s"
    formatter = logging.Formatter(fmt=FORMAT)
    cons_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # add handlers to logger
    logger.addHandler(cons_handler)
    logger.addHandler(file_handler)

    return logger



