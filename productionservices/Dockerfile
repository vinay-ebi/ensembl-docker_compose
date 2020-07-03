FROM python:3.5.6
WORKDIR /app
COPY ./ensembl-prodinf-srv/requirements.txt /app/requirements.txt
COPY ./gunicorn_config.py /app/gunicorn_config.py
COPY ./ssh /root/.ssh
RUN pip install -r requirements.txt


ENV PYTHONPATH="/app/ensembl-prodinf-core:/app/ensembl-prodinf-srv"
EXPOSE 4001

WORKDIR /app/ensembl-prodinf-srv

RUN ssh-keyscan -H 10.7.95.60 >> ~/.ssh/known_hosts
RUN ssh-keyscan -H 172.22.10.207 >> ~/.ssh/known_hosts
#RUN ssh-keyscan -H noah-login-01 >> ~/.ssh/known_hosts

ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/app/gunicorn_config.py", "-b", "0.0.0.0:5000", "event_app:app"]

#-b 0.0.0.0:7013 -n vinay_qrp_app -c /app/gunicorn_config.py event_app:app
