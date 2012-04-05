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
import re
import subprocess
import os.path


scriptdir = os.path.dirname(os.path.abspath(__file__))


def get_settings():
    return sublime.load_settings("SublimeJava.sublime-settings")


def get_setting(key, default=None):
    try:
        s = sublime.active_window().active_view().settings()
        if s.has(key):
            return s.get(key)
    except:
        pass
    return get_settings().get(key, default)


language_regex = re.compile("(?<=source\.)[\w+#]+")
member_regex = re.compile("(([a-zA-Z_]+[0-9_]*)|([\)\]])+)(\.)$")


def get_language(view):
    caret = view.sel()[0].a
    language = language_regex.search(view.scope_name(caret))
    if language == None:
        return None
    return language.group(0)


def is_supported_language(view):
    if view.is_scratch() or not get_setting("sublimejava_enabled", True):
        return False
    language = get_language(view)
    return language == "java"


class SublimeJavaDotComplete(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            self.view.insert(edit, region.end(), ".")
        caret = self.view.sel()[0].begin()
        line = self.view.substr(sublime.Region(self.view.word(caret-1).a, caret))
        if member_regex.search(line) != None:
            sublime.set_timeout(self.delayed_complete, 1)

    def delayed_complete(self):
        self.view.run_command("auto_complete")


class SublimeJava(sublime_plugin.EventListener):

    def find_type_of_variable(self, data, variable):
        print variable
        regex = "(\w[^( \t]+)[ \t]+%s[ \t]*(\;|,|\)|=|:).*$" % variable
        print regex
        match = re.search(regex, data, re.MULTILINE)
        if not match is None:
            return match.group(1)
        else:
            # Variable not defined in this class...
            return None

    def get_cmd(self):
        return "java -classpath .:%s SublimeJava" % get_setting("sublimejava_classpath", ".")

    def find_absolute_of_type(self, data, type):
        match = re.search("class %s" % type, data)
        if not match is None:
            # Class is defined in this file, return package of the file
            package = re.search("[ \t]*package (.*);", data)
            if package is None:
                return type
            return "%s.%s" % (package.group(1), type)
        regex = "[ \t]*import[ \t]+(.*)\.%s" % type
        match = re.search(regex, data)
        if not match is None:
            return "%s.%s" % (match.group(1), type)

        # Couldn't find the absolute name of this class so try to
        # see if it's in one of the packages imported as
        # "import package.*;", or in java.lang
        #
        packages = re.findall("[ \t]*import[ \t]+(.*)\.\*;", data)
        packages.append("java.lang")
        output = self.run_java("%s -findclass %s" % (self.get_cmd(), type), "\n".join(packages))
        return output.strip()

    def run_java(self, cmd, stdin=None):
        proc = subprocess.Popen(
            cmd,
            cwd=scriptdir,
            shell=True,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
            )
        stdout, stderr = proc.communicate(stdin)
        return stdout

    def complete_class(self, absolute_classname, prefix):
        stdout = self.run_java("%s -complete %s %s" % (self.get_cmd(), absolute_classname, prefix))
        ret = [tuple(line.split(";")) for line in stdout.split("\n")[:-1]]
        return sorted(ret, key=lambda a: a[0])

    def get_return_type(self, absolute_classname, prefix):
        stdout = self.run_java("%s -returntype %s %s" % (self.get_cmd(), absolute_classname, prefix))
        return stdout.strip()

    def on_query_completions(self, view, prefix, locations):
        if not is_supported_language(view):
            return []
        line = view.substr(sublime.Region(view.full_line(locations[0]).begin(), locations[0]))
        before = line
        if len(prefix) > 0:
            before = line[:-len(prefix)]
        if re.search("[ \t]+$", before):
            before = ""
        elif re.search("\.$", before):
            # Member completion
            data = view.substr(sublime.Region(0, locations[0]))
            before = re.search("[^ \t]+\.$", before).group(0)

            idx = before.find(".")
            var = before[:idx].strip()
            before = before[idx+1:]
            print "var is %s" % var
            t = self.find_type_of_variable(data, var)
            print "type is %s" % t
            t = self.find_absolute_of_type(data, t)

            print "absolute is %s" % (t)

            idx = before.find(".")
            while idx != -1:
                sub = before[:idx]
                idx2 = sub.find("(")
                if idx2 >= 0:
                    sub = sub[:idx2]

                n = self.get_return_type(t, sub)
                print "%s.%s = %s" % (t, sub, n)
                t = n
                before = before[idx+1:]
                idx = before.find(".")

            print "completing %s.%s" % (t, prefix)

            return self.complete_class(t, prefix)

        print "here"
        return []

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "sublimejava.dotcomplete":
            return get_setting(key.replace(".", "_"), True)
