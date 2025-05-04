import tkinter as tk
from monitor import SystemMonitor
from stress_test import StressTest
import threading

class SystemMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Monitor")
        self.monitor = SystemMonitor()
        self.stress = StressTest()

        # Метки для отображения метрик
        self.cpu_label = tk.Label(root, text="CPU Usage: N/A")
        self.cpu_label.pack()
        self.ram_label = tk.Label(root, text="RAM Usage: N/A")
        self.ram_label.pack()

        # Кнопка для стресс-теста
        self.stress_button = tk.Button(root, text="Run CPU Stress Test (10s)", command=self.run_stress_test)
        self.stress_button.pack()

        # Запуск мониторинга
        self.start_monitoring()

    def update_metrics(self, cpu_usage, ram_info):
        cpu_text = f"CPU Usage: {cpu_usage}"
        ram_text = f"RAM: {ram_info['percent']}% (Used: {ram_info['used']:.2f} GB, Free: {ram_info['free']:.2f} GB)"
        self.cpu_label.config(text=cpu_text)
        self.ram_label.config(text=ram_text)

    def start_monitoring(self):
        def callback(cpu, ram):
            self.update_metrics(cpu, ram)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback,), daemon=True).start()

    def run_stress_test(self):
        self.stress_button.config(state="disabled")
        threading.Thread(target=self.stress.cpu_stress, args=(10,), daemon=True).start()
        self.root.after(10000, lambda: self.stress_button.config(state="normal"))

# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = SystemMonitorApp(root)
    root.mainloop()