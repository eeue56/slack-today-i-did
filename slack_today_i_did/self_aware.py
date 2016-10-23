import os
import subprocess
import sys
import psutil
import logging


def git_checkout(branch):
    os.system('git pull')
    os.system(f'git checkout {branch}')

def git_current_version():
    byte_text = subprocess.check_output(["git", "status"], stderr=subprocess.STDOUT)
    text = byte_text.decode()

    first_line = text.split('\n')[0]

    return first_line


def python_version():
    info = sys.version_info
    version = f'{info[0]}.{info[1]}.{info[2]}'

    return version


def ruby_version():
    byte_text = subprocess.check_output(["ruby", "--version"], stderr=subprocess.STDOUT)
    text = byte_text.decode()

    first_line = text.split('\n')[0]

    return first_line


def restart_program():
    """Restarts the current program, with file objects and descriptors
       cleanup
    """

    try:
        p = psutil.Process(os.getpid())
        for handler in p.get_open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        logging.error(e)

    python = sys.executable
    os.execl(python, python, *sys.argv)
