import json
from typing import Any, Dict, List, Union

import os


class Color:
    def __init__(self, value:int | str):
        self.value = value
        if isinstance(value,str):
            self.value = int(value.replace("#","0x"),16)

    def __str__(self):
        return f"{hex(self.value).replace('0x','#')}"


class Config:
    """
    This class provides a simple configuration file system with easy usage.

    Attributes:
        file (str): The file path for the configuration data.
        layout (List[str]): The layout of the configuration data.
        data (Dict[str, Union[Dict[str, Any], List[Any]]]): The configuration data.
    """

    def __init__(self, file: str):
        """
        Initializes the Config object with a specified file.

        Parameters:
            file (str): The file path for the configuration data.
        """
        self.__file = file
        self.__layout = []
        self.comments = {'top': []}
        self.data = {}

    def set_layout(self, layout: List[str]) -> None:
        """
        Sets the layout for the configuration file.

        Parameters:
            layout (List[str]): The layout of the configuration data.
        """
        self.__layout = layout
        self.data = {section: {} for section in layout}
        self.comments.update({section: {} for section in layout})

    def save(self,create_folder:bool = False) -> None:
        """
        Saves the current configuration data to the specified file.
        """
        if create_folder:
            if os.path.exists(self.__file) == False:
                os.makedirs(os.path.dirname(self.__file).replace("\\", "/"),exist_ok=True)
        lines = []

        # Add top-level comments
        for comment in self.comments['top']:
            lines.append(f"# {comment}\n")

        for section in self.__layout:
            lines.append(f"[{section}]\n")
            section_data = self.data.get(section, {})
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if key in self.comments[section]:
                        for comment in self.comments[section][key]:
                            lines.append(f"# {comment}\n")
                    if isinstance(value, str):
                        value = f"\"{value}\""
                    elif not isinstance(value, (int, float, bool,Color,tuple)):
                        raise ValueError("Invalid value: must be a boolean, string, int, float, or tuple")
                    lines.append(f"{key} = {value}\n")
            elif isinstance(section_data, list):
                for item in section_data:
                    if section_data.index(item) in self.comments[section]:
                        for comment in self.comments[section][section_data.index(item)]:
                            lines.append(f"# {comment}\n")
                    if isinstance(item, str):
                        item = f"\"{item}\""
                    elif not isinstance(item, (int, float, bool)):
                        raise ValueError("Invalid item in list: must be a boolean, string, int, or float")
                    lines.append(f"- {item}\n")
            lines.append("\n")
        
        with open(self.__file, "w") as f:
            f.writelines(lines)

    def load(self) -> None:
        """
        Loads the configuration data from the specified file.
        """
        with open(self.__file, "r") as f:
            lines = f.readlines()

        current_section = None
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                continue
            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                current_section = stripped_line[1:-1]
                self.data[current_section] = {}
            elif "=" in stripped_line:
                if current_section is None:
                    raise ValueError("Key-value pair found outside of a section")
                key, value = map(str.strip, stripped_line.split("=", 1))
                if " " in key:
                    raise ValueError(f"Invalid key '{key}': keys cannot contain spaces")
                if (value == "true") or (value == "True"):
                    value = True
                elif (value == "false") or (value == "False"):
                    value = False
                elif (value.startswith("(")) and (value.endswith(")")):
                    # Assuming the tuple contains only integers
                    value = tuple(map(int, value[1:-1].split(",")))
                elif (value.startswith("#")):
                    # Assume it is a color in hexadecimal format
                    value = Color(value)
                else:
                    value = json.loads(value)
                self.data[current_section][key] = value
            elif stripped_line.startswith("-"):
                if current_section is None:
                    raise ValueError("List item found outside of a section")
                if not isinstance(self.data[current_section], list):
                    self.data[current_section] = []
                value = stripped_line[1:].strip()
                if (value == "true") or (value == "True"):
                    value = True
                elif (value == "false") or (value == "False"):
                    value = False
                else:
                    value = json.loads(value)
                self.data[current_section].append(value)

    def __getitem__(self, key: str) -> Union[Dict[str, Any], List[Any]]:
        """
        Retrieves the value of a specified key from the configuration data.

        Parameters:
            key (str): The key to retrieve the value for.

        Returns:
            Union[Dict[str, Any], List[Any]]: The value associated with the specified key.
        """
        if key in self.data:
            try:
                return self.data[key]
            except KeyError:
                return None
        else:
            raise KeyError(f"'{key}' not found in the configuration data")

    def __setitem__(self, key: str, value: Union[Dict[str, Any], List[Any]]) -> None:
        """
        Sets the value of a specified key in the configuration data.

        Parameters:
            key (str): The key to set the value for.
            value (Union[Dict[str, Any], List[Any]]): The value to set for the specified key.
        """
        if key in self.data:
            self.data[key] = value
        else:
            raise KeyError(f"'{key}' not found in the configuration data")

    def get_data(self) -> Dict[str, Union[Dict[str, Any], List[Any]]]:
        """
        Returns the entire configuration data.

        Returns:
            Dict[str, Union[Dict[str, Any], List[Any]]]: The entire configuration data.
        """
        return self.data

    def create_comment(self, comment: str, section: str = None, key: str | int = None) -> None:
        """
        Creates a comment for a specified key in a specified section, or a top-level comment if no section/key is provided.

        Parameters:
            comment (str): The comment text.
            section (str, optional): The section where the comment should be added.
            key (str, optional): The key above which the comment should be added.
        """
        if not comment:
            raise ValueError("Comment cannot be empty")

        if section is None and key is None:
            # Add a top-level comment
            self.comments['top'].append(comment)
        elif section is not None:
            if section not in self.__layout:
                raise ValueError(f"'{section}' is not a valid section")
            if key is not None:
                if self.data[section][key] is None:
                    raise ValueError(f"'{key}' is not a valid key in '{section}'")
                try:
                    self.comments[section][key].append(comment)
                except KeyError:
                    self.comments[section][key] = [comment]
            else:
                raise ValueError("Key must be specified if section is provided")
