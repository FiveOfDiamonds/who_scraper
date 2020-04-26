import argparse
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import MoveTargetOutOfBoundsException, NoSuchElementException
import time


# parser setup =========================================================================================================
parser = argparse.ArgumentParser()

parser.add_argument("--input", "-i", dest="input", type=str, required=True)
parser.add_argument("--output", "-o", dest="output", type=str, required=True)

args = parser.parse_args()
# ======================================================================================================================


# selenium implementations =============================================================================================
def driver_setup():
    print("setting up webdriver...")
    driver = webdriver.Firefox()
    if driver:
        print(" > driver set up!")
    else:
        print(" > problem setting up driver!")
    return driver


def scrape(driver, url, output_file):
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

    country = driver.find_element_by_link_text("Global").find_elements_by_xpath("../../span")[1].text

    if no_cases:
        output_file.write("%s;;0;cases\n" % country)
        output_file.write("%s;;0;deaths\n" % country)
        return

    for element in data_elements:
        data = []
        parent = element.find_element_by_xpath("../../*[name()='svg']")
        for data_point in element.find_elements_by_tag_name("rect"):
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
                    data.append(data_point_data.text)
                    break
                except MoveTargetOutOfBoundsException:
                    driver.execute_script("arguments[0].scrollIntoView();", data_point)
                    time.sleep(0.01)

        for data_element in data:
            output_file.write("%s;%s;%s;%s\n" % (
                country,
                data_element.split("\n")[0],
                data_element.split("\n")[1],
                "cases" if "Cases"in data_element else "deaths")
            )
    print(" > done")
# ======================================================================================================================


# main =================================================================================================================
def main(main_args):
    driver = driver_setup()
    if not driver:
        return

    print(" > retrieving data listed in %s to %s" % (main_args.input, main_args.output))

    try:
        with open(main_args.input, 'r') as input_file, open(main_args.output, 'w') as output_file:
            while True:
                line = input_file.readline()
                if not line:
                    break

                scrape(driver, line.replace('\n', ''), output_file)

        driver.close()
        print(" > done retrieving data")

    except FileNotFoundError:
        print(" > could not open input file at %s" % main_args.input)
# ======================================================================================================================


if __name__ == '__main__':
    main(args)
