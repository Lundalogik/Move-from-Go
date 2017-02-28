# Move from Go
This is a simple script that converts a exported Lime Go xml-file into flat comma separated csv files.

The ambition is to be able to directly hook these to the Lime CRM textfile import, but this is not done yet

Objects such as "Coworker" is flatten into Coworker.id, Coworker.name ...

## How it works

1. Download the data from Lime Go-admin. Requires an Lime Go Admin account, only available to Lundalogik
2. Put it into the project folder
2. Run `main.py`
3. Use the manual textfile import in Lime CRM

## Tags

Tags are put into a column and separated by semicolon

## Known problems
- Custom fields are not working
- History is mixed of real history and deal and calling list status changes

## Future features
- Directly use the Lime CRM import API
- A basic mapping file
- A cooler mapping file with simple transforms and base values
- A CLI-interface, similair to the one in Move-to-go
- Tests...