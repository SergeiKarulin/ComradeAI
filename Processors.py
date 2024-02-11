from Mycelium import Dialog, Message, UnifiedPrompt
import re
from datetime import datetime
from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

import io
from PIL import Image

import openpyxl
import xml.etree.ElementTree as ET
from xml.dom import minidom

class MessageSplitter:
    def __init__ (self, acceptedRoles=[]):
        self.acceptedRoles = acceptedRoles
        
    def __rrshift__(self, other):
        if isinstance(other, Dialog):
            result = []
            for msg in other.messages:
                if self.acceptedRoles == [] or msg.role in self.acceptedRoles:
                    result.append(Dialog(messages=[msg]))
            return result
        else:
            raise TypeError("Message splitter is only aplicable to Dialog objects")
        
class TextLineSplitter:
    def __init__ (self, lastMessageCount = 1, acceptedRoles=[]):
        self.lastMessageCount = lastMessageCount
        self.acceptedRoles = acceptedRoles
        
    def __rrshift__(self, other):
        if isinstance(other, Dialog):
            i = 0
            result = []
            for msg in reversed(other.messages):
                if i >= self.lastMessageCount:
                    break
                if self.acceptedRoles == [] or msg.role in self.acceptedRoles:
                    for prompt in msg.unified_prompts:
                        if prompt.content_type == "text":
                            lines = prompt.content.splitlines()
                            for line in lines:
                                unified_prompt = UnifiedPrompt(content_type="text", content=line, mime_type="text/plain")
                                message = Message(unified_prompts=[unified_prompt], role = msg.role, sender_info=msg.sender_info, send_datetime=msg.send_datetime, diagnosticData=msg.diagnosticData, agentConfig=msg.agentConfig, billingData=msg.billingData, routingStrategy=msg.routingStrategy)
                                result.append(Dialog(messages=[message]))
                i += 1
            return result
        else:
            raise TypeError("Message splitter is only aplicable to Dialog objects")
        
class TextListSplitter:
    def __init__(self, lastMessageCount=1, acceptedRoles=[], removeListMarks=True):
        self.lastMessageCount = lastMessageCount
        self.acceptedRoles = acceptedRoles
        self.removeListMarks = removeListMarks

        # Extend the pattern to match more complex list bullets
        self.pattern = re.compile(r'^((\d+|[a-zA-Z])(\.\d+)*(\.[a-zA-Z])?[\.\)]\s|[-\*+]|--\s|–\s|—\s)')

    def __rrshift__(self, other):
        if isinstance(other, Dialog):
            i = 0
            result = []
            for msg in reversed(other.messages):
                if i >= self.lastMessageCount:
                    break
                if self.acceptedRoles == [] or msg.role in self.acceptedRoles:
                    for prompt in msg.unified_prompts:
                        if prompt.content_type == "text":
                            lines = prompt.content.splitlines()
                            for line in lines:
                                # Strip leading spaces and tabs before checking for list marks
                                stripped_line = line.lstrip()
                                match = self.pattern.match(stripped_line)
                                if match:
                                    # Calculate content start index, adjusting for stripped leading whitespace
                                    content_start_index = match.end() + (len(line) - len(stripped_line))
                                    line_content = line[content_start_index:] if self.removeListMarks else line
                                    if len(line_content)>0 and len(re.sub(r"[ \t]", "", line_content)) > 0:
                                        unified_prompt = UnifiedPrompt(content_type="text", content=line_content, mime_type="text/plain")
                                        message = Message(unified_prompts=[unified_prompt], role=msg.role, sender_info=msg.sender_info, send_datetime=msg.send_datetime, diagnosticData=msg.diagnosticData, agentConfig=msg.agentConfig, billingData=msg.billingData, routingStrategy=msg.routingStrategy)
                                        result.append(Dialog(messages=[message]))
                i += 1
            return result
        else:
            raise TypeError("Message splitter is only applicable to Dialog objects")
        
class DocxLoader:
    def __init__(self, docxFile, convert_urls=False):
        self.convert_urls = convert_urls
        self.docxFile = docxFile

    def __rshift__(self, other):
        if isinstance(other, Dialog):
            prompts = self.convert(self.docxFile)
            message = Message(unified_prompts=prompts, role = "user", sender_info="ComradeAI user", send_datetime=str(datetime.now()))
            other.messages.append(message)
            return other
        else:
            raise TypeError("DocxLoader can be only applied to a Dialog object")
        
    def is_url(self, text):
        # Simple URL check - may require more sophisticated validation
        return text.startswith('http://') or text.startswith('https://')

    def process_paragraph(self, paragraph):
        prompts = []
        for run in paragraph.runs:
            text = run.text.strip()
            if text and len(text)>0 and len(re.sub(r"[ \t]", "", text)) > 0:
                if self.convert_urls and self.is_url(text):
                    prompts.append(UnifiedPrompt("url", text, "text/plain"))
                else:
                    if self.contains_chars_or_nums(text):
                        prompts.append(UnifiedPrompt("text", text, "text/plain"))
        return prompts

    def process_table_cell(self, cell, table_count, row_index, cell_index):
        cell_id = f"TableCell_{table_count}_{row_index}_{cell_index}"
        cell_prompts = [UnifiedPrompt("text", cell_id, "text/plain")]

        for paragraph in cell.paragraphs:
            cell_prompts.extend(self.process_paragraph(paragraph))
        
        return cell_prompts

    def process_table(self, table, table_count):
        table_prompts = []
        for row_index, row in enumerate(table.rows):
            for cell_index, cell in enumerate(row.cells):
                table_prompts.extend(self.process_table_cell(cell, table_count, row_index, cell_index))
        return table_prompts
    
    def contains_chars_or_nums(self, s):
        return any(char.isalpha() or char.isdigit() for char in s)

    def process_image(self, run):
        inline_shapes = run.element.xpath('.//a:blip')
        if inline_shapes:
            blip_element = inline_shapes[0]
            image_rid = blip_element.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed']
            image_part = run.part.related_parts[image_rid]
            image_bytes = io.BytesIO(image_part.blob)
            image = Image.open(image_bytes)
            return UnifiedPrompt("image", image, "image/jpeg")
        return None

    def convert(self, docx_file):
        doc = Document(docx_file)
        prompts = [UnifiedPrompt("text", "This content is loaded from DOCX file.", "text/plain")]
        table_count = 0

        for element in doc.element.body:
            if isinstance(element, CT_P):
                paragraph = Paragraph(element, doc)
                for run in paragraph.runs:
                    if run.element.xpath('.//a:blip'):
                        image_prompt = self.process_image(run)
                        if image_prompt:
                            prompts.append(image_prompt)
                    else:
                        prompts.extend(self.process_paragraph(paragraph))
                        break  # Exit after processing the first non-image run
            elif isinstance(element, CT_Tbl):
                table = Table(element, doc)
                table_count += 1
                table_prompts = self.process_table(table, table_count)
                prompts.extend(table_prompts)

        return prompts
    
class XlsxLoader:
    def __init__(self, xlsxFile = None, xlsxBytesArray = None, convert_urls=False):
        self.convert_urls = convert_urls
        self.xlsxFile = xlsxFile
        self.xlsxBytesArray = xlsxBytesArray
        if xlsxFile is None and xlsxBytesArray is None:
            raise ValueError ("Either provide a path to XLSX file as xlsxFile or xlsxBytesArray as xlsxBytesArray")

    def __rshift__(self, other):
        if isinstance(other, Dialog):
            xlsx = None
            if self.xlsxBytesArray is not None:
                xlsx = self.xlsxBytesArray
            elif self.xlsxFile is not None:
                xlsx = self.xlsxFile
            prompts = self.convert(xlsx)
            message = Message(unified_prompts=prompts, role ="user", sender_info="ComradeAI user", send_datetime=str(datetime.now()))
            other.messages.append(message)
            return other
        else:
            raise TypeError("XlsxLoader can be only applied to a Dialog object")
        
    def convert(self, xlsx_input):
        if isinstance(xlsx_input, str):
            workbook = openpyxl.load_workbook(xlsx_input, data_only=True)
        elif isinstance(xlsx_input, io.BytesIO):
            workbook = openpyxl.load_workbook(filename=xlsx_input, data_only=True)
        else:
            raise ValueError("Input must be a file path or a BytesIO object")

        prompts = []

        for sheet in workbook.sheetnames:
            sheet_element = ET.Element("Sheet", name=sheet)
            worksheet = workbook[sheet]

            merged_cells_ranges = worksheet.merged_cells.ranges

            for row in worksheet.iter_rows():
                row_element = ET.SubElement(sheet_element, "Row")
                for cell in row:
                    # Check if cell is part of a merged cell and get the value
                    merged_cell_value = self.get_merged_cell_value(cell, merged_cells_ranges)
                    if merged_cell_value is not None:
                        cell_value = merged_cell_value
                    else:
                        cell_value = str(cell.value) if cell.value is not None else ''

                    if isinstance(cell, openpyxl.cell.cell.MergedCell):  # Check if it's a MergedCell
                        continue  # Skip processing for non-top-left cells in merged regions

                    cell_element = ET.SubElement(row_element, "Cell", column=cell.column_letter)
                    cell_element.text = cell_value

            xml_str = ET.tostring(sheet_element, encoding='utf-8').decode('utf-8')
            parsed_xml = minidom.parseString(xml_str)
            pretty_xml_str = parsed_xml.toprettyxml(indent="  ")

            prompts.append(UnifiedPrompt("text", pretty_xml_str, "text/plain"))
        return prompts

    def get_merged_cell_value(self, cell, merged_ranges):
        for merged_range in merged_ranges:
            if cell.coordinate in merged_range:
                top_left_cell = merged_range.start_cell
                return str(top_left_cell.value) if top_left_cell.value is not None else ''
        return None

    def print_prompts(self, prompts):
        for prompt in prompts:
            if prompt.content_type == "image":
                print("image")
            else:
                print(f"{prompt.content_type}: {prompt.content}")

class XlsxSplitter:
    def __init__ (self, splitMethod='row', lastMessageCount = 1, acceptedRoles=[]):
        self.splitMethod = splitMethod
        self.lastMessageCount = lastMessageCount
        self.acceptedRoles = acceptedRoles

    def split_xml_content(self, xml_string, splitMethod):
        root = ET.fromstring(xml_string)
        result = []
        for row in root.findall('.//Row'):
            if splitMethod == 'row':
                # For 'row' split method, concatenate Cell texts with a tab separator
                row_texts = [cell.text or '' for cell in row.findall('.//Cell')]
                result.append('\t'.join(row_texts))
            elif splitMethod == 'cell':
                # For 'cell' split method, add each Cell's text to the result list
                for cell in row.findall('.//Cell'):
                    result.append(cell.text or '')
        return result
        
    def __rrshift__(self, other):
        if isinstance(other, Dialog):
            i = 0
            result = []
            for msg in reversed(other.messages):
                if i >= self.lastMessageCount:
                    break
                if self.acceptedRoles == [] or msg.role in self.acceptedRoles:
                    for prompt in msg.unified_prompts:
                        if prompt.content_type == "text":
                            lines = self.split_xml_content(xml_string = prompt.content, splitMethod = self.splitMethod)
                            for line in lines:
                                if len(line)>0 and len(re.sub(r"[ \t]", "", line)) > 0:
                                    unified_prompt = UnifiedPrompt(content_type="text", content=line, mime_type="text/plain")
                                    message = Message(unified_prompts=[unified_prompt], role = msg.role, sender_info=msg.sender_info, send_datetime=msg.send_datetime, diagnosticData=msg.diagnosticData, agentConfig=msg.agentConfig, billingData=msg.billingData, routingStrategy=msg.routingStrategy)
                                    result.append(Dialog(messages=[message]))
                i += 1
            return result
        else:
            raise TypeError("XML splitter is only aplicable to Dialog objects")