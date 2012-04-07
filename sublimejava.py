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
import sqlite3
import time
import os
import threading


scriptdir = os.path.dirname(os.path.abspath(__file__))
enableCache = True


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


def run_java(cmd, stdin=None):
    proc = subprocess.Popen(
        cmd,
        cwd=scriptdir,
        shell=True,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE
        )
    stdout, stderr = proc.communicate(stdin)
    return stdout

javaseparator = run_java("java -classpath . SublimeJava -separator").strip()


def get_cmd():
    classpath = get_setting("sublimejava_classpath", ["."])
    classpath.append(".")
    classpath = javaseparator.join(classpath)
    return "java -classpath %s SublimeJava" % classpath


class Cache:
    def __init__(self):
        self.cache = None
        self.cacheCursor = None
        self.ready = False
        self.doThread()

    def doThread(self):
        t = threading.Thread(target=self.createDB, args=(get_cmd(),))
        t.start()
        sublime.status_message("SublimeJava: Creating Cache")

    def createDB(self, cmd):
        self.cache = sqlite3.connect("%s/cache.db" % scriptdir)
        self.cacheCursor = self.cache.cursor()
        self.cacheCursor.execute("""create table if not exists source(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            lastmodified TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        self.cacheCursor.execute("""create table if not exists type(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            sourceId INTEGER,
            FOREIGN KEY(sourceId) REFERENCES source(id))""")
        self.cacheCursor.execute(
        """create table if not exists member(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typeId INTEGER,
            returnTypeId INTEGER,
            field_or_method INTEGER,
            flags INTEGER,
            insertionText TEXT,
            displayText TEXT,
            FOREIGN KEY(typeId) REFERENCES type(id),
            FOREIGN KEY(returnTypeId) REFERENCES type(id) )""")
        # Cache a few random classes
        startupcache = ["java.lang.String",
                        "java.lang.System",
                        "java.io.BufferedReader",
                        "java.util.Vector",
                        "java.net.HttpURLConnection",
                        "javax.swing.table.JTableHeader",
                        "android.opengl.GLSurfaceView",
                        "javax.microedition.khronos.egl.EGL10",
                        "android.opengl.GLES20"
                        ]
        for item in startupcache:
            if self.get_typeid(item) == None:
                self.cache_class(item, cmd)
        self.cacheCursor.close()
        self.cache.close()
        self.cache = None
        self.cacheCursor = None
        sublime.set_timeout(self.openDB, 0)

    def openDB(self):
        self.cache = sqlite3.connect("%s/cache.db" % scriptdir)
        self.cacheCursor = self.cache.cursor()
        self.ready = True

    def clear(self):
        if self.ready:
            self.ready = False
            self.cacheCursor.close()
            self.cache.close()
            os.remove("%s/cache.db" % scriptdir)
            self.doThread()

    def is_ready(self):
        return self.ready

    def get_sourceid(self, sourcename):
        sql = "select id from source where name='%s'" % sourcename
        self.cacheCursor.execute(sql)
        id = self.cacheCursor.fetchone()
        if id == None:
            self.cacheCursor.execute("insert into source (name) values ('%s')" % sourcename)
            self.cache.commit()
            self.cacheCursor.execute(sql)
            id = self.cacheCursor.fetchone()
        return id[0]

    def get_typeid(self, typename):
        sql = "select id from type where name='%s'" % typename
        self.cacheCursor.execute(sql)
        id = self.cacheCursor.fetchone()
        if id == None:
            return None
        return id[0]

    def display_status(self):
        sublime.status_message(self.status_text)

    def cache_class(self, absclass, cmd=None):
        if (self.get_cached_class_exists(absclass)):
            print "that class already exists!! : %s" % absclass
            return
        if cmd == None:
            cmd = get_cmd()
        stdout = run_java("%s -cache %s" % (cmd, absclass))
        lines = stdout.split("\n")[:-1]
        if len(lines) == 0:
            # couldn't find this class... just insert
            # a dummy entry for it
            sid = self.get_sourceid("unknown")
            self.cacheCursor.execute("""insert into type (name, sourceId) values ('%s', %d)""" % (absclass, sid))
            self.cache.commit()
            return
        #print lines[0]
        classname, sourcename = lines[0].split(";;--;;")
        self.status_text = "SublimeJava: Caching " + classname
        sublime.set_timeout(self.display_status, 0)

        sourceid = self.get_sourceid(sourcename)
        self.cacheCursor.execute("insert into type (name, sourceId) values ('%s', %d)" % (classname, sourceid))
        self.cache.commit()
        classId = self.get_typeid(classname)
        for line in lines[1:]:
            #print line
            membertype, returnType, flags, displayText, insertionText = line.split(";;--;;")
            membertype = int(membertype)
            flags = int(flags)

            if not self.get_cached_class_exists(returnType):
                self.cache_class(returnType, cmd)
            returnTypeId = self.get_typeid(returnType)

            self.cacheCursor.execute("""insert into member (typeId, returnTypeId, field_or_method, flags, insertionText, displayText) values (%d, %d, %d, %d, '%s', '%s')""" % (classId, returnTypeId, membertype, flags, insertionText, displayText))
            self.cache.commit()

    def get_cached_class_exists(self, classname):
        self.cacheCursor.execute("select * from type where name='%s' limit 1" % classname)
        return self.cacheCursor.fetchone() != None

    def complete(self, absolute_classname, prefix):
        id = self.get_typeid(absolute_classname)
        if id == None:
            cache.cache_class(absolute_classname)
            id = self.get_typeid(absolute_classname)

        self.cacheCursor.execute("select displayText, insertionText from member where typeId = %d and insertionText like '%s%%' order by insertionText" % (id, prefix))
        ret = self.cacheCursor.fetchall()
        if ret == None:
            return []
        return ret

    def get_return_type(self, absolute_classname, prefix):
        id = self.get_typeid(absolute_classname)
        if id == None:
            self.cache_class(absolute_classname)
            id = self.get_typeid(absolute_classname)
        self.cacheCursor.execute("select returnTypeId from member where typeId = %d and insertionText like '%s%%'" % (id, prefix))
        ret = self.cacheCursor.fetchone()
        if ret == None:
            return ""
        else:
            self.cacheCursor.execute("select name from type where id = %d" % ret[0])
            return self.cacheCursor.fetchone()[0]

cache = Cache()


class SublimeJavaClearCache(sublime_plugin.WindowCommand):
    def run(self):
        cache.clear()


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

    def __init__(self):
        self.cache_list = []

    def count_brackets(self, data):
        even = 0
        for i in range(len(data)):
            if data[i] == '{':
                even += 1
            elif data[i] == '}':
                even -= 1
        return even

    def find_type_of_variable(self, data, variable):
        if variable == "this":
            data = data[:data.rfind(variable)]
            idx = data.rfind("class")
            while idx != -1:
                count = self.count_brackets(data[idx:])
                if (count & 1) == 0:
                    return re.search("class\s*([^\s\{]+)([^\{]*\{)(.*)", data[idx:]).group(1)
                idx = data.rfind("class", 0, idx)
            return None
        print variable
        regex = "(\w[^( \t]+)[ \t]+%s[ \t]*(\;|,|\)|=|:).*$" % variable
        print regex
        match = re.search(regex, data, re.MULTILINE)
        if not match is None:
            match = match.group(1)
            if match.endswith("[]"):
                match = match[:-2]
            return match
        else:
            # Variable not defined in this class...
            return None

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
        if enableCache and cache.is_ready():
            packages.append("")  # for int, boolean, etc
            for package in packages:
                classname = package + "." + type
                if cache.get_cached_class_exists(classname):
                    return classname

        # Couldn't find a cached version, invoke java
        output = run_java("%s -findclass %s" % (get_cmd(), type), "\n".join(packages)).strip()
        if len(output) and enableCache and cache.is_ready():
            cache.cache_class(output)
        return output

    def complete_class(self, absolute_classname, prefix):
        if enableCache and cache.is_ready():
            return cache.complete(absolute_classname, prefix)
        else:
            stdout = run_java("%s -complete %s %s" % (get_cmd(), absolute_classname, prefix))
            ret = [tuple(line.split(";;--;;")) for line in stdout.split("\n")[:-1]]
            return sorted(ret, key=lambda a: a[0])

    def get_return_type(self, absolute_classname, prefix):
        ret = ""
        if enableCache and cache.is_ready():
            ret = cache.get_return_type(absolute_classname, prefix)
        else:
            stdout = run_java("%s -returntype %s %s" % (get_cmd(), absolute_classname, prefix))
            ret = stdout.strip()
        ret = re.search("(\[L)?([^;]+)", ret).group(2)
        return ret

    def on_query_completions(self, view, prefix, locations):
        bs = time.time()
        start = time.time()
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
            before = re.search("([^ \t]+)(\.)$", before).group(0)
            match = re.search("([^.\[]+)(\[\d+\])*(\.)(.*)", before)
            var = match.group(1)
            before = match.group(4)
            end = time.time()
            print "var is %s (%f ms) " % (var, (end-start)*1000)
            start = time.time()
            t = self.find_type_of_variable(data, var)
            end = time.time()
            print "type is %s (%f ms)" % (t, (end-start)*1000)
            if t is None:
                t = var
            start = time.time()
            t = self.find_absolute_of_type(data, t)
            end = time.time()
            print "absolute is %s (%f ms)" % (t, (end-start)*1000)

            start = time.time()
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
            end = time.time()
            print "finding what to complete took %f ms" % ((end-start) * 1000)

            print "completing %s.%s" % (t, prefix)
            start = time.time()
            ret = self.complete_class(t, prefix)
            end = time.time()
            print "completion took %f ms" % ((end-start)*1000)
            be = time.time()
            print "total %f ms" % ((be-bs)*1000)
            return ret

        print "here"
        return []

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "sublimejava.dotcomplete":
            return get_setting(key.replace(".", "_"), True)
