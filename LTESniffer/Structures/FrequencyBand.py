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

from typing import Dict, List

from .Cell import Cell


class FrequencyBand:
    def __init__(self, start_frequency: int,
                 end_frequency: int, scanned_ids: List[str], scan=True):
        """
        Init a new FrequencyBand.
        :param start_frequency: Start of the scanning area in Hz.
        :param end_frequency: End of the scanning area in Hz.
        :param scanned_ids: List containing all scanned scan IDs.
        :param scan: True if this band should be scanned else False.
        """
        self.start_frequency = start_frequency
        self.end_frequency = end_frequency
        self.scanned_ids = scanned_ids
        self.scan = scan

        self.cells: List[Cell] = []

    def __str__(self):
        return (f"Band ({self.start_frequency / 1e6}MHz to "
                f" {self.end_frequency / 1e6}MHz)")

    def dict(self) -> Dict:
        """
        Get a dict for data backups.
        :return: Dict representing the object.
        """
        return {
            "start": self.start_frequency,
            "end": self.end_frequency,
            "scanned_ids": self.scanned_ids,
            "scan": self.scan
        }
