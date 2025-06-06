# graphics/prints.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Console output formatting and display utilities for monitoring results,
# including banners, state displays, and performance metrics.

from typing import List, Tuple

from colorama import Fore, Style

from model.event import Event
from model.state import State


class Prints:
    """Handles formatted console output for PoET monitoring results."""

    CURRENT_OUTPUT_LEVEL = None

    @staticmethod
    def banner() -> None:
        """Display PoET ASCII art banner."""
        print(
            rf"""{Fore.GREEN}
{" " * 55}██████╗  ██████╗ ███████╗████████╗
{" " * 55}██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝
{" " * 55}██████╔╝██║   ██║█████╗     ██║   
{" " * 55}██╔═══╝ ██║   ██║██╔══╝     ██║   
{" " * 55}██║     ╚██████╔╝███████╗   ██║   
{" " * 55}╚═╝      ╚═════╝ ╚══════╝   ╚═╝   
{" " * 55}                ,---,_       ,    
{" " * 55}               *>    *`'-. .--'/   
{" " * 55}          .--'`*  .    *`/   <_   
{" " * 55}        >,-'     ._'.. ..__  .  '-.
{" " * 55}      .-'       .'`*    *`'.   '.  
{" " * 55}     >        /   >`-.   .-'<   \  ,  '._|
{" " * 55}    /        ;     '-._> <_.-'    ;   '._>
{" " * 55}   `>       ,/       /___\  /___\  \_    /
{" " * 55}   `*.-|(|          L {Fore.BLUE}o{Fore.GREEN}_/  L {Fore.BLUE}o{Fore.GREEN}_/   |)|`
{" " * 55}      PoET          \;     \    ;/
{" " * 55}                     \  .-, )-. /
{" " * 55}                     /` .'-'.  `l
{" " * 55}                    ;_.-`*.___.'-._l
{Style.RESET_ALL}"""
        )

    @staticmethod
    def seperator(title: str) -> None:
        """Print section separator with title."""
        title_padding = len(title) // 2
        separator_length = 80 - title_padding
        print(
            f'{Fore.LIGHTCYAN_EX}{"#" * separator_length} ({title}) {"#" * separator_length}{Style.RESET_ALL}'
        )

    @staticmethod
    def event(event: Event, debug: bool = False) -> None:
        """Print event information if debug mode is enabled."""
        if debug:
            propositions = ", ".join(event.propositions)
            print(
                f"{Style.BRIGHT}[EVENT]: name: {event.name}, propositions: {propositions}{Style.RESET_ALL}"
            )

    @staticmethod
    def raw_property(details: str) -> None:
        """Print raw property information."""
        print(f"INFO: Property: {details}")

    @staticmethod
    def compiled_property(details: str) -> None:
        """Print compiled property information."""
        print(f"INFO: Parsed formula: {details}")

    @staticmethod
    def total_states(num_states: int) -> None:
        """Print total number of states."""
        print(f"[TOTAL_STATES]: {num_states}\n")

    @staticmethod
    def events_time(
        max_event: Tuple[float, str], min_event: Tuple[float, str], avg_time: float
    ) -> None:
        """Print event timing statistics."""
        print(f"[MAX_EVENT]: It takes {max_event[0]} for the event {max_event[1]}\n")
        print(f"[MIN_EVENT]: It takes {min_event[0]} for the event {min_event[1]}\n")
        print(f"[AVG_EVENTS]: It takes {avg_time} in average per event\n")

    @staticmethod
    def total_events(num_events: int) -> None:
        """Print total number of events."""
        print(f"[TOTAL_EVENTS]: {num_events}\n")

    @staticmethod
    def display_states(
        states: List[State], i_title: str = "", i_debug: bool = False
    ) -> None:
        """Display list of states with formatting."""
        Prints.seperator(f"START {i_title}")

        for state in states:
            color = Prints._get_state_color(state)
            state_display = repr(state) if i_debug else str(state)
            print(f"{color}{state_display}{Style.RESET_ALL}")

        Prints.seperator(f"END {i_title}")

    @staticmethod
    def _get_state_color(state: State) -> str:
        """Get color for state display based on its value."""
        return Fore.LIGHTBLUE_EX if state.value else Fore.RED

    @staticmethod
    def del_state(state: State, debug: bool = False) -> None:
        """Print state deletion information if debug mode is enabled."""
        if debug:
            state_display = repr(state) if debug else str(state)
            print(
                f"{Fore.LIGHTYELLOW_EX}[DELETE STATE]: {state_display}{Style.RESET_ALL}"
            )

    @staticmethod
    def process_error(error: str) -> None:
        """Print process error with formatting."""
        print(
            f"{Fore.RED}[PROCESS ERROR]: {error} "
            f"(check if the number of processes in the trace file is correct){Style.RESET_ALL}\n"
        )
