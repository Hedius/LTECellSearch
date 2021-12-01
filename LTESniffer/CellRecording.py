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

import os
import logging
import time
import subprocess
from pathlib import Path
from typing import Tuple
from datetime import datetime

from .HackRF.Exceptions import HackRFError
from .Structures.Cell import Cell


class CellRecording:
    """
    Record cell data.
    """
    def __init__(self, enable: bool, path_recording_dir: Path,
                 lte_sniffer):
        """
        Init the CellRecording class.
        :param enable: True if recordings should be performed else False.
        :param path_recording_dir: The path to the directory where recordings
                                   should be saved.
        :param lte_sniffer: The main class.
        """
        self._enable = enable
        self.path_recording_dir = path_recording_dir
        self._lte_sniffer = lte_sniffer

        os.makedirs(self.path_recording_dir, exist_ok=True)

    def get_recording_path(self, cell: Cell) -> Tuple[Path, str]:
        """
        Get the path for the recording file of the given cell.
        :param cell: The LTE cell that should be recorded.
        :return: 2-Tuple: the full path, file name
        """
        hackrf = self._lte_sniffer.hack_rf
        # hackrf_recording_{scan_id}f{frequency}_bw{bw}_l{}_g{}_amp{}_cell{}
        # .bin
        file_name = (
            f"{datetime.now().strftime('%y%m%d_%H%M')}_"
            f"hackrf_recording_{cell.scan_id}_cell{cell.cell_id}_"
            f"f{cell.frequency_center}_"
            f"bw{int(hackrf.baseband_filter_bw)}_"
            f"l{hackrf.l_gain}_g{hackrf.g_gain}_amp{int(hackrf.amp_enable)}_"
            f"{int(hackrf.recording_time)}s.bin"
        )

        return self.path_recording_dir / file_name, file_name

    def record_cell(self, cell: Cell):
        path, file_name = self.get_recording_path(cell)
        cur_try = 1
        while True:
            try:
                self._lte_sniffer.hack_rf.cell_recording(
                    frequency_center=cell.frequency_center,
                    path=path
                )
                cell.recordings.append(file_name)
            except HackRFError as e:
                logging.critical(e)
            except subprocess.CalledProcessError:
                if cur_try <= 5:
                    logging.error(
                        f"Recording of cell {cell} failed! Try "
                        f"{cur_try}/{5}.")
                    continue
                else:
                    logging.critical(f"Recording of cell {cell} "
                                     f"failed.")
                    break
            logging.debug(f"Finished recording of cell {cell}.")
            break

    def record(self):
        """
        Record data from all stored cells.
        """
        if self._enable is False:
            return

        logging.debug("Starting Recording:")
        time.sleep(2)  # cooldown

        try:
            for band in self._lte_sniffer.cell_search.frequency_bands:
                for cell in band.cells:
                    self.record_cell(cell)
        except KeyboardInterrupt as e:
            raise e
        finally:
            self._lte_sniffer.cell_search.save_results_to_json()
            self._lte_sniffer.cell_search.save_results_to_csv()
