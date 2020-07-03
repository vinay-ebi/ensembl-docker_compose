{% block qrp %}
  {
    "handover_token": {{ handover_token }},
    "src_uri": {{ src_uri }},
    "status": "true",
    "ENS_VERSION": {{ ENS_VERSION }},
    "EG_VERSION": {{ EG_VERSION}},
    "contact": {{ contact }},
    "comment": {{ comment }},
    "user": "{{user}}",
    
    {% block pipeline %}
          
    {% endblock pipeline %}
 }
{% endblock qrp %}
