test_site_folders:= $(wildcard ./data/test_sites/*)

netcdffiles:= $(wildcard $(sitedir)/ATL03/processed_ATL03_*.nc)
current_dir = $(shell pwd)
figures := $(wildcard ./document/figures/*)
tables:=$(wildcard ./document/tables/*)
xelatex_compile_command := latexmk -xelatex -pdf -synctex=1 -interaction=nonstopmode -file-line-error _report.tex
docker_run:=  docker run --rm -v "$(current_dir)"/document:/workdir -w /workdir texlive/texlive 
chapter_files:=$(wildcard ./document/chapters/*.tex)

all: ./document/_report.pdf ./document/_report.tex 

test_sites:
	echo $(test_site_folders)

figures: $(figures) 
	echo REDOING FIGURES




# if any of the chapters is or the report texfile is newer than the pdf, compile pdf
./document/_report.pdf: ./document/_report.tex $(chapter_files) 
	make figures
	echo compiling latex doc
	$(docker_run) $(xelatex_compile_command)


	


	