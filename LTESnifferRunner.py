#!/usr/bin/env python3

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

import argparse
import logging
import logging.handlers
import os
from argparse import ArgumentParser
from pathlib import Path
from dynaconf import Dynaconf, Validator, validator

from LTESniffer.LTESniffer import LTESniffer


def read_arguments() -> argparse.Namespace:
    """
    Configures the possible arguments and reads them from argv.
    :return: namespace containing the parsed arguments
    """
    parser = ArgumentParser(
        description=("Simple tool for automation of LTE/4G cell searches and "
                     "information gathering using HackRF + LTE-Cell-Scanner "
                     "+ MATLAB.")
    )

    # ToDo Add args for modes?
    parser.add_argument("-c", "--config", dest="CONFIG_FILE",
                        default="settings.toml", required=False,
                        help=("Optional name of a custom config file. "
                              "The file has to be in the folder 1_Config!"
                              "Default: settings.toml"))
    parser.add_argument("-vc", "--validate-config", dest="VALIDATE_CONFIG",
                        action="store_true", default=False,
                        help="Only validate the config.")

    parser.add_argument("-f", "--fast-scan", dest="FAST_SCAN",
                        action="store_true", default=False,
                        help="Perform a fast scan and only scan known "
                             "cells.")

    logging_group = parser.add_argument_group(
        title="Logging",
        description="Logging configuration. All arguments are optional."
    )
    logging_group.add_argument("-l", "--loglevel", dest="LOGLEVEL",
                               choices=["debug", "info", "warning", "error",
                                        "critical"],
                               default="debug", required=False,
                               help="Loglevel (Default: Debug)")

    logging_group.add_argument("--disable-log-stdout", dest="ENABLE_STDOUT",
                               action="store_false", default=True,
                               required=False,
                               help=("Enable logging to stdout. "
                                     "(Default: True)"))

    logging_group.add_argument("--disable-log-file", dest="ENABLE_FILE",
                               action="store_false", default=True,
                               required=False,
                               help="Enable logging to files. (Default: True)")

    logging_group.add_argument("--log-syslog", dest="ENABLE_SYSLOG",
                               action="store_true", default=False,
                               required=False,
                               help=("Enable logging to syslog. "
                                     "(Default: False)"))

    return parser.parse_args()


def configure_logging(log_level: str, log_dir: str, enable_stdout: bool = True,
                      enable_file: bool = True, enable_syslog: bool = False) \
        -> logging:
    """
    Configure the logger
    :param log_level: loglevel as string (NOTSET, DEBUG, INFO, Warning, Error,
                                          critical)
    :param log_dir: Directory for logging.
    :param enable_stdout: Enable logging to stdout?
    :param enable_file: Enable logging to the logging folder?
    :param enable_syslog: Enable logging to syslog?

    :returns logging: object of class logging (root logger)
    """
    log_levels = {
        'NOTSET': 0,
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    level = log_levels[log_level.upper()
                       if log_level.upper() in log_levels
                       else logging.DEBUG]

    # modify root logger
    log = logging.getLogger("")

    form = logging.Formatter("%(asctime)s %(module)s.%(funcName)s: "
                             "[%(levelname)s] %(message)s")

    form_syslog = logging.Formatter("%(module)s.%(funcName)s: "
                                    "[%(levelname)s] %(message)s")

    log_path = ""
    log.setLevel(level)
    if enable_file:
        file = "LTESnifferRepo.log"
        log_dir = Path(log_dir)
        if not log_dir.is_absolute():
            log_dir = Path(__file__).parent.absolute() / log_dir

        os.makedirs(log_dir, exist_ok=True)

        log_path = Path(log_dir, file)

        fh = logging.handlers.TimedRotatingFileHandler(
            log_path,
            when="S", interval=86400,
            backupCount=100
        )
        fh.doRollover()
        fh.setLevel(level)
        fh.setFormatter(form)
        log.addHandler(fh)

    if enable_stdout:
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(form)
        log.addHandler(sh)

    if enable_syslog:
        # unix only
        sl = logging.handlers.SysLogHandler(address="/dev/log")
        sl.setLevel(level)
        sl.setFormatter(form_syslog)
        log.addHandler(sl)

    # log log_path
    if enable_file:
        logging.debug("Logging to %s", log_path)

    return log


def setup_dynaconf(config_dir: str, settings_file: str) -> Dynaconf:
    """
    Setup dynaconf and validate the given config file.
    :param config_dir: path to config dir
    :param settings_file: Name of the config file.
    :return:
    """
    # path hardcoded - bad
    # determine path
    config_folder = Path(__file__).parent.absolute() / Path(config_dir)
    settings_path = Path(config_folder, settings_file)
    if not settings_path.exists():
        logging.critical("The defined custom config file %s does not exist!",
                         settings_path)
        exit(1)

    # dynaconf
    settings = Dynaconf(
        envvar_prefix="LTESNIFFER",
        settings_file=settings_file,
        environments=True,
        load_dotenv=True,
        dotenv_path=config_folder,
        root_path=config_folder,
        default_env="LTESnifferRepo",
        env="LTESnifferRepo"
    )

    # validate
    settings.validators.register(
        # general
        Validator("general.scan_id", "general.base_dir", is_type_of=str,
                  must_exist=True),

        Validator("general.regions", must_exist=True),

        # search
        Validator("search.enable", "search.rescan", is_type_of=bool,
                  must_exist=True),

        Validator("search.scan_config", "search.results_dir",
                  is_type_of=str, must_exist=True),

        Validator("search.step_width",
                  is_type_of=int, must_exist=True, lte=10, gte=1),

        # record
        Validator("record.results_dir", is_type_of=str,
                  must_exist=True),

        Validator("record.amp_enable", "record.antenna_enable",
                  "record.enable", is_type_of=bool, must_exist=True),

        Validator("record.l_gain", "record.g_gain",
                  is_type_of=int, must_exist=True),

        Validator("record.sample_rate", "record.recording_time",
                  "record.baseband_filter_bw", is_type_of=float,
                  must_exist=True),

        # matlab
        Validator("matlab.enable", is_type_of=bool, must_exist=True)
    )

    # correct incorrect values
    try:
        settings.validators.validate()
    except validator.ValidationError as e:
        logging.exception(e)
        exit(1)

    if (settings.record.l_gain < 0 or settings.record.l_gain > 40
            or settings.record.l_gain % 8 != 0):
        logging.warning("Invalid value for l_gain: %sdB! Setting to %sdB",
                        settings.record.l_gain, 40)
        settings.record.l_gain = 40

    if (settings.record.g_gain < 0 or settings.record.g_gain > 62
            or settings.record.g_gain % 2 != 0):
        logging.warning("Invalid value for g_gain: %sdB! Setting to %sdB",
                        settings.record.g_gain, 40)
        settings.record.g_gain = 40

    if settings.record.sample_rate not in (4e6, 8e6, 10e6, 12.5e6, 16e6,
                                           19.2e6, 20e6):
        logging.warning("Invalid value for sample_rate: %sHz! Setting to %sHz",
                        settings.record.sample_rate, 12.5e6)
        settings.record.sample_rate = 12.5e6

    if settings.record.recording_time < 0.1:
        logging.warning("Invalid value for recording time: %ss! Setting to "
                        "%ss",
                        settings.record.recording_time, 1)
        settings.record.recording_time = 1

    if (settings.record.baseband_filter_bw
            not in (1.75e6, 2.5e6, 3.5e6, 5e6, 5.5e6, 6e6, 7e6, 8e6, 9e6,
                    10e6, 12e6, 14e6, 15e6, 20e6, 24e6, 28e6)):
        logging.warning("Invalid value for baseband_filter_bw: %sHz! "
                        "Setting to %sHz",
                        settings.record.baseband_filter_bw, 20e6)
        settings.record.baseband_filter_bw = 20e6

    return settings


def main():
    """
    Main routine
    :return:
    """
    config_dir = "1_Config"
    log_dir = "2_Logs"

    # setup config
    args = read_arguments()

    configure_logging(args.LOGLEVEL, log_dir, args.ENABLE_STDOUT,
                      args.ENABLE_FILE, args.ENABLE_SYSLOG)

    settings = setup_dynaconf(config_dir, args.CONFIG_FILE)
    if args.VALIDATE_CONFIG:
        return 0

    # ToDO much more :p
    try:
        sniffer = LTESniffer(settings=settings,
                             project_dir=Path(__file__).parent.absolute())
        sniffer.search(fast=args.FAST_SCAN)
        sniffer.record()
    except Exception as e:
        logging.exception(e)
        exit(1)


if __name__ == "__main__":
    main()
