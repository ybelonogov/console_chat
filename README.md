# Console_chat

## Описание

Это простое консольное чат-приложение, состоящее из сервера и клиента, реализованное на Python с использованием ООП. Приложение позволяет пользователям регистрироваться, отправлять сообщения друг другу, изменять никнеймы, завершать сессии и выключать сервер (для админа).

## Требования

- Python 3.x
- Библиотеки: `socket`, `threading`, `json`, `sys`

## Установка

1. **Склонируйте репозиторий**

   ```bash
   git clone <repository_url>
   cd <repository_directory>
   
2. **Установите недостающие библиотеки**

## Конфигурация
Измените файл конфигурации config.json в корневой директории проекта:

[//]: # (    ```json)
     {
         "host": "127.0.0.1",
         "port": 12345,
         "max_users": 10,
         "buffer_size": 1024,
         "log_level": "INFO"
     }
## Развертывание
Запустите сервер:

    python server.py config.json

Запустите клиента в другом терминале:

    python client.py config.json
## Использование
### Команды клиента
- Регистрация:

      /register <nickname>

- Изменение никнейма:

      /change_nick <new_nickname>
- Отправка сообщения:

      <recipient_nickname> <message>
- Завершение сессии клиента:

       /quit
Выключение сервера: (только для пользователя с ником admin)

       /shutdownф
## Примеры использования
Регистрация пользователя, отпрака сообщения, выключение сервера и завершение сесии 

    /register Alex
    Bob Привет, как дела?
    /change_nick adimin
    /shutdown
    /quit

## Просмотр логов
    cat /var/log/syslog | grep ChatServer