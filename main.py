# main.py
import customtkinter as ctk
import signal
import sys
import tkinter as tk
import logging

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def signal_handler(sig, frame):
    logging.info("Program stopped via SIGINT")
    print("Program stopped.")
    sys.exit(0)

if __name__ == "__main__":
    logging.info("Starting application")
    try:
        signal.signal(signal.SIGINT, signal_handler)

        logging.info("Testing tkinter")
        root_test = tk.Tk()
        root_test.destroy()
        logging.info("tkinter test passed")

        logging.info("Initializing CustomTkinter")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        root = ctk.CTk()
        root.title("System Stress Test")
        logging.info("CustomTkinter window created")

        # Добавляем скроллбар
        canvas = ctk.CTkCanvas(root, bg="#2b2b2b")  # Задаем фон для отладки
        scrollbar = ctk.CTkScrollbar(root, orientation="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas, fg_color="#2b2b2b")  # Задаем фон для отладки

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.focus_set()  # Устанавливаем фокус на канвас

        # Включаем прокрутку колесом мыши
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)  # Для Windows/Linux
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Для Linux
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Для Linux

        # Главное окно
        from ui import MainApp
        app = MainApp(scrollable_frame)  # Передаем scrollable_frame
        logging.info("MainApp initialized")

        # Устанавливаем минимальный размер окна
        root.minsize(800, 600)

        # Обработчик закрытия окна
        root.protocol("WM_DELETE_WINDOW", app.on_closing)

        # Вывод версии customtkinter для отладки
        logging.info(f"CustomTkinter version: {ctk.__version__}")
        print(f"CustomTkinter version: {ctk.__version__}")

        root.mainloop()
        logging.info("Main loop exited")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)