import requests
import lxml.html
import rdflib
from collections import deque
from urllib.parse import unquote
import sys

flag = [False]
flag_area = [False]

def extract_name(url):
    return url.split("/")[-1]

def create_initial_urls_queue():
    r = requests.get(starting_url)
    doc = lxml.html.fromstring(r.content)
    for url in doc.xpath('//table[contains(@class , "wikitable sortable")]//tr[position()>=2]/td[1]//a[1]/@href'): # should check what about cite_note
        if not url.startswith('#cite') and url.find("Realm") == -1 and url.find("Fifth") == -1 and url.find("Kingdom_of_the") == -1:
            link = prefix + url
            if link not in visited:
                bfs_queue.append(("Country", link))
                visited.add(link)

def insert_to_graph(object1, relation, object2):
    object2 = object2.strip()
    object2 = object2.replace(" ", "_")
    object2 = ontology_prefix + object2
    relation = relation.strip()
    relation = ontology_prefix + relation
    relation = relation.replace(" ", "_")
    for i in range(len(object1)):
        if object1[i].find('#cite') != -1 or object1[i].find("geohack") != -1 or object1[i].find("oordinate") != -1 or object1[i][0] == '[' or object1[i].find("#endnote") != -1:
            continue
        else:
            object1[i] = extract_name(object1[i])

        object1[i] = object1[i].strip(" _(").replace(" ", "_")
        object1[i] = ontology_prefix + object1[i]
        if object1[i].find('Brave') != -1 or object2.find('Brave') != -1:
            continue
        else:
            g.add((rdflib.URIRef(unquote(object1[i])), rdflib.URIRef(relation), rdflib.URIRef(unquote(object2))))

def insert_tuples_to_queue(label , links):
    for link in links:
        bfs_queue.append((label,link))

def country_label_handler(url,label):
    country = extract_name(url)
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    links = []
    data = []
    if label == "Government":
        data = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[th//text()="{}"]/td//a/@href'.format(label))

    elif label == "Capital":
        data = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[th/text()="{}"]/td//a[1]/@href'.format(label))
        if len(data) > 1:
            data = [data[0]]


    elif label == "President" or label == "Prime Minister":
        links = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[th/div/a//text()="{}"]/td//a[1]/@href'.format(label)) # link to the wiki page of the president(/prime mininster)
        data = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[th/div/a//text()="{}"]/td//a[1]/@href'.format(label)) # the president(/prime mininster) name


    elif label == "Population" or label == "Area ":
        row_num = int(doc.xpath('count(//table[contains(@class , "infobox")]/tbody/tr[contains(th/a//text(),"{}")]/preceding-sibling::*)'.format(label.strip())))+2
        if row_num == 2:
            data = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[th/text()="{}"]/td/text()[1]'.format(label.strip()))
            if len(data) == 0:
                row_num = int(doc.xpath('count(//table[contains(@class , "infobox")]/tbody/tr[contains(th/text(),"{}")]/preceding-sibling::*)'.format(label.strip()))) + 2
                data = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[{}]/td/text()[1]'.format(row_num))
        else:
            data = doc.xpath('//table[contains(@class , "infobox")]/tbody/tr[{}]/td/text()[1]'.format(row_num))
            if len(data) > 0 and data[0] == ' (':
                data = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[{}]/td/span/text()[1]'.format(row_num))
                if len(data) == 0:
                    data = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[{}]/td/span/span/text()[1]'.format(row_num))
                    if len(data) == 0:
                        data = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[{}]/td/div/ul/li[1]/text()[1]'.format(row_num))

    if links != []:
        links = [prefix + link for link in links]
        insert_tuples_to_queue(label, links)

    insert_to_graph(data,label,country)


def person_label_handler(url,label):
    person = [extract_name(url)]
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    data1 = []
    data2 = []

    if label == "Born":
        data1 = doc.xpath('//table[@class ="infobox vcard"]/tbody/tr[th//text()="Born"]/td/span/span[1]/text()[1]')
        if len(data1) == 0 or data1[0] == " (":
            data1 = doc.xpath('//table[@class ="infobox vcard"]/tbody/tr[th//text()="Born"]/td/span/span/span[1]/text()')

        data2 = doc.xpath('//table[@class ="infobox vcard"]/tbody/tr[th//text()="Born"]/td/text()[last()]')
        if len(data2) == 0 or data2[0] in trash or data2[0][0].isdigit() or data2[0][0] == " ":
            data2 = doc.xpath('//table[@class ="infobox vcard"]/tbody/tr[th//text()="Born"]/td/a[last()]/text()')

    if data1 != []:
        insert_to_graph(person, label+" at", data1[0])

    if data2 != []:
        if len(data2[0].split(", ")) > 1:
            data2[0] = data2[0].split(", ")[-1]
        insert_to_graph(person, label+" in", data2[0].strip(' ,_'))

def web_crawler():
    while len(bfs_queue) > 0:
        print(len(bfs_queue))
        element_tuple = bfs_queue.popleft()
        if element_tuple[0] == "Country":
            for label in country_labels:
                country_label_handler(element_tuple[1] , label)

        elif element_tuple[0] == "President" or element_tuple[0] == "Prime Minister":
            for label in person_labels:
                person_label_handler(element_tuple[1], label)

def create_ontology():
    create_initial_urls_queue()
    web_crawler()

def format_result(lst):
    for i in range(len(lst)):
        lst[i] = extract_name(lst[i][0]).replace("_", " ").replace("\u2013", "-")
    lst.sort()

def print_result(lst):
    for i in range(len(lst) - 1):
        a = lst[i] + ", "
        print(a, end="")
    if len(lst) > 0:
        print(lst[-1])

def print_result2(lst, flag):
    for i in range(len(lst) - 1):
        a = lst[i] + ", "
        if flag:
            print("President of", a, end="")
        else:
            print("Prime Minister of", a, end="")
    if len(lst) > 0:
        if flag:
            print("President of", lst[-1], end="")
        else:
            print("Prime Minister of", lst[-1], end="")

def ask_question(question):
    g.parse("ontology.nt", format="nt")
    qr = ""
    if question.find("Who is the president of") != -1:
        qr = "select * where {?entity " + "<" + ontology_prefix + "President" + "> <" + ontology_prefix + question[24:-1].replace(" ", "_") + ">" + "}"
    elif question.find("Who is the prime minister of") != -1:
        qr = "select * where {?entity " + "<" + ontology_prefix + "Prime_Minister" + "> <" + ontology_prefix + question[29:-1].replace(" ", "_") + ">" + "}"
    elif question.find("What is the population of") != -1:
        qr = "select * where {?entity " + "<" + ontology_prefix + "Population" + "> <" + ontology_prefix + question[26:-1].replace(" ", "_") + ">" + "}"
    elif question.find("What is the area of") != -1:
        flag_area[0] = True
        qr = "select * where {?entity " + "<" + ontology_prefix + "Area" + "> <" + ontology_prefix + question[20:-1].replace(" ", "_") + ">" + "}"
    elif question.find("What is the form of government in") != -1:
        qr = "select * where {?entity " + "<" + ontology_prefix + "Government" + "> <" + ontology_prefix + question[34:-1].replace(" ", "_") + ">" + "}"
    elif question.find("What is the capital of") != -1:
        qr = "select * where {?entity " + "<" + ontology_prefix + "Capital" + "> <" + ontology_prefix + question[23:-1].replace(" ", "_") + ">" + "}"
    elif question.find("When was the president of") != -1:
        qr = "select ?date where {?entity " + "<" + ontology_prefix + "President" + "> <" + ontology_prefix + question[26:-6].replace(" ", "_") + ">" + ". " + "?entity " + "<" + ontology_prefix + "Born_at" + "> " + "?date" + "}"
    elif question.find("Where was the president of") != -1:
        qr = "select ?date where {?entity " + "<" + ontology_prefix + "President" + "> <" + ontology_prefix + question[27:-6].replace(" ", "_") + ">" + ". " + "?entity " + "<" + ontology_prefix + "Born_in" + "> " + "?date" + "}"
    elif question.find("When was the prime minister of") != -1:
        qr = "select ?date where {?entity " + "<" + ontology_prefix + "Prime_Minister" + "> <" + ontology_prefix + question[31:-6].replace(" ", "_") + ">" + ". " + "?entity " + "<" + ontology_prefix + "Born_at" + "> " + "?date" + "}"
    elif question.find("Where was the prime minister of") != -1:
        qr = "select ?date where {?entity " + "<" + ontology_prefix + "Prime_Minister" + "> <" + ontology_prefix + question[32:-6].replace(" ", "_") + ">" + ". " + "?entity " + "<" + ontology_prefix + "Born_in" + "> " + "?date" + "}"
    elif question.find("Who is") != -1:
        flag[0] = True
        qr = "select * where {<" + ontology_prefix+question[7:-1].replace(" ", "_") + "> <" + ontology_prefix + "President" + ">" + " ?countries" + "}"
        result_list = g.query(qr)
        result_list = list(result_list)
        fl = False
        if len(result_list) > 0:
            format_result(result_list)
            print_result2(result_list,True)
            fl = True
        qr = "select * where {<" + ontology_prefix+question[7:-1].replace(" ", "_") + "> <" + ontology_prefix + "Prime_Minister" + ">" + " ?countries" + "}"
        result_list = g.query(qr)
        result_list = list(result_list)
        if len(result_list) > 0:
            if fl:
                print(", ", end="")
            format_result(result_list)
            print_result2(result_list,False)
        print("")
        return []



    elif question.find("How many") != -1 and question.find("are also") != -1:
        spl = question.split(" are also ")
        a = spl[0]
        b = spl[1]
        qr = "select ?country where { " + "<" + ontology_prefix + a[9:].replace(" ", "_") + "> " + "<" + ontology_prefix + "Government" + "> " + "?country" + ". " + "<" + ontology_prefix + b[:-1].replace(" ", "_") + "> " + "<" + ontology_prefix + "Government" + "> " + "?country" + "}"
        result_list = list(g.query(qr))
        print(len(result_list))
        return []



    elif question.find("List all countries whose capital name contains the string") != -1:
        qr = "select ?capital where { ?capital " + "<" + ontology_prefix + "Capital" + ">" + " ?country" + "}"
        capitals = list(g.query(qr))
        result_list = []
        for cap in capitals:
            if extract_name(cap[0]).lower().find(question[58:].replace(" ", "_")) != -1:
                qr = "select ?country where { <" + ontology_prefix + extract_name(cap[0]) + "> <" + ontology_prefix + "Capital" + ">" + " ?country" + "}"
                country = list(g.query(qr))
                result_list += country
        return result_list


    elif question.find("How many presidents were born in") != -1:
        flag[0] = False
        qr = "select ?entity where {?entity " + "<" + ontology_prefix + "President" + ">" + " ?country" + ". " + "?entity " + "<" + ontology_prefix + "Born_in" + "> " + "<" + ontology_prefix+ question[33:-1].replace(" ", "_") + ">" + "}"
        result_list = set(list(g.query(qr)))
        print(len(result_list))
        return []

    elif question.find("How many prime ministers were born in") != -1:
        flag[0] = False
        qr = "select ?entity where {?entity " + "<" + ontology_prefix + "Prime_Minister" + ">" + " ?country" + ". " + "?entity " + "<" + ontology_prefix + "Born_in" + "> " + "<" + ontology_prefix+ question[38:-1].replace(" ", "_") + ">" + "}"
        result_list = set(list(g.query(qr)))
        print(len(result_list))
        return []

    result_list = g.query(qr)
    return result_list


if __name__ == "__main__":
    g = rdflib.Graph()
    starting_url = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
    prefix = "http://en.wikipedia.org"
    ontology_prefix = "http://example.org/"
    visited = set()  # for bfs
    bfs_queue = deque()  # queue of (element_type , link)
    country_labels = ["Prime Minister", "President", "Capital", "Government", "Area ", "Population"]
    person_labels = ["Born"]
    trash = {"", " ", " ,", ", ", ",", " (", "(", "( ", " )", ")", ") "}
    if sys.argv[1] == "create":
        create_ontology()
        g.serialize("ontology.nt", format="nt")
    elif sys.argv[1] == "question":
        question = sys.argv[2]
        res = list(ask_question(question))
        if flag_area[0]:
            if len(res) > 0:
                r = res[0][0]
                r = r.split("\u00A0")[0]
                r += " km squared"
                r = r.replace("\u2013", "-")
                print(extract_name(r.replace("_", " ")))
        elif not flag[0]:
            format_result(res)
            print_result(res)