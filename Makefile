SCRIPT=import json; print json.load(open('package.json'))['packages'][0]['platforms']['*'][0]['version']
VERSION=$(shell python -c "$(SCRIPT)")

all: clean SublimeJava.class release

SublimeJava.class: SublimeJava.java
	javac -source 1.5 -target 1.5 SublimeJava.java

clean:
	rm -rf release

release:
	mkdir release
	cp -r sublimecompletioncommon release
	find . -maxdepth 1 -type f -exec cp {} release \;
	find release -name ".git*" | xargs rm -rf
	find release -name "*.pyc" -exec rm {} \;
	find release -name "unittest*" -exec rm -f {} \;
	rm -f release/Makefile
	cd release && zip -r SublimeJava-$(VERSION).sublime-package *
