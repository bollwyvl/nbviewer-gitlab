FROM nbviewer_nbviewer:latest

USER root
WORKDIR /srv/nbviewer-gitlab

ADD . /srv/nbviewer-gitlab/
RUN python setup.py develop

WORKDIR /srv/nbviewer
USER nobody
CMD ["python", "-m", "nbviewer", "--port=8080"]
