import os
import pytest
from itertools import zip_longest
from typing import List, Dict, Tuple, Any
from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.plugins.connections import ConnectionPluginRegister
from nornir_netmiko import netmiko_send_command
from stupid_ci import get_configs


def get_snmp_params() -> List[Tuple[Dict[Any, Any], str, Dict[Any, Any]]]:

    results = []

    ConnectionPluginRegister.auto_register()

    # get yaml parameters
    for old_params, new_params, f in get_configs():
        try:
            if (
                old_params["configs"]["snmp"]["params"]
                != new_params["configs"]["snmp"]["params"]
            ):
                print("Start testing")
                try:
                    filtr = new_params["filter"]
                except KeyError:
                    filtr = f"name='{f[:-5]}'"

                nr = InitNornir(config_file="config.yaml")

                # exec in function can't create new vars
                lcls = locals()
                exec(f"nr_filter_object = nr.filter({filtr})", globals(), lcls)
                nr_filter_object = lcls["nr_filter_object"]

                for host, value in nr_filter_object.inventory.hosts.items():
                    value.username = os.environ["DC_USERNAME"]
                    value.password = os.environ["DC_PASSWORD"]
                # print(nr_filter_object.inventory.hosts)

                result = nr_filter_object.run(
                    task=netmiko_send_command,
                    name="compare snmp",
                    command_string="disp cur | i snmp",
                    use_textfsm=True,
                    textfsm_template="snmp.template",
                )

                current_snmp_params = old_params["configs"]["snmp"]["params"]

                results += list(
                    zip_longest(
                        [
                            result[host][0].result[0]
                            for host in nr_filter_object.inventory.hosts
                        ],
                        list(nr_filter_object.inventory.hosts),
                        [current_snmp_params],
                        fillvalue=current_snmp_params,
                    )
                )
        except KeyError:
            continue
    # print(results)
    return results


@pytest.mark.parametrize(
    "device_dict, host, cur_dict", get_snmp_params() or [("empty", "empty", "empty")]
)
def test_snmp(device_dict: Dict[str, str], host: str, cur_dict: Dict[str, str]) -> None:
    if "empty" in [device_dict, host, cur_dict]:
        print("No params for snmp test")
        return
    assert cur_dict == device_dict, f"TESTING FAILED on {host}"
