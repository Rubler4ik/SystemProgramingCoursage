import psutil
import logging

logging.basicConfig(filename='diagnostics.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Diagnostics:
    def check_hardware(self):
        """Проверяет состояние железа."""
        errors = []

        # Проверка температуры CPU
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    if "core" in entry.label.lower() and entry.current > 90:
                        error = f"High CPU temperature: {entry.current}°C"
                        errors.append(error)
                        logging.warning(error)
        except:
            pass

        # Проверка ошибок диска
        try:
            io = psutil.disk_io_counters()
            if io.read_time > 10000 or io.write_time > 10000:
                error = "High disk I/O latency detected"
                errors.append(error)
                logging.warning(error)
        except:
            pass

        # Проверка RAM
        ram = psutil.virtual_memory()
        if ram.percent > 95:
            error = "Critical RAM usage: {:.1f}%".format(ram.percent)
            errors.append(error)
            logging.warning(error)

        return errors