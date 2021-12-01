#  Copyright (C) 2021.
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
import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict

import requests

from .Structures.Cell import Cell


class ProviderMapping:
    """
    Use open data from the Austrian Government to map cell frequencies to
    providers. Workaround since we failed to decode SIBs. Sad.
    """
    def __init__(
            self, cache: Path,
            coverage=None,
            url: str = 'https://data.rtr.at/api/v1/tables/tk_frequenzen.json'):
        if coverage is None:
            coverage = ['national']
        self._url = url
        self._cache_path = cache

        self.coverage = coverage

        self.loaded_data: bool = False
        self.data: Dict = {}

        self.load_frequency_assignments()
        self.remove_invalid_assignments()

    @property
    def assignments(self):
        return self.data['data'] if 'data' in self.data else []

    @assignments.setter
    def assignments(self, value):
        self.data['data'] = value

    @staticmethod
    def download_frequency_assignments(url: str) -> Dict:
        """
        :param url:
        :return:
        """
        r = requests.get(url)
        if r.status_code >= 300:
            raise requests.RequestException
        return r.json()

    @staticmethod
    def save_frequency_assignments(cache: Path, data: Dict):
        """

        :param cache:
        :param data:
        :return:
        """
        with open(cache, 'w') as fp:
            json.dump(data, fp, indent=4)

    @staticmethod
    def read_frequency_assignments(cache: Path) -> Dict:
        """

        :param cache:
        :return:
        """
        with open(cache, 'r') as fp:
            return json.load(fp)

    def load_frequency_assignments(self):
        try:
            self.data = self.download_frequency_assignments(self._url)
            self.save_frequency_assignments(self._cache_path, self.data)
            logging.debug('Successfully downloaded the most recent cell '
                          'assignments from RTR!')
        except requests.RequestException:
            logging.error('Download of most recent RTR assignments has '
                          'failed!')
            try:
                self.data =\
                    self.read_frequency_assignments(self._cache_path)
                logging.warning('Reused previously downloaded assignments!')
            except FileNotFoundError:
                logging.critical('Cell assignments not available! Failed to '
                                 'load saved data!')
                return
        self.loaded_data = True

    def remove_invalid_assignments(self):
        """
        Goes over all assignments and removes those who are not valid today.
        Furthermore, removes assignments, which are not valid for the current
        region.
        :return:
        """
        new_assignments = []
        for assignment in self.assignments:
            # check date
            today = date.today()
            if assignment['startdate'] is not None:
                start_date = date.fromisoformat(assignment['startdate'])
                if today < start_date:
                    continue

            if assignment['expiry'] is not None:
                expiry = date.fromisoformat(assignment['expiry'])
                if today > expiry:
                    continue

            coverage = assignment['coverage']
            match = False
            for cur_coverage in coverage.split(","):
                if cur_coverage in self.coverage:
                    match = True
            if not match and coverage != "national":
                continue
            new_assignments.append(assignment)
        self.assignments = new_assignments

    def find_provider(self, cell: Cell):
        match = False
        for assignment in self.assignments:
            duplex = assignment['duplex']
            operator_id = assignment['betreiberid']
            company = assignment['company']
            band = assignment['frequencyband']
            start_frequency = (assignment['lowerfrequency']
                               if not duplex
                               else assignment['downlinklowerfrequency'])
            higher_frequency = (assignment['higherfrequency']
                                if not duplex
                                else assignment['downlinkhigherfrequency'])
            if start_frequency <= cell.frequency_center <= higher_frequency:
                if match:
                    logging.critical(
                        f'Multiple assignments! Found provider '
                        f'{operator_id} - {company} for '
                        f' cell {cell} in band {band} '
                        f'(Region: {assignment["coverage"]})')
                cell.operator_id = operator_id
                cell.operator = company
                cell.band = band
                cell.region = assignment['coverage']
                match = True
                logging.info(f'Found provider {operator_id} - {company} for '
                             f' cell {cell} in band {band} '
                             f'(Region: {assignment["coverage"]})')
