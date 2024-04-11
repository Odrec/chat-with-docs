import os
import pandas as pd
from openai import OpenAI
import streamlit as st
from streamlit import session_state
from streamlit_option_menu import option_menu
from streamlit_cookies_manager import EncryptedCookieManager
from src import menu_utils
from dotenv import load_dotenv

from src.language_utils import initialize_language

# Load environment variables
load_dotenv()


class SidebarManager:

    def __init__(self):
        """
        Initialize the SidebarManager instance by setting up session cookies and initializing the language.
        """
        self.cookies = self.initialize_cookies()
        initialize_language()

    @staticmethod
    def initialize_cookies():
        """
        Initialize cookies for managing user sessions with enhanced security.

        Uses an encrypted cookie manager and detects the Safari browser to handle specific JavaScript-based delays.
        This ensures a smooth user experience across different browsers.
        """
        cookies = EncryptedCookieManager(
            prefix=os.getenv("COOKIES_PREFIX"),
            password=os.getenv("COOKIES_PASSWORD")
        )

        # JavaScript for detecting Safari browser and adding a delay
        detect_safari_and_sleep_script = """
        <script>
        var isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
        if (isSafari) {
            // Delay execution for specified time when Safari is detected
            // Time is specified in milliseconds (e.g., 2000 milliseconds = 2 seconds)
            setTimeout(function() {
                // After the delay, you may want to execute something specific for Safari
                // Or simply proceed with your app initialization
                console.log('Safari detected, proceeded after delay');
                // Communicate back to Streamlit (if needed)
                window.parent.streamlit.setComponentValue("safari_delayed", true);
            }, 2000); // Adjust the delay time as needed
        }
        </script>
        """

        # Display the script in a Streamlit markdown to ensure it runs
        st.markdown(detect_safari_and_sleep_script, unsafe_allow_html=True)

        return cookies

    def verify_user_session(self):
        """
        Verify the user's session validity. If cookies indicate the session is not yet initiated,
        then redirect the user to the start page.

        This function ensures that unauthorized users are not able to access application sections
        that require a valid session.
        """
        if not self.cookies.ready():
            st.spinner()
            st.stop()

        if self.cookies.get("session") != 'in':
            st.switch_page("start.py")

    @staticmethod
    def initialize_session_variables():
        """
        Initialize essential session variables with default values.

        Sets up the initial state for model selection, chatbot paths, conversation histories,
        prompt options, etc., essential for the application to function correctly from the start.
        """
        required_keys = {
            'model_selection': "OpenAI",
            'selected_chatbot_path': [],
            'conversation_histories': {},
            'selected_chatbot_path_serialized': "",
            'prompt_options': menu_utils.load_prompts_from_yaml(),
            'edited_prompts': {},
            'disable_custom': False,
        }

        for key, default_value in required_keys.items():
            if key not in session_state:
                session_state[key] = default_value

    @staticmethod
    def display_logo():
        """
        Display the application logo in the sidebar.

        Utilizes Streamlit columns to center the logo and injects CSS to hide the fullscreen
        button that appears on hover over the logo.
        """
        with st.sidebar:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image("img/logo.svg", width=100)

                # Gets rid of full screen option for logo image
                hide_img_fs = '''
                <style>
                button[title="View fullscreen"]{
                    visibility: hidden;}
                </style>
                '''

                st.markdown(hide_img_fs, unsafe_allow_html=True)

    @staticmethod
    def load_prompts():
        """
        Load chat prompts based on the selected or default language.

        This method enables dynamic loading of chat prompts to support multi-lingual chatbot interactions.
        If no language is specified in the query parameters, German ('de') is used as the default language.
        """
        language = st.query_params.get('lang', False)
        # Use German language as default
        if not language:
            language = "de"

        """Load chat prompts based on language."""
        session_state["prompt_options"] = menu_utils.load_prompts_from_yaml(language=language)

    def logout_and_redirect(self):
        """
        Perform logout operations and redirect the user to the start page.

        This involves resetting cookies and session variables that signify the user's logged-in state,
        thereby securely logging out the user.
        """
        self.cookies["session"] = 'out'
        session_state["password_correct"] = False
        session_state['credentials_checked'] = False
        st.switch_page('start.py')

    def _display_chatbots_menu(self, options, path=[]):
        """
        Recursively display sidebar menu for chatbot selection based on a nested dictionary structure.

        Allows users to navigate and select chatbots in a hierarchical manner, updating the session state
        to reflect the current selection path.

        :param options: A dictionary containing chatbot options and potential sub-options.
        :param path: A list representing the current selection path as the user navigates the menu.
        """
        if isinstance(options, dict) and options:  # Verify options is a dictionary and not empty
            next_level = list(options.keys())

            with st.sidebar:
                choice = option_menu("", next_level,
                                     # icons=['chat-dots'] * len(next_level),
                                     # menu_icon="cast",
                                     default_index=0)

            if choice:
                new_path = path + [choice]
                session_state['selected_chatbot_path'] = new_path
                self._display_chatbots_menu(options.get(choice, {}), new_path)

    def display_sidebar_controls(self):
        """
        Display sidebar controls and settings for chatbot conversations.

        This function performs the following steps:
        1. Loads prompt options to display in the chatbots' menu.
        2. Checks for changes in the selected chatbot path to update the session state accordingly.
        3. Displays model information for the selected model, e.g., OpenAI.
        4. Provides options for the user to interact with the conversation history,
        including deleting and downloading conversations.
        5. Adds custom CSS to stylize the sidebar.
        6. Offers a logout option.
        """
        self._load_and_display_prompts()

        self._update_path_in_session_state()

        self._display_model_information()

        self._show_conversation_controls()

        self._add_custom_css()

        self._logout_option()

    def _load_and_display_prompts(self):
        """
        Load chat prompts from the session state and display them in the chatbots menu in the sidebar.

        This method first loads the prompts by calling the `load_prompts` method and
        then displays the chatbots menu with the loaded prompts using the `_display_chatbots_menu` method.
        """
        self.load_prompts()
        self._display_chatbots_menu(session_state['prompt_options'])

    @staticmethod
    def _update_path_in_session_state():
        """
        Check if the selected chatbot path in the session state has changed and update the serialized path accordingly.

        This static method compares the current selected chatbot path with the serialized chatbot path saved
         in the session.
        If there is a change, it updates the session state with the new serialized path, allowing for tracking
         the selection changes.
        """
        path_has_changed = menu_utils.path_changed(session_state['selected_chatbot_path'],
                                                   session_state['selected_chatbot_path_serialized'])
        if path_has_changed:
            serialized_path = '/'.join(session_state['selected_chatbot_path'])
            session_state['selected_chatbot_path_serialized'] = serialized_path

    @staticmethod
    def _display_model_information():
        """
        Display OpenAI model information in the sidebar if the OpenAI model is the current selection.

        In the sidebar, this static method shows the model name and version pulled from environment variables
        if 'OpenAI' is selected as the model in the session state. The model information helps users
        identify the active model configuration.
        """
        with st.sidebar:
            if session_state['model_selection'] == 'OpenAI':
                model_text = session_state['_']("Model:")
                st.write(f"{model_text} {os.getenv('OPENAI_MODEL')}")

    def _show_conversation_controls(self):
        """
        Display buttons for conversation management, including deleting and downloading conversation history,
         in the sidebar.

        This method checks if there is an existing conversation history for the currently selected chatbot path and,
         if so,
        displays options to either delete this history or download it as a CSV file. It leverages the
        `_delete_conversation_button` and `_download_conversation_button` methods to render these options.
        """
        conversation_key = session_state['selected_chatbot_path_serialized']
        if conversation_key in session_state['conversation_histories'] and session_state['conversation_histories'][
            conversation_key]:
            with st.sidebar:
                st.markdown("---")
                st.write(session_state['_']("**Options**"))
                col1, col2 = st.columns([1, 5])
                self._delete_conversation_button(col1)
                self._download_conversation_button(col2, conversation_key)

    @staticmethod
    def _delete_conversation_button(column):
        """
        Render a button in the specified column that allows the user
        to delete the active chatbot's conversation history.

        On button click, this static method removes the conversation history from the session state for the
        current chatbot path and triggers a page rerun to refresh the state.

        :param column: The column in Streamlit where the button should be placed.
        This should be a Streamlit column object.
        """
        if column.button("🗑️", help=session_state['_']("Delete the Conversation")):
            session_state['conversation_histories'][session_state['selected_chatbot_path_serialized']] = []
            st.rerun()

    @staticmethod
    def _download_conversation_button(column, conversation_key):
        """
        Render a button in the specified column allowing users to download the conversation history as a CSV file.

        This static method creates a DataFrame from the conversation history stored in the session state under the
        given `conversation_key`, converts it to a CSV format, and provides a download button for the generated CSV.

        :param column: The column in Streamlit where the button should be placed.
        This should be a Streamlit column object.
        :param conversation_key: The key that uniquely identifies the conversation in the session state's
        conversation histories.
        """
        conversation_to_download = session_state['conversation_histories'][conversation_key]
        conversation_df = pd.DataFrame(conversation_to_download,
                                       columns=[session_state['_']('Speaker'),
                                                session_state['_']('Message'),
                                                session_state['_']('System prompt')])
        conversation_csv = conversation_df.to_csv(index=False).encode('utf-8')
        column.download_button("📂", data=conversation_csv, file_name="conversation.csv", mime="text/csv",
                               help=session_state['_']("Download the Conversation"))

    @staticmethod
    def _add_custom_css():
        """
        Inject custom CSS into the sidebar to enhance its aesthetic according to the current theme.

        This static method retrieves the secondary background color from Streamlit's theme options
        and applies custom styles to various sidebar elements, enhancing the user interface.
        """
        color = st.get_option('theme.secondaryBackgroundColor')
        css = f"""
                [data-testid="stSidebarNav"] {{
                    position:absolute;
                    bottom: 0;
                    z-index: 1;
                    background: {color};
                }}
                ... (rest of CSS)
                """
        with st.sidebar:
            st.markdown("---")
            st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

    def _logout_option(self):
        """
        Display a logout button in the sidebar, allowing users to end their session.

        This method renders a logout button in the sidebar. If clicked, it calls the `logout_and_redirect` method
        to clear session variables and cookies, securely logging out the user and redirecting them to the start page.
        """
        with st.sidebar:
            if st.button(session_state['_']('Logout')):
                self.logout_and_redirect()
            st.write(f"Version: *Beta*")


class ChatManager:

    def __init__(self, user):
        """
        Initializes the ChatManager instance with the user's identifier.

        Parameters:
        - user: A string identifier for the user, used to differentiate messages in the conversation.
        """
        self.client = None
        session_state['USER'] = user

    def set_client(self, client):
        """
        Sets the client for API requests, typically used to interface with chat models.

        Parameters:
        - client: The client instance responsible for handling requests to chat models.
        """
        self.client = client

    @staticmethod
    def _update_edited_prompt():
        """
        Updates the edited prompt in the session state to reflect changes made by the user.
        """
        session_state['edited_prompts'][session_state[
            'selected_chatbot_path_serialized']] = session_state['edited_prompt']

    @staticmethod
    def _restore_prompt():
        """
        Restores the original chatbot prompt by removing any user-made edits from the session state.
        """
        if session_state['selected_chatbot_path_serialized'] in session_state['edited_prompts']:
            del session_state['edited_prompts'][session_state['selected_chatbot_path_serialized']]

    def _display_prompt_editor(self, description):
        """
        Displays an editable text area for the current chatbot prompt, allowing the user to make changes.

        Parameters:
        - description: The default chatbot prompt description which can be edited by the user.
        """
        current_chatbot_path_serialized = session_state['selected_chatbot_path_serialized']
        current_edited_prompt = session_state['edited_prompts'].get(current_chatbot_path_serialized, description)

        st.text_area(session_state['_']("System prompt"),
                     value=current_edited_prompt,
                     on_change=self._update_edited_prompt,
                     key='edited_prompt',
                     label_visibility='hidden')

        st.button("🔄", help=session_state['_']("Restore Original Prompt"), on_click=self._restore_prompt)

    @staticmethod
    def _get_description_to_use(default_description):
        """
        Retrieves and returns the current prompt description for the chatbot, considering any user edits.

        Parameters:
        - default_description: The default description provided for the chatbot's prompt.

        Returns:
        - The current (possibly edited) description to be used as the prompt.
        """
        return session_state['edited_prompts'].get(session_state[
                                                       'selected_chatbot_path_serialized'], default_description)

    @staticmethod
    def _display_conversation(conversation_history, container=None):
        """
        Displays the conversation history between the user and the assistant within the given container or globally.

        Parameters:
        - conversation_history: A list containing tuples of (speaker, message) representing the conversation.
        - container: The Streamlit container (e.g., column, expander) where the messages should be displayed.
          If None, messages will be displayed in the main app area.
        """
        for speaker, message, __ in conversation_history:
            chat_message_container = container if container else st
            if speaker == session_state['USER']:
                chat_message_container.chat_message("user").write(message)
            elif speaker == "Assistant":
                chat_message_container.chat_message("assistant").write(message)

    @staticmethod
    def _get_current_conversation_history():
        """
        Retrieves the current conversation history for the selected chatbot path from the session state.

        Returns:
        - A list representing the conversation history.
        """
        serialized_path = session_state['selected_chatbot_path_serialized']
        if serialized_path not in session_state['conversation_histories']:
            session_state['conversation_histories'][serialized_path] = []
        return session_state['conversation_histories'][serialized_path]

    @staticmethod
    def _is_new_message(current_history, user_message):
        """
        Checks if the last message in history differs from the newly submitted user message.

        Parameters:
        - current_history: The current conversation history.
        - user_message: The newly submitted user message.

        Returns:
        - A boolean indicating whether this is a new unique message submission.
        """
        if (not current_history or current_history[-1][0] != session_state['USER']
                or current_history[-1][1] != user_message):
            return True
        return False

    @staticmethod
    def _append_user_message_to_history(current_history, user_message, description_to_use):
        """
        Appends the user's message to the conversation history in the session state.

        Parameters:
        - current_history: The current conversation history.
        - user_message: The message input by the user.
        - description_to_use: The system description or prompt that should accompany user messages.
        """
        # Adding user message and description to the current conversation
        current_history.append((session_state['USER'], user_message, description_to_use))
        session_state['conversation_histories'][session_state['selected_chatbot_path_serialized']] = current_history

    def _process_response(self, current_history, user_message, description_to_use):
        """
        Submits the user message to OpenAI, retrieves the response, and updates the conversation history.

        Parameters:
        - current_history: The current conversation history.
        - user_message: The message input by the user.
        - description_to_use: The current system description or prompt associated with the user message.
        """
        response = self.client.get_response(user_message, description_to_use)
        # Add AI response to the history
        current_history.append(('Assistant', response, ""))
        session_state['conversation_histories'][session_state['selected_chatbot_path_serialized']] = current_history

    def _handle_user_input(self, description_to_use):
        """
        Handles the user input: sends the message to OpenAI, prints it, and updates the conversation history.

        Parameters:
        - description_to_use: The current system description or prompt used alongside user messages.
        """
        if user_message := st.chat_input(session_state['USER']):
            current_history = self._get_current_conversation_history()

            # Ensures unique submission to prevent re-running on refresh
            if self._is_new_message(current_history, user_message):
                self._append_user_message_to_history(current_history, user_message, description_to_use)

                # Print user message immediately after getting entered because we're streaming the chatbot output
                with st.chat_message("user"):
                    st.markdown(user_message)

                # Process and display response
                self._process_response(current_history, user_message, description_to_use)
                st.rerun()

    @staticmethod
    def _fetch_chatbot_description():
        """
        Fetches the description for the current chatbot based on the selected path.

        Returns:
        - A string containing the description of the current chatbot.
        """
        return menu_utils.get_final_description(session_state["selected_chatbot_path"], session_state["prompt_options"])

    @staticmethod
    def _display_openai_model_info():
        """
        Displays information about the current OpenAI model in use.
        """
        using_text = session_state['_']("You're using the following OpenAI model:")
        remember_text = session_state['_']("Remember **not** to enter any personal information"
                                           " or copyrighted material.")
        model_info = f"{using_text} **{os.getenv('OPENAI_MODEL')}**. {remember_text}"
        st.write(model_info)
        st.write(session_state['_']("Each time you enter information,"
                                    " a system prompt is sent to the chat model by default."))

    def _display_chat_interface_header(self):
        """
        Displays headers and model information on the chat interface based on the user's selection.
        """
        st.markdown("""---""")  # Separator for layout
        if (session_state['selected_chatbot_path_serialized'] not in session_state['conversation_histories']
                or not session_state['conversation_histories'][session_state['selected_chatbot_path_serialized']]):
            st.header(session_state['_']("How can I help you?"))
            if session_state['model_selection'] == 'OpenAI':
                self._display_openai_model_info()

    def display_chat_interface(self):
        """
        Displays the chat interface, manages the display of conversation history, and handles user input.

        This method sets up the interface for the chat, including fetching and displaying the system prompt,
        updating session states as necessary, and calling methods to display conversation history and handle user input.
        """
        if 'selected_chatbot_path' in session_state and session_state["selected_chatbot_path"]:

            description = self._fetch_chatbot_description()

            if isinstance(description, str) and len(description.strip()) > 0:

                # Display chat interface header and model information if applicable
                self._display_chat_interface_header()

                with st.expander(label=session_state['_']("View or edit system prompt"), expanded=False):
                    self._display_prompt_editor(description)

                st.markdown("""---""")

                description_to_use = self._get_description_to_use(description)

                # Displays the existing conversation history
                conversation_history = session_state['conversation_histories'].get(session_state[
                                                                                       'selected_chatbot_path_serialized'],
                                                                                   [])
                self._display_conversation(conversation_history)

                # Handles the user's input and interaction with the LLM
                self._handle_user_input(description_to_use)
            else:
                st.error(session_state['_']("The System Prompt should be a string and not empty."))


class AIClient:

    def __init__(self):
        if session_state['model_selection'] == 'OpenAI':

            @st.cache_resource
            def load_openai_data():
                return OpenAI(), os.getenv('OPENAI_MODEL')

            self.client, self.model = load_openai_data()
        else:
            pass
            # Add here client initialization for local model
            # For example using OpenLLM as inference server
            # session_state["inference_server_url"] = "http://localhost:3000/v1"
            # self.client = OpenAI(base_url=session_state['inference_server_url'])
            # models = session_state["client"].models.list()
            # self.model = models.data[0].id

    @staticmethod
    def _generate_response(stream):
        """
        Extracts the content from the stream of responses from the OpenAI API.
        Parameters:
            stream: The stream of responses from the OpenAI API.

        """

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta:
                chunk_content = chunk.choices[0].delta.content
                yield chunk_content

    @staticmethod
    def _concatenate_partial_response(partial_response):
        """
        Concatenates the partial response into a single string.

        Parameters:
            partial_response (list): The chunks of the response from the OpenAI API.

        Returns:
            str: The concatenated response.
        """
        str_response = ""
        for i in partial_response:
            if isinstance(i, str):
                str_response += i

        st.markdown(str_response)

        return str_response

    def get_response(self, prompt, description_to_use):
        """
        Sends a prompt to the OpenAI API and returns the API's response.

        Parameters:
            prompt (str): The user's message or question.
            description_to_use (str): Additional context or instructions to provide to the model.

        Returns:
            str: The response from the chatbot.
        """
        try:
            # Prepare the full prompt and messages with context or instructions
            messages = self._prepare_full_prompt_and_messages(prompt, description_to_use)

            # Send the request to the OpenAI API
            # Display assistant response in chat message container
            response = ""
            with st.chat_message("assistant"):
                with st.spinner(session_state['_']("Generating response...")):
                    stream = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        stream=True,
                    )
                    partial_response = []

                    gen_stream = self._generate_response(stream)
                    for chunk_content in gen_stream:
                        # check if the chunk is a code block
                        if chunk_content == '```':
                            partial_response.append(chunk_content)
                            code_block = True
                            while code_block:
                                try:
                                    chunk_content = next(gen_stream)
                                    partial_response.append(chunk_content)
                                    if chunk_content == "`\n\n":
                                        code_block = False
                                        str_response = self._concatenate_partial_response(partial_response)
                                        partial_response = []
                                        response += str_response

                                except StopIteration:
                                    break

                        else:
                            # If the chunk is not a code block, append it to the partial response
                            partial_response.append(chunk_content)
                            if chunk_content:
                                if '\n' in chunk_content:
                                    str_response = self._concatenate_partial_response(partial_response)
                                    partial_response = []
                                    response += str_response
                # If there is a partial response left, concatenate it and render it
                if partial_response:
                    str_response = self._concatenate_partial_response(partial_response)
                    response += str_response

            return response

        except Exception as e:
            print(f"An error occurred while fetching the OpenAI response: {e}")
            # Optionally, return a default error message or handle the error appropriately.
            return "Sorry, I couldn't process that request."

    @staticmethod
    def _prepare_full_prompt_and_messages(user_prompt, description_to_use):
        """
        Prepares the full prompt and messages combining user input and additional descriptions.

        Parameters:
            user_prompt (str): The original prompt from the user.
            description_to_use (str): Additional context or instructions to provide to the model.

        Returns:
            list: List of dictionaries containing messages for the chat completion.
        """

        if session_state["model_selection"] == 'OpenAI':
            messages = [{
                'role': "system",
                'content': description_to_use
            }]
        else:  # Add here conditions for different types of models
            messages = []

        # Add the history of the conversation, ignore the system prompt
        for speaker, message, __ in session_state['conversation_histories'][
            session_state['selected_chatbot_path_serialized']]:
            role = 'user' if speaker == session_state['USER'] else 'assistant'
            messages.append({'role': role, 'content': message})

        # Building the messages with the "system" message based on expertise area
        if session_state["model_selection"] == 'OpenAI':
            messages.append({"role": "user", "content": user_prompt})
        else:
            # Add the description to the current user message to simulate a system prompt.
            # This is for models that were trained with no system prompt: LLaMA/Mistral/Mixtral.
            # Source: https://github.com/huggingface/transformers/issues/28366
            # Maybe find a better solution or avoid any system prompt for these models
            messages.append({"role": "user", "content": description_to_use + "\n\n" + user_prompt})

        # This method can be expanded based on how you want to structure the prompt
        # For example, you might prepend the description_to_use before the user_prompt
        return messages
