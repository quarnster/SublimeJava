import os
import webbrowser

path_to_full = lambda path: '.'.join(path.replace('\\', '/').split('/'))
remove_dollar = lambda classname: classname.replace('$$', '.')


class JavaClassOpener(object):

    MSG_NO_CLASSES_FOUND = \
        "No classes could be found. Check your %s project setting."

    def __init__(self, completion, view, under_cursor, setting_name):
        self.completion = completion
        self.view = view
        self.window = view.window()
        self.under_cursor = under_cursor
        self.setting_name = setting_name

    def show(self):
        classname = self.completion.get_class_under_cursor() \
            if self.under_cursor \
            else None

        options = []
        for path in self.completion.get_setting(self.setting_name, ""):
            path = os.path.abspath(
                self.completion.expand_path(path, self.window)
            )
            options.extend(self._scan_dir(path, classname))

        def do_open(result):
            if result != -1:
                filename = options[result][1]
                self._view_file(filename)

        if classname is not None and len(options) == 1:
            do_open(0)
        elif len(options) > 1:
            self.window.show_quick_panel([t[0] for t in options], do_open)
        else:
            self.completion.show_error(self.MSG_NO_CLASSES_FOUND %
                                       self.setting_name)

    def _scan_dir(self, base, classname_to_find=None):
        return []

    def _view_file(self, filename):
        pass


class JavaSourceOpener(JavaClassOpener):
    def __init__(self, completion, view, under_cursor):
        super(JavaSourceOpener, self).__init__(completion,
                                               view,
                                               under_cursor,
                                               "sublimejava_srcpath")

    def _scan_dir(self, base, classname_to_find=None):
        for root_name, dir_names, filenames in os.walk(base):
            try:
                dir_names.remove('.svn')
            except:
                pass
            package = path_to_full(root_name[len(base) + 1:]) + "."
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                classname = package + filename.split('.')[0]
                if (classname_to_find is not None and
                        classname != classname_to_find):
                    continue
                yield classname, (root_name + "/" + filename)

    def _view_file(self, filename):
        self.view.window().open_file(filename)


class JavaDocOpener(JavaClassOpener):
    def __init__(self, completion, view, under_cursor):
        super(JavaDocOpener, self).__init__(completion,
                                            view,
                                            under_cursor,
                                            "sublimejava_docpath")

    def _scan_dir(self, base, classname_to_find=None):
        search_classname = None \
            if classname_to_find is None \
            else remove_dollar(classname_to_find)

        for root_name, dir_names, filenames in os.walk(base):
            try:
                dir_names.remove('class-use')
            except:
                pass
            package = path_to_full(root_name[len(base) + 1:]) + "."
            for filename in filenames:
                # - gets all the java overview bidness
                if (not filename.endswith('.html') or
                        '-' in filename or
                        filename == 'index.html'):
                    continue
                classname = remove_dollar(package + filename[:-5])
                if (search_classname is not None and
                        classname != search_classname):
                    continue
                yield classname, (root_name + "/" + filename)

    def _view_file(self, filename):
        webbrowser.open_new(filename)
