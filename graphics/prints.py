# graphics/prints.py

from typing import List

from colorama import Fore, Style

from model.event import Event
from model.state import State


class Prints:
    # init(convert=True)

    @staticmethod
    def banner():
        print(rf"""{Fore.GREEN}
{" " * 55}██████╗          ███████╗████████╗
{" " * 55}██╔══██╗ ██████╗ ██╔════╝╚══██╔══╝
{" " * 55}██████╔╝██╔═══██╗█████╗     ██║   
{" " * 55}██╔═══╝ ██║   ██║██╔══╝     ██║   
{" " * 55}██║     ╚██████╔╝███████╗   ██║   
{" " * 55}╚═╝      ╚═════╝ ╚══════╝   ╚═╝  

{" " * 55}         ,---,_          ,
{" " * 55}          _>   `'-.  .--'/
{" " * 55}     .--'` ._      `/   <_
{" " * 55}      >,-' ._'.. ..__ . ' '-.
{" " * 55}   .-'   .'`         `'.     '.
{" " * 55}    >   / >`-.     .-'< \ , '._|
{" " * 55}   /    ; '-._>   <_.-' ;  '._>
{" " * 55}   `>  ,/  /___\ /___\  \_  /
{" " * 55}   `.-|(|  L {Fore.BLUE}o{Fore.GREEN}_/ L {Fore.BLUE}o{Fore.GREEN}_/   |)|`
{" " * 55} PoET  \;        \      ;/
{" " * 55}         \  .-,   )-.  /
{" " * 55}          /`  .'-'.  `l
{" " * 55}         ;_.-`.___.'-._l
{Style.RESET_ALL}""")

    @staticmethod
    def seperator(i_title):
        num_of_chars = 80 - (len(i_title) // 2)
        print(f'{Fore.LIGHTCYAN_EX}{"#" * num_of_chars} ({i_title}) {"#" * num_of_chars}{Style.RESET_ALL}')

    @staticmethod
    def event(i_event: Event, i_debug: bool = False):
        if i_debug:
            propositions = ', '.join(i_event.propositions)
            print(f'{Style.BRIGHT}[EVENT]: name: {i_event.name}, propositions: {propositions}{Style.RESET_ALL}')

    @staticmethod
    def raw_property(i_details):
        print(f'{Style.BRIGHT}[RAW_PROPERTY]: {i_details}{Style.RESET_ALL}\n')

    @staticmethod
    def compiled_property(i_details):
        print(f'{Style.BRIGHT}[COMPILED_PROPERTY]: {i_details}{Style.RESET_ALL}\n')

    @staticmethod
    def total_states(i_num_of_states):
        print(f'[TOTAL_STATES]: {i_num_of_states}\n')

    @staticmethod
    def events_time(i_max_event, i_min_event, i_avg_events):
        print(f"""[MAX_EVENT]: It takes {i_max_event[0]} for the event {i_max_event[1]}\n""")
        print(f"""[MIN_EVENT]: It takes {i_min_event[0]} for the event {i_min_event[1]}\n""")
        print(f"""[AVG_EVENTS]: It takes {i_avg_events} in average per event\n""")

    @staticmethod
    def total_events(i_num_of_events):
        print(f'[TOTAL_EVENTS]: {i_num_of_events}\n')

    @staticmethod
    def display_states(i_states: List[State], i_title: str = '', i_debug: bool = False):
        Prints.seperator(f'START {i_title}')
        for state in i_states:
            color = Fore.RED if not state.value else Fore.LIGHTBLUE_EX
            if i_debug:
                state = repr(state)
            print(f'{color}{state}{Style.RESET_ALL}')
        Prints.seperator(f'END {i_title}')

    @staticmethod
    def del_state(i_state, i_debug: bool = False):
        if i_debug:
            i_state = repr(i_state)
            print(f'{Fore.LIGHTYELLOW_EX}[DELETE STATE]: {i_state}{Style.RESET_ALL}')

    @staticmethod
    def process_error(i_error):
        print(f'{Fore.RED}[PROCESS ERROR]: {i_error} '
              f'(check if the number of processes in the trace file is correct){Style.RESET_ALL}\n')
