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

    def getIndexByName(self, name):
        namespaces = []
        for namespace in self._namespace_index:
            if name == namespace.name():
                namespaces = [namespace]
                break
            if name in namespace.name():
                namespaces.append(namespace)
        return namespaces


class NamespaceContainer(object):
    _name = ''
    _filename = ''

    def __init__(self, name, filename):
        self._name = name.strip()
        self._filename = filename;

    def name(self):
        return self._name

    def path(self):
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
                    class_name_match = re.search( r'^(?:abstract )?(?:(?:class)|(?:interface)) ([^\s]+)', line)
                if namespace_match and class_name_match:
                    self._index.addNamespace(
                        namespace_match.group(1) + '\\' + class_name_match.group(1),
                        os.path.abspath(file_name)
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
        file_name = self.view.file_name()
        file_path = os.path.abspath(file_name)
        path_list = list(filter(None, file_path.split(os.path.sep)))
        path_list.reverse()
        namespace_list = []
        for item in path_list:
            if not item.endswith('.php'):
                if item[0].isupper() or item == 'eZ':
                    namespace_list.append(item)
                else:
                    break
        if namespace_list:
            namespace = '\\'.join(namespace_list)
            self.view.run_command('private_insert_namespace_statement', { 'namespace': namespace })


class PhpnahaCopyNamespaceAndClass(sublime_plugin.TextCommand):

    def run(self, edit):
        pass


class FilePreviewer(object):
    def preview_file(self, option_index):
        namespace = self._index[option_index]
        self.view.window().open_file(
            namespace.path(),
            sublime.ENCODED_POSITION | sublime.TRANSIENT
        )


class PhpnahaOpenClassFile(sublime_plugin.TextCommand, FilePreviewer):

    _index = None
    _current_view = None

    def run(self, edit):
        # Store current view, so that it can be re-focused after previews
        self._current_view = self.view

        self._index = NamespaceIndex.Instance().getIndex()
        selections = self.view.sel()
        if selections:
            region = selections[0]
            line_region = self.view.expand_by_class(region, sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
            line = self.view.substr(line_region).strip()
            if (re.match(r'^use', line)):
                namespace = re.search( r'^use ([^ ;]+)', line).group(1)
                self._index = NamespaceIndex.Instance().getIndexByName(namespace)
            else:
                word_region = self.view.expand_by_class(region, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END | sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
                word = self.view.substr(word_region).strip()
                if word:
                    # Check if word is
                    # 1. imported with use
                    # 2. in current namespace
                    namespace = False
                    use_regions = self.view.find_all(r'^use ([^;]+)')
                    for use_region in use_regions:
                        use_line = self.view.substr(use_region)
                        if word in use_line:
                            namespace = re.search(r'^use ([^ ;]+)', self.view.substr(use_region)).group(1)
                            self._index = NamespaceIndex.Instance().getIndexByName(namespace)
                            break
                    if not namespace:
                        namespace_region = self.view.find(r'namespace ([^ ;]+)', 0)
                        if namespace_region:
                            namespace_match = self.view.substr(namespace_region)
                            namespace = re.search(r'namespace ([^ ;]+)', namespace_match).group(1)
                            namespace += '\\' + word
                            self._index = NamespaceIndex.Instance().getIndexByName(namespace)

        # Open directly if only one file was found
        if len(self._index) == 1:
            self.select_file(0)
        # Else open quick panel
        else:
            quick_panel_options = [container.name() for container in self._index]
            self.view.window().show_quick_panel(
                items = quick_panel_options,
                on_select = self.select_file,
                on_highlight = self.preview_file,
                flags = sublime.MONOSPACE_FONT
            )

    def select_file(self, option_index):
        # Open file if quick panel was not cancelled
        if option_index != -1:
            self.view.window().open_file(self._index[option_index].path())
        # Else re-focus the current view
        else:
            self.view.window().focus_view(self._current_view)


class PhpnahaFindClassAndInsertUseStatement(sublime_plugin.TextCommand, FilePreviewer):

    _index = None
    _current_view = None

    def run(self, edit):
        self._index = NamespaceIndex.Instance().getIndex()
        # Store current view, so that it can be re-focused if needed
        self._current_view = self.view
        quick_panel_options = [container.name() for container in self._index]
        self.view.window().show_quick_panel(
            items = quick_panel_options,
            on_select = self.select_file,
            on_highlight = self.preview_file,
            flags = sublime.MONOSPACE_FONT
        )

    def select_file(self, option_index):
        # Open file if quick panel was not cancelled
        if option_index != -1:
            self._current_view.run_command('private_insert_use_statement', { 'namespace': self._index[option_index].name() })
        # Else re-focus the current view
        self.view.window().focus_view(self._current_view)


class PrivateInsertUseStatement(sublime_plugin.TextCommand):

    def run(self, edit, namespace):
        use_statement = 'use ' + namespace + ';\n'

        insert_loctions = [
            (
                r'^use ',
                '{1}{0}',
            ),
            (
                r'^namespace ',
                '{0}\n{1}',
            ),
            (
                r'^class ',
                '{1}\n{0}',
            ),
            (
                r'^<\?php',
                '{0}\n{1}',
            ),
        ]
        view = self.view
        for attempt_location in insert_loctions:
            regex, format = attempt_location
            region_match = view.find(regex, 0)
            if region_match:
                line_match = view.full_line(region_match.begin())
                line_text = view.substr(line_match)
                insertion_text = format.format(line_text, use_statement)
                view.replace(edit, line_match, insertion_text)
                break


class PrivateInsertNamespaceStatement(sublime_plugin.TextCommand):

    def run(self, edit, namespace):
        namespace_statement = 'namespace ' + namespace + ';\n'

        insert_loctions = [
            (
                r'^use ',
                '{1}\n{0}',
            ),
            (
                r'^class ',
                '{1}\n{0}',
            ),
            (
                r'^<\?php',
                '{0}\n{1}\n',
            ),
        ]
        view = self.view
        for attempt_location in insert_loctions:
            regex, format = attempt_location
            region_match = view.find(regex, 0)
            if region_match:
                line_match = view.full_line(region_match.begin())
                line_text = view.substr(line_match)
                insertion_text = format.format(line_text, namespace_statement)
                view.replace(edit, line_match, insertion_text)
                break
