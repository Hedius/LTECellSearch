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
import copy
import logging
import os
import csv
import simplejson as json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .HackRF.HackRF import HackRF
from .HackRF.Exceptions import HackRFError, ScanTimeOut
from .ProviderMapping import ProviderMapping
from .Structures.Cell import Cell
from .Structures.FrequencyBand import FrequencyBand


class CellSearch:
    """
    Performs LTE cell searches by using a hackRF.
    """
    def __init__(self, scan_id: str, rescan: bool,
                 path_scan_config: Path, path_results_dir: Path,
                 provider_mapping: ProviderMapping,
                 enable: bool = True, step_width: int = 1):
        """
        Init CellSearch.

        :param scan_id: The ID of the scan.
        :param rescan: Rescan all bands or skip already scanned bands?
        :param path_scan_config: Path to the scan config.
        :param path_results_dir: Path to the results dir.
        :param enable: Enable the cell search module.
        :param step_width: Step width for gross scans. (1 = 100kHz)

        :raises OSError: Failed to open the scan config.
        """
        self.scan_id = scan_id
        self.step_width = step_width
        self._enable = enable
        self._rescan = rescan
        self._path_scan_config = path_scan_config
        self._path_results_dir = path_results_dir
        self._path_results_json = path_results_dir / "CellSearchResults.json"
        self._path_results_csv = path_results_dir / "CellSearchResults.csv"

        self.frequency_bands: List[FrequencyBand] = []

        self._provider_mapping = provider_mapping

        # Load config and restore data
        self.load_frequency_bands()
        self.load_results()

    def load_frequency_bands(self):
        """
        Load the scan config.

        :raises OSError: Write Operation failed.
        """
        # read file
        try:
            with open(self._path_scan_config, "r") as fp:
                data = json.load(fp)
        except OSError as e:
            logging.exception("Failed to load bands config: %s! Exception: %s",
                              self._path_scan_config, e)
            raise e

        logging.debug("Successfully loaded %s bands from %s.", len(data),
                      self._path_scan_config)

        # parse json
        for band_data in data:
            band = FrequencyBand(
                start_frequency=int(band_data["start"]),
                end_frequency=int(band_data["end"]),
                scan=band_data["scan"],
                scanned_ids=band_data["scanned_ids"]
            )
            self.frequency_bands.append(band)

    def save_frequency_bands(self):
        """
        Save the updated scan config.

        :raises OSError: Write operation failed.
        """
        # create dict
        data = []
        for band in self.frequency_bands:
            data.append(band.dict())
        try:
            with open(self._path_scan_config, "w") as fp:
                json.dump(data, fp, indent=2)
        except OSError as e:
            logging.exception("Failed to save bands config: %s! Exception: %s",
                              self._path_scan_config, e)
            raise e

        logging.debug("Successfully saved updated bands config to %s",
                      self._path_scan_config)

    def _scan_peak(self, band: FrequencyBand, window_start, window_end):
        count = 0
        while True:
            # Scan the whole area (EG: Peak at 816MHz ->
            # 815.1 - 816.9 MHz. (Because the gross scan already
            # scanned the others)).
            window_start -= (self.step_width - 1) * 100e3
            window_end += (self.step_width - 1) * 100e3
            logging.debug(f"Scanning peak! - Area {window_start / 1e6}"
                          f"MHz - {window_end / 1e6}MHz")
            try:
                loop = asyncio.get_event_loop()
                peaks_new, cells_dict = loop.run_until_complete(
                    HackRF.cell_search(
                        start_frequency=window_start,
                        end_frequency=window_end,
                        step_width=1
                    )
                )
                self._process_search_result(band, window_start,
                                            window_end, cells_dict)
                return True
            except ScanTimeOut:
                msg = "Peak scan timed out!"
                if count < 3:
                    count += 1
                    logging.error(msg + "Tying again!")
                    continue
                return False
            except HackRFError as e:
                logging.exception(
                    f"{band}: Peak Scan {window_start / 1e6}MHz - "
                    f"{window_end / 1e6}MHz failed! {e}")
                return False

    def _scan_peaks(self, band: FrequencyBand, peaks: Dict):
        """
        Go through all found peaks and scan with a step width of 100kHz
        to find 4G cells.

        :param band: Current frequency band.
        :param peaks: Dict (Key: peak frequency in Hz) - Peaks

        :returns: True if all peak scans have been completed successfully
            else False.
        """
        # Init
        last_peak = window_start = window_end = 0
        peak_scan_successful = True
        run_peak_scan = False
        for i, peak in enumerate(peaks):
            # Init the variables (1st peak)
            if last_peak == 0 or run_peak_scan:
                window_start = peak
                window_end = peak
            if last_peak == 0:
                last_peak = peak

            run_peak_scan = False

            # Run a peak scan if the distance between the last peak and current
            # peak is > peak width = new (area)
            if (peak - last_peak) > self.step_width * 100e3:
                run_peak_scan = True
                window_end = last_peak

            # Trigger a scan if we reach the end of the scan window
            if len(peaks) - 1 == i:
                run_peak_scan = True
                window_end = peak

            # Run the scan if requested
            if run_peak_scan:
                peak_scan_successful = self._scan_peak(band, window_start,
                                                       window_end)
            last_peak = peak
        return peak_scan_successful

    def _process_search_result(self, band: FrequencyBand, start: int, end: int,
                               cells_dict: Dict):
        """
        Processes the result dict received from hackRF and saves the result in
        the given FrequencyBand object.

        :param band: The current frequency band.
        :param start: start frequency of the current scan
        :param end: end frequency of the current scan
        :param cells_dict: The cell search result dict from hackRF.
        """
        # cells found?
        if len(cells_dict) > 0:
            logging.info(
                f"{band} (Scan: Start: {start / 1e6} MHz, "
                f"End: {end / 1e6} MHz): {len(cells_dict)} cells found!")
        else:
            logging.info(
                f"{band} (Scan: Start: {start / 1e6} MHz, End: {end / 1e6} MHz"
                f"): No cells found!")

        # parse the cell data to Cell objects
        for cell_dict in cells_dict:
            # log_dict: (current timestamp)
            log_dict: Dict = copy.deepcopy(cell_dict)
            del log_dict["cell_id"]  # remove the id from the log_dict

            # last time we have seen the cell. (actually not accurate)
            last_seen = datetime.now().strftime("%x %X")
            cell_dict["last_seen"] = last_seen

            # does the cell already exist?
            cell = None
            cell_id = cell_dict["cell_id"]
            for cur_cell in band.cells:
                if cur_cell.cell_id == cell_id:
                    cell = cur_cell
                    logging.info(f"Found existing cell {cell}")
                    # update the log dict of the existing cell
                    cell.data["log"][last_seen] = log_dict
                    break

            # new cell
            if not cell:
                cell = Cell(
                    scan_id=self.scan_id,
                    cell_id=cell_dict["cell_id"],
                    frequency_center=cell_dict["frequency_center"],
                    frequency_offset=cell_dict["frequency_offset"],
                    dpx=cell_dict["dpx"],
                    rx_power=cell_dict["rx_power"],
                    data=cell_dict
                )
                cell.data["log"] = {
                    last_seen: log_dict
                }
                band.cells.append(cell)
                logging.info(f"Found new cell {cell}")
        logging.debug("Finished cell search routine")

    def _gross_scan_band(self, band: FrequencyBand):
        count = 0
        while True:
            try:
                # Search for peaks width the defined step width
                loop = asyncio.get_event_loop()
                peaks, cells_dict = loop.run_until_complete(
                    HackRF.cell_search(
                        start_frequency=band.start_frequency,
                        end_frequency=band.end_frequency,
                        step_width=self.step_width
                    )
                )
                return True, peaks
            except ScanTimeOut:
                msg = f"The gross scan for {band} timed out! "
                if count < 3:
                    count += 1
                    logging.error(msg + "Tying again!")
                    continue
                break
            except HackRFError as e:
                logging.exception(f"{band}: Scan failed! {e}")
                break
        return False, {}

    def perform_search(self):
        """
        Perform a cell search for the given config.
        """
        # module enabled?
        if self._enable is False:
            return
        logging.debug("Starting Cell Search Routine")

        # no bands???
        if len(self.frequency_bands) == 0:
            logging.warning("There are not defined any bands?")

        # issue a scan for all bands
        for band in self.frequency_bands:
            # Scan disabled for band?
            if band.scan is False:
                logging.debug(f"Ignoring band {band}: Scan is set to False!")
                continue

            # Already scanned and rescan disabled?
            if self.scan_id in band.scanned_ids and not self._rescan:
                logging.debug(f"Ignoring band {band}: Already scanned!")
                continue

            # Run the scan
            logging.debug(
                f"{band}: Starting a gross scan for peaks. Width "
                f"{self.step_width * 100}kHz")

            gross_scan_successful, peaks = self._gross_scan_band(band)
            if not gross_scan_successful:
                continue

            # Perform a peak scan width a more accurate resolution
            peak_scan_successful = self._scan_peaks(band, peaks)

            # add the scan id to the scan config to signal a successful scan
            if(peak_scan_successful
                    and gross_scan_successful
                    and self.scan_id not in band.scanned_ids):
                band.scanned_ids.append(self.scan_id)

    def fast_search_cell(self, band: FrequencyBand, cell: Cell):
        start_frequency = int(cell.frequency_center - 200e3)
        end_frequency = int(cell.frequency_center + 200e3)
        count = 0
        while True:
            try:
                # Search for peaks width the defined step width
                loop = asyncio.get_event_loop()
                peaks, cells_dict = loop.run_until_complete(
                    HackRF.cell_search(
                        start_frequency=start_frequency,
                        end_frequency=end_frequency
                    )
                )
                self._process_search_result(band, start_frequency,
                                            end_frequency, cells_dict)
                return True
            except ScanTimeOut:
                msg = f"Scan for cell {cell} timed out!"
                if count < 3:
                    count += 1
                    logging.error(msg + "Tying again!")
                    continue
                break
            except HackRFError as e:
                logging.exception(f"{cell}: Scan failed! {e}")
                break
        return False

    def perform_fast_search(self):
        """
        Use existing data to gather new data for known cells.
        (Only search for MIB at the frequency of known cells)
        """
        # module enabled?
        if self._enable is False:
            return
        logging.debug("Starting Fast Cell Search Routine")

        scanned_frequencies = []
        for band in self.frequency_bands:
            if band.scan is False or self.scan_id not in band.scanned_ids:
                continue

            for cell in band.cells:
                if cell.frequency_center in scanned_frequencies:
                    logging.debug(f"{band}: Skipping {cell}! Already scanned"
                                  " frequency.")
                    continue
                logging.debug(
                    f"{band}: Refreshing cell data for {cell}.")

                if self.fast_search_cell(band, cell):
                    scanned_frequencies.append(cell.frequency_center)

    def perform_provider_mapping(self):
        """

        :return:
        """
        for band in self.frequency_bands:
            for cell in band.cells:
                self._provider_mapping.find_provider(cell)

    def save_results_to_json(self):
        """
        Save the scan results in a json file.
        """
        # generate the data for the json file
        results = []
        for band in self.frequency_bands:
            band_dict = band.dict()
            band_dict["cells"] = {}
            for cell in band.cells:
                band_dict["cells"][cell.cell_id] = cell.dict()
            results.append(band_dict)

        # create the needed folders
        os.makedirs(self._path_results_dir, exist_ok=True)

        # write the json
        with open(self._path_results_json, "w") as fp:
            json.dump(results, fp, indent=2)
        logging.debug("Successfully saved results to %s",
                      self._path_results_json)

    def save_results_to_csv(self):
        """
        Save the scan results in a csv file.
        """
        # generate the data for the csv file
        results = []
        for band in self.frequency_bands:
            for cell in band.cells:
                for time, log in cell.data["log"].items():
                    tmp_dict = {
                        "cell_id": cell.cell_id,
                        "scan_id": cell.scan_id,
                        "time": time,
                        "dpx": cell.dpx,
                        "antenna_port": log["antenna_port"],
                        "frequency_center": log["frequency_center"],
                        "frequency_offset": log["frequency_offset"],
                        "rx_power": log["rx_power"],
                        "cp_type": log["cp_type"],
                        "nRB": log["nRB"],
                        "PHICH_duration": log["PHICH_duration"],
                        "PHICH_resource_type": log["PHICH_resource_type"],
                        "crystal_correction_factor":
                            log["crystal_correction_factor"],
                        "operator_id": cell.operator_id,
                        "operator": cell.operator,
                        "band": cell.band,
                        "region": cell.region
                    }
                    results.append(tmp_dict)
        # create the needed folders
        os.makedirs(self._path_results_dir, exist_ok=True)

        # write the csv
        with open(self._path_results_csv, "w") as f:

            fieldnames = ["cell_id", "scan_id", "time", "dpx", "antenna_port",
                          "frequency_center", "frequency_offset", "rx_power",
                          "cp_type", "nRB", "PHICH_duration",
                          "PHICH_resource_type", "crystal_correction_factor",
                          "operator_id", "operator", "band", "region"]

            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for result in results:
                writer.writerow(result)
        logging.debug("Successfully saved results to %s",
                      self._path_results_csv)

    def load_results(self):
        """
        Load existing scan data and populate the object structure.
        """
        try:
            with open(self._path_results_json, "r") as fp:
                results = json.load(fp)
        except FileNotFoundError:
            logging.info("Unable to load search scan results! Starting with a"
                         " clear record!")
            return

        # parse the json
        for band_dict in results:
            # find the band
            band: Optional[FrequencyBand] = None
            for cur_band in self.frequency_bands:
                if (band_dict["start"] >= cur_band.start_frequency
                        and band_dict["end"] <= cur_band.end_frequency):
                    band = cur_band
                    break
            if band is None:
                logging.critical(
                    f"Invalid Scan Results: Band with start "
                    f" {band_dict['start'] / 1e6} MHz and end "
                    f"{band_dict['end'] / 1e6} MHz missing! "
                    f"Path: {self._path_results_json}")
                continue

            # process all cells of the band
            for cell_id, cell_dict in band_dict["cells"].items():
                cell = Cell(
                        scan_id=cell_dict["scan_id"],
                        cell_id=int(cell_id),
                        frequency_center=cell_dict["frequency_center"],
                        frequency_offset=cell_dict["frequency_offset"],
                        dpx=cell_dict["dpx"],
                        rx_power=cell_dict["rx_power"],
                        data=cell_dict
                    )
                cell.operator_id = cell_dict["operator_id"]
                cell.operator = cell_dict["operator"]
                cell.operator = cell_dict["band"]
                cell.region = cell_dict["region"]
                band.cells.append(cell)
        logging.info("Successfully restored previous scan results!")

    def search(self, fast=False):
        """
        Perform a cell search and save the results.

        :param fast: True if we should only rescan known cells, else False.
        """
        try:
            if fast:
                self.perform_fast_search()
            else:
                self.perform_search()
            self.perform_provider_mapping()
        except KeyboardInterrupt as e:
            raise e
        finally:
            self.save_frequency_bands()
            self.save_results_to_json()
            self.save_results_to_csv()
