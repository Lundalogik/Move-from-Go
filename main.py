import csv
from collections import OrderedDict
import codecs

import xmltodict
from limeclient import ImportFiles, LimeClient, LimeTypes, ImportConfigs, SimpleFieldMapping

import yaml


csv_header_sub_key_separator = '.'
server = ''
database = ''
user = ''
password = ''

def create_mapping_file(*types):
    mappings = {}
    for l_type in types:
        mappings[l_type] = {}
    CLIENT = LimeClient(server, database, verify_ssl_cert=False)
    with CLIENT.login(user, password) as c:
        for l_type in types:
            for t in LimeTypes(c).get_by_name(l_type).fields:
                mappings[l_type][t] = ''
    with open('mapping.yml', 'w') as yaml_file:
        yaml.dump(mappings, yaml_file, default_flow_style=False, default_style='')

def map_import():
    CLIENT = LimeClient(server, database, verify_ssl_cert=False)
    with CLIENT.login(user, password) as c:

        with open('organizations.csv') as content:
            f = ImportFiles(c).create(filename='organizations.csv',
                                      content=content)
            f.save()
        with open("mapping.yml", 'r') as ymlfile:
            mappings = yaml.load(ymlfile)

        for section in mappings:
            l_type = LimeTypes(c).get_by_name(section)
            config = ImportConfigs(c).create(lime_type=l_type, importfile=f)

            for key, mapping in mappings:
                if mapping:
                    field_mapping = SimpleFieldMapping(field=l_type.fields[key],
                                                       column=mapping,
                                                       key=False)
                    config.add_mapping(field_mapping)


def create_csv_headers(main_node, custom_fields):
    csv_headers = set()
    #print(main_node)
    for node in main_node:
        for key, value in node.items():
            if key == 'CustomValues':
                if value:
                    # There can be several CustomValues on a object. Due to XML conversion it is not always a list
                    if isinstance(value['CustomValue'], list):
                        custom_values = []
                        custom_values.extend(value['CustomValue'])
                    else:
                        custom_values = [value['CustomValue']]
                    for custom_value in custom_values:
                        field_id = custom_value['Field']['Id']
                        custom_field_name = [custom_field['Title'] for custom_field in custom_fields['CustomField'] if custom_field['Id'] == field_id][0]
                        csv_headers.add(key + csv_header_sub_key_separator + custom_field_name)
            elif key == 'Employees':
                pass
            elif isinstance(value, str):
                csv_headers.add(key)
            elif isinstance(value, OrderedDict):
                for sub_key, sub_value in value.items():
                    csv_headers.add(key + csv_header_sub_key_separator + sub_key)
    return sorted(list(csv_headers))

class RowFilter:
    def __init__(self, key, value):
        self.key = key
        self.value = value

def parse_object_to_csv_row(headers, node, custom_fields, row_filters):
    row = []

    for key in headers:
        if row_filters:
            for row_filter in row_filters:
                if row_filter.key == key:
                    if node.get(key) == row_filter.value:
                        return None
        # Key has subkeys
        if csv_header_sub_key_separator in key:
            
            # Handle custom values
            if key.split(csv_header_sub_key_separator)[0] == "CustomValues" and node.get('CustomValues'):
                # Might be list or not, make sure it always is.
                if isinstance(node.get('CustomValues').get('CustomValue'), list):
                    custom_values = []
                    custom_values.extend(node.get('CustomValues').get('CustomValue'))
                else:
                    custom_values = [node.get('CustomValues').get('CustomValue')]
                # Make a look up for the ID of the CustomField based on the Name of the Field.
                # Can then be used to extract the value of the correct CustomValue
                custom_field_name = key.split(csv_header_sub_key_separator)[1]
                custom_field_id = [custom_field['Id']
                                   for custom_field in custom_fields['CustomField']
                                   if custom_field['Title'] == custom_field_name][0]

                temp_value = [custom_value['Value']
                              for custom_value in custom_values
                              if custom_value['Field']['Id'] == custom_field_id]
                if temp_value:
                    value = temp_value[0]
                else:
                    value = None

            elif node.get(key.split(csv_header_sub_key_separator)[0], None):
                temp_value = node.get(
                    key.split(csv_header_sub_key_separator)[0]
                ).get(
                    key.split(csv_header_sub_key_separator)[1], None
                )
                if key == "Tags.Tag" and isinstance(temp_value, list):
                    value = ";".join(temp_value)
                elif key == "Source.Id":
                    if len(temp_value.split(":")) > 1:
                        value = temp_value.split(":")[1]
                    else:
                        value = temp_value
                elif key == "Status.StatusReference":
                    value = temp_value['Label']
                else:
                    value = temp_value
            else:
                value = None
        else:
            if key == "CustomValues":
                custom_values = []
                if node.get(key):
                    for _, fields in node.get(key).items():
                        if isinstance(fields, OrderedDict):
                            fields.get['Id']
                            custom_values.append(fields.get('Value'))
                        else:
                            for field in fields:
                                if isinstance(field, OrderedDict):
                                    custom_values.append(field.get('Value'))
                value = ','.join(custom_values)
            else:
                value = node.get(key)
        row.append(value)
    return row

def create_and_fill_csv_file(name, node, custom_fields=None, row_filters=None):
    with codecs.open('./data/' + name +'.csv', 'w', 'utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        csv_headers_sorted = create_csv_headers(node, custom_fields)
        writer.writerow(csv_headers_sorted)
        for org in node:
            row = parse_object_to_csv_row(csv_headers_sorted, org, custom_fields, row_filters)
            if row:
                writer.writerow(row)


def create_import_files_from_xml():
    with codecs.open('./data/ExportApplicationData.xml', 'r', 'utf-8') as go_xml:
        go_data = xmltodict.parse(go_xml.read(), encoding='utf-8')

    create_and_fill_csv_file(
        'organizations',
        go_data['GoImport']['Organizations']['Organization'],
        custom_fields=go_data['GoImport']['Settings']['Organization']['CustomFields']
    )
    create_and_fill_csv_file(
        'deals',
        go_data['GoImport']['Deals']['Deal'],
        custom_fields=go_data['GoImport']['Settings']['Deal']['CustomFields']
    )
    create_and_fill_csv_file(
        'histories',
        go_data['GoImport']['Histories']['History'],
        row_filters=[
            RowFilter('Classification', 'TargetStatus'),
            RowFilter('Classification', 'DealStatus')]
    )
    create_and_fill_csv_file(
        'deal_statuses',
        go_data['GoImport']['Histories']['History'],
        custom_fields=go_data['GoImport']['Settings']['Deal']['CustomFields'],
        row_filters=[
            RowFilter('Classification', 'TargetStatus'),
            RowFilter('Classification', 'TriedToReach'),
            RowFilter('Classification', 'SalesCall'),
            RowFilter('Classification', 'ClientVisit'),
            RowFilter('Classification', 'Comment'),
            RowFilter('Classification', 'TalkedTo')
        ]
    )
    create_and_fill_csv_file(
        'target_statuses',
        go_data['GoImport']['Histories']['History'],
        row_filters=[
            RowFilter('Classification', 'DealStatus'),
            RowFilter('Classification', 'TriedToReach'),
            RowFilter('Classification', 'SalesCall'),
            RowFilter('Classification', 'ClientVisit'),
            RowFilter('Classification', 'Comment'),
            RowFilter('Classification', 'TalkedTo')
        ]
    )
    create_and_fill_csv_file(
        'coworkers',
        go_data['GoImport']['Coworkers']['Coworker'],
    )
    create_and_fill_csv_file(
        'files',
        go_data['GoImport']['Documents']['Files']['File'],
    )
    create_and_fill_csv_file(
        'links',
        go_data['GoImport']['Documents']['Links']['Link'],
    )

    employees = []
    for org in go_data['GoImport']['Organizations']['Organization']:
        emp = org.get('Employees')
        if emp:
            persons = emp.get('Person')
            if isinstance(persons, list):
                for p in persons:
                    p.update({'Organization.Id': org.get('Id')})
                    p.update({'Organization.Name': org.get('Name')})
                    employees.append(p)
            else:
                persons.update({'Organization.Id': org.get('Id')})
                persons.update({'Organization.Name': org.get('Name')})
                employees.append(persons)
    create_and_fill_csv_file(
        'employees', 
        employees,
        custom_fields=go_data['GoImport']['Settings']['Person']['CustomFields']
    )

create_import_files_from_xml()
#create_mapping_file('company', 'person')
#map_import()
