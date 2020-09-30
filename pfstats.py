#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Postfix mail log parser and filter.

This script filters and parses Postfix logs based on provided filter parameters.

Example:
    To use this script type 'python pfstats.py -h'. Below is an example
    that filteres postfix log file (even gziped) based on date, 
    sender of the email and email status::

        $ python pfstats.py -d 'Jul 26' -t 'bounced' -s 'info@altinukshini.com'

Todo:
    * Filter and parse logs from a year ago
    * Add receiver filter
    * Maybe provide from-to date filtering option

"""
__author__ = "Altin Ukshini"
__copyright__ = "Copyright (c) 2017, Altin Ukshini"

__license__ = "MIT License"
__version__ = "1.0"
__maintainer__ = "Altin Ukshini"
__email__ = "altin.ukshini@gmail.com"
__status__ = "Production"


import re
import os
import sys
import gzip
import time
import argparse
import datetime
from random import randint
from argparse import RawTextHelpFormatter
from collections import defaultdict


########################################################
# Config
########################################################

default_log_file = r'/var/log/postfix/mail.log'
default_log_dir = r'/var/log/postfix/'  # Must end with slash '/'

########################################################
# Predefined variables
########################################################

sender_lines = []
status_lines = []
status_lines_by_type = {'bounced' : [], 'deferred' : [], 'sent' : [], 'rejected' : []}
status_types = ['bounced', 'deferred', 'sent', 'rejected']
file_random_no = randint(100000, 999990)
generated_results = defaultdict(dict)

working_dir = os.getcwd() + '/'

start_time = time.time()

### All this formatting bcs of postfix date format :)
date = datetime.datetime.now()
date_today_year = date.strftime("%Y")
date_today_month = date.strftime("%b")
date_today_day = date.strftime("%d").lstrip('0')
date_today = date_today_month + " " + date_today_day
if int(date_today_day) < 10:
    date_today = date_today_month + "  " + date_today_day


########################################################
# Functions
########################################################


def get_receiver(line):
    """Return a string

    Filter line and get the email receiver to=<>.
    """

    receiver = re.search('(?<=to=<).*?(?=>)', line)

    return receiver.group()


def get_sender(line):
    """Return a string

    Filter line and get the email sender from=<>.
    """

    sender = re.search('(?<=from=<).*?(?=>)', line)

    return sender.group()


def get_email_subject(line):
    """Return a string

    Filter line and get the email subject Subject:.
    """

    subject = re.search('(?<=Subject: ).*?(?=\sfrom)', line)

    return subject.group()


def get_email_status(line):
    """Return a string

    Filter line and get the email status (sent, bounced, deferred, rejected).
    """

    status = re.search('(?<=status=).*?(?=\s)', line)

    return status.group()


def get_host_message(line, status):
    """Return a string

    Filter line and get the host message located after status.
    """

    message = re.search('status=' + status + ' (.*)', line)

    return message.group(1)


def get_message_id(line):
    """Return a string

    Filter line and get the email/message id.
    """

    return line.split()[5].replace(":","")


def get_line_date(line):
    """Return a string

    Filter line and get the email date (beginning of the line).
    """

    return line.split()[0] + " "  + str(line.split()[1])


def check_sender_line(line):
    """Return a boolean

    Check if line contains specific words to validate if that's the line
    we want.
    """

    return 'cleanup' in line and 'from=' in line and 'Subject' in line


def filter_line_sender_subject(line):
    """Return void

    Filter line based on sender and subject message and 
    append it to predefined dicts.
    """

    global args, sender_lines

    if args.sender is not None and args.message is not None:
        if args.sender in line and args.message in line:
            sender_lines.append(line)
    elif args.sender is not None and args.message is None:
        if args.sender in line:
            sender_lines.append(line)
    elif args.message is not None and args.sender is None:
        if args.message in line:
            sender_lines.append(line)
    else:
        sender_lines.append(line)


def filter_line(line):
    """Return void

    Filter line based on check_sender_line() and  email status type and append to
    corresponding predefined dicts
    """

    global sender_lines, status_lines, status_lines_by_type, status_types

    if check_sender_line(line):
        filter_line_sender_subject(line)
    elif args.type in status_types:
        if str('status='+args.type) in line and 'to=' in line and 'dsn=' in line:
            status_lines.append(line)
    else:
        if 'status=' in line and 'to=' in line and 'dsn=' in line :
            line_email_status = get_email_status(line)
            if line_email_status in status_types:
                status_lines_by_type[line_email_status].append(line)


def check_if_gz(file_name):
    """Return a boolean

    Check if filename ends with gz extension
    """

    return file_name.endswith('.gz')


def filter_log_file(log_file):
    """Return a string

    Open file and start filtering line by line.
    Apply date filtering as well.
    """

    global date_today, date_filter

    if check_if_gz(log_file):
        with gzip.open(log_file, 'rt') as log_file:
            for line in log_file:
                print(line)
                if date_filter in line:
                    filter_line(line)
    else:
        with open(log_file,'r') as log_file:
            for line in log_file:
                if date_filter in line:
                    filter_line(line)
  
    log_file.close()


def process_line(sender_line, status_lines, status_type, file):
    """Return void

    For each sender, check corresponding message status by message id, extract the required 
    parameters from lines and write them to generated file.
    """

    global args, generated_results

    message_id = get_message_id(sender_line)
    sender = get_sender(sender_line)
    subject = get_email_subject(sender_line)

    for status_line in status_lines:

        if message_id in status_line:
            receiver = get_receiver(status_line)
            host_message = get_host_message(status_line, status_type)
            line_date = get_line_date(status_line)

            generated_results[status_type] += 1

            file.write(
                line_date + args.output_delimiter + 
                sender + args.output_delimiter + 
                receiver + args.output_delimiter + 
                message_id + args.output_delimiter + 
                subject + args.output_delimiter + 
                host_message + "\n")


def write_file_header(file):
    """Return void

    Writes file header that represent columns.
    """

    global args

    file.write(
        "date" + args.output_delimiter + 
        "sender" + args.output_delimiter + 
        "receiver" + args.output_delimiter + 
        "message_id" + args.output_delimiter + 
        "subject" + args.output_delimiter + 
        "host_message\n")


def date_filter_formated(date_filter):
    """Return datetime

    Returns the date provided to a specific format '%Y %b %d'.
    """

    return datetime.datetime.strptime(datetime.datetime.now().strftime('%Y ') + date_filter, '%Y %b %d')


def date_filter_int(date_filter):
    """Return int

    Returns the datetime provided to a specific format '%Y%b%d' as integer.
    """

    return int(date_filter_formated(date_filter).strftime('%Y%m%d'))


def get_files_in_log_dir(default_log_dir):
    """Return list

    Returns a list of files from provided directory path.
    """

    all_log_files = [f for f in os.listdir(default_log_dir) if os.path.isfile(os.path.join(default_log_dir, f))]

    if not all_log_files:
        sys.exit("Default log directory has no files in it!")

    return all_log_files


def generate_files_to_check(date_filter):
    """Return list

    Based on the date filter provided as argument (or today's date), generate the supposed filenames (with specific date and format)
    to check in log directory. This will return two filenames.
    """

    today_plusone = datetime.datetime.now() + datetime.timedelta(days = 1)
    today_minusone = datetime.datetime.now() - datetime.timedelta(days = 1)

    date_filter_plusone = date_filter_formated(date_filter) + datetime.timedelta(days = 1)

    if (date_filter_int(date_filter) < int(datetime.datetime.now().strftime('%Y%m%d')) and 
        date_filter_int(date_filter) == int(today_minusone.strftime('%Y%m%d'))):
        
        return [
            'mail.log-' + datetime.datetime.now().strftime('%Y%m%d'), 
            'mail.log-' + date_filter_formated(date_filter).strftime('%Y%m%d') + '.gz'
        ]
    
    elif (date_filter_int(date_filter) < int(datetime.datetime.now().strftime('%Y%m%d')) and 
          date_filter_int(date_filter) < int(today_minusone.strftime('%Y%m%d'))):

        return [
            'mail.log-' + date_filter_formated(date_filter).strftime('%Y%m%d') + '.gz', 
            'mail.log-' + date_filter_plusone.strftime('%Y%m%d') + '.gz'
        ]

    return []


def populate_temp_log_file(file_name, temp_log_file):
    """Return void

    Populates the combined temporary log file from provided log in log directory.
    """

    if check_if_gz(file_name):
        with gzip.open(file_name, 'rt') as gz_mail_log:
            for line in gz_mail_log:
                temp_log_file.write(line)
        gz_mail_log.close()
    else:
        with open(file_name, 'r') as mail_log:
            for line in mail_log:
                temp_log_file.write(line)
        mail_log.close()


def generate_working_log(date_filter):
    """Return void

    Generates combined working log from different logs from postfix log directory based on date filter.
    """

    global args, log_file, working_dir

    log_dir_files = get_files_in_log_dir(args.log_dir)
    selected_files = generate_files_to_check(date_filter)

    temp_log_file = open(working_dir + 'temp-' + str(date_filter_formated(date_filter).strftime('%Y%m%d')) + '.log', 'w')

    for selected_file in selected_files:
        if selected_file in log_dir_files:
            populate_temp_log_file(args.log_dir + selected_file, temp_log_file)
        else:
            print("File not found: " + selected_file)
    temp_log_file.close()

    log_file = working_dir + 'temp-' + str(date_filter_formated(date_filter).strftime('%Y%m%d')) + '.log'


def print_results(results):
    """Return void

    Prints the end results of the file processing
    """

    global args, file_random_no

    print("\n************************* RESULTS *************************\n")
    if results:
        total = 0
        for result in results:
            total += results[result]
            if result == 'sent':
                print(result + ":   \t" + str(results[result]) \
                    + "\t\t" + result + "-" + str(file_random_no) \
                    + "." + args.output_filetype)
            else:
                print(result + ":\t" + str(results[result]) + "\t\t" \
                    + result + "-" + str(file_random_no) \
                    + "." + args.output_filetype)

        print("\n-----\nTotal:\t\t" + str(total))
    else:
        print('Results could not be printed')
    print("\n***********************************************************")


if __name__ == "__main__":

    ########################################################
    # Argument(s) Parser
    ########################################################

    parser = argparse.ArgumentParser(description='Filter and parse Postfix log files.', formatter_class=RawTextHelpFormatter)

    parser.add_argument('-d', '--date', 
                            dest='date', 
                            default=date_today, 
                            metavar='', 
                            help='''Specify different date. Default is current date.\nFormat: Jan 20 (note one space) & 
Jan  2 (note two spaces).\nDefault is todays date: ''' + date_today + '\n\n')

    parser.add_argument('-t', '--type',
                            dest='type',
                            default='all',
                            metavar='',
                            help='Type of email status: bounced, sent, rejected, deferred.\nDefault is all.\n\n')

    parser.add_argument('-s', '--sender',
                            dest='sender',
                            metavar='',
                            help='Specify senders address in order to query logs matching this parameter\n\n')

    parser.add_argument('-m', '--message',
                            dest='message',
                            metavar='',
                            help='''Postfix default log format must be changed for this option to work.
Add subject message in logs, and then you can use this option to query\nthose emails with specific subject message.\n\n''')

    parser.add_argument('-l', '--log',
                            dest='log',
                            default=default_log_file, 
                            metavar='',
                            help='Specify the log file you want to use.\nDefault is: ' + default_log_file + '\n\n')

    parser.add_argument('--log-dir',
                            dest='log_dir',
                            default=default_log_dir,
                            metavar='',
                            help='Specify the log directory.\nDefault is: ' + default_log_dir + '\n\n')

    parser.add_argument('--output-directory',
                            dest='output_directory',
                            default=working_dir, 
                            metavar='',
                            help='Specify the generated file(s) directory.\nDefault is current working directory: ' + working_dir + '\n\n')

    parser.add_argument('--output-delimiter',
                            dest='output_delimiter',
                            default=';', 
                            metavar='',
                            help='Specify the generated output delimiter.\nDefault is ";"\n\n')

    parser.add_argument('--output-filetype',
                            dest='output_filetype',
                            default='csv',
                            metavar='',
                            help='Specify the generated output file type.\nDefault is "csv"\n\n')

    args = parser.parse_args()


    ## Validate arguments

    log_file = default_log_file
    date_filter = date_today


    # Check if provided parameters are valid

    if os.path.isfile(args.log) is not True:
        parser.error('Provided log file does not exist: ' + args.log)

    if args.output_directory != working_dir and args.output_directory.endswith('/') is not True:
        parser.error('Generated output file(s) directory must end with slash "/"')

    if args.log_dir != default_log_dir and args.log_dir.endswith('/') is not True:
        parser.error('Log directory must end with slash "/"')

    if os.path.exists(args.output_directory) is not True:
        parser.error('Generated output file(s) directory does not exist: ' + args.output_directory)

    if os.path.exists(args.log_dir) is not True:
        parser.error('This log directory does not exist in this system: ' + args.log_dir + '\nMaybe provide a different log dir with --log-dir')

    # If date provided, change date filter to the provided one
    if args.date != date_filter:
        date_filter = args.date

    # If log provided, change default log file to provided one
    if args.log != log_file:
        log_file = args.log


    ########################################################
    # Execution / Log parsing and filtering
    ########################################################


    # Check if provided date is valid
    if int(date_filter_formated(date_filter).strftime('%Y%m%d')) > int(datetime.datetime.now().strftime('%Y%m%d')):
        sys.exit("Provided date format is wrong or higher than today's date!")

    # In case the date filter is provided, and it is different from today,
    # it means that we will have to generate a temp log which contains
    # combined logs from default log dir (gzip logrotated files included)
    if date_filter != date_today and log_file == default_log_file:
        generate_working_log(date_filter)


    # Start filtering log file based on provided filters
    filter_log_file(log_file)


    # If there were no senders/filter matches, exit
    if not sender_lines:
        sys.exit("No matching lines found to be processed with provided filters in log file (" + log_file + "). Exiting...")


    # Start parsing
    # If message status type provided, filter only those messages
    if args.type in status_types:

        generated_results[args.type] = 0
        with open(args.output_directory + args.type + '-' \
            + str(file_random_no) + '.' \
            + args.output_filetype, 'w') as generated_file:

            write_file_header(generated_file)
            
            for sender_line in sender_lines:
                process_line(sender_line, status_lines, args.type, generated_file)

        generated_file.close()

    # Else, filter all status types (bounced, sent, rejected, deferred)
    else:

        for status_type in status_types:

            generated_results[status_type] = 0
            with open(args.output_directory + status_type + '-' \
                + str(file_random_no) + '.' \
                + args.output_filetype, 'w') as generated_file:
                
                write_file_header(generated_file)

                for sender_line in sender_lines:
                    process_line(sender_line, status_lines_by_type[status_type], \
                        status_type, generated_file)

            generated_file.close()


    # Generate and print results
    print_results(generated_results)
    print("--- %s seconds ---" % (time.time() - start_time))
