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







-start all services at once using docker compose
------------------

stop local mysql server : sudo service mysql stop ;

stop local rabbitmq server : sudo rabbitmqctl stop

-elstic search fails with error : max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]
--------------
sudo sysctl -w vm.max_map_count=262144


-create directores in side repo dir for persistance mysql and rabbitmq data storage
-----------
mkdir mysqldata data

-copy ssh keys
----

copy files  id_rsa,  id_rsa.pub and known_hosts from ~/.ssh into application folder  productionservices/ssh which will be  used by radical saga to launch pipeline into farm


-set user name for radical saga 
-----
set below mentioned values accoringly for ur usage in  file ensembl-prodinf-core/ensembl/production/workflow/monitor.py

```
        self.REMOTE_HOST = args.get('remote_host', "noah-login-01")
        self.ADDRESS = args.get('address', '10.7.95.60')  # Address of your server
        self.USER = args.get('user', 'vinay')  # Username
```


-docker-compose:
----
docker-compose up --build

-set the index for elastic search :
-----------------------------
 curl -XPUT http://localhost:9400/pipelines

-deploy into local kubernetes :
-------------------------------
kompose up --push-image=false   (this flag avoid to push image to remote dockerhub repos)


-Apps urls:
----------

- Rabbitmq: localhost:15672
- elasticsearch: localhost:9400
- production srv: localhost:500
- mysql: localhost:3306
- celery flower: localhost:5555 (two celery workers will be started for monitor and qrp queues)
 

-Payload:
-----------
- http://localhost:5000/qrp/submit/job

```{
  "spec": {
    "handover_token": "test_handover_token_11",
    "src_uri": "mysql://vinay:<set password>@<host>:<port>/anopheles_gambiae_core_48_101_4",
    "contact": "vinay@ebi.ac.uk",
    "comment": "testing handover for qrp",
    "hive_url": "mysql://vinay:<password>@<host>:3306/",
    "user": "vinay",
    "progress_complete": 3,
    "progress_total": 3,
    "EG_VERSION" : "100",
    "ENS_VERSION": "100",
    "staging_uri": "mysql://<user>:<password>@<host>:<port>/",
    "tgt_uri": "mysql://<user>:<password>@<host>:<port>/anopheles_gambiae_core_48_101_4"
  },
  "event": {}
}
```

-Check the results:
-----------------
- http://localhost:5000/qrp/jobs
- http://localhost:5000/qrp/jobs?format=json

