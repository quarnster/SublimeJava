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
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Member;
import java.net.URL;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.*;


public class SublimeJava
{
    private static <T extends Method> String[] getCompletion(T m, String filter)
    {
        String str = m.getName();
        if (!str.startsWith(filter))
            return null;
        str += "(";
        String ins = str;
        int count = 1;
        for (Class c2 : m.getParameterTypes())
        {
            if (count > 1)
            {
                str += ", ";
                ins += ", ";
            }
            String n = c2.getName();
            str += n;
            ins += "${"+count + ":" + n + "}";
            count++;
        }
        str += ")\t" + m.getReturnType().getName();
        ins += ")";
        return new String[] {str, ins};
    }
    private static <T extends Field> String[] getCompletion(T f, String filter)
    {
        String str = f.getName();
        if (!str.startsWith(filter))
            return null;

        String rep = str + "\t" + f.getType().getName();
        return new String[] {rep, str};
    }
    private static String[] getCompletion(Class clazz, String filter)
    {
        return new String[] {clazz.getSimpleName() + "\tclass", clazz.getSimpleName()};
    }
    private static <T> String[] getCompletion(T t, String filter)
    {
        if (t instanceof Method)
        {
            return getCompletion((Method)t, filter);
        }
        else if (t instanceof Field)
        {
            return getCompletion((Field)t, filter);
        }
        else if (t instanceof Class)
        {
            return getCompletion((Class)t, filter);
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

    private static <T> void dumpCompletions(T[] arr, String filter)
    {
        for (T t : arr)
        {
            String[] completion = getCompletion(t, filter);
            if (completion == null)
            {
                continue;
            }
            System.out.println(completion[0] + sep + completion[1]);
        }
    }

    private static boolean getReturnType(Field[] fields, String filter)
    {
        for (Field f : fields)
        {
            if (filter.equals(f.getName()))
            {
                System.out.println("" + f.getType().getName());
                return true;
            }
        }
        return false;
    }

    private static boolean getReturnType(Method[] methods, String filter)
    {
        for (Method m : methods)
        {
            if (filter.equals(m.getName()))
            {
                System.out.println("" + m.getReturnType().getName());
                return true;
            }
        }
        return false;
    }
    private static boolean getReturnType(Class[] classes, String filter)
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
                    String args[] = cmd.split(" ");
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
                        else if (args[0].equals("-separator"))
                        {
                            System.out.println(System.getProperty("path.separator"));
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
                                    Class c = Class.forName(classname);
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
                                while (!found && classname.indexOf('.') != -1)
                                {
                                    int idx = classname.lastIndexOf('.');
                                    classname = classname.substring(0, idx) + "$" + classname.substring(idx+1);
                                    try
                                    {
                                        System.err.println("Testing for: " + classname);
                                        Class c = Class.forName(classname);
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
                            continue;
                        }
                        if (args.length < 2)
                            continue;
                        Class<?> c = Class.forName(args[1]);
                        String filter = "";
                        if (args.length >= 3)
                            filter = args[2];
                        if (args[0].equals("-complete"))
                        {
                            dumpCompletions(c.getFields(), filter);
                            dumpCompletions(c.getDeclaredFields(), filter);
                            dumpCompletions(c.getMethods(), filter);
                            dumpCompletions(c.getDeclaredMethods(), filter);
                            dumpCompletions(c.getClasses(), filter);
                            dumpCompletions(c.getDeclaredClasses(), filter);
                        }
                        else if (args[0].equals("-returntype"))
                        {
                            if (getReturnType(c.getDeclaredFields(), filter))
                                continue;
                            if (getReturnType(c.getDeclaredMethods(), filter))
                                continue;
                            if (getReturnType(c.getDeclaredClasses(), filter))
                                continue;
                            if (getReturnType(c.getFields(), filter))
                                continue;
                            if (getReturnType(c.getMethods(), filter))
                                continue;
                            if (getReturnType(c.getClasses(), filter))
                                continue;
                        }
                    }
                    catch (ClassNotFoundException x)
                    {
                    }
                }
                catch (Exception e)
                {
                    System.err.println("Exception caught: " + e.getMessage());
                    e.printStackTrace(System.err);
                }
            }
        }
        catch (Exception e)
        {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace(System.err);
        }
    }
}
