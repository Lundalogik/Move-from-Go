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


def create_csv_headers(main_node):
    csv_headers = set()
    #print(main_node)
    for node in main_node:
        for key, value in node.items():
            if key == 'CustomValues':
                csv_headers.add(key)
            elif key == 'Employees':
                pass
            elif isinstance(value, str):
                csv_headers.add(key)
            elif isinstance(value, OrderedDict):
                for sub_key, sub_value in value.items():
                    csv_headers.add(key + csv_header_sub_key_separator + sub_key)
    return sorted(list(csv_headers))


def parse_object_to_csv_row(headers, node):
    row = []
    for key in headers:
        # Key has subkeys
        if csv_header_sub_key_separator in key:
            if node.get(key.split(csv_header_sub_key_separator)[0], None):
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

def create_and_fill_csv_file(name, node):
     with codecs.open(name+'.csv', 'w', 'utf-8') as f:
        writer = csv.writer(f)
        csv_headers_sorted = create_csv_headers(node)
        writer.writerow(csv_headers_sorted)
        for org in node:
            row = parse_object_to_csv_row(csv_headers_sorted, org)
            writer.writerow(row)


def create_import_files_from_xml():
    with codecs.open('./ExportApplicationData.xml', 'r', 'utf-8') as go_xml:
        go_data = xmltodict.parse(go_xml.read(), encoding='utf-8')

    create_and_fill_csv_file('organizations', go_data['GoImport']['Organizations']['Organization'])
    create_and_fill_csv_file('deals', go_data['GoImport']['Deals']['Deal'])
    create_and_fill_csv_file('histories', go_data['GoImport']['Histories']['History'])
    create_and_fill_csv_file('coworkers', go_data['GoImport']['Coworkers']['Coworker'])

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
    create_and_fill_csv_file('employees', employees)

create_import_files_from_xml()
#create_mapping_file('company', 'person')
#map_import()
