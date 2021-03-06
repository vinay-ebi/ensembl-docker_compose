Overview
========

The healthcheck service provides a set of endpoints to allow `healthchecks <https://github.com/Ensembl/ensj-healthcheck>`_ to be run on specified Ensembl MySQL databases. These endpoints can be used "self-service" by members of the team to check their own code, or programatically by components of the Ensembl Production infrastructure.

Implementation
==============

The endpoints are defined in `hc_app.py <hc_app.py>`_ flask app. They use the
`ensembl-prodinf-core <https://github.com/Ensembl/ensembl-prodinf-core>`_ libraries for scheduling and monitoring Hive jobs. The endpoints use the `HiveInstance <https://github.com/Ensembl/ensembl-prodinf-core/blob/master/ensembl_prodinf/hive.py>`_
class to submit copy jobs to a hive database generated from `Bio::EnsEMBL::Healthcheck::Pipeline::RunStandaloneHealthchecksParallel_conf <https://github.com/Ensembl/ensj-healthcheck/blob/master/perl/Bio/EnsEMBL/Healthcheck/Pipeline/RunStandaloneHealthchecksParallel_conf.pm>`_
which should then be handled by a running beekeeper instance. For more information on how hive is used by this service, please see `hive.rst <https://github.com/Ensembl/ensembl-prodinf-core/blob/master/docs/hive.rst>`_.

After the flask app has been started consult ``/apidocs`` for complete endpoint documentation.

Optionally, when jobs are submitted an email address can be supplied for an email to be sent to when the job completes or fails. This is as described in `README_celery_email.rst <./README_celery_email.rst>`_.

Note that currently the service runs the Java healthchecks from `<https://github.com/Ensembl/ensj-healthcheck>`_ but in future should use the new Perl datachecks from `<https://github.com/Ensembl/ensembl-datacheck>`_. This implementation would need to change in the Hive pipeline specified.

Installation
============

First clone this repo

.. code-block:: bash

  git clone https://github.com/Ensembl/ensembl-prodinf-srv
  cd ensembl-prodinf-srv


To install Python requirements using pip:

.. code-block:: bash

  pip install -r requirements.txt

You can do this on a shared pyenv environment, or per user with the ``--user`` option.

You can also install ``ensembl_prodinf`` from git or by adding an existing install to PYTHONPATH.

.. code-block:: bash

  PYTHONPATH=[install_dir]/ensembl-prodinf/ensembl-prodinf-core

Hive Setup
==========

Before you can use the HC endpoint, you need a beekeeper running the pipeline defined by ``Bio::EnsEMBL::Healthcheck::Pipeline::RunStandaloneHealthchecksParallel_conf``. This also needs a Java jar. To build and initiate the pipeline:

.. code-block:: bash

  ssh ebi-cli-001
  git clone https://github.com/Ensembl/ensj-healthcheck
  cd ensj-healthcheck
  mvn clean install
  JAR=$HOME/.m2/repository/org/ensembl/ensj-healthcheck/1.0.0/ensj-healthcheck-1.0.0-jar-with-dependencies.jar
  SRV=your_mysql_command_wrapper
  init_pipeline.pl Bio::EnsEMBL::Healthcheck::Pipeline::RunStandaloneHealthchecksParallel_conf $($SRV details hive) -hc_jar $JAR

Next, run the ``beekeeper.pl`` supplied by the output with the arguments ``--keep_alive -sleep 0.5``. This ensures the hive runs continually, picking up new jobs as they are submitted.

Please note that beekeeper need to run from an ebi-cli node to be able to send jobs to the farm.
Also please make sure the hive run from the ensj-healthcheck directory or org.ensembl.healthcheck.testcase.eg_core.ProteinTranslation will fail as the script won't be found.
The current hive version compatible with this service is 2.5

Configuration
=============

There are two configuration files you need to have copies of locally:

.. code-block:: bash

  mkdir instance
  cp hc_config.py.instance_example instance/hc_config.py
  cp celery_app_config.py.example celery_app_config.py


Edit them as required. ``hc_config.py`` must contain a URL for the hive MySQL instance described above.

.. code-block:: bash

  HIVE_URI='mysql://myuser:mypass@myhost:3306/standalone_hc_hive'
  DEBUG = True
  HOST = '0.0.0.0'
  PORT = 5001
  HC_LIST_FILE = 'hc_list.json'
  HC_GROUPS_FILE = 'hc_groups.json'

An example of the json files can be found in ``hc_list.json.example`` and ``hc_groups.json.example``.

These files can be automatically generated by running the following scripts:
.. code-block:: bash
  git clone https://github.com/Ensembl/ensj-healthcheck
  cd ensj-healthchecks
  mvn clean package
  java -classpath "./target/healthchecks-jar-with-dependencies.jar" org.ensembl.ListHealthchecks -c group -o hc_groups.json
  java -classpath "./target/healthchecks-jar-with-dependencies.jar" org.ensembl.ListHealthchecks -c test -o hc_list.json

You can also leave ``instance/hc_config.py`` empty and use the defaults in ``hc_config.py`` or override using environment variables.

The following environment variables are supported by the config:

* ``HIVE_URI`` - mysql URI of HC hive database (required)
* ``HIVE_ANALYSIS`` - name of analysis for submitting new jobs to the hive (not usually needed to be changed)
* ``CELERY_BROKER_URL`` - URL of Celery broker
* ``CELERY_RESULT_BACKEND`` - URl of Celery backend
* ``HC_LIST_FILE`` - path to JSON file containing list of hcs
* ``HC_GROUPS_FILE`` - path to JSON file containing list of hc groups

Running Celery
==============
See `README_celery_email.rst <./README_celery_email.rst>`_ about how to run a Celery worker to monitor jobs.

Running
=======

To start the main application as a standalone Flask application:

.. code-block:: bash

  export FLASK_APP=hc_app.py
  cd ensembl-prodinf-srv
  flask run --port 5001 --host 0.0.0.0


or to start the main application as a standalone using gunicorn with 4 threads:

.. code-block:: bash

  pyenv activate ensprod_inf
  cd ensembl-prodinf-srv
  gunicorn -w 4 -b 0.0.0.0:5001 hc_app:app


Note that for production, a different deployment option should be used as the standalone flask app can only serve one request at a time.

There are multiple options, described at:

* http://flask.pocoo.org/docs/0.12/deploying/wsgi-standalone/
* http://flask.pocoo.org/docs/0.12/deploying/uwsgi/

To use a standalone gunicorn server with 4 worker threads:

.. code-block:: bash

  gunicorn -w 4 -b 0.0.0.0:5001 hc_app:app


Client
======

A simple Python REST client for this app can be found in `hc_client.py <https://github.com/Ensembl/ensembl-prodinf-core/blob/master/ensembl_prodinf/hc_client.py>`_.


Using Docker
============

To build a Docker image:

.. code-block:: bash

  docker build -t ensembl_prodinf/hc_app -f Dockerfile.hc .


To run your Docker image against a specified hive, exposing the REST service on port 4001 e.g.:

.. code-block:: bash

  docker run -p 127.0.0.1:4001:4001 --env HIVE_URI='mysql://user:pwd@localhost:3306/my_hive_db' ensembl_prodinf/hc_app


Environment variables should be supplied as arguments to the run command as shown in the example above.
