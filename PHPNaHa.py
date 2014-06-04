import sublime
import sublime_plugin

import os
import os.path

import threading
import codecs
import re
import hashlib



def multiton(cls):
    """
    http://en.wikipedia.org/wiki/Multiton_pattern
    """
    instances = {}
    def getinstance(key):
        if key not in instances:
            instances[key] = cls()
        return instances[key]
    return getinstance


@multiton
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

    def getIndexByClassName(self, class_name):
        class_name = '\\' + class_name.strip('\\')
        namespaces = []
        for namespace in self._namespace_index:
            if namespace.name().endswith(class_name):
                namespaces.append(namespace)
        return namespaces

    def getIndexSubClassesByName(self, name):
        return [namespace for namespace in self._namespace_index if name in namespace.name()]


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


def getProjectIndexInstance(key_base):
    if isinstance(key_base, sublime.Window):
        key = hashlib.md5(''.join(sorted(key_base.folders())).encode('utf-8')).hexdigest()
    else:
        key = 'not_project'
    return NamespaceIndex(key)


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
                elif class_name_match:
                    self._index.addNamespace(
                        '\\' + class_name_match.group(1),
                        os.path.abspath(file_name)
                    )
                    break
        except:
            pass

    def get_php_files(self, dir_name):
        fileList = []
        if not os.access(dir_name, os.R_OK):
            return fileList
        for file in os.listdir(dir_name):
            dirfile = os.path.join(dir_name, file)
            if os.path.isfile(dirfile) and dirfile.endswith('.php'):
                fileList.append(dirfile)
            elif os.path.isdir(dirfile):
                fileList += self.get_php_files(dirfile)
        return fileList


class PhpnahaIndexProjectNamespaces(sublime_plugin.TextCommand):

    _indexer_thread = None

    def run(self, edit):
        if self._indexer_thread != None:
            self._indexer_thread.stop()
        window = self.view.window()
        index = getProjectIndexInstance(window)
        index.clear()
        project_root_folders = window.folders()
        self._indexer_thread = NamespaceIndexerThread( project_root_folders, index )
        self._indexer_thread.start()


class NamespacePathHandler(object):

    def findNamespaceByPath(self, path):
        namespace = ''
        if path:
            path_list = list(filter(None, path.split(os.path.sep)))
            path_list.reverse()
            namespace_list = []
            for item in path_list:
                if not item.endswith('.php'):
                    if item[0].isupper() or item == 'eZ':
                        namespace_list.append(item)
                    else:
                        break
            if namespace_list:
                namespace_list.reverse()
                namespace = '\\'.join(namespace_list)
        return namespace


class PhpnahaInsertNamespaceStatement(sublime_plugin.TextCommand, NamespacePathHandler):

    def run(self, edit):
        file_name = self.view.file_name()
        file_path = os.path.abspath(file_name)
        namespace = self.findNamespaceByPath(file_path)
        if namespace:
            self.view.run_command('private_insert_namespace_statement', { 'namespace': namespace })


class PhpnahaCopyNamespaceAndClass(sublime_plugin.TextCommand, NamespacePathHandler):

    def run(self, edit):
        namespace = False
        class_name = False

        namespace_region = self.view.find(r'namespace ([^ ;]+)', 0)
        if namespace_region:
            namespace_match = self.view.substr(namespace_region)
            namespace = re.search(r'namespace ([^ ;]+)', namespace_match).group(1)
        class_name_region = self.view.find(r'^(?:abstract )?(?:(?:class)|(?:interface)) ([^\s]+)', 0)
        if class_name_region:
            class_name_match = self.view.substr(class_name_region)
            class_name = re.search(r'^(?:abstract )?(?:(?:class)|(?:interface)) ([^\s]+)', class_name_match).group(1)

        clipboard = False
        if namespace and class_name:
            clipboard = namespace + '\\' + class_name
        elif namespace:
            clipboard = namespace
        elif class_name:
            clipboard = '\\' + class_name
        if clipboard:
            sublime.set_clipboard(clipboard)


class FilePreviewer(object):

    def preview_file(self, option_index):
        namespace = self._index[option_index]
        self.view.window().open_file(
            namespace.path(),
            sublime.ENCODED_POSITION | sublime.TRANSIENT
        )

    def quick_panel(self):
        whole_index = self._index_instance.getIndex()
        self._index = whole_index

        selections = self._current_view.sel()
        if selections:
            self.set_index_by_selected_region(selections[0])

        if len(self._index) == 0:
            self._index = whole_index

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


class PhpnahaOpenClassFile(sublime_plugin.TextCommand, FilePreviewer):

    _index_instance = None
    _index = None
    _current_view = None

    def run(self, edit):
        self._index_instance = getProjectIndexInstance(self.view.window())
        self._index = self._index_instance.getIndex()
        self._current_view = self.view
        self.quick_panel()

    def set_index_by_selected_region(self, region):
        line_region = self._current_view.expand_by_class(region, sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
        line = self._current_view.substr(line_region).strip()
        if (re.match(r'^use', line)):
            namespace = re.search( r'^use ([^ ;]+)', line).group(1)
            self._index = self._index_instance.getIndexByName(namespace)
        else:
            word_region = self._current_view.expand_by_class(region, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END | sublime.CLASS_LINE_START | sublime.CLASS_LINE_END, ' ')
            word = self._current_view.substr(word_region).strip().strip('\\')
            word = re.sub(r'^[^\w]+|[^\w]+$', '', str(word))
            if '->' in word:
                word = next(iter(word.split('->')), False)
            if '::' in word:
                word = next(iter(word.split('::')), False)
            if word:
                namespace = False
                use_regions = self._current_view.find_all(r'^use ([^;]+)')
                if '\\' in word:
                    use_end = word.split('\\')[0]
                    for use_region in use_regions:
                        use_line = self._current_view.substr(use_region)
                        if use_line.endswith(use_end):
                            namespace = re.search(r'^use ([^ ;]+)', self._current_view.substr(use_region)).group(1)
                            # Remove duplicate level
                            word_split = word.split('\\')[1:]
                            namespace += '\\' + '\\'.join(word_split)
                            self._index = self._index_instance.getIndexByName(namespace)
                            break
                else:
                    for use_region in use_regions:
                        use_line = self._current_view.substr(use_region)
                        if word in use_line:
                            namespace = re.search(r'^use ([^ ;]+)', self._current_view.substr(use_region)).group(1)
                            self._index = self._index_instance.getIndexByName(namespace)
                            break
                if not namespace:
                    namespace_region = self._current_view.find(r'namespace ([^ ;]+)', 0)
                    if namespace_region:
                        namespace_match = self._current_view.substr(namespace_region)
                        namespace = re.search(r'namespace ([^ ;]+)', namespace_match).group(1)
                        namespace += '\\' + word
                        self._index = self._index_instance.getIndexByName(namespace)
                        if len(self._index) == 0:
                            self._index = self._index_instance.getIndexByClassName(word)
                    else:
                        self._index = self._index_instance.getIndexByName(word)

    def select_file(self, option_index):
        # Open file if quick panel was not cancelled
        if option_index != -1:
            self.view.window().open_file(self._index[option_index].path())
        # Else re-focus the current view
        else:
            self.view.window().focus_view(self._current_view)


class PhpnahaFindClassAndInsertUseStatement(sublime_plugin.TextCommand, FilePreviewer):

    _index_instance = None
    _index = None
    _current_view = None

    def run(self, edit):
        self._index_instance = getProjectIndexInstance(self.view.window())
        self._index = self._index_instance.getIndex()
        self._current_view = self.view
        self.quick_panel()

    def set_index_by_selected_region(self, region):
        line_region = self._current_view.expand_by_class(region, sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
        line = self._current_view.substr(line_region).strip()
        if (re.match(r'^use', line)):
            self._index = self._index_instance.getIndex()
        else:
            word_region = self._current_view.expand_by_class(region, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END | sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
            word = self._current_view.substr(word_region).strip().strip('\\')
            word = re.sub(r'^[^\w]+|[^\w]+$', '', str(word))
            if '->' in word:
                word = next(iter(word.split('->')), False)
            if '::' in word:
                word = next(iter(word.split('::')), False)
            if word:
                namespace_region = self._current_view.find(r'namespace ([^ ;]+)', 0)
                if namespace_region:
                    namespace_match = self._current_view.substr(namespace_region)
                    namespace = re.search(r'namespace ([^ ;]+)', namespace_match).group(1)
                    namespace += '\\' + word
                    self._index = self._index_instance.getIndexByName(namespace)
                    if len(self._index) == 0:
                        self._index = self._index_instance.getIndexByClassName(word)
                else:
                    self._index = self._index_instance.getIndexByName(word)

    def select_file(self, option_index):
        # Open file if quick panel was not cancelled
        if option_index != -1:
            self._current_view.run_command('private_insert_use_statement', { 'namespace': self._index[option_index].name() })
        # Else re-focus the current view
        self.view.window().focus_view(self._current_view)


class PhpnahaFindNamespaceSubClass(sublime_plugin.TextCommand, FilePreviewer):

    _index_instance = None
    _index = None
    _current_view = None
    _word = None
    _word_region = None

    def run(self, edit):
        self._index_instance = getProjectIndexInstance(self.view.window())
        self._current_view = self.view
        self.quick_panel()

    def set_index_by_selected_region(self, region):
        word_region = self._current_view.expand_by_class(region, sublime.CLASS_WORD_START | sublime.CLASS_WORD_END | sublime.CLASS_LINE_START | sublime.CLASS_LINE_END, ' ')
        word = self._current_view.substr(word_region).strip()
        if word:
            word = re.sub(r'^[^\w]+|[^\w]+$', '', str(word))
            self._word_region = word_region
            self._word = word
            use_end_combos = []
            for part in word.split('\\'):
                if use_end_combos:
                    part = use_end_combos[-1] + '\\' + part
                use_end_combos.append(part)
            use_end_combos.reverse()
            use_regions = self._current_view.find_all(r'^use ([^;]+)')
            for use_region in use_regions:
                use_line = self._current_view.substr(use_region)
                if use_line.endswith(word):
                    namespace = re.search(r'^use ([^ ;]+)', self._current_view.substr(use_region)).group(1)
                    self._index = self._index_instance.getIndexSubClassesByName(namespace)
                    break
                else:
                    for use_ending in use_end_combos:
                        if use_line.endswith(use_ending):
                            namespace = re.search(r'^use ([^ ;]+)', self._current_view.substr(use_region)).group(1)
                            self._index = self._index_instance.getIndexSubClassesByName(namespace)
                            break


    def select_file(self, option_index):
        # Open file if quick panel was not cancelled
        if option_index != -1:
            namespace = self._index[option_index].name()
            class_name_parts = namespace.split(self._word)
            if len(class_name_parts) == 2:
                text = self._word + class_name_parts[1] + '\n'
                self._current_view.run_command(
                    'private_replace_region',
                    {
                        'region': (self._word_region.begin(), self._word_region.end()),
                        'text': text
                    }
                )
        # Else re-focus the current view
        self.view.window().focus_view(self._current_view)


class PrivateInsertUseStatement(sublime_plugin.TextCommand):

    def run(self, edit, namespace):
        use_statement = 'use ' + namespace + ';\n'

        insert_loctions = [
            (
                r'^use ',
                '{0}{1}',
                False,
            ),
            (
                r'^namespace ',
                '{0}\n{1}',
                True,
            ),
            (
                r'^class ',
                '{1}\n{0}',
                True,
            ),
            (
                r'^<\?php',
                '{0}\n{1}',
                True,
            ),
        ]
        view = self.view
        for attempt_location in insert_loctions:
            regex, format, search_from_start = attempt_location
            region_match = False
            if search_from_start:
                region_match = view.find(regex, 0)
            else:
                region_matches = view.find_all(regex)
                if region_matches:
                    region_match = region_matches[-1]
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


class PrivateReplaceRegion(sublime_plugin.TextCommand):

    def run(self, edit, region, text):
        region = sublime.Region(region[0], region[1])
        self.view.replace(edit, region, text)
