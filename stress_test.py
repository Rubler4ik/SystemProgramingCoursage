import multiprocessing
import time


class StressTest:
    def cpu_stress(self, duration=10):
        """Нагружает CPU на указанное время (в секундах)."""

        def heavy_task():
            while True:
                # Интенсивные вычисления
                for i in range(1000000):
                    _ = i * i

        processes = []
        for _ in range(multiprocessing.cpu_count()):
            p = multiprocessing.Process(target=heavy_task)
            p.start()
            processes.append(p)

        time.sleep(duration)
        for p in processes:
            p.terminate()
        print(f"CPU stress test completed ({duration} seconds).")


# Тест
if __name__ == "__main__":
    stress = StressTest()
    stress.cpu_stress(5)  # Тест на 5 секунд