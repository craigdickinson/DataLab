import json
import os


class ProjectConfigJSONFile:
    def __init__(self):
        # Config data dictionary to be written to a JSON file
        self.data = {}
        self.filename = ""
        self.full_path = ""

    def load_config_data(self, file_name):
        """Load project config JSON file and return the dictionary data."""

        with open(file_name, encoding="utf-8") as f:
            data = json.load(f)

        # Store filename and set directory to project root
        file_path, self.filename = os.path.split(file_name)

        return data

    def add_campaign_data(self, control):
        """Add project and campaign details."""

        d = dict()
        d["project_number"] = control.project_num
        d["project_name"] = control.project_name
        d["campaign_name"] = control.campaign_name
        d["project_location"] = control.project_path

        self.data["campaign"] = d

    def add_logger_data(self, loggers):
        """Add properties of all loggers."""

        if not loggers:
            return

        self.data["loggers"] = dict()

        for logger in loggers:
            dict_props = dict()

            # Add logger properties
            dict_props = self.add_logger_props(logger, dict_props)

            # Add logger stats and spectral settings
            dict_props = self.add_logger_analysis_settings(logger, dict_props)

            # Add logger props dictionary to loggers dictionary
            self.data["loggers"][logger.logger_id] = dict_props

    def add_general_data(self, control):
        """Add general settings."""

        d = dict()
        d["stats_to_h5"] = control.stats_to_h5
        d["stats_to_csv"] = control.stats_to_csv
        d["stats_to_xlsx"] = control.stats_to_xlsx
        d["spectral_to_h5"] = control.spect_to_h5
        d["spectral_to_csv"] = control.spect_to_csv
        d["spectral_to_xlsx"] = control.spect_to_xlsx

        self.data["general"] = d

    def add_logger_props(self, logger, dict_props):
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

    def add_logger_analysis_settings(self, logger, dict_props):
        """Add control object logger stats and spectral settings to JSON dictionary."""

        # Processed columns group
        dict_props["requested_columns"] = logger.requested_cols
        dict_props["unit_convs"] = logger.unit_conv_factors
        dict_props["user_channel_names"] = logger.user_channel_names
        dict_props["user_channel_units"] = logger.user_channel_units

        # Stats settings group
        dict_props["process_stats"] = logger.process_stats
        dict_props["stats_interval"] = logger.stats_interval

        # Need to convert start and end datetimes to strings to write to JSON format
        # Stats start
        if logger.stats_start is None:
            dict_props["stats_start"] = None
        else:
            dict_props["stats_start"] = logger.stats_start.strftime("%Y-%m-%d %H:%M")

        # Stats end
        if logger.stats_end is None:
            dict_props["stats_end"] = None
        else:
            dict_props["stats_end"] = logger.stats_end.strftime("%Y-%m-%d %H:%M")

        # Stats low and high cut-off frequencies
        dict_props["stats_low_cutoff_freq"] = logger.stats_low_cutoff_freq
        dict_props["stats_high_cutoff_freq"] = logger.stats_high_cutoff_freq

        # Spectral settings group
        dict_props["process_spectral"] = logger.process_spectral
        dict_props["spectral_interval"] = logger.spectral_interval

        # Spectral start
        if logger.spectral_start is None:
            dict_props["spectral_start"] = None
        else:
            dict_props["spectral_start"] = logger.spectral_start.strftime(
                "%Y-%m-%d %H:%M"
            )

        # Spectral end
        if logger.spectral_end is None:
            dict_props["spectral_end"] = None
        else:
            dict_props["spectral_end"] = logger.spectral_end.strftime("%Y-%m-%d %H:%M")

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
