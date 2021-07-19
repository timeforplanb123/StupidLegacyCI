from nornir.core.plugins.connections import ConnectionPluginRegister
from nornir_jinja2.plugins.tasks import template_file
from nornir_cli.common_commands import _info
from nornir_netmiko import netmiko_send_command, netmiko_send_config
import re


def cli(ctx):
    def _change_trap_info(task):
        ConnectionPluginRegister.auto_register()

        cmd = task.run(
            task=netmiko_send_command,
            name="get source address",
            command_string=f"disp ip int br | i {task.host.hostname}",
        )

        regex = r"(?P<source>\S+)\s+\d+(.\d+){3}.*"

        match = re.search(regex, cmd.result)
        task.host["source"] = match.group("source")

        template = task.run(task=template_file, path=".", template="snmp.j2")

        # print(template.result)

        task.run(
            task=netmiko_send_config,
            name="configure snmp",
            config_commands=template.result,
            cmd_verify=False,
            exit_config_mode=False,
        )

    task = ctx.run(task=_change_trap_info, on_failed=True)
    _info(ctx, task)
