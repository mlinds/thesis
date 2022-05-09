files := $(wildcard *.tex)
document: $(files)
	docker run --rm -v "$(pwd)":/home  texlive/texlive cd /home 
