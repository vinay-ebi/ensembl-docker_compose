Automate Production Pipeline For QRP
====================================

- create docker image for:
  - python flask wtih ensembl-production-srv and ensembl-production-core
  - rabbitmq
  - mysqlserver
  - celery workers
  - elastic search


-Production app:
------
cd productionservices

sudo docker build -t qrptest . 

sudo docker run -it -v $(pwd)/ensembl-prodinf-core:/app/ensembl-prodinf-core -v $(pwd)/ensembl-prodinf-srv:/app/ensembl-prodinf-srv --network=host -p 80:80 qrptest /bin/bash

-docker-compose:
----
docker-compose up --build
