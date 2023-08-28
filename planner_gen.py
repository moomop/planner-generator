#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import pathlib
import subprocess


# Function to create an A4 svg that includes to two 135 by 200 mm (slightly smaller than A5)
# pages as svg images:
def write_a4_svg(left_a5, right_a5, a4_filename):
    with open(a4_filename,'w') as output_svg:
        output_svg.write('<svg version="1.1" width="297mm" height="210mm" xmlns="http://www.w3.org/2000/svg">\n')
        if left_a5 is not None:
          output_svg.write(f'<image x="5.5mm"   y="5mm" width="135mm" height="200mm" href="../../{left_a5}"/>\n')
        if right_a5 is not None:
           output_svg.write(f'<image x="156.5mm" y="5mm" width="135mm" height="200mm" href="../../{right_a5}"/>\n')
        # Add two short lines to mark the centerline to aid cutting
        output_svg.write('<line x1="50%" x2="50%" y1="90%" y2="91%" stroke="black" stroke-width="0.5"/>\n')
        output_svg.write('<line x1="50%" x2="50%" y1="9%" y2="10%" stroke="black" stroke-width="0.5"/>\n')
        output_svg.write('</svg>\n')

class TemplatePageManager:
    '''Class to help with creating pages by find/replace in template svgs.
       Takes care of creating the sub dirs which are used for storing the
       various intermediate files.
    '''

    def __init__(self) -> None:
        # Dictionary to store all the strings to replace
        # Keys are the strings in the svg
        # Values are the replacement strings 
        self.replacements = {}

        # List to contain the file names of the A5 svg pages
        self.a5_pages = []

    def create_dirs(self,year):
        # create all the subdirs
        self.year = year
        self.year_dir = f'planner_files_{year}'
        pathlib.Path(self.year_dir).mkdir(exist_ok=True)
        self.a5_pages_dir = os.path.join(self.year_dir,'a5_pages')
        pathlib.Path(self.a5_pages_dir).mkdir(exist_ok=True)
        self.a4_svgs_dir = os.path.join(self.year_dir,'a4_svgs')
        pathlib.Path(self.a4_svgs_dir).mkdir(exist_ok=True)
        self.a4_pdfs_dir = os.path.join(self.year_dir,'a4_pdfs')
        pathlib.Path(self.a4_pdfs_dir).mkdir(exist_ok=True)

    def next_page_number(self):
        return len(self.a5_pages) + 1
    
    def add_blank_page(self):
        self.a5_pages.append(None)

    def add_page_from_template(self, template_name, output_name):
        template = os.path.join('a5_templates', template_name)
        with open(template) as template_file:
            template_string = template_file.read()
        for pattern, replacement in self.replacements.items():
            template_string = template_string.replace(pattern, replacement)
        # Prepend the page number to the name of the output file 
        output_filename = f'{self.next_page_number():03d}_{output_name}'
        output_filename = os.path.join(self.a5_pages_dir,output_filename)
        with open(output_filename,'w') as output_svg:
           output_svg.write(template_string)
        self.a5_pages.append(output_filename)


parser = argparse.ArgumentParser(description='Generate a year of planner')
parser.add_argument('--year', required=True, type=int, help="The year to generate e.g. 2023")
parser.add_argument('--reorder', action='store_true', help="Rearrange A5s for printing on non-duplex printer")
parser.add_argument('--verbose', action='store_true', help="Enable logging of debug messages")

args = parser.parse_args()
year = args.year

if args.verbose:
  log_level = 'DEBUG'
else:
  log_level = 'INFO'
logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

template_page_manager = TemplatePageManager()

# Create directories for outputs
template_page_manager.create_dirs(year)

# Find the number of weeks in the year
# 28th Dec is always in last week of year
# isocalendar returns a 
n_weeks_in_year = datetime.date(year,12,28).isocalendar().week #28th Dec is always in last week of year


# Start with a blank page if not reordering. (Month summary pages are always on right
# hand side, with either a blank page on left if not reordering or nothing on the left
# otherwise)
if not args.reorder:
    template_page_manager.add_blank_page()


logging.info(f"Creating A5 SVGs")
for week in range(1, n_weeks_in_year + 1):

    # We count the week as in the month which in the middle day falls.
    middle_day_of_week = datetime.date.fromisocalendar(year,week,4)
    month = middle_day_of_week.month
    middle_day_of_previous_week = middle_day_of_week - datetime.timedelta(days=7)

    if middle_day_of_week.month != middle_day_of_previous_week.month:
        # New month: set up replacements for calendar grid and other items that only change
        # on a per month basis. Then generate month summary page.

        
        # %B format below gives month name e.g. "August"
        month_string = middle_day_of_week.strftime("%B").upper()
        logging.debug(f"generate month start page for {month_string}")

        # Replace MONTH placeholder in svg with uppercase month e.g. "AUGUST" 
        template_page_manager.replacements['{MONTH}'] = month_string.upper()

        # Setup replacements for calendar grid. SVG templates contain grids like
        #  M    T    W    T    F    S    S
        # {1}  {2}  {3}  {4}  {5}  {6}  {7}
        # ...
        # {36} {37} {38} {39} {40} {41} {42}
        #
        # These replacements are used to replace the days of the month (or empty string
        # if the day is outside the current month)

        # We will want to know the number of weeks in the month. Use this set to keep
        # track of them.
        weeks_in_month = set()

        # Iterate over the 42 days starting from first day in the grid
        first_day_of_month = datetime.date(year,month,1)
        first_day_of_grid = first_day_of_month - datetime.timedelta(days=first_day_of_month.isocalendar().weekday - 1)

        for day in range(0,42):
            date = first_day_of_grid + datetime.timedelta(days=day)
            if date.month != month:
                # replace dates that are outside current month with empty string
                template_page_manager.replacements['{'+ str(day+1) + '}'] = ''   
            else:
                template_page_manager.replacements['{'+ str(day+1) + '}'] = str(date.day)
                weeks_in_month.add(date.isocalendar().week)
      
        n_weeks_in_month = len(weeks_in_month)

        if month != 1:
          # apart frome the first month, insert a blank page for the left hand side of the
          # month spread
          template_page_manager.add_blank_page() 

        # Depending on the number of weeks in the month and hence the number of rows
        # in the calendar, one of three slightly different svg templates is used     
        template_page_manager.add_page_from_template(template_name=f'month_summary_{n_weeks_in_month}wk.svg',
                                                     output_name=f'{month_string}_start_page.svg')

    # Create week page with calender and pad
    logging.debug(f"Generating week pad page for week {week}")

    # Add replacement for WEEK_DESCRIPTION_TEXT with e.g. "2023 WEEK 5"
    week_description_text = f"{year} WEEK {week}"
    template_page_manager.replacements['{WEEK_DESCRIPTION_TEXT}'] = week_description_text

    template_page_manager.add_page_from_template(template_name=f'week_pad.svg',
                                                 output_name=f'week_pad_week{week}.svg')
    
    # Create week page with list of days
    logging.debug(f"Generating week day list page for week {week}")

    # Add replacement for MONTH_DAYS_TEXT with e.g. "JANUARY 9 - 15"
    day1 = datetime.date.fromisocalendar(year,week,1)
    days_of_week = []
    for day in range(7):
        days_of_week.append(day1 + datetime.timedelta(days=day))       

    if days_of_week[0].month == days_of_week[-1].month:
        #all days in same month
        month = days_of_week[0].strftime("%B").upper()
        month_days_text = f'{month} {days_of_week[0].day} - {days_of_week[-1].day}'
    else:
        #days span 2 months
        month_1 = days_of_week[0].strftime("%B").upper()
        month_2 = days_of_week[-1].strftime("%B").upper()
        month_days_text = f'{month_1} {days_of_week[0].day} - {month_2} {days_of_week[-1].day}'
    template_page_manager.replacements['{MONTH_DAYS_TEXT}'] = month_days_text

    # Add replacements for day of month for the week days list, e.g. if the Tuesday is 
    # the 23rd of the month, tue_dom will be replaced with "23"
    template_page_manager.replacements['{mon_dom}']  = str(days_of_week[0].day)
    template_page_manager.replacements['{tue_dom}']  = str(days_of_week[1].day)
    template_page_manager.replacements['{wed_dom}']  = str(days_of_week[2].day)
    template_page_manager.replacements['{thur_dom}'] = str(days_of_week[3].day)
    template_page_manager.replacements['{fri_dom}']  = str(days_of_week[4].day)
    template_page_manager.replacements['{sat_dom}']  = str(days_of_week[5].day)
    template_page_manager.replacements['{sun_dom}']  = str(days_of_week[6].day)

    template_page_manager.add_page_from_template(template_name=f'week_daylist.svg',
                                                 output_name=f'week_daylist_week{week}.svg')

a5_pages = template_page_manager.a5_pages
# Pad A5 page list with empty pages until it has a multiple of 4 pages    
while len(a5_pages)%4 != 0:
    a5_pages.append(None)

logging.info("Creating A4 SVGs")
# Pack the A5 pages into A4 pages
a4_num = 1
a4_svg_files = []
a4_pdf_files = []
while len(a5_pages) > 0:
    if args.reorder:
      # Reorder pages for printing 
      first_a4_right  = a5_pages.pop(0)
      second_a4_left  = a5_pages.pop(0)
      second_a4_right = a5_pages.pop(0)
      first_a4_left   = a5_pages.pop(0)
    else:
      # Leave pages in order
      first_a4_left   = a5_pages.pop(0)
      first_a4_right  = a5_pages.pop(0)
      second_a4_left  = a5_pages.pop(0)
      second_a4_right = a5_pages.pop(0) 
    a4_filename = (os.path.join(template_page_manager.a4_svgs_dir, f'{a4_num:03d}.svg'))
    a4_svg_files.append(a4_filename)
    write_a4_svg(left_a5=first_a4_left, right_a5=first_a4_right, a4_filename=a4_filename)
    a4_num += 1
    a4_filename = (os.path.join(template_page_manager.a4_svgs_dir, f'{a4_num:03d}.svg'))
    a4_svg_files.append(a4_filename)
    write_a4_svg(left_a5=second_a4_left, right_a5=second_a4_right, a4_filename=a4_filename)  
    a4_num += 1

# Convert the A4 svgs to A4 pdfs using cairosvg
logging.info("Converting A4 PDFs using cairosvg")
for a4_svg in a4_svg_files:
    a4_pdf = os.path.basename(a4_svg)[0:-3] + 'pdf'
    a4_pdf = os.path.join(template_page_manager.a4_pdfs_dir,a4_pdf)
    a4_pdf_files.append(a4_pdf)
    cmd = f'cairosvg -o {a4_pdf} {a4_svg}'
    logging.debug(f"Executing command: {cmd}")
    subprocess.run(cmd, shell=True)

# Combine all the A5 pdfs into a single pdf using ghostscript
logging.info("Merging PDFs using Ghostscript")
merged_pdf_file = os.path.join(template_page_manager.year_dir,f'merged_year_{year}.pdf')
cmd = f'gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -dAutoRotatePages=/None -sOutputFile={merged_pdf_file} {" ".join(a4_pdf_files)}'
logging.debug(f"Executing command: {cmd}")
subprocess.run(cmd, shell=True)
logging.info(f'Done - Merged pdf created at {merged_pdf_file}')
