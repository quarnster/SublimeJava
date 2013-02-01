"""
Copyright (c) 2012 Fredrik Ehnbom

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

   1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.

   2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.

   3. This notice may not be removed or altered from any source
   distribution.
"""
import sublime
import sublime_plugin
import os
import re
import bisect
import imp

def reload(mod):
    n = mod.__file__
    if n[-1] == 'c':
        n = n[:-1]
    globals()[mod.__name__] = imp.load_source(mod.__name__, n)
completioncommon = imp.load_source("completioncommon", os.path.join(os.path.dirname(os.path.abspath(__file__)), "sublimecompletioncommon/completioncommon.py"))
completioncommon.reload(completioncommon)

try:
    import SublimeJava.classopener as classopener
except:
    import classopener
imp.reload(classopener)


class SublimeJavaDotComplete(completioncommon.CompletionCommonDotComplete):
    pass


class SublimeJavaCompletion(completioncommon.CompletionCommon):
    def __init__(self):
        super(SublimeJavaCompletion, self).__init__("SublimeJava.sublime-settings", os.path.dirname(os.path.abspath(__file__)))
        self.regex = [
            (re.compile(r"\[I([,)}]|$)"), r"int[]\1"),
            (re.compile(r"\[F([,)}]|$)"), r"float[]\1"),
            (re.compile(r"\[Z([,)}]|$)"), r"boolean[]\1"),
            (re.compile(r"\[B([,)}]|$)"), r"byte[]\1"),
            (re.compile(r"\[C([,)}]|$)"), r"char[]\1"),
            (re.compile(r"\[S([,)}]|$)"), r"short[]\1"),
            (re.compile(r"\[J([,)}]|$)"), r"long[]\1"),
            (re.compile(r"\[D([,)}]|$)"), r"double[]\1"),
            (re.compile(r"\[\L?([\w\./]+)(;)?"), r"\1[]")]

    def show_error(self, msg):
        if self.get_setting("sublimejava_no_visual_errors", False):
            print(msg)
        else:
            sublime.error_message(msg + "\n\nDisable visual error message dialogues with setting:\nsublimejava_no_visual_errors: true")

    def get_packages(self, data, thispackage, type):
        packages = re.findall(r"(?:^|\n)[ \t]*import[ \t]+(.*);", data)
        packages.append("java.lang.*")
        packages.append("")  # for int, boolean, etc
        for package in packages:
            idx = type.find(".")
            if idx == -1:
                idx = len(type)
            subtype = type[:idx]
            if re.search("[\.\$]{1}%s$" % subtype, package):
                # Explicit imports, we want these to have the highest
                # priority when searching for the absolute type, so
                # insert them at the top of the package list.
                # Both the .* version and not is added so that
                # blah.<searchedForClass> and blah$<searchedForClass>
                # is tested
                add = package[:-(len(subtype)+1)]
                packages.insert(0, add + ".*")
                packages.insert(1, add)
                break
        packages.append(thispackage + ".*")
        return packages

    def get_cmd(self):
        classpath = self.get_setting("sublimejava_classpath", ["."])
        newclasspath = []
        window = sublime.active_window()
        for path in classpath:
            newclasspath.append(self.expand_path(path, window))
        classpath = newclasspath
        classpath.insert(0, ".")
        classpath = os.pathsep.join(classpath)
        return "java -classpath \"%s\" SublimeJava" % classpath

    def is_supported_language(self, view):
        if view.is_scratch() or not self.get_setting("sublimejava_enabled", True):
            return False
        language = self.get_language(view)
        return language == "java" or language == "jsp"

    def sub(self, regex, sub, data):
        olddata = data
        data = regex.sub(sub, data)
        while data != olddata:
            olddata = data
            data = regex.sub(sub, data)
        return data

    def fixnames(self, data):
        for regex, replace in self.regex:
            data = self.sub(regex, replace, data)
        return data

    def return_completions(self, comp):
        ret = []
        for display, insert in comp:
            ret.append((self.fixnames(display), self.fixnames(insert)))
        return super(SublimeJavaCompletion, self).return_completions(ret)

    def get_class_under_cursor(self):
        view = sublime.active_window().active_view()
        data = view.substr(sublime.Region(0, view.size()))
        word = view.substr(view.word(view.sel()[0].begin()))
        return self.find_absolute_of_type(data, data, word)

    def get_possible_imports(self, classname):
        imports = []

        if classname is not None:
            stdout = self.run_completion("-possibleimports;;--;;%s" % classname)
            imports = sorted(stdout.split("\n")[:-1])

        return imports


comp = SublimeJavaCompletion()


class SublimeJava(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        return comp.on_query_completions(view, prefix, locations)

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "sublimejava.dotcomplete":
            return comp.get_setting(key.replace(".", "_"), True)
        elif key == "sublimejava.supported_language":
            return comp.is_supported_language(view)
        else:
            return comp.on_query_context(view, key, operator, operand, match_all)


MSG_NO_CLASSES_FOUND = "No classes found to import for name %s."
MSG_ALREADY_IMPORTED = "Class %s has either already been imported, is \
in the current package, or is in the default package."

RE_IMPORT = "import( static)? ([\w\.]+)\.([\w]+|\*);"
RE_PACKAGE = "package ([\w]+.)*\w+;"
RE_IMPORT_SECTION = "(^import[^;\n]+;[^\n]*\n)+"


class ExecuteImportJavaCommand(sublime_plugin.TextCommand):
    def run(self, edit, full_classname):
        insert_point = 0
        newlines_prepend = 0
        newlines_append = 1

        import_classname = full_classname.replace("$", ".")
        import_statement = "import %s;" % (import_classname)
        all_imports_region = self.view.find_all(RE_IMPORT)

        if len(all_imports_region) > 0:
            all_imports = sorted([(region, self.view.substr(region)) for region in all_imports_region], key=lambda a: a[1])
            only_imports = [a[1] for a in all_imports]

            # The following logic is used to find the right spot to insert the import statement at if there are multiple
            # separate import groups. See discussion in #62
            pos = bisect.bisect_left(only_imports, import_statement)

            def score_string(a, b):
                score = 0
                for i in range(min(len(a), len(b))):
                    score += a[i] == b[i]
                return score

            if pos == len(all_imports) or (pos > 0 and \
                    score_string(import_statement, all_imports[pos-1][1]) > score_string(import_statement, all_imports[pos][1])):
                # Insert after
                insert_point = all_imports[pos-1][0].b
                newlines_prepend = 1
                newlines_append = 0
            else:
                # Insert before
                insert_point = all_imports[pos][0].a
                newlines_prepend = 0
                newlines_append = 1
        else:
            package_declaration_region = self.view.find(RE_PACKAGE, 0)

            if package_declaration_region is not None:
                insert_point = package_declaration_region.b
                newlines_prepend = 2
                newlines_append = 0

        import_statement = "%s%s%s" % ("\n" * newlines_prepend,
                                               import_statement,
                                               "\n" * newlines_append)

        self.view.insert(edit, insert_point, import_statement)

        if comp.get_setting("sublimejava_organize_imports", True):
            self.view.run_command("organize_java_imports")


class ImportJavaClassCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        classname = view.substr(view.word(view.sel()[0].begin()))

        if comp.get_class_under_cursor():
            comp.show_error(MSG_ALREADY_IMPORTED % classname)
            return

        imports = comp.get_possible_imports(classname)

        def do_import(index):
            if index != -1:
                self.view.run_command("execute_import_java", {"full_classname": imports[index]})

        if len(imports) > 0:
            view.window().show_quick_panel(imports, do_import)
        else:
            comp.show_error(MSG_NO_CLASSES_FOUND % classname)


class OrganizeJavaImportsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sections = self.view.find_all(RE_IMPORT_SECTION, 0)
        section_imports = [self.view.substr(section) for section in sections]
        for i in range(len(sections)):
            # TODO pass func to organize as java, 3rd party, project
            imports = section_imports[i][:-1].split("\n")
            imports.sort()
            imports = "\n".join(imports) + "\n"

            self.view.replace(edit, sections[i], imports)


class OpenJavaSourceCommand(sublime_plugin.WindowCommand):

    def run(self, under_cursor=False):
        classopener.JavaSourceOpener(comp,
                                     self.window.active_view(),
                                     under_cursor).show()


class OpenJavaDocCommand(sublime_plugin.WindowCommand):

    def run(self, under_cursor=False):
        classopener.JavaDocOpener(comp,
                                  self.window.active_view(),
                                  under_cursor).show()
