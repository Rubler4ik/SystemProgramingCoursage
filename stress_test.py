import multiprocessing
import time
import os
import psutil
import numpy as np
import pyopencl as cl
import logging
import csv

logging.basicConfig(filename='stress_test.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class StressTest:
    def __init__(self):
        self.errors = []

    def cpu_stress(self, duration=10):
        """Нагружает CPU."""

        def heavy_task():
            while True:
                for i in range(1000000):
                    _ = i * i

        processes = []
        try:
            logging.info(f"Starting CPU stress test for {duration} seconds")
            for _ in range(multiprocessing.cpu_count()):
                p = multiprocessing.Process(target=heavy_task)
                p.start()
                processes.append(p)
            time.sleep(duration)
        except Exception as e:
            self.errors.append(f"CPU test error: {str(e)}")
            logging.error(f"CPU test error: {str(e)}")
        finally:
            for p in processes:
                p.terminate()
        logging.info(f"CPU stress test completed ({duration} seconds).")

    def disk_stress(self, duration=10, file_size_mb=100):
        """Нагружает диск."""
        temp_file = "temp_test_file.bin"
        file_size = file_size_mb * 1024 * 1024

        disk = psutil.disk_usage('/')
        free_space = disk.free / (1024 ** 2)
        if free_space < file_size_mb * 2:
            error = f"Not enough free space ({free_space:.2f} MB available, {file_size_mb * 2} MB needed)"
            self.errors.append(error)
            logging.error(error)
            return

        start_time = time.time()
        try:
            logging.info(f"Starting disk stress test for {duration} seconds, file size {file_size_mb} MB")
            while time.time() - start_time < duration:
                with open(temp_file, "wb") as f:
                    f.write(os.urandom(file_size))
                with open(temp_file, "rb") as f:
                    f.read()
        except Exception as e:
            self.errors.append(f"Disk test error: {str(e)}")
            logging.error(f"Disk test error: {str(e)}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        logging.info(f"Disk stress test completed ({duration} seconds, {file_size_mb} MB).")

    def ram_stress(self, duration=10, size_mb=128):
        """Нагружает RAM и измеряет скорость/задержки."""
        ram = psutil.virtual_memory()
        free_mb = ram.free / (1024 ** 2)
        if free_mb < size_mb * 1.5:
            error = f"Not enough free RAM ({free_mb:.2f} MB available, {size_mb * 1.5} MB needed)"
            self.errors.append(error)
            logging.error(error)
            return 0, 0

        size = int(size_mb * 1024 * 1024 / 8)
        start_time = time.time()
        arrays = []
        speeds = []
        latencies = []
        try:
            logging.info(f"Starting RAM stress test for {duration} seconds, size {size_mb} MB")
            while time.time() - start_time < duration:
                t_start = time.time()
                arr = np.zeros(size, dtype=np.float64)
                arrays.append(arr)
                write_time = time.time() - t_start
                write_speed = size_mb / write_time  # МБ/с
                speeds.append(write_speed)

                t_start = time.time()
                _ = arr[np.random.randint(0, size)]
                latency = (time.time() - t_start) * 1000  # мс
                latencies.append(latency)

                time.sleep(0.1)
        except Exception as e:
            self.errors.append(f"RAM test error: {str(e)}")
            logging.error(f"RAM test error: {str(e)}")
        finally:
            arrays.clear()
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        logging.info(
            f"RAM stress test completed ({duration} seconds, {size_mb} MB, Speed: {avg_speed:.2f} MB/s, Latency: {avg_latency:.2f} ms)")

        # Логирование в CSV
        with open("ram_test_results.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([time.time(), size_mb, avg_speed, avg_latency])

        return avg_speed, avg_latency

    def gpu_stress(self, duration=10):
        """Нагружает GPU с помощью PyOpenCL."""
        try:
            logging.info(f"Starting GPU stress test for {duration} seconds")
            platform = cl.get_platforms()[0]
            device = platform.get_devices()[0]
            ctx = cl.Context([device])
            queue = cl.CommandQueue(ctx)

            size = 2048
            a = np.random.rand(size, size).astype(np.float32)
            b = np.random.rand(size, size).astype(np.float32)
            c = np.zeros((size, size), dtype=np.float32)

            mf = cl.mem_flags
            a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
            b_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
            c_buf = cl.Buffer(ctx, mf.WRITE_ONLY, c.nbytes)

            prg = cl.Program(ctx, """
                __kernel void matmul(__global float *a, __global float *b, __global float *c, int size) {
                    int i = get_global_id(0);
                    int j = get_global_id(1);
                    float sum = 0;
                    for (int k = 0; k < size; k++) {
                        sum += a[i * size + k] * b[k * size + j];
                    }
                    c[i * size + j] = sum;
                }
            """).build()

            start_time = time.time()
            while time.time() - start_time < duration:
                prg.matmul(queue, (size, size), None, a_buf, b_buf, c_buf, np.int32(size))
                queue.finish()
        except Exception as e:
            self.errors.append(f"GPU test error: {str(e)}")
            logging.error(f"GPU test error: {str(e)}")
        logging.info(f"GPU stress test completed ({duration} seconds).")

    def get_errors(self):
        """Возвращает список ошибок."""
        return self.errors