# diagnostics.py
import psutil
import logging
import platform
import subprocess

logging.basicConfig(filename='diagnostics.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Diagnostics:
    def check_hardware(self):
        errors = []
        try:
            # CPU
            cpu_usage = psutil.cpu_percent()
            if cpu_usage > 95:
                errors.append("High CPU usage detected")

            # RAM
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                errors.append("High RAM usage detected")

            # Disk
            disk = psutil.disk_usage("/")
            if disk.percent > 90:
                errors.append("Low disk space")

            # Temperature (Linux only)
            if platform.system() == "Linux":
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > 85:
                            errors.append(f"High temperature on {name}: {entry.current}°C")

            # GPU (Linux with nvidia-smi)
            if platform.system() == "Linux":
                try:
                    result = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv"],
                                           capture_output=True, text=True)
                    temp = int(result.stdout.splitlines()[1])
                    if temp > 85:
                        errors.append(f"High GPU temperature: {temp}°C")
                except Exception:
                    pass

        except Exception as e:
            errors.append(f"Diagnostics error: {str(e)}")
            logging.error(f"Diagnostics error: {str(e)}")
        return errors