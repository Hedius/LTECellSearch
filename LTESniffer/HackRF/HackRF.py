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

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from decimal import Decimal
from typing import Dict, Optional, List, Tuple

from .Exceptions import HackRFError, ScanTimeOut


class HackRF:
    """
    Class for interactions with hackRF.
    """

    # Only print the output of hackrf_info once
    PRINTED_HACKRF_INFO = False

    def __init__(self, amp_enable: bool, antenna_enable: bool,
                 l_gain: int, g_gain: int, sample_rate: int,
                 recording_time: float, baseband_filter_bw: int):
        """
        Init HackRF.
        :param amp_enable: Enable the amp of hackRF.
        :param antenna_enable:  Enable the antenna.
        :param l_gain: l_gain
        :param g_gain:  g_gain
        :param sample_rate: sample_rate in Hz
        :param recording_time: time to record per cell
        :param baseband_filter_bw: bw of filter in Hz
        """
        # unused atm - needed for hackrf_transfer later
        self.amp_enable = amp_enable
        self.antenna_enable = antenna_enable
        self.l_gain = l_gain
        self.g_gain = g_gain
        self.sample_rate = sample_rate
        self.recording_time = recording_time
        self.baseband_filter_bw = baseband_filter_bw

    @staticmethod
    def is_connected():
        """
        Check if libhackrf is available and if a hackRF is connected.

        :returns: True if no exception has been raised.
        :raises HackRFError: hackRF not connected or libhackrf missing
        """
        try:
            subprocess.run("hackrf_info",
                           capture_output=HackRF.PRINTED_HACKRF_INFO,
                           check=True)
            HackRF.PRINTED_HACKRF_INFO = True
        except FileNotFoundError:
            logging.critical("Unable to find libhackrf! Make sure that it is "
                             "installed!")
            raise HackRFError("Hackrf lib missing!")
        except subprocess.CalledProcessError:
            logging.critical("HackRF is offline and not connected!")
            raise HackRFError("Unable to find HackRF!")
        return True

    @staticmethod
    def cell_search_available():
        """
        Check if CellSearch is in the $PATH and available.

        :returns: True if no exception has been raised.
        :raises HackRFError: CellSearch not available.
        """
        try:
            subprocess.run("CellSearch", capture_output=True)
        except FileNotFoundError:
            msg = "Unable to locate CellSearch! Is LTE-Cell-Scanner installed?"
            raise HackRFError(msg)
        return True

    @staticmethod
    async def cell_search(start_frequency: float,
                          end_frequency: float,
                          step_width: int = 5) -> Tuple[Dict, List[Dict]]:
        """
        Perform a cell search using LTE-Cell-Scanner and hackRF.

        :param start_frequency: The start frequency of the scanning area in Hz.
        :param end_frequency: The end frequency of the scanning area in Hz.
        :param step_width: step width in 100KHz steps (1 = 100KHz, etc)
        :return: The scan result in a dictionary.

        :raises HackRFError: If the scan fails.
        :raises ScanTimeOut: If the scan gets stuck.
        """
        # make sure that a hackRF is available
        HackRF.is_connected()
        HackRF.cell_search_available()

        peaks = {}
        found_cells = []
        cur_frequency = 0

        # Cell search params
        parameters = (
            "-g", str(40), "-s", str(int(start_frequency)),
            "-e", str(int(end_frequency)), "-n", str(1),
            "-x", str(step_width)
        )

        # Start cell search in an async operation
        proc = await asyncio.create_subprocess_exec(
            "CellSearch",
            *parameters,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        # Check the stdout output of CellSearch.
        while True:
            # retrieve a new line
            try:
                # timeout after 30s
                line = await asyncio.wait_for(proc.stdout.readline(), 30)
            except asyncio.TimeoutError:
                # CellSearch might get stuck after a certain time
                proc.kill()
                raise ScanTimeOut

            if not line:  # EOF - return result
                return peaks, found_cells

            # we have a new line - process it
            line = line.decode()

            # Frequency
            tmp_cur_frequency = check_cur_frequency(start_frequency,
                                                    end_frequency, line)
            if tmp_cur_frequency:
                cur_frequency = tmp_cur_frequency

            # Peak
            peak = check_peak(line)
            if peak > 0:
                peaks[cur_frequency] = peak

            # Found Cell
            cell_dict = check_found_cell(start_frequency, end_frequency, line)
            if cell_dict:  # found a cell
                found_cells.append(cell_dict)

            if proc.returncode is not None and proc.returncode != 0:
                raise HackRFError("Unknown Cell Search Error! Check stderr!")

    def cell_recording(self, frequency_center: float, path: Path):
        """
        Record raw data based on the defined member values of hackRF and
        the given frequency.

        :param frequency_center: The frequency to record.
        :param path: Path where the recording should be saved.

        :raises HackRFError: If the recording fails.
        """
        # make sure that a hackRF is available
        HackRF.is_connected()

        n_samples = int(self.sample_rate * self.recording_time)
        logging.info(f"Starting data recording for {frequency_center / 1e6} "
                     f"MHz. Recording Time: {self.recording_time}s, "
                     f"Samples: {n_samples}, BW: "
                     f"{self.baseband_filter_bw / 1e6} MHz, L_Gain: "
                     f"{self.l_gain} dB, G_Gain: {self.g_gain} dB")

        # Cell search params
        parameters = (
            "hackrf_transfer",
            "-r", path,  # receive mode, save to given path
            "-f", str(int(frequency_center)),  # frequency
            "-a", str(int(self.amp_enable)),  # amp
            "-p", str(int(self.antenna_enable)),  # antenna port power,
            "-l", str(self.l_gain),
            "-g", str(self.g_gain),
            "-s", str(self.sample_rate),
            "-n", str(n_samples),  # Number of samples to transfer
            "-b", str(self.baseband_filter_bw)
        )

        try:
            process = subprocess.run(parameters,
                                     capture_output=False, check=True,
                                     timeout=self.recording_time + 30)
        except TimeoutError:
            raise HackRFError("Recording of data failed for "
                              f"{frequency_center / 1e6} MHz! "
                              "Process should have ended 30s ago!")
        if process.returncode == 0:
            logging.info("Successfully recorded data for "
                         f"{frequency_center / 1e6} MHz! Saved to {path}")
        else:
            raise HackRFError("Recording of data failed for "
                              f" {frequency_center / 1e6} MHz!")


def check_peak(line: str) -> int:
    """
    Check for a peak line. Extract the number of detected peaks.

    :param line: current line

    :returns: detected peaks
    """
    num_peaks = 0
    re_found_peak = re.compile(r"Hit\s+num peaks (\d+)")
    match_found_peak = re.match(re_found_peak, line)
    if match_found_peak:
        num_peaks = int(match_found_peak.group(1))
        logging.debug(
            f"Found {num_peaks} peaks!"
        )
    return num_peaks


def check_cur_frequency(start_frequency: float, end_frequency: float,
                        line: str) -> Optional[float]:
    """
    Check for examining frequency x line.
    Extract the frequency.

    :param start_frequency: start frequency of the scan
    :param end_frequency: end frequency of the scan
    :param line: current line

    :returns: detected peaks
    """
    re_cur_freq = re.compile(r"^Examining center frequency ([\d.]+) MHz")
    start_frequency_mhz = start_frequency / 1e6
    end_frequency_mhz = end_frequency / 1e6

    # Status update
    match_cur_freq = re.match(re_cur_freq, line)
    if match_cur_freq:
        # extract frequency
        cur_freq = float(match_cur_freq.group(1))
        # calculate progress
        try:
            progress = ((cur_freq * 1e6 - start_frequency)
                        / (end_frequency - start_frequency)
                        * 100)
        except ZeroDivisionError:
            progress = 100

        # log the progress event
        logging.debug(
            f"Current scan ({start_frequency_mhz} MHz to {end_frequency_mhz} "
            f"MHz) cur: {cur_freq} MHz, progress: {int(progress)}%"
        )
        return int(cur_freq * 1e6)


def check_found_cell(start_frequency: float, end_frequency: float,
                     line: str) -> Optional[Dict]:
    """
    Process the given string and try to extract information from it.

    :param start_frequency: Start of the scanning area in Hz.
    :param end_frequency: End of the scanning area in Hz.
    :param line: The current stdout line from CellSearch.
    :return: Optional dict containing info about a found cell.
    """
    if len(line) < 3:  # prevent useless regex checks...
        return None

    prefix = (f"Cell Search Result ({start_frequency / 1e6} MHz to "
              f"{end_frequency / 1e6} MHz): ")

    re_no_cells_found = re.compile(r"^No LTE cells were found")
    # is there a better way to do this?
    re_extract_cell_info = re.compile(
        r"([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+"
        r"([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+"
        r"([\d.]+)"
    )

    # No cells found
    match_no_cells_found = re.match(re_no_cells_found, line)
    if match_no_cells_found:
        logging.info(prefix + "No LTE cells found!")
        return None

    # Extract cell info
    match_extract_cell_info = re.match(re_extract_cell_info, line)
    if match_extract_cell_info:
        cell_info = {
            "dpx": match_extract_cell_info.group(1),
            "cell_id": int(match_extract_cell_info.group(2)),
            "antenna_port": match_extract_cell_info.group(3),
            "frequency_center": (int(float(match_extract_cell_info.group(4)
                                           .strip("M")) * 1e6)),
            "frequency_offset": (int(float(match_extract_cell_info.group(5)
                                           .strip("k")) * 1e3)),
            "rx_power": Decimal(match_extract_cell_info.group(6)),
            "cp_type": match_extract_cell_info.group(7),
            "nRB": int(match_extract_cell_info.group(8)),
            "PHICH_duration": match_extract_cell_info.group(9),
            "PHICH_resource_type": match_extract_cell_info.group(10),
            "crystal_correction_factor": Decimal(
                match_extract_cell_info.group(11)
            )
        }
        logging.debug(f"Found a cell: {cell_info}")
        return cell_info


if __name__ == "__main__":
    # just a short test
    logging.basicConfig(level=logging.DEBUG)
    print(HackRF.is_connected())
    print(HackRF.is_connected())
    print(HackRF.cell_search_available())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(HackRF.cell_search(814e6, 817e6))
