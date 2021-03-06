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

from os_vif import objects
from os_vif.objects.vif import VIFPortProfileOVSRepresentor

from vif_plug_agilio_ovs import agilio_linux_net

from vif_plug_ovs import constants
from vif_plug_ovs import exception
from vif_plug_ovs import ovs


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
        mtu = self._get_mtu(vif)
        agilio_linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif_name,
            vif.port_profile.interface_id,
            vif.address, instance_info.uuid,
            mtu,
            timeout=self.config.ovs_vsctl_timeout,
            **kwargs)

    def _update_vif_port(self, vif, vif_name):
        pass

    def _plug_agilio_passthrough(self, vif, instance_info):
        agilio_linux_net.ensure_ovs_bridge(
            vif.network.bridge, constants.OVS_DATAPATH_SYSTEM)
        agilio_linux_net.agilio_claim_passthrough(
            vif.port_profile.representor_name,
            vif.address,
            vif.port_profile.representor_address)
        agilio_linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif.port_profile.representor_name,
            vif.port_profile.interface_id,
            vif.address,
            instance_info.uuid,
            self.config.network_device_mtu,
            timeout=self.config.ovs_vsctl_timeout)

    def _plug_agilio_forwarder(self, vif, instance_info):
        agilio_linux_net.ensure_ovs_bridge(vif.network.bridge,
                                           constants.OVS_DATAPATH_SYSTEM)
        agilio_linux_net.agilio_claim_forwarder(
            vif.port_profile.representor_name,
            vif.address,
            vif.port_profile.representor_address,
            vhupath=vif.path)
        agilio_linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif.port_profile.representor_name,
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
        agilio_linux_net.delete_ovs_vif_port(
            vif.network.bridge,
            vif.port_profile.representor_name,
            timeout=self.config.ovs_vsctl_timeout)
        agilio_linux_net.agilio_release(
            vif.port_profile.representor_address)

    def _unplug_agilio_forwarder(self, vif, instance_info):
        agilio_linux_net.delete_ovs_vif_port(
            vif.network.bridge,
            vif.vif_name,
            timeout=self.config.ovs_vsctl_timeout)
        agilio_linux_net.agilio_release(
            vif.port_profile.representor_address,
            vhupath=vif.path)

    def unplug(self, vif, instance_info):
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if not isinstance(vif.port_profile, VIFPortProfileOVSRepresentor):
            raise exception.WrongPortProfile(
                profile=vif.port_profile.__class__.__name__)

        if isinstance(vif, objects.vif.VIFVHostUser):
            self._unplug_agilio_forwarder(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFHostDevice):
            self._unplug_agilio_passthrough(vif, instance_info)
