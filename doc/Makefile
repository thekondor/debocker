all: debocker.8 debocker.8.html

debocker.8.html: debocker.8.ronn
	ronn --html debocker.8.ronn --manual=debocker --organization=Debian

debocker.8: debocker.8.ronn
	ronn --roff debocker.8.ronn --manual=debocker --organization=Debian

push-html: debocker.8.html
	scp debocker.8.html debocker-server:debocker/index.html

clean:
	rm -f debocker.8 debocker.8.html

.PHONY: push-html
