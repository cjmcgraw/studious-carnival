FROM grafana/grafana:8.3.3

COPY provision-datasources.yml /etc/grafana/provisioning/datasources/defaults.yaml
COPY provision-dashboards.yml /etc/grafana/provisioning/dashboards/defaults.yaml
COPY *.json /etc/dashboards/eqbot/
