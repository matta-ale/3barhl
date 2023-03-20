
#SI SE ROMPE, TUTORIAL: https://www.youtube.com/watch?v=ps1yeWwd6iA


def sendTelegram(message):
    import requests
    chatId = '-724816008'
    url = 'https://api.telegram.org/bot1700277460:AAG4YdeSJZ0iZEYmambFKZN5pZTEVMb-YQ8/sendMessage?chat_id='+chatId+'&text="{}"'.format(message)
    requests.get(url)
    return

