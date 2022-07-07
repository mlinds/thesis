test_site_folders:= $(wildcard ./data/test_sites/*)

netcdffiles:= $(wildcard $(sitedir)/ATL03/processed_ATL03_*.nc)
current_dir = $(shell pwd)
figures_images := $(wildcard ./document/figures/*)
tables:=$(wildcard ./document/tables/*)
python_module_files = $(wildcard ./code/atl_module/*)
xelatex_compile_command := latexmk -xelatex -pdf -synctex=1 -interaction=nonstopmode -file-line-error _report.tex
docker_run:=  docker run --rm -v "$(current_dir)"/document:/workdir -w /workdir texlive/texlive 
chapter_files:=$(wildcard ./document/chapters/*.tex)

.PHONY: python_module figures
all: ./document/_report.pdf 

test_sites:
	echo $(test_site_folders)

python_module: $(python_module_files)

# figures code depends on the module files - if they change, rerun figures
./code/figures.py: python_module

figures: ./code/figures.py 
	echo rebuilding figures
	cd code && python figures.py

# if any of the chapters is or the report texfile is newer than the pdf, compile pdf
./document/_report.pdf: ./document/_report.tex $(chapter_files) $(figures_images) figures
	# $(MAKE) figures
	echo compiling latex doc
	$(docker_run) $(xelatex_compile_command)


	


	