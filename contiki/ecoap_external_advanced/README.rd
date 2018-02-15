inside examples/contiki
RUN AGENT
python agent.py --config config/agent_configs/agent_taisc_ipv6.yaml

RUN CONTROLLER
python ecoap_external_advanced/global_cp.py --config config/localhost/global_cp_config.yaml --nodes config/localhost/nodes.yaml --event_config_file ecoap_external_advanced/event_settings.csv --measurements ecoap_external_advanced/measurement_settings.yaml
