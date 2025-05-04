import psutil
import time


class SystemMonitor:
    def get_cpu_usage(self):
        """Возвращает загрузку CPU в процентах для каждого ядра."""
        return psutil.cpu_percent(interval=1, percpu=True)

    def get_cpu_freq(self):
        """Возвращает частоту CPU."""
        freq = psutil.cpu_freq()
        return freq.current if freq else "N/A"

    def get_ram_usage(self):
        """Возвращает использование RAM (всего, использовано, свободно)."""
        ram = psutil.virtual_memory()
        return {
            "total": ram.total / (1024 ** 3),  # В ГБ
            "used": ram.used / (1024 ** 3),
            "free": ram.free / (1024 ** 3),
            "percent": ram.percent
        }

    def monitor_loop(self, callback, interval=1):
        """Запускает мониторинг и передает данные в callback."""
        while True:
            cpu_usage = self.get_cpu_usage()
            ram_info = self.get_ram_usage()
            callback(cpu_usage, ram_info)
            time.sleep(interval)


# Тест
if __name__ == "__main__":
    monitor = SystemMonitor()


    def print_metrics(cpu, ram):
        print(f"CPU Usage: {cpu}")
        print(f"RAM: {ram['percent']}% (Used: {ram['used']:.2f} GB, Free: {ram['free']:.2f} GB)")


    monitor.monitor_loop(print_metrics)