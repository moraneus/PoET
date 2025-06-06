import json
import random


def generate_events(trace_len: int):
    # Define events for P1, P2, and P3 with their respective patterns
    patterns = {
        "P1": [
            ["S_P1", ["P1"], ["s_p1"]],
            ["C_P1", ["P1"], ["c_p1"]],
            ["E_P1", ["P1"], ["e_p1"]],
        ],
        "P2": [
            ["S_P2", ["P2"], ["s_p2"]],
            ["C_P2", ["P2"], ["c_p2"]],
            ["E_P2", ["P2"], ["e_p2"]],
        ],
        "P3": [
            ["S_P3", ["P3"], ["s_p3"]],
            ["C_P3", ["P3"], ["c_p3"]],
            ["E_P3", ["P3"], ["e_p3"]],
        ],
        "common": [["E_C", ["P1", "P2"], ["e_c"]]],
    }

    # Initial events
    events = [
        ["S_P1", ["P1"], ["s_p1"]],
        ["S_P2", ["P2"], ["s_p2"]],
        ["S_P3", ["P3"], ["s_p3"]],
    ]

    # Prepare to track the number of events added for each process
    events_count = {"P1": 0, "P2": 0, "P3": 0, "common": 0}
    total_events_required = trace_len - 3  # Subtract the initial events

    # Generate the events
    while sum(events_count.values()) < total_events_required:
        # Decide randomly which process to add an event for
        process_to_use = random.choice(list(patterns.keys()))

        # Add the next event for the selected process
        pattern_index = events_count[process_to_use] % len(patterns[process_to_use])
        events.append(patterns[process_to_use][pattern_index])
        events_count[process_to_use] += 1

        # Add the common event 'E_C' after 'C_P1' or 'C_P2'
        if (process_to_use == "P1" and events[-1][0] == "C_P1") or (
            process_to_use == "P2" and events[-1][0] == "C_P2"
        ):
            events.append(patterns["common"][0])
            events_count["common"] += 1

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
    trace_len = input("Write the trace.json.json.json len: ")
    event_data = generate_events(int(trace_len))
    save_to_json(f"trace.json.json.json-{trace_len}.json", event_data)
    print("JSON file has been created successfully.")
