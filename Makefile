all: clean release

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
	cd release && zip -r SublimeJava.sublime-package *
