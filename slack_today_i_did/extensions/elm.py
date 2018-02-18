from collections import defaultdict

from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages


class ElmExtensions(BotExtension):
    def elm_progress(self, channel: str, version: str) -> ChannelMessages:
        """ give a version of elm to get me to tell you how many number files are on master """

        version = version.strip()
        self.repo.get_ready()
        message = ""

        if version == '0.17':
            message += f"There are {self.repo.number_of_016_files}"
        elif version == '0.16':
            message += f"There are {self.repo.number_of_017_files}"
        else:
            num_016 = self.repo.number_of_016_files
            num_017 = self.repo.number_of_017_files
            message += f"There are {num_016} 0.16 files."
            message += f"\nThere are {num_017} 0.17 files."
            message += f"\nThat puts us at a total of {num_017 + num_016} Elm files."

        return ChannelMessage(channel, message)

    def elm_progress_on(self, channel: str, branch_name: str) -> ChannelMessages:
        """ give a version of elm to get me to tell you how many number files are on master """

        self.repo.get_ready(branch_name)
        message = ""

        num_016 = self.repo.number_of_016_files
        num_017 = self.repo.number_of_017_files
        message += f"There are {num_016} 0.16 files."
        message += f"\nThere are {num_017} 0.17 files."
        message += f"\nThat puts us at a total of {num_017 + num_016} Elm files."  # noqa: E501

        return ChannelMessage(channel, message)

    def find_elm_017_matches(self, channel: str, filename_pattern: str) -> ChannelMessages:  # noqa: E501
        """ give a filename of elm to get me to tell you how it looks on master """  # noqa: E501

        self.repo.get_ready()
        message = "We have found the following filenames:\n"

        filenames = self.repo.get_files_for_017(filename_pattern)
        message += " | ".join(filenames)

        return ChannelMessage(channel, message)

    def how_hard_to_port(self, channel: str, filename_pattern: str) -> ChannelMessages:
        """ give a filename of elm to get me to tell you how hard it is to port
            Things are hard if: contains ports, signals, native or html.
            Ports and signals are hardest, then native, then html.
        """

        self.repo.get_ready()
        message = "We have found the following filenames:\n"

        with self.repo.cached_lookups():
            files = self.repo.get_017_porting_breakdown(filename_pattern)

        message += f'Here\'s the breakdown for the:'

        total_breakdowns = defaultdict(int)

        for (filename, breakdown) in files.items():
            total_hardness = sum(breakdown.values())
            message += f'\nfile {filename}: total hardness {total_hardness}\n'
            message += ' | '.join(
                f'{name} : {value}' for (name, value) in breakdown.items()
            )

            for (name, value) in breakdown.items():
                total_breakdowns[name] += value

        message += '\n---------------\n'
        message += 'For a total of:\n'
        message += ' | '.join(
            f'{name} : {value}' for (name, value) in total_breakdowns.items()
        )

        return ChannelMessage(channel, message)
