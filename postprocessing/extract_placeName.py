import os
import xml.etree.ElementTree as ET
import pandas as pd
import re
import argparse
 
def extract_placeName_from_file(xml_file):

    try:

        # Read the XML file as a string

        with open(xml_file, 'r', encoding='utf-8') as file:

            xml_content = file.read()

        # Parse the XML content

        tree = ET.ElementTree(ET.fromstring(xml_content))

        root = tree.getroot()
        
        # Extract the document date        
        date_element = root.find('.//{http://www.tei-c.org/ns/1.0}sourceDesc/{http://www.tei-c.org/ns/1.0}bibl/{http://www.tei-c.org/ns/1.0}date')
        document_date = date_element.get('when') if date_element is not None else None
 
 
        # Extract all placeName elements and their context

        place_data = []

        for placeName in root.findall('.//{http://www.tei-c.org/ns/1.0}placeName'):

            # Get the text content and the 'n' attribute of the placeName element

            name_text = placeName.text

            n_attr = placeName.get('n')
 
            # Find the position of the text in the 'n' attribute

            if n_attr:

                n_pos = xml_content.find(n_attr)

                if n_pos != -1:

                    # Extract context (30 characters before and 50 characters after the 'n' attribute)

                    context_start = max(0, n_pos - 50)

                    context_end = min(len(xml_content), n_pos + len(n_attr) + 70)

                    context = xml_content[context_start:context_end]
 
                    # Clean up the context for readability

                    context = re.sub(r'<.*?>', '', context)  # Remove XML tags
 
                    if name_text:

                        place_data.append((os.path.abspath(xml_file), name_text, document_date,n_attr, context))

            else:

                # If 'n' attribute is not present, extract context around the placeName element

                start_pos = xml_content.find(ET.tostring(placeName, encoding='unicode'))

                end_pos = start_pos + len(ET.tostring(placeName, encoding='unicode'))

                context_start = max(0, start_pos - 30)

                context_end = min(len(xml_content), end_pos + 50)

                context = xml_content[context_start:context_end]
 
                # Clean up the context for readability

                context = re.sub(r'<.*?>', '', context)  # Remove XML tags
 
                if name_text:

                    place_data.append((os.path.abspath(xml_file), name_text, document_date,None, context))

        return place_data

    except ET.ParseError:

        print(f"Failed to parse XML file: {xml_file}")

        return []

    except Exception as e:

        print(f"An error occurred while processing file {xml_file}: {e}")

        return []
 
def extract_placeName_from_folder(folder_path):

    all_place_data = []
 
    # Walk through all files and subfolders

    for subdir, _, files in os.walk(folder_path):

        print(f"Accessing directory: {subdir}")

        for filename in files:

            if filename.endswith(".xml"):

                file_path = os.path.join(subdir, filename)

                try:

                    print(f"Processing file: {file_path}")

                    place_data = extract_placeName_from_file(file_path)

                    all_place_data.extend(place_data)

                except PermissionError:

                    print(f"Permission denied: {file_path}")

                except Exception as e:

                    print(f"An error occurred while accessing {file_path}: {e}")
 
    # Create a DataFrame

    df = pd.DataFrame(all_place_data, columns=['FilePath', 'placeName', 'documentDate','n', 'Context'])

    return df

def main(input_folder, output_csv):     
    df = extract_placeName_from_folder(input_folder)    
    df.to_csv(output_csv, index=False)     
    print(f"Data has been saved to {output_csv}") 
    
if __name__ == "__main__":     
    parser = argparse.ArgumentParser(description="Extract placeName elements from TEI-XML files.")     
    parser.add_argument("input_folder", type=str, help="Path to the folder containing TEI-XML files.")     
    parser.add_argument("output_csv", type=str, help="Path to the output CSV file.") 
    args = parser.parse_args() 
    main(args.input_folder, args.output_csv)