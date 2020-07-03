{% extends "base.tpl" %}

{% block pipeline %}

  {% block core %}

    {% block flow %}
      "flow" : [

      {% block coreStat %}
        {
           "PipelineName": "CoreStats",  
           "PipeConfig": "Bio::EnsEMBL::Production::Pipeline::PipeConfig::CoreStatistics_conf",
           "PipeParams": {
           "params":{
             "-registry": "registry.reg",
             "-species" : "{{species if species != None }}",
             "-division": "{{division if division != None }}",
             "-antispecies": "{{coreStat_antispecies if coreStat_antispecies != None}}"     
           },
           "arguments":[],
         }        
        }     
     {% endblock coreStat %}
      ], 
    {% endblock flow %}
  
  {% endblock core %}

{% endblock pipeline %}
