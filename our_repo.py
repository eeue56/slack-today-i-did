import os
import glob

class OurRepo(object):
    def __init__(self, folder: str, token: str, org: str, repo: str):
        self.folder = folder
        self.token = token
        self.org = org
        self.repo = repo

    def make_repo_dir(self):
        os.makedirs(self.folder, exist_ok=True)

    def _git_init(self):
        print(os.getcwd())
        os.system(f'git clone --depth 1 https://{self.token}@github.com/{self.org}/{self.repo}.git')
        os.system(f'git remote set-url origin https://{self.token}@github.com/{self.org}/{self.repo}.git')

    def _git_clone(self, branch_name='master'):
        print(os.getcwd())
        os.system(f'git remote set-branches origin {branch_name}')
        os.system(f'git fetch --depth 1 origin {branch_name}')
        os.system(f'git checkout {branch_name}')

    def get_ready(self, branch_name='master'):
        current_dir = os.getcwd()
        try:
            self.make_repo_dir()
            os.chdir(self.folder)
            self._git_init()
        except:
            pass
        finally:
            os.chdir(current_dir)

        os.chdir(self.repo_dir)
        try:
            self._git_clone(branch_name)
        finally:
            os.chdir(current_dir)

    @property
    def repo_dir(self):
        return f'{self.folder}/{self.repo}'


ELM_016_FILE = 0
ELM_017_FILE = 1


class ElmRepo(OurRepo):
    def __init__(self, *args, **kwargs):
        OurRepo.__init__(self, *args, **kwargs)
        self._known_files = { ELM_016_FILE : [], ELM_017_FILE : []}

    def get_elm_files(self):
        return glob.glob(f'{self.repo_dir}/**/*.elm', recursive=True)

    @property
    def number_of_017_files(self):
        elm_017_count = 0

        for file in self.get_elm_files():
            if self.what_kinda_file(file) == ELM_017_FILE:
                elm_017_count += 1

        return elm_017_count

    @property
    def number_of_016_files(self):
        elm_016_count = 0

        for file in self.get_elm_files():
            if self.what_kinda_file(file) == ELM_016_FILE:
                elm_016_count += 1

        return elm_016_count

    def what_kinda_file(self, filename):
        if filename in self._known_files[ELM_016_FILE]:
            return ELM_016_FILE

        if filename in self._known_files[ELM_017_FILE]:
            return ELM_017_FILE


        with open(filename) as f:
            for line in f:
                if line.strip():
                    if 'exposing' in line:
                        self._known_files[ELM_017_FILE].append(filename)
                        return ELM_017_FILE
                    if 'where' in line:
                        self._known_files[ELM_016_FILE].append(filename)
                        return ELM_016_FILE
        return None
