/*
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
*/
import java.lang.reflect.*;
import java.net.*;
import java.io.*;
import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.jar.*;

public class SublimeJava
{

    private static String getInstancedType(Class<?> c, String gen, String ret, String[] templateParam)
    {
        if (gen.startsWith("class "))
            gen = gen.substring("class ".length());
        {
            // This is a bit odd, and I'm not sure it's correct. Seems "gen" returns an absolute
            // class path that isn't correct. I've only seen this for the specific class that is
            // in the repro case of issue #26, but it probably happens elsewhere too so could
            // have to be tweaked.
            //
            // In short, gen will list Tests.Tests$Foo whereas the correct type would be just
            // Tests$Foo
            String pat = "(\\w+\\.)+"+ Pattern.quote(ret);
            Pattern p = Pattern.compile(pat);
            Matcher m = p.matcher(gen);
            if (m.find())
            {
                gen = m.replaceAll(Matcher.quoteReplacement(ret));
            }
        }

        if (!gen.equals(ret))
        {
            boolean set = false;
            TypeVariable<?> tv[] = c.getTypeParameters();
            for (int i = 0; i < tv.length && i < templateParam.length; i++)
            {
                String pat = "((^|[<,\\s])+)" + tv[i].getName() +  "(([,\\s>]|$)+)";
                Pattern p = Pattern.compile(pat);
                Matcher m = p.matcher(gen);
                if (m.find())
                {
                    gen = m.replaceAll(Matcher.quoteReplacement(m.group(1) + templateParam[i] + m.group(3)));
                }
            }
            ret = gen;
        }
        return ret;
    }

    private static String[] getCompletion(Method m, String filter, String[] templateParam)
    {
        String str = m.getName();
        if (!str.startsWith(filter))
            return null;
        str += "(";
        String ins = str;
        int count = 1;
        Type[] generic = m.getGenericParameterTypes();
        Class[] normal = m.getParameterTypes();
        for (int i = 0; i < normal.length; i++)
        {
            if (count > 1)
            {
                str += ", ";
                ins += ", ";
            }

            String gen = generic[i].toString();
            String ret = normal[i].getName();
            ret = getInstancedType(m.getDeclaringClass(), gen, ret, templateParam);
            str += ret;
            ins += "${"+count + ":" + ret.replace("$", "\\$") + "}";
            count++;
        }
        str += ")\t" + getInstancedType(m.getDeclaringClass(), m.getGenericReturnType().toString(), m.getReturnType().getName(), templateParam);
        ins += ")";
        return new String[] {str, ins};
    }
    private static String[] getCompletion(Field f, String filter, String[] templateArgs)
    {
        String str = f.getName();
        if (!str.startsWith(filter))
            return null;

        String rep = str + "\t" + getInstancedType(f.getDeclaringClass(), f.getGenericType().toString(), f.getType().getName(), templateArgs);
        return new String[] {rep, str};
    }
    private static String[] getCompletion(Class clazz, String filter, String[] templateArgs)
    {
        return new String[] {clazz.getSimpleName() + "\tclass", clazz.getSimpleName()};
    }
    private static <T> String[] getCompletion(T t, String filter, String[] templateArgs)
    {
        if (t instanceof Method)
        {
            return getCompletion((Method)t, filter, templateArgs);
        }
        else if (t instanceof Field)
        {
            return getCompletion((Field)t, filter, templateArgs);
        }
        else if (t instanceof Class)
        {
            return getCompletion((Class)t, filter, templateArgs);
        }
        return null;
    }
    private static final String sep = ";;--;;";

    private static String getClassname(String pack, String clazz)
    {
        if (pack.endsWith(".*"))
        {
            return pack.substring(0, pack.length()-2) + "." + clazz;
        }
        else if (pack.length() != 0)
        {
            return pack + "$" + clazz;
        }
        return clazz;
    }

    private static final int STATIC_BIT = 1 << 0;
    private static final int PRIVATE_BIT = 1 << 1;
    private static final int PROTECTED_BIT = 1 << 2;
    private static final int PUBLIC_BIT = 1 << 3;

    private static <T> int getModifiers(T t)
    {
        int modifiers = 0;
        if (t instanceof Method)
        {
            Method m = (Method) t;
            modifiers = m.getModifiers();
        }
        else if (t instanceof Field)
        {
            Field f = (Field) t;
            modifiers = f.getModifiers();
        }
        else if (t instanceof Class)
        {
            Class c = (Class) t;
            modifiers = c.getModifiers();
        }
        int returnvalue = 0;
        if (Modifier.isStatic(modifiers))
            returnvalue |= STATIC_BIT;
        if (Modifier.isPrivate(modifiers))
            returnvalue |= PRIVATE_BIT;
        if (Modifier.isProtected(modifiers))
            returnvalue |= PROTECTED_BIT;
        if (Modifier.isPublic(modifiers))
            returnvalue |= PUBLIC_BIT;
        return returnvalue;
    }

    private static <T> void dumpCompletions(T[] arr, String filter, String[] templateArgs)
    {
        for (T t : arr)
        {
            String[] completion = getCompletion(t, filter, templateArgs);
            if (completion == null)
            {
                continue;
            }
            System.out.println(completion[0] + sep + completion[1] + sep + getModifiers(t));
        }
    }

    private static boolean getReturnType(Field[] fields, String filter, String templateParam[])
    {
        for (Field f : fields)
        {
            if (filter.equals(f.getName()))
            {
                String gen = f.getGenericType().toString();
                String ret = f.getType().getName();
                ret = getInstancedType(f.getDeclaringClass(), gen, ret, templateParam);
                System.out.println("" + ret);
                return true;
            }
        }
        return false;
    }

    private static boolean getReturnType(Method[] methods, String filter, String templateParam[])
    {
        for (Method m : methods)
        {
            if (filter.equals(m.getName()))
            {
                String gen = m.getGenericReturnType().toString();
                String ret = m.getReturnType().getName();
                ret = getInstancedType(m.getDeclaringClass(), gen, ret, templateParam);
                System.out.println("" + ret);
                return true;
            }
        }
        return false;
    }
    private static boolean getReturnType(Class[] classes, String filter, String templateParam[])
    {
        for (Class clazz : classes)
        {
            if (filter.equals(clazz.getSimpleName()))
            {
                System.out.println(clazz.getName());
                return true;
            }
        }
        return false;
    }

    private static boolean isPackage(String packageName)
        throws IOException
    {
        Package p = Package.getPackage(packageName);
        if (p != null)
            return true;

        packageName = packageName.replace(".", File.pathSeparator);

        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        for (String s : getClasspathEntries())
        {
            URL url = classLoader.getResource(s + File.pathSeparator + packageName);
            if (url != null)
                return true;
            else
                url = classLoader.getResource(s);
            if (url == null)
                continue;

            String filename = URLDecoder.decode(url.getFile(), "UTF-8");

            if (url.getProtocol().equals("jar"))
            {
                filename = filename.substring(5, filename.indexOf("!"));

                JarFile jf = new JarFile(filename);
                Enumeration<JarEntry> entries = jf.entries();
                while (entries.hasMoreElements())
                {
                    String name = entries.nextElement().getName();
                    if (name.startsWith(packageName))
                    {
                        return true;
                    }
                }
            }
            else
            {
                File folder = new File(filename + File.pathSeparator + packageName);
                if (folder.exists())
                    return true;
            }
        }
        return false;
    }

    private static final String CLASS_FILE_NAME_RE = "(?:$|/)?(\\w+).class";
    private static final String CLASS_FULL_NAME_IN_PKG_RE = "(\\w+(\\.|$){1})+\\w+";
    private static final String DIGITS_CLASS_NAME_RE = "\\d+";
    private static final String SUBLIME_JAVA_CLASS_RE = "SublimeJava";

    private static Pattern classFileNamePattern, classFullNameInPackagePattern, digitsClassnamePattern, sublimeJavaClassPattern;
    static
    {
        classFileNamePattern = Pattern.compile(CLASS_FILE_NAME_RE);
        classFullNameInPackagePattern = Pattern.compile(CLASS_FULL_NAME_IN_PKG_RE);
        digitsClassnamePattern = Pattern.compile(DIGITS_CLASS_NAME_RE);
        sublimeJavaClassPattern = Pattern.compile(SUBLIME_JAVA_CLASS_RE);
    }

    private static String getImport(String classFileName, String searchClass)
    {
        Matcher classnameMatcher = classFileNamePattern.matcher(classFileName);
        if (classnameMatcher.find())
        {
            String classname = classnameMatcher.group(1);
            if ((searchClass != null && searchClass.equals(classname)) ||
                (searchClass == null && !digitsClassnamePattern.matcher(classname).matches()))
            {
                String fullClassname = classFileName.replace("\\","/").replace("/", ".").replace(".class", "");
                if (fullClassname.startsWith("."))
                {
                    fullClassname = fullClassname.substring(1);
                }
                // Only allow class as import if it has a package. Classes in
                // default package are not allowed to be imported.
                if (classFullNameInPackagePattern.matcher(fullClassname).matches()){
                    return fullClassname;
                }
            }
        }
        return null;
    }

    private static String[] getClasspathEntries()
    {
        Set<String> paths = new HashSet<String>();
        paths.add("java/lang/String.class");
        for (String s : System.getProperty("java.class.path").split(System.getProperty("path.separator")))
        {
            paths.add(s);
        }
        return paths.toArray(new String[0]);
    }

    private static URL getUrlFromClasspathEntry(ClassLoader classLoader, String classpathEntry, String packagePath)
    {
        URL url = null;
        if (classpathEntry.endsWith(".class"))
            url = classLoader.getResource(classpathEntry);
        else
        {
            String path = "file://" + new File(classpathEntry).getAbsolutePath();
            if (path.endsWith(".jar"))
            {
                path = "jar:" + path + "!/" + packagePath;
            }
            else
            {
                path += "/" + packagePath;
            }
            try
            {
                System.err.println("path: " + path);
                url = new URL(path);
            }
            catch (Exception e)
            {}
        }
        return url;
    }

    private static void printImportsNotInJar(File current, File root, String classname, Set<String> possibleImports)
    {
        Matcher classnameMatcher = classFileNamePattern.matcher(current.getName());
        if (current.isFile() && classnameMatcher.matches())
        {
            if (classname == null || classname.equals(classnameMatcher.group(1)))
            {
                String classFileName = current.getAbsolutePath().substring(root.getAbsolutePath().length());
                printPossibleImport(getImport(classFileName, classname), possibleImports);
            }
        }
        else if (current.isDirectory())
        {
            for (File file : current.listFiles())
            {
                printImportsNotInJar(file, root, classname, possibleImports);
            }
        }
    }

    private static void getPossibleImports(String classname)
        throws IOException
    {
        Set<String> possibleImports = new HashSet<String>();
        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        for (String s : getClasspathEntries())
        {
            URL url = getUrlFromClasspathEntry(classLoader, s, "");
            if (url == null)
                continue;
            System.err.println("s: " + s);
            System.err.println("url: " + url);

            String filename = URLDecoder.decode(url.getFile(), "UTF-8");
            if (url.getProtocol().equals("jar"))
            {
                filename = filename.substring(5, filename.indexOf("!"));

                JarFile jf = new JarFile(filename);
                Enumeration<JarEntry> entries = jf.entries();
                while (entries.hasMoreElements())
                {
                    String imp = getImport(entries.nextElement().getName(), classname);
                    printPossibleImport(imp, possibleImports);

                }
            }
            else
            {
                File folder = new File(filename);
                printImportsNotInJar(folder, folder, classname, possibleImports);
            }
        }
    }

    private static void printPossibleImport(String fullClassname, Set<String> possibleImports)
    {
        if (fullClassname != null && possibleImports.add(fullClassname))
            System.out.println(fullClassname);
    }

    private static void completePackage(String packageName)
        throws IOException
    {
        String packagePath = packageName.replace(".", "/");

        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        for (String s : getClasspathEntries())
        {
            URL url = getUrlFromClasspathEntry(classLoader, s, packagePath);
            if (url == null)
                continue;
            System.err.println("s: " + s);
            System.err.println("packagename: " + packagePath);
            System.err.println("url: " + url);

            String filename = URLDecoder.decode(url.getFile(), "UTF-8");
            Set<String> packages = new HashSet<String>();
            if (url.getProtocol().equals("jar"))
            {
                filename = filename.substring(5, filename.indexOf("!"));

                JarFile jf = new JarFile(filename);
                Enumeration<JarEntry> entries = jf.entries();
                while (entries.hasMoreElements())
                {
                    String name = entries.nextElement().getName();
                    if (name.startsWith(packagePath))
                    {
                        name = name.substring(packagePath.length()+1);
                        int idx = name.indexOf('/');
                        if (idx != -1)
                        {
                            name = name.substring(0, idx);
                            if (packages.add(name))
                            {
                                System.out.println(name + "\tpackage" + sep + name);
                            }
                            continue;
                        }
                        name = name.replace(".class", "").replace('/', '.');
                        System.out.println(name + "\tclass" + sep + name);
                    }
                }
            }
            else
            {
                File folder = new File(filename);
                File[] files = folder.listFiles();
                if (files == null)
                    continue;
                for (File f : files)
                {
                    String name = f.getName();
                    if (name.endsWith(".class"))
                    {
                        name = name.substring(0, name.length()-6);
                        System.out.println(name + "\tclass" + sep + name);
                    }
                    else if (f.isDirectory())
                    {
                        System.out.println(name + "\tpackage" + sep + name);
                    }
                }
            }
        }
    }

    private static <T extends Throwable> void reportError(T e)
    {
        String type = "Error";
        if (e instanceof Exception)
            type = "Exception";
        String cn = e.getClass().getName();
        String msg = e.getMessage();
        if (msg == null)
            msg = "";

        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        e.printStackTrace(pw);

        String stack = sw.toString();
        if (stack.indexOf(cn) == -1 && msg.indexOf(cn) == -1)
        {
            stack = cn + "\n" + stack;
        }
        if (stack.indexOf(msg) != -1)
            msg = "";
        System.err.println(type + ": " + msg + " " + stack + "\n" + ";;--;;");
    }

    private static class MyClassLoader
    extends ClassLoader
    {
        MyClassLoader()
        {
            super(MyClassLoader.class.getClassLoader());
        }
        public Class<?> loadClass(String name)
            throws ClassNotFoundException
        {
            // First we use the superclass to get a hold of the class.
            Class c = super.loadClass(name);
            DataInputStream s = null;
            try
            {
                // However, as the default class loader does not reload classes that have changed
                // we use the handle to the class to try and get it's actual .class definition
                // which we then define in THIS ClassLoader subclass. Hence: dynamic class reloading :)
                String path = ClassLoader.getSystemResource(c.getName().replaceAll("\\.", "/") + ".class").getFile();
                File f = new File(path);
                if (!f.exists()) {
                    return c;
                }
                int len = (int) f.length();
                byte[] data = new byte[len];
                s = new DataInputStream(new FileInputStream(f));
                s.readFully(data);
                return defineClass(name, data, 0, len);
            }
            catch (Exception e)
            {
                reportError(e);
            }
            finally
            {
                if (s != null)
                    try { s.close(); } catch (Exception e) {}
            }
            throw new ClassNotFoundException();
        }
    }

    private static Class<?> loadClass(String name)
        throws ClassNotFoundException
    {
        // See http://stackoverflow.com/questions/4285855/difference-betweeen-loading-a-class-using-classloader-and-class-forname/7099453#7099453
        // for an explanation of using a class loader vs Class.forName
        ClassLoader cls = new MyClassLoader();
        return cls.loadClass(name);
    }

    public static void main(String... unusedargs)
    {
        try
        {
            BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
            boolean first = true;
            while (true)
            {
                try
                {
                    if (!first)
                        // Just to indicate that there's no more output from the command and we're ready for new input
                        System.out.println(";;--;;");
                    first = false;
                    String cmd = in.readLine();
                    if (cmd == null)
                        break;
                    String args[] = cmd.split(";;--;;");
                    System.err.println(args.length);
                    for (int i = 0; i < args.length; i++)
                    {
                        System.err.println(args[i]);
                    }

                    try
                    {
                        if (args[0].equals("-quit"))
                        {
                            System.err.println("quitting upon request");
                            return;
                        }
                        else if (args[0].equals("-possibleimports"))
                        {
                            String arg = null;
                            if (args.length > 1)
                            {
                                arg = args[1];
                            }
                            getPossibleImports(arg);
                            continue;
                        }
                        else if (args[0].equals("-findclass"))
                        {
                            String line = null;
                            ArrayList<String> packages = new ArrayList<String>();
                            try
                            {
                                while ((line = in.readLine()) != null)
                                {
                                    if (line.compareTo(sep) == 0)
                                        break;
                                    packages.add(line);
                                }
                            }
                            catch (Exception e)
                            {
                            }
                            boolean found = false;
                            for (String pack : packages)
                            {
                                try
                                {
                                    String classname = getClassname(pack, args[1]);
                                    System.err.println("Testing for: " + classname);
                                    Class c = loadClass(classname);
                                    System.out.println("" + c.getName());
                                    found = true;
                                    break;
                                }
                                catch (Exception e)
                                {
                                }
                            }
                            if (found)
                                continue;
                            // Still haven't found anything, so try to see if it's an internal class
                            for (String pack : packages)
                            {
                                String classname = getClassname(pack, args[1]);
                                while (!found && classname != null && classname.indexOf('.') != -1)
                                {
                                    int idx = classname.lastIndexOf('.');
                                    classname = classname.substring(0, idx) + "$" + classname.substring(idx+1);
                                    try
                                    {
                                        System.err.println("Testing for: " + classname);
                                        Class c = loadClass(classname);
                                        System.out.println("" + c.getName());
                                        found = true;
                                        break;
                                    }
                                    catch (Exception e)
                                    {
                                    }
                                }
                                if (found)
                                    break;
                            }
                            // Nothing yet.. Is it a package by any chance?
                            if (isPackage(args[1]))
                                System.out.println(args[1]);
                            continue;
                        }
                        if (args.length < 2)
                            continue;
                        Class<?> c = loadClass(args[1]);
                        String filter = "";
                        if (args.length >= 3)
                        {
                            filter = args[2];
                            if (filter.equals(sep))
                            {
                                filter = "";
                            }
                        }
                        int len = args.length - 3;
                        if (len < 0)
                            len = 0;
                        String[] templateParam = new String[len];
                        for (int i = 0; i < len; i++)
                        {
                            templateParam[i] = args[i+3];
                        }
                        if (args[0].equals("-complete"))
                        {
                            dumpCompletions(c.getFields(), filter, templateParam);
                            dumpCompletions(c.getDeclaredFields(), filter, templateParam);
                            dumpCompletions(c.getMethods(), filter, templateParam);
                            dumpCompletions(c.getDeclaredMethods(), filter, templateParam);
                            dumpCompletions(c.getClasses(), filter, templateParam);
                            dumpCompletions(c.getDeclaredClasses(), filter, templateParam);
                        }
                        else if (args[0].equals("-returntype"))
                        {
                            if (getReturnType(c.getDeclaredFields(), filter, templateParam))
                                continue;
                            if (getReturnType(c.getDeclaredMethods(), filter, templateParam))
                                continue;
                            if (getReturnType(c.getDeclaredClasses(), filter, templateParam))
                                continue;
                            if (getReturnType(c.getFields(), filter, templateParam))
                                continue;
                            if (getReturnType(c.getMethods(), filter, templateParam))
                                continue;
                            if (getReturnType(c.getClasses(), filter, templateParam))
                                continue;
                        }
                    }
                    catch (ClassNotFoundException x)
                    {
                        // Maybe it's a package then?
                        if (args[0].equals("-complete"))
                        {
                            completePackage(args[1]);
                        }
                        else if (args[0].equals("-returntype"))
                        {
                            String name = args[1] + "." + args[2];
                            if (isPackage(name))
                                System.out.println(name);
                        }
                    }
                }
                catch (Error e)
                {
                    reportError(e);
                }
                catch (Exception e)
                {
                    reportError(e);
                }
            }
        }
        catch (Exception e)
        {
            reportError(e);
        }
    }
}
