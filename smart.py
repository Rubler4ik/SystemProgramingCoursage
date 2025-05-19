# smart.py
import subprocess
import logging
import platform
import re

logging.basicConfig(filename='smart.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize WMI_AVAILABLE without attempting import on Linux
WMI_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import wmi
        WMI_AVAILABLE = True
    except ImportError:
        logging.warning("WMI module not available; Windows S.M.A.R.T. monitoring will be disabled")

class SMARTMonitor:
    def get_smart_data_linux(self):
        try:
            result = subprocess.run(["smartctl", "--scan"], capture_output=True, text=True)
            devices = [line.split()[0] for line in result.stdout.splitlines()]
            smart_data = {}

            for device in devices:
                try:
                    info = subprocess.run(["smartctl", "-a", device], capture_output=True, text=True)
                    output = info.stdout
                    health = "PASS" if "PASSED" in output else "FAIL"
                    temp_match = re.search(r"Temperature_Celsius\s+\d+\s+(\d+)", output)
                    temperature = temp_match.group(1) if temp_match else "N/A"
                    reallocated_match = re.search(r"Reallocated_Sector_Ct\s+\d+\s+(\d+)", output)
                    reallocated = reallocated_match.group(1) if reallocated_match else "0"
                    wear_match = re.search(r"Wear_Leveling_Count\s+\d+\s+(\d+)", output)
                    wear = wear_match.group(1) if wear_match else "N/A"

                    smart_data[device] = {
                        "health_status": health,
                        "temperature": temperature,
                        "reallocated_sectors": reallocated,
                        "wear_level": wear
                    }
                except Exception as e:
                    logging.error(f"SMART error for {device}: {str(e)}")
            return smart_data
        except Exception as e:
            logging.error(f"SMART scan error: {str(e)}")
            return {}

    def get_smart_data_windows(self):
        if not WMI_AVAILABLE:
            logging.error("WMI module not available for Windows S.M.A.R.T. monitoring")
            return {}
        try:
            c = wmi.WMI(namespace="root\\wmi")
            smart_data = {}
            for disk in c.MSStorageDriver_FailurePredictStatus():
                disk_id = disk.InstanceName.split("\\")[2]
                health = "PASS" if not disk.PredictFailure else "FAIL"
                temperature = "N/A"  # Requires additional WMI class or external tool
                reallocated = "N/A"  # Requires additional logic
                wear = "N/A"  # Requires additional logic
                smart_data[disk_id] = {
                    "health_status": health,
                    "temperature": temperature,
                    "reallocated_sectors": reallocated,
                    "wear_level": wear
                }
            return smart_data
        except Exception as e:
            logging.error(f"Windows SMART error: {str(e)}")
            return {}

    def get_smart_data(self):
        if platform.system() == "Linux":
            return self.get_smart_data_linux()
        elif platform.system() == "Windows":
            return self.get_smart_data_windows()
        else:
            logging.warning("S.M.A.R.T. monitoring not supported on this OS")
            return {}