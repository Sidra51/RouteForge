import math
from typing import List, Dict, Any

class BenchmarkMetrics:
    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        """Calculate the given percentile (0 to 100) using linear interpolation."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        if len(sorted_vals) == 1:
            return float(sorted_vals[0])
        
        k = (len(sorted_vals) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return float(sorted_vals[int(k)])
        
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return float(d0 + d1)

    @staticmethod
    def calculate_std_dev(values: List[float], mean_val: float) -> float:
        """Calculate standard deviation of a sample values list."""
        if len(values) <= 1:
            return 0.0
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        return round(math.sqrt(variance), 2)

    @classmethod
    def aggregate_model_metrics(cls, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Group individual trial runs by (provider, model) and calculate statistical metrics:
        P50, P95, P99, Mean, StdDev, Cost, Throughput, and Success Rate.
        """
        if not runs:
            return {}

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in runs:
            key = f"{r['provider']}::{r['model']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(r)

        result: Dict[str, Dict[str, Any]] = {}

        for key, item_runs in grouped.items():
            provider, model = key.split("::")
            total_trials = len(item_runs)
            successful_runs = [r for r in item_runs if r.get("is_success")]
            success_rate = round((len(successful_runs) / total_trials) * 100.0, 1)

            latencies = [float(r["latency_ms"]) for r in item_runs if r.get("latency_ms") is not None]
            
            if latencies:
                mean_lat = round(sum(latencies) / len(latencies), 1)
                p50_lat = round(cls.calculate_percentile(latencies, 50), 1)
                p95_lat = round(cls.calculate_percentile(latencies, 95), 1)
                p99_lat = round(cls.calculate_percentile(latencies, 99), 1)
                std_dev_lat = cls.calculate_std_dev(latencies, mean_lat)
            else:
                mean_lat = p50_lat = p95_lat = p99_lat = std_dev_lat = 0.0

            costs = [float(r.get("cost", 0.0)) for r in item_runs]
            mean_cost = round(sum(costs) / len(costs), 6) if costs else 0.0
            total_cost = round(sum(costs), 6)

            gen_tps_vals = [float(r.get("generation_tokens_per_sec", 0.0)) for r in successful_runs]
            mean_gen_tps = round(sum(gen_tps_vals) / len(gen_tps_vals), 2) if gen_tps_vals else 0.0

            e2e_tps_vals = [float(r.get("end_to_end_tokens_per_sec", 0.0)) for r in successful_runs]
            mean_e2e_tps = round(sum(e2e_tps_vals) / len(e2e_tps_vals), 2) if e2e_tps_vals else 0.0

            scores = [float(r.get("quality_score")) for r in successful_runs if r.get("quality_score") is not None]
            mean_quality = round(sum(scores) / len(scores), 2) if scores else 0.0

            result[key] = {
                "provider": provider,
                "model": model,
                "total_trials": total_trials,
                "successful_trials": len(successful_runs),
                "success_rate": success_rate,
                "mean_latency_ms": mean_lat,
                "p50_latency_ms": p50_lat,
                "p95_latency_ms": p95_lat,
                "p99_latency_ms": p99_lat,
                "std_dev_latency_ms": std_dev_lat,
                "mean_cost": mean_cost,
                "total_cost": total_cost,
                "mean_generation_tps": mean_gen_tps,
                "mean_e2e_tps": mean_e2e_tps,
                "mean_quality_score": mean_quality
            }

        return result
