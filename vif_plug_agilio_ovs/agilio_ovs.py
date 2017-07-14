# Derived from os-vif/vif_plug_ovs/ovs.py
#
# Copyright (C) 2017 Netronome Systems, Inc.
# Copyright (C) 2011 Midokura KK
# Copyright (C) 2011 Nicira, Inc
# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# import re
# import sys

from os_vif import objects
from os_vif.objects.vif import VIFPortProfileOVSRepresentor

from vif_plug_agilio_ovs import agilio_linux_net as linux_net

from vif_plug_ovs import constants
from vif_plug_ovs import exception
from vif_plug_ovs import ovs
# from vif_plug_ovs.ovs import OvsPlugin

# from vif_plug_ovs import linux_net

# PCIADDR_RE = re.compile("/([^/]+)\.sock$")


class AgilioOvsPlugin(ovs.OvsPlugin):
    """An OS-VIF plugin that extends the OVS plugin with Agilio support.

    """

    def describe(self):
        return objects.host_info.HostPluginInfo(
            plugin_name="agilio_ovs",
            vif_info=[
                objects.host_info.HostVIFInfo(
                    vif_object_name=objects.vif.VIFVHostUser.__name__,
                    min_version="1.0",
                    max_version="1.0"),
                objects.host_info.HostVIFInfo(
                    vif_object_name=objects.vif.VIFHostDevice.__name__,
                    min_version="1.0",
                    max_version="1.0"),
            ])

    def _create_vif_port(self, vif, vif_name, instance_info, **kwargs):
        # Note: calls agilio_linux_net in stead of linux_net
        mtu = self._get_mtu(vif)
        linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif_name,
            vif.port_profile.interface_id,
            vif.address, instance_info.uuid,
            mtu,
            timeout=self.config.ovs_vsctl_timeout,
            **kwargs)

    def _update_vif_port(self, vif, vif_name):
        # Note: calls agilio_linux_net in stead of linux_net
        mtu = self._get_mtu(vif)
        linux_net.update_ovs_vif_port(vif_name, mtu)

    def _plug_agilio_passthrough(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.ensure_ovs_bridge(
            vif.network.bridge, constants.OVS_DATAPATH_SYSTEM)
        linux_net.agilio_claim_passthrough(
            vif.port_profile.vif_name,
            vif.address,
            vif.dev_address)
        linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif.port_profile.vif_name,
            vif.port_profile.interface_id,
            vif.address,
            instance_info.uuid,
            self.config.network_device_mtu,
            timeout=self.config.ovs_vsctl_timeout)

    def _plug_agilio_forwarder(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.ensure_ovs_bridge(vif.network.bridge,
                                    constants.OVS_DATAPATH_SYSTEM)
        linux_net.agilio_claim_forwarder(
            vif.vif_name,
            vif.address,
            vif.port_profile.dev_address,
            vhupath=vif.path)
        linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif.vif_name,
            vif.port_profile.interface_id,
            vif.address,
            instance_info.uuid,
            self.config.network_device_mtu,
            timeout=self.config.ovs_vsctl_timeout,
            virtio_forwarder=1)

    def plug(self, vif, instance_info):
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if not isinstance(vif.port_profile, VIFPortProfileOVSRepresentor):
            raise exception.WrongPortProfile(
                profile=vif.port_profile.__class__.__name__)
        if isinstance(vif, objects.vif.VIFHostDevice):
            self._plug_agilio_passthrough(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFVHostUser):
            self._plug_agilio_forwarder(vif, instance_info)

    def _unplug_agilio_passthrough(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.delete_ovs_vif_port(
            vif.network.bridge,
            vif.port_profile.vif_name,
            timeout=self.config.ovs_vsctl_timeout)
        linux_net.agilio_release(vif.dev_address)

    def _unplug_agilio_forwarder(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.delete_ovs_vif_port(
            vif.network.bridge,
            vif.vif_name,
            timeout=self.config.ovs_vsctl_timeout)
        linux_net.agilio_release(
            vif.port_profile.dev_address,
            vhupath=vif.path)

    def unplug(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if not isinstance(vif.port_profile, VIFPortProfileOVSRepresentor):
            raise exception.WrongPortProfile(
                profile=vif.port_profile.__class__.__name__)

        if isinstance(vif, objects.vif.VIFVHostUser):
            self._unplug_agilio_forwarder(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFHostDevice):
            self._unplug_agilio_passthrough(vif, instance_info)
