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

from pathlib import Path
from typing import Optional

from dynaconf import Dynaconf

from .HackRF.HackRF import HackRF
from .CellSearch import CellSearch
from .CellRecording import CellRecording
from .ProviderMapping import ProviderMapping


class LTESniffer:
    """
    The main class of the LTESnifferRepo project.
    Performs cell searches, data recording and analyzing.
    """
    def __init__(self, settings: Dynaconf, project_dir: Path):
        """
        Init LTESnifferRepo
        :param settings: dynaconf settings
        :param project_dir: main project directory (absolute path)
        """
        # setup the directory structure
        self.scan_id: str = settings.general.scan_id
        self._path_project_dir = project_dir
        self.path_base_dir = (self._path_project_dir
                              / settings.general.base_dir
                              / self.scan_id)
        self.path_search_dir = self._get_correct_path(
            settings.search.results_dir)
        self.path_record_dir = self._get_correct_path(
            settings.record.results_dir)

        self.path_scan_config = (project_dir
                                 / "1_Config"
                                 / settings.search.scan_config)

        self.path_assignments_cache = (project_dir
                                       / "frequency_assignments.json")

        # check if HackRF is connected if needed:
        if True in (settings.search.enable, settings.record.enable):
            HackRF.is_connected()
            HackRF.cell_search_available()

        # hackRF
        self.hack_rf = HackRF(
            amp_enable=settings.record.amp_enable,
            antenna_enable=settings.record.antenna_enable,
            l_gain=settings.record.l_gain,
            g_gain=settings.record.g_gain,
            sample_rate=settings.record.sample_rate,
            recording_time=settings.record.recording_time,
            baseband_filter_bw=settings.record.baseband_filter_bw
        )

        # Frequency Mapping
        self.provider_mapping = ProviderMapping(
            cache=self.path_assignments_cache,
            coverage=settings.general.regions
        )

        # cell search
        self.cell_search = CellSearch(
            scan_id=self.scan_id,
            enable=settings.search.enable,
            rescan=settings.search.rescan,
            path_scan_config=self.path_scan_config,
            path_results_dir=self.path_search_dir,
            provider_mapping=self.provider_mapping,
            step_width=settings.search.step_width
        )

        # recording
        self.recording = CellRecording(
            enable=settings.record.enable,
            path_recording_dir=self.path_record_dir,
            lte_sniffer=self
        )

    def _get_correct_path(self, path_str: str, prefix: Optional[Path] = None) \
            -> Path:
        """
        Convert the given path to an absolute path if it is relative.
        :param path_str: Absolute or relative path.
        :param prefix: The absolute prefix.
        :return: The new absolute path.
        """
        prefix: Path = self.path_base_dir if not prefix else prefix
        path = Path(path_str)
        if path.is_absolute():
            return path
        return prefix / path

    def search(self, fast=False):
        """
        Perform a cell search and save the results.

        :param fast: True if we should only rescan known cells, else False.
        """
        self.cell_search.search(fast)

    def record(self):
        """
        Perform a data recording for all saved cells.
        """
        self.recording.record()
