# Derived from os-vif/vif_plug_ovs/linux_net.py
#
# Copyright (C) 2017 Netronome Systems, Inc.
# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Linux utilities necessary for Agilio OVS network setup."""

from oslo_concurrency import processutils
from oslo_log import log as logging

from vif_plug_agilio_ovs import privsep
from vif_plug_ovs import exception

LOG = logging.getLogger(__name__)


def _ovs_vsctl(args, timeout=None):
    full_args = ['ovs-vsctl']
    if timeout is not None:
        full_args += ['--timeout=%s' % timeout]
    full_args += args
    try:
        return processutils.execute(*full_args)
    except Exception as e:
        LOG.error("Unable to execute %(cmd)s. Exception: %(exception)s",
                  {'cmd': full_args, 'exception': e})
        raise exception.AgentError(method=full_args)


def _agilio_vf_mgr(args):
    full_args = ['agilio-vf-mgr.py']
    full_args += args
    try:
        return processutils.execute(
            *full_args,
            run_as_root=True,
            check_exit_code=[0, 1])
    except Exception as e:
        LOG.error("Unable to execute %(cmd)s. Exception: %(exception)s",
                  {'cmd': full_args, 'exception': e})
        raise exception.AgentError(method=full_args)


def _create_ovs_vif_cmd(bridge, dev, iface_id, mac,
                        instance_id, interface_type=None,
                        vhost_server_path=None, virtio_forwarder=None):
    cmd = ['--', 'add-port', bridge, dev,
           '--', 'set', 'Interface', dev,
           'external-ids:iface-id=%s' % iface_id,
           'external-ids:iface-status=active',
           'external-ids:attached-mac=%s' % mac,
           'external-ids:vm-uuid=%s' % instance_id]
    if interface_type:
        cmd += ['type=%s' % interface_type]
    if vhost_server_path:
        cmd += ['options:vhost-server-path=%s' % vhost_server_path]
    if virtio_forwarder:
        cmd += ['external-ids:virtio_forwarder=%s' % virtio_forwarder]
    return cmd


def _create_ovs_bridge_cmd(bridge, datapath_type):
    return ['--', '--may-exist', 'add-br', bridge,
            '--', 'set', 'Bridge', bridge, 'datapath_type=%s' % datapath_type]


@privsep.vif_plug.entrypoint
def create_ovs_vif_port(bridge, dev, iface_id, mac, instance_id,
                        mtu=None, interface_type=None, timeout=None,
                        vhost_server_path=None, virtio_forwarder=None):
    delete_ovs_vif_port(bridge, dev, timeout=timeout)
    cmd = _create_ovs_vif_cmd(bridge, dev, iface_id,
                              mac, instance_id, interface_type,
                              vhost_server_path, virtio_forwarder)
    _ovs_vsctl(cmd, timeout=timeout)


@privsep.vif_plug.entrypoint
def agilio_claim_passthrough(dev, mac_address, pci_slot):
    _agilio_vf_mgr(['--claim-passthrough', dev, mac_address,
                   '--pciaddr', pci_slot])


@privsep.vif_plug.entrypoint
def agilio_claim_forwarder(dev, mac_address, pci_slot, vhupath=None):
    cmd = ['--claim-forwarder', dev, mac_address, '--pciaddr', pci_slot]
    if vhupath:
        cmd += ['--vhupath', vhupath]
    _agilio_vf_mgr(cmd)


@privsep.vif_plug.entrypoint
def agilio_release(pci_slot, vhupath=None):
    cmd = ['--releasepci', pci_slot]
    if vhupath:
        cmd += ['--vhupath', vhupath]
    _agilio_vf_mgr(cmd)


@privsep.vif_plug.entrypoint
def delete_ovs_vif_port(bridge, dev, timeout=None):
    _ovs_vsctl(['--', '--if-exists', 'del-port', bridge, dev],
               timeout=timeout)


@privsep.vif_plug.entrypoint
def ensure_ovs_bridge(bridge, datapath_type):
    _ovs_vsctl(_create_ovs_bridge_cmd(bridge, datapath_type))
