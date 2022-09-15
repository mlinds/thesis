for d in ./*.svg;
do 
echo " $(basename $d)"
inkscape -D --export-latex -o "$(basename $d).pdf" "$d"
done