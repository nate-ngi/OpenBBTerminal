"""OS Controller Module"""
__docformat__ = "numpy"

import argparse
import logging
from typing import List

from prompt_toolkit.completion import NestedCompleter

from openbb_terminal import feature_flags as obbff
from openbb_terminal.alternative.os import github_view
from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    EXPORT_BOTH_RAW_DATA_AND_FIGURES,
    EXPORT_ONLY_RAW_DATA_ALLOWED,
    log_and_raise,
    parse_known_args_and_warn,
    valid_repo,
)
from openbb_terminal.menu import session
from openbb_terminal.parent_classes import BaseController
from openbb_terminal.rich_config import console

logger = logging.getLogger(__name__)


class OsController(BaseController):
    """Open Source Controller class"""

    CHOICES_COMMANDS = ["sh", "tr", "rs"]
    PATH = "/alternative/os/"

    def __init__(self, queue: List[str] = None):
        """Constructor"""
        super().__init__(queue)

        if session and obbff.USE_PROMPT_TOOLKIT:
            choices: dict = {c: {} for c in self.controller_choices}
            choices["tr"]["-s"] = {c: None for c in ["stars", "forks"]}
            self.completer = NestedCompleter.from_nested_dict(choices)

    def print_help(self):
        """Print help"""
        help_text = """[cmds]
        rs          repo summary
        sh          repo star history
        tr          top starred repos[/cmds]
        """
        console.print(text=help_text, menu="Alternative - Open Source")

    @log_start_end(log=logger)
    def call_sh(self, other_args: List[str]):
        """Process sh command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="sh",
            description="Display a repo star history [Source: https://api.github.com]",
        )
        parser.add_argument(
            "-r",
            "--repo",
            type=str,
            required="-h" not in other_args,
            dest="repo",
            help="Repository to search for star history. Format: org/repo, e.g., openbb-finance/openbbterminal",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-r")
        ns_parser = parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
        )
        if ns_parser:
            if len(self.queue) == 0:
                log_and_raise(
                    argparse.ArgumentTypeError(
                        f"{ns_parser.repo} is not a valid repo. Valid repo: org/repo"
                    )
                )
            repo = ns_parser.repo + "/" + self.queue[0]
            if valid_repo(repo):
                github_view.display_star_history(repo=repo, export=ns_parser.export)
                self.queue = self.queue[1:]

    @log_start_end(log=logger)
    def call_rs(self, other_args: List[str]):
        """Process rs command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="rs",
            description="Display a repo summary [Source: https://api.github.com]",
        )
        parser.add_argument(
            "-r",
            "--repo",
            type=str,
            required="-h" not in other_args,
            dest="repo",
            help="Repository to search for repo summary. Format: org/repo, e.g., openbb-finance/openbbterminal",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-r")
        ns_parser = parse_known_args_and_warn(
            parser, other_args, export_allowed=EXPORT_ONLY_RAW_DATA_ALLOWED, raw=True
        )
        if ns_parser:
            if len(self.queue) == 0:
                log_and_raise(
                    argparse.ArgumentTypeError(
                        f"{ns_parser.repo} is not a valid repo. Valid repo: org/repo"
                    )
                )
            repo = ns_parser.repo + "/" + self.queue[0]
            if valid_repo(repo):
                github_view.display_repo_summary(repo=repo, export=ns_parser.export)
                self.queue = self.queue[1:]

    @log_start_end(log=logger)
    def call_tr(self, other_args: List[str]):
        """Process tr command"""
        parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            prog="tr",
            description="Display top repositories [Source: https://api.github.com]",
        )
        parser.add_argument(
            "-s",
            "--sortby",
            type=str,
            dest="sortby",
            help="Sort repos by {stars, forks}. Default: stars",
            default="stars",
            choices=["stars", "forks"],
        )

        parser.add_argument(
            "-c",
            "--categories",
            type=str,
            dest="categories",
            help="Filter by repo categories. If more than one separate with a comma: e.g., finance,investment",
            default="",
        )
        if other_args and "-" not in other_args[0][0]:
            other_args.insert(0, "-c")
        ns_parser = parse_known_args_and_warn(
            parser,
            other_args,
            export_allowed=EXPORT_BOTH_RAW_DATA_AND_FIGURES,
            raw=True,
            limit=10,
        )
        if ns_parser:
            github_view.display_top_repos(
                sortby=ns_parser.sortby,
                categories=ns_parser.categories,
                limit=ns_parser.limit,
                export=ns_parser.export,
            )