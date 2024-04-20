import json
import random


def generate_events(i_trace_len: int):
    # Define the possible events
    base_events = [
        ["S_P1", ["P1"], ["s_p1"]],
        ["E_P1", ["P1"], ["e_p1"]],
        ["S_P2", ["P2"], ["s_p2"]],
        ["E_P2", ["P2"], ["e_p2"]]
    ]

    # To store the output events
    output_events = []
    active_processes = {'P1': False, 'P2': False}

    while len(output_events) < i_trace_len:
        # Randomly pick an event from those that are currently valid to add
        valid_events = [event for event in base_events if
                        (event[0].startswith('S_') and not active_processes[event[1][0]]) or
                        (event[0].startswith('E_') and active_processes[event[1][0]])]

        if valid_events:
            event = random.choice(valid_events)
            process = event[1][0]

            # Toggle the active state based on the type of event
            if event[0].startswith("S_"):
                output_events.append(event)
                active_processes[process] = True
            else:
                output_events.append(event)
                active_processes[process] = False
        else:
            # If no valid event is found (which should not happen normally), break to avoid infinite loop
            break

    return output_events


def save_to_json(file_path, data):
    # Structure the final JSON object
    json_data = {
        "processes": 2,
        "events": data
    }
    # Write to a JSON file with specific formatting
    with open(file_path, 'w') as f:
        f.write('{\n  "processes": 2,\n  "events": [\n')
        for i, event in enumerate(json_data['events']):
            # Format each event entry
            if i < len(json_data['events']) - 1:
                f.write('    {},\n'.format(json.dumps(event)))
            else:
                f.write('    {}\n'.format(json.dumps(event)))
        f.write('  ]\n}')


if __name__ == "__main__":
    trace_len = input(f"Write the trace len: ")
    event_data = generate_events(int(trace_len))
    save_to_json(f"trace-{trace_len}.json", event_data)
    print("JSON file has been created successfully with formatted output.")
