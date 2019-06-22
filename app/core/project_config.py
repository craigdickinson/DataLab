import json
import os

from PyQt5.QtCore import QObject, pyqtSignal
from dateutil.parser import parse

from app.core.logger_properties import LoggerProperties


class ProjectConfigJSONFile(QObject):
    signal_warning = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Config data dictionary to be written to a JSON file
        self.data = {}
        self.filename = ""
        self.full_path = ""

    def load_config_data(self, file_name):
        """Load project config JSON file and return the dictionary data."""

        with open(file_name, encoding="utf-8") as f:
            self.data = json.load(f)

        # Store filename and set directory to project root
        file_path, self.filename = os.path.split(file_name)

    def map_json_to_control(self, control):
        """
        Take JSON config dictionary and map to a Control class object.
        :param control: Instance of Control class.
        :return: Populated control object.
        """

        data = self.data
        control = self._map_campaign_dict(data, control)
        control = self._map_loggers_dict(data, control)
        control = self._map_general_dict(data, control)

        return control

    def map_json_to_seascatter(self, scatter):
        """
        Take JSON config dictionary and map to a Seascatter class object.
        :param scatter: Instance of Seascatter class.
        :return: Populated scatter object.
        """

        data = self.data
        scatter = self._map_seascatter_dict(data, scatter)

        return scatter

    def map_json_to_transfer_functions(self, tf):
        """
        Take JSON config dictionary and map to a TransferFunctions class object.
        :param tf: Instance of TransferFunctions class.
        :return: Populated tf object.
        """

        data = self.data
        tf = self._map_transfer_functions_dict(data, tf)

        return tf

    def _map_campaign_dict(self, data, control):
        """Map the config campaign section to the control object."""

        key = "campaign"
        if key in data.keys():
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.signal_warning.emit(msg)
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
        control.config_file = self.filename

        return control

    def _map_loggers_dict(self, data, control):
        """Map the config loggers section to the control object for all logger."""

        key = "loggers"
        if key in data.keys():
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.signal_warning.emit(msg)
            return control

        for logger_id, dict_logger in data.items():
            # Create new logger properties object and assign attributes from JSON dictionary
            logger = LoggerProperties()
            logger.logger_id = logger_id

            # Logger properties
            logger = self._map_logger_props(logger, dict_logger)

            # Logger screening settings
            logger = self._map_logger_screening_settings(logger, dict_logger)

            # Finally, assign logger to control object
            control.logger_ids.append(logger_id)
            control.logger_ids_upper.append(logger_id.upper())
            control.loggers.append(logger)

        return control

    def _map_logger_props(self, logger, dict_logger):
        """Retrieve logger properties from JSON dictionary and map to logger object."""

        logger.file_format = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="file_format",
            attr=logger.file_format,
        )
        logger.logger_path = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="logger_path",
            attr=logger.logger_path,
        )
        logger.file_timestamp_format = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="file_timestamp_format",
            attr=logger.file_timestamp_format,
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
        logger.file_ext = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="file_ext",
            attr=logger.file_ext,
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
        logger.num_columns = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="num_columns",
            attr=logger.num_columns,
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
        logger.freq = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="logging_freq",
            attr=logger.freq,
        )
        logger.duration = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="logging_duration",
            attr=logger.duration,
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

    def _map_logger_screening_settings(self, logger, dict_logger):
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
        if process_start is None:
            logger.process_start = None
        else:
            try:
                # Need to convert process start to datetime
                logger.process_start = parse(process_start, yearfirst=True)
            except ValueError:
                msg = f"Process start format not recognised for logger {logger.logger_id}."
                self.signal_warning.emit(msg)

        process_end = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_end",
            attr=logger.process_end,
        )
        if process_end is None:
            logger.process_end = None
        else:
            try:
                # Need to convert process end to datetime
                logger.process_end = parse(process_end, yearfirst=True)
            except ValueError:
                msg = (
                    f"Process end format not recognised for logger {logger.logger_id}."
                )
                self.signal_warning.emit(msg)

        logger.process_type = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_type",
            attr=logger.process_type,
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
        logger.process_spectral = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="process_spectral",
            attr=logger.process_spectral,
        )
        logger.spect_interval = self._get_key_value(
            section=logger.logger_id,
            data=dict_logger,
            key="spectral_interval",
            attr=logger.spect_interval,
        )
        return logger

    def _map_general_dict(self, data, control):
        """Map the general settings section to the control object."""

        key = "general"
        if key in data.keys():
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.signal_warning.emit(msg)
            return control

        control.stats_output_folder = self._get_key_value(
            section=key, data=data, key="stats_folder", attr=control.stats_output_folder
        )
        control.spect_output_folder = self._get_key_value(
            section=key,
            data=data,
            key="spectral_folder",
            attr=control.spect_output_folder,
        )
        control.stats_to_h5 = self._get_key_value(
            section=key, data=data, key="stats_to_h5", attr=control.stats_to_h5
        )
        control.stats_to_csv = self._get_key_value(
            section=key, data=data, key="stats_to_csv", attr=control.stats_to_csv
        )
        control.stats_to_xlsx = self._get_key_value(
            section=key, data=data, key="stats_to_xlsx", attr=control.stats_to_xlsx
        )
        control.spect_to_h5 = self._get_key_value(
            section=key, data=data, key="spectral_to_h5", attr=control.spect_to_h5
        )
        control.spect_to_csv = self._get_key_value(
            section=key, data=data, key="spectral_to_csv", attr=control.spect_to_csv
        )
        control.spect_to_xlsx = self._get_key_value(
            section=key, data=data, key="spectral_to_xlsx", attr=control.spect_to_xlsx
        )

        return control

    def _map_seascatter_dict(self, data, scatter):
        """Map the seascatter settings section to the transfer function object."""

        key = "seascatter"
        if key in data.keys():
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.signal_warning.emit(msg)
            return scatter

        scatter.metocean_logger = self._get_key_value(
            section=key,
            data=data,
            key="metocean_logger_id",
            attr=scatter.metocean_logger,
        )
        scatter.hs_col = self._get_key_value(
            section=key, data=data, key="hs_column", attr=scatter.hs_col
        )
        scatter.tp_col = self._get_key_value(
            section=key, data=data, key="tp_column", attr=scatter.tp_col
        )

        return scatter

    def _map_transfer_functions_dict(self, data, tf):
        """Map the transfer functions settings section to the transfer function object."""

        key = "transfer_functions"
        if key in data.keys():
            data = data[key]
        else:
            msg = f"'{key}' key not found in config file."
            self.signal_warning.emit(msg)
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

    def _get_key_value(self, section, data, key, attr=None):
        """Assign data from a JSON key to control object attribute."""

        if key in data.keys():
            return data[key]
        else:
            msg = f"'{key}' key not found in config file for {section} dictionary."
            self.signal_warning.emit(msg)
            return attr

    def add_campaign_settings(self, control):
        """Add project and campaign details."""

        d = dict()
        d["project_number"] = control.project_num
        d["project_name"] = control.project_name
        d["campaign_name"] = control.campaign_name
        d["project_location"] = control.project_path

        self.data["campaign"] = d

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

            # Add logger props dictionary to loggers dictionary
            self.data["loggers"][logger.logger_id] = dict_props

    def add_general_settings(self, control):
        """Add general settings."""

        d = dict()
        d["stats_folder"] = control.stats_output_folder
        d["spectral_folder"] = control.spect_output_folder
        d["stats_to_h5"] = control.stats_to_h5
        d["stats_to_csv"] = control.stats_to_csv
        d["stats_to_xlsx"] = control.stats_to_xlsx
        d["spectral_to_h5"] = control.spect_to_h5
        d["spectral_to_csv"] = control.spect_to_csv
        d["spectral_to_xlsx"] = control.spect_to_xlsx

        self.data["general"] = d

    def add_seascatter_settings(self, scatter):
        """Add seascatter settings."""

        d = dict()
        d["metocean_logger_id"] = scatter.metocean_logger
        d["hs_column"] = scatter.hs_col
        d["tp_column"] = scatter.tp_col

        self.data["seascatter"] = d

    def add_transfer_functions_settings(self, tf):
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
    def _add_logger_props(logger, dict_props):
        """Add control object logger properties to JSON dictionary."""

        dict_props["file_format"] = logger.file_format
        dict_props["logger_path"] = logger.logger_path
        dict_props["file_timestamp_format"] = logger.file_timestamp_format
        dict_props["data_timestamp_format"] = logger.timestamp_format
        dict_props["data_datetime_format"] = logger.datetime_format
        dict_props["file_ext"] = logger.file_ext
        dict_props["file_delimiter"] = logger.file_delimiter
        dict_props["num_header_rows"] = logger.num_headers
        dict_props["num_columns"] = logger.num_columns
        dict_props["channel_header_row"] = logger.channel_header_row
        dict_props["units_header_row"] = logger.units_header_row
        dict_props["logging_freq"] = logger.freq
        dict_props["logging_duration"] = logger.duration
        dict_props["all_channel_names"] = logger.all_channel_names
        dict_props["all_channel_units"] = logger.all_channel_units

        return dict_props

    @staticmethod
    def _add_logger_screening_settings(logger, dict_props):
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
            dict_props["process_start"] = logger.process_start.strftime(
                "%Y-%m-%d %H:%M"
            )

        # Process end
        if logger.process_end is None:
            dict_props["process_end"] = None
        else:
            dict_props["process_end"] = logger.process_end.strftime("%Y-%m-%d %H:%M")

        # Data type to screen on
        dict_props["process_type"] = logger.process_type

        # Stats low and high cut-off frequencies
        dict_props["low_cutoff_freq"] = logger.low_cutoff_freq
        dict_props["high_cutoff_freq"] = logger.high_cutoff_freq

        # Stats settings group
        dict_props["process_stats"] = logger.process_stats
        dict_props["stats_interval"] = logger.stats_interval

        # Spectral settings group
        dict_props["process_spectral"] = logger.process_spectral
        dict_props["spectral_interval"] = logger.spect_interval

        return dict_props

    def save_config(self, proj_num, proj_name, proj_path):
        """Export project configuration data as JSON file."""

        # Create file path to save to
        proj_name = "_".join(proj_name.split())
        self.filename = "_".join((proj_num, proj_name, "Config.json"))
        self.full_path = os.path.join(proj_path, self.filename)

        # Save as JSON file
        # Prevent ascii characters in file. Indent gives nicer layout instead of one long line string
        with open(self.full_path, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(self.data, indent=4, sort_keys=False, ensure_ascii=False)
            )
