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
import os.path
import re
try:
    from sublimecompletioncommon import completioncommon
    reload(completioncommon)
except:
    def hack(func):
        # If there's a sublime.error_message before a window is open
        # on Windows 7, it appears the main editor window
        # is never opened...
        class hackClass:
            def __init__(self, func):
                self.func = func
                self.try_now()

            def try_now(self):
                if sublime.active_window() == None:
                    sublime.set_timeout(self.try_now, 500)
                else:
                    self.func()
        hackClass(func)

    def showError():
        sublime.error_message("""\
Unfortunately SublimeJava currently can't be installed \
via Package Control at the moment. Please see http://www.github.com/quarnster/SublimeJava \
for more details.""")
    hack(showError)


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
        return "java -classpath %s SublimeJava" % classpath

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
