import json
import random


def generate_events(trace_len: int):
    # Define events for P1 and P2 with their respective patterns
    patterns = {
        "P1": [
            ["a1", ["P1"], ["a", "t1", "t2"]],
            ["b2", ["P1"], ["b", "t1"]],
            ["b1", ["P1"], ["b", "t2"]],
            ["a2", ["P1"], ["a"]],
        ],
        "P2": [
            ["a1'", ["P2"], ["a'", "t1'", "t2'"]],
            ["b2'", ["P2"], ["b'", "t1'"]],
            ["b1'", ["P2"], ["b'", "t2'"]],
            ["a2'", ["P2"], ["a'"]],
        ],
    }

    # Initial event
    events = [["init", ["P1", "P2"], ["init"]]]

    # Prepare to track the number of events added for each process
    events_count = {"P1": 0, "P2": 0}
    total_events_required = (trace_len // 2) - 1

    # Generate the events
    while (
        events_count["P1"] < total_events_required
        or events_count["P2"] < total_events_required
    ):
        # Decide randomly which process to add an event for, ensuring balance by the end
        process_to_use = random.choice(
            [p for p in events_count if events_count[p] < total_events_required]
        )
        # Add the next event for the selected process
        pattern_index = events_count[process_to_use] % len(patterns[process_to_use])
        events.append(patterns[process_to_use][pattern_index])
        events_count[process_to_use] += 1

    # Add the final sync event
    events.append(["sync", ["P1", "P2"], ["sync"]])

    return events


def save_to_json(file_path, data):
    # Prepare the JSON structure
    json_data = {"processes": 2, "events": data}

    # Manually create a JSON string with the desired format
    with open(file_path, "w") as file:
        file.write('{\n  "processes": 2,\n  "events": [\n')
        for i, event in enumerate(json_data["events"]):
            if i < len(json_data["events"]) - 1:
                file.write("    {},\n".format(json.dumps(event)))
            else:
                file.write("    {}\n".format(json.dumps(event)))
        file.write("  ]\n}")


if __name__ == "__main__":
    trace_len = input("Write the trace.json.json.json len: ")
    event_data = generate_events(int(trace_len))
    save_to_json(f"trace.json.json.json-{trace_len}.json", event_data)
    print("JSON file has been created successfully.")
