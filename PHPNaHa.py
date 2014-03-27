import sublime
import sublime_plugin

import os
import os.path

import threading
import codecs
import re


class Singleton:
    """
    http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)


NAMESPACE_INDEX = []

@Singleton
class NamespaceIndex:

    def clear(self):
        NAMESPACE_INDEX = []

    def addNamespace(self, name, filename):
        NAMESPACE_INDEX.append(NamespaceContainer(name, filename))


class NamespaceContainer(object):
    _name = ''
    _filename = ''

    def __init__(self, name, filename):
        self._name = name.strip()
        self._filename = filename;

    def name(self):
        return self._name

    def filename(self):
        return self._filename


class NamespaceIndexerThread(threading.Thread):

    _index = None

    def __init__(self, root_folders, storage):
        # Timeout is in seconds
        self.timeout = 30
        self._index = storage
        self.root_folders = root_folders
        threading.Thread.__init__(self)

    def run(self):
        for folder in self.root_folders:
            files = self.get_php_files(folder)
            for file_name in files:
                self.store_namespace(file_name)

    def stop(self):
        if self.isAlive():
            self._Thread.__stop()

    def store_namespace(self, file_name):
        # Must be like _a_ PHP file in Symfony with bad encoding
        try:
            file_lines = codecs.open(file_name, 'r', 'utf-8')
            namespace_match = False
            class_name_match = False
            for line in file_lines:
                if line.startswith('namespace'):
                    namespace_match = re.search(r'^namespace ([^;]*)', line)
                if re.match(r'^(abstract|class|interface)', line):
                    class_name_match = re.search( r'^(?:abstract )?(?:(?:class)|(?:interface)) ([^ ]+)', line)
                if namespace_match and class_name_match:
                    self._index.addNamespace(
                        namespace_match.group(1) + '\\' + class_name_match.group(1),
                        os.path.basename(file_name)
                    )
                    break
        except:
            pass

    def get_php_files(self, dir_name):
        fileList = []
        for file in os.listdir(dir_name):
            dirfile = os.path.join(dir_name, file)
            if os.path.isfile(dirfile) and dirfile.endswith('.php'):
                fileList.append(dirfile)
            elif os.path.isdir(dirfile):
                fileList += self.get_php_files(dirfile)
        return fileList


class PhpnahaDebug(sublime_plugin.TextCommand):

    def run(self, edit):
        print(len(NAMESPACE_INDEX))
        print(NAMESPACE_INDEX[0].name())
        pass


class PhpnahaIndexProjectNamespaces(sublime_plugin.TextCommand):

    _indexer_thread = None

    def run(self, edit):
        NamespaceIndex.Instance().clear()
        if self._indexer_thread != None:
            self._indexer_thread.stop()
        project_root_folders = self.view.window().folders()
        self._indexer_thread = NamespaceIndexerThread(
            project_root_folders,
            NamespaceIndex.Instance()
        )
        self._indexer_thread.start()


class PhpnahaInsertNamespaceStatement(sublime_plugin.TextCommand):

    def run(self, edit):
        pass


class PhpnahaCopyNamespaceAndClass(sublime_plugin.TextCommand):

    def run(self, edit):
        pass


class PhpnahaOpenClassFile(sublime_plugin.TextCommand):

    def run(self, edit):
        pass


class PhpnahaFindClassAndInsertUseStatement(sublime_plugin.TextCommand):

    def run(self, edit):
        pass
