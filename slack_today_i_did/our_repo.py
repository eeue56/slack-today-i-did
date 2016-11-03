"""
This file lets you do things with a repo. At the moment, the ElmRepo class
can be used in order to get meta info on Elm files in a repo,
such as the number of 0.16/0.17 files
"""

import os
import glob
from typing import List, Dict
from enum import Enum
from contextlib import contextmanager


class OurRepo(object):
    def __init__(self, folder: str, token: str, org: str, repo: str):
        self.folder = folder
        self.token = token
        self.org = org
        self.repo = repo

    def make_repo_dir(self) -> None:
        os.makedirs(self.folder, exist_ok=True)

    def _git_init(self) -> None:
        url = f'https://{self.token}@github.com/{self.org}/{self.repo}.git'
        os.system(f'git clone --depth 1 {url}')
        os.chdir(self.repo)
        os.system(f'git remote set-url origin {url}')

    def _git_clone(self, branch_name: str = 'master') -> None:
        os.system(f'git remote set-branches origin {branch_name}')
        os.system(f'git fetch --depth 1 origin {branch_name}')
        os.system(f'git checkout origin/{branch_name}')

    def get_ready(self, branch_name: str = 'master') -> None:
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


class ElmVersion(Enum):
    unknown = -1
    v_016 = 0
    v_017 = 1


class ElmRepo(OurRepo):
    def __init__(self, *args, **kwargs):
        OurRepo.__init__(self, *args, **kwargs)
        self._known_files = {ElmVersion.v_016: [], ElmVersion.v_017: []}
        self._breakdown_cache = {}
        self._import_cache = {}
        self._breakdown_lock = False

    def get_elm_files(self) -> List[str]:
        return glob.glob(f'{self.repo_dir}/**/*.elm', recursive=True)

    @property
    def number_of_017_files(self):
        elm_017_count = 0

        for file in self.get_elm_files():
            if self.what_kinda_file(file) == ElmVersion.v_017:
                elm_017_count += 1

        return elm_017_count

    @property
    def number_of_016_files(self):
        elm_016_count = 0

        for file in self.get_elm_files():
            if self.what_kinda_file(file) == ElmVersion.v_016:
                elm_016_count += 1

        return elm_016_count

    def get_files_for_017(self, pattern: str) -> List[str]:
        pattern = pattern.replace('.', '/')
        all_files = glob.glob(
            f'{self.repo_dir}/**/{pattern}.elm',
            recursive=True
        )

        return [
            filename for filename in all_files
            if self.what_kinda_file(filename) == ElmVersion.v_017
        ]

    def get_matching_filenames(self, pattern: str) -> List[str]:
        pattern = pattern.replace('.', '/')
        all_files = glob.glob(
            f'{self.repo_dir}/**/{pattern}.elm',
            recursive=True
        )
        return all_files

    @contextmanager
    def lock(self) -> None:
        self.create_lock()
        yield
        self.remove_lock()

    def create_lock(self) -> None:
        """ create a lock so that caches can be used to make some calcs faster """
        self._breakdown_lock = True
        self._breakdown_cache = {}
        self._import_cache = {}

    def remove_lock(self) -> None:
        """ removes a lock so caches are no longer used """
        self._breakdown_lock = False

    def get_017_porting_breakdown(self, pattern: str) -> Dict[str, Dict[str, int]]:  # noqa: E501
        all_files = self.get_matching_filenames(pattern)

        breakdown = {
            filename: self.how_hard_to_port(filename) for filename in all_files
            if self.what_kinda_file(filename) == ElmVersion.v_016
        }

        if len(all_files) == 1:
            imports = self.file_import_list(all_files[0])
            for import_ in imports:
                file_names = self.get_matching_filenames(import_)

                if not any(name in breakdown for name in file_names):
                    import_breakdown = self.get_017_porting_breakdown(import_)
                    breakdown.update(import_breakdown)

        return breakdown

    def file_import_list(self, filename: str) -> List[str]:
        """ returns the list of modules imported by a file """

        if self._breakdown_lock:
            if filename in self._import_cache:
                return self._import_cache[filename]

        import_lines = []
        in_comment = False

        with open(filename) as f:
            for line in f:
                if in_comment:
                    if line.strip().endswith('-}'):
                        in_comment = False
                elif line.startswith('import '):
                    just_the_module = 'import '.join(line.split('import ')[1:])
                    import_lines.append(just_the_module)
                elif line.strip().startswith('{-'):
                    if line.strip().endswith('-}'):
                        in_comment = False
                    else:
                        in_comment = True
                elif not (line.startswith('module') or line.startswith(' ')):
                    # we're past the imports
                    break

        if self._breakdown_lock:
            self._import_cache[filename] = import_lines

        return import_lines

    def how_hard_to_port(self, filename: str) -> Dict[str, int]:
        """ returns a breakdown of how hard a file is to port 0.16 -> 0.17 """

        if self._breakdown_lock:
            if filename in self._breakdown_cache:
                return self._breakdown_cache[filename]

        breakdown = {}

        with open(filename) as f:
            text = f.read()

        if 'port' in text or 'Signal' in text:
            port_count = text.count('port')
            signal_count = text.count('Signal')
            breakdown['Ports and signals'] = (port_count + signal_count) * 3

        if 'import Native' in text:
            native_modules_count = text.count('import Native')
            breakdown['Native modules imported'] = (native_modules_count * 2)

        if ' Html' in text:
            html_count = text.count(' Html')
            breakdown['Html stuff'] = html_count

        if self._breakdown_lock:
            self._breakdown_cache[filename] = breakdown

        return breakdown

    def what_kinda_file(self, filename: str) -> ElmVersion:
        """ if a filename is known to be 0.16 or 0.17, return that const
            otherwise, go through line by line to try and find some identifiers
        """
        if filename in self._known_files[ElmVersion.v_016]:
            return ElmVersion.v_016

        if filename in self._known_files[ElmVersion.v_017]:
            return ElmVersion.v_017

        with open(filename) as f:
            for line in f:
                if line.strip():
                    if 'exposing' in line:
                        self._known_files[ElmVersion.v_017].append(filename)
                        return ElmVersion.v_017
                    if 'where' in line:
                        self._known_files[ElmVersion.v_016].append(filename)
                        return ElmVersion.v_016
        return ElmVersion.unknown
