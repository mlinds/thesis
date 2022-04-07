docker run --rm -it --name thesis_container -e GRANT_SUDO=yes --user root --entrypoint /bin/bash -p 8888:8888 -v "C:\Users\maxli\OneDrive - Van Oord\Documents\thesis":/home/jovyan/work thesis-stack:latest


