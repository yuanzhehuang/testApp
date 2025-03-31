import base64
import logging
import mimetypes
import os
import requests # Make sure 'requests' is in requirements.txt
import customtkinter as ctk

from typing import Optional
from src.config.config_manager import config_manager
from src.config.env_manager import env_manager
from src.ui.dialogs import showinfo, showerror, askstring, askyesno # Use centralized dialogs

logger = logging.getLogger(__name__)

# --- Helper Function to Get API Tokens ---
def _get_api_token(system_key: str, config_section: str, config_key: str, prompt_title: str, prompt_text: str) -> Optional[str]:
    """
    Retrieves an API token, prioritizing .env, then prompting the user if necessary.

    Args:
        system_key: The key used to store the token in .env (e.g., "JTMF_API_TOKEN").
        config_section: The config.ini section (e.g., "JTMF").
        config_key: The config.ini key (e.g., "API_TOKEN"). Deprecated for tokens.
        prompt_title: Title for the input dialog if token is missing.
        prompt_text: Text for the input dialog if token is missing.

    Returns:
        The API token as a string, or None if not found/provided.
    """
    # 1. Prioritize .env file
    api_token = env_manager.get_secret(system_key)
    if api_token:
        logger.debug(f"Found {system_key} in environment/secrets.")
        return api_token

    # 2. (Optional/Legacy) Check config.ini - Not recommended for tokens!
    # api_token = config_manager.get(config_section, config_key)
    # if api_token:
    #     logger.warning(f"Found {system_key} in config.ini - recommend moving to .env file for security.")
    #     env_manager.set_secret(system_key, api_token) # Optionally move it to .env
    #     return api_token

    # 3. Prompt user if not found
    logger.warning(f"{system_key} not found in .env. Prompting user.")
    api_token = askstring(prompt_title, prompt_text)
    if api_token:
            # Save to .env for future use
            if env_manager.set_secret(system_key, api_token):
                logger.info(f"Saved {system_key} provided by user to .env file.")
            else:
                logger.error(f"Failed to save {system_key} to .env file.")
            return api_token
    else:
        logger.warning(f"User did not provide {system_key}.")
        showerror("Missing Token", f"{prompt_title} is required for upload.")
        return None

# --- JIRA Upload Function ---
def upload_doc_to_jira(file_path: str) -> bool:
    """
    Uploads a document file to a JIRA issue attachment.

    Args:
        file_path: The path to the document file to upload.

    Returns:
        True if upload was successful (or simulated), False otherwise.
    """
    logger.info(f"Attempting to upload '{os.path.basename(file_path)}' to JIRA...")

    # --- Get Configuration ---
    api_token = _get_api_token("JIRA_API_TOKEN", "JIRA", "API_TOKEN", "JIRA API Token", "Enter your JIRA API Token:")
    if not api_token:
        return False

    api_uri_base = config_manager.get("JIRA", "API_URI", fallback="").rstrip('/')
    if not api_uri_base:
            showerror("Missing Config", "JIRA API URI is not set in config.ini [JIRA] section.")
            logger.error("JIRA API URI missing in configuration.")
            return False

    # --- Get Issue Key ---
    test_issue_key = askstring("JIRA Issue Key", "Enter the JIRA Issue Key (e.g., PROJ-123):")
    if not test_issue_key:
        logger.warning("User cancelled or did not enter JIRA Issue Key.")
        return False # Indicate cancellation/failure

    # --- Prepare Request ---
    upload_url = f"{api_uri_base}/rest/api/3/issue/{test_issue_key}/attachments" # Using API v3 standard

    headers = {
        "Authorization": f"Bearer {api_token}", # Standard for Atlassian API Tokens
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check" # Required for multipart uploads
    }

    try:
        # Guess the mime type
        file_type, _ = mimetypes.guess_type(file_path)
        if file_type is None:
            file_type = 'application/octet-stream' # Default if type cannot be guessed
        logger.debug(f"Detected file type: {file_type}")

        with open(file_path, 'rb') as file:
                files = {
                    'file': (os.path.basename(file_path), file, file_type)
                }

                showinfo("Upload Info", f"Uploading '{os.path.basename(file_path)}' to JIRA issue {test_issue_key}...")

                # --- Send Request ---
                logger.debug(f"POSTing attachment to {upload_url}")
                response = requests.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    timeout=60 # Add a timeout (e.g., 60 seconds)
                )

                # --- Handle Response ---
                logger.debug(f"JIRA Response Status Code: {response.status_code}")
                # logger.debug(f"JIRA Response Body: {response.text}") # Careful logging potentially large/sensitive data

                if response.status_code == 200:
                    logger.info(f"Successfully uploaded attachment to JIRA issue {test_issue_key}.")
                    showinfo("Success", f"Document uploaded successfully to JIRA issue {test_issue_key}!")
                    return True
                else:
                    error_msg = f"Failed to upload to JIRA. Status: {response.status_code}."
                    try:
                        # Try to get more specific error from JIRA response
                        error_data = response.json()
                        messages = error_data.get('errorMessages', [])
                        errors = error_data.get('errors', {})
                        if messages:
                            error_msg += f" Messages: {'; '.join(messages)}"
                        if errors:
                            error_msg += f" Errors: {errors}"
                        logger.error(f"{error_msg} Response: {response.text}")
                    except requests.exceptions.JSONDecodeError:
                        logger.error(f"{error_msg} Response: {response.text}") # Log raw text if not JSON
                    showerror("Upload Failed", error_msg)
                    return False

    except FileNotFoundError:
        logger.error(f"File not found for upload: {file_path}")
        showerror("File Error", f"The specified file could not be found:\n{file_path}")
        return False
    except requests.exceptions.RequestException as e:
            logger.error(f"Network or request error uploading to JIRA: {e}", exc_info=True)
            showerror("Network Error", f"Could not connect to JIRA or upload failed:\n{e}")
            return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during JIRA upload: {e}", exc_info=True)
        showerror("Error", f"An unexpected error occurred during upload:\n{e}")
        return False


# --- JTMF Upload Function ---
def upload_doc_to_jtmF(file_path: str) -> bool:
    """
    Uploads a document file as evidence to a JTM F test run execution.

    Args:
        file_path: The path to the document file to upload.

    Returns:
        True if upload was successful, False otherwise.
    """
    logger.info(f"Attempting to upload '{os.path.basename(file_path)}' to JTMF...")

    # --- Get Configuration ---
    api_token = _get_api_token("JTMF_API_TOKEN", "JTMF", "API_TOKEN", "JTMF API Token", "Enter your JTMF API Token:")
    if not api_token:
        return False

    api_uri_base = config_manager.get("JTMF", "API_URI", fallback="").rstrip('/')
    if not api_uri_base:
        showerror("Missing Config", "JTMF API URI is not set in config.ini [JTMF] section.")
        logger.error("JTMF API URI missing in configuration.")
        return False

    # --- Get Test Run / Case Keys (Example - Adapt to actual JTM F API) ---
    # The specific JTM F API endpoint and required IDs might differ significantly.
    # This example uses placeholder IDs often needed for test execution APIs.
    test_execution_key = askstring("JTM F Test Execution", "Enter the JTM F Test Execution Key:")
    if not test_execution_key:
        logger.warning("User cancelled or did not enter JTM F Test Execution Key.")
        return False

    # test_case_key = askstring("JTM F Test Case", "(Optional) Enter the JTM F Test Case Key:")
    # test_run_id = askstring("JTM F Test Run ID", "(Optional) Enter the JTM F Test Run ID:")

    # --- Prepare Request (Adapt to actual JTM F API endpoint and structure) ---
    # Example: Assuming an endpoint like /rest/raven/1.0/api/testrun/{execKey}/attachment
    # The actual payload structure (JSON vs multipart) depends heavily on the API.
    # This example assumes a Base64 encoded payload within JSON, which is less common
    # for file uploads than multipart/form-data but was hinted at in the original code.

    # **Option 1: Assuming Base64 JSON Payload (from original code hint)**
    # upload_url = f"{api_uri_base}/rest/raven/1.0/api/testrun/{test_execution_key}/attachment" # Example endpoint
    # headers = {
    #     "Authorization": f"Bearer {api_token}",
    #     "Accept": "application/json",
    #     "Content-Type": "application/json",
    # }
    # try:
    #     with open(file_path, 'rb') as file:
    #         file_content = file.read()
    #         file_base64 = base64.b64encode(file_content).decode('utf-8')

    #     file_type, _ = mimetypes.guess_type(file_path)
    #     if file_type is None:
    #         file_type = 'application/octet-stream'

    #     payload = {
    #         'fileName': os.path.basename(file_path),
    #         'file': file_base64, # Base64 encoded content
    #         'contentType': file_type,
    #         # Add other required fields like testCaseKey, testRunId if needed by API
    #     }
    #     response = requests.post(upload_url, headers=headers, json=payload, timeout=60)

    # **Option 2: Assuming Multipart Upload (More Standard for Files)**
    upload_url = f"{api_uri_base}/rest/raven/1.0/api/testrun/{test_execution_key}/attachment" # Adjust endpoint if needed
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
            # Content-Type is set automatically by requests for multipart
        "X-Atlassian-Token": "no-check" # May or may not be needed for JTM F
    }
    try:
        file_type, _ = mimetypes.guess_type(file_path)
        if file_type is None:
            file_type = 'application/octet-stream'

        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, file_type)}
            # Add other form data if required by the API (e.g., testCaseKey)
            # data = {'testCaseKey': test_case_key}
            data = None # If no extra data needed

            showinfo("Upload Info", f"Uploading '{os.path.basename(file_path)}' to JTMF Execution {test_execution_key}...")

            logger.debug(f"POSTing attachment to {upload_url}")
            response = requests.post(
                upload_url,
                headers=headers,
                files=files,
                data=data, # Add other form data here if needed
                timeout=60
            )


        # --- Handle Response (Generic - Adapt based on JTM F specifics) ---
        logger.debug(f"JTMF Response Status Code: {response.status_code}")

        # Common success codes: 200 OK, 201 Created, 204 No Content
        if response.status_code in [200, 201, 204]:
            logger.info(f"Successfully uploaded evidence to JTMF Execution {test_execution_key}.")
            showinfo("Success", f"Evidence uploaded successfully to JTMF Execution {test_execution_key}!")
            return True
        else:
            error_msg = f"Failed to upload to JTMF. Status: {response.status_code}."
            try:
                error_data = response.json()
                error_msg += f" Response: {error_data}"
                logger.error(f"{error_msg}")
            except requests.exceptions.JSONDecodeError:
                logger.error(f"{error_msg} Response: {response.text}") # Log raw text if not JSON
            showerror("Upload Failed", error_msg)
            return False

    except FileNotFoundError:
        logger.error(f"File not found for upload: {file_path}")
        showerror("File Error", f"The specified file could not be found:\n{file_path}")
        return False
    except requests.exceptions.RequestException as e:
            logger.error(f"Network or request error uploading to JTMF: {e}", exc_info=True)
            showerror("Network Error", f"Could not connect to JTMF or upload failed:\n{e}")
            return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during JTMF upload: {e}", exc_info=True)
        showerror("Error", f"An unexpected error occurred during upload:\n{e}")
        return False


# --- Upload Choice Dialog ---
def ask_file_upload(parent_window, file_path: str):
    """
    Asks the user if they want to upload the generated file and to which system.

    Args:
        parent_window: The parent Tkinter window (for modality). Can be None.
        file_path: Path to the file to potentially upload.
    """
    if not file_path or not os.path.exists(file_path):
            logger.warning("ask_file_upload called with invalid file path.")
            return

    # Use askyesno which is simpler than a custom choice window if only Yes/No needed first
    if askyesno("Upload Document?", f"Document saved successfully:\n{file_path}\n\nDo you want to upload this document?"):
        ask_file_upload_type(parent_window, file_path)


def ask_file_upload_type(parent_window, file_path: str):
    """Presents a choice to upload to JIRA or JTMF."""
    choice_win = ctk.CTkToplevel(parent_window)
    choice_win.title("Upload Destination")
    choice_win.geometry("350x200")
    choice_win.transient(parent_window) # Keep on top of parent
    choice_win.grab_set() # Make modal

    choice_var = ctk.StringVar(value="None")

    def submit_choice():
        choice = choice_var.get()
        choice_win.destroy() # Close the dialog first

        if choice == "jira":
            upload_doc_to_jira(file_path)
        elif choice == "jtmF":
            upload_doc_to_jtmF(file_path)
        else:
                logger.info("User selected no upload destination.")


    ctk.CTkLabel(choice_win, text="Select the system to upload to:", font=("Arial", 12)).pack(pady=10, anchor="w", padx=20)

    rb_jira = ctk.CTkRadioButton(choice_win, text="JIRA Issue Attachment", variable=choice_var, value="jira")
    rb_jira.pack(pady=5, anchor="w", padx=20)

    rb_jtmF = ctk.CTkRadioButton(choice_win, text="JTMF Test Evidence", variable=choice_var, value="jtmF")
    rb_jtmF.pack(pady=5, anchor="w", padx=20)

    submit_button = ctk.CTkButton(choice_win, text="Upload", command=submit_choice)
    submit_button.pack(pady=20)

    # Center the window (optional)
    choice_win.update_idletasks()
    x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (choice_win.winfo_width() // 2)
    y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (choice_win.winfo_height() // 2)
    choice_win.geometry(f"+{x}+{y}")

    choice_win.wait_window() # Wait for the window to be destroyed
