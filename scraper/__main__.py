import argparse
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import MoveTargetOutOfBoundsException, NoSuchElementException
from selenium.webdriver.firefox.options import Options
import time
from os import makedirs
from os.path import exists, isdir, join, basename


# parser setup =========================================================================================================
parser = argparse.ArgumentParser()

parser.add_argument("--input", "-i", dest="input", type=str, required=True)
parser.add_argument("--output", "-o", dest="output", type=str, required=True)
parser.add_argument("--reset-data", dest="reset_data", action="store_true")
parser.add_argument("-r", dest="recursive", action="store_true")

args = parser.parse_args()
# ======================================================================================================================


# sorter ===============================================================================================================
def rect_sort(element):
    return float(element.get_attribute("x")) + 2
# ======================================================================================================================


# selenium implementations =============================================================================================
def driver_setup():
    print(" > setting up webdriver...")

    driver_options = Options()
    driver = webdriver.Firefox(firefox_options=driver_options)

    if driver:
        print(" > driver set up!")
    else:
        print(" > problem setting up driver!")
    return driver


def scrape(driver, url, output_directory, reset_data=False, output_list_file=None):
    print(" > retrieving data from %s" % url)

    driver.get(url)

    # wait for loading of data
    while True:
        no_cases = [element
                    for element in driver.find_elements_by_tag_name("h3")
                    if "0 cases reported to the WHO for this country, territory, or area" in element.text]
        data_elements = [element
                         for element in driver.find_elements_by_class_name("vx-group")
                         if element.get_attribute("class") == "vx-group"]
        if not data_elements and not no_cases:
            time.sleep(0.5)
        else:
            break

    country = driver.find_element_by_link_text("Global").find_elements_by_xpath("../../span")[1]\
        .text.replace(' ', '_')\
        .lower()\
        + ".csv"
    if output_list_file:
        output_list_file.write(country)
    print(" > writing to data %s" % join(output_directory, country))
    driver.execute_script("document.evaluate(\"//div[@id='root']/div/div\", document, null, "
                          "XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.remove();")

    cases = []
    deaths = []
    if not exists(join(output_directory, country)):
        print(" > no existing file was found, generating new one")
    else:
        print(" > loading existing data from file")
        with open(join(output_directory, country), 'r+') as output_file:
            while True:
                line = output_file.readline()
                if not line:
                    break
                if "cases" in line:
                    cases.append(line.split(";")[0])
                elif "deaths" in line:
                    deaths.append(line.split(";")[0])

    with open(join(output_directory, country), 'a+') as output_file:
        if no_cases:
            if "" not in cases:
                output_file.write(";0;cases\n")
            if "" not in deaths:
                output_file.write(";0;deaths\n")
            return

        for element in data_elements:
            data = []
            parent = element.find_element_by_xpath("../../*[name()='svg']")

            while True:
                try:
                    ActionChains(driver).move_to_element_with_offset(parent, int(parent.get_attribute("width")), -1)\
                        .perform()
                    break
                except MoveTargetOutOfBoundsException:
                    driver.execute_script("arguments[0].scrollIntoView();", parent)
                    time.sleep(0.01)

            rects = element.find_elements_by_tag_name("rect")
            rects.sort(key=rect_sort, reverse=True)

            process_list(driver, output_file, rects, parent, element, data, reset_data, cases, deaths)

    print(" > done")


def process_list(driver, output_file, rects, parent, element, data, reset_data, cases, deaths):
    for data_point in rects:
        x = float(data_point.get_attribute("x")) + 2
        y = 15
        while True:
            try:
                ActionChains(driver).move_to_element_with_offset(parent, x, y).perform()

                while True:
                    try:
                        data_point_data = element.find_element_by_xpath("../../div")
                        if data_point_data.text not in data:
                            break
                    except NoSuchElementException:
                        time.sleep(0.01)

                if "Confirmed Cases" in data_point_data.text:
                    data_element = data_point_data.text.split("\n")
                    if data_element[0] not in cases:
                        output_file.write("%s;%s;%s\n" % (
                            data_element[0],
                            data_element[1],
                            "cases")
                        )
                    elif not reset_data:
                        print(" > %s already in data, skipping this list." % data_element[0])
                        return
                elif "Deaths" in data_point_data.text:
                    data_element = data_point_data.text.split("\n")
                    if data_element[0] not in deaths:
                        output_file.write("%s;%s;%s\n" % (
                            data_element[0],
                            data_element[1],
                            "deaths")
                        )
                    elif not reset_data:
                        print(" > %s already in data, skipping this list." % data_element[0])
                        return
                break
            except MoveTargetOutOfBoundsException:
                driver.execute_script("arguments[0].scrollIntoView();", data_point)
                time.sleep(0.01)

# ======================================================================================================================


# main =================================================================================================================
def main(main_args):
    driver = driver_setup()
    if not driver:
        return

    if not exists(main_args.output) or not isdir(main_args.output):
        makedirs(main_args.output)

    if main_args.recursive:
        if exists(main_args.input):
            print(" > retrieving data listed in %s to %s" % (main_args.input, main_args.output))

        output_list = join(main_args.output, basename(main_args.input))
        if exists(output_list) and not main_args.reset_data:
            print(" > %s already exists, overwrite it?" % output_list)
            while input("y or [n]: ") is not 'y':
                print(" > not overwriting file")
                return

        with open(main_args.input, 'r') as input_file, open(output_list, 'w') as output_list_file:
            while True:
                line = input_file.readline()
                if not line:
                    break

                scrape(driver, line.replace('\n', ''), args.output, main_args.reset_data, output_list_file)

    else:
        scrape(driver, main_args.input, args.output, main_args.reset_data)

    driver.close()
    print(" > done retrieving data")
# ======================================================================================================================


if __name__ == '__main__':
    main(args)
