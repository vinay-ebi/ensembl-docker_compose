FROM python:3.5.6
WORKDIR /app
COPY ../productionservices/ensembl-prodinf-srv/requirements.txt /app/requirements.txt
COPY ../productionservices/gunicorn_config.py /app/gunicorn_config.py
RUN pip install -r requirements.txt


ENV PYTHONPATH="/app/ensembl-prodinf-core:/app/ensembl-prodinf-srv"

WORKDIR /app/ensembl-prodinf-srv

CMD ["celery", "-A", "ensembl_prodinf.event_tasks worker" , "-l",  "info", "-Q", "qrp", "-n", "qrp-handover@%%h"]
