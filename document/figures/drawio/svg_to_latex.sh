for d in ./*.svg;
do 
echo " $(basename $d)"
inkscape --export-latex -o "$(basename $d).tex" "$d"
done