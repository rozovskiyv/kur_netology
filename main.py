import json
import requests
import os
import string
import datetime
from pprint import pprint
import configparser
from tqdm import tqdm


def get_token(name):
    """
    Возвращает токен из INI файла указанной сети
    """
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config[name]['token']


def is_valid_filename(filename):
    """
    Проверяет, что заданное имя файла является допустимым для использования в качестве имени файла или папки.
    Возвращает True, если имя файла допустимо, и False в противном случае.
    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    for char in filename:
        if char not in valid_chars:
            return False
    return True


def get_photo_count():
    while True:
        res = int(input('Введите требуемое количество фотографий от 1 до 1000 включительно:'))
        if res in range(1, 1001):
            break
        else:
            print('Число некорректно')
    return res


def make_dicts_for_upload(photos_list):
    """
    Создаёт список словарей с информацией о фотографиях.
    Последний элемент содержит ссылку на макс. размер, можно переделать под сравнение размеров
    """
    result = []
    ext = '.jpg'
    for photo in photos_list:
        url = photo['sizes'][-1]['url']
        file_name = str(photo['likes']['count'])
        size = photo['sizes'][-1]['type']

        for el in result:
            if (file_name + ext) == el['file_name']:
                file_name += datetime.datetime.now().strftime("_%Y-%m-%d")

        result.append({'url': url,
                       'file_name': file_name + ext,
                       'size': size})
    return result


def save_photos_to_disk(dict_photos, folder=None):
    """
    Сохраняет фотографии из словаря в указанную папку на диске удалив оттуда все файлы
    """
    current = os.getcwd()
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f'Не получилось удалить {file_path}. Причина: {e}')

    os.makedirs(folder, exist_ok=True)

    with tqdm(total=100, desc="Сохраняем фотографии из vk в папку") as pbar:
        for photo in dict_photos:
            file_name = photo['file_name']
            with open(os.path.join(current, folder, file_name), 'wb') as f:
                res = requests.get(photo['url'])
                f.write(res.content)
            pbar.update(100 / len(dict_photos))


class VK:
    """
    Создаёт класс для работы с соцсетью Вконтакте
    """
    url = 'https://api.vk.com/method/'

    def __init__(self, token):
        self.token = token
        self.params = {'access_token': token,
                       'v': '5.131'}

    def show_albom_list(self, owner_id=None):
        """
        Выполняем запрос к API VK для получения списка альбомов и выбора необходимого
        """
        add_params = {'need_system': 1,
                      'owner_id': owner_id}
        response = requests.get(vk.url + 'photos.getAlbums', params={**self.params, **add_params})

        # Получаем список альбомов из ответа сервера
        albums = response.json()["response"]["items"]

        # Выводим названия всех альбомов
        print(f'Для пользователя {owner_id} доступны следующие альбомы:')
        albums_numbers = []
        for album in albums:
            print(f'{album["title"]} - id: {album["id"]}')
            albums_numbers.append(album["id"])
        # Запрашиваем id альбома
        while True:
            res = int(input('Введите код альбома:'))
            if res in albums_numbers:
                break
            else:
                print('Нет альбома с таким кодом')
        return res  # Возвращаем код нужного альбома

    def get_user_info(self, ids, fields):
        """
        Выводит данные об указанном пользователе
        """
        add_params = {'user_ids': ids,
                      'fields': fields}
        return requests.get(vk.url + 'users.get', params={**self.params, **add_params}).json()

    def get_photos(self, owner_id=None, album=-6, count=5):
        """
        Возвращает список словарей с информацией о фотографиях указанного пользователя (owner_id)
        По умолчанию берёт 5 фотографий из альбома profile текущего пользователя
        """
        add_params = {'owner_id': owner_id,
                      'album_id': album,
                      'extended': 1,
                      'photo_sizes': 1,
                      'count': count}
        return requests.get(vk.url + 'photos.get', params={**self.params, **add_params}).json()['response']['items']


class YDisk:
    def __init__(self, token):
        self.token = token

    def get_headers(self):
        return {
            'Content-type': 'application/json',
            'Authorization': 'OAuth {}'.format(self.token)
        }

    def get_file_list(self):
        res_url = 'https://cloud-api.yandex.net/v1/disk/resources/files'
        headers = self.get_headers()
        response = requests.get(res_url, headers=headers)
        return response.json()

    def make_folder(self, name):
        """
        Создаёт папку и выдаёт статус
        """
        headers = self.get_headers()
        params = {'path': name,
                  'type': 'dir'}
        response = requests.put('https://cloud-api.yandex.net/v1/disk/resources', headers=headers, params=params)
        # if response.status_code == 201:
        #     print(f'Папка "{name}" на Yandex Disk создана')
        # elif response.status_code == 409:
        #     print(f'Папка "{name}" на Yandex Disk уже есть')
        # else:
        #     print(f'Создание папки выдало код {response.status_code}')

    def _get_upload_link(self, file_path):
        """
        Подготавливает ссылку для закачивания файла на диск
        """
        headers = self.get_headers()
        params = {'path': file_path, 'overwrite': 'true'}
        response = requests.get('https://cloud-api.yandex.net/v1/disk/resources/upload', headers=headers, params=params)
        return response.json()

    def upload(self, path, name):
        link = self._get_upload_link(path + '/' + name)
        href = link.get('href')
        requests.put(href, data=open(os.path.join(path, name), 'rb'))


if __name__ == '__main__':
    # считываем токены с ini файла и создаем экземпляры классов ВК и Яндекс диск
    vk = VK(get_token('vk.com'))
    ya = YDisk(get_token('ya.disk'))

    # Задаём id пользователя, чьи фотографии будем сохранять
    vk_id = '65348919'

    # Выбираем альбом для скачивания
    album_id = -6  # Или используем vk.show_albom_list(vk_id)

    # Выбираем количество фото для скачивания
    count_photo = 5  # или используем get_photo_count()

    # получаем информацию о фотографиях и создаём словарь с нужными данными
    photos = vk.get_photos(vk_id, album_id, count_photo)
    photos_url = make_dicts_for_upload(photos)

    # сохраняем фото на диск в указанную папку удалив оттуда все файлы
    folder_name = 'vk_photo'
    save_photos_to_disk(photos_url, folder_name)

    # создаём json файл скопировав photos_url без ключа url
    json_temp = []
    for el in photos_url:
        del el['url']
        json_temp.append(el)
    json_filename = os.path.join(folder_name, 'photos_info.json')
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(json_temp, f, ensure_ascii=False, indent=4)

    # создаём одноименную папку на яндекс диске
    ya.make_folder(folder_name)

    # заливаем фотографии на яндекс диск
    with tqdm(total=100, desc="Заливаем фотографии на Яндекс диск") as pbar:
        for el in photos_url:
            ya.upload(folder_name, el['file_name'])
            pbar.update(100 / len(photos_url))

    # заливаем json файл
    with tqdm(total=100, desc="Добавляем json файл на Яндекс диск") as pbar:
        ya.upload(folder_name, 'photos_info.json')
        pbar.update(100)
