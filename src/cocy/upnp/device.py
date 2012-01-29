"""
..
   This file is part of the CoCy program.
   Copyright (C) 2011 Michael N. Lipp
   
   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.

.. codeauthor:: mnl
"""
from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, ElementTree
from circuitsx.tools import replace_targets
from circuits.web.controllers import expose, BaseController
from cocy.providers import BinarySwitch
from cocy.upnp import SSDP_DEVICE_SCHEMA, SSDP_SCHEMAS, UPNP_SERVICE_ID_PREFIX
from util.compquery import Queryable
from util.misc import parseSoapRequest

class UPnPDevice(BaseController, Queryable):

    channel = "upnp"
    
    class Properties(object):
        def __init__(self, dev_type, ver, spec_ver_major, spec_ver_minor,
                     services):
            object.__init__(self)
            self.type = dev_type
            self.ver = ver
            self.spec_ver_major = spec_ver_major
            self.spec_ver_minor = spec_ver_minor
            self.services = services

    _mapping = {
        # Provider: Properties("Basic", 1, 1, 0, []),
        BinarySwitch: Properties("BinaryLight", 0.9, 1, 0,
            [("SwitchPower:1", UPNP_SERVICE_ID_PREFIX + "SwitchPower:1")])
    }

    def __init__(self, provider, config_id, uuid_map, service_map, port):
        self.valid = False
        self._provider = provider
        self.web_server_port = port
        manifest = provider.provider_manifest()
        for itf, props in self._mapping.iteritems():
            if isinstance(provider, itf):
                self.valid = True
                self._props = props
            break;
        if manifest.unique_id and uuid_map.has_key(manifest.unique_id):
            self._uuid = uuid_map[manifest.unique_id]
        else:
            self._uuid = str(uuid4())
            uuid_map[manifest.unique_id] = self._uuid
        self._path = "/" + self.uuid
        replace_targets(self, {"#me": "/upnp-web" + self._path})
        super(UPnPDevice, self).__init__();
        self.config_id = config_id
        self.friendly_name = manifest.display_name
        self.manufacturer = manifest.manufacturer or "cocy"
        self.model_description = manifest.description
        self.model_name = manifest.full_name or manifest.display_name
        self.model_number = manifest.model_number

        self._services = set()
        service_insts = []
        for (service_type, service_id) in self._props.services:
            if not service_map.has_key(service_type):
                continue
            service_insts.append((service_map[service_type], service_id))
            self._services.add(service_map[service_type])

        desc = self._desc_funcs[self.type_ver](self, config_id, service_insts)
        class Writer(object):
            result = ""
            def write(self, value):
                self.result += value
        writer = Writer()
        ElementTree(desc).write(writer, xml_declaration=True,
                                method="xml", encoding="utf-8")
        self.description = writer.result

    @property
    def provider(self):
        return self._provider

    @property
    def uuid(self):
        return self._uuid

    @property
    def root_device(self):
        return True # TODO:

    @property
    def services(self):
        return self._services

    def __getattr__(self, name):
        if not name.startswith("_") and hasattr(self._props, name):
            return getattr(self._props, name, None)
        raise AttributeError

    @property
    def type_ver(self):
        return "%s:%s" % (self._props.type, str(self._props.ver))

    def _common_device_desc(self, config_id, services):
        root = Element("{%s}root" % SSDP_DEVICE_SCHEMA,
                       attrib = {"configId": str(config_id)})
        specVersion = SubElement(root, "{%s}specVersion" % SSDP_DEVICE_SCHEMA)
        SubElement(specVersion, "{%s}major" % SSDP_DEVICE_SCHEMA).text \
            = str(self.spec_ver_major)
        SubElement(specVersion, "{%s}minor" % SSDP_DEVICE_SCHEMA).text \
            = str(self.spec_ver_minor)
        device = SubElement(root, "{%s}device" % SSDP_DEVICE_SCHEMA)
        SubElement(device, "{%s}deviceType" % SSDP_DEVICE_SCHEMA).text \
            = SSDP_SCHEMAS + ":device:" + self.type_ver
        for tag, attrib in [("friendlyName", "friendly_name"),
                            ("manufacturer", "manufacturer"),
                            ("modelDescription", "model_description"),
                            ("modelName", "model_name"),
                            ("modelNumber", "model_number")]:
            if getattr(self, attrib, None):
                SubElement(device, "{%s}%s" % (SSDP_DEVICE_SCHEMA, tag)).text \
                    = getattr(self, attrib, None)
        SubElement(device, "{%s}UDN" % SSDP_DEVICE_SCHEMA).text \
            = "uuid:" + self.uuid
        if services and len(services) > 0:
            serviceList = SubElement(device, 
                                     "{%s}serviceList" % SSDP_DEVICE_SCHEMA)
            for service in services:
                self._addService(serviceList, service)
        return root
        
    _desc_funcs = {
        "BinaryLight:0.9": _common_device_desc,
        "Basic:1": _common_device_desc
    }

    def _addService(self, service_list, service_tuple):
        (service_type, service_id) = service_tuple
        service = SubElement(service_list, "{%s}service" % SSDP_DEVICE_SCHEMA)
        SubElement(service, "{%s}serviceType" % SSDP_DEVICE_SCHEMA).text \
            = SSDP_SCHEMAS + ":service:" + service_type.type_ver
        SubElement(service, "{%s}serviceId" % SSDP_DEVICE_SCHEMA).text \
            = service_id
        SubElement(service, "{%s}SCPDURL" % SSDP_DEVICE_SCHEMA).text \
            = service_type.description_url
        SubElement(service, "{%s}controlURL" % SSDP_DEVICE_SCHEMA).text \
            = self._path + "/control"
        SubElement(service, "{%s}eventSubURL" % SSDP_DEVICE_SCHEMA).text \
            = self._path + "/sub"
        
    @expose("control", target="#me")
    def _on_control(self):
        payload = parseSoapRequest(self.request)[2]
        action = payload.tag
        for node in payload:
            print node

        self.response.headers["Content-Type"] = "text/xml"
        return "control"

    @expose("sub", target="#me")
    def _on_sub(self):
        self.response.headers["Content-Type"] = "text/xml"
        return "sub"
    
    @expose("description.xml", target="#me")
    def _on_description(self):
        self.response.headers["Content-Type"] = "text/xml"
        return self.description
