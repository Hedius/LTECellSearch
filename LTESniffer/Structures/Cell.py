#  Copyright (C) 2020.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from typing import Dict


class Cell:
    """
    Represents a LTE cell.
    """

    def __init__(self, scan_id: str, cell_id: int, frequency_center: int,
                 frequency_offset: int, dpx: str, rx_power: str,
                 data=None):
        """
        Init a new cell
        :param scan_id: The ID of the scan.
        :param cell_id:  cell_id
        :param frequency_center: center frequency in Hz
        :param frequency_offset: offset frequency in Hz
        :param dpx: dpx
        :param rx_power: RX power
        :param data: Dict from hackRF search
        """
        if data is None:
            data = {}
            self.recordings = []
        else:
            self.recordings = (data["recordings"]
                               if "recordings" in data
                               else [])

        self.scan_id = scan_id
        self.cell_id = cell_id

        self.frequency_center = frequency_center
        self.frequency_offset = frequency_offset

        self.rx_power = rx_power

        self.dpx = dpx

        self.operator_id = "N/A"
        self.operator = "N/A"
        self.band = "N/A"
        self.region = "N/A"

        self.data = data

    def __str__(self):
        return (
            f"Cell: Scan_ID: {self.scan_id}, Cell_ID: {self.cell_id}, "
            f"Frequency_center: {self.frequency_center} Hz, "
            f"Frequency_offset: {self.frequency_offset} Hz, "
            f"DPX: {self.dpx}, Operator: "
            f"{self.operator if len(self.operator) > 0 else 'Unknown'}"
        )

    def dict(self) -> Dict:
        """
        Get a dict for data backups.
        :return: Dict representing the object.
        """
        self.data["scan_id"] = self.scan_id
        self.data["cell_id"] = self.cell_id
        self.data["frequency_center"] = self.frequency_center
        self.data["frequency_offset"] = self.frequency_offset
        self.data["rx_power"] = self.rx_power
        self.data["dpx"] = self.dpx
        self.data["recordings"] = self.recordings
        self.data["operator_id"] = self.operator_id
        self.data["operator"] = self.operator
        self.data["band"] = self.band
        self.data["region"] = self.region
        return self.data
