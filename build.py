import json
import os
import sys
import subprocess
import tempfile

if __name__ == "__main__":
    def get(url):
        proc = subprocess.Popen("curl -s %s" % url, shell=True, stdout=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return stdout

    def run(cmd):
        assert(os.system(cmd) == 0)

    version = json.load(open('package.json'))['packages'][0]['platforms']['*'][0]['version']
    if not os.access("SublimeJava.class", os.R_OK) or os.path.getmtime("SublimeJava.java") > os.path.getmtime("SublimeJava.class"):
        run("javac -source 1.5 -target 1.5 SublimeJava.java")

    package_name = "SublimeJava-%s.sublime-package" % version


    for arg in sys.argv[1:]:
        if arg == "--create":
            run("rm -rf release")
            run("mkdir release")
            run("cp -r sublimecompletioncommon release")
            run("find . -maxdepth 1 -type f -exec cp {} release \;")
            run("find release -name \".git*\" | xargs rm -rf")
            run("find release -name \"*.pyc\" -exec rm {} \;")
            run("find release -name \"unittest*\" -exec rm -f {} \;")
            run("rm -f release/build.py")
            run("cd release && zip -r %s *" % package_name)
        elif arg == "--upload":
            current_downloads = json.loads(get("https://api.github.com/repos/quarnster/SublimeJava/downloads"))
            for download in current_downloads:
                assert download['name'] != package_name
            f = tempfile.NamedTemporaryFile()
            f.write("""{ "name": "%s", "size": %s}""" % (package_name, os.path.getsize("release/%s" % package_name)))
            f.flush()
            response = get("-X POST -d @%s -u quarnster https://api.github.com/repos/quarnster/SublimeJava/downloads" % f.name)
            f.close()
            args = """
-F "key=%s" \
-F "acl=%s" \
-F "success_action_status=201" \
-F "Filename=%s" \
-F "AWSAccessKeyId=%s" \
-F "Policy=%s" \
-F "Signature=%s" \
-F "Content-Type=%s" \
-F "file=@release/%s" \
https://github.s3.amazonaws.com/""" % (response["path"], response["acl"], response["name"], response["accesskeyid"], response["policy"], response["signature"], response["mime_type"], package_name)
            print get(args)




