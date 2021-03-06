"""Class to read a project config json file and map to a control object and to save a control object as a json file."""

__author__ = "Craig Dickinson"

import json
import os

from dateutil.parser import parse

from core.control import Control
from core.logger_properties import LoggerProperties
from core.calc_seascatter import Seascatter
from core.calc_transfer_functions import TransferFunctions


class ProjectConfigJSONFile(object):
    def __init__(self):
        # Config data dictionary to be written to a JSON file
        self.data = {}
        self.filename = ""
        self.full_path = ""
        self.warnings = []

    def load_config_data(self, filename):
        """Load project config JSON file and return the dictionary data."""

        with open(filename, encoding="utf-8") as f:
            self.data = json.load(f)

        # Store filename and set directory to project root
        self.filename = os.path.basename(filename)

    def json_to_control(self, control: Control):
        """
        Take JSON config dictionary and map to a Control class object.
        :param control: Instance of Control class.
        :return: Populated control object.
        """

        # Store config filename
        control.config_file = self.filename
        data = self.data
        control = self._map_general(data, control)
        control = self._map_loggers(data, control)

        return control

    def json_to_seascatter(self, scatter: Seascatter):
        """
        Take JSON config dictionary and map to a Seascatter class object.
        :param scatter: Instance of Seascatter class.
        :return: Populated scatter object.
        """

        data = self.data
        scatter = self._map_seascatter(data, scatter)

        return scatter

    def json_to_transfer_functions(self, tf: TransferFunctions):
        """
        Take JSON config dictionary and map to a TransferFunctions class object.
        :param tf: Instance of TransferFunctions class.
        :return: Populated tf object.
        """

        data = self.data
        tf = self._map_transfer_functions(data, tf)

        return tf

    def _map_general(self, data, control: Control):
        """Map the general settings section to the control object."""

        key = "general"
        if key in data:
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.warnings.append(msg)
            return control

        control.project_num = self._get_key_value(
            section=key, data=data, key="project_number", attr=control.project_num
        )
        control.project_name = self._get_key_value(
            section=key, data=data, key="project_name", attr=control.project_name
        )
        control.campaign_name = self._get_key_value(
            section=key, data=data, key="campaign_name", attr=control.campaign_name
        )
        control.project_path = self._get_key_value(
            section=key, data=data, key="project_location", attr=control.project_path
        )
        control.azure_account_name = self._get_key_value(
            section=key, data=data, key="azure_account_name", attr=control.azure_account_name
        )
        control.azure_account_key = self._get_key_value(
            section=key, data=data, key="azure_account_key", attr=control.azure_account_key
        )
        control.filter_type = self._get_key_value(
            section=key, data=data, key="filter_type", attr=control.filter_type
        )
        control.butterworth_order = self._get_key_value(
            section=key, data=data, key="butterworth_order", attr=control.butterworth_order
        )
        control.global_process_stats = self._get_key_value(
            section=key, data=data, key="global_process_stats", attr=control.global_process_stats
        )
        control.global_process_spect = self._get_key_value(
            section=key, data=data, key="global_process_spectral", attr=control.global_process_spect
        )
        control.stats_output_folder = self._get_key_value(
            section=key, data=data, key="stats_folder", attr=control.stats_output_folder
        )
        control.spect_output_folder = self._get_key_value(
            section=key, data=data, key="spectral_folder", attr=control.spect_output_folder
        )
        control.hist_output_folder = self._get_key_value(
            section=key, data=data, key="histogram_folder", attr=control.hist_output_folder
        )
        control.integration_output_folder = self._get_key_value(
            section=key, data=data, key="integration_folder", attr=control.integration_output_folder
        )
        control.stats_to_csv = self._get_key_value(
            section=key, data=data, key="stats_to_csv", attr=control.stats_to_csv
        )
        control.stats_to_xlsx = self._get_key_value(
            section=key, data=data, key="stats_to_xlsx", attr=control.stats_to_xlsx
        )
        control.stats_to_h5 = self._get_key_value(
            section=key, data=data, key="stats_to_h5", attr=control.stats_to_h5
        )
        control.spect_to_csv = self._get_key_value(
            section=key, data=data, key="spectral_to_csv", attr=control.spect_to_csv
        )
        control.spect_to_xlsx = self._get_key_value(
            section=key, data=data, key="spectral_to_xlsx", attr=control.spect_to_xlsx
        )
        control.spect_to_h5 = self._get_key_value(
            section=key, data=data, key="spectral_to_h5", attr=control.spect_to_h5
        )
        control.hist_to_csv = self._get_key_value(
            section=key, data=data, key="histogram_to_csv", attr=control.hist_to_csv
        )
        control.hist_to_xlsx = self._get_key_value(
            section=key, data=data, key="histogram_to_xlsx", attr=control.hist_to_xlsx
        )
        control.hist_to_h5 = self._get_key_value(
            section=key, data=data, key="histogram_to_h5", attr=control.hist_to_h5
        )

        return control

    def _map_loggers(self, data, control: Control):
        """Map the config loggers section to the control object for all logger."""

        key = "loggers"
        if key in data:
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.warnings.append(msg)
            return control

        for logger_id, dict_logger in data.items():
            # Create new logger properties object and assign attributes from JSON dictionary
            logger = LoggerProperties(logger_id)

            # Logger properties
            logger = self._map_logger_props(logger, dict_logger)

            # Logger screening settings
            logger = self._map_logger_screening_settings(logger, dict_logger)

            # Logger histogram settings
            logger = self._map_logger_histogram_settings(logger, dict_logger)

            # Logger time series integration settings
            logger = self._map_logger_integration_settings(logger, dict_logger)

            # Map Azure account settings (if any) to logger
            logger.azure_account_name = control.azure_account_name
            logger.azure_account_key = control.azure_account_key

            # Finally, assign logger to control object
            control.logger_ids.append(logger_id)
            control.logger_ids_upper.append(logger_id.upper())
            control.loggers.append(logger)

        return control

    def _map_seascatter(self, data, scatter: Seascatter):
        """Map the seascatter settings section to the transfer function object."""

        key = "seascatter"
        if key in data:
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.warnings.append(msg)
            return scatter

        scatter.metocean_logger = self._get_key_value(
            section=key, data=data, key="metocean_logger_id", attr=scatter.metocean_logger
        )
        scatter.hs_col = self._get_key_value(
            section=key, data=data, key="hs_column", attr=scatter.hs_col
        )
        scatter.tp_col = self._get_key_value(
            section=key, data=data, key="tp_column", attr=scatter.tp_col
        )
        scatter.hs_col_idx = self._get_key_value(
            section=key, data=data, key="hs_col_idx", attr=scatter.hs_col_idx
        )
        scatter.tp_col_idx = self._get_key_value(
            section=key, data=data, key="tp_col_idx", attr=scatter.tp_col_idx
        )

        return scatter

    def _map_transfer_functions(self, data, tf: TransferFunctions):
        """Map the transfer functions settings section to the transfer function object."""

        key = "transfer_functions"
        if key in data:
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.warnings.append(msg)
            return tf

        tf.disp_dir = self._get_key_value(
            section=key, data=data, key="logger_disp_path", attr=tf.disp_dir
        )
        tf.rot_dir = self._get_key_value(
            section=key, data=data, key="logger_rot_path", attr=tf.rot_dir
        )
        tf.bm_dir = self._get_key_value(
            section=key, data=data, key="location_bm_path", attr=tf.bm_dir
        )
        tf.num_loggers = self._get_key_value(
            section=key, data=data, key="num_fea_loggers", attr=tf.num_loggers
        )
        tf.num_locs = self._get_key_value(
            section=key, data=data, key="num_fea_locations", attr=tf.num_locs
        )
        tf.num_ss = self._get_key_value(
            section=key, data=data, key="num_fea_seastates", attr=tf.num_ss
        )
        tf.logger_names = self._get_key_value(
            section=key, data=data, key="logger_names", attr=tf.logger_names
        )
        tf.loc_names = self._get_key_value(
            section=key, data=data, key="location_names", attr=tf.loc_names
        )
        tf.perc_occ = self._get_key_value(
            section=key, data=data, key="seastate_perc_occ", attr=tf.perc_occ
        )

        return tf

    def _map_logger_props(self, logger: LoggerProperties, dict_logger):
        """Retrieve logger properties from JSON dictionary and map to logger object."""

        logger.enabled = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="enabled", attr=logger.enabled
        )
        logger.data_on_azure = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="data_on_azure",
            attr=logger.data_on_azure,
        )
        logger.logger_path = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="logger_path", attr=logger.logger_path
        )
        logger.file_format = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="file_format", attr=logger.file_format
        )
        logger.file_timestamp_embedded = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="file_timestamp_embedded",
            attr=logger.file_timestamp_embedded,
        )
        logger.file_timestamp_format = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="file_timestamp_format",
            attr=logger.file_timestamp_format,
        )
        logger.first_col_data = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="first_col_data",
            attr=logger.first_col_data,
        )
        logger.file_ext = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="file_ext", attr=logger.file_ext
        )
        logger.file_delimiter = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="file_delimiter",
            attr=logger.file_delimiter,
        )
        logger.num_headers = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="num_header_rows",
            attr=logger.num_headers,
        )
        logger.channel_header_row = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="channel_header_row",
            attr=logger.channel_header_row,
        )
        logger.units_header_row = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="units_header_row",
            attr=logger.units_header_row,
        )
        logger.timestamp_format = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="data_timestamp_format",
            attr=logger.timestamp_format,
        )
        logger.datetime_format = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="data_datetime_format",
            attr=logger.datetime_format,
        )
        logger.num_columns = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="num_columns", attr=logger.num_columns
        )
        logger.freq = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="logging_freq", attr=logger.freq
        )
        logger.duration = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="logging_duration", attr=logger.duration
        )
        logger.enforce_max_duration = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="enforce_max_duration",
            attr=logger.enforce_max_duration,
        )
        logger.index_col_name = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="index_column_name",
            attr=logger.index_col_name,
        )
        logger.all_channel_names = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="all_channel_names",
            attr=logger.all_channel_names,
        )
        logger.all_channel_units = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="all_channel_units",
            attr=logger.all_channel_units,
        )

        return logger

    def _map_logger_screening_settings(self, logger: LoggerProperties, dict_logger):
        """Retrieve logger screening settings from JSON dictionary and map to logger object."""

        logger.cols_to_process = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="columns_to_process",
            attr=logger.cols_to_process,
        )
        logger.unit_conv_factors = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="unit_convs",
            attr=logger.unit_conv_factors,
        )
        logger.user_channel_names = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="user_channel_names",
            attr=logger.user_channel_names,
        )
        logger.user_channel_units = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="user_channel_units",
            attr=logger.user_channel_units,
        )
        process_start = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_start",
            attr=logger.process_start,
        )

        # Start file index used
        if process_start is None:
            logger.process_start = None
        elif type(process_start) is int:
            logger.process_start = process_start
        # Start date used - convert to datetime
        else:
            try:
                logger.process_start = parse(process_start, yearfirst=True)
            except ValueError:
                msg = f"Process start format not recognised for logger {logger.logger_id}."
                self.warnings.append(msg)

        process_end = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="process_end", attr=logger.process_end
        )

        # End file index used
        if process_end is None:
            logger.process_end = None
        elif type(process_end) is int:
            logger.process_end = process_end
        # End date used - convert to datetime
        else:
            try:
                logger.process_end = parse(process_end, yearfirst=True)
            except ValueError:
                msg = f"Process end format not recognised for logger {logger.logger_id}."
                self.warnings.append(msg)

        logger.num_selected_files = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="number_of_selected_files",
            attr=logger.num_selected_files,
        )
        logger.process_type = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="process_type", attr=logger.process_type
        )
        logger.low_cutoff_freq = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="low_cutoff_freq",
            attr=logger.low_cutoff_freq,
        )
        logger.high_cutoff_freq = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="high_cutoff_freq",
            attr=logger.high_cutoff_freq,
        )
        logger.process_stats = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_stats",
            attr=logger.process_stats,
        )
        logger.stats_interval = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="stats_interval",
            attr=logger.stats_interval,
        )
        logger.process_spect = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_spectral",
            attr=logger.process_spect,
        )
        logger.spect_interval = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="spectral_interval",
            attr=logger.spect_interval,
        )
        logger.psd_nperseg = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="psd_num_points_per_segment",
            attr=logger.psd_nperseg,
        )
        logger.psd_window = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="psd_window", attr=logger.psd_window
        )
        logger.psd_overlap = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="psd_overlap", attr=logger.psd_overlap
        )

        return logger

    def _map_logger_histogram_settings(self, logger, dict_logger):
        """Retrieve logger rainflow histogram settings from JSON dictionary and map to logger object."""

        logger.process_hists = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_histograms",
            attr=logger.process_hists,
        )
        logger.channel_bin_sizes = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="channel_bin_sizes",
            attr=logger.channel_bin_sizes,
        )
        logger.channel_num_bins = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="channel_num_bins",
            attr=logger.channel_num_bins,
        )
        return logger

    def _map_logger_integration_settings(self, logger: LoggerProperties, dict_logger):
        """Retrieve logger time series integration settings from JSON dictionary and map to logger object."""

        logger.process_integration = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_integration",
            attr=logger.process_integration,
        )
        logger.apply_gcorr = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="apply_gravity_correction",
            attr=logger.apply_gcorr,
        )
        logger.output_rms_summary = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="output_rms_summary",
            attr=logger.output_rms_summary,
        )
        logger.acc_x_col = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="acc_x_col", attr=logger.acc_x_col
        )
        logger.acc_y_col = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="acc_y_col", attr=logger.acc_y_col
        )
        logger.acc_z_col = self._get_key_value(
            section=logger.logger_id, data=dict_logger, key="acc_z_col", attr=logger.acc_z_col
        )
        logger.ang_rate_x_col = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_x_col",
            attr=logger.ang_rate_x_col,
        )
        logger.ang_rate_y_col = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_y_col",
            attr=logger.ang_rate_y_col,
        )
        logger.acc_x_units_conv = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_x_units_conv",
            attr=logger.acc_x_units_conv,
        )
        logger.acc_y_units_conv = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_y_units_conv",
            attr=logger.acc_y_units_conv,
        )
        logger.acc_z_units_conv = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_z_units_conv",
            attr=logger.acc_z_units_conv,
        )
        logger.ang_rate_x_units_conv = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_x_units_conv",
            attr=logger.ang_rate_x_units_conv,
        )
        logger.ang_rate_y_units_conv = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_y_units_conv",
            attr=logger.ang_rate_y_units_conv,
        )
        logger.acc_x_low_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_x_low_cutoff",
            attr=logger.acc_x_low_cutoff,
        )
        logger.acc_y_low_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_y_low_cutoff",
            attr=logger.acc_y_low_cutoff,
        )
        logger.acc_z_low_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_z_low_cutoff",
            attr=logger.acc_z_low_cutoff,
        )
        logger.ang_rate_x_low_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_x_low_cutoff",
            attr=logger.ang_rate_x_low_cutoff,
        )
        logger.ang_rate_y_low_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_y_low_cutoff",
            attr=logger.ang_rate_y_low_cutoff,
        )
        logger.acc_x_high_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_x_high_cutoff",
            attr=logger.acc_x_high_cutoff,
        )
        logger.acc_y_high_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_y_high_cutoff",
            attr=logger.acc_y_high_cutoff,
        )
        logger.acc_z_high_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="acc_z_high_cutoff",
            attr=logger.acc_z_high_cutoff,
        )
        logger.ang_rate_x_high_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_x_high_cutoff",
            attr=logger.ang_rate_x_high_cutoff,
        )
        logger.ang_rate_y_high_cutoff = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="ang_rate_y_high_cutoff",
            attr=logger.ang_rate_y_high_cutoff,
        )

        return logger

    def _get_key_value(self, section, data, key, attr=None):
        """Assign data from a JSON key to control object attribute."""

        if key in data:
            return data[key]
        else:
            msg = f"'{key}' key not found in config file under '{section}' dictionary."
            self.warnings.append(msg)
            return attr

    def add_general_settings(self, control: Control):
        """Add general settings."""

        d = dict()
        d["project_number"] = control.project_num
        d["project_name"] = control.project_name
        d["campaign_name"] = control.campaign_name
        d["project_location"] = control.project_path
        d["azure_account_name"] = control.azure_account_name
        d["azure_account_key"] = control.azure_account_key
        d["filter_type"] = control.filter_type
        d["butterworth_order"] = control.butterworth_order
        d["global_process_stats"] = control.global_process_stats
        d["global_process_spectral"] = control.global_process_spect
        d["stats_folder"] = control.stats_output_folder
        d["spectral_folder"] = control.spect_output_folder
        d["histogram_folder"] = control.hist_output_folder
        d["integration_folder"] = control.integration_output_folder
        d["stats_to_csv"] = control.stats_to_csv
        d["stats_to_xlsx"] = control.stats_to_xlsx
        d["stats_to_h5"] = control.stats_to_h5
        d["spectral_to_csv"] = control.spect_to_csv
        d["spectral_to_xlsx"] = control.spect_to_xlsx
        d["spectral_to_h5"] = control.spect_to_h5
        d["histogram_to_csv"] = control.hist_to_csv
        d["histogram_to_xlsx"] = control.hist_to_xlsx
        d["histogram_to_h5"] = control.hist_to_h5

        self.data["general"] = d

    def add_loggers_settings(self, loggers):
        """Add properties of all loggers."""

        if not loggers:
            return

        self.data["loggers"] = dict()

        for logger in loggers:
            dict_props = dict()

            # Add logger properties
            dict_props = self._add_logger_props(logger, dict_props)

            # Add logger stats and spectral settings
            dict_props = self._add_logger_screening_settings(logger, dict_props)

            # Add logger histogram settings
            dict_props = self._add_logger_histogram_settings(logger, dict_props)

            # Add logger conversion settings
            dict_props = self._add_logger_integration_settings(logger, dict_props)

            # Add logger props dictionary to loggers dictionary
            self.data["loggers"][logger.logger_id] = dict_props

    def add_seascatter_settings(self, scatter: Seascatter):
        """Add seascatter settings."""

        d = dict()
        d["metocean_logger_id"] = scatter.metocean_logger
        d["hs_column"] = scatter.hs_col
        d["tp_column"] = scatter.tp_col
        d["hs_col_idx"] = scatter.hs_col_idx
        d["tp_col_idx"] = scatter.tp_col_idx

        self.data["seascatter"] = d

    def add_transfer_functions_settings(self, tf: TransferFunctions):
        """Add transfer functions settings."""

        d = dict()
        d["logger_disp_path"] = tf.disp_dir
        d["logger_rot_path"] = tf.rot_dir
        d["location_bm_path"] = tf.bm_dir
        d["num_fea_loggers"] = tf.num_loggers
        d["num_fea_locations"] = tf.num_locs
        d["num_fea_seastates"] = tf.num_ss
        d["logger_names"] = tf.logger_names
        d["location_names"] = tf.loc_names
        d["seastate_perc_occ"] = tf.perc_occ

        self.data["transfer_functions"] = d

    @staticmethod
    def _add_logger_props(logger: LoggerProperties, dict_props):
        """Add control object logger properties to JSON dictionary."""

        dict_props["enabled"] = logger.enabled
        dict_props["data_on_azure"] = logger.data_on_azure
        dict_props["logger_path"] = logger.logger_path
        dict_props["file_format"] = logger.file_format
        dict_props["file_timestamp_embedded"] = logger.file_timestamp_embedded
        dict_props["file_timestamp_format"] = logger.file_timestamp_format
        dict_props["first_col_data"] = logger.first_col_data
        dict_props["file_ext"] = logger.file_ext
        dict_props["file_delimiter"] = logger.file_delimiter
        dict_props["num_header_rows"] = logger.num_headers
        dict_props["channel_header_row"] = logger.channel_header_row
        dict_props["units_header_row"] = logger.units_header_row
        dict_props["data_timestamp_format"] = logger.timestamp_format
        dict_props["data_datetime_format"] = logger.datetime_format
        dict_props["num_columns"] = logger.num_columns
        dict_props["logging_freq"] = logger.freq
        dict_props["logging_duration"] = logger.duration
        dict_props["enforce_max_duration"] = logger.enforce_max_duration
        dict_props["index_column_name"] = logger.index_col_name
        dict_props["all_channel_names"] = logger.all_channel_names
        dict_props["all_channel_units"] = logger.all_channel_units

        return dict_props

    @staticmethod
    def _add_logger_screening_settings(logger: LoggerProperties, dict_props):
        """Add control object logger stats and spectral settings to JSON dictionary."""

        # Processed columns group
        dict_props["columns_to_process"] = logger.cols_to_process
        dict_props["unit_convs"] = logger.unit_conv_factors
        dict_props["user_channel_names"] = logger.user_channel_names
        dict_props["user_channel_units"] = logger.user_channel_units

        # Need to convert start and end datetimes to strings to write to JSON format
        # Process start
        if logger.process_start is None:
            dict_props["process_start"] = None
        else:
            # Start date used
            if logger.file_timestamp_embedded is True:
                dict_props["process_start"] = logger.process_start.strftime("%Y-%m-%d %H:%M")
            # Start file index used
            else:
                dict_props["process_start"] = logger.process_start

        # Process end
        if logger.process_end is None:
            dict_props["process_end"] = None
        else:
            # End date used
            if logger.file_timestamp_embedded is True:
                dict_props["process_end"] = logger.process_end.strftime("%Y-%m-%d %H:%M")
            else:
                dict_props["process_end"] = logger.process_end

        # Number of files to process
        dict_props["number_of_selected_files"] = logger.num_selected_files

        # Data type to screen on
        dict_props["process_type"] = logger.process_type

        # Stats low and high cut-off frequencies
        dict_props["low_cutoff_freq"] = logger.low_cutoff_freq
        dict_props["high_cutoff_freq"] = logger.high_cutoff_freq

        # Stats settings group
        dict_props["process_stats"] = logger.process_stats
        dict_props["stats_interval"] = logger.stats_interval

        # Spectral settings group
        dict_props["process_spectral"] = logger.process_spect
        dict_props["spectral_interval"] = logger.spect_interval
        dict_props["psd_num_points_per_segment"] = logger.psd_nperseg
        dict_props["psd_window"] = logger.psd_window
        dict_props["psd_overlap"] = logger.psd_overlap

        return dict_props

    @staticmethod
    def _add_logger_histogram_settings(logger: LoggerProperties, dict_props):
        """Add control object logger histogram settings to JSON dictionary."""

        dict_props["process_histograms"] = logger.process_hists
        dict_props["channel_bin_sizes"] = logger.channel_bin_sizes
        dict_props["channel_num_bins"] = logger.channel_num_bins

        return dict_props

    @staticmethod
    def _add_logger_integration_settings(logger: LoggerProperties, dict_props):
        """Add control object logger time series integration settings to JSON dictionary."""

        dict_props["process_integration"] = logger.process_integration
        dict_props["apply_gravity_correction"] = logger.apply_gcorr
        dict_props["output_rms_summary"] = logger.output_rms_summary
        dict_props["acc_x_col"] = logger.acc_x_col
        dict_props["acc_y_col"] = logger.acc_y_col
        dict_props["acc_z_col"] = logger.acc_z_col
        dict_props["ang_rate_x_col"] = logger.ang_rate_x_col
        dict_props["ang_rate_y_col"] = logger.ang_rate_y_col
        dict_props["acc_x_units_conv"] = logger.acc_x_units_conv
        dict_props["acc_y_units_conv"] = logger.acc_y_units_conv
        dict_props["acc_z_units_conv"] = logger.acc_z_units_conv
        dict_props["ang_rate_x_units_conv"] = logger.ang_rate_x_units_conv
        dict_props["ang_rate_y_units_conv"] = logger.ang_rate_y_units_conv
        dict_props["acc_x_low_cutoff"] = logger.acc_x_low_cutoff
        dict_props["acc_y_low_cutoff"] = logger.acc_y_low_cutoff
        dict_props["acc_z_low_cutoff"] = logger.acc_z_low_cutoff
        dict_props["ang_rate_x_low_cutoff"] = logger.ang_rate_x_low_cutoff
        dict_props["ang_rate_y_low_cutoff"] = logger.ang_rate_y_low_cutoff
        dict_props["acc_x_high_cutoff"] = logger.acc_x_high_cutoff
        dict_props["acc_y_high_cutoff"] = logger.acc_y_high_cutoff
        dict_props["acc_z_high_cutoff"] = logger.acc_z_high_cutoff
        dict_props["ang_rate_x_high_cutoff"] = logger.ang_rate_x_high_cutoff
        dict_props["ang_rate_y_high_cutoff"] = logger.ang_rate_y_high_cutoff

        return dict_props

    def save_config(self, proj_path, filename):
        """Export project configuration data as JSON file."""

        self.filename = filename
        self.full_path = os.path.join(proj_path, filename)

        # Save as JSON file
        # Prevent ascii characters in file. Indent gives nicer layout instead of one long line string
        with open(self.full_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, sort_keys=False, ensure_ascii=False)
