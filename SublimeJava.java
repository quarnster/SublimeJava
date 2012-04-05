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


public class SublimeJava
{
   public static void main(String... args)
    {
        try
        {
            if (args[0].equals("-findclass"))
            {
                String line = null;
                try
                {
                    BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
                    while ((line = in.readLine()) != null)
                    {
                        try
                        {
                            Class<?> c = Class.forName(line + "." + args[1]);
                            System.out.println("" + c.getName());
                            return;
                        }
                        catch (Exception e)
                        {
                        }
                    }
                }
                catch (Exception e)
                {
                }
                return;
            }
            Class<?> c = Class.forName(args[1]);
            String filter = "";
            if (args.length >= 3)
                filter = args[2];
            if (args[0].equals("-complete"))
            {
                for (Field f : c.getFields())
                {
                    String str = f.getName();
                    if (!str.startsWith(filter))
                        continue;

                    String rep = str + "\t" + f.getType().getName();
                    System.out.println(rep + ";" + str);
                }
                for (Method m : c.getMethods())
                {
                    String str = m.getName();
                    if (!str.startsWith(filter))
                        continue;
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
                    System.out.println(str + ";" + ins);
                }
            }
            else
            {
                for (Field f : c.getFields())
                {
                    if (filter.equals(c.getName()))
                    {
                        System.out.println("" + f.getType());
                        return;
                    }
                }
                for (Method m : c.getMethods())
                {
                    if (filter.equals(m.getName()))
                    {
                        System.out.println("" + m.getReturnType().getName());
                        return;
                    }
                }
            }
        }
        catch (ClassNotFoundException x)
        {
        }
    }
}
