import json
import random


def generate_events(trace_len: int):
    # Define events for P1, P2, and P3 with their respective patterns
    patterns = {
        "P1": [
            ["S_P1", ["P1"], ["s_p1"]],
            ["E_P1", ["P1"], ["e_p1"]],
            ["SR_P1", ["P1", "P3"], ["sr_p1"]],
        ],
        "P2": [
            ["S_P2", ["P2"], ["s_p2"]],
            ["E_P2", ["P2"], ["e_p2"]],
            ["SR_P2", ["P2", "P3"], ["sr_p2"]],
        ],
    }

    # Initial events
    events = []

    # Prepare to track the number of events added for each process
    events_count = {"P1": 0, "P2": 0}
    total_events_required = trace_len

    # Generate the events
    while sum(events_count.values()) < total_events_required:
        # Decide randomly which process to add an event for
        process_to_use = random.choice(list(patterns.keys()))

        # Add the next event for the selected process
        pattern_index = events_count[process_to_use] % len(patterns[process_to_use])
        events.append(patterns[process_to_use][pattern_index])
        events_count[process_to_use] += 1

        # Add the 'E_PX' event after 'S_PX' for the selected process
        if pattern_index == 0:
            events.append(patterns[process_to_use][1])
            events_count[process_to_use] += 1

        # Add the 'SR_PX' event after 'E_PX' for the selected process
        if pattern_index == 1:
            events.append(patterns[process_to_use][2])
            events_count[process_to_use] += 1

    return events


def save_to_json(file_path, data):
    # Prepare the JSON structure
    json_data = {"processes": 3, "events": data}

    # Manually create a JSON string with the desired format
    with open(file_path, "w") as file:
        file.write('{\n "processes": 3,\n "events": [\n')
        for i, event in enumerate(json_data["events"]):
            if i < len(json_data["events"]) - 1:
                file.write(" {},\n".format(json.dumps(event)))
            else:
                file.write(" {}\n".format(json.dumps(event)))
        file.write(" ]\n}")


if __name__ == "__main__":
    trace_len = input("Write the trace len: ")
    event_data = generate_events(int(trace_len))
    save_to_json(f"trace-{trace_len}.json", event_data)
    print("JSON file has been created successfully.")
