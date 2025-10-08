import PySimpleGUI as sg
import json
import os
import io
from PIL import Image
import concurrent.futures
import google.generativeai as genai
from google.generativeai import types


# --- API INTEGRATION ---

def generate_image_from_api(api_key, prompt):
    """Generates an image using the Google Gemini API (Imagen model) and returns image bytes."""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1)
        )

        if response.generated_images:
            pil_image = response.generated_images[0].image
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue(), None
        else:
            return None, "API returned no images."

    except Exception as e:
        return None, f"An API error occurred: {e}"


# --- UI LAYOUT ---

def create_main_window():
    # --- Left Sidebar for Stats and Unit List ---
    stats_frame = sg.Frame("Statistics", [
        [sg.Text("Total Units:", size=(12, 1)), sg.Text("0", key="-TOTAL-")],
        [sg.Text("Approved:", size=(12, 1)), sg.Text("0", key="-APPROVED-")],
        [sg.Text("Pending:", size=(12, 1)), sg.Text("0", key="-PENDING-")],
        [sg.Text("Skipped:", size=(12, 1)), sg.Text("0", key="-SKIPPED-")],
    ])

    unit_list_frame = sg.Frame("Unit Progress", [
        [sg.Table(
            values=[],
            headings=["Unit Name", "Status", "Redos"],
            key="-UNIT-TABLE-",
            display_row_numbers=False,
            auto_size_columns=False,
            col_widths=[20, 10, 5],
            justification='left',
            enable_events=True,
            num_rows=20
        )]
    ])

    left_col = sg.Column([
        [stats_frame],
        [unit_list_frame]
    ])

    # --- Center Area for Image Review ---
    image_review_frame = sg.Frame("Image Review", [
        [sg.Text("Current Unit: ", size=(15,1)), sg.Text("", key="-CURRENT-UNIT-", size=(30,1), font=("Helvetica", 14, "bold"))],
        [sg.Image(key="-IMAGE-", size=(400, 400), background_color='lightgray')],
        [sg.Text("Redo with extra comments:")],
        [sg.InputText(key="-REDO-COMMENTS-", size=(60, 1))],
        [
            sg.Button("Approve", key="-APPROVE-", button_color=('white', 'green'), size=(10,2)),
            sg.Button("Redo", key="-REDO-", button_color=('white', 'orange'), size=(10,2)),
            sg.Button("Reject/Skip", key="-SKIP-", button_color=('white', 'red'), size=(10,2))
        ]
    ], element_justification='center')

    # --- Top Panel for Controls ---
    top_panel = sg.Frame("Setup & Controls", [
        [
            sg.Text("Gemini API Key:"),
            sg.Input(key="-API-KEY-", password_char='*'),
            sg.Button("Load Unit List", key="-LOAD-UNITS-"),
            sg.Button("Select Output Folder", key="-OUTPUT-FOLDER-")
        ],
        [
            sg.Text("Prompt Template:"),
            sg.Combo([], key="-PROMPT-TEMPLATE-", size=(40,1), readonly=True),
            sg.Button("Manage Templates", key="-MANAGE-TEMPLATES-"),
            sg.Text("Batch Size:"),
            sg.Input("5", key="-BATCH-SIZE-", size=(5,1)),
            sg.Button("Start/Resume Generation", key="-START-", size=(20, 1))
        ]
    ])

    # --- Main Layout Assembly ---
    layout = [
        [top_panel],
        [sg.HorizontalSeparator()],
        [left_col, sg.VerticalSeparator(), sg.Column([[image_review_frame]])]
    ]

    return sg.Window("AI-Powered Icon Generator", layout, finalize=True)


# --- DATA MANAGEMENT ---

def load_json_file(filepath, default_data):
    """Loads a JSON file, returning default data if it doesn't exist or is invalid."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return default_data
    return default_data

def save_json_file(filepath, data):
    """Saves data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_templates():
    return load_json_file("templates.json", {
        "Minimalist Style": "A flat, minimalist icon for a game unit named {unit_name}, vector style, on a white background.",
        "Pixel Art Style": "16-bit pixel art icon of a {unit_name}, vibrant colors."
    })

def save_templates(templates):
    save_json_file("templates.json", templates)

def load_project_state():
    return load_json_file("project_state.json", [])

def save_project_state(state):
    save_json_file("project_state.json", state)


def manage_templates_window(templates):
    """Opens a window to add, edit, and delete prompt templates."""
    layout = [
        [sg.Text("Manage Prompt Templates")],
        [sg.Listbox(values=list(templates.keys()), size=(40, 10), key="-TEMPLATE-LIST-", enable_events=True)],
        [sg.Text("Template Name:"), sg.Input(key="-TPL-NAME-", size=(30,1))],
        [sg.Text("Template Prompt:")],
        [sg.Multiline(key="-TPL-PROMPT-", size=(60, 5))],
        [sg.Button("Save Template"), sg.Button("Delete Template")]
    ]

    window = sg.Window("Template Manager", layout, modal=True)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == "-TEMPLATE-LIST-":
            name = values["-TEMPLATE-LIST-"][0]
            window["-TPL-NAME-"].update(name)
            window["-TPL-PROMPT-"].update(templates[name])
        elif event == "Save Template":
            name = values["-TPL-NAME-"]
            prompt = values["-TPL-PROMPT-"]
            if name and prompt:
                templates[name] = prompt
                window["-TEMPLATE-LIST-"].update(values=list(templates.keys()))
        elif event == "Delete Template":
            name = values["-TPL-NAME-"]
            if name in templates:
                del templates[name]
                window["-TPL-NAME-"].update("")
                window["-TPL-PROMPT-"].update("")
                window["-TEMPLATE-LIST-"].update(values=list(templates.keys()))

    window.close()
    return templates

def update_stats_display(window, state):
    """Updates the statistics display in the UI."""
    total = len(state)
    approved = sum(1 for u in state if u['status'] == 'approved')
    pending = sum(1 for u in state if u['status'] == 'pending')
    skipped = sum(1 for u in state if u['status'] == 'skipped')
    window["-TOTAL-"].update(total)
    window["-APPROVED-"].update(approved)
    window["-PENDING-"].update(pending)
    window["-SKIPPED-"].update(skipped)

def update_unit_table(window, state):
    """Updates the unit list table in the UI."""
    table_data = [[u['unit_name'], u['status'], u['redo_count']] for u in state]
    window["-UNIT-TABLE-"].update(values=table_data)

def find_next_pending(state, current_index):
    """Finds the index of the next unit with 'pending' status."""
    if not state:
        return -1
    # Start searching from the next unit
    for i in range(current_index + 1, len(state)):
        if state[i]['status'] == 'pending':
            return i
    # If not found, search from the beginning
    for i in range(current_index + 1):
        if state[i]['status'] == 'pending':
            return i
    return -1 # No pending units left

def display_image(window, image_data):
    """Displays an image in the UI."""
    if image_data:
        try:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((400, 400))
            bio = io.BytesIO()
            img.save(bio, format="PNG")
            window["-IMAGE-"].update(data=bio.getvalue())
        except Exception as e:
            sg.popup_error(f"Error displaying image: {e}")
    else:
        # Clear the image area if there's no image data
        window["-IMAGE-"].update(data=None, size=(400,400), background_color='lightgray')

def generation_worker(window, unit, api_key, prompt):
    """Worker function to generate a single image in a thread."""
    image_data, error = generate_image_from_api(api_key, prompt)

    # Send result back to the main thread
    window.write_event_value(("-WORKER-DONE-", (unit['unit_name'], image_data, error, prompt)))
    return

# --- Main Application Logic ---
def main():
    # --- Initialization ---
    project_state = load_project_state()
    templates = load_templates()
    output_folder = ""
    current_unit_index = 0
    generated_images = {}  # In-memory cache for generated image data
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    active_workers = 0

    window = create_main_window()

    def set_current_unit(index):
        nonlocal current_unit_index
        current_unit_index = index
        if 0 <= index < len(project_state):
            unit = project_state[index]
            window["-CURRENT-UNIT-"].update(unit['unit_name'])
            image_data = generated_images.get(unit['unit_name'])
            display_image(window, image_data)
        else:
            current_unit_index = -1
            window["-CURRENT-UNIT-"].update("All units processed!")
            display_image(window, None)

    def toggle_controls(disabled):
        window["-LOAD-UNITS-"].update(disabled=disabled)
        window["-OUTPUT-FOLDER-"].update(disabled=disabled)
        window["-MANAGE-TEMPLATES-"].update(disabled=disabled)
        window["-START-"].update(disabled=disabled)
        window["-APPROVE-"].update(disabled=disabled)
        window["-REDO-"].update(disabled=disabled)
        window["-SKIP-"].update(disabled=disabled)
        window["-UNIT-TABLE-"].update(disabled=disabled)
        window.refresh()

    # --- Populate UI with loaded data ---
    window["-PROMPT-TEMPLATE-"].update(values=list(templates.keys()), value=list(templates.keys())[0] if templates else "")
    update_stats_display(window, project_state)
    update_unit_table(window, project_state)
    set_current_unit(find_next_pending(project_state, -1))

    # --- Main Event Loop ---
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

        api_key = values["-API-KEY-"]

        if event == "-LOAD-UNITS-":
            filepath = sg.popup_get_file("Select Unit List File", file_types=(("Text Files", "*.txt"),))
            if filepath:
                with open(filepath, 'r') as f:
                    unit_names = [line.strip() for line in f if line.strip()]
                project_state = [{"unit_name": name, "status": "pending", "redo_count": 0, "image_path": None, "final_prompt": None} for name in unit_names]
                generated_images.clear()
                save_project_state(project_state)
                update_stats_display(window, project_state)
                update_unit_table(window, project_state)
                set_current_unit(0)
                sg.popup(f"Loaded {len(unit_names)} units.")

        elif event == "-OUTPUT-FOLDER-":
            folder = sg.popup_get_folder("Select Output Folder")
            if folder:
                output_folder = folder
                sg.popup(f"Output folder set to: {output_folder}")

        elif event == "-MANAGE-TEMPLATES-":
            updated_templates = manage_templates_window(templates.copy())
            if updated_templates:
                templates = updated_templates
                save_templates(templates)
                window["-PROMPT-TEMPLATE-"].update(values=list(templates.keys()))
                sg.popup("Templates saved.")

        elif event == "-UNIT-TABLE-":
            if values["-UNIT-TABLE-"]:
                set_current_unit(values["-UNIT-TABLE-"][0])

        elif event == "-APPROVE-":
            if not output_folder:
                sg.popup_error("Please select an output folder first.")
                continue
            if 0 <= current_unit_index < len(project_state):
                unit = project_state[current_unit_index]
                image_data = generated_images.get(unit['unit_name'])
                if image_data:
                    image_path = os.path.join(output_folder, f"{unit['unit_name']}.png")
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    unit['status'] = 'approved'
                    unit['image_path'] = image_path
                    save_project_state(project_state)
                    update_stats_display(window, project_state)
                    update_unit_table(window, project_state)
                    next_pending_index = find_next_pending(project_state, current_unit_index)
                    set_current_unit(next_pending_index)
                else:
                    sg.popup_error("No image to approve. Please generate one first.")

        elif event == "-SKIP-":
            if 0 <= current_unit_index < len(project_state):
                unit = project_state[current_unit_index]
                unit['status'] = 'skipped'
                save_project_state(project_state)
                update_stats_display(window, project_state)
                update_unit_table(window, project_state)
                next_pending_index = find_next_pending(project_state, current_unit_index)
                set_current_unit(next_pending_index)

        elif event == "-REDO-":
            if not api_key:
                sg.popup_error("Please enter your Gemini API key.")
                continue
            if current_unit_index == -1:
                sg.popup_error("Please select a unit to redo.")
                continue

            unit = project_state[current_unit_index]
            unit['redo_count'] += 1
            template = values["-PROMPT-TEMPLATE-"]
            base_prompt = templates.get(template, "").format(unit_name=unit['unit_name'])
            extra_comments = values["-REDO-COMMENTS-"]
            final_prompt = f"{base_prompt}, {extra_comments}" if extra_comments else base_prompt

            window["-CURRENT-UNIT-"].update(f"{unit['unit_name']} (Generating...)")
            toggle_controls(True)
            active_workers += 1
            executor.submit(generation_worker, window, unit, api_key, final_prompt)

        elif event == "-START-":
            if not api_key:
                sg.popup_error("Please enter your Gemini API key.")
                continue

            pending_units = [u for u in project_state if u['status'] == 'pending']
            if not pending_units:
                sg.popup("No pending units to generate.")
                continue

            batch_size_str = values.get("-BATCH-SIZE-", "5")
            try:
                batch_size = int(batch_size_str)
                if not 1 <= batch_size <= 20: raise ValueError
            except (ValueError, TypeError):
                sg.popup_error("Batch size must be an integer between 1 and 20.")
                continue

            executor._max_workers = batch_size
            sg.popup_quick_message(f"Starting batch generation for {len(pending_units)} units...", auto_close_duration=3)
            toggle_controls(True)

            template = values["-PROMPT-TEMPLATE-"]
            for unit in pending_units:
                active_workers += 1
                prompt = templates.get(template, "").format(unit_name=unit['unit_name'])
                executor.submit(generation_worker, window, unit, api_key, prompt)

        elif event == ("-WORKER-DONE-"):
            active_workers -= 1
            unit_name, image_data, error, prompt = values[event]
            unit = next((u for u in project_state if u['unit_name'] == unit_name), None)

            if unit:
                if error:
                    print(f"Worker error for {unit_name}: {error}")
                else:
                    generated_images[unit_name] = image_data
                    unit['final_prompt'] = prompt
                    save_project_state(project_state)
                    update_unit_table(window, project_state)

                    if project_state[current_unit_index]['unit_name'] == unit_name:
                        display_image(window, image_data)
                        window["-CURRENT-UNIT-"].update(unit_name)

            if active_workers == 0:
                toggle_controls(False)

    window.close()
    executor.shutdown(wait=False)

if __name__ == "__main__":
    main()