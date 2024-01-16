from datetime import datetime
from typing import List, Optional
import re
from PIL import Image
from pytesseract import pytesseract


def founded_name(text: str, regex_list: List[str]) -> Optional[str]:
    for regex in regex_list:
        found_name = re.findall(regex, text)
        if found_name:
            name = found_name[-1].strip()  # Используется последнее подходящее фио
            # т.к. в блоке может быть несколько фио, а необходимо то, что идёт последним
            if "," in name:
                name = name[:name.index(",")]
            break
    else:
        name = None
    return name


def founded_address(text: str, regex_list: List[str]) -> Optional[str]:
    for regex in regex_list:
        found_address = re.search(regex, text)
        if found_address:
            address = found_address.group().strip().replace("\n", ", ")  # замена лишних переносов на запятые
            while ', ,' in address:  # удаление лишних запятых, добавленных на предыдущем шаге
                address = address.replace(", ,", ",")
            if "Non-ID Affidavit" in address:
                address = address.replace("Non-ID Affidavit", "")
            break
    else:
        address = None
    return address


def founded_description(text: str, regex_list: List[str]) -> Optional[str]:
    for regex in regex_list:
        description = re.search(regex, text, flags=re.I)
        if description:
            description = description.group()
            while "\n" in description:
                description = description.strip().replace("\n", " ")
            break
    else:
        description = None
    return description


def extract_name_address_description(text: str) -> List[str]:
    # В данном разделе осуществляется поиск части текста, в котором указывается фио и адрес. Поиск осуществляется по
    # фразе "Prepared by and return to". Если поиск по ключевой фразе не помог,
    # то фио будет подтягиваться из блока, указанного над адресом почты
    regex_for_base_founded = [
        r"by\s{,3}(?:and|\n)\s{,3}\b\w{,12}\b\s{,3}(?:to|..).{,3}\n(?:.*\n){,20}.{,50}\b\d{5}\b",
        r"(?:\n{1,3}.{,50}){3,8}\b\d{5}\b"]
    for regex in regex_for_base_founded:
        base_founded = re.search(regex, text, flags=re.I)
        if base_founded:
            break
    else:
        base_founded = None

    # Если блок с данными найден, то происходит его анализ
    if base_founded:
        new_text = base_founded.group()
        # Поиск адресса
        regex_for_founded_address = [r'\d{1,6}\s.{,50}\n{1,5}.{1,50}\n{1,5}.{5,50}\n{1,5}.{5,50}\b\d{5}\b',
                                     r'(?:(?:\d{1,6}.{,50}\n{1,5}.{,50}\n{1,5}.{5,50}\b)|'
                                     r'(?:\d{1,6}.{,50}\n{1,5}.{,50}\b))\d{5}\b']
        address = founded_address(new_text, regex_for_founded_address)

        #  Поиск имени
        regex_for_founded_name = [
            r"\n\b[A-Z]{1}[a-z]{1,20}\b.{,3}\b[A-Z8](?:[a-z]{,20}|[\.,]{1})\b.{,3}"
            r"\b(?:[A-Z]{1}[a-z]{,20}){,1}"
            r"\b(?:(?!,\sPA)(?!P\.A)(?!Company)(?!LLC)(?!\d{1,7}).)*\n",
            r"(?<=Print Name:).{,3}\b[A-Z]{1}[a-z]{1,20}\b.{,3}"
            r"\b[A-Z8](?:[a-z]{,20}|[\.,]{1})\b.{,3}\b(?:[A-Z]{1}[a-z]{,20}){,1}\b"]
        name = founded_name(new_text, regex_for_founded_name)
    else:
        name = None
        address = None

    #  блок отвечающий за поиск имени во всем тексте, если оно не было найдено в отдельном блоке
    regex_for_second_try_founded_name = [r"(?<=Print Name:).{,3}\b[A-Z]{1}[a-z]{1,20}\b.{,3}"
                                         r"\b[A-Z8](?:[a-z]{,20}|[\.,]{1})\b.{,3}\b(?:[A-Z]{1}[a-z]{,20}){,1}\b",
                                         r"(?<=undersigne.,).*(?=, do hereby|hereby)?",
                                         r"(?<=Prepared by:).{,3}\b[A-Z]{1}[a-z]{1,20}\b.{,3}"
                                         r"\b[A-Z8](?:[a-z]{,20}|[\.,]{1})\b"]
    if name is None and regex_for_second_try_founded_name:
        name = founded_name(text, regex_for_second_try_founded_name)

    #  блок отвечающий за поиск адреса во всем тексте, если он не было найдено в отдельном блоке
    regex_for_second_try_founded_address = [r"(?<=.ailing..ddress:).*\n",
                                            r"(?<=c.o).*\s{,2}\b\d{5}\b\n"]
    if address is None and regex_for_second_try_founded_address:
        address = founded_address(text, regex_for_second_try_founded_address)

    # В данном разделе осуществляется поиск содержания документа. Поиск осуществляется по фразе "Before me"
    regex_for_founded_description = [r"(?<=hereby.state)(?:.*\n|.*)*$",
                                     r"(\b.[er].{1,2}(?:0|o)\w{2},?\s{1,2}\w{,3})(?:.*(?:\n|$))*"]
    description = founded_description(text, regex_for_founded_description)

    # замена ненайденных значений пустыми значениями
    none_list = ["Имя не найдено", "Адрес не найден", "Описание документа не найдено"]
    list_for_return = [name, address, description]
    list_for_return = [list_for_return[i] if list_for_return[i] else none_list[i] for i in range(3)]
    return list_for_return


def work_with_file(file_path: str) -> List[str]:
    image = Image.open(file_path)
    image = image.resize((977, 1265))
    path_to_tesseract = r"D:\Program Files\tesseract\tesseract.exe"  # r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    pytesseract.tesseract_cmd = path_to_tesseract
    text = pytesseract.image_to_string(image)

    # Извлекаем фио, адрес и описание
    name, address, description = extract_name_address_description(text)
    time = datetime.now().strftime("%d.%m.%Y %H:%M")
    print(f"Найденные данные\nИмя: {name};\nАдрес: {address};\nОписание файла: {description};\n"
          f" Дата и время получения данных из файла: \n{time}.")
    return [name, address, description, time]
