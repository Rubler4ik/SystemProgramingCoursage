import customtkinter as ctk
from monitor import SystemMonitor
from stress_test import StressTest
from diagnostics import Diagnostics
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import csv
import time
import subprocess
import logging

logging.basicConfig(filename='ui.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Stress Test")
        self.monitor = SystemMonitor()
        self.stress = StressTest()
        self.diagnostics = Diagnostics()

        # Очереди для хранения данных графиков
        self.cpu_history = collections.deque(maxlen=30)
        self.gpu_history = collections.deque(maxlen=30)
        self.time_history = collections.deque(maxlen=30)

        # Основной фрейм
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # График
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(pady=10)

        # Метки для метрик
        self.cpu_label = ctk.CTkLabel(self.main_frame, text="CPU Usage: N/A")
        self.cpu_label.pack()
        self.cpu_freq_label = ctk.CTkLabel(self.main_frame, text="CPU Freq: N/A")
        self.cpu_freq_label.pack()
        self.cpu_temp_label = ctk.CTkLabel(self.main_frame, text="CPU Temp: N/A")
        self.cpu_temp_label.pack()
        self.ram_label = ctk.CTkLabel(self.main_frame, text="RAM Usage: N/A")
        self.ram_label.pack()
        self.disk_label = ctk.CTkLabel(self.main_frame, text="Disk Usage: N/A")
        self.disk_label.pack()
        self.disk_io_label = ctk.CTkLabel(self.main_frame, text="Disk IO: N/A")
        self.disk_io_label.pack()
        self.gpu_label = ctk.CTkLabel(self.main_frame, text="GPU Usage: N/A, Temp: N/A")
        self.gpu_label.pack()

        # Фрейм для галочек
        self.test_frame = ctk.CTkFrame(self.main_frame)
        self.test_frame.pack(pady=10)

        # Галочки для выбора тестов
        self.cpu_test_var = ctk.BooleanVar(value=True)
        self.ram_test_var = ctk.BooleanVar(value=True)
        self.disk_test_var = ctk.BooleanVar(value=True)
        self.gpu_test_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(self.test_frame, text="CPU Test", variable=self.cpu_test_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(self.test_frame, text="RAM Test", variable=self.ram_test_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(self.test_frame, text="Disk Test", variable=self.disk_test_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(self.test_frame, text="GPU Test", variable=self.gpu_test_var).pack(side="left", padx=5)

        # Кнопка для запуска теста
        self.start_button = ctk.CTkButton(self.main_frame, text="Start Stress Test (10s)", command=self.run_stress_test)
        self.start_button.pack(pady=10)

        # Индикатор прогресса
        self.progress_label = ctk.CTkLabel(self.main_frame, text="Test Progress: Idle")
        self.progress_label.pack()

        # Метка для ошибок
        self.error_label = ctk.CTkLabel(self.main_frame, text="Errors: None")
        self.error_label.pack()

        # Метка для результатов RAM
        self.ram_result_label = ctk.CTkLabel(self.main_frame, text="RAM Test Results: N/A")
        self.ram_result_label.pack()

        # Запуск мониторинга
        self.start_monitoring()

    def update_metrics(self, cpu_usage, cpu_freq, cpu_temp, ram_info, disk_usage, disk_io, gpu_info):
        logging.debug(f"Updating metrics: CPU={cpu_usage}, Freq={cpu_freq}, Temp={cpu_temp}, RAM={ram_info}, Disk={disk_usage}, IO={disk_io}, GPU={gpu_info}")
        # Средняя загрузка CPU и GPU для графика
        avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
        self.cpu_history.append(avg_cpu)
        gpu_usage = gpu_info['usage'] if isinstance(gpu_info['usage'], (int, float)) else 0
        self.gpu_history.append(gpu_usage)
        self.time_history.append(len(self.cpu_history))

        # Обновление графика
        self.ax.clear()
        self.ax.plot(self.time_history, self.cpu_history, label="CPU Usage (%)")
        self.ax.plot(self.time_history, self.gpu_history, label="GPU Usage (%)")
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Usage (%)")
        self.ax.legend()
        self.canvas.draw()
        logging.debug("Graph updated")

        # Обновление метрик
        cpu_text = f"CPU Usage: {cpu_usage}"
        cpu_freq_text = f"CPU Freq: {cpu_freq} MHz"
        cpu_temp_text = f"CPU Temp: {cpu_temp}°C"
        ram_text = f"RAM: {ram_info['percent']}% (Used: {ram_info['used']:.2f} GB, Free: {ram_info['free']:.2f} GB)"
        disk_text = f"Disk: {disk_usage['percent']}% (Used: {disk_usage['used']:.2f} GB, Free: {disk_usage['free']:.2f} GB)"
        disk_io_text = f"Disk IO: Read {disk_io['read_bytes']:.2f} MB, Write {disk_io['write_bytes']:.2f} MB"
        gpu_text = f"GPU Usage: {gpu_info['usage']}%, Temp: {gpu_info['temp']}°C"
        self.cpu_label.configure(text=cpu_text)
        self.cpu_freq_label.configure(text=cpu_freq_text)
        self.cpu_temp_label.configure(text=cpu_temp_text)
        self.ram_label.configure(text=ram_text)
        self.disk_label.configure(text=disk_text)
        self.disk_io_label.configure(text=disk_io_text)
        self.gpu_label.configure(text=gpu_text)

        # Проверка ошибок
        errors = self.diagnostics.check_hardware() + self.stress.get_errors()
        self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

        # Логирование метрик
        with open("metrics.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([time.time(), avg_cpu, ram_info["percent"], disk_usage["percent"],
                           disk_io["read_bytes"], disk_io["write_bytes"], gpu_usage])
        logging.debug("Metrics logged")

    def run_stress_test(self):
        logging.info("Starting stress test")
        self.start_button.configure(state="disabled")
        self.progress_label.configure(text="Test Progress: Running...")
        tests = []
        if self.cpu_test_var.get():
            tests.append(threading.Thread(target=self.stress.cpu_stress, args=(10,), daemon=True))
        if self.ram_test_var.get():
            ram_thread = threading.Thread(target=self.run_ram_stress_with_result, args=(10, 128), daemon=True)
            tests.append(ram_thread)
        if self.disk_test_var.get():
            tests.append(threading.Thread(target=self.stress.disk_stress, args=(10, 100), daemon=True))
        if self.gpu_test_var.get() and 'NVIDIA' in subprocess.getoutput('lspci'):
            tests.append(threading.Thread(target=self.stress.gpu_stress, args=(10,), daemon=True))

        for test in tests:
            test.start()
        self.root.after(10000, self.finish_stress_test)

    def finish_stress_test(self):
        logging.info("Stress test completed")
        self.start_button.configure(state="normal")
        self.progress_label.configure(text="Test Progress: Completed")

    def run_ram_stress_with_result(self, duration, size_mb):
        """Запускает тест RAM и отображает результаты."""
        speed, latency = self.stress.ram_stress(duration, size_mb)
        if speed and latency:
            self.ram_result_label.configure(text=f"RAM Test Results: Speed: {speed:.2f} MB/s, Latency: {latency:.2f} ms")
        logging.debug(f"RAM test results: Speed={speed}, Latency={latency}")

    def start_monitoring(self):
        logging.info("Starting monitoring")
        def callback(cpu, cpu_freq, cpu_temp, ram, disk, io, gpu):
            self.update_metrics(cpu, cpu_freq, cpu_temp, ram, disk, io, gpu)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback, 1), daemon=True).start()