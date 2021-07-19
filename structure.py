import os
import re
import pynetbox
from pynetbox.core.api import Api as api


def create_repo(nb: api, path: str, platform: str) -> None:
    # create regions and sites
    for obj in nb.dcim.sites.all():
        if obj.region:
            os.makedirs(f"{path}/{obj.region.slug}/{obj.slug}", exist_ok=True)

    # create .yaml for regions, site, devices
    for device in nb.dcim.devices.filter(platform=platform):
        site_name = device.site.slug
        for root, dirs, _ in os.walk(path):
            # create common.yaml files for regions and sites
            if ".git" not in root and not os.path.exists(f"{root}/common.yaml"):
                with open(f"{root}/common.yaml", "w"):
                    pass
            # create {device.name}.json for devices
            if site_name in dirs:
                if not os.path.exists(f"{root}/{site_name}/{device.name}.yaml"):
                    with open(f"{root}/{site_name}/{device.name}.yaml", "w"):
                        pass
                    # alternate, but not for mac
                    # os.mknod(f"{root}/{site_name}/{device.name}.yaml")


if __name__ == "__main__":
    create_repo(
        # change your_netbox_domain and your_netbox_token
        nb=pynetbox.api(
            "http://your_netbox_domain", token="your_netbox_token"
        ),
        path=os.getcwd(),
        # change the your_device_platform
        platform="your_device_platform",
    )
