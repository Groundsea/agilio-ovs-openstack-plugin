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

import re
import sys

from os_vif import objects
from os_vif.objects.vif import VIFPortProfileOpenVSwitch

from vif_plug_agilio_ovs import agilio_linux_net as linux_net

from vif_plug_agilio_ovs.objects.vif import VIFAgilioOpenVSwitch

from vif_plug_ovs import constants
from vif_plug_ovs import exception
from vif_plug_ovs import ovs
from vif_plug_ovs.ovs import OvsPlugin

# from vif_plug_ovs import linux_net

PCIADDR_RE = re.compile("/([^/]+)\.sock$")


class AgilioOvsPlugin(ovs.OvsPlugin):
    """An OS-VIF plugin that extends the OVS plugin with Agilio support.

    """

    def describe(self):
        return objects.host_info.HostPluginInfo(
            plugin_name="agilio_ovs",
            vif_info=[
                objects.host_info.HostVIFInfo(
                    vif_object_name=VIFAgilioOpenVSwitch.__name__,
                    min_version="1.0",
                    max_version="1.0"),
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

    def _plug_bridge(self, vif, instance_info):
        """Plug using hybrid strategy

        Create a per-VIF linux bridge, then link that bridge to the OVS
        integration bridge via a veth device, setting up the other end
        of the veth device just like a normal OVS port. Then boot the
        VIF on the linux bridge using standard libvirt mechanisms.
        """

        # Note: calls agilio_linux_net in stead of linux_net
        v1_name, v2_name = self.get_veth_pair_names(vif)

        linux_net.ensure_bridge(vif.bridge_name)

        mtu = self._get_mtu(vif)
        if not linux_net.device_exists(v2_name):
            linux_net.create_veth_pair(v1_name, v2_name, mtu)
            linux_net.add_bridge_port(vif.bridge_name, v1_name)
            linux_net.ensure_ovs_bridge(vif.network.bridge,
                                        constants.OVS_DATAPATH_SYSTEM)
            self._create_vif_port(vif, v2_name, instance_info)
        else:
            linux_net.update_veth_pair(v1_name, v2_name, mtu)
            self._update_vif_port(vif, v2_name)

    def _plug_vif_windows(self, vif, instance_info):
        """Create a per-VIF OVS port."""

        # Note: calls agilio_linux_net in stead of linux_net
        if not linux_net.device_exists(vif.id):
            linux_net.ensure_ovs_bridge(vif.network.bridge,
                                        constants.OVS_DATAPATH_SYSTEM)
            self._create_vif_port(vif, vif.id, instance_info)

    def _plug_agilio_passthrough(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        vif_name = OvsPlugin.gen_port_name("tap", vif.id)
        linux_net.ensure_ovs_bridge(
            vif.network.bridge, constants.OVS_DATAPATH_SYSTEM)
        linux_net.agilio_claim_passthrough(
            vif_name,
            vif.address,
            vif.dev_address)
        linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif_name,
            vif.port_profile.interface_id,
            vif.address, instance_info.uuid,
            self.config.network_device_mtu,
            timeout=self.config.ovs_vsctl_timeout)

    def _plug_agilio_forwarder(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.ensure_ovs_bridge(vif.network.bridge,
                                    constants.OVS_DATAPATH_SYSTEM)
        dev_address = PCIADDR_RE.search(vif.path).group(1)
        linux_net.agilio_claim_forwarder(
            vif.vif_name,
            vif.address,
            dev_address)
        linux_net.create_ovs_vif_port(
            vif.network.bridge,
            vif.vif_name,
            vif.port_profile.interface_id,
            vif.address, instance_info.uuid,
            self.config.network_device_mtu,
            timeout=self.config.ovs_vsctl_timeout,
            virtio_forwarder=1)

    def plug(self, vif, instance_info):
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if not isinstance(vif.port_profile, VIFPortProfileOpenVSwitch):
            raise exception.WrongPortProfile(
                profile=vif.port_profile.__class__.__name__)
        if isinstance(vif, objects.vif.VIFHostDevice):
            self._plug_agilio_passthrough(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFVHostUser):
            self._plug_agilio_forwarder(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFOpenVSwitch):
            if sys.platform != constants.PLATFORM_WIN32:
                linux_net.ensure_ovs_bridge(vif.network.bridge,
                                            constants.OVS_DATAPATH_SYSTEM)
            else:
                self._plug_vif_windows(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFBridge):
            if sys.platform != constants.PLATFORM_WIN32:
                self._plug_bridge(vif, instance_info)
            else:
                self._plug_vif_windows(vif, instance_info)

    def _unplug_bridge(self, vif, instance_info):
        """UnPlug using hybrid strategy

        Unhook port from OVS, unhook port from bridge, delete
        bridge, and delete both veth devices.
        """

        # Note: calls agilio_linux_net in stead of linux_net
        v1_name, v2_name = self.get_veth_pair_names(vif)

        linux_net.delete_bridge(vif.bridge_name, v1_name)

        linux_net.delete_ovs_vif_port(vif.network.bridge, v2_name,
                                      timeout=self.config.ovs_vsctl_timeout)

    def _unplug_vif_windows(self, vif, instance_info):
        """Remove port from OVS."""

        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.delete_ovs_vif_port(vif.network.bridge, vif.id,
                                      timeout=self.config.ovs_vsctl_timeout)

    def _unplug_agilio_passthrough(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        vif_name = OvsPlugin.gen_port_name("tap", vif.id)
        linux_net.delete_ovs_vif_port(
            vif.network.bridge,
            vif_name,
            timeout=self.config.ovs_vsctl_timeout)
        linux_net.agilio_release(vif_name)

    def _unplug_agilio_forwarder(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        linux_net.delete_ovs_vif_port(
            vif.network.bridge,
            vif.vif_name,
            timeout=self.config.ovs_vsctl_timeout)
        linux_net.agilio_release(vif.vif_name)

    def unplug(self, vif, instance_info):
        # Note: calls agilio_linux_net in stead of linux_net
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if not isinstance(vif.port_profile, VIFPortProfileOpenVSwitch):
            raise exception.WrongPortProfile(
                profile=vif.port_profile.__class__.__name__)

        if isinstance(vif, objects.vif.VIFVHostUser):
            self._unplug_agilio_forwarder(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFHostDevice):
            self._unplug_agilio_passthrough(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFOpenVSwitch):
            if sys.platform == constants.PLATFORM_WIN32:
                self._unplug_vif_windows(vif, instance_info)
        elif isinstance(vif, objects.vif.VIFBridge):
            if sys.platform != constants.PLATFORM_WIN32:
                self._unplug_bridge(vif, instance_info)
            else:
                self._unplug_vif_windows(vif, instance_info)
