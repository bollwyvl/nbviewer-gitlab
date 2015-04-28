FROM nbviewer_nbviewer:latest

USER root
ADD . /srv/nbviewer-gitlab
WORKDIR /srv/nbviewer-gitlab
RUN python setup.py install

WORKDIR /srv/nbviewer
USER nobody
CMD ["python", "-m", "nbviewer", "--port=8080"]