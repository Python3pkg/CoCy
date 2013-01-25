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
"""
from cocy.upnp.adapters.adapter import upnp_service, UPnPServiceController

class BinarySwitchPowerController(UPnPServiceController):
    
    def __init__(self, device_path, service, service_id):
        super(BinarySwitchPowerController, self).__init__\
            (device_path, service, service_id)

    @upnp_service
    def SetTarget(self, **kwargs):
        self.parent.provider.state \
            = (kwargs["newTargetValue"] in ["1", "yes", "true"])
        return []

    @upnp_service
    def GetTarget(self, **kwargs):
        return [("RetTargetValue", "1" if self.parent.provider.state else "0")]

    @upnp_service
    def GetStatus(self, **kwargs):
        return [("ResultStatus", "1" if self.parent.provider.state else "0")]
