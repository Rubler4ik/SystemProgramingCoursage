import psutil
import time
import subprocess
import json
import logging

logging.basicConfig(filename='monitor.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemMonitor:
    def get_cpu_usage(self):
        """Возвращает загрузку CPU в процентах для каждого ядра."""
        try:
            usage = psutil.cpu_percent(interval=1, percpu=True)
            logging.debug(f"CPU usage: {usage}")
            return usage
        except Exception as e:
            logging.error(f"CPU usage error: {str(e)}")
            return [0] * psutil.cpu_count()

    def get_cpu_freq(self):
        """Возвращает частоту CPU."""
        try:
            freq = psutil.cpu_freq()
            result = freq.current if freq else "N/A"
            logging.debug(f"CPU freq: {result}")
            return result
        except Exception as e:
            logging.error(f"CPU freq error: {str(e)}")
            return "N/A"

    def get_cpu_temp(self):
        """Возвращает температуру CPU (если доступно)."""
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    if "core" in entry.label.lower():
                        logging.debug(f"CPU temp: {entry.current}")
                        return entry.current
            logging.debug("No CPU temp available")
            return "N/A"
        except Exception as e:
            logging.error(f"CPU temp error: {str(e)}")
            return "N/A"

    def get_ram_usage(self):
        """Возвращает использование RAM."""
        try:
            ram = psutil.virtual_memory()
            result = {
                "total": ram.total / (1024 ** 3),  # В ГБ
                "used": ram.used / (1024 ** 3),
                "free": ram.free / (1024 ** 3),
                "percent": ram.percent
            }
            logging.debug(f"RAM usage: {result}")
            return result
        except Exception as e:
            logging.error(f"RAM usage error: {str(e)}")
            return {"total": 0, "used": 0, "free": 0, "percent": 0}

    def get_disk_usage(self):
        """Возвращает использование диска (корневой раздел)."""
        try:
            disk = psutil.disk_usage('/')
            result = {
                "total": disk.total / (1024 ** 3),  # В ГБ
                "used": disk.used / (1024 ** 3),
                "free": disk.free / (1024 ** 3),
                "percent": disk.percent
            }
            logging.debug(f"Disk usage: {result}")
            return result
        except Exception as e:
            logging.error(f"Disk usage error: {str(e)}")
            return {"total": 0, "used": 0, "free": 0, "percent": 0}

    def get_disk_io(self):
        """Возвращает статистику чтения/записи диска."""
        try:
            io = psutil.disk_io_counters()
            result = {
                "read_bytes": io.read_bytes / (1024 ** 2) if io else 0,  # В МБ
                "write_bytes": io.write_bytes / (1024 ** 2) if io else 0  # В МБ
            }
            logging.debug(f"Disk IO: {result}")
            return result
        except Exception as e:
            logging.error(f"Disk IO error: {str(e)}")
            return {"read_bytes": 0, "write_bytes": 0}

    def get_gpu_usage(self):
        """Возвращает загрузку и температуру GPU (NVIDIA или Intel)."""
        try:
            # NVIDIA
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu', '--format=csv,noheader'],
                                  capture_output=True, text=True, timeout=1)
            usage, temp = result.stdout.strip().split(',')
            result = {
                "usage": int(usage.strip().strip('%')),
                "temp": int(temp.strip())
            }
            logging.debug(f"GPU usage (NVIDIA): {result}")
            return result
        except Exception as e:
            logging.error(f"NVIDIA GPU error: {str(e)}")
            try:
                # Intel
                result = subprocess.run(['intel_gpu_top', '-J'], capture_output=True, text=True, timeout=1)
                data = json.loads(result.stdout)
                usage = data.get('engines', {}).get('Render/3D', {}).get('busy', 0)
                result = {
                    "usage": usage,
                    "temp": "N/A"
                }
                logging.debug(f"GPU usage (Intel): {result}")
                return result
            except Exception as e:
                logging.error(f"Intel GPU error: {str(e)}")
                return {"usage": "N/A", "temp": "N/A"}

    def monitor_loop(self, callback, interval=1):
        """Запускает мониторинг и передает данные в callback."""
        try:
            while True:
                cpu_usage = self.get_cpu_usage()
                cpu_freq = self.get_cpu_freq()
                cpu_temp = self.get_cpu_temp()
                ram_info = self.get_ram_usage()
                disk_usage = self.get_disk_usage()
                disk_io = self.get_disk_io()
                gpu_info = self.get_gpu_usage()
                logging.debug("Calling callback with metrics")
                callback(cpu_usage, cpu_freq, cpu_temp, ram_info, disk_usage, disk_io, gpu_info)
                time.sleep(interval)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped gracefully")
            print("Monitoring stopped gracefully.")