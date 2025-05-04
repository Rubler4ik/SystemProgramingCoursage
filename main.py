import customtkinter as ctk
from ui import SystemMonitorApp
import signal
import sys
import tkinter as tk
import logging

# Настройка логирования
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def signal_handler(sig, frame):
    logging.info("Program stopped via SIGINT")
    print("Program stopped.")
    sys.exit(0)


if __name__ == "__main__":
    logging.info("Starting application")
    try:
        # Установка обработчика SIGINT
        signal.signal(signal.SIGINT, signal_handler)

        # Проверка tkinter
        logging.info("Testing tkinter")
        root_test = tk.Tk()
        root_test.destroy()
        logging.info("tkinter test passed")

        # Инициализация CustomTkinter
        logging.info("Initializing CustomTkinter")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        root = ctk.CTk()
        logging.info("CustomTkinter window created")

        # Запуск приложения
        app = SystemMonitorApp(root)
        logging.info("SystemMonitorApp initialized")

        # Запуск главного цикла
        root.mainloop()
        logging.info("Main loop exited")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)