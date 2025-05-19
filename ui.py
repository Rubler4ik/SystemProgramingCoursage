# ui.py
import customtkinter as ctk
from monitor import SystemMonitor
from stress_test import StressTest
from diagnostics import Diagnostics
from smart import SMARTMonitor
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import csv
import time
import logging
import os

logging.basicConfig(filename='ui.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainApp:
    def __init__(self, root):
        self.root = root
        self.monitor = SystemMonitor()
        self.diagnostics = Diagnostics()
        self.metrics = {
            "CPU Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "CPU Freq (MHz)": {"min": float("inf"), "current": 0, "max": 0},
            "CPU Temp (°C)": {"min": float("inf"), "current": 0, "max": 0},
            "RAM Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "RAM Used (GB)": {"min": float("inf"), "current": 0, "max": 0},
            "RAM Freq (MHz)": {"min": float("inf"), "current": 0, "max": 0},
            "Disk Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "Disk Read (MB)": {"min": float("inf"), "current": 0, "max": 0},
            "Disk Write (MB)": {"min": float("inf"), "current": 0, "max": 0},
            "GPU Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "GPU Memory (%)": {"min": float("inf"), "current": 0, "max": 0},
            "GPU Temp (°C)": {"min": float("inf"), "current": 0, "max": 0},
            "Net Sent (MB)": {"min": float("inf"), "current": 0, "max": 0},
            "Net Recv (MB)": {"min": float("inf"), "current": 0, "max": 0},
            "Power (W)": {"min": float("inf"), "current": 0, "max": 0}
        }
        self.fan_speeds = {}
        self.top_processes = []
        self.is_running = True
        self.after_ids = []
        self.root.bind("<Configure>", self.on_configure)
        self.setup_ui()
        self.start_monitoring()

    def on_configure(self, event):
        if hasattr(self.root, 'master') and hasattr(self.root.master, 'canvas'):
            self.root.master.canvas.configure(scrollregion=self.root.master.canvas.bbox("all"))

    def on_closing(self):
        self.is_running = False
        self.monitor.stop()
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        if hasattr(self.root, 'master'):
            self.root.master.after(100, self.root.master.destroy)
        else:
            self.root.after(100, self.root.destroy)

    def setup_ui(self):
        menubar = ctk.CTkFrame(self.root)
        menubar.pack(fill="x")
        stress_menu = ctk.CTkOptionMenu(menubar, values=["CPU Test", "RAM Test", "Disk Test", "GPU Test", "S.M.A.R.T. Monitor"],
                                        command=self.open_test_window)
        stress_menu.pack(side="left", padx=5, pady=5)

        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(self.metrics_frame, text="Metric", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Min", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Current", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Max", font=("Roboto", 12, "bold")).grid(row=0, column=3, padx=5, pady=2)

        self.metric_labels = {}
        for i, metric in enumerate(self.metrics):
            ctk.CTkLabel(self.metrics_frame, text=metric, font=("Roboto", 12)).grid(row=i+1, column=0, padx=5, pady=2)
            self.metric_labels[metric] = {
                "min": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "current": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "max": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12))
            }
            self.metric_labels[metric]["min"].grid(row=i+1, column=1, padx=5, pady=2)
            self.metric_labels[metric]["current"].grid(row=i+1, column=2, padx=5, pady=2)
            self.metric_labels[metric]["max"].grid(row=i+1, column=3, padx=5, pady=2)

        self.fan_frame = ctk.CTkFrame(self.main_frame)
        self.fan_frame.pack(pady=5, fill="x")
        self.fan_label = ctk.CTkLabel(self.fan_frame, text="Fan Speeds: N/A", font=("Roboto", 12))
        self.fan_label.pack()

        self.process_frame = ctk.CTkFrame(self.main_frame)
        self.process_frame.pack(pady=5, fill="x")
        self.process_label = ctk.CTkLabel(self.process_frame, text="Top Processes: N/A", font=("Roboto", 12))
        self.process_label.pack()

        self.error_frame = ctk.CTkFrame(self.main_frame)
        self.error_frame.pack(pady=5, fill="x")
        self.error_label = ctk.CTkLabel(self.error_frame, text="Errors: None", font=("Roboto", 12))
        self.error_label.pack()

    def open_test_window(self, test_name):
        window = ctk.CTkToplevel(self.root)
        window.title(test_name)
        try:
            if test_name == "CPU Test":
                CPUWindow(window)
            elif test_name == "RAM Test":
                RAMWindow(window)
            elif test_name == "Disk Test":
                DiskWindow(window)
            elif test_name == "GPU Test":
                GPUWindow(window)
            elif test_name == "S.M.A.R.T. Monitor":
                SMARTWindow(window)
        except Exception as e:
            logging.error(f"Error opening test window {test_name}: {str(e)}")
            window.destroy()

    def update_metrics(self, cpu_usage, cpu_freq, cpu_temp, fan_speeds, ram_info, ram_freq, disk_usage, disk_io, gpu_info, net_info, power_info, top_processes):
        if not self.is_running:
            return
        def update():
            if not self.is_running:
                return
            try:
                self.metrics["CPU Usage (%)"]["current"] = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
                self.metrics["CPU Freq (MHz)"]["current"] = float(cpu_freq) if cpu_freq != "N/A" else 0
                self.metrics["CPU Temp (°C)"]["current"] = float(cpu_temp) if cpu_temp != "N/A" else 0
                self.metrics["RAM Usage (%)"]["current"] = ram_info["percent"]
                self.metrics["RAM Used (GB)"]["current"] = ram_info["used"]
                self.metrics["RAM Freq (MHz)"]["current"] = float(ram_freq) if ram_freq != "N/A" else 0
                self.metrics["Disk Usage (%)"]["current"] = disk_usage["percent"]
                self.metrics["Disk Read (MB)"]["current"] = disk_io["read_bytes"]
                self.metrics["Disk Write (MB)"]["current"] = disk_io["write_bytes"]
                self.metrics["GPU Usage (%)"]["current"] = float(gpu_info["usage"]) if gpu_info["usage"] != "N/A" else 0
                self.metrics["GPU Memory (%)"]["current"] = float(gpu_info["memory"]) if gpu_info["memory"] != "N/A" else 0
                self.metrics["GPU Temp (°C)"]["current"] = float(gpu_info["temp"]) if gpu_info["temp"] != "N/A" else 0
                self.metrics["Net Sent (MB)"]["current"] = net_info["bytes_sent"]
                self.metrics["Net Recv (MB)"]["current"] = net_info["bytes_recv"]
                self.metrics["Power (W)"]["current"] = float(power_info) if power_info != "N/A" else 0

                for metric in self.metrics:
                    if self.metrics[metric]["current"] < self.metrics[metric]["min"]:
                        self.metrics[metric]["min"] = self.metrics[metric]["current"]
                    if self.metrics[metric]["current"] > self.metrics[metric]["max"]:
                        self.metrics[metric]["max"] = self.metrics[metric]["current"]
                    self.metric_labels[metric]["min"].configure(text=f"{self.metrics[metric]['min']:.1f}")
                    self.metric_labels[metric]["current"].configure(text=f"{self.metrics[metric]['current']:.1f}")
                    self.metric_labels[metric]["max"].configure(text=f"{self.metrics[metric]['max']:.1f}")

                self.fan_speeds = fan_speeds
                fan_text = ", ".join([f"{k}: {v} RPM" for k, v in fan_speeds.items()])
                self.fan_label.configure(text=f"Fan Speeds: {fan_text if fan_text else 'N/A'}")

                self.top_processes = top_processes
                process_text = "\n".join([f"{p['name']}: CPU={p['cpu']:.1f}%, RAM={p['memory']:.1f}%" for p in top_processes])
                self.process_label.configure(text=f"Top Processes: {process_text or 'N/A'}")

                errors = self.diagnostics.check_hardware()
                self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

                with open(os.path.join("metrics.csv"), "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time()] + [self.metrics[m]["current"] for m in self.metrics])
            except Exception as e:
                logging.error(f"Main update_metrics error: {str(e)}")
        after_id = self.root.after(0, update)
        self.after_ids.append(after_id)

    def start_monitoring(self):
        def callback(cpu_usage, cpu_freq, cpu_temp, fan_speeds, ram_info, ram_freq, disk_usage, disk_io, gpu_info, net_info, power_info, top_processes):
            if self.is_running:
                self.update_metrics(cpu_usage, cpu_freq, cpu_temp, fan_speeds, ram_info, ram_freq, disk_usage, disk_io, gpu_info, net_info, power_info, top_processes)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback, 1), daemon=True).start()

class CPUWindow:
    def __init__(self, root):
        self.root = root
        self.monitor = SystemMonitor()
        self.stress = StressTest()
        self.diagnostics = Diagnostics()
        self.cpu_history = collections.deque(maxlen=30)
        self.time_history = collections.deque(maxlen=30)
        self.metrics = {
            "Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "Frequency (MHz)": {"min": float("inf"), "current": 0, "max": 0},
            "Temperature (°C)": {"min": float("inf"), "current": 0, "max": 0}
        }
        self.fan_speeds = {}
        self.is_running = True
        self.after_ids = []
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        self.start_monitoring()

    def on_closing(self):
        self.is_running = False
        self.monitor.stop()
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        self.root.after(100, self.root.destroy)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(pady=10)

        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(self.metrics_frame, text="Metric", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Min", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Current", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Max", font=("Roboto", 12, "bold")).grid(row=0, column=3, padx=5, pady=2)

        self.metric_labels = {}
        for i, metric in enumerate(self.metrics):
            ctk.CTkLabel(self.metrics_frame, text=metric, font=("Roboto", 12)).grid(row=i+1, column=0, padx=5, pady=2)
            self.metric_labels[metric] = {
                "min": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "current": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "max": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12))
            }
            self.metric_labels[metric]["min"].grid(row=i+1, column=1, padx=5, pady=2)
            self.metric_labels[metric]["current"].grid(row=i+1, column=2, padx=5, pady=2)
            self.metric_labels[metric]["max"].grid(row=i+1, column=3, padx=5, pady=2)

        self.fan_frame = ctk.CTkFrame(self.main_frame)
        self.fan_frame.pack(pady=5, fill="x")
        self.fan_label = ctk.CTkLabel(self.fan_frame, text="Fan Speeds: N/A", font=("Roboto", 12))
        self.fan_label.pack()

        self.start_button = ctk.CTkButton(self.main_frame, text="Start Stress Test (10s)", command=self.run_stress_test, font=("Roboto", 12))
        self.start_button.pack(pady=5)
        self.progress_label = ctk.CTkLabel(self.main_frame, text="Test Progress: Idle", font=("Roboto", 12))
        self.progress_label.pack()
        self.error_label = ctk.CTkLabel(self.main_frame, text="Errors: None", font=("Roboto", 12))
        self.error_label.pack()

    def update_metrics(self, cpu_usage, cpu_freq, cpu_temp, fan_speeds):
        if not self.is_running:
            return
        def update():
            if not self.is_running:
                return
            try:
                avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
                self.cpu_history.append(avg_cpu)
                self.time_history.append(len(self.cpu_history))

                self.ax.clear()
                self.ax.plot(self.time_history, self.cpu_history, label="CPU Usage (%)", color="green")
                self.ax.set_ylim(0, 100)
                self.ax.set_xlabel("Time (s)")
                self.ax.set_ylabel("Usage (%)")
                self.ax.legend()
                self.canvas.draw()

                self.metrics["Usage (%)"]["current"] = avg_cpu
                self.metrics["Frequency (MHz)"]["current"] = float(cpu_freq) if cpu_freq != "N/A" else 0
                self.metrics["Temperature (°C)"]["current"] = float(cpu_temp) if cpu_temp != "N/A" else 0

                for metric in self.metrics:
                    if self.metrics[metric]["current"] < self.metrics[metric]["min"]:
                        self.metrics[metric]["min"] = self.metrics[metric]["current"]
                    if self.metrics[metric]["current"] > self.metrics[metric]["max"]:
                        self.metrics[metric]["max"] = self.metrics[metric]["current"]
                    self.metric_labels[metric]["min"].configure(text=f"{self.metrics[metric]['min']:.1f}")
                    self.metric_labels[metric]["current"].configure(text=f"{self.metrics[metric]['current']:.1f}")
                    self.metric_labels[metric]["max"].configure(text=f"{self.metrics[metric]['max']:.1f}")

                self.fan_speeds = fan_speeds
                fan_text = ", ".join([f"{k}: {v} RPM" for k, v in fan_speeds.items()])
                self.fan_label.configure(text=f"Fan Speeds: {fan_text}")

                errors = self.diagnostics.check_hardware() + self.stress.get_errors()
                self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

                with open(os.path.join("cpu_metrics.csv"), "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time(), avg_cpu, cpu_freq, cpu_temp])
            except Exception as e:
                logging.error(f"CPU update_metrics error: {str(e)}")
        after_id = self.root.after(0, update)
        self.after_ids.append(after_id)

    def run_stress_test(self):
        logging.info("Starting CPU stress test")
        self.start_button.configure(state="disabled")
        self.progress_label.configure(text="Test Progress: Running...")
        threading.Thread(target=self.stress.cpu_stress, args=(10, 2000), daemon=True).start()
        self.root.after(10000, self.finish_stress_test)

    def finish_stress_test(self):
        logging.info("CPU stress test completed")
        self.start_button.configure(state="normal")
        self.progress_label.configure(text="Test Progress: Completed")

    def start_monitoring(self):
        def callback(*args):
            cpu_usage = args[0] if len(args) > 0 else []
            cpu_freq = args[1] if len(args) > 1 else "N/A"
            cpu_temp = args[2] if len(args) > 2 else "N/A"
            fan_speeds = args[3] if len(args) > 3 else {}
            if self.is_running:
                self.update_metrics(cpu_usage, cpu_freq, cpu_temp, fan_speeds)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback, 1), daemon=True).start()

class RAMWindow:
    def __init__(self, root):
        self.root = root
        self.monitor = SystemMonitor()
        self.stress = StressTest()
        self.diagnostics = Diagnostics()
        self.ram_history = collections.deque(maxlen=30)
        self.time_history = collections.deque(maxlen=30)
        self.metrics = {
            "Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "Used (GB)": {"min": float("inf"), "current": 0, "max": 0},
            "Frequency (MHz)": {"min": float("inf"), "current": 0, "max": 0}
        }
        self.is_running = True
        self.after_ids = []
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        self.start_monitoring()

    def on_closing(self):
        self.is_running = False
        self.monitor.stop()
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        self.root.after(100, self.root.destroy)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(pady=10)

        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(self.metrics_frame, text="Metric", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Min", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Current", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Max", font=("Roboto", 12, "bold")).grid(row=0, column=3, padx=5, pady=2)

        self.metric_labels = {}
        for i, metric in enumerate(self.metrics):
            ctk.CTkLabel(self.metrics_frame, text=metric, font=("Roboto", 12)).grid(row=i+1, column=0, padx=5, pady=2)
            self.metric_labels[metric] = {
                "min": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "current": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "max": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12))
            }
            self.metric_labels[metric]["min"].grid(row=i+1, column=1, padx=5, pady=2)
            self.metric_labels[metric]["current"].grid(row=i+1, column=2, padx=5, pady=2)
            self.metric_labels[metric]["max"].grid(row=i+1, column=3, padx=5, pady=2)

        self.start_button = ctk.CTkButton(self.main_frame, text="Start Stress Test (10s)", command=self.run_stress_test, font=("Roboto", 12))
        self.start_button.pack(pady=5)
        self.progress_label = ctk.CTkLabel(self.main_frame, text="Test Progress: Idle", font=("Roboto", 12))
        self.progress_label.pack()
        self.error_label = ctk.CTkLabel(self.main_frame, text="Errors: None", font=("Roboto", 12))
        self.error_label.pack()
        self.result_label = ctk.CTkLabel(self.main_frame, text="RAM Test Results: N/A", font=("Roboto", 12))
        self.result_label.pack()

    def update_metrics(self, ram_info, ram_freq):
        if not self.is_running:
            return
        def update():
            if not self.is_running:
                return
            try:
                self.ram_history.append(ram_info["percent"])
                self.time_history.append(len(self.ram_history))

                self.ax.clear()
                self.ax.plot(self.time_history, self.ram_history, label="RAM Usage (%)", color="green")
                self.ax.set_ylim(0, 100)
                self.ax.set_xlabel("Time (s)")
                self.ax.set_ylabel("Usage (%)")
                self.ax.legend()
                self.canvas.draw()

                self.metrics["Usage (%)"]["current"] = ram_info["percent"]
                self.metrics["Used (GB)"]["current"] = ram_info["used"]
                self.metrics["Frequency (MHz)"]["current"] = float(ram_freq) if ram_freq != "N/A" else 0

                for metric in self.metrics:
                    if self.metrics[metric]["current"] < self.metrics[metric]["min"]:
                        self.metrics[metric]["min"] = self.metrics[metric]["current"]
                    if self.metrics[metric]["current"] > self.metrics[metric]["max"]:
                        self.metrics[metric]["max"] = self.metrics[metric]["current"]
                    self.metric_labels[metric]["min"].configure(text=f"{self.metrics[metric]['min']:.1f}")
                    self.metric_labels[metric]["current"].configure(text=f"{self.metrics[metric]['current']:.1f}")
                    self.metric_labels[metric]["max"].configure(text=f"{self.metrics[metric]['max']:.1f}")

                errors = self.diagnostics.check_hardware() + self.stress.get_errors()
                self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

                with open(os.path.join("ram_metrics.csv"), "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time(), ram_info["percent"], ram_info["used"], ram_freq])
            except Exception as e:
                logging.error(f"RAM update_metrics error: {str(e)}")
        after_id = self.root.after(0, update)
        self.after_ids.append(after_id)

    def run_stress_test(self):
        logging.info("Starting RAM stress test")
        self.start_button.configure(state="disabled")
        self.progress_label.configure(text="Test Progress: Running...")
        threading.Thread(target=self.run_ram_stress_with_result, args=(10, 128), daemon=True).start()
        self.root.after(10000, self.finish_stress_test)

    def finish_stress_test(self):
        logging.info("RAM stress test completed")
        self.start_button.configure(state="normal")
        self.progress_label.configure(text="Test Progress: Completed")

    def run_ram_stress_with_result(self, duration, size_mb):
        seq_speed, seq_latency, rand_speed, rand_latency = self.stress.ram_stress(duration, size_mb)
        if not self.is_running:
            return
        def update_result():
            if not self.is_running:
                return
            try:
                if seq_speed:
                    self.result_label.configure(
                        text=f"RAM Test Results: Seq Speed: {seq_speed:.2f} MB/s, Seq Latency: {seq_latency:.2f} ms, "
                             f"Rand Speed: {rand_speed:.2f} MB/s, Rand Latency: {rand_latency:.2f} ms")
                logging.debug(f"RAM test results: Seq Speed={seq_speed}, Seq Latency={seq_latency}, "
                              f"Rand Speed={rand_speed}, Rand Latency={rand_latency}")
            except Exception as e:
                logging.error(f"RAM result update error: {str(e)}")
        after_id = self.root.after(0, update_result)
        self.after_ids.append(after_id)

    def start_monitoring(self):
        def callback(*args):
            ram_info = args[4] if len(args) > 4 else {}
            ram_freq = args[5] if len(args) > 5 else "N/A"
            if self.is_running:
                self.update_metrics(ram_info, ram_freq)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback, 1), daemon=True).start()

class DiskWindow:
    def __init__(self, root):
        self.root = root
        self.monitor = SystemMonitor()
        self.stress = StressTest()
        self.diagnostics = Diagnostics()
        self.disk_history = collections.deque(maxlen=30)
        self.time_history = collections.deque(maxlen=30)
        self.metrics = {
            "Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "Read (MB)": {"min": float("inf"), "current": 0, "max": 0},
            "Write (MB)": {"min": float("inf"), "current": 0, "max": 0}
        }
        self.is_running = True
        self.after_ids = []
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        self.start_monitoring()

    def on_closing(self):
        self.is_running = False
        self.monitor.stop()
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        self.root.after(100, self.root.destroy)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(pady=10)

        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(self.metrics_frame, text="Metric", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Min", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Current", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Max", font=("Roboto", 12, "bold")).grid(row=0, column=3, padx=5, pady=2)

        self.metric_labels = {}
        for i, metric in enumerate(self.metrics):
            ctk.CTkLabel(self.metrics_frame, text=metric, font=("Roboto", 12)).grid(row=i+1, column=0, padx=5, pady=2)
            self.metric_labels[metric] = {
                "min": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "current": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "max": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12))
            }
            self.metric_labels[metric]["min"].grid(row=i+1, column=1, padx=5, pady=2)
            self.metric_labels[metric]["current"].grid(row=i+1, column=2, padx=5, pady=2)
            self.metric_labels[metric]["max"].grid(row=i+1, column=3, padx=5, pady=2)

        self.start_button = ctk.CTkButton(self.main_frame, text="Start Stress Test (10s)", command=self.run_stress_test, font=("Roboto", 12))
        self.start_button.pack(pady=5)
        self.progress_label = ctk.CTkLabel(self.main_frame, text="Test Progress: Idle", font=("Roboto", 12))
        self.progress_label.pack()
        self.error_label = ctk.CTkLabel(self.main_frame, text="Errors: None", font=("Roboto", 12))
        self.error_label.pack()
        self.result_label = ctk.CTkLabel(self.main_frame, text="Disk Test Results: N/A", font=("Roboto", 12))
        self.result_label.pack()

    def update_metrics(self, disk_usage, disk_io):
        if not self.is_running:
            return
        def update():
            if not self.is_running:
                return
            try:
                self.disk_history.append(disk_io["read_bytes"] + disk_io["write_bytes"])
                self.time_history.append(len(self.disk_history))

                self.ax.clear()
                self.ax.plot(self.time_history, self.disk_history, label="Disk IO (MB)", color="green")
                self.ax.set_xlabel("Time (s)")
                self.ax.set_ylabel("IO (MB)")
                self.ax.legend()
                self.canvas.draw()

                self.metrics["Usage (%)"]["current"] = disk_usage["percent"]
                self.metrics["Read (MB)"]["current"] = disk_io["read_bytes"]
                self.metrics["Write (MB)"]["current"] = disk_io["write_bytes"]

                for metric in self.metrics:
                    if self.metrics[metric]["current"] < self.metrics[metric]["min"]:
                        self.metrics[metric]["min"] = self.metrics[metric]["current"]
                    if self.metrics[metric]["current"] > self.metrics[metric]["max"]:
                        self.metrics[metric]["max"] = self.metrics[metric]["current"]
                    self.metric_labels[metric]["min"].configure(text=f"{self.metrics[metric]['min']:.1f}")
                    self.metric_labels[metric]["current"].configure(text=f"{self.metrics[metric]['current']:.1f}")
                    self.metric_labels[metric]["max"].configure(text=f"{self.metrics[metric]['max']:.1f}")

                errors = self.diagnostics.check_hardware() + self.stress.get_errors()
                self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

                with open(os.path.join("disk_metrics.csv"), "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time(), disk_usage["percent"], disk_io["read_bytes"], disk_io["write_bytes"]])
            except Exception as e:
                logging.error(f"Disk update_metrics error: {str(e)}")
        after_id = self.root.after(0, update)
        self.after_ids.append(after_id)

    def run_stress_test(self):
        logging.info("Starting Disk stress test")
        self.start_button.configure(state="disabled")
        self.progress_label.configure(text="Test Progress: Running...")
        threading.Thread(target=self.run_disk_stress_with_result, args=(10, 100), daemon=True).start()
        self.root.after(10000, self.finish_stress_test)

    def finish_stress_test(self):
        logging.info("Disk stress test completed")
        self.start_button.configure(state="normal")
        self.progress_label.configure(text="Test Progress: Completed")

    def run_disk_stress_with_result(self, duration, file_size_mb):
        results = self.stress.disk_stress(duration, file_size_mb)
        if not self.is_running:
            return
        def update_result():
            if not self.is_running:
                return
            try:
                if results["seq_q32t1_read"]:
                    self.result_label.configure(
                        text=f"Disk Test Results:\n"
                             f"Seq Q32T1 Read: {results['seq_q32t1_read']:.2f} MB/s, Write: {results['seq_q32t1_write']:.2f} MB/s\n"
                             f"4K Q32T1 Read: {results['4k_q32t1_read']:.2f} MB/s, Write: {results['4k_q32t1_write']:.2f} MB/s\n"
                             f"Seq Read: {results['seq_read']:.2f} MB/s, Write: {results['seq_write']:.2f} MB/s\n"
                             f"4K Q1T1 Read: {results['4k_q1t1_read']:.2f} MB/s, Write: {results['4k_q1t1_write']:.2f} MB/s")
                logging.debug(f"Disk test results: {results}")
            except Exception as e:
                logging.error(f"Disk result update error: {str(e)}")
        after_id = self.root.after(0, update_result)
        self.after_ids.append(after_id)

    def start_monitoring(self):
        def callback(*args):
            disk_usage = args[6] if len(args) > 6 else {}
            disk_io = args[7] if len(args) > 7 else {}
            if self.is_running:
                self.update_metrics(disk_usage, disk_io)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback, 1), daemon=True).start()

class GPUWindow:
    def __init__(self, root):
        self.root = root
        self.monitor = SystemMonitor()
        self.stress = StressTest()
        self.diagnostics = Diagnostics()
        self.gpu_history = collections.deque(maxlen=30)
        self.time_history = collections.deque(maxlen=30)
        self.metrics = {
            "Usage (%)": {"min": float("inf"), "current": 0, "max": 0},
            "Memory (%)": {"min": float("inf"), "current": 0, "max": 0},
            "Temperature (°C)": {"min": float("inf"), "current": 0, "max": 0}
        }
        self.is_running = True
        self.after_ids = []
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        self.start_monitoring()

    def on_closing(self):
        self.is_running = False
        self.monitor.stop()
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        self.root.after(100, self.root.destroy)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(pady=10)

        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(self.metrics_frame, text="Metric", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Min", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Current", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.metrics_frame, text="Max", font=("Roboto", 12, "bold")).grid(row=0, column=3, padx=5, pady=2)

        self.metric_labels = {}
        for i, metric in enumerate(self.metrics):
            ctk.CTkLabel(self.metrics_frame, text=metric, font=("Roboto", 12)).grid(row=i+1, column=0, padx=5, pady=2)
            self.metric_labels[metric] = {
                "min": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "current": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12)),
                "max": ctk.CTkLabel(self.metrics_frame, text="N/A", font=("Roboto", 12))
            }
            self.metric_labels[metric]["min"].grid(row=i+1, column=1, padx=5, pady=2)
            self.metric_labels[metric]["current"].grid(row=i+1, column=2, padx=5, pady=2)
            self.metric_labels[metric]["max"].grid(row=i+1, column=3, padx=5, pady=2)

        self.start_button = ctk.CTkButton(self.main_frame, text="Start Stress Test (10s)", command=self.run_stress_test, font=("Roboto", 12))
        self.start_button.pack(pady=5)
        self.progress_label = ctk.CTkLabel(self.main_frame, text="Test Progress: Idle", font=("Roboto", 12))
        self.progress_label.pack()
        self.error_label = ctk.CTkLabel(self.main_frame, text="Errors: None", font=("Roboto", 12))
        self.error_label.pack()

    def update_metrics(self, gpu_info):
        if not self.is_running:
            return
        def update():
            if not self.is_running:
                return
            try:
                gpu_usage = float(gpu_info["usage"]) if gpu_info["usage"] != "N/A" else 0
                self.gpu_history.append(gpu_usage)
                self.time_history.append(len(self.gpu_history))

                self.ax.clear()
                self.ax.plot(self.time_history, self.gpu_history, label="GPU Usage (%)", color="green")
                self.ax.set_ylim(0, 100)
                self.ax.set_xlabel("Time (s)")
                self.ax.set_ylabel("Usage (%)")
                self.ax.legend()
                self.canvas.draw()

                self.metrics["Usage (%)"]["current"] = gpu_usage
                self.metrics["Memory (%)"]["current"] = float(gpu_info["memory"]) if gpu_info["memory"] != "N/A" else 0
                self.metrics["Temperature (°C)"]["current"] = float(gpu_info["temp"]) if gpu_info["temp"] != "N/A" else 0

                for metric in self.metrics:
                    if self.metrics[metric]["current"] < self.metrics[metric]["min"]:
                        self.metrics[metric]["min"] = self.metrics[metric]["current"]
                    if self.metrics[metric]["current"] > self.metrics[metric]["max"]:
                        self.metrics[metric]["max"] = self.metrics[metric]["current"]
                    self.metric_labels[metric]["min"].configure(text=f"{self.metrics[metric]['min']:.1f}")
                    self.metric_labels[metric]["current"].configure(text=f"{self.metrics[metric]['current']:.1f}")
                    self.metric_labels[metric]["max"].configure(text=f"{self.metrics[metric]['max']:.1f}")

                errors = self.diagnostics.check_hardware() + self.stress.get_errors()
                self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

                with open(os.path.join("gpu_metrics.csv"), "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time(), gpu_info["usage"], gpu_info["memory"], gpu_info["temp"]])
            except Exception as e:
                logging.error(f"GPU update_metrics error: {str(e)}")
        after_id = self.root.after(0, update)
        self.after_ids.append(after_id)

    def run_stress_test(self):
        logging.info("Starting GPU stress test")
        self.start_button.configure(state="disabled")
        self.progress_label.configure(text="Test Progress: Running...")
        threading.Thread(target=self.stress.gpu_stress, args=(10,), daemon=True).start()
        self.root.after(10000, self.finish_stress_test)

    def finish_stress_test(self):
        logging.info("GPU stress test completed")
        self.start_button.configure(state="normal")
        self.progress_label.configure(text="Test Progress: Completed")

    def start_monitoring(self):
        def callback(*args):
            gpu_info = args[8] if len(args) > 8 else {}
            if self.is_running:
                self.update_metrics(gpu_info)
        threading.Thread(target=self.monitor.monitor_loop, args=(callback, 1), daemon=True).start()

class SMARTWindow:
    def __init__(self, root):
        self.root = root
        self.smart = SMARTMonitor()
        self.is_running = True
        self.after_ids = []
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        self.start_monitoring()

    def on_closing(self):
        self.is_running = False
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        self.root.after(100, self.root.destroy)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.smart_frame = ctk.CTkFrame(self.main_frame)
        self.smart_frame.pack(pady=5, fill="x")
        self.smart_label = ctk.CTkLabel(self.smart_frame, text="S.M.A.R.T.: Collecting data...", font=("Roboto", 12))
        self.smart_label.pack()

        self.error_label = ctk.CTkLabel(self.main_frame, text="Errors: None", font=("Roboto", 12))
        self.error_label.pack()

        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.pack(pady=5, fill="x")
        headers = ["Disk", "Temperature (°C)", "Health", "Reallocated Sectors", "Wear Level"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(self.metrics_frame, text=header, font=("Roboto", 12, "bold")).grid(row=0, column=i, padx=5, pady=2)

        self.disk_labels = {}

    def update_metrics(self):
        if not self.is_running:
            return
        def update():
            if not self.is_running:
                return
            try:
                smart_data = self.smart.get_smart_data()

                for disk in self.disk_labels:
                    for label in self.disk_labels[disk].values():
                        label.destroy()
                self.disk_labels.clear()

                row = 1
                for disk, data in smart_data.items():
                    self.disk_labels[disk] = {
                        "name": ctk.CTkLabel(self.metrics_frame, text=disk, font=("Roboto", 12)),
                        "temp": ctk.CTkLabel(self.metrics_frame, text=data["temperature"], font=("Roboto", 12)),
                        "health": ctk.CTkLabel(self.metrics_frame, text=data["health_status"], font=("Roboto", 12)),
                        "reallocated": ctk.CTkLabel(self.metrics_frame, text=data["reallocated_sectors"], font=("Roboto", 12)),
                        "wear": ctk.CTkLabel(self.metrics_frame, text=data["wear_level"], font=("Roboto", 12))
                    }
                    self.disk_labels[disk]["name"].grid(row=row, column=0, padx=5, pady=2)
                    self.disk_labels[disk]["temp"].grid(row=row, column=1, padx=5, pady=2)
                    self.disk_labels[disk]["health"].grid(row=row, column=2, padx=5, pady=2)
                    self.disk_labels[disk]["reallocated"].grid(row=row, column=3, padx=5, pady=2)
                    self.disk_labels[disk]["wear"].grid(row=row, column=4, padx=5, pady=2)
                    row += 1

                smart_text = "\n".join([
                    f"{disk}: Temp={data['temperature']}°C, Health={data['health_status']}, "
                    f"Reallocated={data['reallocated_sectors']}, Wear={data['wear_level']}"
                    for disk, data in smart_data.items()
                ])
                self.smart_label.configure(text=f"S.M.A.R.T.:\n{smart_text or 'No data available'}")
                logging.debug(f"SMARTWindow updated: {smart_text}")

                errors = []
                if not smart_data:
                    errors.append("No S.M.A.R.T. data available")
                self.error_label.configure(text=f"Errors: {', '.join(errors) if errors else 'None'}")

                with open(os.path.join("smart_metrics.csv"), "a", newline="") as f:
                    writer = csv.writer(f)
                    for disk, data in smart_data.items():
                        writer.writerow([
                            time.time(),
                            disk,
                            data["temperature"],
                            data["health_status"],
                            data["reallocated_sectors"],
                            data["wear_level"]
                        ])
            except Exception as e:
                logging.error(f"SMART update_metrics error: {str(e)}")
                self.error_label.configure(text=f"Errors: S.M.A.R.T. monitoring failed: {str(e)}")
        after_id = self.root.after(0, update)
        self.after_ids.append(after_id)

    def start_monitoring(self):
        def monitor_loop():
            while self.is_running:
                self.update_metrics()
                time.sleep(5)
        threading.Thread(target=monitor_loop, daemon=True).start()