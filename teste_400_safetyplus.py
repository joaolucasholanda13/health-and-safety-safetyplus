
import argparse
import concurrent.futures
import json
import ssl
import time
import urllib.request
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--ca-file")
parser.add_argument("--authorize-load", action="store_true")
parser.add_argument("--stages", default="5,10,25")
args = parser.parse_args()

if not args.authorize_load:
    parser.error("É necessária autorização para executar o teste.")

ctx = ssl.create_default_context(cafile=args.ca_file)
results = []

def request():
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(
            args.url.rstrip("/") + "/login",
            context=ctx,
            timeout=10
        ) as response:
            status = response.status
            response.read(1024)
    except Exception as e:
        return (time.perf_counter() - start) * 1000, str(e)
    return (time.perf_counter() - start) * 1000, (
        None if status < 500 else f"HTTP {status}"
    )

for clients in map(int, args.stages.split(",")):
    print(f"\nTestando {clients} clientes simultâneos...")
    started = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=clients
    ) as executor:
        samples = list(executor.map(lambda _: request(), range(clients)))

    elapsed = time.perf_counter() - started
    latencies = sorted(x[0] for x in samples)
    errors = [x[1] for x in samples if x[1]]

    result = {
        "clientes": clients,
        "requisicoes": len(samples),
        "requisicoes_por_segundo": round(len(samples) / elapsed, 2),
        "latencia_media_ms": round(sum(latencies) / len(latencies), 2),
        "p95_ms": round(latencies[min(len(latencies)-1, int(len(latencies)*0.95))], 2),
        "erros": len(errors),
        "exemplos_erros": errors[:3],
    }
    results.append(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))

with open("resultado_400_safetyplus.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nRelatório salvo em resultado_400_safetyplus.json")
