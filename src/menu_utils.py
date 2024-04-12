import yaml
import streamlit as st

from langchain.prompts import PromptTemplate


def _load_docs_prompts_from_yaml(language, prompt_key):
    # Use basic prompts
    if language == 'en':
        file_path_basic = 'prompts_config/docs_basic_prompts_en.yml'
        file_path_template = 'prompts_config/prompt_templates_en.yml'
    else:
        file_path_basic = 'prompts_config/docs_basic_prompts_de.yml'
        file_path_template = 'prompts_config/prompt_templates_en.yml'

    with open(file_path_basic, 'r', encoding='utf-8') as file:
        prompt_templates_basic = yaml.safe_load(file)

    with open(file_path_template, 'r', encoding='utf-8') as file:
        prompt_templates = yaml.safe_load(file)

    template_info = prompt_templates['prompt_templates'][prompt_key]

    summary_reduce_prompt = prompt_templates['prompt_templates']['summary_reduce_assistance']
    summary_map_prompt = prompt_templates['prompt_templates']['summary_map_assistance']
    queries_prompt = {'queries': prompt_templates_basic['Queries'], 'icon': '🌟'}

    # Create the PromptTemplate instance with the loaded template and input_variables
    return (PromptTemplate(template=template_info['template'],
                           input_variables=template_info['input_variables']),
            summary_reduce_prompt,
            summary_map_prompt,
            queries_prompt)


def _load_chat_prompts_from_yaml(language):
    # Use basic prompts
    if language == 'en':
        file_path = 'prompts_config/chat_basic_prompts_en.yml'
    else:
        file_path = 'prompts_config/chat_basic_prompts_de.yml'

    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


# Function to load prompts from a YAML file
@st.cache_data
def load_prompts_from_yaml(language='de', typ='chat', prompt_key=None):
    if typ == 'chat':
        return _load_chat_prompts_from_yaml(language)
    elif typ == 'doc':
        return _load_docs_prompts_from_yaml(language, prompt_key)


def load_dict_from_yaml(file):
    return yaml.safe_load(file)


def dict_to_yaml(dictionary):
    """Converts a dictionary to a YAML string."""
    return yaml.dump(dictionary, allow_unicode=True)


def set_prompt_for_path(prompts_dict, path, edited_prompt):
    """Recursively updates the prompt for a specific path in the prompts dictionary."""
    if len(path) == 1:
        prompts_dict[path[0]] = edited_prompt
    else:
        if path[0] in prompts_dict and isinstance(prompts_dict[path[0]], dict):
            set_prompt_for_path(prompts_dict[path[0]], path[1:], edited_prompt)


@st.cache_data
def get_final_description(selected_path, options):
    """
    Navigate through the options based on the selected path,
    returning the final description or None if not a final option.

    :param selected_path: List of strings representing the selected menu path.
    :param options: The current prompt options.
    :return: The description string if a final option is reached, None otherwise.
    """
    current_option = options
    for step in selected_path:
        # Navigate deeper if the next step exists and is a dictionary
        if step in current_option and isinstance(current_option[step], dict):
            current_option = current_option[step]
        elif step in current_option:  # Final step with a description
            return current_option[step]
        else:
            return None  # Path does not exist
    # Return None if the final option hasn't been reached or doesn't have a description
    return None


@st.cache_data
def path_changed(current_path, previous_path_serialized):
    """
    Check if the current selected path has changed compared to the previously serialized path.

    :param current_path: List of currently selected path elements.
    :param previous_path_serialized: Previously stored serialized path.
    :return: Boolean indicating whether the path has changed.
    """
    current_path_serialized = '/'.join(
        current_path)  # Serialize the current path for comparison
    return current_path_serialized != previous_path_serialized
