import sys
import os
import subprocess
import time

def run_all_suites():
    print("=======================================================================")
    print("   EJECUCIÓN DE TODAS LAS HISTORIAS DE USUARIO (HU-01 a HU-14)       ")
    print("   SISTEMA DE GESTIÓN CLÍNICA DENTAL GUSTAVO                          ")
    print("=======================================================================")

    test_files = [f"test_hu{i:02d}.py" for i in range(1, 15)]
    results = {}

    python_exe = sys.executable

    start_total = time.time()
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        t_start = time.time()
        res = subprocess.run([python_exe, test_path], capture_output=True, text=True)
        elapsed = time.time() - t_start
        status = "PASSED" if res.returncode == 0 else "FAILED"
        results[test_file] = (status, elapsed, res.stderr if res.returncode != 0 else "")
        print(f"[{status}] {test_file} ({elapsed:.2f}s)")
        if res.returncode != 0:
            print("ERROR DETALLE:")
            print(res.stdout[-500:])
            print(res.stderr[-500:])

    total_elapsed = time.time() - start_total
    print("\n=======================================================================")
    print(f"   RESUMEN FINAL: {sum(1 for s, _, _ in results.values() if s == 'PASSED')} / {len(test_files)} SUITES PASARON")
    print(f"   TIEMPO TOTAL: {total_elapsed:.2f}s")
    print("=======================================================================")

if __name__ == "__main__":
    run_all_suites()
