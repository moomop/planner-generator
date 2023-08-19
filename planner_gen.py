#!/usr/bin/env python3
import argparse
import calendar
import datetime
import os
import pathlib
import subprocess

# Function to create an A4 svg that refers to two 
def write_a4_svg(left_a5, right_a5, a4_filename):
    with open(a4_filename,'w') as output_svg:
        output_svg.write('<svg version="1.1" width="297mm" height="210mm" xmlns="http://www.w3.org/2000/svg">\n')
        if left_a5 is not None:
          output_svg.write(f'<image x="5.5mm"   y="5mm" width="135mm" height="200mm" href="../../{left_a5}"/>\n')
        if right_a5 is not None:
           output_svg.write(f'<image x="156.5mm" y="5mm" width="135mm" height="200mm" href="../../{right_a5}"/>\n')
        output_svg.write('<line x1="50%" x2="50%" y1="90%" y2="91%" stroke="black" stroke-width="0.5"/>\n')
        output_svg.write('<line x1="50%" x2="50%" y1="9%" y2="10%" stroke="black" stroke-width="0.5"/>\n')
        output_svg.write('</svg>\n') 


parser = argparse.ArgumentParser(description='Generate a year of planner')
parser.add_argument('--year', required=True, type=int, help="The year to generate e.g. 2023")
parser.add_argument('--reorder', action='store_true', help="Rearrange A5s for printing on non-duplex printer")
args = parser.parse_args()

# Create directories for outputs
year = args.year
year_dir = 'planner_files_{}'.format(year)
pathlib.Path(year_dir).mkdir(exist_ok=True)
a5_pages_dir = os.path.join(year_dir,'a5_pages')
pathlib.Path(a5_pages_dir).mkdir(exist_ok=True)
a4_svgs_dir = os.path.join(year_dir,'a4_svgs')
pathlib.Path(a4_svgs_dir).mkdir(exist_ok=True)
a4_pdfs_dir = os.path.join(year_dir,'a4_pdfs')
pathlib.Path(a4_pdfs_dir).mkdir(exist_ok=True)


n_weeks = datetime.date(year,12,28).isocalendar()[1] #28th Dec is always in last week of year
prev_month = None
a5_pages = []

# Start with a blank page if not reordering. (Month summary pages are always on right
# hand side, with either a blank page on left if not reordering or nothing on the left
# otherwise)
if not args.reorder:
    a5_pages.insert(0,None)

replacements = {}
a5_page_num = 1
for week in range(1, n_weeks + 1):
    middle_day_of_week = datetime.date.fromisocalendar(year,week,4)
    month = middle_day_of_week.month
    month_string = middle_day_of_week.strftime("%B").upper()

    if month != prev_month:
        # New month: create month summary page
        if prev_month is not None:
          a5_pages.append(None)
        prev_month = month
        print(f"generate month start page for {month_string}")
        replacements['{MONTH}'] = month_string
        month_cal = calendar.monthcalendar(year, month)
        n_weeks_in_month = len(month_cal)
        month_cal_flat = [d for w in month_cal for d in w]
        while len(month_cal_flat) < 42:
            month_cal_flat.append(0)
        for i, v in enumerate(month_cal_flat,start=1):
            if v == 0:
                replacements['{'+ str(i) + '}'] = ''
            else:
                replacements['{'+ str(i) + '}'] = str(v)
        month_template = os.path.join('a5_templates', f'month_summary_{n_weeks_in_month}wk.svg')
        with open(month_template) as template_file:
            month_template_string = template_file.read()
        for pattern, replacement in replacements.items():
            month_template_string = month_template_string.replace(pattern, replacement)
        a5_filename = f'{a5_page_num:03d}_{month_string}_start_page.svg'
        
        a5_filename = os.path.join(a5_pages_dir,a5_filename)
        with open(a5_filename,'w') as output_svg:
            output_svg.write(month_template_string)
        
        a5_pages.append(a5_filename)
        a5_page_num += 1

    # Create week page with calender and pad
    print(f"Generating week pad page for week {week}")
    week_pad_template = os.path.join('a5_templates', f'week_pad.svg')
    with open(week_pad_template) as template_file:
        week_pad_template_string = template_file.read()
    week_description_text = "{} WEEK {}".format(year, week)
    replacements['{WEEK_DESCRIPTION_TEXT}'] = week_description_text
    for pattern, replacement in replacements.items():
        week_pad_template_string = week_pad_template_string.replace(pattern, replacement)
    a5_filename = f'{a5_page_num:03d}_week_pad_week{week}.svg'
    a5_filename = os.path.join(a5_pages_dir,a5_filename)
    with open(a5_filename,'w') as output_svg:
        output_svg.write(week_pad_template_string)
    a5_pages.append(a5_filename)
    a5_page_num += 1
    
    # Create week page with list of days
    print(f"Generating week day list page for week {week}")
    week_daylist_template = os.path.join('a5_templates', f'week_daylist.svg')
    with open(week_daylist_template) as template_file:
        week_daylist_template_string = template_file.read()
    
    day1 = datetime.date.fromisocalendar(year,week,1)
    days_of_week = []
    for day in range(7):
        days_of_week.append(day1 + datetime.timedelta(days=day))       

    if days_of_week[0].month == days_of_week[-1].month:
        #all days in same month
        month = days_of_week[0].strftime("%B").upper()
        month_days_text = '{} {} - {}'.format(month, days_of_week[0].day, days_of_week[-1].day)

    else:
        #days span 2 months
        month_1 = days_of_week[0].strftime("%B").upper()
        month_2 = days_of_week[-1].strftime("%B").upper()
        month_days_text = '{} {} - {} {}'.format(month_1, days_of_week[0].day, month_2, days_of_week[-1].day)
    replacements['{MONTH_DAYS_TEXT}'] = month_days_text
    replacements['{mon_dom}']  = str(days_of_week[0].day)
    replacements['{tue_dom}']  = str(days_of_week[1].day)
    replacements['{wed_dom}']  = str(days_of_week[2].day)
    replacements['{thur_dom}'] = str(days_of_week[3].day)
    replacements['{fri_dom}']  = str(days_of_week[4].day)
    replacements['{sat_dom}']  = str(days_of_week[5].day)
    replacements['{sun_dom}']  = str(days_of_week[6].day)
    for pattern, replacement in replacements.items():
        week_daylist_template_string = week_daylist_template_string.replace(pattern, replacement)
    a5_filename = f'{a5_page_num:03d}_week_daylist_week{week}.svg'
    a5_filename = os.path.join(a5_pages_dir,a5_filename)
    with open(a5_filename,'w') as output_svg:
        output_svg.write(week_daylist_template_string)
    a5_pages.append(a5_filename)
    a5_page_num += 1

# Pad A5 page list with empty pages until it has a multiple of 4 pages    
while len(a5_pages)%4 != 0:
    a5_pages.append(None)

# Pack the A5 pages into A4 pages
a4_num = 1
a4_svg_files = []
a4_pdf_files = []
while len(a5_pages) > 0:
    if args.reorder:
      first_a4_right  = a5_pages.pop(0)
      second_a4_left  = a5_pages.pop(0)
      second_a4_right = a5_pages.pop(0)
      first_a4_left   = a5_pages.pop(0)
    else:
      first_a4_left   = a5_pages.pop(0)
      first_a4_right  = a5_pages.pop(0)
      second_a4_left  = a5_pages.pop(0)
      second_a4_right = a5_pages.pop(0) 
    a4_filename = (os.path.join(a4_svgs_dir, f'{a4_num:03d}.svg'))
    a4_svg_files.append(a4_filename)
    write_a4_svg(first_a4_left, first_a4_right, a4_filename)
    a4_num += 1
    a4_filename = (os.path.join(a4_svgs_dir, f'{a4_num:03d}.svg'))
    a4_svg_files.append(a4_filename)
    write_a4_svg(second_a4_left, second_a4_right, a4_filename)  
    a4_num += 1

# Convert the A4 svgs to A4 pdfs using cairosvg
for a4_svg in a4_svg_files:
    a4_pdf = os.path.basename(a4_svg)[0:-3] + 'pdf'
    a4_pdf = os.path.join(a4_pdfs_dir,a4_pdf)
    a4_pdf_files.append(a4_pdf)
    cmd = f'cairosvg -o {a4_pdf} {a4_svg}'
    print(cmd)
    subprocess.run(cmd, shell=True)

# Combine all the A5 pdfs into a single pdf using ghostscript
merged_pdf_file = os.path.join(year_dir,f'merged_year_{year}.pdf')
cmd = f'gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -dAutoRotatePages=/None -sOutputFile={merged_pdf_file} {" ".join(a4_pdf_files)}'
print(cmd)
subprocess.run(cmd, shell=True)
print(f'Merged pdf created at {merged_pdf_file}')
