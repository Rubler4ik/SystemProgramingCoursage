# monitor.py
import psutil
import subprocess
import time
import logging
import platform
import os

logging.basicConfig(filename='monitor.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemMonitor:
    def __init__(self):
        self.running = True
        self.net_io = psutil.net_io_counters()
        self.disk_io = psutil.disk_io_counters()

    def get_cpu_usage(self):
        return psutil.cpu_percent(percpu=True)

    def get_cpu_freq(self):
        try:
            freq = psutil.cpu_freq().current
            return f"{freq:.0f}" if freq else "N/A"
        except Exception as e:
            logging.error(f"get_cpu_freq error: {str(e)}")
            return "N/A"

    def get_cpu_temp(self):
        try:
            if platform.system() == "Linux":
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        if "coretemp" in name.lower() or "cpu" in entry.label.lower():
                            return f"{entry.current:.1f}"
            elif platform.system() == "Windows":
                # Требуется дополнительная библиотека, например, wmi
                return "N/A"
            return "N/A"
        except Exception as e:
            logging.error(f"get_cpu_temp error: {str(e)}")
            return "N/A"

    def get_fan_speeds(self):
        try:
            if platform.system() == "Linux":
                fans = psutil.sensors_fans()
                return {name: entry.current for name, entries in fans.items() for entry in entries}
            return {}
        except Exception as e:
            logging.error(f"get_fan_speeds error: {str(e)}")
            return {}

    def get_ram_info(self):
        try:
            mem = psutil.virtual_memory()
            return {
                "percent": mem.percent,
                "used": mem.used / (1024 ** 3)
            }
        except Exception as e:
            logging.error(f"get_ram_info error: {str(e)}")
            return {"percent": 0, "used": 0}

    def get_ram_freq(self):
        try:
            if platform.system() == "Linux":
                result = subprocess.run(["dmidecode", "-t", "17"], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    if "Speed" in line and "MHz" in line:
                        return line.split(":")[1].strip().split()[0]
            return "N/A"
        except Exception as e:
            logging.error(f"get_ram_freq error: {str(e)}")
            return "N/A"

    def get_disk_usage(self):
        try:
            disk = psutil.disk_usage("/")
            return {"percent": disk.percent}
        except Exception as e:
            logging.error(f"get_disk_usage error: {str(e)}")
            return {"percent": 0}

    def get_disk_io(self):
        try:
            new_io = psutil.disk_io_counters()
            read_bytes = (new_io.read_bytes - self.disk_io.read_bytes) / (1024 ** 2)
            write_bytes = (new_io.write_bytes - self.disk_io.write_bytes) / (1024 ** 2)
            self.disk_io = new_io
            return {"read_bytes": read_bytes, "write_bytes": write_bytes}
        except Exception as e:
            logging.error(f"get_disk_io error: {str(e)}")
            return {"read_bytes": 0, "write_bytes": 0}

    def get_gpu_info(self):
        try:
            if platform.system() == "Linux":
                result = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu", "--format=csv"],
                                       capture_output=True, text=True)
                lines = result.stdout.splitlines()
                if len(lines) > 1:
                    data = lines[1].split(", ")
                    return {
                        "usage": data[0].replace(" %", ""),
                        "memory": data[1].replace(" %", ""),
                        "temp": data[2]
                    }
            return {"usage": "N/A", "memory": "N/A", "temp": "N/A"}
        except Exception as e:
            logging.error(f"get_gpu_info error: {str(e)}")
            return {"usage": "N/A", "memory": "N/A", "temp": "N/A"}

    def get_net_info(self):
        try:
            new_io = psutil.net_io_counters()
            bytes_sent = (new_io.bytes_sent - self.net_io.bytes_sent) / (1024 ** 2)
            bytes_recv = (new_io.bytes_recv - self.net_io.bytes_recv) / (1024 ** 2)
            self.net_io = new_io
            return {"bytes_sent": bytes_sent, "bytes_recv": bytes_recv}
        except Exception as e:
            logging.error(f"get_net_info error: {str(e)}")
            return {"bytes_sent": 0, "bytes_recv": 0}

    def get_power_info(self):
        try:
            if platform.system() == "Linux":
                with open("/sys/class/power_supply/BAT0/power_now", "r") as f:
                    return f"{int(f.read()) / 1000000:.1f}"
            return "N/A"
        except Exception as e:
            logging.error(f"get_power_info error: {str(e)}")
            return "N/A"

    def get_top_processes(self):
        try:
            processes = []
            for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                processes.append({
                    "name": proc.info['name'],
                    "cpu": proc.info['cpu_percent'],
                    "memory": proc.info['memory_percent']
                })
            return sorted(processes, key=lambda x: x['cpu'], reverse=True)[:5]
        except Exception as e:
            logging.error(f"get_top_processes error: {str(e)}")
            return []

    def monitor_loop(self, callback, interval):
        while self.running:
            try:
                cpu_usage = self.get_cpu_usage()
                cpu_freq = self.get_cpu_freq()
                cpu_temp = self.get_cpu_temp()
                fan_speeds = self.get_fan_speeds()
                ram_info = self.get_ram_info()
                ram_freq = self.get_ram_freq()
                disk_usage = self.get_disk_usage()
                disk_io = self.get_disk_io()
                gpu_info = self.get_gpu_info()
                net_info = self.get_net_info()
                power_info = self.get_power_info()
                top_processes = self.get_top_processes()

                callback(cpu_usage, cpu_freq, cpu_temp, fan_speeds, ram_info, ram_freq, disk_usage, disk_io, gpu_info, net_info, power_info, top_processes)
            except Exception as e:
                logging.error(f"monitor_loop error: {str(e)}")
            time.sleep(interval)

    def stop(self):
        self.running = False