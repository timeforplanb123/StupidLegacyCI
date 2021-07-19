import os
import yaml
from typing import List, Dict, Tuple, Optional, Iterable, Iterator, Sequence, Union, Any
from dataclasses import field
from pydantic.dataclasses import dataclass
import itertools
from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.inventory import ConnectionOptions
from nornir.core.task import Task
from nornir_netmiko.tasks import netmiko_send_config
from nornir_cli.common_commands import _info


def read_yaml_file(filename: str) -> Dict[Any, Any]:
    with open(filename, "r") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as err:
            print(err)

# SAVE = ["q", "save", "Y"]
try:
    SAVE = os.environ["SAVE"].split(",")
except KeyError:
    SAVE = ["q", "save", "Y"]


def get_configs() -> Iterator[Sequence[Tuple[str]]]:
    for root, dirs, files in os.walk("previous"):
        for f in files:
            if "yaml" in f:
                # files from previous and last commit
                print(f"{root}/{f}")
                print(f"{root.replace('previous/', '')}/{f}")

                old_params = read_yaml_file(f"{root}/{f}") or {
                    "configs": {"": {"params": {"": []}}}
                }
                print(old_params)

                new_params = read_yaml_file(f"{root.replace('previous/', '')}/{f}")
                print(new_params)
                yield old_params, new_params, f


def generator(old_params: Any, new_params: Any) -> Iterator[Sequence[Tuple[str]]]:
    for old_param, new_param in itertools.zip_longest(
        old_params["configs"], new_params["configs"]
    ):
        yield old_param, new_param


@dataclass
class StupidCI:
    """The  StupidCI object is the point of entry.

    It has parameter validation using pydantic.

    After instantiating the StupiCI you can run methods for delete, compare or deploy
    some commands. You can pass parameters like lists of commands or script to each method.

    **Attributes**:
    :param no_params: params of the previous commit from yaml file

    :param yes_params: params of the last commit from yaml file

    :param compare_script: path to script for compare params with compare method. It's
    optional. You can use lists of commands or script

    :param no_commands: commands for deleting parameters. List or empty list

    :param yes_commands: commands for deploy new parameters from last commit. List or
    empty list

    :param delete_commands: commands for deleting all parameters. List or str. It's
    optional

    :param config_commands: commands for deployment configuration. List or str. It's
    optional

    :param iter_no_commands: service parameter in __post_init__

    :param iter_yes_commands: service parameter in __post_init__

    """

    no_params: Dict[str, List[Optional[str]]]
    yes_params: Dict[str, List[Optional[str]]]
    compare_script: str = ""
    no_commands: List[List[Optional[str]]] = field(default_factory=list)
    yes_commands: List[List[Optional[str]]] = field(default_factory=list)
    delete_commands: Union[List[Optional[str]], str] = ""
    config_commands: Union[List[Optional[str]], str] = ""
    iter_no_commands: Iterable[List[Optional[str]]] = field(init=False, repr=False)
    iter_yes_commands: Iterable[List[Optional[str]]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.iter_no_commands = iter(self.no_commands)
        self.iter_yes_commands = iter(self.yes_commands)

    def delete(self) -> Union[List[Optional[str]], str]:
        if not any(self.yes_params.values()):
            return self.delete_commands

    def config(self) -> Union[List[Optional[str]], str]:
        if not any(self.no_params.values()) and all(self.yes_params.values()):
            return self.config_commands

    def compare(self) -> Union[List[Optional[str]], str]:
        final_commands = []
        if list(self.no_params.items()) != list(self.yes_params.items()):
            if self.compare_script:
                return self.compare_script
            elif self.no_commands and self.yes_commands:
                for k, v in self.yes_params.items():
                    no_cmd = ",".join(next(self.iter_no_commands))
                    yes_cmd = ",".join(next(self.iter_yes_commands))
                    if v != self.no_params[k]:
                        no_cmd = (
                            no_cmd.format(*self.no_params[k])
                            if self.no_params[k]
                            else ""
                        )
                        yes_cmd = yes_cmd.format(*v) if v else ""
                        final_commands.extend((no_cmd + "," + yes_cmd).split(","))
        return final_commands

    def deploy(self, f: str = "", commands: Union[List[str], str] = "") -> None:
        if not commands:
            print("Empty commands")
            return

        self.nr = InitNornir(config_file="config.yaml")
        exec(f"nr_filter_object = self.nr.filter({f})")
        self.nr_filter_object = locals()["nr_filter_object"]


        for host, value in self.nr_filter_object.inventory.hosts.items():
            value.username = os.environ["DC_USERNAME"]
            value.password = os.environ["DC_PASSWORD"]
            for k, v in self.yes_params.items():
                self.nr_filter_object.inventory.hosts[host][k] = v

        if isinstance(commands, list):
            # commands after comparing the parameters from previous and last commit
            print(commands)
            task = self.nr_filter_object.run(
                task=netmiko_send_config,
                name="processing",
                config_commands=commands + SAVE,
            )
            _info(self.nr_filter_object, task)
        elif isinstance(commands, str):
            # commands(script) after comparing the parameters from previous and last commit
            print(commands)
            t = __import__(f"{commands[:-3]}", None, None, ["cli"])
            t.cli(self.nr_filter_object)


if __name__ == "__main__":

    for old_params, new_params, f in get_configs():
        for old_param, new_param in generator(old_params, new_params):

            stupid_ci = StupidCI(
                no_params=old_params["configs"][old_param]["params"],
                yes_params=new_params["configs"][new_param]["params"],
                **new_params[new_param]["commands"],
            )

            commands = stupid_ci.delete() or stupid_ci.config() or stupid_ci.compare()

            try:

                stupid_ci.deploy(f=new_params["filter"], commands=commands)
            except KeyError:
                stupid_ci.deploy(f=f"name='{f[:-5]}'", commands=commands)
