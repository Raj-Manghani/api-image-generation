# AI-Powered Icon Generation Application

This application helps you automatically generate icons for a list of unit names using the Google Gemini API.

## How to Use

### 1. Prerequisites
- Python 3.x
- An API key for the Google Gemini API.

### 2. Installation
1.  Clone or download this repository.
2.  Install the required Python libraries:
    ```bash
    pip install pysimplegui pillow requests
    ```

### 3. Running the Application
1.  Run the application from your terminal:
    ```bash
    python icon_generator.py
    ```

### 4. Setup
1.  **API Key**: Enter your Google Gemini API key into the "Gemini API Key" input field.
2.  **Load Unit List**: Click "Load Unit List" to select a `.txt` file containing a list of names, with each name on a new line.
3.  **Select Output Folder**: Click "Select Output Folder" to choose where the generated icons will be saved.
4.  **Prompt Template**: Select a prompt template from the dropdown. You can manage templates via the "Manage Templates" button.

### 5. Generating Icons
1.  **Batch Size**: Set the number of concurrent API requests.
2.  **Start Generation**: Click "Start/Resume Generation" to begin creating icons for all pending units.

### 6. Reviewing Icons
- The main area will display the generated icon for the current unit.
- **Approve**: Saves the icon to your output folder and moves to the next unit.
- **Redo**: Add comments to the "Redo with extra comments" box and click "Redo" to generate a new version.
- **Reject/Skip**: Skips the current unit.

### 7. Data Files
- `project_state.json`: Automatically saves your progress.
- `templates.json`: Stores your prompt templates.