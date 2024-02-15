# Processors Module

The Processors Module offers solutions for data loading, parsing, and transforming, facilitating the handling of dialogues, documents, and URLs. Below are detailed explanations of each class and their supported parameters for customization.

## MessageSplitter
- **Purpose**: Splits a `Dialog` object into separate `Dialog` objects for each message, allowing independent processing based on the roles of the messages.
- **Parameters**:
  - `acceptedRoles`: List of message roles to include in the split. If empty, all messages are accepted.

## TextLineSplitter
- **Purpose**: Splits text prompts within a `Dialog` into separate `Dialog` objects for each line of text, enabling line-by-line processing.
- **Parameters**:
  - `lastMessageCount`: Number of last messages to consider for splitting.
  - `acceptedRoles`: List of message roles to consider for splitting. If empty, all roles are included.

## TextListSplitter
- **Purpose**: Splits text prompts within a `Dialog` into separate `Dialog` objects for each list item, aimed at processing each list item individually.
- **Parameters**:
  - `lastMessageCount`: Number of last messages to consider for splitting.
  - `acceptedRoles`: List of message roles to consider for splitting. If empty, all roles are included.
  - `removeListMarks`: Boolean indicating whether to remove list markers (e.g., bullets, numbers) from the beginning of each list item.

## TextRegExpSplitter
- **Purpose**: Splits text prompts within a `Dialog` based on a regular expression pattern, facilitating customized text segmentation.
- **Parameters**:
  - `pattern`: Regular expression pattern used for splitting text prompts.
  - `lastMessageCount`: Number of last messages to consider for splitting.
  - `acceptedRoles`: List of message roles to consider for splitting. If empty, all roles are included.
  - `removePattern`: Boolean indicating whether to remove the matched pattern from the beginning of each segmented text.

## DocxLoader
- **Purpose**: Loads content from a DOCX file, converting each paragraph into a text prompt for processing.
- **Parameters**:
  - `docxFile`: Path to the DOCX file to be loaded.
  - `convert_urls`: Boolean indicating whether URLs in the text should be converted to URL prompts.

## XlsxLoader
- **Purpose**: Loads content from an XLSX file, converting each sheet into a text prompt for processing.
- **Parameters**:
  - `xlsxFile`: Path to the XLSX file to be loaded (optional if `xlsxBytesArray` is provided).
  - `xlsxBytesArray`: Byte array of the XLSX file content (optional if `xlsxFile` is provided).
  - `convert_urls`: Boolean indicating whether URLs in the text should be converted to URL prompts.

## UrlLoader
- **Purpose**: Loads text content from specified URL(s), facilitating the processing of web content.
- **Parameters**:
  - `urlContainingContent`: URL(s) from which the text content will be loaded.

## XlsxSplitter
- **Purpose**: Splits content loaded from an XLSX file into multiple `Dialog` objects based on rows or cells.
- **Parameters**:
  - `splitMethod`: Method to split the content ('row' or 'cell').
  - `lastMessageCount`: Number of last messages to consider for splitting.
  - `acceptedRoles`: List of message roles to consider for splitting. If empty, all roles are included.

## DialogToFileDownloader
- **Purpose**: Downloads all dialog content to a folder, creating an XML index and an HTML file for content navigation.
- **Parameters**:
  - `dirPath`: Directory path where the content will be downloaded. If not provided, a default `/downloads/` directory in the current working directory will be used.

This documentation aims to provide a comprehensive guide to utilizing the Processors Module effectively, with an emphasis on the flexibility offered by each class's parameters.
