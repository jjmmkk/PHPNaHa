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



@Singleton
class NamespaceIndex:

    _namespace_index = []

    def clear(self):
        self._namespace_index = []

    def addNamespace(self, name, filename):
        self._namespace_index.append(NamespaceContainer(name, filename))

    def getIndex(self):
        return self._namespace_index


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
        sublime.status_message('PHPNaHa: Beginning indexing')
        for folder in self.root_folders:
            files = self.get_php_files(folder)
            for file_name in files:
                self.store_namespace(file_name)
        sublime.status_message('PHPNaHa: Finished indexing')

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
                if line.startswith('<?php') and 'namespace' in line:
                    namespace_match = re.search(r'namespace ([^;]*)', line)
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
        print(len(NamespaceIndex.Instance().getIndex()))
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
        index = NamespaceIndex.Instance().getIndex()
        quick_panel_options = [container.name() for container in index]
        self.view.window().show_quick_panel(
            items = quick_panel_options,
            on_select = self.select_file,
            on_highlight = self.preview_file
        )

    def select_file(self, index):
        if index == -1:
            return
        else:
            print('index selected: ' + index)

    def preview_file(self, index):
        print('preview index: ' + index)


class PhpnahaFindClassAndInsertUseStatement(sublime_plugin.TextCommand):

    def run(self, edit):
        pass
